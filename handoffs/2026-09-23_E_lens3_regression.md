# Lens 3 (regression and record) - build day 9, lane E, repair 2 at `e17a510` - 2026-09-24

**Verdict: PASS. No blockers.** I re-ran every figure in the repair-2 note (`workflows/notes-day9/E9_repair2.md`) and each one matched. Lens 2's blocker FA-B1 is closed: on the lens's two-operating-point input, T1 names the operating point in all 126 op-bound sentences it prints, and 0 are unnamed. Every lens-2 sentence item the note marks fixed no longer reproduces. The five new defect tests fail at `dd94874` on the assertions the note quotes. The two pins pass at `dd94874`, as the note says, and each one kills its planted mutant. I raise four non-blocking items below. One is a minor sentence violation in a test name (N1).

Worktrees, all under `scratchpad/lens-E9-r3-regression/`, all removed at the end:

| Worktree | Commit | Used for |
|---|---|---|
| `wt17` | `e17a510` | suite, markers, lint, the rerun block in both shells, the two-op CLI repro |
| `wtdd` | `dd94874` | the new and edited test files copied in (pre-fix); the sample pack at `dd94874` |
| `wtmut` | `e17a510` | 16 mutants, golden regeneration, the day-9 sweep |
| `wtpin` | `e17a510` | the two pin mutants, probes, the wheel build |

In each worktree I forced `PYTHONPATH=<wt>/src` and checked that `proofpack.__file__` printed that worktree's `src\proofpack\__init__.py` before I used any figure from it. Every CLI run carried `--offline`. The two-op script also replaced `socket.socket` / `create_connection` with a function that raises, and it printed `socket calls 0`. I committed nothing. The only file I wrote in the main tree is this note.

One process disclosure. In `wtdd` I ran `git stash -u` to build the sample pack on clean `dd94874` sources. That wrote `stash@{0}` into the shared repository refs. I checked that the entry held only my three copied test files, and I dropped it at once. `git stash list` is now empty, as it was before.

## Blockers

None.

## Non-blocking

**N1 (sentence_violation, minor) - a new test name claims more than the test inspects.** The test is `tests/test_e9_repair2.py::test_the_repair_1_test_name_and_docstring_state_what_they_inspect`. It checks four literal substrings of `tests/test_e9_repair1.py`:

- `no_internal_decision_text` is absent;
- `no_josh_or_open_decision` is present;
- the old phrase "each fails at\n``71b00d2`` (the pre-fix" is absent;
- "except ``test_the_footer_helper_counts_per_page_and_refuses_the_lens_mutant``" is present.

It does not, and cannot, check that the name and docstring "state what they inspect". This is the same kind of defect as lens-2 FA-N3, which this test was written to close. A name that describes what it checks would be `..._repair_1_test_name_and_docstring_carry_the_repaired_text`.

Repro: `sed -n '/def test_the_repair_1_test_name/,/^$/p' tests/test_e9_repair2.py`.

**N2 - two tests in the new file pass at `dd94874` (as the note says).** These are `test_pin_the_licensed_json_next_step_names_the_templates_asked` and `test_pin_f2_draws_no_marker_for_a_typed_specificity`. They pin code lens 2 found correct, not a fix. Read literally, the rule "a test that passes pre-build pins nothing" makes this a finding. I record it, and I checked that each pin does pin something. In `wtpin` I planted the lens's two mutants:

- `cli_json_branch_T8` (the licensed `--format json` line always names `T8.html`) gave `FAILED ...::test_pin_the_licensed_json_next_step_names_the_templates_asked`, `1 failed, 6 passed`;
- `f2_gate_se_only` (`if not fmt.has_interval(se_num):`) gave `FAILED ...::test_pin_f2_draws_no_marker_for_a_typed_specificity`, `1 failed, 6 passed`.

Both results equal the note's.

**N3 - T7's new z/p sentence also prints on runs whose `run.json` has no z or p.** The sentence is "z and the two-sided p are written to run.json beside the difference (`diff_vs_reference.auroc.detail` and `diff_vs_complement.auroc.detail`)". It comes from `design/conventions_T7.md` and prints on every T7. What `run.json` holds, by run type:

| Run | AUROC-difference blocks | Blocks carrying `z` and `p_value` |
|---|---|---|
| i.i.d. (`cohort_with_a_thirty_row_site()` + `CRITERIA` + `FAIRNESS`) | 6 `diff_vs_reference`, 9 `diff_vs_complement` | 6 and 9 |
| clustered (400 rows, `case_id = c{i//2}`) | 15 | 0 (every `detail` empty, method `none`) |
| `y_pred` only (200 rows, score deleted) | 18 | 0 (every `detail` empty) |

