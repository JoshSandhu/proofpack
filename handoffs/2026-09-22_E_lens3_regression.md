# Lens 3 (regression and record) - build day 8, lane E, repair 2 at `7fa690b` - 2026-09-23

**Verdict: FAIL.** Three blockers. (1) Repair 2 took out a rejection that `657ef11` had. It
replaced the substring test for `well-calibrated` with a token test, so `well-calibratedness`,
`well-calibratedly`, `well-calibrateds` and 177 more spellings that `657ef11` rejected are
now accepted. (2) Part of lens-2 FA-B2 still reproduces. Lens 2's single-field sweep counted
"18 on the criterion claims", and the same 18 are still accepted. Among them, a **met**
criterion re-labelled `CRITERION_NOT_MET_RECORD` passes, and so does the overall sensitivity
claim re-labelled `AUROC_ESTIMATE`. The rule-4 docstring's "so `AUROC_ESTIMATE` with `op1` is
refused" is false for that claim. (3) The comment in `scripts/mutation_sweep.py` and the
note both say the withdrawn mutant `checker_format_characters_kept` "became equivalent". It
did not. With it planted, `com\u00adpass` is rejected where the real code accepts it, and
`-m day8` still gives 224 passed. A DEC-12(ii) mutant was withdrawn because of a sentence
that no run tested.

Everything else the note states re-measures. Full suite `1012 passed, 1 skipped, 1 xfailed`
in both shells. Markers `day8` 224, `day7` 139, `day6` 285, `day5` 54, `day4` 182, `day3`
29 + 1 xfailed, `day2` 40, `day1` 59 + 1 skipped. `--collect-only` day1..day7 gives
60 / 40 / 30 / 182 / 54 / 285 / 139, the `7b2ca2a` counts. `ruff check` is clean and
`ruff format --check` reports 132 files. At `657ef11`, `test_e8_repair2.py` gives 7 failed
and 2 passed, each failure on an assertion. The day-8 sweep gives `41 planted, 41 killed,
0 survived`. `--list` prints 212 lines. The repaired mask's figures match numpy and
statsmodels to within 1.11e-16. Every lens-2 repro closes. Nothing in `tests/` was deleted,
no skip, xfail or `.only` was added, and no marker was removed.

Worktrees: `7fa690b` as `head`, `657ef11` as `base`, and two more `7fa690b` worktrees,
`mut` for my mutations and `sweep` for the sweep. All four sit under
`scratchpad/lens-E8-r3-regression/`. I forced `PYTHONPATH=<worktree>/src` and proved it
before every figure: `python -c "import proofpack;print(proofpack.__file__)"` printed that
worktree's own `src\proofpack\__init__.py`. All four worktrees are removed. I read the main
tree and wrote nothing there except this note.

## Blockers

### B1 - repair 2 accepts 180 `well-calibrated` spellings that `657ef11` rejected (a regression in the verdict-word rule)

At `657ef11`, `free_text_reason` rejected any text whose normalised form contained the
substring `"well-calibrated"`. Repair 2 changed that line to
`words & {"well-calibrated", "wellcalibrated"}`, a match on the whole token. Any letter
joined to the phrase now carries it past the rule:

| `free_text` | `657ef11` | `7fa690b` |
|---|---|---|
| `well-calibratedness` | `free_text_verdict_word` | `None` (accepted) |
| `well-calibratedly` | `free_text_verdict_word` | `None` |
| `well-calibrateds` | `free_text_verdict_word` | `None` |
| `xwell-calibrated` | `free_text_verdict_word` | `None` |
| `unwell-calibratedness` | `free_text_verdict_word` | `None` |

Differential fuzz (`probe/fz.py`, run once in each worktree and the JSON dumps compared).
Input: every listed word from `VERDICT_WORDS`, `CERTIFICATION_WORDS` and `well-calibrated`,
each with ten prefixes and ten suffixes, seven attached tails, and eleven separators at
every internal position. Each spelling ran bare and inside "The model was {} here.", which
gives 18,752 texts. **180 were rejected at `657ef11` and are accepted at `7fa690b`.** Every
one is `well-calibrated` with an attached prefix or suffix. 5,338 texts were accepted at
`657ef11` and are rejected at `7fa690b` (see N5). Lenses 1 and 2 graded the class "a
spelling of a listed word accepted by `free_text`" as a blocker. Here that class opens
through a rule the repair rewrote, and no test pins the substring case.
`tests/test_e8_repair2.py` feeds `well-cali-brated` and 14 spaced letters. It feeds no
suffix.

