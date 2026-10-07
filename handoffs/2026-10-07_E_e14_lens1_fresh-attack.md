**Verdict: FAIL. 4 blockers, all sentences. The behaviour holds at `a1840fc`. I measured each of these myself: the cover row (T1 19 -> 3 entries, T8 7 -> 2, T2 14 -> 2), the margin lines (T1 21 -> 19, 0 repeats), the global flags (137 parses, 0 refused; 0 socket attempts with `--offline` last on all 7 commands), the map prompt (25 answers; only `a`/`accept` accept), the fixtures register (46 rows, 35 matched on both sides) and CI (run 37631774505 on `a1840fc`, 7 jobs, all success). The blockers: B1, a test name claims more than the test inspects. Its counter-example, a T1.docx cover that drops 2 of the 3 documents, passes the full suite at 2401 passed. B2, a code comment and a commit message say the old re-prompt told the buyer nothing about how to accept; it said `answer a or q` under a `[a]ccept` prompt. B3, a stale docstring reason about the DOCX. B4, the note's golden line count.**

# E14 lens 1 (cold fresh-attack) on engine a1840fc - Wednesday 7 October 2026

Cold lens on `e14-lw01` at `a1840fc` (5 commits on `3ee5601`). Inputs: the diff `3ee5601..a1840fc`, the builder's note `scratchpad/notes/E14_build.md`, `handoffs-orchestrator/2026-10-07_LW01_log.md` and `2026-10-07_user_review_notes.md`.

Method. I used three detached worktrees under `scratchpad/lens-E14-r1-fresh-attack/`: `tip` (`a1840fc`), `base` (`3ee5601`) and `mid` (`834634c`). `PYTHONPATH` was set to each tree's `src`, and I checked it each time with `python -c "import proofpack;print(proofpack.__file__)"`. It printed `...\lens-E14-r1-fresh-attack\<tree>\src\proofpack\__init__.py`. Every probe was my own script, not the repository's test helpers. The probes were:
- `probe_flags.py`: my own argparse walk.
- `probe_pack.py`: licensed CLI runs with the socket patched to record and refuse.
- `analyse.py` / `analyse_docx.py`: count the cover entries and margin lines from `design/guidance_map_v1.csv`'s columns (document, version_date, status, section, estar_section). They do not use `label_for`.
- `probe_maps.py`: planted guidance maps.
- `probe_prompt.py`.
- `mutate.py`.

Each mutant was reverted with `git checkout`, and `git status --short` in `tip` was empty after every run. I made no commits. Platform: Windows 11 Home 10.0.26200, Python 3.14.6, Git Bash.

## Blockers

### B1. False test name, and a surviving mutant in a blocker class: `test_docx_cover_row_names_the_distinct_documents` does not check that the T1 DOCX cover names the distinct documents

The test (`tests/test_e14_cover_row.py`) takes the DOCX cover cell of T1 and T8 and asserts two things only: `INTERNAL_PREFIX not in cell` and `cell.count(AIDSF_TITLE) == 1`. A cover that names only the AI-DSF draft passes it.

Counter-example, constructed and run. In `scripts/make_docx_templates.py` `build_t1()` I changed `{% for ref in cover_guidance %}` to `{% for ref in cover_guidance[:1] %}` and regenerated `src/proofpack/templates/T1.docx` with the script. The T1 DOCX cover then drops the FDA 2007 statistical guidance and the PCCP guidance, which is a missing document on the buyer's cover. Full suite: **`2401 passed, 5 skipped in 334.82s`**, the same counts as the unmutated tree. The same truncation in both DOCX templates was caught, but only for T8, by `test_ap4_roundtrip.py::test_every_t8_criteria_cell_and_every_t7_table_cell_is_in_the_docx_as_the_html_shows_it`. Nothing compares the T1 DOCX cover with T1's guidance table.