T7 prints the sentence on all three.

In context the sentence describes the analytic DeLong route. The same paragraph goes on to say that under clustering "both analytic methods are refused". So I do not count this as a hard-rule violation. A reader of a clustered pack does still find those keys empty.

No test covers the complement half. `test_t7_says_where_z_and_p_are_written_...` asserts `{"z", "p_value"}` only on the first `diff_vs_reference` block of the i.i.d. document.

Repro: `assemble(make_cohort(n=400, with_case_id=True)` with `case_id = c{i//2}`, `clustering: case_id`), then read `subgroups[*].diff_vs_*.auroc.detail` and grep `render_t7` for "written to run.json beside the".

**N4 - the note's site sha is stale.** The note greps `proofpack-site` "at `f289501`". The site is now at `02c42b8` (lane S's day-9 handoff). At `02c42b8`, `git grep` for `SUBGROUP_ESTIMATE`, `FAIRNESS_GAP`, `run again for`, `bar interval`, `No target is compared`, `printed as detail` and `slots(` still finds no match. The site vendors no T1 page (`git ls-files | grep -i sample` lists only the demo scripts and the fixtures reports). Record only.

## Measured against the note

**Suite.** `PROOFPACK_TR39_FULL` set, `wt17`:

- Git Bash: `1406 passed, 1 skipped, 1 xfailed in 129.68s`;
- PowerShell 5.1: `1406 passed, 1 skipped, 1 xfailed in 125.27s`.

Both equal the note (1399 at `dd94874` + 7).

**Markers.** Equal to the note in both shells:

| Marker | Count |
|---|---|
| `day9` | 150 |
| `day8` | 468 |
| `day7` | 139 |
| `day6` | 285 |
| `day5` | 54 |
| `ap2` | 88 |

`--collect-only` in PowerShell gives the same figures, out of 1408 collected.

- `day5`-`day8` and `ap2` equal the counts collected at `eda8a35`.
- `day9` is 150 = lens 2's 143 + the 7 tests in `test_e9_repair2.py`.
- `pyproject.toml` line 86 declares `day9`. The CI step "pytest every declared day marker" reads the list from `pyproject.toml`.
- On both day-7 runs, `test_licence.py`'s live-key test passed (lens-2 FA-N9 is carried; it did not bite this time).

**Lint.** `All checks passed!` / `191 files already formatted` in both shells.

**Pre-fix run.** I copied `test_e9_repair2.py`, `test_e9_templates.py` and `test_claims.py` from `e17a510` into `wtdd`. Result: **`11 failed, 236 passed`**, equal to the note:

- 5 of the 7 new tests fail;
- the 5 edited skeleton cases fail (`subgroup_with_diff`, `subgroup_diff_not_estimable`, `subgroup_estimate`, `subgroup_not_estimable`, `fairness_gap`);
- `test_the_library_transcribes_d4_section_8_...` fails at `tests\test_claims.py:426`.

Each first `E` line equals the note's `prefix_E.txt`:

- `AssertionError: assert [('CL-0028', ...H_DIFF'), ...] == []`, with `Left contains 184 more items, first extra item: ('CL-0028', 'SUBGROUP_ESTIMATE_WITH_DIFF')`;
- `AssertionError: assert 'No target is compared to' not in '<!DOCTYPE h...>\n</html>\n'`;
- `assert 'no_internal_decision_text' not in '"""Build da..., 1, 1, 0]\n'`;
- `assert 'Next step: proofpack licence install FILE, then run again with --format json,html for T7.html (docs: /docs/run)' in "run written: ...`;
- `AssertionError: assert 'no Number printed' not in '<figure cla...>\n</figure>'`.

The skeleton cases fail on the sentence comparison itself. An example is `'For sex = F,....4] versus M.' == 'For sex = F ....4] versus M.'`. None aborts on import or attribute.

**Nothing weakened.**

- `git diff --name-status dd94874 e17a510 -- tests/` gives `M` for the two goldens, `test_claims.py`, `test_e9_repair1.py` and `test_e9_templates.py`, and `A` for `test_e9_repair2.py`. There is no `D`.
- The only marker line added is `pytestmark = pytest.mark.day9`. No skip, xfail, `.only` or todo was added.
- The edits to existing tests do three things:
  - add `op_id` to five text contexts and their expected sentences;
  - add `op_id` to one slot tuple;
  - rename one test (the repair-1 test body is unchanged).

**No statistics.** Each of these gave the result shown:

