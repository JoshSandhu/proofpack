# Lens 2 (regression and record) - build day 8, lane E, repair 1 at `657ef11` - 2026-09-23

**Verdict: FAIL.** Two blockers, both found by the DEC-12(i) fresh-attack pass on the two
repaired gates (H02 on `y_pred`; the free_text word rule), neither in the note. Everything
the note states re-measures: `988 passed, 1 skipped, 1 xfailed` in both shells; `-m day8`
200, `day7` 139, `day6` 285, `day5` 54, `day4` 182, `day3` 29 + 1 xfailed, `day2` 40, `day1`
59 + 1 skipped; `--collect-only` day1..day7 = 60 / 40 / 30 / 182 / 54 / 285 / 139, the seven
counts of `7b2ca2a`, and day8 200 of 990; ruff clean; the 42 pre-fix failures at `29fc04e`
each on the line the note quotes; the day-8 sweep `28 planted, 28 killed, 0 survived; 177 s`
and the day-7 sweep `25 planted, 25 killed, 0 survived; 164 s`; the corpus 115 files, all
115 loaded, 42 of 42 codes covered; the golden 39,800 bytes LF, regenerated equal; tokens
equal to D5 section 3.1; the wheel test fails with the force-include line removed; the
footer and anchor tests fail with the footer emptied and the qualifier removed; nothing in
`tests/` deleted, no marker removed, no skip/xfail added; the five lens-1 blockers closed on
the lens-1 scripts re-run against the tip. Below that: twelve non-blocking items, three of
them sentences.

Worktrees: `657ef11` (`tip`), `29fc04e` (`base`), a second `657ef11` for the sweeps
(`sweep`) under `scratchpad/lens-E8-r2-regression/`, and a fourth `657ef11` at
`scratchpad/lens-E8-r1-fresh-attack/eng-attack` so the lens-1 attack scripts ran unchanged
against the tip; `PYTHONPATH=<worktree>/src` forced and `python -c "import proofpack;print(
proofpack.__file__)"` printed that worktree's own `src\proofpack\__init__.py` before every
figure. Without `PYTHONPATH` the same command prints the main tree (`C:\Users\joshs\GPS\
ProofPack\proofpack\src\proofpack\__init__.py`, from the `.pth`), as the task warns. All four
worktrees removed. The main tree was read only; this note is the one file I wrote there (the
two untracked `2026-09-22_A_ap2_lens2_*.md` notes are lane A's).

## Blockers

### B1 - a blank `y_pred` passes H02 and is counted as "predicted negative": 60 empty predictions in 120 rows give exit 0, `halts []`, `warnings []`, and `21/42 (50.0%) [35.5, 64.5]ᶜ` on the page

The repaired gate reads `y_pred` through `observed = {v for v in values.tolist() if v is
not None}` (`gates.py` line 57): an empty cell is `None` after ingest and is skipped. On a
y_pred-only table `overall_block` then computes `pred = (y_pred == positive)`, so every
missing prediction is a negative prediction. Measured through the CLI (the path the repair
test takes: `cli.main(["run", ..., "--offline"], registry=ephemeral_registry())`, own
`PROOFPACK_HOME`, `make_cohort(n=120, with_y_pred=True)` with the score column deleted):

| table | exit | `flow` | `two_by_two` | sensitivity on the page |
|---|---|---|---|---|
| 60 of 120 `y_pred` cells empty | 0, `T8.html` written | `analysed 120 of 120`, `excluded_missing_label 0`, `halts []`, `warnings []` | `{tp 21, fn 21, fp 7, tn 71}` | `21/42 (50.0%) [35.5, 64.5]ᶜ`, `C1 not_met` |
| every `y_pred` cell empty | 0, `T8.html` written | the same, nothing excluded, nothing warned | `{tp 0, fn 42, fp 0, tn 78}` | `0/42 (0.0%) [0.0, 8.4]`, `C1 not_met` |
| 60 of 120 `y_true` cells empty (control) | 2 | `analysed 60 of 120`, `excluded_missing_label 60`, W10 | `{tp 21, fn 3, fp 7, tn 29}` | `21/24 (87.5%) [69.0, 95.7]ᵇᶜ` |
| score present, 60 of 120 `y_pred` empty | 0 | nothing excluded, nothing warned; the two-by-two comes from the score, the blanks are neither H04-checked nor reported | `{tp 34, fn 8, fp 20, tn 58}` | `34/42 (81.0%)` |

The `y_true` row shows the engine has a typed path for a missing label (excluded and
counted in `flow`); a missing prediction has none. This is lens-1 B3's shape (a wrong number
and a wrong status reach the page from a table that should HALT or at least flag) through
a blank instead of a foreign label, on the gate the repair touched. The repair's own
sentences are false for it: `HALT_CODES["H02"]` "y_true or y_pred values not a subset of
declared classes and indeterminate values" (a blank is not in that set and does not halt);
the README "a `y_pred` column holding a value outside `classes.positive`, `classes.negative`
and `indeterminates.values` halts H02"; `schema_v1.json`'s "Values must be a subset of
declared classes.positive ∪ classes.negative ∪ indeterminates.values, else H02". The
schema types `y_pred` as `["string", "integer", "null"]` and D1 section 2's row says "int or
string | optional" with no null semantics, so whether a blank should HALT, be excluded like
a missing label, or be an indeterminate is a decision - but silently counting it as a
negative prediction is none of the three. The class is older than E8 (the day-4 subgroup
route does the same); E8 and this repair are where it reaches `overall`, the criteria table
and T8 with a gate that claims to cover the column.