This test is also skipped in CI. Log of the `pytest + ruff` job of my gate run 37631774505: `SKIPPED [1] tests/test_e14_cover_row.py:90: could not import 'docxtpl'` and `64 passed, 2 skipped, 2340 deselected` under `pytest -m day14`. The `docx-extra` job runs `-m ap4` only.

The shipped T1.docx is right today. My licensed run printed 3 entries: the AI-DSF title once, with "draft guidance (January 2025), not for implementation", then 2007, then PCCP. But the name asserts a check that does not exist, and a missing document on the cover is a blocker class.

Repair: assert the DOCX cover entries equal the HTML cover's labels in order, for T1 and T8. Then either give the test the `ap4` marker (so the docx-extra job runs it) or make it refuse the skip under `PROOFPACK_REQUIRE_DOCX=1`. Or rename the test to what it inspects.

Repro: in a tree at `a1840fc`, make the edit above, run `python scripts/make_docx_templates.py`, then run `python -m pytest -q -p no:cacheprovider`.

### B2. False sentence (code comment and commit message): "re-prompted without being told how to accept" / "was told nothing about how to accept"

- `src/proofpack/cli.py`, comment above `ALL_HIGH_REPROMPT`: "a buyer who typed ``y`` in the LW-01 walk-through was re-prompted without being told how to accept."
- Commit `834634c`: "in the walk-through a buyer typing 'y' was told nothing about how to accept."

Counter-example run at `3ee5601` (`probe_prompt.py`, all-high mapping of `row_id,y_true,score`, answers `y` then `q`): the buyer sees `every role is high (3 columns): [a]ccept / [q]uit? `, then `  answer a or q`, then the same `[a]ccept` prompt again. The prompt line is unchanged by E14. `test_e14_map_prompt.py` itself asserts `set(prompts) == {"every role is high (N columns): [a]ccept / [q]uit? "}`. So the buyer was told `a` twice. User review note 17 says only "`y` re-prompts. Say 'type a to accept' in the prompt's first line or accept y."

Repair: "at 3ee5601 it read `answer a or q`, which does not say that `a` accepts". The commit message is on an unpushed branch; reword it, or record the correction in the handoff.

Repro: `PYTHONPATH=<3ee5601>/src python -c "from proofpack import cli; ..."` feeding `y`,`q` to `_confirm_interactive` (`probe_prompt.py`). Output: `'y' HALT H07 ['  answer a or q'] proposed`.

### B3. Stale sentence (docstring): `anchors.distinct_notes`, "(the DOCX template prints the id on each line and reads the same context)"

This parenthetical was written at `8681684`, when the DOCX template printed one row per id. At `a1840fc` the T1 DOCX rows go through `distinct_notes` too, and a merged row prints several ids on one line. Counter-example, from the rendered T1.docx of my licensed run (`analyse_docx.py`): section 7's row is `... eSTAR: to confirm  [FDA_AIDSF_PERF_VALIDATION, FDA_AIDSF_LABELING_METRICS]`. `FDA_AIDSF_LABELING_METRICS` has no line of its own. 19 DOCX margin rows carry 21 ids.

Repair: "the DOCX template reads the same context and prints the merged ids in one bracket".

Repro: `python analyse_docx.py design/guidance_map_v1.csv <pack>/T1.docx`. Output: `rows 19 ... ids 21 distinct 17`.

### B4. False figure (the builder's note, which feeds the handoff): "Goldens (3ee5601 -> a1840fc): 3 files, 6 lines out, 3 in. Nothing else changed."

`git diff --numstat 3ee5601 a1840fc -- tests/fixtures/golden` gives:

```
3	5	tests/fixtures/golden/T1.html
2	3	tests/fixtures/golden/T2.html
1	1	tests/fixtures/golden/T8.html
```

