# Lane E - build day 11 (E11) - lens 3, regression-and-record, at `3302d59` (repair 2; base `0fa9391`; Friday 2 October 2026)

**PASS. No blockers.** Both lens-2 blockers are closed at `3302d59`, and each has a regression test that fails at `0fa9391` on an assertion, not an import abort.
- **FA-B1 = RG-B1.** I re-ran the repairer's own driver at the tip (R 2000). It printed 0 unmarked cells on 2000 of 2000 draws for each of three shapes:
  - five cases of 50 rows beside 25 one-row cases: `5x50+25x1 ... coverage 0.7615; methods {'wilson_deff': 2000}; marks {'ᵈ': 1203, 'ᶜᵈ': 797}; unmarked 0`;
  - four cases of 19 rows beside 26 one-row cases: 0.8360, `unmarked 0`;
  - 30 cases of 20 rows, TAU2 0.8, truth 0.98: 0.8125, `marks {'ᵈ': 2000}`.
- **FA-B2.** With every `FDA_AIDSF_*` row moved to 2025-02-03, T1, T7 and T8 HTML and the whole T1, T7 and T8 DOCX packages (every `.xml` part, `docProps/core.xml` included) hold no `January 2025`.

Everything the note quotes reproduces, in both shells: the suite, the seven markers, ruff, every command and every figure. There are two exceptions: one test count (N4) and the contended timings. Seven non-blocking records follow. The one to read first is N1: T2 prints `ᵈ` with no key anywhere on the page. The B1 repair touches a statistical gate's output, so DEC-12 (i) still owes it its fresh-attack lens. This note is the regression half of that lens and does not discharge it.

Setup: detached worktrees under `scratchpad/lens-E11-r3-regression/`:
- `wt3` (`3302d59`): the suite, markers, commands and sweeps;
- `wt0` (`0fa9391`): the new tests, copied in;
- `wtad` (`ad66073`): item 0's tests, copied in;
- `wtm` (`3302d59`): one planted mutant, restored.

Before any figure, `PYTHONPATH=<wt>/src python -c "import proofpack;print(proofpack.__file__)"` printed that worktree's own `src\proofpack\__init__.py`, in Git Bash and in PowerShell 5.1. `PROOFPACK_REQUIRE_DOCX=1` and `PYTHONIOENCODING=utf-8` were set on every suite run. Platform: Windows 11, CPython 3.14.6, numpy 2.5.1. A fresh-attack lens ran on the same machine at the same time, so timings are contended. I committed, pushed and paid for nothing. My one download was the Newcombe fetch that item 4's check names (three URLs, once each). This note is the only file I wrote outside the scratchpad.

## Blockers

None.

## Non-blocking