Repro (worktree root, PYTHONPATH forced, from `tests/`): build `make_cohort(n=120,
with_y_pred=True)`, `del cols["score"]`, set `cols["y_pred"][i] = ""` for every even `i`,
write it with `_prepare`, run `cli.main(["run", "--input", csv, "--criteria", yml, "--out",
out, "--offline"], registry=ephemeral_registry())` → `0`; `run.json` `overall.op1.two_by_two
== {'fn': 21, 'fp': 7, 'tn': 71, 'tp': 21}`, `flow.excluded_missing_label == 0`, `halts ==
[]`, `warnings == []`.

### B2 - the free_text word rule is evaded by a C0 control character inside the word and by small-capital letters: `pa\x01ss`, `pa\x1fss`, `pa\x7fss`, `pa\x85ss` and `ᴘᴀss` are accepted

`normalise_free_text` drops `Mn` and `Cf`; a `Cc` character (U+0001, U+001F, U+007F, U+0085)
is kept and, being outside `[a-z\-]`, splits the word: `free_text_reason("pa\x01ss")` is
`None` (measured; `"pa\x00ss"` likewise). Small capitals U+1D18 (ᴘ) and U+1D00 (ᴀ) are `Ll`
letters absent from the 27-entry `CONFUSABLES` map: `free_text_reason("ᴘᴀss")` is `None`.
Same class as lens-1 B2 (an invisible or look-alike character inside a listed word), graded
by the same rule (the checker is the only gate a re-orderer faces); no engine claim carries
`free_text` today, so no page is affected. What the repair does reject, measured here:
U+200B, U+2060, U+180E (`Cf`), U+200F, U+FEFF, the combining long stroke U+0335 and the
combining solidus U+0338, mathematical bold `𝐩𝐚𝐬𝐬`, Greek `ρass`, `ⓟass`, mixed Cyrillic
`pаѕѕ`, `faíl`, `(fail)`, `fail.`, `passes`, `un_biased`. Accepted and not graded: `p@ss`,
`pas s`, `p-a-s-s`, `pa\u2009ss` (a thin space is a space), `wellcalibrated` (not a listed
word).

Repro: `python -c "from proofpack.narrate.checker import free_text_reason as f;
print(f('pa\x01ss'), f('pa\x7fss'), f('\u1d18\u1d00ss'))"` → `None None None`.

## Non-blocking

