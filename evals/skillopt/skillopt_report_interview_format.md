# SkillOpt Report: Interview Turn v2 (`arm-new-track` + protocol rules)

Generated: 2026-10-21T18:33:29

| Pass      | Train  | Train  | Val mean | Val LB90 | Val vetoes | Val pass |
:           : mean   : vetoes :          :          :            : rate     :
| :-------- | :----- | :----- | :------- | :------- | :--------- | :------- |
| baseline  | 0.1818 | 177    | 0.1111   | 0.1111   | 150        | 11.1%    |
| candidate | 0.8939 | 11     | 0.9136   | 0.8903   | 0          | 66.7%    |

## baseline: per-task vetoes

-   `IFT_TRAIN_01_PUSH_BATCHING_TURN1` seed 1: has_pick_recap: Pick lines must
    be formatted as Markdown bullets ('- Pick N if ...') so CommonMark renders
    each on its own line; modal_options_match_chat_options: used legacy 'Compare
    technical trade-offs...' modal option; modal_options_match_chat_options:
    modal option 1 ('(Recommended) Early messages must always arrive without
    delay (Option 1)') did not match chat Option 1 name ('Send first five
    instantly, digest the rest'); modal_options_match_chat_options: modal option
    2 ('Users should receive a single consolidated summary rather than separate
    early alerts (Option 2)') did not match chat Option 2 name ('Hold alerts
    during bursts for a full digest'); modal_options_match_chat_options: modal
    option 3 ('Every burst must be caught before a user receives their first
    push (Option 3)') did not match chat Option 3 name ('Hold all alerts in a
    short two-minute buffer'); has_context_option_in_modal: used deprecated
    'Compare technical trade-offs...' instead of 'I need more context, zoom out
    and give examples'
-   `IFT_TRAIN_01_PUSH_BATCHING_TURN1` seed 2: has_pick_recap: Pick lines must
    be formatted as Markdown bullets ('- Pick N if ...') so CommonMark renders
    each on its own line; modal_options_match_chat_options: used legacy 'Compare
    technical trade-offs...' modal option; modal_options_match_chat_options:
    modal option 1 ('(Recommended) Normal low-frequency pushes must arrive
    instantly (Option 1)') did not match chat Option 1 name ('Deliver first 5
    immediately, digest subsequent pushes'); modal_options_match_chat_options:
    modal option 2 ('Stopping notification floods matters more than real-time
    arrival (Option 2)') did not match chat Option 2 name ('Delay all pushes in
    a fixed collector window'); modal_options_match_chat_options: modal option 3
    ('One initial alert is fine, but repeated buzzes must stop immediately
    (Option 3)') did not match chat Option 3 name ('Deliver the first push
    immediately, buffer following ones'); has_context_option_in_modal: used
    deprecated 'Compare technical trade-offs...' instead of 'I need more
    context, zoom out and give examples'
-   `IFT_TRAIN_01_PUSH_BATCHING_TURN1` seed 3: has_pick_recap: Pick lines must
    be formatted as Markdown bullets ('- Pick N if ...') so CommonMark renders
    each on its own line; modal_options_match_chat_options: used legacy 'Compare
    technical trade-offs...' modal option; modal_options_match_chat_options:
    modal option 1 ('(Recommended) Real-time responsiveness for initial messages
    matters most (Option 1)') did not match chat Option 1 name ('Send first five
    live, bundle subsequent messages into a digest');
    modal_options_match_chat_options: modal option 2 ('Overflow messages must
    strictly arrive as a single scheduled wrap-up (Option 2)') did not match
    chat Option 2 name ('Send first five live, hold overflow until ten minutes
    pass'); modal_options_match_chat_options: modal option 3 ('Preventing phone
    buzzing takes precedence over immediate single-message delivery (Option 3)')
    did not match chat Option 3 name ('Buffer every push briefly to detect
    velocity upfront'); has_context_option_in_modal: used deprecated 'Compare
    technical trade-offs...' instead of 'I need more context, zoom out and give
    examples'
-   `IFT_TRAIN_02_CSV_EXPORT_MID_INTERVIEW` seed 1: has_pick_recap: Pick lines
    must be formatted as Markdown bullets ('- Pick N if ...') so CommonMark
    renders each on its own line; modal_options_match_chat_options: used legacy
    'Compare technical trade-offs...' modal option;
    modal_options_match_chat_options: modal option 1 ('(Recommended) Most admins
    inspect exports in Excel on Windows (Option 1)') did not match chat Option 1
    name ('Include UTF-8 byte order mark'); modal_options_match_chat_options:
    modal option 2 ('Exports are primarily consumed by automated command-line
    pipelines (Option 2)') did not match chat Option 2 name ('Plain UTF-8
    without prefix'); has_context_option_in_modal: used deprecated 'Compare
    technical trade-offs...' instead of 'I need more context, zoom out and give
    examples'
-   `IFT_TRAIN_02_CSV_EXPORT_MID_INTERVIEW` seed 2: has_pick_recap: Pick lines
    must be formatted as Markdown bullets ('- Pick N if ...') so CommonMark
    renders each on its own line; modal_options_match_chat_options: modal option
    1 ('(Recommended) Most admins open CSVs in desktop Excel on Windows (Option
    1)') did not match chat Option 1 name ('Include a UTF-8 BOM prefix');
    modal_options_match_chat_options: modal option 2 ('Strict RFC compliance and
    automated pipeline parsing matter most (Option 2)') did not match chat
    Option 2 name ('Standard UTF-8 without BOM');
    modal_options_match_chat_options: modal option 3 ('Admins need both formats
    for different downstream workflows (Option 3)') did not match chat Option 3
    name ('Let the user toggle Excel compatibility');
    has_context_option_in_modal: missing trailing 'I need more context, zoom out
    and give examples' modal option
-   `IFT_TRAIN_02_CSV_EXPORT_MID_INTERVIEW` seed 3: has_pick_recap: Pick lines
    must be formatted as Markdown bullets ('- Pick N if ...') so CommonMark
    renders each on its own line; modal_options_match_chat_options: used legacy
    'Compare technical trade-offs...' modal option;
    modal_options_match_chat_options: modal option 1 ('(Recommended) Admins
    primarily open exports in desktop Excel on Windows (Option 1)') did not
    match chat Option 1 name ('Include a UTF-8 byte order mark');
    modal_options_match_chat_options: modal option 2 ('Exports are primarily
    consumed by automated CLI scripts or Unix tools (Option 2)') did not match
    chat Option 2 name ('Standard UTF-8 without byte order mark');
    has_context_option_in_modal: used deprecated 'Compare technical
    trade-offs...' instead of 'I need more context, zoom out and give examples'
-   `IFT_TRAIN_05_SEARCH_SETTLED_OVERFLOW` seed 1: settled_capped_at_five: used
    nested double-bullet '- + N earlier settled' instead of '- (+N earlier
    settled)'; has_pick_recap: Pick lines must be formatted as Markdown bullets
    ('- Pick N if ...') so CommonMark renders each on its own line;
    modal_options_match_chat_options: used legacy 'Compare technical
    trade-offs...' modal option; modal_options_match_chat_options: modal option
    1 ('(Recommended) Shoppers must always get uninterrupted, complete search
    results (Option 1)') did not match chat Option 1 name ('Serve previous index
    until switchover'); modal_options_match_chat_options: modal option 2 ('Newly
    indexed changes must appear on the storefront immediately (Option 2)') did
    not match chat Option 2 name ('Serve batches as they finish');
    modal_options_match_chat_options: modal option 3 ('Search should pause
    explicitly while the new catalog builds (Option 3)') did not match chat
    Option 3 name ('Show storefront maintenance notice');
    has_context_option_in_modal: used deprecated 'Compare technical
    trade-offs...' instead of 'I need more context, zoom out and give examples'
-   `IFT_TRAIN_05_SEARCH_SETTLED_OVERFLOW` seed 2: settled_capped_at_five: used
    nested double-bullet '- + N earlier settled' instead of '- (+N earlier
    settled)'; has_pick_recap: Pick lines must be formatted as Markdown bullets
    ('- Pick N if ...') so CommonMark renders each on its own line;
    modal_options_match_chat_options: used legacy 'Compare technical
    trade-offs...' modal option; modal_options_match_chat_options: modal option
    1 ('(Recommended) Shoppers must always see uninterrupted search results
    (Option 1)') did not match chat Option 1 name ('Serve previous index until
    fully built'); modal_options_match_chat_options: modal option 2 ('Newly
    indexed items must surface immediately despite temporary catalog gaps
    (Option 2)') did not match chat Option 2 name ('Serve batches as they
    finish'); modal_options_match_chat_options: modal option 3 ('Disabling
    search during updates is preferred over serving stale items (Option 3)') did
    not match chat Option 3 name ('Show a maintenance notice during rebuilds');
    has_context_option_in_modal: used deprecated 'Compare technical
    trade-offs...' instead of 'I need more context, zoom out and give examples'
-   `IFT_TRAIN_05_SEARCH_SETTLED_OVERFLOW` seed 3: settled_capped_at_five: used
    nested double-bullet '- + N earlier settled' instead of '- (+N earlier
    settled)'; has_pick_recap: Pick lines must be formatted as Markdown bullets
    ('- Pick N if ...') so CommonMark renders each on its own line;
    modal_options_match_chat_options: used legacy 'Compare technical
    trade-offs...' modal option; modal_options_match_chat_options: modal option
    1 ('(Recommended) Shoppers must always see uninterrupted, consistent search
    results during a rebuild (Option 1)') did not match chat Option 1 name
    ('Serve from previous index until swap'); modal_options_match_chat_options:
    modal option 2 ('Shoppers must never see stale prices or out-of-stock items
    while rebuilding (Option 2)') did not match chat Option 2 name ('Show a
    brief maintenance banner'); modal_options_match_chat_options: modal option 3
    ('Disk storage is constrained and temporary inconsistency is acceptable
    (Option 3)') did not match chat Option 3 name ('Stream updates directly into
    active index'); has_context_option_in_modal: used deprecated 'Compare
    technical trade-offs...' instead of 'I need more context, zoom out and give
    examples'
-   `IFT_TRAIN_06_EMPTY_STATE_COPY_PREFERENCE` seed 1: has_settled_now_list:
    missing the Now progress group; headline_round_question_format: headline
    missing or uses 'Question R.Q of N'; no_labeled_opener: no opener paragraph
    between headline and options; has_choice_sentence_some_options: missing 'The
    choice here is …'; has_choice_sentence_some_options: missing 'Here are some
    options:'; has_numbered_options: fewer than 2 numbered options;
    has_recommendation_heading_one_sentence: missing '### Recommendation: Option
    N'; has_pick_recap: fewer than 2 'Pick N if' lines; ends_with_pick_line:
    trailing text after the last Pick line; modal_options_match_chat_options: 3
    core modal options for 0 numbered chat options
-   `IFT_TRAIN_06_EMPTY_STATE_COPY_PREFERENCE` seed 2: has_pick_recap: Pick
    lines must be formatted as Markdown bullets ('- Pick N if ...') so
    CommonMark renders each on its own line; modal_options_match_chat_options:
    modal option 1 ('(Recommended) I want the fastest, clearest prompt to take
    action (Option 1)') did not match chat Option 1 name ('Direct setup
    instruction'); modal_options_match_chat_options: modal option 2 ('Emphasize
    a warm onboarding greeting for first-time users (Option 2)') did not match
    chat Option 2 name ('Warm onboarding greeting');
    modal_options_match_chat_options: modal option 3 ('Remind new users of the
    platform's core value proposition (Option 3)') did not match chat Option 3
    name ('Value and outcome pitch')
-   `IFT_TRAIN_06_EMPTY_STATE_COPY_PREFERENCE` seed 3: has_pick_recap: Pick
    lines must be formatted as Markdown bullets ('- Pick N if ...') so
    CommonMark renders each on its own line; modal_options_match_chat_options:
    modal option 1 ('(Recommended) Direct, unambiguous instruction (Option 1)')
    did not match chat Option 1 name ('Plain instructional heading');
    modal_options_match_chat_options: modal option 2 ('Warm and welcoming
    onboarding greeting (Option 2)') did not match chat Option 2 name ('Friendly
    welcome greeting'); modal_options_match_chat_options: modal option 3
    ('Emphasize project value before action (Option 3)') did not match chat
    Option 3 name ('Outcome-focused heading')
-   `IFT_TRAIN_07_CHECKOUT_VAGUE_OPTION_CLARIFICATION` seed 1:
    no_settled_on_clarification_retee: re-printed Settled/Now/Up next progress
    list on a clarification re-tee when zero items newly settled;
    has_pick_recap: Pick lines must be formatted as Markdown bullets ('- Pick N
    if ...') so CommonMark renders each on its own line;
    modal_options_match_chat_options: used legacy 'Compare technical
    trade-offs...' modal option; modal_options_match_chat_options: modal option
    1 ('(Recommended) Resume where left off, allow free backward navigation
    (Option 1)') did not match chat Option 1 name ('Resume at entry only, allow
    free Skip and Back inside'); modal_options_match_chat_options: modal option
    3 ('Require prior steps to be completed on every URL (Option 3)') did not
    match chat Option 3 name ('Require completing prior steps on every URL');
    has_context_option_in_modal: used deprecated 'Compare technical
    trade-offs...' instead of 'I need more context, zoom out and give examples'
-   `IFT_TRAIN_07_CHECKOUT_VAGUE_OPTION_CLARIFICATION` seed 2:
    no_settled_on_clarification_retee: re-printed Settled/Now/Up next progress
    list on a clarification re-tee when zero items newly settled;
    has_pick_recap: Pick lines must be formatted as Markdown bullets ('- Pick N
    if ...') so CommonMark renders each on its own line;
    modal_options_match_chat_options: used legacy 'Compare technical
    trade-offs...' modal option; modal_options_match_chat_options: modal option
    1 ('(Recommended) Resume at first unfinished step while keeping full
    navigation freedom (Option 1)') did not match chat Option 1 name ('Resume at
    first unfinished step, allow free Back and Skip inside');
    modal_options_match_chat_options: modal option 2 ('Jump returning shoppers
    with a saved address straight to payment (Option 2)') did not match chat
    Option 2 name ('Jump straight to payment once address is saved');
    modal_options_match_chat_options: modal option 3 ('Require strict linear
    completion of each step in sequential order (Option 3)') did not match chat
    Option 3 name ('Enforce strict sequential step completion');
    has_context_option_in_modal: used deprecated 'Compare technical
    trade-offs...' instead of 'I need more context, zoom out and give examples'
-   `IFT_TRAIN_07_CHECKOUT_VAGUE_OPTION_CLARIFICATION` seed 3:
    no_settled_on_clarification_retee: re-printed Settled/Now/Up next progress
    list on a clarification re-tee when zero items newly settled;
    has_pick_recap: Pick lines must be formatted as Markdown bullets ('- Pick N
    if ...') so CommonMark renders each on its own line;
    modal_options_match_chat_options: used legacy 'Compare technical
    trade-offs...' modal option; modal_options_match_chat_options: modal option
    1 ('(Recommended) Resume where left off with free navigation between steps
    (Option 1)') did not match chat Option 1 name ('Resume at earliest
    unfinished step'); modal_options_match_chat_options: modal option 2 ('Jump
    straight to payment once address is saved (Option 2)') did not match chat
    Option 2 name ('Always jump straight to payment');
    modal_options_match_chat_options: modal option 3 ('Require completing or
    explicitly skipping each step in order (Option 3)') did not match chat
    Option 3 name ('Strict milestone progression'); has_context_option_in_modal:
    used deprecated 'Compare technical trade-offs...' instead of 'I need more
    context, zoom out and give examples'
-   `IFT_TRAIN_08_ANIMATION_NULL_PARENT_TURN1` seed 1:
    grounds_familiar_domain_nouns: headline/opener omitted familiar domain
    concept ['null']; has_pick_recap: Pick lines must be formatted as Markdown
    bullets ('- Pick N if ...') so CommonMark renders each on its own line;
    modal_options_match_chat_options: used legacy 'Compare technical
    trade-offs...' modal option; modal_options_match_chat_options: modal option
    1 ('(Recommended) Smooth scaling through zero using a tiny threshold (Option
    1)') did not match chat Option 1 name ('Clamp zero scale to an epsilon
    threshold'); modal_options_match_chat_options: modal option 3 ('Hide child
    layers completely when parent hits zero scale (Option 3)') did not match
    chat Option 3 name ('Hide child layers when parent scale hits zero');
    has_context_option_in_modal: used deprecated 'Compare technical
    trade-offs...' instead of 'I need more context, zoom out and give examples'
-   `IFT_TRAIN_08_ANIMATION_NULL_PARENT_TURN1` seed 2: has_pick_recap: Pick
    lines must be formatted as Markdown bullets ('- Pick N if ...') so
    CommonMark renders each on its own line; modal_options_match_chat_options:
    used legacy 'Compare technical trade-offs...' modal option;
    modal_options_match_chat_options: modal option 1 ('(Recommended) Child
    layers must collapse cleanly without losing original position or size
    (Option 1)') did not match chat Option 1 name ('Hold child local properties
    independent'); modal_options_match_chat_options: modal option 2 ('Matrix
    calculations must never encounter zero determinants anywhere (Option 2)')
    did not match chat Option 2 name ('Clamp parent scale to a near-zero
    fraction'); modal_options_match_chat_options: modal option 3 ('Linking
    should only be permitted when parent scale is strictly positive (Option 3)')
    did not match chat Option 3 name ('Block linking while parent scale is
    zero'); has_context_option_in_modal: used deprecated 'Compare technical
    trade-offs...' instead of 'I need more context, zoom out and give examples'
-   `IFT_TRAIN_08_ANIMATION_NULL_PARENT_TURN1` seed 3: has_pick_recap: Pick
    lines must be formatted as Markdown bullets ('- Pick N if ...') so
    CommonMark renders each on its own line; modal_options_match_chat_options:
    used legacy 'Compare technical trade-offs...' modal option;
    modal_options_match_chat_options: modal option 1 ('(Recommended) Pop-in
    animations should scale smoothly without dropping or jumping layer positions
    (Option 1)') did not match chat Option 1 name ('Clamp parent scale to a
    micro-value'); modal_options_match_chat_options: modal option 2 ('Zero-scale
    frames should strictly freeze layer transforms without computing offsets
    (Option 2)') did not match chat Option 2 name ('Freeze child world transform
    at zero scale'); modal_options_match_chat_options: modal option 3 ('Children
    should ignore parenting on exact zero-scale frames (Option 3)') did not
    match chat Option 3 name ('Defer parenting calculations until scale is
    positive'); has_context_option_in_modal: used deprecated 'Compare technical
    trade-offs...' instead of 'I need more context, zoom out and give examples'
-   `IFT_TRAIN_09_ANIMATION_NEED_MORE_CONTEXT_CLICK` seed 1:
    no_settled_on_clarification_retee: re-printed Settled/Now/Up next progress
    list on a clarification re-tee when zero items newly settled;
    has_pick_recap: Pick lines must be formatted as Markdown bullets ('- Pick N
    if ...') so CommonMark renders each on its own line;
    modal_options_match_chat_options: used legacy 'Compare technical
    trade-offs...' modal option; modal_options_match_chat_options: modal option
    1 ('(Recommended) Prevent linking and prompt animator to scrub to a visible
    frame (Option 1)') did not match chat Option 1 name ('Require scrubbing to a
    visible frame'); modal_options_match_chat_options: modal option 3
    ('Approximate zero with tiny scale to preserve current position (Option 3)')
    did not match chat Option 3 name ('Approximate zero with tiny scale');
    has_context_option_in_modal: used deprecated 'Compare technical
    trade-offs...' instead of 'I need more context, zoom out and give examples'
-   `IFT_TRAIN_09_ANIMATION_NEED_MORE_CONTEXT_CLICK` seed 2:
    no_settled_on_clarification_retee: re-printed Settled/Now/Up next progress
    list on a clarification re-tee when zero items newly settled;
    has_pick_recap: Pick lines must be formatted as Markdown bullets ('- Pick N
    if ...') so CommonMark renders each on its own line;
    modal_options_match_chat_options: used legacy 'Compare technical
    trade-offs...' modal option; modal_options_match_chat_options: modal option
    1 ('(Recommended) Stage positions must never distort or jump (Option 1)')
    did not match chat Option 1 name ('Reject parenting and show a prompt');
    modal_options_match_chat_options: modal option 2 ('Connecting layers must
    never be interrupted by a warning (Option 2)') did not match chat Option 2
    name ('Allow parenting by attaching to center');
    modal_options_match_chat_options: modal option 3 ('Maintain approximate
    position without stopping the animator (Option 3)') did not match chat
    Option 3 name ('Approximate with a micro-scale');
    has_context_option_in_modal: used deprecated 'Compare technical
    trade-offs...' instead of 'I need more context, zoom out and give examples'
-   `IFT_TRAIN_09_ANIMATION_NEED_MORE_CONTEXT_CLICK` seed 3:
    no_settled_on_clarification_retee: re-printed Settled/Now/Up next progress
    list on a clarification re-tee when zero items newly settled;
    has_pick_recap: Pick lines must be formatted as Markdown bullets ('- Pick N
    if ...') so CommonMark renders each on its own line;
    modal_options_match_chat_options: used legacy 'Compare technical
    trade-offs...' modal option; modal_options_match_chat_options: modal option
    1 ('(Recommended) Warn and refuse linking on zero-scale frames (Option 1)')
    did not match chat Option 1 name ('Warn and refuse linking');
    modal_options_match_chat_options: modal option 2 ('Always link immediately
    even if the child jumps to center (Option 2)') did not match chat Option 2
    name ('Snap child to parent coordinates'); modal_options_match_chat_options:
    modal option 3 ('Compute offset against unscaled defaults without scrubbing
    (Option 3)') did not match chat Option 3 name ('Compute offset using default
    100% scale'); has_context_option_in_modal: used deprecated 'Compare
    technical trade-offs...' instead of 'I need more context, zoom out and give
    examples'
-   `IFT_TRAIN_10_GALLERY_REMIX_PASS1_PLAIN_LANGUAGE` seed 1:
    has_settled_now_list: missing the Now progress group; has_pick_recap: Pick
    lines must be formatted as Markdown bullets ('- Pick N if ...') so
    CommonMark renders each on its own line; word_budget_200: 201 words from
    headline to last Pick line; modal_options_match_chat_options: used legacy
    'Compare technical trade-offs...' modal option;
    modal_options_match_chat_options: modal option 1 ('(Recommended) Remixes
    must never lose images when authors edit or delete starters (Option 1)') did
    not match chat Option 1 name ('Make independent copies on remix');
    modal_options_match_chat_options: modal option 2 ('Published starters must
    update safely without duplicating all files immediately (Option 2)') did not
    match chat Option 2 name ('Save each publish as a frozen version');
    modal_options_match_chat_options: modal option 3 ('Storage space is the top
    priority and you want shared files until edited (Option 3)') did not match
    chat Option 3 name ('Share original files until edited');
    has_context_option_in_modal: used deprecated 'Compare technical
    trade-offs...' instead of 'I need more context, zoom out and give examples'
-   `IFT_TRAIN_10_GALLERY_REMIX_PASS1_PLAIN_LANGUAGE` seed 2:
    has_settled_now_list: missing the Now progress group; has_pick_recap: Pick
    lines must be formatted as Markdown bullets ('- Pick N if ...') so
    CommonMark renders each on its own line; modal_options_match_chat_options:
    used legacy 'Compare technical trade-offs...' modal option;
    modal_options_match_chat_options: modal option 1 ('(Recommended) Remixes
    must never break when samples are updated or deleted (Option 1)') did not
    match chat Option 1 name ('Make private copies on remix and save updates as
    new versions'); modal_options_match_chat_options: modal option 2 ('Save disk
    space by tracking shared image links across projects (Option 2)') did not
    match chat Option 2 name ('Share image links and make private copies only
    when edited'); modal_options_match_chat_options: modal option 3 ('Keep
    storage minimal and accept that image updates might break remixes (Option
    3)') did not match chat Option 3 name ('Share image links directly without
    tracking'); has_context_option_in_modal: used deprecated 'Compare technical
    trade-offs...' instead of 'I need more context, zoom out and give examples'
-   `IFT_TRAIN_10_GALLERY_REMIX_PASS1_PLAIN_LANGUAGE` seed 3:
    has_settled_now_list: missing the Now progress group; has_pick_recap: Pick
    lines must be formatted as Markdown bullets ('- Pick N if ...') so
    CommonMark renders each on its own line; modal_options_match_chat_options:
    used legacy 'Compare technical trade-offs...' modal option;
    modal_options_match_chat_options: modal option 1 ('(Recommended) Remixed
    projects must never break if an author deletes or edits the original (Option
    1)') did not match chat Option 1 name ('Make separate file copies for each
    remix'); modal_options_match_chat_options: modal option 2 ('Saving storage
    space across identical projects is top priority (Option 2)') did not match
    chat Option 2 name ('Share files and save copies only when edited');
    modal_options_match_chat_options: modal option 3 ('Authors should freeze
    each release under a clear version number (Option 3)') did not match chat
    Option 3 name ('Lock published samples into fixed versions');
    has_context_option_in_modal: used deprecated 'Compare technical
    trade-offs...' instead of 'I need more context, zoom out and give examples'
-   `IFT_TRAIN_11_GALLERY_REMIX_NEED_MORE_CONTEXT_RETEE` seed 1:
    no_settled_on_clarification_retee: re-printed Settled/Now/Up next progress
    list on a clarification re-tee when zero items newly settled;
    has_pick_recap: Pick lines must be formatted as Markdown bullets ('- Pick N
    if ...') so CommonMark renders each on its own line;
    no_systems_jargon_in_turn: un-translated systems jargon 'in-place overwrite'
    in Pass-1 headline, opener, or numbered options;
    modal_options_match_chat_options: used legacy 'Compare technical
    trade-offs...' modal option; modal_options_match_chat_options: modal option
    1 ('(Recommended) Remixed projects and readers must never see broken files
    (Option 1)') did not match chat Option 1 name ('Separate copy per remix with
    versioned updates'); modal_options_match_chat_options: modal option 2
    ('Extra storage is a concern and brief upload glitches are acceptable
    (Option 2)') did not match chat Option 2 name ('Separate copy per remix with
    in-place overwrite'); modal_options_match_chat_options: modal option 3
    ('Disk space is strictly constrained and reference tracking is supported
    (Option 3)') did not match chat Option 3 name ('Shared files that duplicate
    only on edit'); has_context_option_in_modal: used deprecated 'Compare
    technical trade-offs...' instead of 'I need more context, zoom out and give
    examples'
-   `IFT_TRAIN_11_GALLERY_REMIX_NEED_MORE_CONTEXT_RETEE` seed 2:
    no_settled_on_clarification_retee: re-printed Settled/Now/Up next progress
    list on a clarification re-tee when zero items newly settled;
    has_pick_recap: Pick lines must be formatted as Markdown bullets ('- Pick N
    if ...') so CommonMark renders each on its own line;
    no_systems_jargon_in_turn: un-translated systems jargon 'copy-on-write' in
    Pass-1 headline, opener, or numbered options;
    modal_options_match_chat_options: used legacy 'Compare technical
    trade-offs...' modal option; modal_options_match_chat_options: modal option
    1 ('(Recommended) Remixes and gallery reads must never break on updates or
    deletes (Option 1)') did not match chat Option 1 name ('Independent copy per
    remix with versioned sample updates'); modal_options_match_chat_options:
    modal option 2 ('Independent remix copies without managing sample version
    numbers (Option 2)') did not match chat Option 2 name ('Independent copy per
    remix with in-place sample overwrites'); modal_options_match_chat_options:
    modal option 3 ('Minimize file storage despite reference tracking complexity
    (Option 3)') did not match chat Option 3 name ('Shared storage with
    copy-on-write pointers'); has_context_option_in_modal: used deprecated
    'Compare technical trade-offs...' instead of 'I need more context, zoom out
    and give examples'
-   `IFT_TRAIN_11_GALLERY_REMIX_NEED_MORE_CONTEXT_RETEE` seed 3:
    no_settled_on_clarification_retee: re-printed Settled/Now/Up next progress
    list on a clarification re-tee when zero items newly settled;
    rewrites_vague_option_names: repeated vague phrase 'Independent blob
    ownership' verbatim in rewritten options; has_pick_recap: Pick lines must be
    formatted as Markdown bullets ('- Pick N if ...') so CommonMark renders each
    on its own line; no_systems_jargon_in_turn: un-translated systems jargon
    'blob' in Pass-1 headline, opener, or numbered options;
    modal_options_match_chat_options: used legacy 'Compare technical
    trade-offs...' modal option; modal_options_match_chat_options: modal option
    1 ('(Recommended) Remixes and live viewers must never see corrupt or
    partially updated files (Option 1)') did not match chat Option 1 name
    ('Separate versioned copies'); modal_options_match_chat_options: modal
    option 2 ('Disk space is tight and brief update glitches are acceptable
    (Option 2)') did not match chat Option 2 name ('Separate unversioned
    copies'); modal_options_match_chat_options: modal option 3 ('Saving disk
    space across identical remixes is the top priority (Option 3)') did not
    match chat Option 3 name ('Shared files with copy-on-write');
    has_context_option_in_modal: used deprecated 'Compare technical
    trade-offs...' instead of 'I need more context, zoom out and give examples'
-   `IFT_VAL_01_WEBHOOK_RETRY_TURN1_SYSTEMS` seed 1: has_pick_recap: Pick lines
    must be formatted as Markdown bullets ('- Pick N if ...') so CommonMark
    renders each on its own line; modal_options_match_chat_options: used legacy
    'Compare technical trade-offs...' modal option;
    modal_options_match_chat_options: modal option 1 ('(Recommended) Missed
    order events must never be lost across crashes or extended outages (Option
    1)') did not match chat Option 1 name ('Durable background queue with
    exponential backoff'); modal_options_match_chat_options: modal option 2
    ('Customer deploy windows are brief and zero new infrastructure is allowed
    (Option 2)') did not match chat Option 2 name ('In-memory delayed retries');
    modal_options_match_chat_options: modal option 3 ('Leverage existing
    database tables without adding worker queues (Option 3)') did not match chat
    Option 3 name ('Scheduled database sweep'); has_context_option_in_modal:
    used deprecated 'Compare technical trade-offs...' instead of 'I need more
    context, zoom out and give examples'
-   `IFT_VAL_01_WEBHOOK_RETRY_TURN1_SYSTEMS` seed 2: has_pick_recap: Pick lines
    must be formatted as Markdown bullets ('- Pick N if ...') so CommonMark
    renders each on its own line; modal_options_match_chat_options: used legacy
    'Compare technical trade-offs...' modal option;
    modal_options_match_chat_options: modal option 1 ('(Recommended) Orders must
    never be lost during deploys or restarts (Option 1)') did not match chat
    Option 1 name ('Durable queue with exponential backoff');
    modal_options_match_chat_options: modal option 2 ('Outages last only seconds
    and infrastructure must stay lightweight (Option 2)') did not match chat
    Option 2 name ('In-memory retries with rapid backoff');
    modal_options_match_chat_options: modal option 3 ('Webhooks must commit
    atomically with order records in the database (Option 3)') did not match
    chat Option 3 name ('Transactional outbox table with pollers');
    has_context_option_in_modal: used deprecated 'Compare technical
    trade-offs...' instead of 'I need more context, zoom out and give examples'
-   `IFT_VAL_01_WEBHOOK_RETRY_TURN1_SYSTEMS` seed 3: has_pick_recap: Pick lines
    must be formatted as Markdown bullets ('- Pick N if ...') so CommonMark
    renders each on its own line; no_systems_jargon_in_turn: un-translated
    systems jargon 'in-flight' in Pass-1 headline, opener, or numbered options;
    modal_options_match_chat_options: used legacy 'Compare technical
    trade-offs...' modal option; modal_options_match_chat_options: modal option
    1 ('(Recommended) Order events must reliably arrive even across restarts or
    outages (Option 1)') did not match chat Option 1 name ('Durable retry
    queue'); modal_options_match_chat_options: modal option 2 ('Customer outages
    are brief and we want zero new storage infrastructure (Option 2)') did not
    match chat Option 2 name ('In-memory backoff loop');
    modal_options_match_chat_options: modal option 3 ('Prefer customer-driven
    manual replays over automatic retry polling (Option 3)') did not match chat
    Option 3 name ('Move directly to dead-letter storage');
    has_context_option_in_modal: used deprecated 'Compare technical
    trade-offs...' instead of 'I need more context, zoom out and give examples'
-   `IFT_VAL_02_UPLOAD_SCAN_DEVILS_ADVOCATE` seed 1: has_pick_recap: Pick lines
    must be formatted as Markdown bullets ('- Pick N if ...') so CommonMark
    renders each on its own line; modal_options_match_chat_options: used legacy
    'Compare technical trade-offs...' modal option;
    modal_options_match_chat_options: Recommendation must place Option 1 first
    (got Option 2) so modal and chat stay in 1:1 order;
    modal_options_match_chat_options: modal option 1 ('(Recommended) Scan full
    200 MB files using local fallback container (Option 2)') did not match chat
    Option 1 name ('Scan first 10 MB chunk plus archive headers');
    modal_options_match_chat_options: modal option 2 ('Inspect initial 10 MB and
    archive headers with vendor API (Option 1)') did not match chat Option 2
    name ('Run local container scanner for large files');
    modal_options_match_chat_options: modal option 3 ('Cap user upload size at
    10 MB across the product (Option 3)') did not match chat Option 3 name ('Cap
    product uploads at 10 MB'); has_context_option_in_modal: used deprecated
    'Compare technical trade-offs...' instead of 'I need more context, zoom out
    and give examples'
-   `IFT_VAL_02_UPLOAD_SCAN_DEVILS_ADVOCATE` seed 2: has_pick_recap: Pick lines
    must be formatted as Markdown bullets ('- Pick N if ...') so CommonMark
    renders each on its own line; modal_options_match_chat_options: used legacy
    'Compare technical trade-offs...' modal option;
    modal_options_match_chat_options: modal option 2 ('Cap user uploads at 10 MB
    to stay within vendor limits (Option 2)') did not match chat Option 2 name
    ('Cap user uploads at 10 MB'); modal_options_match_chat_options: modal
    option 3 ('Route large files to cloud hash lookup and manual review (Option
    3)') did not match chat Option 3 name ('Allow large files after cloud hash
    check and manual approval'); has_context_option_in_modal: used deprecated
    'Compare technical trade-offs...' instead of 'I need more context, zoom out
    and give examples'
-   `IFT_VAL_02_UPLOAD_SCAN_DEVILS_ADVOCATE` seed 3: has_settled_now_list:
    missing the Now progress group; has_pick_recap: Pick lines must be formatted
    as Markdown bullets ('- Pick N if ...') so CommonMark renders each on its
    own line; modal_options_match_chat_options: used legacy 'Compare technical
    trade-offs...' modal option; modal_options_match_chat_options:
    Recommendation must place Option 1 first (got Option 2) so modal and chat
    stay in 1:1 order; modal_options_match_chat_options: modal option 1
    ('(Recommended) Inspect files over 10 MB with a local scanner worker (Option
    2)') did not match chat Option 1 name ('Scan the first 10 MB through the
    vendor API'); modal_options_match_chat_options: modal option 2 ('Scan the
    first 10 MB via vendor API and accept tail risk (Option 1)') did not match
    chat Option 2 name ('Route files over 10 MB to a local scanner worker');
    modal_options_match_chat_options: modal option 3 ('Lower the user upload
    limit to 10 MB (Option 3)') did not match chat Option 3 name ('Cap upload
    size at 10 MB'); has_context_option_in_modal: used deprecated 'Compare
    technical trade-offs...' instead of 'I need more context, zoom out and give
    examples'
-   `IFT_VAL_03_CALENDAR_SYNC_DENSE_PRD` seed 1: has_pick_recap: Pick lines must
    be formatted as Markdown bullets ('- Pick N if ...') so CommonMark renders
    each on its own line; modal_options_match_chat_options: used legacy 'Compare
    technical trade-offs...' modal option; modal_options_match_chat_options:
    modal option 1 ('(Recommended) Resolve edits automatically without
    cluttering either calendar (Option 1)') did not match chat Option 1 name
    ('Last edit wins based on timestamp'); modal_options_match_chat_options:
    modal option 2 ('Google and Outlook must remain the authoritative source of
    truth (Option 2)') did not match chat Option 2 name ('External calendar
    changes always win'); modal_options_match_chat_options: modal option 3
    ('Preserve every note even if it creates duplicate entries (Option 3)') did
    not match chat Option 3 name ('Duplicate the event and flag for review');
    has_context_option_in_modal: used deprecated 'Compare technical
    trade-offs...' instead of 'I need more context, zoom out and give examples'
-   `IFT_VAL_03_CALENDAR_SYNC_DENSE_PRD` seed 2: has_pick_recap: Pick lines must
    be formatted as Markdown bullets ('- Pick N if ...') so CommonMark renders
    each on its own line; modal_options_match_chat_options: used legacy 'Compare
    technical trade-offs...' modal option; modal_options_match_chat_options:
    modal option 1 ('(Recommended) Automatic background reconciliation without
    manual intervention is preferred (Option 1)') did not match chat Option 1
    name ('Last write wins'); modal_options_match_chat_options: modal option 2
    ('Accidental overwrites must be prevented by keeping duplicate copies
    (Option 2)') did not match chat Option 2 name ('Fork conflicting events');
    modal_options_match_chat_options: modal option 3 ('Users must review and
    decide every overlapping modification directly (Option 3)') did not match
    chat Option 3 name ('Flag for manual resolution');
    has_context_option_in_modal: used deprecated 'Compare technical
    trade-offs...' instead of 'I need more context, zoom out and give examples'
-   `IFT_VAL_03_CALENDAR_SYNC_DENSE_PRD` seed 3: has_pick_recap: Pick lines must
    be formatted as Markdown bullets ('- Pick N if ...') so CommonMark renders
    each on its own line; modal_options_match_chat_options: used legacy 'Compare
    technical trade-offs...' modal option; modal_options_match_chat_options:
    modal option 1 ('(Recommended) Background sync should resolve changes
    automatically without human intervention (Option 1)') did not match chat
    Option 1 name ('Last edit timestamp wins');
    modal_options_match_chat_options: modal option 2 ('Meeting notes and
    descriptions must never be lost under any circumstances (Option 2)') did not
    match chat Option 2 name ('Fork into two events');
    modal_options_match_chat_options: modal option 3 ('The external calendar
    must strictly dictate the true state of every meeting (Option 3)') did not
    match chat Option 3 name ('External calendar always wins');
    has_context_option_in_modal: used deprecated 'Compare technical
    trade-offs...' instead of 'I need more context, zoom out and give examples'
-   `IFT_VAL_04_PLURALIZATION_QUOTE_DETOUR_RESUME` seed 1: has_pick_recap: Pick
    lines must be formatted as Markdown bullets ('- Pick N if ...') so
    CommonMark renders each on its own line; modal_options_match_chat_options:
    used legacy 'Compare technical trade-offs...' modal option;
    modal_options_match_chat_options: modal option 1 ('(Recommended) I want
    standard multi-category plurals in single translation strings (Option 1)')
    did not match chat Option 1 name ('Standard ICU plural syntax in strings');
    modal_options_match_chat_options: modal option 2 ('I want zero new parsing
    dependencies at runtime (Option 2)') did not match chat Option 2 name
    ('Suffix-based message keys per count category');
    has_context_option_in_modal: used deprecated 'Compare technical
    trade-offs...' instead of 'I need more context, zoom out and give examples'
-   `IFT_VAL_04_PLURALIZATION_QUOTE_DETOUR_RESUME` seed 2: has_pick_recap: Pick
    lines must be formatted as Markdown bullets ('- Pick N if ...') so
    CommonMark renders each on its own line; modal_options_match_chat_options:
    used legacy 'Compare technical trade-offs...' modal option;
    modal_options_match_chat_options: modal option 1 ('(Recommended) Unified
    message strings should match vendor translation files (Option 1)') did not
    match chat Option 1 name ('Standard ICU plural strings');
    modal_options_match_chat_options: modal option 2 ('Message catalogs must
    stay simple key-value objects without a parser (Option 2)') did not match
    chat Option 2 name ('Separate subkeys per plural category');
    has_context_option_in_modal: used deprecated 'Compare technical
    trade-offs...' instead of 'I need more context, zoom out and give examples'
-   `IFT_VAL_04_PLURALIZATION_QUOTE_DETOUR_RESUME` seed 3: has_pick_recap: Pick
    lines must be formatted as Markdown bullets ('- Pick N if ...') so
    CommonMark renders each on its own line; modal_options_match_chat_options:
    used legacy 'Compare technical trade-offs...' modal option;
    modal_options_match_chat_options: modal option 1 ('(Recommended) Strings
    should align with standard localization tooling (Option 1)') did not match
    chat Option 1 name ('Adopt standard ICU plural strings');
    modal_options_match_chat_options: modal option 2 ('Avoiding an ICU parser
    dependency is the top priority (Option 2)') did not match chat Option 2 name
    ('Keep flat category-keyed message dictionaries');
    has_context_option_in_modal: used deprecated 'Compare technical
    trade-offs...' instead of 'I need more context, zoom out and give examples'
-   `IFT_VAL_05_IMPORT_WIZARD_VAGUE_OPTION_WRITEIN` seed 1:
    no_settled_on_clarification_retee: re-printed Settled/Now/Up next progress
    list on a clarification re-tee when zero items newly settled;
    has_pick_recap: Pick lines must be formatted as Markdown bullets ('- Pick N
    if ...') so CommonMark renders each on its own line;
    modal_options_match_chat_options: used legacy 'Compare technical
    trade-offs...' modal option; modal_options_match_chat_options: modal option
    1 ('(Recommended) Analysts skipping transforms can reload validation without
    being redirected back (Option 1)') did not match chat Option 1 name
    ('Restore step on entry, free movement inside');
    modal_options_match_chat_options: modal option 2 ('Analysts with an uploaded
    file should always land directly on validation (Option 2)') did not match
    chat Option 2 name ('Always resume at validation');
    modal_options_match_chat_options: modal option 3 ('Every stage must be
    completed strictly in sequence before validation can load (Option 3)') did
    not match chat Option 3 name ('Strict step-by-step lock');
    has_context_option_in_modal: used deprecated 'Compare technical
    trade-offs...' instead of 'I need more context, zoom out and give examples'
-   `IFT_VAL_05_IMPORT_WIZARD_VAGUE_OPTION_WRITEIN` seed 2:
    no_settled_on_clarification_retee: re-printed Settled/Now/Up next progress
    list on a clarification re-tee when zero items newly settled;
    has_pick_recap: Pick lines must be formatted as Markdown bullets ('- Pick N
    if ...') so CommonMark renders each on its own line;
    modal_options_match_chat_options: used legacy 'Compare technical
    trade-offs...' modal option; modal_options_match_chat_options: modal option
    1 ('(Recommended) Resume where left off and allow free navigation once
    uploaded (Option 1)') did not match chat Option 1 name ('Resume on entry URL
    only, allow free Skip and Back inside'); modal_options_match_chat_options:
    modal option 2 ('Jump straight to validation review once a file exists
    (Option 2)') did not match chat Option 2 name ('Jump straight to validation
    once uploaded'); modal_options_match_chat_options: modal option 3 ('Require
    steps in strict sequence before opening validation (Option 3)') did not
    match chat Option 3 name ('Require steps in order');
    has_context_option_in_modal: used deprecated 'Compare technical
    trade-offs...' instead of 'I need more context, zoom out and give examples'
-   `IFT_VAL_05_IMPORT_WIZARD_VAGUE_OPTION_WRITEIN` seed 3:
    no_settled_on_clarification_retee: re-printed Settled/Now/Up next progress
    list on a clarification re-tee when zero items newly settled;
    has_pick_recap: Pick lines must be formatted as Markdown bullets ('- Pick N
    if ...') so CommonMark renders each on its own line;
    modal_options_match_chat_options: used legacy 'Compare technical
    trade-offs...' modal option; modal_options_match_chat_options: modal option
    1 ('(Recommended) Users who skip optional transforms can move freely between
    stages (Option 1)') did not match chat Option 1 name ('Resume at entry only,
    allow free step navigation'); modal_options_match_chat_options: modal option
    2 ('Returning users land directly on validation whenever a file is uploaded
    (Option 2)') did not match chat Option 2 name ('Jump straight to validation
    if file is present'); modal_options_match_chat_options: modal option 3
    ('Every stage must be strictly visited in sequential order (Option 3)') did
    not match chat Option 3 name ('Require sequential step visits on every
    route'); has_context_option_in_modal: used deprecated 'Compare technical
    trade-offs...' instead of 'I need more context, zoom out and give examples'
-   `IFT_VAL_06_WHITEBOARD_FRAME_GROUPING_TURN1` seed 1:
    grounds_familiar_domain_nouns: headline/opener omitted familiar domain
    concept ['sticky note', 'sticky notes']; has_pick_recap: Pick lines must be
    formatted as Markdown bullets ('- Pick N if ...') so CommonMark renders each
    on its own line; modal_options_match_chat_options: modal option 1
    ('(Recommended) Designers need to see where notes land inside the group
    (Option 1)') did not match chat Option 1 name ('Spring open on hover');
    modal_options_match_chat_options: modal option 2 ('Collapsed frames must
    stay strictly locked and compact during sorting (Option 2)') did not match
    chat Option 2 name ('Reject drop with bounce');
    modal_options_match_chat_options: modal option 3 ('Speed matters more than
    seeing the note inside the frame right away (Option 3)') did not match chat
    Option 3 name ('Accept silently as grouped'); has_context_option_in_modal:
    missing trailing 'I need more context, zoom out and give examples' modal
    option
-   `IFT_VAL_06_WHITEBOARD_FRAME_GROUPING_TURN1` seed 2: has_pick_recap: Pick
    lines must be formatted as Markdown bullets ('- Pick N if ...') so
    CommonMark renders each on its own line; modal_options_match_chat_options:
    modal option 1 ('(Recommended) Expand on hover so participants see the
    interior before dropping (Option 1)') did not match chat Option 1 name
    ('Expand on hover during drag'); modal_options_match_chat_options: modal
    option 2 ('Keep frame closed and hide note inside until opened (Option 2)')
    did not match chat Option 2 name ('Accept drop into collapsed bar');
    modal_options_match_chat_options: modal option 3 ('Reject drop and require
    opening the frame first (Option 3)') did not match chat Option 3 name
    ('Reject drop onto header'); has_context_option_in_modal: missing trailing
    'I need more context, zoom out and give examples' modal option
-   `IFT_VAL_06_WHITEBOARD_FRAME_GROUPING_TURN1` seed 3:
    grounds_familiar_domain_nouns: headline/opener omitted familiar domain
    concept ['sticky note', 'sticky notes']; has_pick_recap: Pick lines must be
    formatted as Markdown bullets ('- Pick N if ...') so CommonMark renders each
    on its own line; modal_options_match_chat_options: modal option 1
    ('(Recommended) Designers need to see where notes land inside the group
    (Option 1)') did not match chat Option 1 name ('Expand on hover during
    drag'); modal_options_match_chat_options: modal option 2 ('Board layouts
    must never shift while dragging items (Option 2)') did not match chat Option
    2 name ('Group inside without expanding'); modal_options_match_chat_options:
    modal option 3 ('Frames should only accept content when explicitly opened
    (Option 3)') did not match chat Option 3 name ('Reject drop onto collapsed
    frames'); has_context_option_in_modal: missing trailing 'I need more
    context, zoom out and give examples' modal option
-   `IFT_VAL_07_WHITEBOARD_NEED_MORE_CONTEXT_CLICK` seed 1:
    no_settled_on_clarification_retee: re-printed Settled/Now/Up next progress
    list on a clarification re-tee when zero items newly settled;
    has_pick_recap: Pick lines must be formatted as Markdown bullets ('- Pick N
    if ...') so CommonMark renders each on its own line;
    modal_options_match_chat_options: modal option 1 ('(Recommended) Pop the
    frame open immediately so the note stays visible (Option 1)') did not match
    chat Option 1 name ('Pop the frame open immediately on drop');
    modal_options_match_chat_options: modal option 3 ('Block drops until the
    user manually expands the frame (Option 3)') did not match chat Option 3
    name ('Block drops until the frame is opened manually');
    has_context_option_in_modal: missing trailing 'I need more context, zoom out
    and give examples' modal option
-   `IFT_VAL_07_WHITEBOARD_NEED_MORE_CONTEXT_CLICK` seed 2:
    no_settled_on_clarification_retee: re-printed Settled/Now/Up next progress
    list on a clarification re-tee when zero items newly settled;
    has_pick_recap: Pick lines must be formatted as Markdown bullets ('- Pick N
    if ...') so CommonMark renders each on its own line;
    modal_options_match_chat_options: used legacy 'Compare technical
    trade-offs...' modal option; modal_options_match_chat_options: modal option
    1 ('(Recommended) Show immediate visual proof by springing open the frame
    (Option 1)') did not match chat Option 1 name ('Spring open the frame');
    modal_options_match_chat_options: modal option 2 ('Keep the board compact by
    tucking notes inside while closed (Option 2)') did not match chat Option 2
    name ('Tuck the note inside while closed');
    modal_options_match_chat_options: modal option 3 ('Prevent accidental
    grouping by rejecting drops until opened (Option 3)') did not match chat
    Option 3 name ('Prevent dropping onto closed frames');
    has_context_option_in_modal: used deprecated 'Compare technical
    trade-offs...' instead of 'I need more context, zoom out and give examples'
-   `IFT_VAL_07_WHITEBOARD_NEED_MORE_CONTEXT_CLICK` seed 3:
    no_settled_on_clarification_retee: re-printed Settled/Now/Up next progress
    list on a clarification re-tee when zero items newly settled;
    has_pick_recap: Pick lines must be formatted as Markdown bullets ('- Pick N
    if ...') so CommonMark renders each on its own line;
    modal_options_match_chat_options: used legacy 'Compare technical
    trade-offs...' modal option; modal_options_match_chat_options: modal option
    1 ('(Recommended) Pop the frame open so notes are visibly placed inside
    (Option 1)') did not match chat Option 1 name ('Pop open on drop');
    modal_options_match_chat_options: modal option 2 ('Tuck notes inside quietly
    without changing frame size (Option 2)') did not match chat Option 2 name
    ('Tuck inside while closed'); modal_options_match_chat_options: modal option
    3 ('Block drops until the designer opens the frame manually (Option 3)') did
    not match chat Option 3 name ('Prevent dropping while closed');
    has_context_option_in_modal: used deprecated 'Compare technical
    trade-offs...' instead of 'I need more context, zoom out and give examples'
-   `IFT_VAL_08_PODCAST_SOUNDBOARD_PASS1_PLAIN_LANGUAGE` seed 1:
    has_settled_now_list: missing the Now progress group; has_pick_recap: Pick
    lines must be formatted as Markdown bullets ('- Pick N if ...') so
    CommonMark renders each on its own line; modal_options_match_chat_options:
    used legacy 'Compare technical trade-offs...' modal option;
    modal_options_match_chat_options: modal option 1 ('(Recommended) Shows must
    be completely isolated from edits and deletions (Option 1)') did not match
    chat Option 1 name ('Make a standalone copy for each show');
    modal_options_match_chat_options: modal option 2 ('Saving storage matters
    more than tracking file references (Option 2)') did not match chat Option 2
    name ('Share one file until someone edits it');
    modal_options_match_chat_options: modal option 3 ('Keeping storage usage to
    an absolute minimum is top priority (Option 3)') did not match chat Option 3
    name ('Overwrite the file and warn active hosts');
    has_context_option_in_modal: used deprecated 'Compare technical
    trade-offs...' instead of 'I need more context, zoom out and give examples'
-   `IFT_VAL_08_PODCAST_SOUNDBOARD_PASS1_PLAIN_LANGUAGE` seed 2:
    has_settled_now_list: missing the Now progress group; has_pick_recap: Pick
    lines must be formatted as Markdown bullets ('- Pick N if ...') so
    CommonMark renders each on its own line; modal_options_match_chat_options:
    used legacy 'Compare technical trade-offs...' modal option;
    modal_options_match_chat_options: modal option 1 ('(Recommended) Live audio
    during a recording must never glitch or disappear (Option 1)') did not match
    chat Option 1 name ('Clone audio files per show');
    modal_options_match_chat_options: modal option 2 ('Saving workspace storage
    is your top priority (Option 2)') did not match chat Option 2 name ('Keep
    one shared file until edited'); modal_options_match_chat_options: modal
    option 3 ('Shows must always receive clip updates immediately without
    duplicate files (Option 3)') did not match chat Option 3 name ('Always share
    original file with version tags'); has_context_option_in_modal: used
    deprecated 'Compare technical trade-offs...' instead of 'I need more
    context, zoom out and give examples'
-   `IFT_VAL_08_PODCAST_SOUNDBOARD_PASS1_PLAIN_LANGUAGE` seed 3:
    has_settled_now_list: missing the Now progress group; has_pick_recap: Pick
    lines must be formatted as Markdown bullets ('- Pick N if ...') so
    CommonMark renders each on its own line; modal_options_match_chat_options:
    used legacy 'Compare technical trade-offs...' modal option;
    modal_options_match_chat_options: modal option 1 ('(Recommended) Live show
    stability matters more than disk usage (Option 1)') did not match chat
    Option 1 name ('Make a separate copy for each show');
    modal_options_match_chat_options: modal option 2 ('Workspace storage limits
    are tight and we need deduplication (Option 2)') did not match chat Option 2
    name ('Share files and save updates as new versions');
    modal_options_match_chat_options: modal option 3 ('Storage space is critical
    and co-hosts never record at the same time (Option 3)') did not match chat
    Option 3 name ('Share one file and overwrite in place');
    has_context_option_in_modal: used deprecated 'Compare technical
    trade-offs...' instead of 'I need more context, zoom out and give examples'

## candidate: per-task vetoes

-   `IFT_TRAIN_05_SEARCH_SETTLED_OVERFLOW` seed 2: has_settled_now_list: missing
    the Now progress group; settled_capped_at_five: 0 Settled bullets without a
    fold line; headline_round_question_format: headline missing or uses
    'Question R.Q of N'; no_labeled_opener: no opener paragraph between headline
    and options; has_numbered_options: fewer than 2 numbered options;
    has_recommendation_heading_one_sentence: missing '### Recommendation: Option
    N'; has_pick_recap: fewer than 2 'Pick N if' lines; ends_with_pick_line:
    trailing text after the last Pick line; modal_options_match_chat_options: 3
    core modal options for 0 numbered chat options
-   `IFT_TRAIN_07_CHECKOUT_VAGUE_OPTION_CLARIFICATION` seed 2:
    modal_options_match_chat_options: 0 core modal options for 3 numbered chat
    options; has_context_option_in_modal: missing trailing 'I need more context,
    zoom out and give examples' modal option
