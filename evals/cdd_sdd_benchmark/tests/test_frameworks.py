"""Tests for bench/frameworks.py, fetch_packs.py lockfile logic, and leakage_audit.py.

Hermetic: synthetic packs in temp dirs. Tests that need the real fetched packs
are skipped when the pack cache is absent.

Run from BASE: PYTHONDONTWRITEBYTECODE=1 python3 -m unittest tests.test_frameworks
"""

import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

sys.dont_write_bytecode = True
BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE)

from bench import frameworks as fw  # pylint: disable=g-import-not-at-top
from bench import schema  # pylint: disable=g-import-not-at-top
import fetch_packs  # pylint: disable=g-import-not-at-top
import leakage_audit  # pylint: disable=g-import-not-at-top

_PC = {
    "product": "A billing service for small shops.",
    "tech_stack": ["Go / gRPC", "Postgres"],
    "decisions": [{"id": "ADR-0002", "title": "Use gRPC", "status": "accepted",
                   "body": "All internal services talk gRPC."}],
    "glossary": [{"term": "Invoice", "definition": "A bill sent to a shop."}],
    "prior_plan": {"title": "Add refunds", "summary": "Refund flow.",
                   "decisions": ["Refunds are async"],
                   "tasks": [{"text": "Add table", "done": True},
                             {"text": "Add RPC", "done": False}]},
}


def _write(root, rel, text):
  path = os.path.join(root, rel)
  os.makedirs(os.path.dirname(path), exist_ok=True)
  with open(path, "w", encoding="utf-8") as f:
    f.write(text)