Repro (worktree root, PYTHONPATH forced):
`python -c "from proofpack.narrate.checker import free_text_reason as f;print(f('well-calibratedness'),f('well-calibratedly'))"`.
At `7fa690b` it prints `None None`. At `657ef11` it prints
`free_text_verdict_word free_text_verdict_word`.

### B2 - lens-2 FA-B2's 18 accepted criterion-claim mutations still reproduce; a met criterion passes the checker as "Record of criterion not met", and a sensitivity claim passes as `AUROC_ESTIMATE`

I re-ran lens 2's `b_checker.py` unchanged against `7fa690b` (`LENS_WT` set to the `head`
worktree). The B5 section is now closed: `swaps: 42849 accepted: 0`, where lens 2 had
13,962. The B4 single-field mutations give `mutations: 8988 accepted: 39`, where lens 2 had
685:

- `('CRITERION_STATUS', 'template_id'): 18`: every criterion claim re-labelled to
  `CRITERION_NOT_MET_RECORD` or to `ATTAINABILITY_NOTE`. This is exactly the "18 on the
  criterion claims" in lens 2's FA-B2. Repair 2 put these two templates inside
  `BOUND_TEMPLATES` and added no rule that ties the template to the row's status.
- `('OVERALL_ESTIMATE', 'template_id'): 13` and `('AUROC_ESTIMATE', 'template_id'): 1`: the
  13 overall claims re-labelled `AUROC_ESTIMATE`, and the AUROC claim re-labelled
  `OVERALL_ESTIMATE`.
- `('CALIB_HIERARCHY', 'metric_id'): 4` and `('FAIRNESS_GAP', 'metric_id'): 3`: swaps inside
  one metric family. The template prints the whole family, so I record these and do not
  grade them.

Measured directly (`probe/tmpl.py`, synthetic document, 70 engine claims):

- `CL-0062` (`C_met`, status `met`) with `template_id` set to `CRITERION_NOT_MET_RECORD`:
  **ACCEPTED**. That skeleton reads "Record of criterion not met: {criterion_id}, ...". The
  same holds for `CL-0067` (`C_auroc`, `met`) and for every `not_assessable` row. A status
  word can therefore contradict `criteria_results` and still pass the checker. E7's
  decision table says a criteria row's status comes "from the three-word enum only".
- `CL-0001` (`OVERALL_ESTIMATE`, `sensitivity`, `op1`, `/overall/op1/sensitivity`, est
  `0.75`) with `template_id` set to `AUROC_ESTIMATE`: **ACCEPTED**. That skeleton reads
  "AUROC was {est} ...", so the sentence would print the sensitivity 0.75 as the AUROC. The
  document's AUROC is `0.8353343290441176`. This is lens-1 B1's class: a correct number
  attached to the wrong metric.
- Sentence violation (`checker.py`, the rule-4 docstring): "every pointer's operating point
  equals the claim's - null equals null, so `AUROC_ESTIMATE` with `op1` is refused". The
  counter-example is the `CL-0001` re-label above: an `AUROC_ESTIMATE` claim with
  `operating_point op1`, accepted. The test feeds only `CL-0014` with its operating point
  changed.

Reachability. No page is wrong today: T8 prints no claim sentence, and E8 has no code that
fills a skeleton. Lens 2 graded FA-B2 as a blocker on the same terms, because the checker is
the only gate between a re-ordered claim list and E9's sentences. The note does not list
the 18 as open or carried.

Repro (from `tests/`, PYTHONPATH forced): build the synthetic document as
`test_e8_repair2.py`'s `document` fixture does, then
`c = copy.deepcopy(claims.build_claims(d)[61]); c["template_id"] = "CRITERION_NOT_MET_RECORD"; print(c["status"], checker.check([c], d).verdicts[0].accepted)`.
It prints `met True`.

