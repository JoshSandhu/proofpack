**Verdict: FAIL. 2 blockers, both sentences. No behaviour defect found: at `e67c5fa` the buyer's pages, DOCX, flags, prompt, fixtures register and CI all hold under my own probes. I measured: the cover row (licensed T1 19 -> 3 entries, T8 7 -> 2, compare-T2 14 -> 2, compare-T8 10 -> 2; a several-document fixture 25 -> 7 on T1); the margin lines (T1 21 -> 19, 0 repeats; DOCX 21 -> 19 rows carrying the same 21 ids); the flags (177 parses per tree, 0 refused on Python 3.14.6 and 3.12.10; 0 socket attempts with `--offline` last on all 8 commands, against 1 attempt each for `run` and `compare` without it); the prompt (30 answers, only `a`, `A `, `  Accept ` accept); the fixtures register (46 rows, 35 matched at 3ee5601 and at e67c5fa); 20 mutants, 19 killed; and my gate run 37642319586, `GREEN e67c5fa`. B1: the repair's own regression test is named `..._every_e14_docx_test_is_selected_by_ap4_and_takes_the_extra_rule`, but a DOCX test added to an E14 module through the CLI with `importorskip` passes it and is skipped silently under `PROOFPACK_REQUIRE_DOCX=1`. That is the FA-B1/RG-N3 class it was written to close. B2: commit `e67c5fa`'s message quotes `assert 'ap4' in set()` as the failure at `a1840fc`; the failure there is the set comparison.**

# E14 lens 2 (cold fresh-attack) on engine e67c5fa - Wednesday 7 October 2026

Cold lens on `e14-lw01` at `e67c5fa` (the repair of `a1840fc`, 6 commits on `3ee5601`). Inputs:
- the diff `a1840fc..e67c5fa`, and `3ee5601..e67c5fa` for the behaviour;
- the repair note `scratchpad/notes/E14_repair1.md`;
- the two lens-1 notes, now committed under `handoffs/`;
- `handoffs-orchestrator/2026-10-07_LW01_log.md` and `2026-10-07_user_review_notes.md`.

Method. I used five detached worktrees under `scratchpad/lens-E14-r2-fresh-attack/`:
- `tip` (`e67c5fa`) for the suite, the markers and the probes;
- `prev` (`a1840fc`) for the before figures;
- `base` (`3ee5601`) for the pre-E14 pages;
- `mut` (`e67c5fa`) and `mutprev` (`a1840fc`) for the mutants.

`PYTHONPATH` was set to each tree's `src` and checked with `python -c "import proofpack;print(proofpack.__file__)"`, which printed `...\lens-E14-r2-fresh-attack\<tree>\src\proofpack\__init__.py` each time. Every count below comes from my own scripts (`analyse.py`, `analyse_docx.py`, `probe_flags.py`, `probe_socket.py`, `probe_prompt.py`, `probe_multi.py`, `mutate.py`). They read `design/guidance_map_v1.csv`'s columns and python-docx directly. They do not use `label_for`, `cover()`, `cell_texts` or `e14_pages`. I used the repository's test helpers only to build documents and licences (`assemble`, `write_licence`, `ephemeral_registry`, `confirmed_mapping`).

Each mutant was reverted with `git checkout -- .` and `git clean`, and `git status --short` was empty after each. All five worktrees are removed. I made no commits. In `wt-e14` I created only this file. Platform: Windows 11 Home 10.0.26200, Python 3.14.6 (plus 3.12.10 for the argparse walk), Git Bash.

## Blockers

### B1. False test name, and the counter-example sits in the blocker class it was written to close: `tests/test_e14_repair1.py::test_fa_b1_rg_n3_every_e14_docx_test_is_selected_by_ap4_and_takes_the_extra_rule`

What it inspects (its own docstring says this accurately): the module-level `test_*` functions of `tests/test_e14_*.py` whose source contains the substring `render_docx`. It checks that their set is exactly the two known tests, that each carries `ap4`, that each has one `skipif` with `SKIP_REASON`, and that none calls `importorskip`. The name claims more: that *every* E14 DOCX test is selected by `ap4` and takes the extra's skip rule.