That is 9 lines out and 6 in. "6 out, 3 in" counts the margin lines only and leaves out the 3 cover lines, which also changed. The per-file bullets beneath it are right. I checked the hunks `-147 +147` and `-283,4 +283,2` (T1), `-152 +152` and `-380,2 +380` (T2), `-146 +146` (T8), and the link counts 19 -> 3, 14 -> 2, 7 -> 2. The handoff should print 9 out, 6 in. Lens 1 (regression) found the same figure and graded it non-blocking (its N1). Under this lens's rule a false figure is a blocker. The repair is one line of the handoff.

Repro: `git -C C:/Users/joshs/GPS/ProofPack/proofpack diff --numstat 3ee5601 a1840fc -- tests/fixtures/golden`.

## Non-blocking (record and carry)

- **N1. A mutant survives behind the `guidance_map` hook.** In `render/html.py` `t8_context`, `anchors.cover_documents(refs, guidance_map)` -> `anchors.cover_documents(refs)` survives: 187 passed over the 10 files of `mutate.py` (the 4 E14 test files, `test_render_t1.py`, `test_e10_t2.py`, `test_render_t8.py`, `test_ap4_roundtrip.py`, `test_mapping_repair2.py`, `test_mapping_repair3.py`). It differs only when a caller passes a map other than the shipped one. The CLI never does, so a buyer cannot reach it. A planted-map render of T8 would kill it.
- **N2. Two mutants are equivalent on the shipped map.** `is_internal` keyed on `document.startswith("ProofPack internal")` instead of `status == "internal"`: survives (187 passed). Both internal rows carry both, and planted map D (`PP_SCOPE` renamed, status still `internal`) shows the shipped rule is status-based. Adding `draft` to the `distinct_notes` key: survives, because the label already encodes the draft status.
- **N3. The walk test's docstring is literally true but needs a follow-up.** `test_e14_global_flags.py` says "a parser added later is covered without editing this file". I added `lic_sub.add_parser("lensleaf")` without `common`: 7 failed, the 6 `lensleaf` cases plus the walk test. With `parents=[common]`: `1 failed, 56 passed`, the walk test, which pins the 8 leaves. So coverage needs no edit, but a green suite does. Lens 1 (regression) reported the same as its N2.
- **N4. `workflows/ci_gate.sh` reported a failure for an infrastructure reason, not for E14.** My gate on `a1840fc` printed `failed to get runs: HTTP 403: API rate limit exceeded` 30 times. `gh run list` calls `/actions/workflows`. The gate then printed `gate: no workflow run started for ci/a1840fc-1791381046-16825 in 300 s`, deleted the branch and exited 3. The run had started: `gh api repos/JoshSandhu/proofpack/actions/runs?head_sha=a1840fc...` (a different endpoint, which answered) showed run 37631774505 `completed success`, with 7 jobs each `success`. The jobs are wheel artefact, pytest + ruff, Docker image smoke, pip-audit, unshare -rn run, ap4 with [docx], and import without scipy. `gh api rate_limit` showed core 5000/5000, so this was a secondary limit. The gate's message "no workflow run started" was false in this case.
- **N5. The footer still lists both `ProofPack internal` entries.** I counted 10 of 10 T1 page footers in my licensed run. The builder carried this.

## What I could not break (what I tried, with figures)