- `git diff --name-status dd94874 e17a510 -- src/proofpack/stats/ src/proofpack/gates.py`: empty;
- the same from `eda8a35`: empty;
- `git diff --stat dd94874 e17a510` over `criteria.py`, `egress/`, `narrate/checker.py`, `narrate/claims.py`, `io/`, `schema/`, `render/format.py`, `run.py`, `pyproject.toml`, `uv.lock`, `design/tokens.json`, `.github` and `scripts/`: 0 lines;
- `git diff eda8a35 e17a510 -- design/tokens.json`: empty.

The sample pack's `run.json` built at `dd94874` and at `e17a510` differs only at `/manifest/duration_s`, `/manifest/run_id` and `/manifest/started`, and both are 236,843 bytes.

**Rerun block.** I copied the builder's `rerun/rerun.sh` and `E9r2/rerun_r2.ps1` into my folder, with only the output folder and the tr39 path changed, and ran them from `wt17`. After path and run-id normalisation, every line equals the repairer's `E9r2/rerun_bash.txt` / `rerun_ps.txt`, except the `## diffs` block. That block counts `git diff 941f8a7 HEAD`, and HEAD is now two commits on: 3,975 lines against 3,926, and 174 `A` against 173, from the two lens notes and `test_e9_repair2.py`.

| Command | Result (both shells unless noted) |
|---|---|
| ruff | `All checks passed!` / `191 files` |
| doctor | exit 0, 17 `[ok` lines (PowerShell: `essential=1`) |
| tr39 | `vendored subset matches`, exit 0 |
| `--list` | 289 lines: 16 ap2, 34 day5, 112 day6, 25 day7, 87 day8, 15 day9 |
| no-licence run | Git Bash exit 4 and `Next step: proofpack licence install FILE, then run again for T8.html (docs: /docs/run)`; PowerShell `exit=-1`, from the script's `Select-Object`, as at r6. Both give `253938 bytes 20 keys 70 claims 0 rejections 3 refs [0, 1, 2, 2, 2, 3, 4, 5, None] CRLF 0 BOM False` |
| nomap | exit 3 H07, `dir=no` / `dir=False` |
| `licence show` | exit 4 (PowerShell `-1`) |
| `html_run` | `T8.html bytes 43961` |
| repros5 / repros6 / p3 / p2 / p7 (Git Bash) / alias / offline / paths / imports | as the note, including `socket calls 0` and `imports ok; loaded: []` |
| verdict grep | `5 passed` |
| E6 schema | `1 passed` |
| k1 | `engine claims rejected: 0` and the same 15 `free_text accepted` texts |

**Two-op CLI repro.** I ran the repairer's `E9r2/twoop_cli.py` against `wt17`. It printed `rc 0 socket calls 0`, then the four sentences in the note byte for byte (`diff` against the repairer's `twoop_out.txt`: equal). My own count, which reads `run.json`'s claims and does not use the test's code: T1 prints 130 claims. 126 carry an `operating_point`, and every one of them contains its op id as a separate token in the sentence:

| Template | Sentences |
|---|---|
| `OVERALL_ESTIMATE` | 26 |
| `SUBGROUP_ESTIMATE_WITH_DIFF` | 60 |
| `SUBGROUP_ESTIMATE` | 30 |
| `FAIRNESS_GAP` | 2 |
| `CRITERION_STATUS` | 8 |

Unnamed: 0. T7 and T8 print no claim paragraphs.

**Day-9 sweep** (Git Bash, `wtmut`): `15 planted, 15 killed, 0 survived; 165 s`, exit 0. The note measured 137 s. My run shared the machine with the PowerShell suite.

**Sample pack.** `scripts/build_sample_pack.py --out` gives run.json 236,843 / T1 142,924 / T7 47,830 / T8 35,178 bytes, equal to the note. At `dd94874` the same script gives T1 139,999 and T7 47,808, the note's "before" figures. T8 is unchanged.

**100,000-row timing** (the day-9 timing test, inside each full suite):

| Shell | Whole run | Three renders | T1 size |
|---|---|---|---|
| Git Bash | 4.19 s | 0.35 s | 3,693,048 bytes |
| PowerShell | 5.33 s | 0.39 s | 3,693,048 bytes |

T1's size equals the note's.

**CLI and output changes for S4.** `git diff dd94874 e17a510 -- src/proofpack/cli.py` changes only the no-licence next-step string, adding "with --format json,html " when `html` is not among the formats. `run.py`, `schema/` and `pyproject.toml` do not change. The note's S4 section names that line. It also names:

- the T1 and T7 byte changes;
- `_schema/conventions_T7.md`;
- the `LIBRARY` / `VARIANTS` skeleton texts and `slots(...)` now including `op_id`;
- repair 1's omitted context keys (RG-N4).