| # | Record | Evidence and one-line repro |
|---|---|---|
| N1 | **T2 prints `ᵈ` with no key anywhere on the page.** Under clustering, the per-version proportions in a compare go through `proportion_ci` and carry the flag. T2 prints it as `ᵈ`, but T2 has no tier legend; `grep -i "tier\|superscript\|half-width\|imprecise" src/proofpack/templates/T2.html` finds nothing. `ᶜ` has had the same gap on T2 since E10. The note says "a fourth legend row on T1 and T7" and nowhere says that T2 prints the mark. The mark is the B1 remedy, and on T2 a reader is not told what it means. Fix shape: a T2 legend, or the note and DEC-43 list naming the gap and carrying it. | I gave the F5 pair `case_id = c{i % 40}` and `clustering.unit: case_id`, then rendered T2: `d marks on T2: 15  a/b/c: 0 0 7`, `legend text present: False`, sample cell `41/50 (82.0%) [69.2, 90.2]ᶜᵈ`. Repro: `PYTHONPATH=wt3/src python probe/t2_clustered.py wt3 <work>` |
| N2 | **The `ᵈ` legend row cites "T7 section 6", which an unclustered T7 does not print.** The row is printed on every T1 and T7, but section 6 ("Coverage of the clustered intervals") appears only on a clustered run. The committed golden `T7.html` gains the row, and its headings run `1. … 5. Calibration`, then `7. Fairness`. | `grep -n "<h2" tests/fixtures/golden/T7.html` (no `t7-s6`), plus the golden diff line `+<tr><th scope="row">ᵈ</th><td>… (T7 section 6)</td></tr>` in `T7.html` and `T1.html`. On the lens-shape run, section 6 is present: `probe/t7s6.py` |
| N3 | **Carried row E11r2-1 does not list every clustered interval without `ᵈ`.** It names "subgroup differences, AUROC, O:E, calibration slope and intercept, T2 differences". On the lens-shape run, these also print a clustered interval with no `ᵈ`: `calibration/brier`, `brier_ref`, `intercept_large` and `ipa`, plus `subgroups/#/metrics/brier` (9 cells). T1 prints IPA's tiers (`ipa_tiers`). No cell whose id is in `fmt.PROPORTION_IDS` had an interval without the flag. | `PYTHONPATH=wt3/src python probe/unmarked.py wt3` lists `cluster_bootstrap_percentile` Numbers with an interval and no flag: `/calibration/brier`, `/calibration/brier_ref`, `/calibration/intercept`, `/calibration/intercept_large`, `/calibration/ipa`, `/calibration/oe`, `/calibration/slope`, `/overall/threshold_free/auroc`, 9 x `/subgroups/#/metrics/auroc`, 9 x `/subgroups/#/metrics/brier` |
| N4 | **The note's "fails pre-build" count is one short.** The note says `15 failed, 10 passed`. With `test_e11_repair2.py` and the tip's `test_e11_deff_wilson.py` copied into `wt0`, I measured `15 failed, 11 passed in 10.10s`, of 26 tests collected at the tip (15 in `repair2`, 11 in `deff_wilson`). The 15 failures are the ones the note names, and each first-failing line matches the note's quote. The extra pass is the tenth unchanged `deff_wilson` test. | `PYTHONPATH=wt0/src python -m pytest -q -rA tests/test_e11_repair2.py tests/test_e11_deff_wilson.py` in `wt0` |
| N5 | **No test pins which map row the Guidance status item reads.** I planted `AIDSF_STATUS_ANCHOR = "FDA_AIDSF_DATA_MGMT"` in `render/html.py` and it survived `-m "day11 or day10 or day9 or day8 or ap4"`: `1190 passed, 1 skipped`. Every moved-map test moves all twelve `FDA_AIDSF_*` rows together, and every row carries the same date today. The note's sentence ("it reads `FDA_AIDSF_PERF_VALIDATION`, and the moved-map tests feed 2025-02-03 into every `FDA_AIDSF_*` row") is accurate; the choice of row is simply not pinned. One assertion would pin it: a test that moves only `FDA_AIDSF_PERF_VALIDATION` and expects the item and the T1 `<h1>` to agree. | `wtm`, the one-line edit, the marker run, `git checkout -- src` |
| N6 | **Two existing tests were loosened, each with its reason written beside it.** `test_bootstrap_carried.py::_strip_sd` now drops the string `clustered_coverage_not_established` from every list before it compares with the `a0c9abc` snapshot. `test_e9_repair1.py::test_a_decile_bin_with_a_typed_reason_is_not_plotted` removes the flag from its planted refusal "as the engine would". Both are scoped to the one string, and no assertion line was removed anywhere in the diff (`git diff 0fa9391 3302d59 -- tests \| grep "^-\s*assert"` is empty). | the diff hunks |
| N7 | **The DEC-43 bullet's list of places that carry the flag is incomplete.** The bullet places the flag in `run.json` under "overall, subgroups, calibration decile bins". A compare's `run.json` also carries it under `comparison.prior.overall.*` (7 Numbers) and `comparison.prior.calibration.decile_curve.*` (10). | `probe/t2_clustered.py` path counts |

## What I could not break (re-measured)

**Suite and lint, at `3302d59`:**

| Run | Result |
|---|---|
| Full suite, PowerShell 5.1, `PROOFPACK_TR39_FULL` set | `1979 passed, 1 skipped, 1 xfailed in 294.29s` (the note: `1979 passed, 1 skipped, 1 xfailed`) |
| Full suite, Git Bash, no TR39 file beside the worktree | `1978 passed, 2 skipped, 1 xfailed in 298.99s`. The extra skip is `test_e8_repair4.py:405` (the full `confusables.txt` is looked for beside the repository), as lens 2 recorded |
| Markers, both shells, `PROOFPACK_TR39_FULL` set | `day11` 125, `day10` 262, `day9` 337, `day8` 471, `ap3` 176, `ap2` 91, `ap4` 197 passed: the note's figures exactly |
| `ruff check .` / `ruff format --check .`, both shells | `All checks passed!` / `290 files already formatted` |

