# ADR & Glossary Preflight Interceptor

> Loaded on demand by Armature skills. Not an always-on rule.

Whenever ANY Armature skill is executed against an existing project:

1.  **Lazy Detection:** Check whether `{PROJECT_ROOT}/{PROJECT_CONTEXT_DIR}/adr/` exists and
    contains at least one `.md` file.
2.  **Interception:** If no ADR files are found AND the project is brownfield
    (contains source code or existing Armature / Conductor docs):
    -   Temporarily pause the invoked skill's primary protocol.
    -   Sweep existing static documentation (`tech-stack.md`, `product.md`,
        legacy track `spec.md`, `README.md`, `docs/`) AND—when retroactive
        brownfield archaeology is active or authorized—mine VCS commit history
        (`git log -n 50` or VCS commit logs) and past conversation transcripts
        or agent memory for foundational architectural decisions,
        schema/protocol migrations, and negative constraints (tried and
        discarded alternatives).
    -   Filter extracted statements through the 3-part gate (hard to reverse ×
        surprising × real trade-off).
    -   If qualifying candidates are identified, interview the user via
        `ask_question`: *"I swept your existing docs, commit history, and past
        sessions and found foundational decisions that predate our ADR system.
        Formalize them before we proceed?"*
    -   Write accepted items to `{PROJECT_CONTEXT_DIR}/adr/NNNN-slug.md` and initialize
        `terms.md`.
    -   Upon completion (or if the user selects 'Skip'), immediately resume and
        execute the originally invoked skill command.