- **Suite and lint at `a1840fc`, Git Bash:** `2401 passed, 5 skipped in 317.13s`. The 5th skip is `test_e8_repair4.py:405`: there is no sibling `workflows/data` beside a scratch worktree, as the note explains. That is 2406 collected, against the note's 2402 + 4. `ruff check .`: All checks passed. `ruff format --check .`: 355 files already formatted.
- **Markers, tip vs base:** `day12` 199 passed, 3 skipped vs the same; `day13` 133 vs 133; `ap4` 198 vs 198; `fixture` 178 vs 178; `day14` 66 passed (tip only). Deselected counts show 2406 tests at the tip vs 2340 at the base, a difference of 66, the day14 tests. No test was lost.
- **The new tests against the old engine:** `PYTHONPATH=<3ee5601>/src` running the tip's 4 E14 files: `32 failed, 34 passed`, split 4 + 5 + 20 + 3 across cover, margin, flags and prompt, as the note says. `test_cover_row_lists_each_distinct_guidance_document_once` fails at the base with `AssertionError: ('T1 (render)', 19, 3)`. At `834634c`, `test_docx_t1_prints_each_repeated_line_once_naming_every_id` fails (`1 failed`) and `test_ap4_roundtrip.py` gives `1 failed, 19 passed` (`test_draft_anchor_labels_survive_in_the_html_count[T1]`). Run 37627915858 has head `834634c` and conclusion `failure`. Run 37629330981 on `a1840fc`: `success`.
- **Cover (attack 1), licensed CLI runs.** These were licensed runs of the site's `public/demo/synthetic_cohort.csv` (5,000 rows) with its criteria, under an empty home with an ephemeral-signed licence, with all three flags last. `analyse.py` read the guidance table of each page and computed my own expectation: one entry per distinct (document, version_date, status) among non-internal ids, in table order.

  | page | table rows | distinct documents | cover entries | cover ids = my expectation | broken `#` links | margin lines (repeats) |
  |---|---|---|---|---|---|---|
  | T1 (run) | 19 | 3 | 3 | MATCH | 0 of 22 | 19 (0) |
  | T8 (run) | 7 | 2 | 2 | MATCH | 0 of 8 | 6 (0) |
  | T2 (compare F5) | 14 | 2 | 2 | MATCH | 0 of 12 | 10 (0) |
  | T8 (compare F5) | 10 | 2 | 2 | MATCH | 0 of 8 | 6 (0) |

  The same files at `3ee5601` gave T1 19 cover entries (12 AI-DSF ids plus 2 internal) and 21 lines (2 repeats), T1 324,900 B against 320,859 B at the tip; T8 7; T2 14 (1 internal) and 11 lines (1 repeat); compare-T8 10. The multiset of ids cited per page (link plus `data-also`) is identical between base and tip: T1 21 ids, 17 distinct. Every AI-DSF cover entry carries "draft guidance (January 2025), not for implementation". No element id is duplicated.
- **Cover with planted maps (several documents and versions), T1/T8/T2 via `render_*(doc, guidance_map=rows)`.** Each case printed MATCH and 0 broken links:
  - A: three AI-DSF rows dated 2025-06-01. Expected 4/3/3 entries, got 4/3/3; the June entry reads "draft guidance (June 2025), not for implementation".
  - B: `FDA_STAT2007_BY_SITE` status ` Internal `. Dropped from the cover; its table row stays.
  - C: 2007 rows with sections 5.1 and 7. T1 margin lines 20, not merged.
  - D: `PP_SCOPE` renamed, still `internal`. Still off the cover.
  - E: one AI-DSF row `final` under the same title. Separate draft and final entries.
  - F: different eSTAR text on one merged row. 20 lines, not merged.
