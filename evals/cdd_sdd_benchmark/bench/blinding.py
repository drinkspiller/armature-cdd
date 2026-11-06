"""Framework-identifier scrubbing for judge inputs.

The judge must not be able to tell which framework produced a transcript from
the framework's name, its slash commands, or its context-directory names.
`blind()` replaces every identifier from the UNION of all frameworks in a run
with a neutral token, so the judge cannot infer the framework from which
identifiers survive.

Residual unblinding risk (documented, not mitigated here): blinding only
replaces identifiers. It does not rewrite content. A framework's distinctive
output structure (headings, checklists, interview formats, file naming such as
numbered decision records, phrase patterns copied from its pack) can still be
recognizable to a judge model that has seen the upstream repos. The report's
Limitations section states this. Altering content beyond identifiers would
change what is being judged, so this module deliberately does not do that.
(bench/judge.py separately withholds read_file/list_dir results and the
host-expanded command body, because those return pack text verbatim.)

Identifier hygiene: generic English words (for example "specify", "plan",
"track") are not in DEFAULT_IDENTIFIERS because scrubbing them would damage
ordinary prose. If a pack lists such a word, it is scrubbed everywhere for all
frameworks alike, which keeps blinding symmetric at some cost to readability.
"""

from __future__ import annotations

import itertools
import re
from typing import Iterable, List, Sequence

FRAMEWORK_TOKEN = "[FRAMEWORK]"
COMMAND_TOKEN = "[COMMAND]"
CONTEXT_DIR_TOKEN = "[CONTEXT_DIR]"
CONTEXT_FILE_TOKEN = "[CONTEXT_FILE]"
_FILE_RE = re.compile(r"\.(md|mdc|toml|json|ya?ml|txt|sh|py|js|ts)$", re.I)

# Baseline identifiers that are always scrubbed, even if a pack forgets to
# list them. Packs add their own via FrameworkPack.identifiers().
DEFAULT_IDENTIFIERS = (
    "armature",
    "armature-cdd",
    "conductor",
    "spec kit",
    "spec-kit",
    "speckit",
    "openspec",
    "bmad",
    "bmad-method",
    "memory bank",
    "memory-bank",
    "internal_sdd",
    "wayfinder",
    ".specify/",
    "openspec/",
    "memory-bank/",
    "armature/",
    "conductor/",
    ".bmad-core/",
)

_CMD_PREFIX_RE = re.compile(r"^[/@*]")


def _classify(ident: str) -> str:
  """Returns the neutral token class for one identifier."""
  s = ident.strip()
  if _CMD_PREFIX_RE.match(s) and len(s) > 1:
    return COMMAND_TOKEN
  if s.endswith("/") or s.startswith("."):
    return CONTEXT_DIR_TOKEN
  if _FILE_RE.search(s) and " " not in s:
    return CONTEXT_FILE_TOKEN
  # Dotted or hyphenated command stems such as "speckit.plan", "arm-new-track",
  # "bmad-master" are command-like when they contain a separator.
  if re.search(r"[a-z0-9][.\-:][a-z]", s, re.I) and " " not in s:
    return COMMAND_TOKEN
  return FRAMEWORK_TOKEN


def _variants(ident: str) -> List[str]:
  """Expands an identifier into the surface forms that appear in text."""
  s = ident.strip()
  out = {s}
  core = s.strip("/")
  if s.endswith("/") or s.startswith("."):
    out.add(core)  # "openspec/" also appears as bare "openspec" in paths.
  # A "/name" command does NOT imply its bare form: many packs use generic
  # English skill names (/implement, /research, /pr), and scrubbing the bare
  # word would damage ordinary prose. Packs list bare forms explicitly when
  # the name is framework-distinctive (for example "arm-new-track").
  if " " in s:
    out.add(s.replace(" ", "-"))
    out.add(s.replace(" ", "_"))
    out.add(s.replace(" ", ""))
  if "-" in core and "/" not in core:
    out.add(core.replace("-", "_"))
  return [v for v in out if v]