class FakePackTest(unittest.TestCase):
  """Synthetic pack covering every registry feature."""

  def setUp(self):
    super().setUp()
    self.root = tempfile.mkdtemp(prefix="fwtest-")
    self.addCleanup(shutil.rmtree, self.root, ignore_errors=True)
    _write(self.root, "rules/core.md",
           "---\ntrigger: always_on\ndescription: x\n---\n\n# Core rule\nSee "
           "~/.host/plugins/fake/skills/plan/SKILL.md\n")
    _write(self.root, "rules/second.md", "# Second rule\n")
    _write(self.root, "skills/plan/SKILL.md",
           "---\nname: fake-plan\ndescription: >-\n  Plan a feature\n  carefully.\n"
           "---\n\nPlan this: $ARGUMENTS\n")
    _write(self.root, "skills/plan/workflow.md", "step 1\n")
    _write(self.root, "skills/review/SKILL.md",
           "---\nname: fake-review\ndescription: 'Review it''s work'\n---\n\nReview body.\n")
    _write(self.root, "commands/fix.toml",
           'description = "Fix a bug"\nprompt = """\nFix: {{args}}\n"""\n')
    _write(self.root, "scripts/run.sh", "#!/bin/bash\necho ran \"$@\"\n")
    _write(self.root, "skip/me.md", "nope\n")
    self.entry = {
        "key": "fakefw",
        "display_name": "Fake Framework",
        "paradigm": "Testing",
        "visibility": "public",
        "source": {"type": "local", "path": "unused"},
        "always_on": ["rules/core.md", "rules/second.md"],
        "skills_index": {"fake-plan": "skills/plan/SKILL.md",
                         "fake-review": "skills/review/SKILL.md",
                         "fake:fix": "commands/fix.toml"},
        "commands": {"fp": "skills/plan/SKILL.md"},
        "extra_files": ["skills/**", "scripts/*.sh"],
        "exclude_files": ["skip/**"],
        "install_map": [["scripts/(.+)", ".fake/scripts/\\1"]],
        "copies": [["rules/second.md", ".fake/copy.md"]],
        "generated_files": {".fake/config.toml": "a = 1\n"},
        "path_rewrites": [["~/.host/plugins/fake/", ".agent/fakefw/"]],
        "intent_map": {"feature_plan": "fp", "hotfix": "fake:fix",
                       "review": "fake-review"},
        "context_layout": "generic",
        "pack_commands": [{"id": "sh", "kind": "bash_script",
                           "match": r"^(bash\s+)?\.fake/scripts/",
                           "path_globs": [".fake/scripts/*.sh"]}],
        "identifiers": ["FakeFW"],
    }

  def _pack(self, entry=None, lock=None, verify=True):
    return fw.FrameworkPack(entry or self.entry, self.root, lock, verify=verify)

  def test_source_file_order_and_globs(self):
    files = fw.expand_source_files(self.entry, self.root)
    self.assertEqual(files[:5], ["rules/core.md", "rules/second.md",
                                 "skills/plan/SKILL.md",
                                 "skills/review/SKILL.md", "commands/fix.toml"])
    self.assertIn("skills/plan/workflow.md", files)
    self.assertIn("scripts/run.sh", files)
    self.assertNotIn("skip/me.md", files)

  def test_missing_explicit_file_raises(self):
    entry = dict(self.entry, always_on=["rules/missing.md"])
    with self.assertRaises(fw.PackError):
      self._pack(entry)

  def test_system_prompt_order_index_and_rewrites(self):
    sp = self._pack().system_prompt("BASE PROMPT")
    self.assertTrue(sp.startswith("BASE PROMPT\n\n"))
    self.assertLess(sp.index("# Core rule"), sp.index("# Second rule"))
    self.assertNotIn("trigger: always_on", sp)  # Frontmatter stripped.
    self.assertIn(".agent/fakefw/skills/plan/SKILL.md", sp)  # Rewritten path.
    self.assertNotIn("~/.host", sp)
    self.assertIn("- fake-plan: Plan a feature carefully. (path: "
                  ".agent/fakefw/skills/plan/SKILL.md)", sp)
    self.assertIn("- fake-review: Review it's work", sp)
    self.assertIn("- fake:fix: Fix a bug (path: .agent/fakefw/commands/fix.toml)", sp)
    self.assertIn("read_file", sp)

  def test_empty_pack_leaves_base_prompt(self):
    entry = dict(self.entry, always_on=[], skills_index={}, commands={},
                 intent_map={})
    self.assertEqual(self._pack(entry).system_prompt("BASE"), "BASE\n")

  def test_sandbox_files(self):
    sb = self._pack().sandbox_files()
    self.assertIn(".agent/fakefw/skills/plan/workflow.md", sb)
    self.assertIn(".fake/scripts/run.sh", sb)
    self.assertEqual(sb[".fake/copy.md"], "# Second rule\n")
    self.assertEqual(sb[".fake/config.toml"], "a = 1\n")
    self.assertIn(".agent/fakefw/skills", sb[".agent/fakefw/rules/core.md"])

  def test_expand_user_message(self):
    p = self._pack()
    self.assertEqual(p.expand_user_message("drift_audit", "hello"), "hello")
    out = p.expand_user_message("feature_plan", "add refunds")
    self.assertIn("Plan this: add refunds", out)
    self.assertTrue(out.startswith(
        "Base directory for this command: .agent/fakefw/skills/plan"))
    self.assertNotIn("$ARGUMENTS", out)
    self.assertIn("Fix: crash on login", p.expand_user_message("hotfix", "crash on login"))
    review = p.expand_user_message("review", "the diff")
    self.assertTrue(review.endswith("Review body.\n\nUser request: the diff"))
    with self.assertRaises(fw.PackError):
      p.expand_user_message("not_an_intent", "x")

  def test_intent_map_validation(self):
    with self.assertRaises(fw.PackError):
      self._pack(dict(self.entry, intent_map={"feature_plan": "nope"}))
    with self.assertRaises(fw.PackError):
      self._pack(dict(self.entry, intent_map={"bogus": None}))
    self.assertEqual(set(self._pack().intent_map), set(schema.INTENTS))

  def test_identifiers(self):
    ids = self._pack(dict(self.entry, bare_name_tokens=["fake"])).identifiers()
    for want in ("fakefw", "Fake Framework", "FakeFW", "fake-plan", "/fake-plan",
                 "fake:fix", ".agent/fakefw/", ".fake/", "run.sh"):
      self.assertIn(want, ids)
    self.assertEqual(ids, sorted(ids, key=lambda s: (-len(s), s)))
    self.assertFalse(any(i.startswith("docs/") for i in ids))

  def test_generic_skill_names_not_bare_identifiers(self):
    entry = dict(self.entry, bare_name_tokens=["fake"],
                 skills_index={"implement": "skills/plan/SKILL.md",
                               "pr": "skills/review/SKILL.md"},
                 commands={}, intent_map={})
    ids = self._pack(entry).identifiers()
    self.assertNotIn("implement", ids)
    self.assertIn("/implement", ids)
    self.assertNotIn("pr", ids)

  def test_lock_verification(self):
    p = self._pack(verify=False)
    lock = {"files": p.file_hashes()}
    self._pack(lock=lock)  # Matches.
    _write(self.root, "skills/plan/workflow.md", "tampered\n")
    with self.assertRaises(fw.PackIntegrityError):
      self._pack(lock=lock)
    self.assertIn("generated:.fake/config.toml", p.file_hashes())

  def test_pack_commands_bash(self):
    p = self._pack()
    cmd = p.pack_commands[0]
    self.assertEqual(cmd["id"], "sh")
    self.assertTrue(re.search(cmd["match"], "bash .fake/scripts/run.sh x"))
    sbx = tempfile.mkdtemp(prefix="sbx-")
    self.addCleanup(shutil.rmtree, sbx, ignore_errors=True)
    argv = cmd["resolve"](["bash", ".fake/scripts/run.sh", "x"], sbx)
    self.assertEqual(argv[1:], [".fake/scripts/run.sh", "x"])
    self.assertIsNone(cmd["resolve"](["bash", "other.sh"], sbx))
    self.assertIsNone(cmd["resolve"](["bash", ".fake/scripts/../../x.sh"], sbx))
    for path, text in p.sandbox_files().items():
      _write(sbx, path, text)
    out = subprocess.run(argv, cwd=sbx, capture_output=True, text=True,
                         check=True).stdout
    self.assertEqual(out.strip(), "ran x")

  def test_pack_commands_python_project_root(self):
    entry = dict(self.entry, pack_commands=[{
        "id": "py", "kind": "python_script", "match": "x",
        "path_globs": ["_bmad/scripts/*.py"]}])
    resolve = self._pack(entry).pack_commands[0]["resolve"]
    argv = resolve(["uv", "run", "--no-cache", "{project-root}/_bmad/scripts/r.py",
                    "--project-root", "{project-root}"], "/tmp/sbx")
    self.assertEqual(argv[1:], ["_bmad/scripts/r.py", "--project-root", "/tmp/sbx"])
    self.assertIsNone(resolve(["python3", "evil.py"], "/tmp/sbx"))

  def test_node_cli_unavailable_is_disclosed(self):
    entry = dict(self.entry, pack_commands=[{
        "id": "cli", "kind": "node_cli", "bin": "nosuchcli", "match": "^nosuchcli"}])
    cache = tempfile.mkdtemp()
    self.addCleanup(shutil.rmtree, cache, ignore_errors=True)
    p = fw.FrameworkPack(entry, self.root, None, cache_dir=cache)
    self.assertIsNone(p.pack_commands[0]["resolve"])
    self.assertIn("not installed", p.pack_commands[0]["unavailable_reason"])


