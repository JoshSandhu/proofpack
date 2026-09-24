# Lens 5 (fresh attack) - build day 9, lane E, repair 4 at `e62d329` against `f72a9af` - 2026-09-24

**Verdict: PASS. No blockers.**

Lens-4 FA-B1 no longer reproduces at `e62d329`. I fed 11 inputs of my own, plus the paired criteria through the CLI in five licence states. On every one of them, no F5 plot draws a `paired_difference_vs_prior` criterion, and every other `ci_lower_bound` criterion is still drawn. The inputs:

- paired criteria on sensitivity, specificity, AUROC, age and op2;
- a paired criterion at `level: "*"`;
- a paired and a point criterion sharing an id and a value, in both orders;
- a paired criterion beside the fairness bound;
- a paired `ppa` criterion under a comparator;
- a paired criterion with injected site levels.

Checks on the tests:

- `tests/test_e9_repair4.py` run at `f72a9af`: `3 failed, 1 passed`, as the commit message says.
- `tests/test_e9_repair3.py` (the `e62d329` text) run at `952bddc`: `5 failed`, as its docstring says.

I record nine non-blocking items:

- **N1 is the one Josh should read.** T1 prints a paired-difference criterion as if it bounded the subgroup's own sensitivity. This is the text form of the defect repair 4 fixed on the figure.
- **Two sentence violations** in the repair's own text (N2, N3).
- **Three surviving non-equivalent mutants** in `_criterion_lines` (N5 to N7).
- The rest are records.

Two findings are graded by interpretation. Josh can overrule either:

- **N4.** One repair-4 test passes at `f72a9af`. The task's blocker list includes "a test that passes at f72a9af". I grade it non-blocking. It is declared as a pin in the commit message and the note, and the regression test for each repaired finding fails at `f72a9af`.
- **N1.** Every value and status it prints equals `run.json`, and D4 section 5.6 has no `type` column. I grade it record-and-carry. If Josh reads lens-4 FA-B1's grading as covering text as well as figures, N1 is a blocker and the verdict is FAIL.

**Worktrees.** All were under `scratchpad/lens-E9-r5-fresh-attack/`, and all were removed at the end:

| Worktree | Commit | Used for |
|---|---|---|
| `wt` | `e62d329` | suite, markers, lint (both shells), every probe, CLI states, sample pack, F17, timing, imports |
| `wtf` | `f72a9af` | `test_e9_repair4.py` copied in, pre-fix run |
| `wt95` | `952bddc` | `test_e9_repair3.py` (the `e62d329` text) copied in, pre-fix run |
| `wt1d` | `1d19e62` | the note's "baseline slip" claim |
| `wtmut` | `e62d329` | the committed day-9 sweep, my 7 mutants |

- **Imports.** In each worktree, `PYTHONPATH=<wt>/src python -c "import proofpack;print(proofpack.__file__)"` printed that worktree's `src\proofpack\__init__.py` before I used any figure from it.
- **Network.** Every CLI run carried `--offline`, with `socket.socket` and `socket.create_connection` replaced by a function that raises. Every run printed `socket calls 0`.
- **What I wrote.** I committed nothing. The only file I wrote in the main tree is this note. When I finished, `git status --short` in the main tree showed that file and the regression lens's note only. HEAD is `e62d329`.

## Blockers

None.

## Non-blocking (record-and-carry)

### N1 - T1 describes a paired-difference criterion as a bound on the subgroup's own statistic

This is the text twin of lens-4 FA-B1, and it is new.

**Input.** `probe/p2.py`, state `ok`, `--templates T1,T7,T8`, run through the CLI:

- `Cpd` (sensitivity, `type: paired_difference_vs_prior`, op1, sex = F, −0.05);
- `Cauc_pd` (auroc, the same type, 0.55);
- `C3` (op2, 0.70) and `C4` (op1, 0.6);
- `FAIRNESS`, with op2 at threshold 0.3.