### B3 - the withdrawn sweep mutant `checker_format_characters_kept` is not equivalent; the committed comment and the note say it is

The `scripts/mutation_sweep.py` comment reads: "a kept Mn / Cf character only splits a word
into more tokens ... the mutant became equivalent (it survived at repair 2)". The note item
3 reads: "`checker_format_characters_kept` **survived** and is equivalent after repair 2."
No run in the note tests "equivalent". I planted the mutant in `mut`, replacing
`if unicodedata.category(ch) in ("Mn", "Cf"):` with `if False:`:

- `python -m pytest -m day8`: `224 passed, 790 deselected`. The mutant survives, as the note
  says.
- `free_text_reason("com\u00adpass")` (compass with a soft hyphen): real code `None`, mutant
  `free_text_verdict_word`. `pass\u200dport` and `tres\u00adpass` behave the same way. The
  two versions differ on these inputs, so the mutant is not equivalent. A one-line test
  asserting `None` for `com\u00adpass` kills it.

The note's reasoning holds for rejections: a kept character cannot hide a listed word of at
most 14 letters. It does not hold for acceptances. So after the withdrawal, no test and no
mutant pins the step "drop Mn and Cf". DEC-12(ii) asks for the sweep to be committed and
run. This is a hard-rule sentence in shipped code, it was never tested, and a counter-example
refutes it.

Repro (in a scratch worktree): plant the replacement above, run
`python -c "from proofpack.narrate.checker import free_text_reason as f;print(f('com\u00adpass'))"`.
It prints `free_text_verdict_word` (real code: `None`). Then run
`python -m pytest -q -m day8`, which gives `224 passed`.

## Non-blocking

**N1 - The S4 list leaves out one output change: `flow.indeterminate` now counts a `y_pred`
holding a declared indeterminate value on tables *with* a score column too, and those rows
leave every score statistic.** Measured (`probe/gate.py` P3): 120 rows with a score column,
`y_pred = "indeterminate"` on 12 rows, `indeterminates.values ["indeterminate"]`. At
`657ef11` the result was `indeterminate 0`, `analysed 120` and two-by-two
`{tp 34, fn 8, fp 20, tn 58}`. At `7fa690b` it is `indeterminate 12`, `analysed 108` and
`{tp 34, fn 7, fp 17, tn 50}`. The behaviour follows `schema_v1.json` ("an alternative to
listing indeterminate values in y_true / y_pred"). The README's sentence is unscoped and
true. Two gaps remain. First, the note's "CLI / output changes S4 must know" names only
`excluded_missing_score`. Second, the test feeds the no-score table only, so the score-table
case is not pinned. The case also cuts against the README's "beside a score column the
score is the input": that holds for a blank `y_pred` and fails for an indeterminate one.
Whether a y_pred-indeterminate row with a valid score should leave AUROC and calibration is
for Josh to decide.

**N2 - The pre-fix figures and their artefact disagree by one.** The note says "26 failed
and 136 passed" for the repairer's three files. `scratchpad/repair-E8-r2/prefix_tb.txt`
ends `25 failed, 137 passed in 4.45s`. I ran the three committed files plus the 16 corpus
changes in `base` and got `27 failed, 137 passed in 4.64s`. That equals the note's 26/136
plus the orchestrator's two tests, one of which fails at `657ef11` and one of which passes.
So the note's figure is consistent, and the artefact it cites is an earlier state.

**N3 - Sentences (recorded, not graded).**
- Corpus `129`'s `rule` says "every run of consecutive tokens is joined". The code joins runs
  of two to 14 tokens.
- A `test_free_text_...` comment reads "`w e l l c a l i b r a t e d`: fourteen single
  letters: the longest run joined". With `_JOIN_RUN = 13` planted, `-m day8` gives
  `224 passed` (measured), so the literal does not pin 14: `calibrated` is itself listed.
  The note says so in item 3. The comment still suggests the literal pins 14.

**N4 - Docstrings.** The docstrings of `_tokens` and `_words` cite lens ids and name no
D1 section 4.4 line. `test_the_lens_b2_literal_claims_are_rejected_with_the_named_code` and
`test_free_text_separated_control_and_small_capital_spellings_are_rejected` have no
docstring. The other new docstrings name their test ids or measured literals.

**N5 - The join rule rejects ordinary prose.** "Specificity was reported in significant
detail." gives `free_text_verdict_word`, because `in` + `significant` joins to
`insignificant`. The fuzz in B1 found 5,338 texts that `657ef11` accepted and `7fa690b`
rejects. These rejections err on the side of refusing, and no engine claim carries
`free_text` today. E9's narrative will meet them.

**N6 - The carried observation, confirmed.** A `FLOW_COUNTS` claim that keeps
`subgroup {age, 40-65}` and states `not_assessable` over `/flow/analysed` is **accepted**. So
is a `FLOW_COUNTS` claim that keeps `metric_id sensitivity`, `op1` and
`guidance_ref FDA_AIDSF_PERF_VALIDATION`. `test_a_claim_bound_to_a_documented_scalar_must_state_not_assessable`
asserts the second one as accepted.

**N7 - The golden's mask is `manifest.numpy` only** (lens 2's N9 stands). An unmasked render
differs in one line (`x.y.z` against `2.5.1`). `run_id` (`test-only-assembler`), `started`
(`2026-09-18T00:00:00Z`) and `duration_s` (`None`) are constants of the assembler, not masks.