class RenderContextTest(unittest.TestCase):
  """Every layout renders the same neutral facts into native locations."""

  def _render(self, layout, raw=None):
    root = tempfile.mkdtemp()
    self.addCleanup(shutil.rmtree, root, ignore_errors=True)
    for rel, text in (raw or {}).items():
      _write(root, rel, text)
    entry = {"key": "k", "display_name": "K", "paradigm": "p",
             "visibility": "public", "source": {"type": "local", "path": "x"},
             "always_on": [], "skills_index": {}, "extra_files": ["**"],
             "context_layout": layout}
    return fw.FrameworkPack(entry, root).render_context(_PC)

  def _assert_facts(self, files):
    blob = "\n".join(files.values())
    for fact in ("billing service for small shops", "Postgres",
                 "All internal services talk gRPC.", "ADR-0002", "Use gRPC",
                 "A bill sent to a shop.", "Refunds are async", "Add RPC"):
      self.assertIn(fact, blob)

  def test_all_layouts_carry_all_facts(self):
    raws = {"conductor": {"templates/workflow.md": "# Workflow\n"},
            "mattpocock": {
                "skills/engineering/setup-matt-pocock-skills/issue-tracker-local.md": "local\n",
                "skills/engineering/setup-matt-pocock-skills/domain.md": "domain\n"}}
    for layout in fw._RENDERERS:  # pylint: disable=protected-access
      with self.subTest(layout=layout):
        self._assert_facts(self._render(layout, raws.get(layout)))

  def test_native_paths(self):
    self.assertIn("armature/adr/0002-use-grpc.md", self._render("armature"))
    self.assertIn("armature/terms.md", self._render("armature"))
    self.assertIn(".specify/memory/constitution.md", self._render("speckit"))
    self.assertIn("openspec/config.yaml", self._render("openspec"))
    self.assertIn("memory-bank/systemPatterns.md", self._render("memory_bank"))
    self.assertIn("docs/adrs/ADR-0002.md", self._render("internal_sdd"))
    self.assertIn("docs/adr/0002-use-grpc.md", self._render("mattpocock"))
    conductor = self._render("conductor", {"templates/workflow.md": "# W\n"})
    self.assertEqual(conductor["conductor/workflow.md"], "# W\n")
    self.assertIn("docs/decisions/ADR-0002.md", conductor)
    generic = self._render("generic")
    for path in ("docs/product.md", "docs/decisions/ADR-0002.md",
                 "docs/glossary.md", "docs/plan/current.md"):
      self.assertIn(path, generic)

  def test_decision_text_identical_across_adr_layouts(self):
    a = self._render("armature")["armature/adr/0002-use-grpc.md"]
    g = self._render("generic")["docs/decisions/ADR-0002.md"]
    c = self._render("internal_sdd")["docs/adrs/ADR-0002.md"]
    self.assertEqual(a, g)
    self.assertEqual(a, c)

  def test_empty_and_string_plan(self):
    root = tempfile.mkdtemp()
    self.addCleanup(shutil.rmtree, root, ignore_errors=True)
    entry = {"key": "k", "display_name": "K", "paradigm": "p",
             "visibility": "public", "source": {"type": "local", "path": "x"},
             "context_layout": "memory_bank"}
    p = fw.FrameworkPack(entry, root)
    self.assertIn("memory-bank/activeContext.md", p.render_context({}))
    self.assertIn("Do X first", p.render_context(
        {"prior_plan": "Do X first"})["memory-bank/activeContext.md"])


