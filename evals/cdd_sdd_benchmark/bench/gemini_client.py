"""Minimal REST client for the Gemini API `generateContent` endpoint.

Design rules (see DESIGN.md, "Harness-error policy"):

* Function calling, `systemInstruction`, and `generationConfig` are passed
  through as-is.
* Model `content` objects are returned verbatim (`ModelResponse.content`) so the
  caller can replay them, including `thoughtSignature` fields that Gemini 3
  requires on multi-turn function calling.
* Transport errors (429, 5xx, timeouts, connection resets, unparseable bodies)
  and EMPTY candidates (no visible text and no function call) are retried up to
  `max_retries` times with exponential backoff and jitter. After that the call
  raises `HarnessError`. The client never returns an empty string silently and
  never switches to a different model.
* One process-wide semaphore bounds concurrent requests; a shared cooldown
  stretches after every 429 (adaptive backoff) and decays on success.
* The API key comes from `GEMINI_API_KEY`, travels in a header (never in the
  URL), and is never logged or included in error messages.
"""

from __future__ import annotations

import dataclasses
import json
import logging
import os
import random
import re
import socket
import threading
import time
import urllib.error
import urllib.request
from typing import Any, Callable, Dict, List, Optional

from bench import schema

API_ROOT = "https://generativelanguage.googleapis.com/v1beta/models"
DEFAULT_MAX_OUTPUT_TOKENS = 16384
RETRYABLE_HTTP = frozenset({408, 429, 500, 502, 503, 504})
EMPTY_RETRY_SEED_STRIDE = 1_000_003
CONTEXT_OVERFLOW_RE = re.compile(
    r"exceeds the maximum number of tokens|input token count.*exceeds|"
    r"context (window|length)", re.I)

_LOG = logging.getLogger(__name__)


class HarnessError(RuntimeError):
  """Infrastructure failure. Rollouts that hit it are excluded from scoring."""


class ContextOverflowError(HarnessError):
  """The request exceeded the model's context window (HTTP 400).

  This is a property of the framework's prompts and transcript size, not of
  the infrastructure, so the agent loop scores it (turn ended_by
  "context_overflow") instead of excluding the rollout.
  """


@dataclasses.dataclass
class ModelResponse:
  """One accepted `generateContent` candidate."""

  text: str  # Visible text (thought parts excluded).
  function_calls: List[Dict[str, Any]]  # [{"name", "args", "id"?}]
  content: Dict[str, Any]  # Raw candidate content, for verbatim replay.
  finish_reason: str
  usage: schema.Usage  # Usage of the accepted response only.
  attempts: int  # HTTP requests made, including retries.
  retried_finish_reasons: List[str]  # finishReason of discarded attempts.
  retry_reasons: List[str]  # Why each discarded attempt was retried.
  # Tokens billed on discarded (empty) attempts; excluded from `usage` so
  # output-length checks see only the accepted response.
  retry_usage: schema.Usage = dataclasses.field(default_factory=schema.Usage)


class _Throttle:
  """Process-wide concurrency limit plus adaptive 429 cooldown."""

  def __init__(self, max_concurrency: int):
    self._sem = threading.BoundedSemaphore(max(1, max_concurrency))
    self._lock = threading.Lock()
    self._cooldown_s = 0.0
    self._not_before = 0.0

  def acquire(self) -> None:
    self._sem.acquire()
    while True:
      with self._lock:
        wait = self._not_before - time.monotonic()
      if wait <= 0:
        return
      time.sleep(min(wait, 5.0))

  def release(self) -> None:
    self._sem.release()

  def on_rate_limited(self) -> None:
    with self._lock:
      self._cooldown_s = min(60.0, max(2.0, self._cooldown_s * 2))
      self._not_before = max(
          self._not_before,
          time.monotonic() + self._cooldown_s * (0.5 + random.random()),
      )

  def on_success(self) -> None:
    with self._lock:
      self._cooldown_s *= 0.8
      if self._cooldown_s < 0.5:
        self._cooldown_s = 0.0


_THROTTLE_LOCK = threading.Lock()
_THROTTLE: Optional[_Throttle] = None


def set_concurrency(max_concurrency: int) -> None:
  """Sets the process-wide limit on in-flight API requests."""
  global _THROTTLE
  with _THROTTLE_LOCK:
    _THROTTLE = _Throttle(max_concurrency)