**N1 - Sentence. `tests/test_e8_repair1.py` module docstring: "every one failed in a worktree
at 29fc04e with PYTHONPATH forced".** `test_the_clustered_overall_prevalence_is_the_pooled_
positive_share` passes at `29fc04e` (`1 passed in 0.74s`, measured in the base worktree),
which the note itself says ("This test does **not** fail at `29fc04e`"). The docstring
generalises over the file's ten tests; nine failed. One word to fix.

**N2 - Sentence. README and `gate_h02` docstring: H02 on `y_pred` fires "before any
statistic, with or without a score column".** The note's counter-example runs are the
no-score table only; the with-score case was not run on record. I ran it: score present,
`y_pred` `yes` / `no` beside classes `1` / `0`, through the CLI → `exit 3`, `HALT H02: y_pred
contains value(s) outside declared classes and indeterminate values`, no directory; `ingest`
calls the gates in the order `h02, h03, h05, h06, h01, h04, h10`, so "before any statistic"
holds. The sentence is true for a foreign label and false for a blank (B1); it should name
the two tables run.

**N3 - `test_declared_values_print_every_digit` fails at `29fc04e` on `AttributeError: module
'proofpack.render.format' has no attribute 'declared'`** - an abort, not an assertion, so
that test pins the function's existence, not its digits. The behaviour is pinned by
`test_declared_numbers_print_every_digit_on_the_page`, which fails at `29fc04e` on
`AssertionError: threshold 0.4275 rule` (measured), and by the golden. The note quotes the
abort honestly. Record, not a defect.

**N4 - `test_two_criteria_sharing_an_id_print_their_own_author_and_justification` fails at
`29fc04e` on its first line (`KeyError: 'declaration_index'`)**, before the author assertion.
I ran the author assertion alone at `29fc04e`: both rows print `Author One · 2026-01-01;
Author Two · 2026-02-02` and `first justification / second justification`, so the
behavioural line fails there too. Record, not a defect.

**N5 - Docstrings.** `_number_or_none`, `_authored` and `_justification` (new or rewritten)
carry no docstring; `gate_h02` and `format.declared` cite the lens id and the test, not a
D1 / D4 line - because none exists: D1 section 5.6's H02 row still reads `y_true` only
(needs-from-Josh 1 of the note) and D4 section 1.2 has no rule for a declared value. The
checker's new rules 4, 6, 7, 8 and 10 name their test ids and corpus files.

**N6 - `guidance_ref` swapped to any map row is accepted on all 70 engine claims** (the
lens-1 `b_checker.py` B3 section re-run against the tip: `total accepted mutations: 70`,
every one `guidance_ref` → `FDA_STAT2007_CI`). Carried by the note as specified (FA-N4); the
number is stated here so the next lens does not re-count it.

**N7 - The free_text words D1 section 4.4 does not list are still accepted**: `ninety`, `IV`,
`percent`, `&sect;`, `guidances`, `C.F.R.`, `21CFR`, `FDAcleared`, `noninferiority`,
`unsafe`, `safely`, `accepted`, `acceptably`, `biases`, `calibration`, `p a s s` spaced
(the lens-1 script's `[!!]` lines against the tip). FA-N3, needs-from-Josh 2; recorded.

**N8 - `ruff format --check` counts differ**: 129 files in the clean `657ef11` worktree, 130
in the note, 131 in the main tree (the main tree's extra files are outside git; `ruff check`
and `ruff format --check` pass in all three). RG-N12 recorded the same drift at E8.

**N9 - The golden's mask is `manifest.numpy` alone** (RG-N10 stands): an unmasked render
differs from the masked one in exactly one line (`<tr><th scope="row">numpy</th><td
class="mono">2.5.1</td></tr>` → `x.y.z`); `run_id` (`test-only-assembler`), `started`
(`2026-09-18T00:00:00Z`) and `duration_s` (`None`) are assembler constants. The task's
"masking touches only run_id, started and duration_s" is the brief's wording, not the
test's; the golden's 14 changed lines are the `.customer-text` CSS line, the three T1-1
declaration rows (`0.500` → `0.5`, `0.300` → `0.3`, `0.100` → `0.1`), the caption and nine
Value cells - exactly as the note says.

**N10 - The wheel test's `pytest.skip` path (RG-N13) is unchanged**; carried by the note.
On this machine the test ran (`1 passed in 1.96s`).

**N11 - Two-shell figures.** The note gives `run.json` 253,943 bytes (Bash) / 253,942
(PowerShell); I measured 253,943 in both shells (the `duration_s` digits vary run to run).
Not a defect.

**N12 - The sweep's day-6 count.** `--list` prints 199 lines: 34 day5, 112 day6, 25 day7,
28 day8, 0 duplicate ids - the note's figures (a naive `grep -o day6` over the whole line
gives 114 because two descriptions mention the marker; the second column gives 112).

## What I could not break

Every attack below ran in a worktree with `proofpack.__file__` proved first.

- **The suite and the markers.** Git Bash `988 passed, 1 skipped, 1 xfailed in 74.38s`;
  PowerShell 5.1 `988 passed, 1 skipped, 1 xfailed in 66.58s`; the skip is
  `test_doctor_cli.py:57`, the xfail `test_f13_matches_proc_on_the_asah_dataset`. Markers
  (PowerShell): day8 `200 passed, 790 deselected in 12.86s`, day7 139, day6 285, day5 54,
  day4 182, day3 `29 passed, 1 xfailed`, day2 40, day1 `59 passed, 1 skipped`. `--collect-
  only`: day1 60, day2 40, day3 30, day4 182, day5 54, day6 285, day7 139, day8 200 of 990
  (day1..day7 the `7b2ca2a` counts). `ruff check` `All checks passed!` and `ruff format
  --check` clean in both shells. `day8` is declared at `pyproject.toml` line 82; `ci.yml`
  reads the marker list out of `pyproject.toml` and installs with `uv sync --all-groups
  --locked`; `uv.lock` carries `name = "jinja2"` (line 497) and `{ name = "jinja2",
  specifier = ">=3.1" }` (line 980).
- **Nothing weakened.** `git diff --name-status 29fc04e 657ef11 -- tests/`: 31 `A`, 4 `M`,
  0 `D`. Removed `pytest.mark` lines: 0; added: 2 (the new file's `pytestmark` and the
  corpus-count test). `grep -nE "^\+.*(skip|xfail|\.only|todo)"` over the whole diff hits
  only the two lens-1 notes (prose), two mutant ids containing `_skipped`, and one docstring
  naming a mutant - no new skip, xfail or `.only` in code or tests. `cli.py` and `run.py`
  are untouched by this diff (`--stat` empty), so the note's DEC-43 list is complete against
  the schemas and `errors.py`: `declaration_index` required on `criterionResult`, six new
  reason codes (42), the `y_pred` description, `HALT_CODES["H02"]`'s text, the `.customer-
  text` rule and the declared-digit printing.
- **Fails pre-build.** `tests/test_e8_repair1.py`, `tests/test_render_format.py`,
  `tests/test_claims.py` and corpus `086`-`115` copied into the `29fc04e` worktree
  (115 corpus files there after the copy): `42 failed, 111 passed in 3.45s` - the note's 41
  plus the two-operating-point test it ran separately. First E line of each, `--tb=line`:
  the sibling sweep `assert [('CL-0001', ...youden'), ...] == []`; the literal claims
  `({'claim_id': 'CL-0062', ...}, 'metric_mismatch')`; the two-operating-point test `assert
  None == 'operating_point_mismatch'`; free_text `AssertionError: pаss`; H02 `Failed: DID NOT
  RAISE HaltError`; declared digits `AssertionError: threshold 0.4275 rule`; prior_version
  `jinja2.exceptions.UndefinedError: 'dict object' has no attribute 'prior_version'`;
  declaration index `KeyError: 'declaration_index'`; malformed documents `AttributeError:
  'str' object has no attribute 'get'`; `fmt.declared` `AttributeError ... no attribute
  'declared'`; corpus `086`-`099` and `101`-`115` `('<file>', 'accepted')`; `100`
  `Verdict(claim_id='CL-9107', accepted=False, reason_code='status_recomputation_mismatch',
  detail={'reason': 'no Number bound'})`; the count test `assert (36 == 42)`; and the
  numerically-correct-corpus test on `086` (a sibling pointer not a Number under the old
  predicate). All as the note quotes.
- **The old day-7 forms** (`git show 7b2ca2a:tests/test_run_cli.py`) against the tip:
  `2 failed` on `assert {...'prevalence': {... 'est': 0.345 ...}} is None` for the clustered
  and the y-pred-only tests; unchanged since lens 1.
- **The corpus.** 115 `.json` files and no other entry in the directory; `CORPUS_FILES =
  sorted(CORPUS.glob("*.json"))` feeds the parametrised test, `test_claims.py` collects 130
  (115 + 15); every file has `name`, `rule`, `expected_reason_code`; the 115 codes cover all
  42 of `REASON_CODES` (`set(REASON_CODES) - expected == set()`); files `086`-`115` each
  name the lens finding and the code in their `rule`.
- **The sweeps** (own worktree): day8 `28 planted, 28 killed, 0 survived; 177 s`, day7 `25
  planted, 25 killed, 0 survived; 164 s`, tree clean after; the builder's
  `<scratchpad>/repair-E8-r1/sweep_day8_final.txt` ends `28 planted, 28 killed, 0 survived;
  177 s` / `exit 0` (the run the note said was still going).
- **The golden.** Committed `i/lf w/crlf`; LF-normalised 39,800 bytes; the masked render is
  39,800 bytes and `equal: True`; two renders of the same document are identical.
- **The footer emptied** (`page_footer` macro body removed from `base.html`): `assert 0 ==
  3`, `assert 0 == 1`, `assert 0 == 2`, `assert (0 == 3)` - `4 failed` (the three footer
  tests and the watermark test), restored by `git checkout`.
- **The qualifier removed** (`design/guidance_map_v1.csv`, `FDA_AIDSF_PERF_VALIDATION`
  status `draft - not for implementation` → `draft`): `test_every_fda_aidsf_anchor_carries_
  the_draft_label_in_data_and_on_the_page` ERRORs in its fixture with `AnchorError: guidance
  map row 'FDA_AIDSF_PERF_VALIDATION' is a draft without the 'not for implementation'
  qualifier in its status ('draft'); refusing to render`, and `test_the_guidance_map_draft_
  rows_all_carry_the_qualifier_and_are_the_fda_aidsf_rows` fails `assert not True`.
- **The wheel.** `python -m uv build --wheel` from the worktree; installed `--no-deps
  --no-index --target` into a `python -m venv --without-pip` venv: `site-packages` holds
  `bin`, `proofpack`, `proofpack-0.1.0.dev1.dist-info`; `find venv -name "*.pth"` is empty;
  with `PYTHONPATH` unset and `PYTHONNOUSERSITE=1`, `proofpack.__file__` and
  `resource_path("tokens.json")` print `...\wheel\venv\Lib\site-packages\proofpack\...`,
  `site.ENABLE_USER_SITE False`. The wheel lists the three templates and the seven
  `_schema` resources including `tokens.json`. With the force-include line
  `"design/tokens.json" = "proofpack/_schema/tokens.json"` removed from `pyproject.toml` the
  committed test fails: `FileNotFoundError: packaged resource 'tokens.json' not found` from
  `venv\Lib\site-packages\proofpack\resources.py` line 39; restored.
- **tokens.json versus D5 section 3.1.** All 19 hex values (`ink` `#16202b` ... `ok-line`
  `#86b39a`) match by name; no hex in the file is outside the D5 table; the type scale
  `0.72 / 0.78 / 0.85 / 0.92 / 1 / 1.15 / 1.4 / clamp(1.8rem, 4.2vw, 2.7rem)`, line heights
  `1.6 / 1.25 / 1.45`, tracking `0.06em`, `tabular-nums`, spacing `0.25 .. 3rem`, radii `4 /
  6 / 8`, `1px`, `3px solid` + `2px`, `68ch / 74rem / 44rem`, `motion none`, print `A4`,
  `20mm 18mm 26mm`, `0.72rem` all match the section text. (The file is not in this diff.)
- **Imports with packages hidden.** `jinja2`, `markupsafe`, six `cryptography` modules,
  `scipy`, `scipy.stats`, `scipy.special`, `statsmodels`, `sklearn` set to `None` in
  `sys.modules`: `proofpack`, `.stats`, `.narrate`, `.narrate.checker`, `.narrate.claims`,
  `.render`, `.render.format`, `.render.html`, `.criteria`, `.gates`, `.run`, `.cli` import;
  none of the hidden modules loaded; `render.html.environment()` raises `RendererUnavailable
  ... needs the package 'jinja2'`. No `socket`, `urllib`, `http`, `requests` or `ssl` import
  under `src/proofpack`.
- **The lens-1 blockers on the lens-1 scripts, re-run unchanged against a `657ef11`
  worktree at their hard-coded path.** `b_checker.py`: `engine claims: 70 accepted: 70`;
  B4 `accepted sibling-metric swaps: 0` (lens 1: 339); B3 field mutations accepted 70, all
  `guidance_ref` (N6; lens 1: 294); the twelve B2 spellings each `REJECTED
  free_text_verdict_word`; B6 `final ids: ['CL-0001']` with `[('CL-0001',
  'claim_id_duplicate', True), ('CL-0001', 'claim_id_duplicate', False)]`. `c_renderer.py`
  C10: `threshold 0.4275 printed as: ['0.4275']`, the YAML echo `['0.4275'] ['0.8525',
  '0.9', '0.5']`. `d_wiring.py` D9 (yes/no y_pred): `rc 3 files no dir`; D10 (no
  prior_version): `rc 0 files ['T8.html', 'ingest_report.json', 'run.json']`; D12 (two
  `C_dup` rows): `row 1 ... authored 'Author One · 2026-01-01' justification 'first
  justification'`, `row 2 ... 'Author Two · 2026-02-02' ... 'second justification'`.
- **The repaired H02 on foreign labels, through the CLI:** `yes`/`no`, `1.0`/`0.0`,
  `TRUE`/`FALSE` beside classes `1`/`0`, with and without a score column, each `exit 3`,
  `HALT H02: y_pred contains value(s) outside declared classes and indeterminate values`,
  no pack directory; integer `0`/`1` and string `1`/`0` pass with the same two-by-two
  `{tp 34, fn 8, fp 20, tn 58}`. At the gate: `HaltError` `{'column': 'y_pred',
  'n_unknown_values': 2, 'n_declared': 2}`.
- **The checker's docstring claims.** "the engine sets `metric_id` on every claim it builds
  that binds a Number": on the synthetic (70 claims), two-operating-point (118), clustered
  (60) and y-pred-only (61) documents, 0 Number-binding claims with a null `metric_id`, 0
  engine pointers off the eight `POINTER_SHAPES`, 0 rejections of the engine's own claims.
  RG-N1 "did not reproduce as described": `fairness = "x"` patched into the assembled
  document with the engine's FAIRNESS_GAP claim gives `value_ref_unresolved` (rule 3 first),
  as the note says; the test's four-`/flow/`-ref shape gives `subgroup_not_in_document`.
- **Numbers, re-derived without repo statistics code.** Clustered fixture of the new test
  (200 rows, 100 two-row cases): my numpy two-by-two `{tp 57, fn 12, fp 35, tn 96}` equals
  the engine's; sensitivity, specificity, PPV, NPV, accuracy, prevalence equal the pooled
  ratios (57/69, 96/131, 57/92, 96/108, 153/200, 69/200) with deviation `0.00e+00` on all
  six, each `cluster_bootstrap_percentile`; `threshold_free.prevalence == op1.prevalence`
  (the FA-N2 mutant's line is now killed by the sweep and by the test). The E7 e2e run:
  sensitivity 96/128 engine Wilson `(0.6684443704768314, 0.8169871513864144)` versus
  statsmodels `(0.6684443704768313, 0.8169871513864144)`, `|dlo| 1.11e-16`, `|dhi| 0`;
  AUROC engine `0.8353343290441176` versus `sklearn.roc_auc_score` on `test.csv`
  `0.8353343290441176`, `|d| 0.0`, `delong_wald`, n 400. `fmt.declared`: `0.4275 → 0.4275`,
  `0.8525`, `0.0125`, `0.1005`, `0.8 → 0.8`, `1e-7 → 0.0000001`, `0.1+0.2 →
  0.30000000000000004` (what `json.dumps` carries), `1e21 → 1000000000000000000000`, `-0.0
  → −0.0`, `5 → 5` - every string equal to `json.dumps(x)` up to the minus sign.
- **The two-shell run** on `scratchpad/e2e_shell/` (400 rows, confirmed mapping, own empty
  `PROOFPACK_HOME`, no licence): both shells print the same six lines ending `HTML not
  written: licence refused (no_file); run.json only (D1 section 7: after grace, JSON only)`
  / `Next step: proofpack licence install FILE, then run again for T8.html (docs:
  /docs/run)`, `exit=4`, the pack holding `ingest_report.json` (649 bytes) and `run.json`
  (253,943 bytes in both); the two `run.json` validate against `output_schema_v1.json` with
  0 errors, 20 top-level keys, 70 claims, 0 rejections, 3 `guidance_refs`
  (`FDA_AIDSF_PERF_VALIDATION`, `FDA_AIDSF_SUBGROUP_PERF`, `FDA_AIDSF_CALIBRATION`, `draft
  true`), `declaration_index` `[0, 1, 2, 2, 2, 3, 4, 5, None]`, watermark `LICENCE EXPIRED -
  not for submission`; the only top-level block differing between shells is `manifest`, in
  `duration_s`, `run_id`, `started`. No mapping file: `HALT H07: run proofpack map first
  ...`, `exit=3`, no directory. `doctor --offline` exit 0 with the note's last line, and
  `licence show` `licence: none found` / `status: refused (no_file)` / exit 4, in both
  shells.

## What I could not check

- **CI on ubuntu / Python 3.12**: the engine is not pushed (never push); the golden, the
  marker loop and the wheel job were not run there.
- **The sweeps in PowerShell**: Git Bash only (the note's figures are Bash).
- **A real-licence HTML from the plain CLI**: the signing key is not on this machine; the
  HTML path ran through `cli.main(..., registry=ephemeral_registry())` as the tests do.
- **`unicode-bidi: isolate` and `@page` in a browser**: no browser driven; the CSS line is
  present in `base.html` (measured), its effect is not.
- **What a blank `y_pred` should do** (B1): HALT, exclusion with a `flow` count, or an
  indeterminate - D1 section 2 gives no null semantics; that is Josh's call, and the
  silent negative is not one of the options.

## Sentences I refused to write

- "The repaired H02 catches every mislabelled y_pred." B1 is the blank.
- "free_text cannot spell a verdict word past the rule." B2 is `pa\x01ss` and `ᴘᴀss`; the
  sixteen rejected spellings and the two accepted ones are listed instead.
- "The new tests would have caught the lens-1 findings." Nine of the ten fail at `29fc04e`;
  the tenth passes there; two fail on an abort or a key rather than the behavioural line
  (N3, N4), and the behavioural lines were run separately.
- "The renderer prints the declared value as declared." Written instead: `declared()` equals
  `json.dumps` on the eleven literals above, and `0.80` in YAML is `0.8` on the page.
- "The clustered block is correct." Written instead: six pooled ratios at `0.00e+00` on one
  200-row fixture, and Wilson / AUROC on one 400-row run against statsmodels and sklearn.

## Re-run these

```bash
W=<scratchpad>/lens-E8-r2-regression
git -C C:/Users/joshs/GPS/ProofPack/proofpack worktree add --detach $W/tip 657ef11
cd $W/tip && export PYTHONPATH=$W/tip/src && python -c "import proofpack;print(proofpack.__file__)"
python -m pytest -q -p no:cacheprovider                          # 988 passed, 1 skipped, 1 xfailed
python -m pytest -q -p no:cacheprovider -m day8                  # 200 passed
python scripts/mutation_sweep.py --marker day8                   # 28 planted, 28 killed, 0 survived
PYTHONIOENCODING=utf-8 python -c "from proofpack.narrate.checker import free_text_reason as f;print(f('pa\x01ss'),f('\u1d18\u1d00ss'))"   # B2: None None
# B1: the blank-y_pred table through cli.main(..., registry=ephemeral_registry()) as in the Blockers section
git -C C:/Users/joshs/GPS/ProofPack/proofpack worktree remove --force $W/tip
```