class HelpersTest(unittest.TestCase):

  def test_frontmatter(self):
    meta, body = fw.split_frontmatter(
        '---\nname: a\ndescription: "q \\"x\\""\nmetadata:\n  k: v\nother: |\n'
        '  l1\n  l2\n---\nBody\n')
    self.assertEqual(meta["name"], "a")
    self.assertEqual(meta["description"], 'q "x"')
    self.assertEqual(meta["other"], "l1\nl2")
    self.assertNotIn("metadata", meta)
    self.assertEqual(body, "Body\n")
    self.assertEqual(fw.split_frontmatter("no fm"), ({}, "no fm"))

  def test_glob(self):
    self.assertTrue(fw.glob_match("a/b/c.md", "a/**"))
    self.assertTrue(fw.glob_match("a/c.md", "a/**/c.md"))
    self.assertTrue(fw.glob_match("x/v6-shims/y/z", "**/v6-shims/**"))
    self.assertFalse(fw.glob_match("a/b/c.md", "a/*.md"))

  def test_lock_path(self):
    self.assertTrue(fw.lock_path_for("/x/registry.json").endswith("/x/packs.lock.json"))
    self.assertTrue(fw.lock_path_for("/x/registry_internal.json").endswith(
        "/x/packs_internal.lock.json"))

  def test_speckit_transform(self):
    raw = ("---\ndescription: Do the plan.\nscripts:\n  sh: scripts/bash/setup-plan.sh --json\n"
           "  ps: scripts/powershell/setup-plan.ps1 -Json\n---\n\n"
           "Run `{SCRIPT}` then __SPECKIT_COMMAND_TASKS__. Read /memory/constitution.md "
           "and templates/plan-template.md. Agent __AGENT__. {ARGS}\n")
    out = fw._speckit_command_to_skill("plan", raw, "agy")  # pylint: disable=protected-access
    self.assertIn("name: speckit-plan", out)
    self.assertIn("`.specify/scripts/bash/setup-plan.sh --json`", out)
    self.assertIn("/speckit-tasks", out)
    self.assertIn(".specify/memory/constitution.md", out)
    self.assertIn(".specify/templates/plan-template.md", out)
    self.assertIn("Agent agy. $ARGUMENTS", out)
    self.assertNotIn("powershell", out)

  def test_find_monorepo_root(self):
    root = fw.find_monorepo_root()
    if root is not None:
      self.assertEqual(os.path.basename(root), "monorepo")