def _throttle() -> _Throttle:
  global _THROTTLE
  with _THROTTLE_LOCK:
    if _THROTTLE is None:
      _THROTTLE = _Throttle(8)
    return _THROTTLE


def usage_from_metadata(meta: Dict[str, Any], latency_s: float) -> schema.Usage:
  """Maps `usageMetadata` to `schema.Usage` (never uses totalTokenCount)."""
  return schema.Usage(
      input_tokens=int(meta.get("promptTokenCount", 0) or 0),
      output_tokens=int(meta.get("candidatesTokenCount", 0) or 0),
      thinking_tokens=int(meta.get("thoughtsTokenCount", 0) or 0),
      cached_tokens=int(meta.get("cachedContentTokenCount", 0) or 0),
      api_calls=1,
      latency_s=latency_s,
  )


def parse_candidate(body: Dict[str, Any]) -> Optional[Dict[str, Any]]:
  """Extracts text, function calls, and raw content from a response body.

  Returns None when the response has no usable candidate (no visible text and
  no function call), which the caller treats as a retryable empty response.
  """
  cands = body.get("candidates") or []
  if not cands:
    return None
  cand = cands[0]
  content = cand.get("content") or {}
  parts = content.get("parts") or []
  texts: List[str] = []
  calls: List[Dict[str, Any]] = []
  for p in parts:
    if "functionCall" in p:
      fc = p["functionCall"] or {}
      call = {"name": fc.get("name", ""), "args": fc.get("args") or {}}
      if fc.get("id"):
        call["id"] = fc["id"]
      calls.append(call)
    elif "text" in p and not p.get("thought"):
      texts.append(p["text"])
  text = "".join(texts)
  if not text.strip() and not calls:
    return {"empty": True, "finish_reason": cand.get("finishReason", "")}
  if "role" not in content:
    content = dict(content, role="model")
  return {
      "empty": False,
      "text": text,
      "function_calls": calls,
      "content": content,
      "finish_reason": cand.get("finishReason", ""),
  }


