# E11 (build day 11, lane E) at `ba26d88`: cold fresh-attack lens 4 (2 October 2026)

**Verdict: PASS. No blockers.** Three non-equivalent mutants survive the whole suite (N1-N3), two sentences in the repair are false (N4, N5), and the F4 calibration figure draws clustered decile intervals with no `ᵈ` (N6, graded non-blocking below with the reason; Josh may read DEC-75 (b) more strictly). Read the non-blocking list; it is not empty.

What I attacked and could not break, in one line each (figures further down):
- **DEC-75 (a).** No McNemar p-value in `run.json`, on T2, or in a sentence, on 17 clustered compares: 13 declared shapes, the detected route, an unpaired compare and two point-estimate / no-criteria variants. The unclustered compare is byte-for-byte the same in `comparison.mcnemar` / `mcnemar_by_metric` (bar the new null key) and `differences` as at `45e6761`. Its p-values are re-derived by hand from F5's raw CSVs.
- **DEC-75 (b).** Every Number with an interval in 15 clustered runs and 15 clustered compares carries `clustered_coverage_not_established`, at least five cases, a tier below 30 cases and `ᵃ` below 10. The JSON walk found 0 exceptions in 1,333 Numbers with an interval. Page scans of T1, T2, T7 and T8 (HTML, and T1 / T7 / T8 DOCX), cell by cell, found 0 table cells or sentences with an interval and no `ᵈ`. The unclustered pages print `ᵈ` only in the legend row.
- **DEC-75 (c).** At 2, 3 and 4 cases (six shapes), 0 Numbers with an interval anywhere in `run.json` or on a page. At 5 cases the cells print with `ᵃᵈ`.
- **DEC-75 (d).** I re-derived 5 of the 36 Newcombe limits with my own method-10 code from the PDF on disk: four match, and the excluded fifth is `0.873672` against the printed `0.8736`.
- **Lens 3's FA-B1 and FA-B2** no longer reproduce on lens 3's own probes.

Target: `ba26d88` on `main` (repair 3 is `6e19574`; `ba26d88` adds the handoff), unpushed. Detached worktrees under `scratchpad/lens-E11-r4-fresh-attack/`:
- `wt` (`ba26d88`): the suite, lint, probes, the coverage regeneration and the repository's day-11 sweep;
- `wt2` (`ba26d88`): my 30 planted mutants, each restored with `git checkout`;
- `wt3` (`ba26d88`): M19 planted by hand, then restored; the oracle, TR39 and doctor checks;
- `wt0` (`45e6761`): the regression runs.

`PYTHONPATH=<wt>/src python -c "import proofpack;print(proofpack.__file__)"` printed a path inside each worktree before I trusted any figure there. Every suite run had `PROOFPACK_REQUIRE_DOCX=1` and `PYTHONIOENCODING=utf-8`. Every CLI run was in-process through `proofpack.cli.main(..., registry=ephemeral_registry())` with `--offline`. Platform: Windows 11, CPython 3.14.6 (win-amd64), numpy 2.5.1, Git Bash. I committed, pushed and downloaded nothing. This note is the only file I wrote outside the scratchpad. The worktrees were clean (`git status --short` empty) and were removed with `git worktree remove --force` at the end.

## Blockers

None.

## Non-blocking (record and carry)

**N1. Mutant M19 survives every behavioural test in the suite.** The mutant is `narrate/claims.py:588`, `if not isinstance(entry, dict) or entry.get("p") is None:` changed to `if not isinstance(entry, dict):`; this is the repository's own `e11r3_mcnemar_sentence_on_a_refused_entry`.
- Under `-m day11`, the only failure is `tests/test_sweep_day11.py::test_every_day11_pattern_matches_its_file_the_declared_number_of_times`, the sweep's pattern-count test (`1 failed, 143 passed`).
- The full suite, with that test deselected, gives `1 failed, 1995 passed, 2 skipped, 1 xfailed`. The one failure is `tests/test_sweep_day9.py::test_every_declared_mutant_of_every_day_still_matches_its_file`, another pattern test.
- What the mutant changes, measured in `wt3` on a clustered F5 compare (`grp:3`, 34 cases): the page is unchanged (no McNemar sentence). `run.json` gains `claim_rejections: [{"claim_id": "CL-0033", "detail": {"value_ref": "/comparison/mcnemar/op1/p"}, "reason_code": "value_ref_unresolved", "substituted": false, "template_id": "MCNEMAR_RESULT"}]`.
- So the claims checker catches what the guard was written to stop, and the guard has no test of its own.
- The repair note's `71 planted, 71 killed` counts this mutant as killed. In my runs it is killed only by the pattern-count test, which fails for any mutant whose replacement removes its own pattern. My run of the repository sweep is reported under "What I could not break".
- Repro: plant the line in a worktree, then `PYTHONPATH=<wt>/src python -m pytest -q -m day11 -x`.

