# Framework packs

This directory says which real, shipped files the benchmark loads for each
framework, and how they are loaded. `bench/frameworks.py` implements the
loading, and `fetch_packs.py` fetches and pins the files.

| File                       | Purpose                                       |
| :------------------------- | :-------------------------------------------- |
| `registry.json`            | Public frameworks. Each one is pinned to an   |
:                            : exact upstream commit.                        :
| `registry_internal.json`   | Internal-only frameworks, loaded from local   |
:                            : monorepo paths. **Never port this file to the :
:                            : OSS copy.**                                   :
| `packs.lock.json`          | Generated. For each public framework: the     |
:                            : source, the ref, the sha256 of every loaded   :
:                            : file, pack-tool versions, and size stats.     :
| `packs_internal.lock.json` | Generated. The same data for internal         |
:                            : frameworks. **Never port this file to the OSS :
:                            : copy.**                                       :

Do not edit the lockfiles by hand. Run `python3 fetch_packs.py` to regenerate
them, and `python3 fetch_packs.py --verify` to check them. `load_registry()`
refuses to load a pack whose files do not match its lockfile.

## Loading model (identical for every framework)

The harness does what an Antigravity/Claude-Code-style host does after a default
install of the framework:

1.  **System prompt** = the shared `BASE_PROMPT`, then each `always_on` file in
    order (YAML frontmatter stripped, as hosts do for rules), then a skills
    index. The index has one line per skill or command: name, frontmatter
    `description` (for TOML commands, `description`), and the sandbox path. The
    agent is told it can open these files with `read_file`.
2.  **Sandbox files**: every loaded file is placed where a real install puts it.
    Project-local installs keep their real paths (`.agents/skills/...`,
    `.specify/...`, `_bmad/...`, `.clinerules/...`). Global installs, such as
    plugin and extension directories in `~`, are mirrored under
    `.agent/<key>/...`. `path_rewrites` repoints the pack's own references to
    those home-directory paths at the mirror.
3.  **Slash commands**: when a scenario's `intent` maps to a command, the first
    user message is replaced by the command body. The user's text is substituted
    for `$ARGUMENTS` (spec-kit/Claude/Antigravity convention) or `{{args}}`
    (Gemini CLI convention). If the body has neither placeholder, the text is
    appended under `User request:`. Every expansion is prefixed with
    `Base directory for this command: <sandbox dir>`, as Claude Code does, so
    relative references such as `./workflow.md` resolve.
4.  **Project context**: the scenario's neutral facts are rendered into each
    framework's native files. Facts with no native home go to the generic
    fallback (`docs/product.md`, `docs/tech-stack.md`,
    `docs/decisions/ADR-XXXX.md`, `docs/glossary.md`, `docs/plan/current.md`).
    Every layout uses byte-identical wording for a decision record and a
    glossary entry, so only the location differs.
5.  **Pack tools** (`pack_commands`): when a framework's own instructions run
    its own tooling, the sandbox executes that tooling for real, at the pinned
    version. The environment is scrubbed and a 60 s timeout applies. See below.

Any setup command a framework expects has been treated as already run. Each
renderer writes every file that framework's setup check requires. Armature and
Conductor commands halt unless `workflow.md` (copied verbatim from the pack's
own template) and `product-guidelines.md` exist. The scenarios carry no
guideline facts, so the guidelines file reads "No product guidelines recorded
yet." in both. Each renderer writes the files that setup would have produced.

## Frameworks