Counter-example, constructed and run (mutant T3 in `mutate.py`). I appended a genuine DOCX test to `tests/test_e14_cover_row.py`. It runs `cli.main(["run", ..., "--templates", "T1", "--format", "docx", "--offline"])` on a 400-row cohort, opens `T1.docx` through `_d = pytest.importorskip("docx")`, and asserts the cover cell holds 3 entries. It carries no `ap4` mark, and its source does not contain `render_docx`.
- The E14 files with `PROOFPACK_REQUIRE_DOCX=1`: `74 passed`. The meta-test passed, and so did the new test, because the extra is installed here.
- With docxtpl, docx and matplotlib hidden by a `-p` plugin (`sys.modules[name] = None`) and `PROOFPACK_REQUIRE_DOCX=1`: `1 passed, 1 skipped`. The skip reads `SKIPPED [1] tests\test_e14_cover_row.py:114: could not import 'docx': import of docx halted; None in sys.modules`.
- `pytest -m ap4 --collect-only tests/test_e14_cover_row.py`: `1/6 tests collected`. The docx-extra job would never select the new test.

So the meta-test stays green while an E14 DOCX test skips silently in every CI job. That is exactly the defect of FA-B1/RG-N3 (`SKIPPED [1] tests/test_e14_cover_row.py:90: could not import 'docxtpl'`). Today no such test exists, so the shipped tests are not under-run. The name, though, states a guarantee the check does not make, which is lens 1's B1 again in a new place.

Repair, either of:
- Rename the test to what it inspects, for example `test_fa_b1_rg_n3_the_e14_tests_that_call_render_docx_carry_ap4_and_needs_extra`.
- Widen the scan to every `test_*` of the `test_e14_*` modules whose source mentions `docx` or calls `importorskip`. T3 above is then the failing counter-example to run first.

Repro: append T3's function (the `EXTRA_TEST` text in `scratchpad/lens-E14-r2-fresh-attack/mutate.py`) to `tests/test_e14_cover_row.py` at `e67c5fa`, then run `PROOFPACK_REQUIRE_DOCX=1 python -m pytest -q -p no:cacheprovider tests/test_e14_repair1.py tests/test_e14_cover_row.py`. Result: all pass.

### B2. False quoted figure (commit message `e67c5fa`): "test_e14_repair1.py inspects those marks; it fails at a1840fc ("assert 'ap4' in set()")"