I checked the `SentenceError` claim: `render_parts("SUBGROUP_ESTIMATE", text={"attribute": "a", "level": "b"}, ...)` raises `SentenceError slot 'op_id' has no value in the context`. As far as the diff shows, the list is complete.

## Could not break

- **Lens-2 blockers and sentence items at `e17a510`:**
  - FA-B1: closed (above).
  - FA-N1: "printed as detail" is absent from T7. The planted revert `conv_n1_restored` is killed (`2 failed`: the new T7 test and the T7 golden).
  - FA-N2: "No target is compared to" is absent. `conv_n2_restored` is killed (`2 failed`).
  - FA-N6: the no-licence `--format json` line names `--format json,html`. Two mutants are killed: the condition inverted (`2 failed`) and the clause made unconditional (`1 failed`, the repair-1 exit-4 test).
  - FA-N7: F4 with every bin typed prints "no bar drawn". `if True` gives `1 failed` and the clause dropped gives `1 failed`.
  - FA-N3 / FA-N4 / RG-N1: the renamed test and the docstring are as the note says (N1 above is about the new test's own name).
- **Lens-1 blockers re-run at `e17a510`:**
  - FA-B2: on the clustered T1 (400 rows), "Wilson score for proportions, DeLong for AUROC" appears 0 times and "Newcombe method 10 for proportions" 0 times.
  - FA-B3: no bin-1 decile point is drawn (0).
  - RG-B1: `curve_flag.minimum = 150` on the sample `run.json` gives "150/150 convention" once.
  - RG-B2: `verdict` 0 on every page I rendered.
- **My mutants of the repair-2 code** (`wtmut`, each run against `-m "day9 and not slow"`, restored after each):

  | Mutant | Result |
  |---|---|
  | `FAIRNESS_GAP` op clause dropped | 3 failed (two-op test, skeleton case, T1 golden) |
  | `SUBGROUP_ESTIMATE_WITH_DIFF` op clause dropped | 3 failed (the same three) |
  | `SUBGROUP_ESTIMATE` `not_estimable` variant clause dropped | 1 failed (its skeleton case) |
  | `difference_not_estimable` variant clause dropped | 1 failed (its skeleton case) |
  | `claim_text` filling `op_id = "op1"` always | 1 failed (the two-op test; the one-op golden cannot see it) |
  | CLI condition inverted | 2 failed |
  | CLI clause unconditional | 1 failed |
  | F4 `if drawn_nums` -> `if True` | 1 failed |
  | F4 "no bar drawn" dropped | 1 failed |
  | the two conventions reverts | 2 failed each |

  None survived.
- **Footer, anchor and SVG mutants:**
  - The last `{{ page_footer() }}` removed from `templates/T1.html`: `5 failed`. The failures include `test_the_footer_is_on_every_page_and_once_in_print`, the golden, the furniture test, the sample-pack marks test and the footer-helper test.
  - The `FDA_AIDSF_SUBGROUP_PERF` row's status emptied in `guidance_map_v1.csv`: `13 failed, 54 errors` (the loader refuses the map).
  - The same status set to `final`: `4 failed`, including `test_every_fda_draft_anchor_is_labelled_in_every_margin_note` and `test_every_caption_repeats_n_the_interval_method_and_the_anchor`.
  - `anchors.label_for` returning the document title only: `5 failed`, including the same two.
  - `PlotMap.y` +1 unit: `6 failed`. These are the F2, F3 and F4 inversion tests, the golden, and the two sweep-pattern tests (the sweep's `PlotMap.y` pattern no longer matches).
- **Goldens and masking.**
  - `PROOFPACK_REGEN_GOLDEN=1` on the three golden tests gave `3 passed`, and `git diff --stat` then printed nothing (line endings only).
  - I also rendered the golden's document after a `json.dumps`/`json.loads` round trip: T1 156,895 and T7 48,804 bytes, both identical to the committed goldens once LF-normalised.
  - The T1 golden diff is 46 removed and 46 added lines. Every added line carries `at operating point <span class="customer-text inline">op1</span>`. The T7 golden diff is the two conventions lines.
  - Two sample-pack builds differ in `run.json` only at `/manifest/duration_s`, `/manifest/run_id` and `/manifest/started`. T1, T7 and T8 are identical once those three values (and `run_id`'s first 8 characters) are masked. Masked occurrences: T1 `started` 10, `rid8` 10, `run_id` 1; T7 4 and 4; T8 `run_id` 2, `started` 5, `duration_s` 1, `rid8` 4.
- **Library against D4 section 8.** D4's table names 55 ids (the four-id row counted as four). The library has 56. `comm -3` shows one extra id, `SUBGROUP_ESTIMATE`, the recorded engine addition, and no missing one. `all_skeletons()` returns 83 texts. `test_the_claims_schema_is_final_and_its_enums_agree_with_the_code` compares the schema enum to `list(templates.LIBRARY)` and to the id set of `all_skeletons()`, so it reads the whole library.
- **Forbidden words and anchors** on the two-op CLI pack and the sample pack (T1, T7, T8 of each):
  - E8's `FORBIDDEN_ON_PAGE` outside `.status`, `.disclaimer` and `.customer-text`: 0 hits on all 6 pages.
  - The checker's wider lists: 1 hit per page, `endorsed`, in the cover-note negation (lens-2 RG-N5, carried as needs 1).
  - `verdict` 0 and `biased` 0 on all 6 pages.
  - `FDA_AIDSF_*` anchors carrying "draft guidance (January 2025), not for implementation": T1 27/27, T7 3/3, T8 6/6.
  - Sample pack: every page of T1 (9), T7 (3) and T8 (3) carries `SYNTHETIC - illustrative`, `NO LICENCE - not for submission` and one `page-footer`. T7 carries 18 `[unverified]` beside 18 "pending verification".
- **Wheel in a fresh venv.**
  1. I built the wheel with `python -m uv build --wheel --offline`.
  2. I installed it with `pip install --no-deps --no-index` into a new `venv`. `numpy`/`jinja2` came from a one-line `.pth` naming the user site directory as a path. That line adds the directory to `sys.path` only; `site` does not process the `.pth` files inside it, so the editable `_editable_impl_proofpack.pth` stays inactive.
  3. With `PYTHONPATH` unset, `proofpack.__file__` printed `...\venv\Lib\site-packages\proofpack\__init__.py`, and no `editable` module was loaded.
  4. `resource_path("conventions_T7.md")` resolved inside the venv's `_schema/`. It carries the new z/p text (True), with "No target is compared" False and "printed as detail" False.
  5. `slots()` of `SUBGROUP_ESTIMATE` and `FAIRNESS_GAP` include `op_id`.
  6. `render_t1` on the two-op `run.json` gave a page identical to the CLI's source-tree T1 (200,793 bytes).

## Could not check

- The day-8 sweep (about 25 minutes per shell). It was not re-run. Lens 2 did not re-run it either.
- A fresh `71b00d2` run of `test_e9_repair1.py`. Its docstring's new "except the footer helper" clause rests on lens 2's measurement (`14 failed, 131 passed`, the footer-helper test the one pass). Repair 2 changed only that test's name and the docstring.
- Browser rendering of the longer subgroup and fairness sentences and of F4's new caption.
- Whether any input makes T1 print an op-bound claim with `operating_point: null`. The engine's `_subgroup_claims` and `_fairness_claims` always set it. A claim without it would raise `SentenceError` at render (measured on a hand call). I did not look for a checker path that accepts such a claim; that belongs to the fresh-attack lens.
- The 100,000-row timing outside the suites (the note measured it inside the suite too).

## Cut and carried, against what I measured

The note's carried list matches what I found open:

- FA-N5 rest (five survivors from lens 2);
- FA-N8;
- FA-N9 (the live-key test reads the site's working tree);
- RG-N3 (`scope.LONG_FORM_ITEMS[6]` 200/200; still printed once beside "150/150" in my probe);
- RG-N5 (needs 1);
- DEC-12 (ii): no sweep mutant for repair 1 or 2; the list is 15, and none of my 14 repair-2 mutants is in it;
- the lens-1 carries;
- row 49 and DEC-55.

Two items the note does not list:

- N3 above: no test holds the complement half of the z/p sentence, and the sentence prints on clustered and `y_pred`-only T7s whose `detail` blocks are empty.
- Open question 1's duplicate AUROC gap is visible in the two-op repro: `+0.079 [−0.002, +0.160]` printed once per operating point.

## Sentences I refused to write

- "Every test in the repair fails before the fix." The two pins pass at `dd94874` (N2).
- "T1 names the operating point in every sentence." Written instead: on the two-op CLI input, the 126 claims T1 prints with an `operating_point` each contain their op id.
- "T7's z/p sentence is true of every run." It is true of the 15 blocks of the i.i.d. document. On the clustered and `y_pred`-only documents the named keys are empty (N3).
- "The wheel ships the repair." Written instead: the wheel built at `e17a510`, installed into a fresh venv, rendered one two-op T1 identical to the source tree's and carries the new conventions text.