def build_patterns(identifiers: Iterable[str]) -> List[tuple]:
  """Returns (regex_source, token) pairs, longest surface form first."""
  forms = {}
  for ident in list(DEFAULT_IDENTIFIERS) + list(identifiers or []):
    if not ident or not ident.strip():
      continue
    token = _classify(ident)
    for v in _variants(ident):
      key = v.lower()
      # A command form wins over a bare-name form for the same string.
      if key not in forms or token == COMMAND_TOKEN:
        forms[key] = (v, token)
  ordered = sorted(forms.values(), key=lambda x: (-len(x[0]), x[0].lower()))
  pats = []
  for v, token in ordered:
    esc = re.escape(v)
    # Word-ish boundaries: do not match inside a longer identifier, but allow
    # path separators, punctuation, and whitespace on either side.
    left = r"(?<![A-Za-z0-9_])" if re.match(r"[A-Za-z0-9_]", v) else ""
    if v.startswith("/"):
      # A slash command starts a token; "/pr" must not match inside
      # "docs/pr" or "a.b/pr".
      left = r"(?<![A-Za-z0-9_./-])"
    right = r"(?![A-Za-z0-9_])" if re.search(r"[A-Za-z0-9_]$", v) else ""
    pats.append((left + esc + right, token))
  return pats


_CACHE = {}


def _compiled(identifiers: Sequence[str]):
  """Returns (combined regex, lowercased_surface -> token dict), memoized."""
  key = tuple(sorted(set(identifiers or [])))
  if key not in _CACHE:
    forms = {}
    for ident in list(DEFAULT_IDENTIFIERS) + list(key):
      if not ident or not ident.strip():
        continue
      token = _classify(ident)
      for v in _variants(ident):
        low = v.lower()
        if low not in forms or token == COMMAND_TOKEN:
          forms[low] = (v, token)
    ordered = sorted(forms.values(), key=lambda x: (-len(x[0]), x[0].lower()))
    tok_map = {}
    items = []
    for v, token in ordered:
      tok_map[v.lower()] = token
      esc = re.escape(v)
      left = r"(?<![A-Za-z0-9_])" if re.match(r"[A-Za-z0-9_]", v) else ""
      if v.startswith("/"):
        left = r"(?<![A-Za-z0-9_./-])"
      right = r"(?![A-Za-z0-9_])" if re.search(r"[A-Za-z0-9_]$", v) else ""
      items.append((left, right, esc))
    chunks = [
        f"{l}(?:{'|'.join(x[2] for x in grp)}){r}"
        for (l, r), grp in itertools.groupby(items, key=lambda x: (x[0], x[1]))
    ]
    _CACHE[key] = (re.compile("|".join(chunks), re.IGNORECASE), tok_map)
  return _CACHE[key]


def blind(text: str, identifiers: Sequence[str]) -> str:
  """Replaces every framework identifier in `text` with a neutral token.

  Args:
    text: Transcript, action log, or path text.
    identifiers: Union of FrameworkPack.identifiers() across ALL frameworks in
      the run. DEFAULT_IDENTIFIERS are always included.

  Returns:
    The text with identifiers replaced by [FRAMEWORK], [COMMAND],
    [CONTEXT_DIR], or [CONTEXT_FILE]. Matching is case-insensitive and
    longest-first. Nothing else in the text is changed.
  """
  if not text:
    return text
  regex, tok_map = _compiled(identifiers)
  return regex.sub(lambda m: tok_map[m.group(0).lower()], text)


def surviving_identifiers(text: str, identifiers: Sequence[str]) -> List[str]:
  """Returns identifiers still present after blinding (should be empty)."""
  blinded = blind(text, identifiers)
  low = blinded.lower()
  found = []
  for ident in list(DEFAULT_IDENTIFIERS) + list(identifiers or []):
    raw = ident.strip().lower()
    s = raw if raw.startswith("/") else raw.strip("/")
    if len(s) < 3:
      continue
    left = r"(?<![a-z0-9_./-])" if s.startswith("/") else r"(?<![a-z0-9_])"
    if re.search(left + re.escape(s) + r"(?![a-z0-9_])", low):
      found.append(ident)
  return found