**N8 - The note gives no command for `doctor`.** `python -m proofpack doctor --offline`
fails in Git Bash with `No module named proofpack.__main__`. `python -m proofpack.cli doctor
--offline` exits 0 in both shells, prints 17 `[ok  ]` lines, and ends `All essential checks
passed.` The two shells' outputs are equal apart from the home path and PowerShell's BOM.

**N9 - The old day-7 file fails in four tests on the tip, not one.** I ran
`git show 7b2ca2a:tests/test_run_cli.py` against `7fa690b`: `4 failed, 19 passed`. The
failures are the clustered test (`assert {...} is None`), the y_pred-only test, and two that
E8 changed at `ee295cc`: `guidance_refs == []` became "claims present", and the status-word
walk now excludes `claims`. The committed diff for each is shown by
`git diff 7b2ca2a 7fa690b -- tests/test_run_cli.py`, and each change carries an E8 comment.

## What I could not break

- **The suite and the markers, both shells.** Git Bash gives
  `1012 passed, 1 skipped, 1 xfailed in 104.95s`. PowerShell 5.1 gives
  `1012 passed, 1 skipped, 1 xfailed in 67.74s`. The skip is `test_doctor_cli.py:57`; the
  xfail is `test_f13_matches_proc_on_the_asah_dataset`. Git Bash markers: day1 `59 passed,
  1 skipped`, day2 40, day3 `29 passed, 1 xfailed`, day4 182, day5 54, day6 285, day7 139,
  day8 224. PowerShell markers: day5 54, day6 285, day7 139, day8 224. `--collect-only`:
  60 / 40 / 30 / 182 / 54 / 285 / 139 / 224 of 1,014. `ruff check`: `All checks passed!` and
  `ruff format --check`: `132 files already formatted`, in both shells. `day8` is declared at
  `pyproject.toml` line 82. `ci.yml` reads the marker list out of `pyproject.toml` and runs
  `uv sync --all-groups --locked` (lines 25 and 74). `uv.lock` carries `name = "jinja2"`
  (line 497) and `{ name = "jinja2" }` (line 955).
- **Nothing weakened in `tests/`.** `git diff --name-status 657ef11 7fa690b -- tests/`
  shows 16 `A` and 4 `M`, and no `D`. Grepping the diff for added or removed
  skip / xfail / `.only` / todo / `pytest.mark` lines finds one line, the new file's
  `pytestmark = pytest.mark.day8`. Three existing expectations changed, each with a comment
  naming the rule order: corpus `103`, `test_e8_repair1` case 11, and the malformed-document
  test. I removed `fairness = fairness if isinstance(fairness, dict) else {}` from `mut`: the
  new sub-case fails with `AttributeError: 'str' object has no attribute 'get'`, so the guard
  is still pinned.