Run at `a1840fc` (`mutprev`, with the tip's `tests/test_e14_repair1.py` copied in): `7 failed in 0.92s`. The meta-test fails on the set comparison, not on `'ap4' in set()`:

```
E       AssertionError: assert {('test_e14_c...ng_every_id')} == {('test_e14_c...ng_every_id')}
E         Extra items in the left set:
E         ('test_e14_cover_row', 'test_docx_cover_row_names_the_distinct_documents')
E         Extra items in the right set:
E         ('test_e14_cover_row', 'test_docx_cover_row_text_equals_the_html_cover_labels_in_order')
```

The repair note says it correctly: "the first failing line is `Extra items in the left set`"; `assert 'ap4' in set()` appears only "with the expected set edited to a1840fc's names". The commit message drops that condition. This is the same kind of slip as lens 1's B2 (a commit-message sentence) and B4 (a note figure), each graded a blocker. Repair: one line in the E14 handoff correcting the commit message. The branch history need not be rewritten, just as `834634c` was handled.

Repro: `git -C <a1840fc tree> ...`; copy `tests/test_e14_repair1.py` from `e67c5fa`, then run `python -m pytest -q -p no:cacheprovider tests/test_e14_repair1.py`.

## Non-blocking (record and carry)

- **N1. Two drafts of one document dated in the same month print as one cover entry.** This is reachable only with a planted map. `cover_documents` dedupes on the label, and a draft label carries only the month and year (`label_for` uses `month_year`). I planted map `same_month`: AI-DSF `SUBGROUP_PERF`, `CALIBRATION` and `PERF_VALIDATION` dated `2025-01-28`, the other nine `2025-01-07`. My expectation counts distinct (document, version_date, status) among non-internal ids. Results:
  - T1: 3 entries for 4 groups.
  - T8: 2 for 3.
  - T2: 7 for 8.
  - The missing entry is the `2025-01-28` version.

  The guidance table itself prints the two versions under identical labels, so the loss starts in `label_for`, which predates E14. The shipped map dates all 12 AI-DSF rows `2025-01-07`, and the CLI never passes another map. The docstring's "(document, version or date, status ...)" and `test_cover_row_lists_each_distinct_guidance_document_once` both key on the label, so neither can see this case. If the map ever carries two dated drafts, the label needs the full date.
- **N2. The cover's internal rule is status equality.** Planted map `internal_spelling`, with `PP_SCOPE` status `internal (ProofPack)`: the `ProofPack internal: scope...` entry appears on the cover (T1 4 entries, T8 3, T2 8). This is not reachable on the shipped map. Lens 1 recorded the same rule (its N2).
- **N3. The sentence guards are literal substrings.** I re-inserted the old FA-B2 sentence into the tip's `cli.py`, rewrapped as `re-prompted without` / `#: being told how to accept.`. `test_e14_repair1.py -k cli`: `2 passed`. So the guard catches only the exact old wording.
- **N4. Review note 17's literal ask is not met.** The note asks: "Say 'type a to accept' in the prompt's first line or accept y." The first line is unchanged at `every role is high (N columns): [a]ccept / [q]uit? ` (it is line 304 at `3ee5601` and line 322 at `e67c5fa`), and `y` still does not accept. Only the re-prompt changed. No sentence claims otherwise: the `cli.py` comment says "under the unchanged prompt line". It is for Josh to decide whether the re-prompt is enough.
- **N5. Carried items still open.** I did not re-run them:
  - FA-N1, the `t8_context` `guidance_map` mutant.
  - FA-N5, the footer's internal entries: `ProofPack internal` occurs 23 times in my licensed T1.html, including the 2 guidance-table rows and every footer.
  - RG-N7, F19 `small_only_values`.

## What I could not break (what I tried, with figures)

- **Suite and lint at `e67c5fa` (scratch `tip`, Git Bash):** `2408 passed, 5 skipped in 418.76s`. The 5th skip is `test_e8_repair4.py:405` (no sibling `workflows/data` beside a scratch tree), so the total is 2413, the note's 2409 + 4. `ruff check .`: All checks passed. `ruff format --check .`: 358 files already formatted (355 at `a1840fc`).
- **Markers, tip against `a1840fc`:**

  | marker | e67c5fa | a1840fc |
  |---|---|---|
  | `day14` | 73 | 66 |
  | `day13` | 133 | 133 |
  | `day12` | 199 + 3 skipped | 199 + 3 skipped |
  | `ap4` | 200 | 198 |
  | `ap4` with `PROOFPACK_REQUIRE_DOCX=1` | 200 | 198 |
  | `fixture` | 178 | 178 |

  Deselected totals are 2413 against 2406. The difference of 7 is `test_e14_repair1.py`, and the replaced cover test counts one for one. No test was lost.
- **Lens 1's blockers are closed:**
  - FA-B1: at `a1840fc`, with `build_t1`'s cover loop cut to `cover_guidance[:1]` and T1.docx regenerated, the old test gives `1 passed` and the new test fails, `AssertionError: ('T1', 'FDA draft guidance, ...`.
  - FA-B2: the comment now matches `3ee5601`, where the prompt line read `[a]ccept / [q]uit? ` and the re-prompt `  answer a or q`.
  - FA-B3: the DOCX now prints merged ids in one bracket. My licensed T1.docx has 19 rows carrying 21 ids.
  - FA-B4: the note reads "9 lines out, 6 in". `git diff --numstat 3ee5601 e67c5fa -- tests/fixtures/golden` gives T1 `3 5`, T2 `2 3` and T8 `1 1`.
  - RG-N2: the docstring's literal counter-example, `sub.add_parser("probe", parents=[common])` (without `help=`) inserted above `licence` at `a1840fc`, gives `1 failed, 56 passed`, and the failure is the walk test.
- **The ap4 selection and skip rule (at `a1840fc` with the tip's two test files):**
  - `-m ap4 --collect-only`: `2/11 tests collected`.
  - Modules hidden, no variable: `2 skipped`, both with `SKIP_REASON`.
  - Modules hidden, `PROOFPACK_REQUIRE_DOCX=1`: `2 failed`, each `DocxExtraMissing`.
- **Cover (attack 1).** These were licensed CLI runs (`run --templates T1,T7,T8 --format json,html,docx` on the 5,000-row `make_cohort`; `compare` of F5 with `--templates T2,T7,T8 --format json,html,docx`), with `--offline --quiet --json-log` last, `egress.telemetry: true`, and sockets patched to refuse. Both exited 0 with 0 socket attempts. "Equals mine" means the cover equals my CSV-derived expectation, ids and labels in table order; the DOCX cell equals the HTML labels joined with `"; "`.

  | page | table rows | documents | cover (base) | equals mine | broken `#` links | margin lines (base) | repeats | ids per block = base |
  |---|---|---|---|---|---|---|---|---|
  | run T1.html | 19 | 3 | 3 (19) | yes | 0 of 22 | 19 (21) | 0 | yes |
  | run T8.html | 7 | 2 | 2 (7) | yes | 0 of 8 | 6 (6) | 0 | yes |
  | compare T2.html | 14 | 2 | 2 (14) | yes | 0 of 12 | 10 (11) | 0 | yes |
  | compare T8.html | 10 | 2 | 2 (10) | yes | 0 of 8 | 6 (6) | 0 | yes |
  | run T1.docx | - | - | 3 = HTML | yes | - | 19 rows (21) | 0 | yes |
  | run T8.docx, compare T8.docx | - | - | 2 = HTML | yes | - | 6 (6) | 0 | yes |

  - **Several documents (shipped map).** The synthetic document's `guidance_refs` plus `GB_PMS_44ZM3`, `GB_PMS_44ZL`, `EU_MDR_ART86_1`, `MDCG_2022_21`, `MDCG_2020_8`, two PCCP ids, `PP_SCOPE` and `FDA_STAT2007_BY_SITE`:
    - T1: 25 table rows, 7 documents, cover 7 (base 25), equals mine, 0 broken of 26 links.
    - T8: 14 rows, cover 7 (base 14).
    - T2: 20 rows, cover 7 (base 20).
    - T1.docx and T8.docx covers: 7 entries each, equal to the HTML.
  - In every page above: no duplicated element id, no internal entry on any cover, and the one AI-DSF cover entry carries "draft guidance (January 2025), not for implementation".
  - **Planted maps** `stat_two_versions` (`FDA_STAT2007_INDETERMINATE` dated 2008-01-01) and `section_filled` (sections on `LABELING_METRICS` and `INDETERMINATE`): covers equal mine. Margin lines are 20 and 21, with 0 repeats and 0 wrong merges, so lines that differ visibly are not merged.
- **Margin notes (attack 2).** For every merged line in every page, I rebuilt each `data-also` id's visible line from the CSV (`maps to <label> · section <s> · eSTAR: <e>`) and its draft class. HTML and DOCX gave 0 mismatches (`bad_merge: []`, `bad_rows: []`). Every DOCX row has `PP Margin Note Draft` exactly when its ids are drafts.
- **Flags (attack 3).** `probe_flags.py` walks the parser itself and finds 8 leaves. It puts each flag in every slot before, between and after the words and the required arguments, plus repeats, all 6 orders of the three after the last word, and two mixed placements: 177 parses per tree.
  - `e67c5fa`: 0 refused, 0 wrong values, on 3.14.6 and on 3.12.10.
  - `3ee5601`: 48 refused, all `licence show|verify|install` (`unrecognized arguments: --offline`).
  - Sockets: `connect`, `connect_ex`, `create_connection` and `getaddrinfo` were patched to record and raise, under `egress.telemetry: true`. `--offline`, and all three flags, last on `licence install|verify|show`, `doctor`, `map`, `run`, `compare` and `fixtures`: 0 attempts. Without the flag, `run` and `compare` each made 1 attempt, so the patch works.
- **Map prompt (attack 4).** Each answer was followed by `q`. The answers were `y Y yes n no e x`, the empty answer, `"  "`, a tab, `aa ok accept! a.`, Cyrillic `а`, full-width `ａ`, `ａccept`, `á`, `a` followed by U+200B, `q! "quit now" 1 true edit`. Every one printed `  type a and press Enter to accept, or q to quit` and halted H07 with `decided_by` `proposed`. Only `A `, `  Accept ` and `a` accepted. `Q`, `abort` and `QUIT` halted without a re-prompt.
- **Fixtures (attack 5).** `fixtures --offline` exited 0 at `3ee5601` and at `e67c5fa`: 46 rows each, 35 matched, 7 suite_only and 4 not_built. Every row matched at the base matches at the tip. The only differing field is F13's `reason`, which carries the tree's HEAD. `e67c5fa` changes no golden and no template (`git diff --stat a1840fc e67c5fa -- tests/fixtures src/proofpack/templates` is empty). Since `3ee5601` the golden lines are the 3 cover rows and the 2 merged margin blocks only.
- **Mutants: 20 in `mutate.py`, 19 killed.** They ran with `PROOFPACK_REQUIRE_DOCX=1` over the E14 files (plus `test_ap4_roundtrip`, `test_render_t1`, `test_render_t8` and `test_e10_t2` for the source mutants). The DOCX mutants were regenerated through `scripts/make_docx_templates.py`.
  - DOCX cover mutants: `[:1]` on T1 and on T8, reversed, `guidance_refs`, `[1:]` (drops the AI-DSF draft), drafts filtered out on T1 and on T8, ids for labels.
  - DOCX margin mutants: the bracket without `also`, the rows without `distinct_notes`, the filter replaced by the identity.
  - Test mutants: `ap4` removed from the cover test, `ap4`/`needs_extra` removed from the margin test.
  - Source mutants: cover not deduped, internal rows kept, notes keyed without eSTAR, the old re-prompt, `y` accepting, `verify` without `common`.

  The new DOCX cover test failed on all 8 DOCX cover mutants. On 2 of them (T1 `[:1]` and T1 reversed) it was the only failing test. The survivor is T3 (B1).
- **CI (attack 6).** `bash workflows/ci_gate.sh <tip> e67c5fa` printed:
  - `gate: JoshSandhu/proofpack e67c5fa -> ci/e67c5fa-1791385600-29284`
  - `gate: run 37642319586 ci: success`
  - `gate: GREEN e67c5fa`, exit 0

  All 7 jobs were `success`: import without scipy, Docker smoke, wheel, pip-audit, ap4 with [docx], pytest + ruff, and unshare -rn. The docx-extra job reads `199 passed, 1 skipped, 2213 deselected`; the run for `a1840fc`, 37629330981, read 197 per lens 1. The main job reads `2274 passed, 139 skipped`, `-m day14` `71 passed, 2 skipped`, `-m day13` `133 passed` and `-m day12` `199 passed, 3 skipped`. `git ls-remote origin "refs/heads/ci/e67c5fa-1791385600*"` printed nothing. Run 37642117620 on another `ci/e67c5fa-...` branch is not mine.

## What I could not check

- **Which two tests the docx-extra job's +2 are.** CI runs `-q`, so passed tests are not named. I infer them from the count and from the local `-m ap4` selection.
- **PowerShell 5.1.** I ran Git Bash only.
- **The Linux-only jobs** (reference image, network namespace). I read them from run 37642319586's conclusions.
- **A site-issued licence on the `--templates T1,T7,T8` buyer path.** I used ephemeral-signed licences.

## Changes for other lanes (site pin move from 8ef3266)

`e67c5fa` changes no CLI flag, default, path, JSON key, golden or rendered string; it changes tests, one comment and one docstring. The builder's list for `3ee5601..a1840fc` stands:
- the cover row of T1, T2 and T8;
- one margin line fewer in T1 section 7 and T2 section 5;
- `data-also` on a merged note;
- the DOCX bracket with several ids;
- the re-prompt string;
- the `licence show|verify|install --help` usage lines.

## Sentences I refused to write

- "Every E14 DOCX test runs in CI." B1 shows the meta-test does not ensure it.
- "The cover lists every distinct guidance version." N1: two drafts in one month merge (planted map).
- "The sentence guards stop the false sentences coming back." N3: a rewrapped copy passes.
- "Note 17 is fixed." N4: the first line is unchanged and `y` still re-prompts.