class RegistryTest(unittest.TestCase):
  """Structural checks on the shipped registries (no network)."""

  def _entries(self):
    out = []
    for path in fw.default_registry_paths():
      if os.path.isfile(path):
        out += [(path, e) for e in fw.read_registry(path)]
    return out

  def test_registry_structure(self):
    keys = set()
    for path, e in self._entries():
      with self.subTest(key=e["key"]):
        self.assertNotIn(e["key"], keys)
        keys.add(e["key"])
        if e.get("excluded"):
          self.assertTrue(e.get("exclude_reason"))
          continue
        self.assertEqual(set(e["intent_map"]), set(schema.INTENTS))
        names = set(e.get("skills_index", {})) | set(e.get("commands", {}))
        for cmd in e["intent_map"].values():
          if cmd is not None:
            self.assertIn(cmd, names)
        self.assertIn(e["context_layout"], fw._RENDERERS)  # pylint: disable=protected-access
        if e["source"]["type"] == "git":
          self.assertRegex(e["source"]["ref"], r"^[0-9a-f]{40}$")
          self.assertTrue(e["source"]["repo"].startswith("https://github.com/"))
        if path.endswith("registry.json"):
          self.assertEqual(e["visibility"], "public")
          self.assertEqual(e["source"]["type"], "git")
        else:
          self.assertEqual(e["visibility"], "internal")

  def test_public_registry_has_no_internal_identifiers(self):
    path = os.path.join(fw.FRAMEWORKS_DIR, "registry.json")
    with open(path, encoding="utf-8") as f:
      text = f.read().lower()
    # Built from fragments so this file itself passes an internal-id grep.
    for bad in ("goo" + "gle3", "corp." + "google", "jet" + "ski", "skye" + "bot",
                "cas" + "tor"):
      self.assertNotIn(bad, text)

  def test_pack_cache_env_override(self):
    old = os.environ.get("CDD_BENCH_PACK_CACHE")
    try:
      os.environ["CDD_BENCH_PACK_CACHE"] = "/tmp/custom_cdd_pack_cache"
      self.assertEqual(fw._default_cache_dir(), "/tmp/custom_cdd_pack_cache")
    finally:
      if old is None:
        os.environ.pop("CDD_BENCH_PACK_CACHE", None)
      else:
        os.environ["CDD_BENCH_PACK_CACHE"] = old


@unittest.skipUnless(
    os.path.isdir(fw.PACK_CACHE_DIR) and os.path.isfile(
        os.path.join(fw.FRAMEWORKS_DIR, "packs.lock.json")),
    "pack cache not fetched; run fetch_packs.py")