- **Fails pre-build.** All 20 changed test paths copied into `base` (`657ef11`):
  `test_e8_repair2.py` gives `7 failed, 2 passed`. The two that pass are
  `test_h02_on_y_pred_fires_beside_a_score_column` and
  `test_a_claim_bound_to_a_documented_scalar_must_state_not_assessable`, the ones the note
  names. The first E lines are all assertions: `assert (0 == 60)`, `assert (0 == 12)`,
  `assert [('CL-0001', ...alytic'), ...] == []`, `(... 'SUBGROUP_ESTIMATE' ...,
  'value_ref_unbound')`, `assert 'No acceptan...ere declared' not in ...`,
  `AssertionError: 'p a s s'`, `AssertionError: miscalibrated`. Corpus `116`-`122`, `124`-`130`
  give `('<file>', 'accepted')`. `123` and `103` give `relation_mismatch` (at `657ef11` rule 5
  refused them). The count test gives `assert (42 == 43)`.
- **The corpus.** `tests/fixtures/claims_corpus` holds 130 entries, all `.json`, and every
  file has `rule` and `expected_reason_code`. `CORPUS_FILES = sorted(CORPUS.glob("*.json"))`,
  and the parametrised test collects `130 tests`. Files `116`-`130` each name the lens id and
  the code in their `rule`.
- **The sweep** (`sweep` worktree): `41 planted, 41 killed, 0 survived; 303 s`, `exit 0`,
  tree clean after. `--list` prints 212 lines in both shells: 34 day5, 112 day6, 25 day7,
  41 day8, no duplicate ids. The two retargeted repair-1 mutants and the 13 new ones are each
  `killed`. `_JOIN_RUN = 13` survives `-m day8` (`224 passed`), as the note records.
- **The repaired mask (the statistical gate DEC-12(i) names), re-derived with my own numpy
  counts and statsmodels.** Case: 120 rows, no score column, 60 blank `y_pred`. Engine flow
  `excluded_missing_score 60`, `analysed 60`, and the identity rows_read = dev +
  missing_label + missing_score + indeterminate + analysed holds. Two-by-two
  `{tp 21, fn 3, fp 7, tn 29}` equals my count on the non-blank rows. Sensitivity 21/24
  Wilson `(0.6899611872949992, 0.9565566591987656)` against statsmodels
  `proportion_confint(method="wilson")`: deviation `0.00e+00` on both ends. Specificity
  29/36, PPV 21/28, NPV 29/32 and accuracy 50/60: estimate deviation `0.00e+00`, CI deviation
  at most `1.11e-16`. At `657ef11` the same table gives `{tp 21, fn 21, fp 7, tn 71}`, and
  the sensitivity CI is off by 0.335 / 0.312. That is the defect, and it is now gone.
  Blank `y_pred` and blank `y_true` on the same 12 rows: counted
  `excluded_missing_label 12`, `excluded_missing_score 0` at both commits. Clustered
  y_pred-only table, 200 rows in 100 two-row cases, 40 blanks: `excluded_missing_score 40`,
  `analysed 160`, `n_cases 100`, two-by-two equal to my count,
  `cluster_bootstrap_percentile`. `git diff 657ef11 7fa690b -- src/proofpack/stats/` is empty.