**Fails pre-build.** At `0fa9391` (tests copied into `wt0`), all 14 non-control tests in `test_e11_repair2.py` failed, and so did `test_e11_deff_wilson.py::test_t7_prints_the_committed_table`. No failure was an import abort. First failing lines, verbatim:
- `assert 'wilson_refused_clustered' == 'clustered_co...t_established'`;
- `assert 0 == 1`, four times, once per route;
- `assert ['wilson_refused_clustered'] == ['wilson_refu..._established']`;
- `assert 'any other c...er bootstrap' not in 'Wilson scor..._ci_invalid.'`;
- `assert 'draft guidance (January 2025), not for implementation' in 'Guidance status. Every guidance reference ...'`;
- `assert ('January 2025' not in '<!DOCTYPE h...` (T1/T8, T2);
- `('January 2025' not in 'T1 · FDA AI..._MODEL_CARD]'` / `'T8 · Run ma...not recorded'`;
- `assert ['Guidance st...lementation.'] == []`;
- `AssertionError: ['declare', 'map']`;
- `assert '(lowest 0.763: 30 cases of 50 rows' in ...`.

The control test passed there, as the note says it should.

**Item 0 at `ad66073`.** I copied in the tip's `test_e11_merge_blockers.py` and `test_ap4_roundtrip.py`: `20 failed, 23 passed`. All three blockers have failing tests:
- B1: `test_compare_format_docx_without_the_extra_exits_7_...[hidden0-3]` and `test_compare_help_names_docx`;
- B2: `test_t1_criteria_cells_with_a_paired_subgroup_criterion_equal_the_html_in_the_docx`;
- B3: eight `test_run_templates_t2_names_compare_...` cases, four `test_run_templates_t2_t8_names_t8_only` cases and two `test_compare_next_step_never_names_t2_docx` cases.

The passes are the controls and the cases that were already right at `ad66073`. Lens 1's blockers stay closed under their tests: `test_e11_repair1.py` + `test_e11_merge_blockers.py` gave `33 passed` at the tip.

**Nothing weakened.**
- `git diff --name-status 0fa9391 3302d59` shows 0 `D`. The two removed `def test_` lines are the FA-N1 and FA-N2 renames.
- The only marker, skip or xfail lines added are `pytestmark = pytest.mark.day11` and one `@pytest.mark.ap4`.
- No marker was removed.
- `day11` sits beside `day10` in `pyproject.toml`. CI's day loop (`ci.yml` lines 50-66) reads every `day\d+` from that file.

**Statistical-gate hunks.** `git diff --name-status 0fa9391 3302d59 -- src/proofpack/stats/` lists two files:
- `bootstrap.py`: `replace` imported, comment text, `CLUSTERED_COVERAGE_FLAG`, `_with_clustered_coverage_mark`, and two call sites in `proportion_ci`. No interval function, constant value or route changed.
- `number.py`: one `FLAGS` entry.

Both the commit message and the note name this a statistical-gate output change owed DEC-12 (i). The schema diff is additive: one enum value and a description sentence in `output_schema_v1.json`. `egress_schema.json` has no flag field ("no flags, no ci_level, no reason text").

**Goldens.** `PROOFPACK_REGEN_GOLDEN=1 -k golden` gave `6 passed`. After LF-normalising, the SHA-256 of all five goldens (T1, T2, T7, T8, T12) equals the committed bytes, and `git diff --stat` is empty. I restored them with `git checkout`. The golden diff holds only the Guidance status item (T1, T2, T8), the `ᵈ` legend row (T1, T7) and the model-card note (T1). F17's mask is `MASKED_KEYS = ("run_id", "started", "duration_s")` (`scripts/f17_determinism.py:58`), and nothing else is masked there.

**The note's commands, both shells, at `3302d59`.** Each matches the note:

| Command | Result |
|---|---|
| `doctor --offline` | exit 0, 17 `[ok`, `All essential checks passed.`, `Next step: write criteria.yaml (...), then proofpack map --input test.csv --criteria criteria.yaml`. `map --help` accepts `--input` and `--criteria` |
| `fixtures --offline` | exit 0, `rows 46: matched 34, not matched 0, no oracle recorded 2, no independent oracle 0, not built 5, compared by the test suite only 5` |
| `capture_fixture_oracles.py --check` | `captured values: 72 identical, 0 differ within their tolerance, 0 differ outside it`, exit 0 |
| `tr39_subset.py <absolute path> --check`, run from the worktree | `vendored subset matches`, exit 0 |
| `coverage_bar.py --deff-wilson --json OUT` | threshold 30; `identical True`, and byte-identical after LF-normalising. 124 s (Git Bash), 136 s (PowerShell); the note says 114 s |
| `build_sample_pack.py --compare` | exit 0; `run.json` 236,843, T1 143,151, T7 48,219, T8 35,179, `compare.json` 329,347, T2 69,923. On T2, `SYNTHETIC - illustrative` 8 and `NO LICENCE - not for submission` 7. `January 2025` count = literal-qualifier count on T1 63/63, T2 15/15, T7 7/7, T8 15/15, and `Jan 2025` 0 |
| `f17_determinism.py --n 400 --compare` | `run exit codes [4, 4]; identical under the mask ['run_id', 'started', 'duration_s']: yes`, exit 0 |
| `test_e10_timing.py -s` | `compare --templates T2 31.38 s` (Git Bash) / `34.65 s` (PowerShell), `T2 render 0.04 s; T2 74189 bytes`, 1 passed. The note says 28.50 s; my runs were contended |
| `mutation_sweep.py --marker day11` (Git Bash) | `56 planted, 56 killed, 0 survived; 1083 s`. All six `e11r2_*` were `killed` |
| `mutation_sweep.py --marker day10` (PowerShell) | `37 planted, 37 killed, 0 survived; 1735 s`, exit 0. It ran alongside the day-11 sweep, so the time is contended |