**What T1 prints, verbatim:**

- the `CRITERION_STATUS` sentence: "Criterion Cpd (sensitivity, sex = F, op1 , CI lower bound >= −0.05 ; A , 2026-01-01 ): not assessable (requires_compare)." It is followed by "Criterion Cauc_pd (AUROC, sex = F , CI lower bound >= 0.55 ; ...): not assessable (requires_compare)";
- Table T1-17: `1 Cpd sensitivity sex = F op1 ci lower bound >= −0.05 A · 2026-01-01 — — — — not assessable requires_compare — —`;
- T1-11, op1, the F row: `Cpd (row 1) → not assessable ; max LB — at n = —, attainable: —`, in the row whose columns are "Δ Sensitivity vs ref".

**What the page does not print.** On that T1, `paired`, `prior version` and `evaluated by compare` occur **0** times. (`evaluated by compare` is `criteria.py`'s gloss for `requires_compare`.) The declared `type` reaches only T8's echo of `criteria.yaml`: 3 hits there, 0 on T1 and T7.

**Why it matters.** A reader of the sentence reads −0.05 as a bound on the lower confidence bound of sex = F's sensitivity. The customer declared it as a margin on the new-minus-prior difference. That is the misreading lens 4 graded a blocker when it was drawn on F5, and repair 4 closed it on F5 only.

**Why I did not grade it a blocker:**

- every printed value is the declared one, and the status is the run's own (`not_assessable`, `requires_compare`);
- D4 section 5.6's T1-17 layout (Id, Metric, Scope, Statistic, Comparator, Value, ...) and D4 section 8's `CRITERION_STATUS` skeleton have no place for the type.

The gap is in the spec as much as in the build, so it needs Josh's decision: a `type` column in T1-17 and a "(difference vs prior version)" phrase in `CRITERION_STATUS`, or neither. That change touches a skeleton, which DEC-64 and the D4 section 8 table bind.

**Repro.** From `tests/`: `render_t1.render_t1(assemble(cohort_with_a_thirty_row_site(), make_criteria(criteria=[_criterion(id="Cpd", type="paired_difference_vs_prior", scope={"attribute": "sex", "level": "F"}, value=-0.05)], fairness=None)))`. The page contains `CI lower bound >= −0.05` and 0 occurrences of `paired`.

### N2 (sentence_violation) - `tests/test_e9_repair3.py` docstring: "... the first ``E`` line of each is quoted under "Pre-fix" in ``handoffs/2026-09-24_E_lens4_regression.md`` and in the repair-4 note."

The first half is true. The lens-4 regression note carries `**Pre-fix.**` once and quotes an `E` line for each of the five tests. My own run of the `e62d329` file at `952bddc` gave `5 failed` with the same five first lines.

The second half is false. The repair-4 note (`scratchpad/notes/E9_repair4.md`) quotes the `E` lines of the four repair-4 tests only. I grepped it for four strings that appear in the repair-3 `E` lines:

- `written to`
- `state_what_they_inspect`
- `For F versu`
- `C3 (A, 2026-01-01): 0.7`

Result: 0 hits.

This is the lens-4 N1 kind again, written by the repair that closed lens-4 N1. **Repro:** grep the repair-4 note for any of the four strings.

### N3 (sentence_violation, minor) - `tests/test_e9_repair4.py` docstring: "The first ``E`` line of each test, run in an ``f72a9af`` worktree ..., is quoted in the message of the commit that added this file."

The file has 4 tests. At `f72a9af` it gives `3 failed, 1 passed`. `test_the_sex_t1_11_rows_still_print_the_paired_rows_status_and_not_cref` passes, so it has no `E` line, and `1d19e62`'s message quotes three. The commit message itself says "3 failed, 1 passed" correctly. The docstring's "each" does not.

**Repro:** copy the file into an `f72a9af` worktree and run it with `PYTHONPATH` forced.

### N4 - one repair-4 test passes at `f72a9af` (graded non-blocking, see above)

`test_the_sex_t1_11_rows_still_print_the_paired_rows_status_and_not_cref` passes at `f72a9af`. This is disclosed in the commit message ("the T1-11 pin describes behaviour f72a9af already had") and in the note. It pins the behaviour the new `subgroup_blocks` docstring describes: `Cref` at sex = M, the reference level, is printed in no T1-11.

The regression tests for FA-B1, FA-N1 and FA-N2 each fail at `f72a9af`. FA-N3 is the rename, which the FA-N1 test reads. The first `E` lines are:

- `{'F5-sex-sensitivity': ['customer criterion Cpd (A, 2026-01-01): −0.05', ...]} != ...`;
- `assert 'the first `... repair note' not in ...`;
- `assert '(an ``auroc`` criterion' not in ...`.

### N5 - surviving non-equivalent mutant in the repair-4 filter: `paired_after_dedupe`

The mutant moves the paired-type skip below `seen.add(key)`.

**Against `-m "day9 and not slow"`:** `1 failed, 156 passed`. The one failure is `test_sweep_day9.py::test_every_day9_pattern_matches_its_file_the_declared_number_of_times`, which fails because the committed pattern no longer matches, not because behaviour changed.

**It is not equivalent.** Take `Cdup` declared twice on sex = F, op1, 0.4: first as a paired criterion (row 1, `not_assessable`), then as a point criterion (row 2, `met`).

- At `e62d329`, F5 draws `customer criterion Cdup (A, 2026-01-01): 0.4` at `M282.0,20.0 L282.0,72.0`.
- Under the mutant, F5 draws no line (`probe/p1.py` under `probe/mut2.py dedupe`).

No test declares a paired and a point criterion with the same id and value. The line goes missing, but no wrong value appears, so this is record-and-carry. **Repro:** `python probe/mut2.py <wt> dedupe` with `PROBE=probe/p1.py`.

### N6 - surviving non-equivalent mutant: `label_author_first_entry` (survives the full suite)

The mutant makes the F5 label read `entries[0]`'s author instead of the drawn row's entry. Against the full suite: `1415 passed, 1 skipped, 1 xfailed in 106.72s`. No test declares two F5-drawn criteria with different authors.

`probe/p_auth.py` declares `Ca` (Dr A, 2026-01-01, 0.3) and `Cb` (Dr B, 2026-02-02, 0.5):

- at `e62d329`, the labels are `['customer criterion Ca (Dr A, 2026-01-01): 0.3', 'customer criterion Cb (Dr B, 2026-02-02): 0.5']`;
- under the mutant, the second label is `'customer criterion Cb (Dr A, 2026-02-02): 0.5'`.

The label line predates repair 4. Repair 4 moved the `entry` lookup it reads above the filter. **Repro:** `python probe/p_auth.py <wt>` with the one-line mutation.

### N7 - carried lens-4 FA-N4 survivor `f5_dedupe_by_id_only` still survives

Against `-m "day9 and not slow"`: `158 passed, 1259 deselected`. It is non-equivalent on lens 4's `C1` 0.4 / 0.3 input. The note carries it.

### N8 - F5 draws declared values outside the axis range outside the plot (pre-existing, record)

These are point criteria, whose statistic is the plotted one:

- `Cneg` (sensitivity, sex = F, −0.05, `met`): `M178.5,20.0 L178.5,72.0`, left of x0 = 190;
- `Cbig` (auroc, sex = F, 1.3, `not_met`): `M489.0,20.0 L489.0,72.0`. The axis ends at x = 420, and the line crosses the printed value column at x = 430.

`Cabs` (sex = X, a level that is not in the data, `level_absent`) is also drawn, at `M305.0,...`, on "Sensitivity by sex". The value and label are the customer's own. The position is off the plot. **Repro:** `probe/p1.py`, cases "point value -0.05", "point value 1.3 on auroc" and "level absent X".

### N9 - a paired criterion at `level: "*"` appears in no T1-11 and on no F5 (record)

`Cstar_pd` (sex = `*`) gives one `criteria_results` row, `{'attribute': 'sex', 'level': '*'}`, `not_assessable`, `requires_compare`. `_reads_for` does not expand a paired criterion by level, so T1-11 matches no level and F5 skips it. It is printed in T1-17 and in its sentence only. This is the same shape as carried row 110. **Repro:** `probe/p1.py`, case "paired level *".

## Measured against the note and the commit messages

| Command (`wt`, `e62d329`, `PROOFPACK_TR39_FULL` = `workflows/data/confusables-18.0.0.txt`) | Git Bash | PowerShell 5.1 | Note |
|---|---|---|---|
| `python -m pytest -q -p no:cacheprovider` | `1415 passed, 1 skipped, 1 xfailed in 141.33s` | `1415 passed, 1 skipped, 1 xfailed in 117.80s` | the same counts |
| `-m day9` / `day8` / `day7` / `day6` / `day5` | `159` / `468` / `139` / `285` / `54 passed` | `day9` `159 passed` | `159` / `468` / `139` / `285` |
| `-m ap2` / `day4` / `day3` / `day2` / `day1` | `88` / `182` / `29 passed, 1 xfailed` / `40` / `59 passed, 1 skipped` | - | equal to the r6 block |
| `ruff check .` / `ruff format --check .` | `All checks passed!` / `198 files already formatted` | the same | the same |
| `doctor --offline` (empty home) | 17 `[ok` lines, exit 0 | - | 17, exit 0 |
| `tr39_subset.py <full file> --check` | `vendored subset matches` | - | the same |
| `licence show` (empty home) | `licence: none found`, `refused (no_file)`, exit 4 | - | exit 4 |
| `mutation_sweep.py --list` | 292 lines: ap2 16, day5 34, day6 112, day7 25, day8 87, day9 18 | - | the same |
| `mutation_sweep.py --marker day9` (`wtmut`) | `18 planted, 18 killed, 0 survived; 180 s`, exit 0; `f5_criterion_line_for_paired_difference` killed with `1 failed, 23 passed` | - | `18 planted, 18 killed ... 190 s` |
| `mutation_sweep.py --marker day9` at `1d19e62` | `baseline (no mutant) does not pass -m day9; refusing to sweep`, `FAILED ...test_the_repair_3_file_names_where_its_e_lines_are_and_what_its_t1_11_test_reads`, exit 2 | - | the note's "baseline slip", confirmed |

**No statistics changed.** `git diff --stat f72a9af e62d329` over `stats/`, `gates.py`, `criteria.py`, `narrate/`, `egress/`, `io/`, `run.py`, `cli.py`, `render/format.py`, `schema/`, `design/`, `pyproject.toml`, `uv.lock` and `.github` prints nothing. So does `eda8a35..e62d329` over `stats/`, `gates.py`, `criteria.py` and `design/tokens.json`.

**Tests.** `git diff --name-status f72a9af e62d329 -- tests scripts` gives:

- `M scripts/mutation_sweep.py`
- `M tests/test_e9_repair3.py`
- `A tests/test_e9_repair4.py`

The only marker, skip or xfail line added is `+pytestmark = pytest.mark.day9`.

## What I could not break (with figures)

**Lens-4 FA-B1 (the blocker) is closed.** `probe/p1.py` at `e62d329` rendered 11 documents. On every one, the F5 lines equal the non-paired `ci_lower_bound` rows at the plotted operating point, and each T1-11 prints every row by position with its own status:

- paired on specificity, age 0-40 and op2 (two-op): no line;
- paired + point with the same id and value, in both orders: one line, from the point row;
- paired beside `FAIRNESS`: T1-11 prints `Cpd 1 not assessable` and `fairness:tpr_gap 2 criterion not met`.

Through the CLI (`probe/p2.py`, the four criteria above), the 9 T1s written in states ok, trial and grace (3 flag variants each) all give `F5-sex-sensitivity ['customer criterion C4 (A, 2026-01-01): 0.6']`, with empty specificity and AUROC plots. Under a comparator (`probe/variants.py`), `F5-sex-ppa` draws `Cppa` and not `Cpd_ppa`.

**Lens-4 N1 to N3.** Checked on the `e62d329` source:

- `test_e9_repair3.py` no longer says "in the repair note" (N2 above is its replacement sentence);
- `render/t1.py` no longer carries "(an ``auroc`` criterion";
- the repair-3 T1-11 test is renamed, and its regex reads the sex F row of op1 and op2, as the new name says.

**The new `subgroup_blocks` docstring.** "The reference level has no T1-11 row, so a criteria row scoped on it is printed in no T1-11" holds on `Cref` and on `probe/p1.py`. A declared reference level missing from the data halts `H09: subgroup reference_level is not a level of the analysed rows`, so no page has a table without a reference row.

**My mutants of the repair-4 code** (`probe/mut.py`, each against `-m "day9 and not slow" -x`, the file restored after each):

| Mutant | Result |
|---|---|
| `entries[i - 1]` | killed, `test_a_paired_difference_criterion_draws_no_f5_line` |
| guard `0 < i` | killed, the same |
| `type` read from the row | killed, the same |
| `type not in (paired, point)` | killed, the same |
| label author from `entries[0]` | **survived** (N6) |
| paired skip after dedupe | killed only by the sweep-pattern test (N5) |
| dedupe by id only | **survived** (N7, carried) |

**Cells.** `probe/cells.py` never imports `render.format`. It re-derives cells by D4 section 1.2 from the exact binary value (`Decimal(x)`, half-even, U+2212, a sign on differences, zero unsigned). It resolves each `data-ref` pointer in `run.json` and compares the cell character by character after separating the tier marks:

| Document | Match | Mismatch | Printed as a reason |
|---|---|---|---|
| licensed two-op CLI T1 | 244 | 0 | 16 |
| `y_pred`-only | 94 | 0 | 29 |
| clustered | 92 | 0 | 50 |
| logit | 116 | 0 | 7 |
| 40-level site | 306 | 0 | 52 |
| comparator | 126 | 0 | 10 |

Each Number that carries a reason prints `n.e. (<its reason>)` and `no interval`, never a bare estimate. Every tier mark equals the Number's `flags`: ᶜ = `imprecise`, ᵇ = `very_low_precision`.

**Digits.** `probe/digits.py` traces every digit run outside `data-ref` cells, SVG and customer text to some rounding of a `run.json` value:

- licensed T1: 1,814 runs, 11 distinct untraced. All 11 are dates, versions, the run id, `SHA-256`, `510(k)`, `21 CFR 807.92` and `SI 2024/1368`.
- T7: the untraced runs are dates, versions, citation years, URLs and the static conventions text (the coverage table with 0.897, and F6's chi-square 4.63 / 13.90). The per-method counts are counts of `run.json` Numbers.

**Methods.** `probe/methods.py` compares T7's methods table with an independent count of Numbers per method in `run.json`:

- licensed run: wilson 249, newcombe10 384, delong_wald 45, irls_wald 6, log_delta 8, delong_logit 7, bootstrap_percentile 11, none 19;
- clustered run: cluster_bootstrap_percentile 95, none 322.

These equal T7's counts. T7 section 4's difference methods (`delong_wald` 15, `newcombe10` 180) equal my own count over `diff_vs_reference` and `diff_vs_complement`.

**Figures** (`probe/figs.py`, the documented `data-map` inverted). The largest deviation across the licensed, clustered, logit and 40-level T1s:

| Mark | Largest deviation |
|---|---|
| F2 curve (401 points; 1,201 on the 40-level run) | 0 |
| F2 operating-point markers | 2.8e-14 |
| F4 decile points and bars | 0 |
| F4 histogram x-range and height | 0 |
| every F5 estimate | 0 |

The only `fill` other than `none` is `.fig-hist`, in CSS. `<rect>` occurs 10 times per T1 with a probability score. The 40-level site draws 40 rows (viewBox height 1120). A level at 0 positives prints `n.e. (zero_denominator)` and draws no point.

- Logit score: `F4 (calibration) is omitted: calibration is null (score_not_probability).`
- `y_pred`-only: `... (no_score_column)` and `F2 (ROC) is not drawn: the run document carries no ROC array.`
- No table on any of the 15 variant pages has an empty body.

**Facets** (`render.sentences.facet_text`, every facet and all four kinds):

- A Number with est 0.8123, CI 0.7012 to 0.9034 and k/n 81/100 prints `81.2%`, `70.1%`, `90.3%` and `81/100 (81.2%) [70.1, 90.3]`, each facet in its own slot.
- A typed reason prints `n.e. (zero_denominator)` / `no interval` in every position.
- A negative difference prints `−3.2 [−6.1, −0.4]`. Zero and −0.00004 print `0.0 [−2.0, +2.0]`.
- On a suppressed Number, `k` and `n` print the counts, but egress (`egress/build.py`) writes suppressed cells with null counts, and T1 and T7 carry no suppressed Numbers.

**Words and anchors** (`probe/scan.py`, `html.parser`). The scan excludes customer text only; status spans and disclaimers are inspected. The word list is the checker's `VERDICT_WORDS` ∪ `CERTIFICATION_WORDS` ∪ `FORBIDDEN_ON_PAGE` ∪ the brief's words, plus "model is", "performs well", "no evidence of bias" and "well calibrated".

The pages scanned were T1 and T7 of six CLI runs (licensed two-op, `y_pred`, clustered, logit, 40-level, comparator) and T8 of the licensed run. Hits on T1 and T8:

- `met` only inside `.status` ("criterion met" / "criterion not met");
- `endorsed`, `approved` and `certification` only in the cover note and the long disclaimer, as negations (carried RG-N5).

T7's only hits are `guarantee` in the conventions negations (carried) and `endorsed` in the cover note.

All 83 skeletons plus the phrase maps (104 texts) carry no listed word except the three status phrases and T2's `CRITERION_NOT_MET_RECORD`.

Every `<a href="#FDA_AIDSF_*">` carries "draft guidance (January 2025), not for implementation": 0 unlabelled of 27 on T1, 3 on T7 and 6 on T8. `@import`, `url(`, `<link`, `<script` and `javascript:` occur 0 times. No hex colour lies outside `tokens.json`. `font-family` is only `var(--pp-type-text)` / `var(--pp-type-mono)`.

**Injection** (`probe/inj.py`, through the CLI). The inputs:

- seven site levels: `<script>alert(1)</script>`, `<img src=x onerror=1>`, `{{ 7*7 }}`, `{% raw %}x`, U+202E, `LONG` + 10,000 `L` + `[unverified] planted`, and U+200B;
- a criterion id `C<b>x</b>{{7*7}}`;
- a model name with `<script>`, U+202E and `[unverified] model`;
- a 10,000-character `[unverified] slot` string as author, justification, reference-standard description and operating-point source.

Results: rc 0. `html.parser` finds no `script`, `img`, `iframe`, `object`, `embed` or `b` start tag and no `on*` attribute on T1, T7 or T8.

| Page | `{{ 7*7 }}` literal | U+202E as `&#x202e;` | U+202E raw | `[unverified] planted` | `[unverified] model` | 10,000-character runs |
|---|---|---|---|---|---|---|
| T1 | 29 | 29 | 0 | 11 | 10 | kept |
| T7 | 3 | - | 0 | - | 3 | - |
| T8 | 13 | - | 0 | - | 5 | kept |

U+200B is carried raw, 11 times on T1 (carried FA-N8).

**Licence states** (`probe/p2.py`, `--templates T1,T7,T8`; counts are footers / marks):

| State | Result |
|---|---|
| ok | rc 0; footers T1 9, T7 3, T8 3 |
| trial | rc 0; `TRIAL` T1 12, T7 5, T8 8 |
| grace | rc 0; `LICENCE EXPIRED - not for submission` T1 11, T7 5, T8 7 |
| expired | rc 4, no HTML, `Next step: proofpack licence install FILE, then run again for T1.html, T7.html, T8.html (docs: /docs/run)` |
| none | the same as expired |

- `--templates T9`: rc 5 in every state, `error: unknown --templates id 'T9'; choose from T1, T7, T8`, no traceback.
- `T1,,T7` and `t1`: rc 0 with the named pages, or rc 4 with a next-step line naming only them.
- 0 socket calls in all 20 runs.

**Sample pack** (built twice, sockets refused, 0 calls, exit 0). Sizes: run.json 236,843, T1 142,924, T7 47,666, T8 35,178 bytes, equal to the note's.

- `run.json` differs only at `/manifest/duration_s`, `/manifest/run_id` and `/manifest/started`.
- T1, T7 and T8 are identical after masking those values.
- Each page container carries a footer: T1 9 of 9, T7 3 of 3, T8 3 of 3.
- `SYNTHETIC - illustrative` occurs T1 12, T7 5, T8 7 times. `NO LICENCE - not for submission` occurs T1 11, T7 5, T8 7 times.
- T7 carries 18 `[unverified]` beside 18 `pending verification`.

**F17.** I ran one prepared input (paired criteria, two operating points) in two homes. `run.json` differs at `duration_s`, `run_id` and `started` only, and T1, T7 and T8 are identical after masking.

A first attempt that wrote the input twice also differed at `mapping_sha256`, because the mapping file was written twice.

**100,000 rows** (`tests/test_render_timing.py -s`): `run --templates T1,T7,T8 4.73 s; T1+T7+T8 renders from run.json 0.27 s; T1 3693048 bytes`.

**Imports with jinja2 and markupsafe blocked** by a meta-path finder. `proofpack`, `proofpack.stats`, `cli`, `run`, `narrate.templates`, `render.sentences`, `render.figures` and `render.format` import, with `jinja2 loaded: False` and `markupsafe loaded: False`. `render.t1` refuses to import: `blocked by lens5: markupsafe`.

## What I could not check

- A wheel in a fresh venv. `hatchling` is not installed, and building one needs a download I have no approval for. Repair 4 changes no packaged non-Python resource.
- The day-8 sweep (about 21 minutes). Repair 4 touches no day-8 path: the diff over `narrate/`, `egress/`, `run.py` and `cli.py` is 0 lines.
- The PowerShell day-9 sweep.
- Browser rendering of an off-axis criterion line (N8), and of overlapping labels when two criterion values are close. All labels sit at y = 14.
- Whether a customer would declare a paired-difference criterion with a subgroup scope. The schema and `io/declare.py` accept it, and the CLI runs it to rc 0.

## Sentences I refused to write

- "F5 now draws only criteria that constrain the plotted statistic." N8's `Cabs` (a level not in the data) is drawn. What I wrote instead: on the 11 inputs named, no paired criterion is drawn, and each non-paired `ci_lower_bound` row at the plotted operating point is.
- "The page no longer presents a paired margin as a level threshold." N1 shows that the sentence and T1-17 do.
- "Every repair-4 test fails before the fix." The pin passes (N4).
- "The repair-3 docstring now points to where its E lines are." Half of its pointer is false (N2).
- "`_criterion_lines` has no surviving mutant." N5, N6 and N7 survive.