- **The lens-2 repros, on lens 2's own scripts against the tip.** `a_overall.py` A1
  (clustered, 300 rows): six pooled ratios at deviation `0.00e+00`, and `proportion_ci`
  equal to the block on five. A5 (12 blank `y_pred`): `excluded_missing_score 12`,
  `analysed 108`, two-by-two equal to the non-blank count. A9 (blank beside a score):
  unchanged. `d2_followup.py` D9b (FA-B1 through the CLI): `18 / 22 est 0.8182`, page cell
  `18/22 (81.8%) [61.5, 92.7]ᵇᶜ`. `d_wiring.py` D10 (FA-B3): "No acceptance criteria were
  declared" present `False`, criterion rows 1, section-7 not_met 1. D1 to D8 and D11: the
  figures lens 2 lists, including `T8.html` 40,145 bytes, 70 claims, 0 rejections,
  `declaration_index [0, 1, 2, 2, 2, 3, 4, 5, None]`, no CRLF and no BOM, grace watermark
  ×7, exit 4 with JSON only past grace and with no file, `--offline` 0 socket calls.
  RG-B2's repro: `free_text_verdict_word` ×3. FA-B4's repro: ×3. `b_checker.py` B1: every
  spelling lens 2 rejected or accepted gives the same result. The exception is `p a s s`,
  now rejected.
- **The golden.** Rendered in `head` with `numpy` masked: 39,800 bytes against the committed
  39,800 LF bytes, `equal True`. The file is `i/lf w/lf` in the main tree.
- **Footer removed** (the `<footer ...>` line of `page_footer` in
  `src/proofpack/templates/base.html` emptied in `mut`): `4 failed, 1 passed`, on
  `assert 0 == 3`, `assert 0 == 1`, `assert 0 == 2`, `assert (0 == 3)`.
- **The draft label removed**, tried two ways. First: `label_for` returning `document` alone.
  `test_every_fda_aidsf_anchor_carries_the_draft_label_in_data_and_on_the_page` fails with
  `AssertionError: {'id': 'FDA_AIDSF_PERF_VALIDATION', 'label': 'FDA draft guidance, ...
  (Docket FDA-2024-D-4488)', 'draft': True, 'url': None}`. Second: the CSV row's status
  changed to `draft`. The test ERRORs with `AnchorError: guidance map row
  'FDA_AIDSF_PERF_VALIDATION' is a draft without the 'not for implementation' qualifier ...;
  refusing to render`.
- **The wheel.** The committed test passes: `1 passed in 2.19s`. The wheel lists all seven
  `_schema` files including `tokens.json` (4,903 bytes) and the three templates. I installed
  it by hand into a fresh `python -m venv --without-pip`. `Lib/site-packages` holds `bin`,
  `proofpack` and `proofpack-0.1.0.dev1.dist-info`, and there are 0 `.pth` files in the venv.
  With `PYTHONPATH` unset and `PYTHONNOUSERSITE=1`, `proofpack.__file__` and
  `resource_path("tokens.json")` print `...\venv\Lib\site-packages\proofpack\...`, with
  `site.ENABLE_USER_SITE False`. With the user site on, `proofpack.__file__` is still the
  venv's. I then removed the line `"design/tokens.json" = "proofpack/_schema/tokens.json"`
  from `pyproject.toml` in `mut`. The committed test fails with `FileNotFoundError: packaged
  resource 'tokens.json' not found` and `assert 1 == 0`.
- **tokens.json against D5 section 3.1.** My parser reads the nine table rows. All 19 names
  and hex values are equal and 0 differ. My WCAG recomputation equals every
  `contrast_computed` (16.46, 7.09, 4.57, 1.34, 9.97, 11.69, 6.80, 10.02, 9.11). The three
  D5-stated ratios that differ (6.2, 8.7, 7.9) are recorded in the file's `source` string.
  The file is unchanged since `a2246c1`.
- **Imports with dependencies hidden.** I set 13 names to `None` in `sys.modules`: `jinja2`,
  `markupsafe`, `scipy`, `scipy.stats`, `scipy.special`, six `cryptography` modules,
  `statsmodels`, `sklearn`. Then `proofpack`, `.stats`, `.narrate.checker`,
  `.narrate.claims`, `.render.format`, `.render.html`, `.io.schema`, `.gates`, `.run` and
  `.cli` all import, and none of the hidden modules is loaded. `environment()` raises
  `RendererUnavailable the HTML renderer needs the package 'jinja2' ...`.
- **The S4 list against the diff.** `cli.py` and `run.py` are not in
  `git diff --stat 657ef11 7fa690b`. The schema changes are the three the note lists: the
  `excluded_missing_score` description, `value_ref_unbound` in the enum, and the `y_pred`
  description. `errors.py` changes `HALT_CODES["H02"]` text only. `html.py` changes
  `has_criteria`, a page change on fairness-only criteria that the Landed table names. The
  one omission is N1.