**Figures quoted on the page and in the note, re-derived.**
- **The coverage driver at the tip.** `scratchpad/e11r2/repro_b1.py 2000` printed the note's 0.7615 (seed 7002), 0.8360 (seed 7201) and 0.8125 (seed 7101), and 0.9400 for the bootstrap shape (R 300). Every cell was marked.
- **My own simulation.** `probe/indep.py` imports no repository code. It uses the ratio-estimator design effect `K/(K-1) * sum (y_i - p m_i)^2 / n^2 / (p(1-p)/n)`, floored at 1, with `sum m_i^2 / n` at p = 0 or 1, and Wilson on `n / DEFF` with z = 1.959964. On other seeds, R 4000, it gave 0.7790, 0.8327 and 0.7965. These agree with the T7 sentence that these shapes cover below 0.90.
- **The T7 sentence's grid range** ("0.137 to 1.000"): the committed JSON's 1000 rows run from 0.13725 to 1.0.
- **The note's quoted cells.** The run quote `82.9ᵈ` and `was 228/275 (82.9%ᵈ), 95% CI 77.2% to 87.4%` is asserted by `test_a_run_on_the_lens_shape_...`. `33/37 (89.2%) [82.9, 93.8]ᵃᵈ` is present on T1 of the lens-shape run (`probe/t1cell.py`).

**The mark through every route and medium.**
- No Number whose id is in `fmt.PROPORTION_IDS` has an interval without the flag on the lens-shape run (`probe/unmarked.py`).
- `design_effect` returns `deff None` only for a single case, so the four parametrised routes cover every route that prints an interval.
- T1.docx and T7.docx of the lens-shape run carry the legend row (`T1 d count 141 legend True`, `T7 d count 8 legend True`). Rendering them recorded 0 Python warnings, so the figure PNGs drew `ᵈ` with no missing-glyph warning.
- Criteria, `run.py` and `egress/` read no flag (grep). The site imports nothing from `proofpack.scope` (`git grep` in `proofpack-site`, read only).

**The Newcombe fetch record**, fetched once each today:
- the DOI: `302` to `onlinelibrary.wiley.com/...`;
- Wiley: `403`;
- the course copy: `200`, 139,150 bytes, `%PDF-1.2`, 16 `/Type /Page` objects, SHA-256 `90a3a04944c41bebde4d92d4b9cce9c77f3b67f407433b7a103bebc35e0d0f87`.

All of this equals `fixtures/newcombe1998_paired.json` `provenance.attempts`.

**DEC-43.** In this diff, `cli.py` changes its docstring only, `run.py` is untouched, and the schema change is the one enum value. The note's list covers these, plus the doctor line, the T7 text, the legend row and the `{aidsf_draft}` slot. N7 is its one gap.

**Hard rule.** Every sentence in the diff that says what the mark or the map reading does names its input or its test:
- the `bootstrap.py` constant comment: "the tested input is one case of 7 rows", `tests/test_e11_repair2.py`;
- `html.py`'s `long_form_items` docstring: the lens's 2025-02-03 edit;
- `doctor.py`'s comment: "checks every "proofpack <word>" here against the parser's subcommands".

Each of these has a mutant that the day-11 sweep killed. T7 section 6 says "This is a measurement on the grid's shapes, not a guarantee". I found no sentence asserting a guarantee without a counter-example, so I refused none.

## What I could not check

- The CI run itself. Nothing is pushed, so neither the day loop nor the `docx-extra` job has run on `3302d59`.
- Linux and macOS. Every figure here is win-amd64-cp314.
- The DEC-12 (i) fresh-attack lens on the B1 repair. That is a separate lens, and this note does not stand in for it.
- Need 49's choice. It is Josh's: (a) the blanket mark, which is what is built; (b) a several-large-case grid family; (c) refusal.
- The Newcombe Table III transcription (17 of 18 rows). I checked the fetch record only; lens 1 FA re-read the table.