class GeminiClient:
  """Thread-safe Gemini REST client with honest retry semantics."""

  def __init__(
      self,
      api_key: Optional[str] = None,
      timeout_s: float = 300.0,
      max_retries: int = 4,
      base_backoff_s: float = 2.0,
      max_backoff_s: float = 60.0,
      urlopen: Optional[Callable[..., Any]] = None,
      sleep: Callable[[float], None] = time.sleep,
  ):
    self._api_key = api_key if api_key is not None else os.environ.get(
        "GEMINI_API_KEY", ""
    )
    if not self._api_key:
      raise HarnessError("GEMINI_API_KEY is not set")
    self._timeout_s = timeout_s
    self._max_retries = max_retries
    self._base_backoff_s = base_backoff_s
    self._max_backoff_s = max_backoff_s
    self._urlopen = urlopen or urllib.request.urlopen
    self._sleep = sleep

  def __repr__(self) -> str:  # Never expose the key.
    return "GeminiClient(api_key=<redacted>)"

  def _backoff(self, attempt: int) -> float:
    base = min(self._max_backoff_s, self._base_backoff_s * (2**attempt))
    return base * (0.5 + random.random() * 0.5)

  def generate(
      self,
      model: str,
      contents: List[Dict[str, Any]],
      system_instruction: Optional[str] = None,
      tools: Optional[List[Dict[str, Any]]] = None,
      temperature: Optional[float] = 1.0,
      seed: Optional[int] = None,
      max_output_tokens: int = DEFAULT_MAX_OUTPUT_TOKENS,
      response_mime_type: Optional[str] = None,
      extra_generation_config: Optional[Dict[str, Any]] = None,
      tool_config: Optional[Dict[str, Any]] = None,
  ) -> ModelResponse:
    """Calls `models/{model}:generateContent`; see module docstring."""
    gen: Dict[str, Any] = {"maxOutputTokens": max_output_tokens}
    if temperature is not None:
      gen["temperature"] = temperature
    if seed is not None:
      gen["seed"] = int(seed)
    if response_mime_type:
      gen["responseMimeType"] = response_mime_type
    if extra_generation_config:
      gen.update(extra_generation_config)
    payload: Dict[str, Any] = {"contents": contents, "generationConfig": gen}
    if system_instruction:
      payload["systemInstruction"] = {"parts": [{"text": system_instruction}]}
    if tools:
      payload["tools"] = [{"functionDeclarations": tools}]
    if tool_config:
      payload["toolConfig"] = tool_config
    url = f"{API_ROOT}/{model}:generateContent"

    retry_reasons: List[str] = []
    retried_finish: List[str] = []
    attempts = 0
    empty_retries = 0
    retry_usage = schema.Usage()
    throttle = _throttle()
    for attempt in range(self._max_retries + 1):
      attempts += 1
      if seed is not None:
        # After an empty candidate, resending the identical seeded payload
        # tends to reproduce the same empty output, so empty-candidate
        # retries perturb the seed (transport retries keep it).
        gen["seed"] = int(seed) + EMPTY_RETRY_SEED_STRIDE * empty_retries
      data = json.dumps(payload).encode("utf-8")
      reason = ""
      rate_limited = False
      req = urllib.request.Request(
          url,
          data=data,
          method="POST",
          headers={
              "Content-Type": "application/json",
              "x-goog-api-key": self._api_key,
          },
      )
      throttle.acquire()
      t0 = time.monotonic()
      try:
        with self._urlopen(req, timeout=self._timeout_s) as resp:
          raw = resp.read()
        latency = time.monotonic() - t0
      except urllib.error.HTTPError as e:
        latency = time.monotonic() - t0
        detail = _http_error_detail(e)
        if e.code == 400 and CONTEXT_OVERFLOW_RE.search(detail):
          raise ContextOverflowError(
              f"{model}: context window exceeded: {detail}") from None
        if e.code not in RETRYABLE_HTTP:
          raise HarnessError(
              f"{model}: HTTP {e.code} (not retryable): {detail}"
          ) from None
        rate_limited = e.code == 429
        reason = f"HTTP {e.code}: {detail}"
        raw = None
      except (urllib.error.URLError, socket.timeout, TimeoutError,
              ConnectionError, OSError) as e:
        latency = time.monotonic() - t0
        reason = f"transport: {type(e).__name__}: {e}"
        raw = None
      finally:
        if rate_limited:
          throttle.on_rate_limited()
        throttle.release()

      if raw is not None:
        try:
          body = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as e:
          body = None
          reason = f"unparseable body: {e}"
        if body is not None:
          parsed = parse_candidate(body)
          if parsed is not None and not parsed["empty"]:
            throttle.on_success()
            return ModelResponse(
                text=parsed["text"],
                function_calls=parsed["function_calls"],
                content=parsed["content"],
                finish_reason=parsed["finish_reason"],
                usage=usage_from_metadata(
                    body.get("usageMetadata") or {}, latency
                ),
                attempts=attempts,
                retried_finish_reasons=retried_finish,
                retry_reasons=retry_reasons,
                retry_usage=retry_usage,
            )
          if body.get("usageMetadata"):
            retry_usage.add(usage_from_metadata(body["usageMetadata"],
                                                latency))
          fr = parsed["finish_reason"] if parsed else ""
          block = (body.get("promptFeedback") or {}).get("blockReason", "")
          retried_finish.append(fr or "NO_CANDIDATE")
          reason = (
              f"empty candidate (finishReason={fr or 'none'}"
              + (f", blockReason={block}" if block else "")
              + (f", seed={gen['seed']}" if "seed" in gen else "")
              + ")"
          )
          empty_retries += 1
      retry_reasons.append(reason)
      _LOG.warning(
          "%s attempt %d/%d failed: %s",
          model, attempt + 1, self._max_retries + 1, reason,
      )
      if attempt < self._max_retries:
        self._sleep(self._backoff(attempt))
    raise HarnessError(
        f"{model}: failed after {attempts} attempts; last: {retry_reasons[-1]}"
    )


def _http_error_detail(e: urllib.error.HTTPError) -> str:
  try:
    body = e.read().decode("utf-8", "replace")
    msg = json.loads(body).get("error", {}).get("message", body)
  except Exception:  # pylint: disable=broad-except
    msg = str(e.reason)
  return str(msg)[:300]