**N2. Mutant M28 survives the full suite.** The mutant drops `*auroc_precision_flags(n_cases, resampler.class_units.values()),` from `comparison._paired_auroc_cell`, so the clustered paired AUROC difference loses its class tier.
- `-m day11`: `144 passed`. Full suite: `1996 passed, 2 skipped, 1 xfailed`.
- Not equivalent. F5 with the 50 positive rows in 8 cases and the 50 negatives as single-row cases (58 cases; `probe/q1_cli.py OUT posgrp:8 1`) at the tip: `comparison.differences.auroc.number.flags` = `['delong_refused_clustered', 'very_low_precision', 'clustered_coverage_not_established']`, and T2 prints `−0.078 [−0.179, +0.003]ᵇᵈ`.
- With the mutant, `clustered_number` adds `precision_flags(58)` = `[]`, so the cell keeps `ᵈ` but loses `ᵇ`.
- Not a blocker class, because the cell keeps its mark. The test gap: no test feeds a paired AUROC difference of 30 or more cases with fewer than ten cases in a class.

**N3. Mutant M30 survives the full suite.** The mutant is `calibration._clustered_cell` `status = "refused_clustered" if number.has_ci else "unavailable"` changed to `status = "refused_clustered"`.
- `-m day11`: `144 passed`. Full suite: `1996 passed, 2 skipped, 1 xfailed`.
- JSON-only (`analytic_status` of a calibration cell refused for fewer than five cases). The repair note names this status change, and no test inspects it. Related to the repair's own carried row E11r3-6.

**N4 (sentence, shipped test docstring).** `tests/test_e11_repair3.py` line 3 says: "Each test below except the two control tests was run against `45e6761` ... and failed there".
- The file has one control test: `grep -n -i control` finds only `test_control_an_unclustered_compare_keeps_the_mcnemar_p_value`.
- Measured at `45e6761` (`wt0`): `19 failed, 1 passed` of 20. The repair note's own figure agrees.

**N5 (sentence, shipped docstring).** `stats/bootstrap.py::clustered_number` says that below five cases "the interval is refused - a Number with the same estimate, counts and flags (`imprecise` dropped ...)". The next bullet adds the case-count tier only "otherwise".
- The code adds `precision_flags(n_cases)` before the refusal branch, so a refused Number that had no tier gains one.
- Counter-example: F5 compare with `case_id` of four cases of 25 rows in a shuffled order (`probe/q1_cli.py OUT perm:25,25,25,25 1`). `comparison.differences.brier` and `.slope` are built with `flags=[]`. They come out `not_estimable_reason fewer_than_five_cases` with `flags ['not_evaluable_shown_for_transparency']`.
- The behaviour is reasonable; the sentence is false.

**N6. The F4 calibration figure draws clustered decile intervals with no `ᵈ`.** On a clustered run (`grp:3`, 34 cases) T1's F4 figure draws nine decile bars. These are `wilson_deff` Numbers whose decile-table cells print `ᵃᶜᵈ` / `ᵇᶜᵈ` directly below. Neither the bars nor the caption carry a mark. The caption reads "bar interval: Wilson score on the design-effect sample size n / DEFF; not drawn, no interval: bin 5 n.e. (boundary_estimate)ᵃ ...". I looked at the T1.docx PNG (`word/media/image2.png`) myself: the legend line carries `ᵈ` on slope and intercept only.
- Graded non-blocking because the grading rule's object is an interval cell, and every one of those Numbers' cells carries the mark. Figure bars carry no `ᵃᵇᶜ` either, clustered or not.
- The F5 forest plot's row labels and the ROC legend do carry `ᵈ` (F5 labels via `fmt.tiers`).
- Present at `45e6761` too, not introduced by repair 3.
- DEC-75 (b) says "so none prints unlabelled". If Josh reads a figure bar as printing, this is a blocker for him to call.