class RealPacksTest(unittest.TestCase):
  """Loads the real pinned packs and checks them against the lockfile."""

  @classmethod
  def setUpClass(cls):
    super().setUpClass()
    cls.packs = fw.load_registry([os.path.join(fw.FRAMEWORKS_DIR, "registry.json")])

  def test_all_public_load_and_expand(self):
    self.assertGreaterEqual(len(self.packs), 7)
    for p in self.packs:
      with self.subTest(key=p.key):
        sp = p.system_prompt("BASE")
        self.assertTrue(sp.startswith("BASE"))
        for path in p.sandbox_files():
          self.assertFalse(path.startswith("/") or ".." in path.split("/"))
        for intent in schema.INTENTS:
          out = p.expand_user_message(intent, "USER_TEXT_MARKER")
          self.assertIn("USER_TEXT_MARKER", out)
        ctx = p.render_context(_PC)
        self.assertTrue(ctx)
        self.assertIn(p.key, p.identifiers())

  def test_generic_words_never_bare_identifiers(self):
    union = set()
    for p in self.packs:
      union.update(i.lower() for i in p.identifiers())
    for word in ("implement", "research", "prototype", "triage", "pr", "tdd",
                 "handoff", "code-review", "john", "progress.md", "docs/adr/"):
      self.assertNotIn(word, union)

  def test_setup_files_exist_for_commands_that_require_them(self):
    for p in self.packs:
      ctx = p.render_context(_PC)
      if p.context_layout in ("armature", "conductor"):
        d = p.context_layout
        for f in ("product.md", "tech-stack.md", "workflow.md",
                  "product-guidelines.md", "tracks.md", "index.md"):
          self.assertIn(f"{d}/{f}", ctx, p.key)

  def test_sandbox_text_has_no_leftover_installer_placeholders(self):
    for p in self.packs:
      for path, text in p.sandbox_files().items():
        with self.subTest(key=p.key, path=path):
          self.assertNotIn("__SPECKIT_COMMAND_", text)
          self.assertNotIn("{SCRIPT}", text)


class LeakageAuditTest(unittest.TestCase):

  def test_tokenize_and_ngrams(self):
    toks = leakage_audit.tokenize("The agent MUST get explicit user confirmation!")
    self.assertEqual(toks, ["agent", "explicit", "user", "confirmation"])
    self.assertIn(("explicit", "user", "confirmation"), leakage_audit.ngrams(toks, 3))

  def test_audit_counts(self):
    packs = {"a": {"display_name": "A", "visibility": "public",
                   "text": "Always require explicit user confirmation first."},
             "b": {"display_name": "B", "visibility": "public",
                   "text": "Totally unrelated words here."}}
    units = [{"scenario": "S1", "kind": "criterion", "where": "c0",
              "text": "Gets explicit user confirmation before deleting."},
             {"scenario": "S1", "kind": "turn", "where": "s0t0",
              "text": "Please delete the table."}]
    res = leakage_audit.audit(packs, units)
    self.assertEqual(res["frameworks"]["a"]["units_with_3gram"], 1)
    self.assertEqual(res["frameworks"]["a"]["exclusive_3grams"], 1)
    self.assertEqual(res["frameworks"]["b"]["units_with_3gram"], 0)
    md = leakage_audit.to_markdown(res, "T")
    self.assertIn("| A (`a`)", md)

  def test_v2_units(self):
    d = tempfile.mkdtemp()
    self.addCleanup(shutil.rmtree, d, ignore_errors=True)
    path = os.path.join(d, "t.jsonl")
    with open(path, "w") as f:
      f.write(json.dumps({"id": "X", "sessions": [{"turns": ["a", "b"]}, {"turns": ["c"]}],
                          "judge_criteria": ["j"], "checks": [
                              {"id": "c1", "description": "d"}]}) + "\n")
    units = leakage_audit.scenario_units_v2([path])
    self.assertEqual([u["kind"] for u in units],
                     ["turn", "turn", "turn", "criterion", "check"])

  @unittest.skipUnless(os.path.isfile(os.path.join(BASE, "legacy_v1", "scenarios.jsonl")),
                       "legacy data absent")
  def test_reproduces_v1_finding(self):
    units = leakage_audit.scenario_units_legacy(
        os.path.join(BASE, "legacy_v1", "scenarios.jsonl"))
    packs = leakage_audit.pack_texts_legacy(
        os.path.join(BASE, "legacy_v1", "configs", "frameworks.json"))
    res = leakage_audit.audit(packs, units)["frameworks"]
    arm = res["armature_oss"]["units_with_3gram_by_kind"].get("criterion", 0)
    self.assertGreaterEqual(arm, 8)
    for key in ("github_spec_kit", "openspec", "bmad_method", "canonical_conductor"):
      self.assertLessEqual(
          res[key]["units_with_3gram_by_kind"].get("criterion", 0), 1)