| Key                   | Upstream (pinned)                                                                                                                   | Always-on                       | On-demand                                | Install layout                                                                                                           | Context layout                                                                                   |
| :-------------------- | :---------------------------------------------------------------------------------------------------------------------------------- | :------------------------------ | :--------------------------------------- | :----------------------------------------------------------------------------------------------------------------------- | :----------------------------------------------------------------------------------------------- |
| `armature_oss`        | [drinkspiller/armature-cdd](https://github.com/drinkspiller/armature-cdd/tree/3639baa7499cd8a1f354e19e0783e997b0651ad1) @ `3639baa` | `rules/armature_protocol.md`,   | 8 core skills (`arm-*`), plus the        | `.agent/armature_oss/` (global plugin)                                                                                   | `armature/` (index, product, tech-stack, `adr/NNNN-slug.md`, `terms.md`, `tracks.md`,            |
:                       : (v0.34.4)                                                                                                                           : `rules/armature_antigravity.md` : reference rules                          :                                                                                                                          : `tracks/<id>/`)                                                                                  :
:                       :                                                                                                                                     :                                 : `armature_adr_preflight.md` and          :                                                                                                                          :                                                                                                  :
:                       :                                                                                                                                     :                                 : `armature_cdd_protocols.md`, plus        :                                                                                                                          :                                                                                                  :
:                       :                                                                                                                                     :                                 : `arm-setup/assets`                       :                                                                                                                          :                                                                                                  :
| `github_spec_kit`     | [github/spec-kit](https://github.com/github/spec-kit/tree/34a0d388eac671d656eb05b125ad3ed6056168ed) @ `34a0d38` (v1.3.0)            | none (Spec Kit installs no      | 9 commands as                            | `specify init --ai agy --script sh`: `.agents/skills/`, `.specify/{templates,scripts/bash,memory}`                       | `.specify/memory/constitution.md` (tech constraints and decisions),                              |
:                       :                                                                                                                                     : context file for skills agents) : `.agents/skills/speckit-<name>/SKILL.md` :                                                                                                                          : `specs/001-<slug>/{spec,plan,tasks}.md`, generic product and glossary                            :
| `openspec`            | [Fission-AI/OpenSpec](https://github.com/Fission-AI/OpenSpec/tree/27c0515724decc633818c735ee596481eec78a8b) @ `27c0515` (v1.16.0)   | none                            | 6 `core`-profile skills (propose,        | `openspec init --tools antigravity`: `.agents/skills/openspec-*`                                                         | `openspec/config.yaml` (`context:` holds product and tech stack), `openspec/changes/<slug>/`,    |
:                       :                                                                                                                                     :                                 : explore, apply, update, sync, archive)   :                                                                                                                          : generic decisions and glossary                                                                   :
| `bmad_method`         | [bmad-code-org/BMAD-METHOD](https://github.com/bmad-code-org/BMAD-METHOD/tree/bab9082c3e884e0d72c759bcd1a6d90bcc01be84) @ `bab9082` | none                            | 29 skills (core and bmm modules).        | antigravity-cli platform: `.agents/skills/bmad-*`, `_bmad/scripts`, `_bmad/config.toml` (from module.yaml defaults)      | `_bmad-output/planning-artifacts/architecture/architecture.md`,                                  |
:                       : (v6.12.4, latest stable)                                                                                                            :                                 : Deprecated v6 shims are excluded.        :                                                                                                                          : `_bmad-output/specs/<slug>/SPEC.md`, generic product and glossary                                :
| `memory_bank`         | [cline/prompts](https://github.com/cline/prompts/tree/2fc3b77a8fe39553ac424bfc7cdc9883e4a21e1f) @ `2fc3b77`                         | `.clinerules/memory-bank.md`    | none                                     | `.clinerules/memory-bank.md`, as the [Cline                                                                              | `memory-bank/{projectbrief,productContext,techContext,systemPatterns,activeContext,progress}.md` |
:                       :                                                                                                                                     :                                 :                                          : docs](https\://github.com/cline/cline/blob/d3ecc4890e8f9bcb77182b96c77fa90575e8e145/docs/best-practices/memory-bank.mdx) :                                                                                                  :
:                       :                                                                                                                                     :                                 :                                          : instruct                                                                                                                 :                                                                                                  :
| `canonical_conductor` | [gemini-cli-extensions/conductor](https://github.com/gemini-cli-extensions/conductor/tree/7a5c560a4fdf5297be58594cc37527eb12790272) | `GEMINI.md` (`contextFileName`  | 6 `/conductor:*` TOML commands, plus     | `.agent/canonical_conductor/` (global extension)                                                                         | `conductor/` (index, product, tech-stack, workflow copied from the template, `tracks.md`,        |
:                       : @ `7a5c560` (conductor-v0.4.1)                                                                                                      : in `gemini-extension.json`)     : `templates/`                             :                                                                                                                          : `tracks/<id>/`), generic decisions and glossary                                                  :
| `wayfinder`           | [mattpocock/skills](https://github.com/mattpocock/skills/tree/d1478fcb140db0b93c0c8df17bcfd311844749d0) @ `d1478fc` (v1.3.2)        | none                            | 27 skills: `skills/engineering` and      | `.agent/wayfinder/skills/` (global)                                                                                      | `docs/adr/NNNN-slug.md`, `GLOSSARY.md`, `docs/agents/{issue-tracker,domain}.md` (local-markdown  |
:                       :                                                                                                                                     :                                 : `skills/productivity`, per the README's  :                                                                                                                          : tracker, from the setup seeds), `.scratch/<slug>/`, generic product and tech                     :
:                       :                                                                                                                                     :                                 : Gemini CLI install                       :                                                                                                                          :                                                                                                  :

### How "wayfinder" was resolved

v1's `wayfinder` entry describes a planning skill: a map issue labelled
`wayfinder:map`, decision tickets of type research/prototype/grilling/task, and
"Plan, don't do". That is the `wayfinder` skill in
[mattpocock/skills](https://github.com/mattpocock/skills/blob/d1478fcb140db0b93c0c8df17bcfd311844749d0/skills/engineering/wayfinder/SKILL.md),
so a real public pack exists and the framework is **not excluded**. The skill
depends on `setup-matt-pocock-skills` and `grilling`, and the README's Gemini
CLI path installs `skills/engineering` and `skills/productivity` together, so
the benchmark loads both sets. With no `gh` available, the skill's documented
fallback applies: "If no tracker has been provided, default to the
local-markdown tracker". The renderer writes `docs/agents/issue-tracker.md` from
the setup skill's local seed.

### Exclusions and approximations (disclosed)

-   **Armature (both)**: the bug-bash skills are opt-in
    (`install.sh --experimental`, default N) and are not loaded.
-   **Spec Kit**: only the `sh` script variant is installed (`--script sh`).
    `.specify/init-options.json` and extension hooks are not written, and the
    skills treat both as optional.
-   **OpenSpec**: slash commands `/opsx-<id>` expand to the matching skill body.
    The Antigravity workflow file generated by `init` is not byte-compared with
    it. `verify`, `new`, `continue`, `ff`, `onboard`, and `bulk-archive` sit
    outside the default `core` profile and are not installed.
-   **BMAD**: `_bmad/config.toml` uses module.yaml defaults with
    `{project-root}` left symbolic, and the `[agents.*]` tables are not written.
    The `bmad-generate-project-context` shim and all `v6-shims` are excluded as
    deprecated forwarders.
-   **Memory Bank**: the cline/prompts file is used. It is the fuller official
    version of the docs snippet (it adds the Plan/Act mode workflows).
-   **Conductor**: `policies/conductor.toml` is a Gemini CLI tool-permission
    policy, not prompt text, and is not loaded.
-   **InternalSDD**: `agents/*` (subagent definitions) are not loaded because
    the harness has no subagent tool. `scripts/` need monorepo Python
    dependencies, so they are not pack tools. `plugin.json` suggests
    `/internal_sdd-lite`, which does not exist.
-   Repo-root `AGENTS.md`/`GEMINI.md` files are not auto-injected for any
    framework. Only registry `always_on` files reach the system prompt.

## Intent → command mapping

**One rule for every framework:** an intent maps to a command only if (a) the
framework's own docs present that command for the situation, and (b) the
command's prerequisites exist in the sandbox at that point. Every renderer
writes the setup files its commands check for, so a missing track, spec, or
external system is the only thing that can fail (b). Otherwise the intent is
`null` and the user's message is sent verbatim. Expansion happens on the first
turn of session 0 (scenario `intent`, or `sessions[0].intent`) and on the first
turn of any later session that sets `sessions[i].intent`.

| :-- | :-- | :-- | :-- | :-- | :-- | :-- | :-- | :-- | | `feature_plan` |
`arm-new-track` | `speckit-specify` | `opsx-propose` | `bmad-build` | null |
`conductor:newTrack` | `wayfinder` | `internal_sdd-explore` | | `hotfix` | null
| null | null | null | null | null | null | null | | `drift_audit` | `arm-drift`
| null | null | null | null | null | null | `internal_sdd-drift` | |
`ops_request` | null | null | null | null | null | null | null | null | |
`review` | null | null | null | `bmad-code-review` | null | `conductor:review` |
`code-review` | null | | `resume` | `arm-implement` | `speckit-implement` |
`opsx-apply` | `bmad-build` | null | `conductor:implement` | `implement` |
`internal_sdd-work-local` |

Rationale and sources (pinned commits above):

-   **`hotfix` and `ops_request`** are null for every framework. Users of all of
    them type a trivial fix or an ops request as a plain request, even where a
    planning command could technically take it (for example `arm-new-track`,
    "feature or bug fix track", or `bmad-build`, which says to skip obvious,
    low-risk mechanical changes). None of the frameworks ships an ops command.
-   **`feature_plan`**. Armature `arm-new-track`: "Start a new feature or bug
    fix track". Spec Kit: the README workflow starts with specify, and under the
    agy integration the invocation is hyphenated (`/speckit-specify`). OpenSpec:
    the README names `/opsx:propose` as the canonical start (`/opsx-` in
    Antigravity). BMAD: the README says "invoke `bmad-build` with what you want
    to change". Conductor: `/conductor:newTrack`. Wayfinder: the `wayfinder`
    planning skill. InternalSDD: `plugin.json` suggests `/internal_sdd-explore`
    for new features. Memory Bank has no commands; its triggers are plain
    phrases.
-   **`drift_audit`** (code vs. recorded decisions). `arm-drift` ("verify
    spec-to-code alignment") needs only the project context, which is rendered.
    `internal_sdd-drift` ("checks for drift between the documentation and the
    actual codebase") needs only ADRs/OpenSpecs, which are rendered from the
    decisions. `speckit-analyze` compares spec/plan/tasks artifacts, not code,
    and requires them to exist (its check-prerequisites script fails without a
    feature dir), so it maps to null. OpenSpec's `verify` is outside the default
    `core` profile. BMAD, Conductor, Memory Bank, and Wayfinder ship no drift
    command.
-   **`review`** (the scenarios ask to review a patch or branch before merging;
    no track or spec exists). Mapped: `bmad-code-review` and `code-review`
    (generic code review of changes), and `conductor:review`, which uses the
    user's arguments as the review scope when given ("If the arguments above are
    populated ... use them as the target scope"). Null: `arm-review`
    auto-detects an in-progress track and otherwise prompts for a track name;
    `speckit-converge` requires spec/plan/tasks; `internal_sdd-review` reviews a
    change in the remote code review system and publishes findings there, which
    the sandbox does not have.
-   **`resume`** (continue earlier work recorded in `prior_plan`, which every
    renderer writes as that framework's native in-progress plan):
    `arm-implement`, `speckit-implement`, `opsx-apply`, `bmad-build`,
    `conductor:implement`, `implement` (Wayfinder set: "Implement ... based on a
    spec or set of tickets"), `internal_sdd-work-local` (local backlog
    execution).

The mapping is a modeling choice and is listed in the report's Limitations.

## Blinding identifiers

`identifiers()` returns, per pack: the key, the display name, the registry
`identifiers` list, every skill/command as `/name`, the bare name only when it
contains one of the pack's `bare_name_tokens` (`arm-`, `speckit`, `opsx`,
`bmad`, `conductor`, `wayfinder`, ...), sandbox install dirs and skill paths,
always-on file names, pack-tool script names and CLI names, and the layout's
native context dirs. Generic words (`implement`, `research`, `pr`, `triage`,
common first names, `docs/adr/`, `progress.md`) are deliberately excluded,
because the judge's blinding would otherwise rewrite ordinary words in user and
agent text.

## Pack tools executed by the sandbox

| Framework         | Tool                                 | Resolution                     |
| :---------------- | :----------------------------------- | :----------------------------- |
| `github_spec_kit` | `.specify/scripts/bash/*.sh`         | Run through `bash` from the    |
:                   :                                      : sandbox copy                   :
| `openspec`        | `openspec ...`                       | The pinned                     |
:                   :                                      : `@fission-ai/openspec@1.16.0`, :
:                   :                                      : installed by `fetch_packs.py`  :
:                   :                                      : into the pack cache's          :
:                   :                                      : `_tools/`. Telemetry is off    :
:                   :                                      : (`OPENSPEC_TELEMETRY=0`,       :
:                   :                                      : `DO_NOT_TRACK=1`). If node/npm :
:                   :                                      : is missing, the lockfile       :
:                   :                                      : records `available\: false`    :
:                   :                                      : and the report must disclose   :
:                   :                                      : it.                            :
| `bmad_method`     | `uv run ... _bmad/scripts/*.py` and  | Run with `python3` on the      |
:                   : `.agents/skills/bmad-*/scripts/*.py` : sandbox copy, with             :
:                   :                                      : `{project-root}` replaced by   :
:                   :                                      : the sandbox dir                :

`bench/sandbox.py` refuses to run a pack script that the agent has modified.

## Size (chars/4 token estimate)

"Always-on" counts the always-on rule text as injected. "System prompt addition"
also includes the skills index. "Total pack" counts every loaded file, all of
which the agent can read on demand.

| Framework           | Always-on | Always-on | Sys-prompt | Sys-prompt | Files | Skills/commands | Total     | Total   |
:                     : chars     : tok       : addition   : addition   :       :                 : pack      : pack    :
:                     :           :           : chars      : tok        :       :                 : chars     : tok     :
| :------------------ | --------: | --------: | ---------: | ---------: | ----: | --------------: | --------: | ------: |
| armature_oss        | 86,939    | 21,734    | 89,709     | 22,427     | 15    | 8               | 361,248   | 90,312  |
| github_spec_kit     | 0         | 0         | 1,880      | 470        | 20    | 9               | 225,855   | 56,463  |
| openspec            | 0         | 0         | 2,413      | 603        | 6     | 6               | 94,748    | 23,687  |
| bmad_method         | 0         | 0         | 9,080      | 2,270      | 209   | 29              | 1,432,002 | 358,000 |
| memory_bank         | 3,535     | 883       | 3,741      | 935        | 1     | 0               | 3,871     | 967     |
| canonical_conductor | 2,172     | 543       | 3,501      | 875        | 17    | 6               | 152,530   | 38,132  |
| wayfinder           | 0         | 0         | 5,978      | 1,494      | 52    | 27              | 215,141   | 53,785  |

For comparison, v1 gave Armature a 5.8 KB prompt and competitors roughly 1 KB
paraphrases. In v2, every framework's own size is what it ships.

## Leakage audit

`python3 leakage_audit.py [--tasks ...] [--legacy] [--out-json F --out-md F]`
counts stopword-filtered 3-/4-grams shared between each pack's text and each
scenario unit (user turn, judge criterion, check description).

-   **Calibration on v1** (`--legacy`): the v1 Armature prompt shares 3-grams
    with 11/120 criteria. Competitor paraphrases share them with 0–1/120. This
    reproduces the v1 finding.
-   **v2**: no pack shares a 4-gram with any core or held-out unit. Armature
    shares one 3-gram, "turn asking user", from `asked_user` check descriptions.
    Other packs share at most two incidental 3-grams.

## Cache location

-   Third-party files are never committed. In writable checkouts the cache
    defaults to `BASE/.pack_cache/` (gitignored), falling back to
    `~/.cache/cdd_sdd_benchmark/pack_cache` when already populated or on
    read-only mounts. `CDD_BENCH_PACK_CACHE` overrides both.
-   `registry.json` and `packs.lock.json` define the pinned public pack set;
    `load_registry()` skips optional registry files that do not exist.