**N7. On a run of four or fewer cases T7 does not explain the reason every cell prints.** On the four-case F5 run (`25,25,25,25`):
- T1 prints `fewer_than_five_cases` 50 times and T2 21 times.
- T7 contains it 0 times. Section 6 (where the "Fewer than five cases" paragraph lives) and the `cluster_bootstrap_percentile` method description (which names the rule) are printed only when a Number carries one of the two clustered methods, and here none does.
- The T1 legend row's "(T7 section 6, printed when the run has a clustered interval)" is true of this run; the reason is simply undocumented on the run's own pages.

**N8 (sentence on the page, pre-existing).** T1's IPA footnote prints "The IPA row's tier superscript (ᵃ) is the proportion tier applied to the IPA's own interval: it states the half-width on the IPA's scale" on the four-case run.
- On that run the IPA has no interval: `n.e. (insufficient_clusters)`, flags `['not_evaluable_shown_for_transparency']`.
- `ᵃ` is the case-count tier, not a half-width. The same sentence prints at `45e6761` (measured, `o/old_25x4`).
- Repair 3 rewrote the expression that feeds this footnote (`calibration_block`'s `ipa_tiers`) and wrote a test of it, but tested only the `ᵇᶜ` case with an interval.

**N9. What DEC-75 (c)'s floor of five lets print, measured.** This is information for Josh; it is within DEC-75 and every cell carries `ᵃᵈ`.
- Coverage of the printed interval at exactly five cases, engine `proportion_ci`, R 1000, B 400, TAU2 0.5 (`probe/q7_cov5.py`):

  | case sizes | truth | coverage | method |
  |---|---|---|---|
  | `10,3,3,3,3` | 0.5 | **0.839** | cluster bootstrap |
  | `10,3,3,3,3` | 0.9 | 0.897 (777 of 1000 printed; the rest `boundary_estimate`) | cluster bootstrap |
  | `60,10,10,10,10` | 0.8 | **0.790** | cluster bootstrap |
  | `20,20,20,20,20` | 0.9 | **0.826** | `wilson_deff` |

  My own percentile cluster bootstrap on the same cohorts: 0.838 / 0.697 / 0.783 / 0.730.
- An AUROC cell of three positive cases beside three negative cases (six cases) prints with `ᵃᵈ`. That is the repair's need 52.

**N10. The Accept test was weakened.** `tests/test_e11_deff_wilson.py::test_accept_every_printed_cell_under_the_committed_threshold_carries_its_tier...` replaced `seen["cluster_bootstrap_percentile"] > 0` with `seen["fewer_than_five_cases"] > 0`. The cohort no longer has to exercise a bootstrap-route proportion at all. The other files still exercise that route, so this is coverage of the test, not of the code.

## What I could not break (tried, with figures)

- **Suite and lint (`wt`, `ba26d88`, Git Bash, `PROOFPACK_TR39_FULL` set).**
  - Full suite: `1998 passed, 1 skipped, 1 xfailed in 251.54s`. The skip is `test_doctor_cli.py:57`; the xfail is F13 pROC, day 12.
  - `ruff check .`: `All checks passed!`. `ruff format --check .`: `294 files already formatted`.
  - Markers (`--collect-only`, each passed inside the full run): `day11` 144, `day10` 262, `day9` 337, `day8` 471, `ap4` 198, `ap3` 176, `ap2` 91. These are the note's figures exactly. Against lens 3's `3302d59` figures, day11 is +19 and ap4 +1; the rest are unchanged.
- **Regression at `45e6761`.**
  - The tip's `tests/test_e11_repair3.py` in `wt0` gives `19 failed, 1 passed`; the pass is the control.
  - The four `test_dec75b_every_...` parameters fail with `Left contains 30 / 10 / 26 / 130 more items`, which are the handoff's "30, 10, 26 and 130" exactly.
  - The same CLI probe on four cases of 25 rows at `45e6761`: run 27 and compare 49 Numbers with an interval, every one below five cases. At the tip: 0 and 0.
- **DEC-75 (a), McNEMAR under clustering** (`probe/q1_cli.py`, compare `--templates T2,T7,T8 --format json,html,docx` plus run `T1,T7,T8`).
  - Shapes: `5 x 12 + 40 x 1`; `grp:3` (34 cases, within outcome and sex); `grp:10,1,1` (27); `grp:6` (18); `grp:20` (8); `grp:12`; `grp:13,12`; `20 x 5`; `perm:20 x 5`; `perm:60,10,10,10,10`; `50,50`; `34,33,33`; `25 x 4`; `perm:25 x 4`; `perm:40,30,20,10`; `sexsplit:2` and `sexsplit:3` (one sex single-row cases, the other two or three cases per class); `posgrp:8`.
  - Also the detected route (`clustering.unit: none` with repeated `case_id`, W13), a clustered `--allow-unpaired` compare (`mcnemar` null, no caption clause) and the lens-3 shapes through lens 3's `p1_clustered_cli.py`.
  - Every clustered compare printed `mcnemar.op1` `b 10 c 2 p None statistic None method none not_computed_reason mcnemar_assumes_independent_pairs`, and Se / Sp `b 5 c 1` the same.
  - Every T2 printed 0 McNemar p cells and 0 sentences matching `McNemar ... p =`, with the caption clause present. T7 named McNemar only in the section-6 sentence.
  - The schema refuses `p` beside the reason and a reason-less `none` (the test feeds both, and I read the `oneOf`).
- **Unclustered McNemar, by hand** (own code, F5 raw CSVs at `>= 0.5`).
  - Accuracy `e f g h` = `80 2 10 8`: b 10, c 2, exact p `0.03857421875`, corrected chi-square 4.0833 (p 0.0433, not used: b + c = 12 < 25).
  - Sensitivity and specificity: each `40 1 5 4`, exact p `0.21875`.
  - The engine's unclustered `run.json` gives the same three p-values with `exact_mcnemar` and `not_computed_reason None`.
  - Against `45e6761` on the same unclustered compare, `comparison.mcnemar`, `mcnemar_by_metric` (bar the new key) and `differences` are equal. T2's text differs only by the new legend table and "paired cases" -> "paired rows" (six sentences). The unclustered run's `run.json` (minus manifest, flow, ledger) is equal; T1 / T7 differ only by the `ᵈ` legend row's text, and T8 by that and its new legend.
- **McNemar type I error, own code** (`probe/q4_mcn.py`, no repository import, R 2000, seed 4242, each version's own case effect Var 0.5 and row noise Var 0.5): `5 x 50 + 25 x 1`, p 0.9: **0.543**; `30 x 10`, p 0.85: **0.255**; `275 x 1`: **0.0355**. These agree with T7's printed 0.538 / 0.263 to Monte-Carlo error. Lens 3's `p5_own.py` re-run at R 1000: 0.5330 / 0.2630 / 0.0280, own and engine `mcnemar()` equal.
- **DEC-75 (b), marks** (my own walker and page scanner, `probe/q1_cli.py` and `probe/q2_cells.py`).
  - Walker check on every Number with both bounds: the flag, `n_cases >= 5`, a tier below 30 cases and `ᵃ` below 10. Total 0 exceptions:

    | shape | compare: Numbers / exceptions | run: Numbers / exceptions |
    |---|---|---|
    | `5 x 12 + 40 x 1` | 49 / 0 | 26 / 0 |
    | `grp:3` | 106 / 0 | 67 / 0 |
    | `grp:10,1,1` | 101 / 0 | 66 / 0 |
    | `grp:6` | 92 / 0 | 56 / 0 |
    | `20 x 5` | 32 / 0 | 16 / 0 |
    | `perm:20 x 5` | 64 / 0 | 33 / 0 |
    | `perm:60,10,10,10,10` | 55 / 0 | 29 / 0 |
    | `grp:20` | 34 / 0 | 14 / 0 |
    | `grp:12` | 72 / 0 | 42 / 0 |
    | `sexsplit:2` | 62 / 0 | 31 / 0 |
    | `sexsplit:3` | 91 / 0 | 57 / 0 |
    | `posgrp:8` | 99 / 0 | 62 / 0 |
    | detected `grp:3` | 106 / 0 | 67 / 0 |

  - Families present across those documents: calibration O:E, slope, intercepts, Brier, reference Brier, IPA, decile bins; overall and subgroup AUROC; `diff_vs_reference`, `diff_vs_complement`, fairness gaps; `comparison.differences` (proportions, AUROC, Brier, slope); `comparison.subgroups`; prior-version cells.
  - Page scan, per HTML / DOCX table row (the mark in the cell or the estimate cell before it) and per paragraph outside tables: 0 unmarked intervals on T2.html, T8.html / .docx (compare and run) and T1.html / .docx in every shape above. Up to 100 intervals per T1.html. The only scanner hits were the T7 prose range "(range [0, 1])" and three sentences whose mark follows the interval (`... IPA 0.348 [0.154, 0.498]ᵃᶜᵈ`), which I read by eye.
  - The unclustered F5 control: `ᵈ` occurs once per page, in the legend row only; 198 compare and 128 run Numbers with an interval, none with the flag.
  - The legend row is present on T1, T2, T7 and T8 (HTML and DOCX) wherever criteria exist. A clustered compare with `criteria: []` prints 0 `ᵈ` on T8 and no T8 legend; T2 there has 48 `ᵈ` and the legend.
- **Lens 3's probes at the tip.**
  - `p1_clustered_cli.py`, ten cases of ten rows: T2-3 Sensitivity `−8.0 [−37.1, +4.0]ᵃᵈ`, `5 / 1`, `n.e. (mcnemar_assumes_independent_pairs)`. `run.json` `n_cases 6`, flags `['newcombe_refused_clustered', 'not_evaluable_shown_for_transparency', 'clustered_coverage_not_established']`.
  - `p1_clustered_cli.py`, lens shape: `−8.0 [−28.6, +1.1]ᵇᵈ`, `n_cases 14`, and Accuracy `−8.0 [−17.9, −0.9]ᵈ`, all three McNemar cells `n.e.`. The sentence reads "on 100 paired rows". FA-B1 and FA-B2 do not reproduce.
  - `p2_diff_cov.py 1000 500`: paired Se difference `5 x 50 + 25 x 1` coverage **0.8849**, every printed cell flagged `newcombe_refused_clustered, clustered_coverage_not_established`. `10 x 10` **0.8850**, flags `+ very_low_precision`. `10 x 5` 0.9208; `5 x 10` 0.9635 with `ᵃ`. `4 x 3`: 0 printed (the probe's ZeroDivisionError). This is the note's 0.8849 / 0.8850 exactly.
  - `p11_sub_own.py`: own subgroup differences 0.8690 / 0.9020 / 0.8370.
- **DEC-75 (c), below five cases.**
  - `50,50`; `34,33,33`; `25 x 4`; `perm:25 x 4`; `perm:40,30,20,10`: 0 Numbers with an interval in either `run.json` and 0 intervals on every page. T1 printed `n.e. (fewer_than_five_cases)ᵃ` 50 times on `25 x 4`.
  - Point-estimate criteria on a four-case cell (`probe/q5_pe.py`): `not_assessable`, `no_interval`, detail `fewer_than_five_cases`, for sensitivity and the paired accuracy difference.
  - `sexsplit:2`: sex F's sensitivity (2 cases), AUROC (4) and every `diff_vs_reference` (smaller side 2 or 4) refused. `sexsplit:3`: F's sensitivity (3 cases) refused; F's AUROC (6 cases, both classes) prints `ᵃᵈ`.
  - Five cases (`20 x 5`): every interval `ᵃᵈ`.
  - DEFF-Wilson by hand (own fractions-free code against `proportion_ci`):
    - 6 x 5 (3,4,1,5,2,0): DEFF 2.8, `[0.243137, 0.756863]`;
    - unequal 5,5,4,4,3,3,2,2,1,1: DEFF 1.91358, `[0.362097, 0.798542]`;
    - five cases of 4 rows (share exactly 0.20): DEFF 2.5, `[0.215216, 0.784784]`;
    - 12 singletons: DEFF 1, `[0.319511, 0.80674]`.
    - Each matches the engine to 1e-6.
    - Four cases of 3 rows (2/1/3/0): DEFF 20/9 = 2.2222, with no interval and `fewer_than_five_cases`.
- **DEC-75 (d), Newcombe.** I extracted Table III from `scratchpad/e11/newcombe1998_uottawa.pdf` (SHA-256 `90a3a049...0d0f87`) with pypdf and computed method 10 with my own code. The limits, mine against the paper:

  | e f g h | mine | printed |
  |---|---|---|
  | `36 12 2 0` | (0.05693, 0.340428) | (0.0569, 0.3404) |
  | `35 14 0 1` | (0.146074, 0.417462) | (0.1461, 0.4175) |
  | `53 0 0 1` | (−0.072938, 0.072938) | (−0.0729, 0.0729) |
  | `0 29 1 0` | (0.666592, 0.988183) | (0.6666, 0.9882) |
  | `1 97 1 1`, lower | 0.873672 | 0.8736 (the recorded exclusion) |

  - F5 `80 2 10 8`: (−0.155356, −0.010249).
  - `fixtures --offline`: `rows 46: matched 34, not matched 0, no oracle recorded 2, no independent oracle 0, not built 5, compared by the test suite only 5`. `unverified` appears 37 times in `fixtures_report.json`. `F5-newcombe-paired` compares 35 values, worst 4.876e-5, `unverified: false`.
- **AI-DSF qualifier.** Two scanners: lens 3's `p3_scan.py`, and my own per-block-element / per-`w:p` scan. Each counts mentions of AI-DSF, "Lifecycle Management and Marketing Submission", "draft guidance" or "AI-enabled device software functions" that lack `draft guidance (January 2025), not for implementation`:

  | run | page | mentions / unqualified |
  |---|---|---|
  | clustered `grp:3` | T2 | 12 / 0 |
  | clustered `grp:3` | T7 | 4-7 / 0 |
  | clustered `grp:3` | T8 | 10-13 / 0 |
  | clustered `grp:3` | T1.html | 31-46 / 0 |
  | clustered `grp:3` | T1.docx | 45 / 0 |
  | unclustered | every page | 0 unqualified |
  | four-case | every page | 0 unqualified |

  The new T2 and T8 legend tables carry no guidance text.
- **Ledger.** Lens 3's `p6_ledger.py` at the tip:
  - run, run, compare: 1 / 2 / 3, no W14;
  - fourth: 4, rc 2, W14;
  - five runs: W14 on 4 and 5;
  - no licence, and licence without compare: rc 4, no ledger;
  - json-only run and compare: no ledger, `ledger_count` 0;
  - limit 1 on the second run: 2, W14;
  - `compare --format json,docx --templates T2`: no ledger.
  - Unchanged from lens 3.
- **Coverage table.** `coverage_bar.py --deff-wilson --json` in `wt`: threshold 30, `elapsed 95 s`. The output equals `design/coverage_deff_wilson.json` as JSON: `identical True`.
- **Other checks.**
  - `capture_fixture_oracles.py --check`: `72 identical, 0 differ within their tolerance, 0 differ outside it`.
  - `tr39_subset.py ... --check`: `vendored subset matches`.
  - `doctor --offline`: `All essential checks passed.`.
  - `build_sample_pack.py --compare`: run.json 236,843, T1 143,196, T7 48,264, T8 35,179, compare.json 329,448, T2 70,598 bytes. These are the note's figures exactly.
  - Forbidden-word scan of the diff's added lines and of the sample-pack and clustered pages (`seamless`, `cutting-edge`, `robust`, `leverage`, `empower`, `unlock`, `revolutionis*`, `game-changing`, `AI-powered`, `!`): 0. The only "guarantee" is the pre-existing "not a guarantee".
- **Mutation (my 30, `probe/q3_mut.py`, each against `-m day11 -x` in `wt2`).**
  - 27 were killed by a behavioural test: M1-M18 and M20-M27, plus M29. M1-M18 cover MIN 5 -> 4; `<` -> `<=`; no tier; no mark; and the call removed at each of the eleven call sites (paired proportion, paired AUROC, paired calibration, subgroup proportion / AUROC / Brier, calibration bootstrap / Brier, AUROC, both `proportion_ci` routes). They also cover McNemar computed under clustering, by op and by metric; the T2 refusal and caption flag; and the T2 / T8 legends. M20-M27 and M29 include the refused cell keeping `imprecise`, the tier always added, the IPA footnote filter and the T2 p text.
  - The killing tests were `test_e11_repair3.py` (eight different tests), `test_e11_repair2.py::test_the_lens_in_route_shape_prints_the_mark` and `test_e11_deff_wilson.py::test_the_route_switches_at_five_cases...`.
  - Three survived: M19, M28 and M30 (N1-N3).
- **The repository's sweep.** SWEEP_LINE

## What I could not check

- The R 2000 / B 1000 coverage figures of lens 3 (I re-ran at R 1000, B 500 with the same seeds and obtained the note's figures, not lens 3's).
- PowerShell 5.1 runs: every figure here is from Git Bash.
- Whether a figure bar counts as a "printed interval" under DEC-75 (b): that is Josh's reading (N6).
- The DOCX forest-plot PNG labels beyond the two images I viewed (ROC legend `AUROC 0.830 [0.735, 0.936]ᶜᵈ`; calibration legend with `ᵈ` on slope and intercept).
- Linux / the reference platform.