class PackProvenanceAndLocalPathTest(unittest.TestCase):
  """Tests for Step 2.2 (.fetched mtime check) and Step 2.4 (local_path)."""

  def test_git_pack_mtime_check_catches_in_place_edit(self):
    cache_dir = tempfile.mkdtemp()
    self.addCleanup(shutil.rmtree, cache_dir, ignore_errors=True)
    ref = "a" * 40
    entry = {
        "key": "fake_git_pack",
        "source": {
            "type": "git",
            "repo": "https://github.com/example/repo",
            "ref": ref,
        },
    }
    root = fw.source_root(entry, cache_dir)
    os.makedirs(os.path.join(root, "rules"), exist_ok=True)
    rule_path = os.path.join(root, "rules", "rule.md")
    with open(rule_path, "w", encoding="utf-8") as f:
      f.write("# Clean rule\n")
    marker = os.path.join(root, ".fetched")
    with open(marker, "w", encoding="utf-8") as f:
      f.write("{}\n")
    os.utime(rule_path, (1000.0, 1000.0))
    os.utime(marker, (1001.0, 1001.0))
    self.assertEqual(fw.check_git_pack_mtime(entry, cache_dir), [])

    # Touch the cached file so its mtime is newer than .fetched -> fails.
    os.utime(rule_path, (1005.0, 1005.0))
    probs = fw.check_git_pack_mtime(entry, cache_dir)
    self.assertTrue(
        any(
            "cache modified after fetch: fake_git_pack/rules/rule.md" in p
            for p in probs
        ),
        probs,
    )

  def test_local_path_source_requires_env_and_records_git_head(self):
    repo_dir = tempfile.mkdtemp()
    self.addCleanup(shutil.rmtree, repo_dir, ignore_errors=True)
    os.makedirs(os.path.join(repo_dir, "rules"), exist_ok=True)
    with open(
        os.path.join(repo_dir, "rules", "p.md"), "w", encoding="utf-8"
    ) as f:
      f.write("# Dev rule\n")
    subprocess.run(
        ["git", "-C", repo_dir, "init"],
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "-C", repo_dir, "config", "user.email", "test@example.com"],
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "-C", repo_dir, "config", "user.name", "Test"],
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "-C", repo_dir, "add", "."],
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "-C", repo_dir, "commit", "-m", "init"],
        check=True,
        capture_output=True,
    )
    # Create one untracked file so dirty_files == 1.
    with open(
        os.path.join(repo_dir, "rules", "dirty.md"), "w", encoding="utf-8"
    ) as f:
      f.write("# Dirty\n")

    entry = {
        "key": "armature_oss_dev",
        "display_name": "Armature (OSS, unreleased working tree)",
        "paradigm": "Context-Driven Development",
        "visibility": "public",
        "source": {"type": "local_path", "env": "CDD_BENCH_ARMATURE_OSS_ROOT"},
        "always_on": ["rules/p.md"],
        "skills_index": {},
        "context_layout": "armature",
    }
    with mock.patch.dict(os.environ, {}, clear=False):
      os.environ.pop("CDD_BENCH_ARMATURE_OSS_ROOT", None)
      with self.assertRaises(fw.PackError):
        fw.source_root(entry)

    with mock.patch.dict(
        os.environ, {"CDD_BENCH_ARMATURE_OSS_ROOT": repo_dir}, clear=False
    ):
      root = fw.source_root(entry)
      self.assertEqual(root, os.path.abspath(repo_dir))
      pack = fw.FrameworkPack(entry, root, None, verify=False)
      self.assertIn("rules/p.md", pack.file_hashes())
      lk = fetch_packs.lock_entry(pack, {})
      self.assertTrue(lk.get("git_head"))
      self.assertEqual(len(lk["git_head"]), 40)
      self.assertEqual(lk.get("dirty_files"), 1)


if __name__ == "__main__":
  unittest.main()