- **DOCX (attack 2).** Licensed-run T1.docx: cover 3 entries, 0 internal; margin rows 19, 0 repeated visible rows, 21 ids. All 14 draft rows keep the `PP Margin Note Draft` style and the qualifier; the 5 others use `PP Margin Note`. T8.docx and compare-T8.docx: 2 entries. T7.docx and T7.html: 6 lines, 0 repeats; T12.html: 3, 0. Regenerating the templates with `scripts/make_docx_templates.py` gives T1, T7 and T8.docx byte-identical to the committed files.
- **Flags (attack 3).** My walk found 8 leaves. Each of the 3 flags went into every slot: before, between and after each subcommand word, and after the last positional or required option. I also tried all 6 orders of the 3 flags after the last word, and the bare command. That is 137 parses, 0 refused, every flag `True` and every default `False`. At `3ee5601` the same walk gives 33 refusals, all `licence`. `licence verify nonexistent.lic --offline`: base exit 2 `unrecognized arguments: --offline`, tip exit 4 `status: refused (no_file)`. For the socket test, `socket.socket.connect`, `connect_ex`, `socket.create_connection` and `socket.getaddrinfo` were patched to record and raise, and both criteria copies were set to `egress.telemetry: true`. Positive control without the flags: 2 attempts (`create_connection(('proofpack.globalphoenix.co.uk', 443))` from `run` and `compare`). With `--offline --quiet --json-log` after the words, on `licence install|verify|show`, `doctor`, `run` (T1,T7,T8, json/html/docx), `compare` (T2,T7,T8) and `fixtures`: all exited 0 with 0 attempts. CI run 37631774505's unshare job: success.
- **Map prompt (attack 4).** Fed to an all-high mapping, then `q`: `y Y yes n no e x`, empty, space, tab, `aa ok accept! a.`, Cyrillic `а`, full-width `ａ`, `q! "quit now" 1 true`. Every one re-prompted with `  type a and press Enter to accept, or q to quit` and halted H07 with `decided_by` still `proposed`. Only `A `, ` Accept ` and `a` accepted; `Q` and `abort` halted without a re-prompt. At the base the same answers behave identically, with `  answer a or q`.
- **Fixtures (attack 5).** `fixtures --offline` at base and tip: 46 rows each, 35 matched, 7 suite_only, 4 not_built, the same ids. No row matched at the base fails to match at the tip. The only differing field is F13's `reason`, which embeds this checkout's HEAD sha. Goldens: only the T1, T2 and T8 HTML lines of items 1 and 2 changed. No T7 or T12 golden changed.
- **Mutants: 27 run by `mutate.py`, 24 killed, 3 survived** (N1, N2). The killed ones:
  - the cover keeping internal rows, not deduping, deduping by id, or taking the last item per label;
  - the notes key dropping estar, section or label;
  - merged ids dropped, the input mutated in place, the last of a group printed;
  - `data-also` dropped, the draft class dropped;
  - the T1 or T2 notes not deduped;
  - the T8 or T2 cover reading `guidance_refs`, `t2.py` cover = refs;
  - the DOCX `distinct_notes` filter replaced by the identity;
  - `licence show` or `install` without `common`, the `common` default `False` instead of `SUPPRESS`;
  - the old re-prompt text, `y` accepting, the empty answer accepting.

  Through the generator I ran 3 DOCX mutants more, all killed: T8.docx cover reading `guidance_refs`; the bracket dropping merged ids; DOCX rows not deduped. The T1-only cover truncation of B1 survived the full suite.
- **CI (attack 6).** Run 37631774505 (my push, `ci/a1840fc-1791381046-16825`): `completed success`, 7 jobs, each `success`. Run 37629330981 (the builder's): `completed success`. My branch is gone from origin. `ci/a1840fc-1791382169-18586` exists and is not mine; another session's gate.

## What I could not check

- The note's "Git Bash full suite at 834634c: 1 failed, 2400 passed". I ran only the failing files at `834634c`.
- PowerShell 5.1 figures. I ran Git Bash only.
- The test docstring's "in the LW-01 walk-through (... the site's synthetic cohort) `y` re-prompted". The LW-01 log and review note do not name the data the `y` was typed against.
- Python 3.12 locally. CI ran 3.12 and passed.

## Changes for other lanes (site pin move from 8ef3266)

This list adds nothing to the builder's. `public/sample-pack/T1.html` and `T8.html` change at the cover row, and T1 section 7 goes from 4 margin lines to 2. Any copy quoting `answer a or q` needs the new line; a grep of `proofpack-site/src` found 0. `/docs/quickstart` line 111's before-and-after claim now holds for `licence show|verify|install` too.

## Sentences I refused to write

- "The cover is complete in the DOCX". No test pins it for T1 (B1).
- "CI runs the E14 DOCX tests". It skips them (CI log above).
- "The gate is green on my run". The gate script exited 3 (N4). The run itself succeeded, and that is what I report.