## What I could not check

- CI on ubuntu / Python 3.12: the engine is not pushed.
- The sweep in PowerShell: I ran it in Git Bash only, which is the shell the note used.
- Lens 1's own attack scripts, unchanged: I re-ran lens 2's, which include lens 1's literal
  cases (the B1 spellings, D9 `yes`/`no`, D12 authors).
- A real-licence HTML from the plain CLI: no signing key on this machine. The HTML path ran
  through `main(..., registry=ephemeral_registry())`.
- Whether an indeterminate `y_pred` beside a valid score should leave the analysis (N1), and
  whether the checker should tie a template to its metric and to its row's status (B2).
  Those are rule decisions. What I measured is what is accepted today.

## Sentences I refused to write

- "Repair 2 closes the free_text evasions." Refused: B1 is a regression the repair
  introduced.
- "The checker binds every claim to its Number." Refused: B2. Written instead: 42,849 swaps
  and 0 accepted; 8,988 single-field mutations and 39 accepted.
- "The sweep kills every non-equivalent mutant." Refused: B3.
- "The blank-y_pred repair is correct." Written instead: one 120-row table and one 200-row
  clustered table re-derived, deviations 0 to 1.11e-16.
- "The S4 list is complete." Refused: N1.

## Re-run these

```bash
S=<scratchpad>/lens-E8-r3-regression
git -C C:/Users/joshs/GPS/ProofPack/proofpack worktree add --detach $S/head 7fa690b
git -C C:/Users/joshs/GPS/ProofPack/proofpack worktree add --detach $S/base 657ef11
cd $S/head && PYTHONPATH=$S/head/src python -c "import proofpack;print(proofpack.__file__)"
PYTHONPATH=$S/head/src python -m pytest -q -p no:cacheprovider            # 1012 passed, 1 skipped, 1 xfailed
PYTHONPATH=$S/head/src python -m pytest -q -p no:cacheprovider -m day8    # 224 passed
PYTHONPATH=$S/head/src python -m proofpack.cli doctor --offline           # exit 0 (not python -m proofpack)
# B1: prints None None at 7fa690b; free_text_verdict_word x2 at 657ef11
PYTHONPATH=$S/head/src python -c "from proofpack.narrate.checker import free_text_reason as f;print(f('well-calibratedness'),f('well-calibratedly'))"
# B2: $S/probe/tmpl.py  (LENS_WT=$S/head)  -> CL-0062 met -> NOT_MET_RECORD: ACCEPTED; sensitivity as AUROC_ESTIMATE: ACCEPTED
# B3: plant 'if False:' for the Mn/Cf line in a scratch worktree; f('com\u00adpass') -> free_text_verdict_word; -m day8 224 passed
PYTHONPATH=$S/head/src python scripts/mutation_sweep.py --marker day8     # 41 planted, 41 killed, 0 survived (in its own worktree)
git -C C:/Users/joshs/GPS/ProofPack/proofpack worktree remove --force $S/head
git -C C:/Users/joshs/GPS/ProofPack/proofpack worktree remove --force $S/base
```

## What the repair needs

B1: bring back a rejection for the phrase whether or not letters touch it: the substring
test beside the token test. Add a test with `well-calibratedness`, `well-calibratedly` and
`xwell-calibrated`. B2: a rule that refuses `CRITERION_NOT_MET_RECORD` unless the row's
status is `not_met`, and a rule that ties `AUROC_ESTIMATE` to `metric_id auroc` and
`OVERALL_ESTIMATE` to a metric other than `auroc`. Add corpus cases for the `CL-0062` and
`CL-0001` re-labels, and correct the rule-4 docstring sentence. B3: restore
`checker_format_characters_kept`, add a test asserting `free_text_reason("com\u00adpass") is
None`, and replace the "equivalent" sentence in `scripts/mutation_sweep.py`. B1 touches the
verdict-word gate, so the repair is lensed again.
