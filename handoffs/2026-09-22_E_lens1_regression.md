# Lens 1 (regression and record) - build day 8, lane E, `29fc04e` - 2026-09-23

**Verdict: PASS.** No blocker. Every figure in the orchestrator's note re-measures: `946
passed, 1 skipped, 1 xfailed` in both shells; `-m day8` 158 collected and 158 passed;
`day1`..`day7` collect 60 / 40 / 30 / 182 / 54 / 285 / 139 at `29fc04e`, the same seven
counts as at `7b2ca2a`; ruff and format clean; doctor exit 0 with the note's last line; the
day-8 sweep `15 planted, 15 killed, 0 survived` (122 s here, 110 s in the note); the corpus is
85 files, all 85 loaded by the parametrised test, each naming `name`, `rule` and a reason code
in `REASON_CODES`, and the 85 cover all 36 codes; the golden regenerates byte-identical
(39,638 bytes LF); `design/tokens.json` equals every value D5 section 3.1 states and the nine
WCAG ratios I recomputed without repo code equal the file's `contrast_computed` to the second
decimal; the wheel test installs into a venv with no `.pth` and fails when the force-include
line is removed; the footer test fails with the footer macro emptied; the anchor test goes red
with a map row's qualifier removed; the old day-7 clustered and y-pred-only assertions fail on
the new tree; the new test files all abort at `7b2ca2a` and the six modified tests all fail
there on their assertions; nothing in `tests/` was deleted and no marker was removed.
Thirteen non-blocking items follow, three of them sentences the hard rule refuses (each with
the counter-example I ran), and four things S4 must add to the note's DEC-43 list.

Worktrees: `29fc04e`, `7b2ca2a` and a third `29fc04e` for the attacks, under
`scratchpad/lens-E8-r1-regression/`, `PYTHONPATH=<worktree>/src` forced and proved by
`python -c "import proofpack;print(proofpack.__file__)"` printing that worktree's own
`src/proofpack/__init__.py` before every figure below. The main tree was read only; this
note is the one file written there. All three worktrees removed at the end.

## Blockers

None.

## Non-blocking

Numbered N1-N13. "Sentence" marks a hard-rule violation: a shipped sentence that asserts what
a check guarantees or prevents without a counter-example recorded; the counter-example I ran
is quoted.

**N1 - Sentence. `checker.check` "never raises on malformed input"** (`src/proofpack/narrate/
checker.py`, the `check` docstring line "Pure; never raises on malformed input", and the
module docstring "raises nothing"). `test_the_checker_never_raises_on_garbage` feeds nine
literal garbage *claims*; the sentence generalises to every input, and the second argument
is also input. Two counter-examples, both run:
`checker.check([<a FAIRNESS_GAP claim with four /flow/ scalar refs and relation
not_assessable>], {"flow": <the run's flow>, "fairness": "x"})` raises
`AttributeError: 'str' object has no attribute 'get'` (rule 5, `fairness.get("gaps")`);
and `build_claims` / `check` on the synthetic run document with
`subgroups[4].diff_vs_reference.op1.sensitivity.number.ci_lo = "-0.1"` raises
`TypeError: '>' not supported between instances of 'str' and 'int'` (`claims.relation_of`,
`lo > 0`). Neither document can come out of `assemble_run`, so the CLI cannot reach it; the
sentence is what is wrong. Write "raises nothing on a malformed *claim* (the nine inputs of
`test_the_checker_never_raises_on_garbage`); the document is the engine's own".

**N2 - Sentence. "a right-to-left override in a label cannot reorder the page"** (`src/
proofpack/render/html.py` module docstring; `neutralise_bidi`). The function rewrites U+202E
as `&#x202e;`. A numeric character reference is decoded to the code point by every HTML
parser, so the override reaches the rendered text unchanged. Run: a `site` level
`"\u202eS1"` through `assemble` and `render_t8`; the bytes hold `&#x202e;` and no raw
U+202E (as `test_html_injection_in_a_justification_and_a_level_label_is_escaped` asserts),
and the test module's own `text_nodes()` (`HTMLParser(convert_charrefs=True)`) returns the
node `'site = \u202eS1'` with the override in it; `html.unescape("&#x202e;S1") ==
"\u202eS1"`. What stops the override reaching the rest of the page is HTML's block bidi
boundary (a `<td>` is its own bidi paragraph), not this function; inside the cell the text
after the override is reversed. The sentence names an inspection ("the raw byte does not
appear") as a guarantee. Either isolate customer text (`<bdi>` or `unicode-bidi: isolate` on
`.customer-text`, then a test that reads the DOM, not the bytes) or reword to what is
inspected.

**N3 - Sentence (trivial). `format.count` docstring: "``None`` prints as an em-dash-free blank
marker"** - `fmt.count(None)` returns `'\u2014'`, which is EM DASH (measured: `hex(ord(...))
== 0x2014`). The docstring says the opposite of the code.

**N4 - The claims checker accepts a Number whose interval is a string.** `is_number_object`
checks the eight keys, not their types; `relation_of` reads `ci_lo is None`. Run: the
synthetic run document with `overall.op1.sensitivity.ci_lo = "0.1"` and the engine's own
`OVERALL_ESTIMATE` claim -> `accepted True, reason_code None`. Unreachable through the engine
(the output schema types every Number and `assemble_run` writes only Numbers), so no
customer sees it; a `value_ref_not_a_number` on a non-numeric `est`/`ci_lo`/`ci_hi` would
close it in one line, with the literal above as the test.

**N5 - `run` with the new default and no jinja2: exit 5, `run.json` written, no summary
line.** Run (worktree, `jinja2` and `markupsafe` set to `None` in `sys.modules`, the
test-only registry licence): `exit 5`, stderr `error: the HTML renderer needs the package
'jinja2', which is not installed (install proofpack with its dependencies: jinja2>=3.1)`,
stdout empty, the pack directory holding `ingest_report.json` and `run.json`. The refusal is
typed, but the `run written: ...` line and the criteria counts are never printed because
`write_documents` runs before `_emit`. A `pip install proofpack` pulls jinja2, so a customer
does not hit it; the site's `scripts/demo_sample.py` (read only) calls `cli.main(["run",
..., "--quiet"])` with no `--format`, so under the S4 pin move the Pyodide bundle either
carries jinja2 + MarkupSafe or passes `--format json` - see S4 below. Consider emitting the
summary before the documents, or catching `RendererUnavailable` into a `document_notes`
line and exit 0.

**N6 - S4 (DEC-43): the note's CLI list omits four things the diff changes.** Measured against
`git diff 7b2ca2a 29fc04e -- src/proofpack/cli.py src/proofpack/run.py schema/`:
(a) the `--json-log` `run` payload gains six keys - `formats`, `templates`, `documents`,
`document_notes`, `claims`, `claim_rejections` (`test_json_log_reports_the_documents`);
(b) `guidance_refs` in `run.json` was `[]` on every run and is now filled - three items on
the synthetic run (`FDA_AIDSF_PERF_VALIDATION`, `FDA_AIDSF_SUBGROUP_PERF`,
`FDA_AIDSF_CALIBRATION`), each `{id, label, draft, url}`; the output schema now requires
`claims` and `claim_rejections` and closes the `guidance_refs` item;
(c) the console "Next step" line after `run` has three variants (documents written / no
usable licence / `--format json`), none of them E7's `then the T1/T7/T8 renderers`;
(d) N5: `run` needs jinja2 at run time under the default; `run.json` on the 400-row fixture
grows from 216,303 bytes (E7) to 253,701 (the `claims` block; measured on
`pack_bash_lic/run.json`).

**N7 - README not updated.** `grep -n "\-\-format\|\-\-templates\|T8.html" README.md` returns
nothing; the E7 decision table's rule was that a customer-facing `run` decision is stated in
the README's `proofpack run` section. The flags, the default, `T8.html` beside `run.json`, and
the JSON-only behaviour after grace exist only in `cli.py`'s docstring and the note.

**N8 - `guidance_refs` (data) and T8 section 9 (page) list different anchor sets.** `run.json`
carries the three anchors the accepted claims cite (the schema description says so); the
page's section 9 table and the footer's "Guidance references:" list carry seven - those
three plus T8's own `PP_SCOPE`, `PP_METHODS`, `FDA_AIDSF_DATA_MGMT`, `FDA_PCCP_MP1_DATA`
(`T8_ANCHORS`, resolved at render time). D4 section 11 item 9 says "every anchor used in
the render" and D4 section 1.1 says the cover's guidance-version list is `guidance_refs`.
The four extra labels come from the shipped map, not from the run, so "the HTML carries
nothing run.json does not" holds for data; the two lists disagree in count (3 vs 7). Either
add T8's anchors to `narrative_block` or say in the schema description that the page adds
the template's own.

**N9 - D4 section 11 item 3 asks for `criteria.yaml` "rendered verbatim (monospace)"; the page
prints the `declarations` block of `run.json` re-serialised as YAML with sorted keys** (the
note records it as a decision: "the page is a pure function of run.json"). The customer's
comments, key order and quoting are gone; the file's SHA-256 is in the manifest. Josh's call
whether the label "Manufacturer text - the declarations block of run.json as YAML" is enough
for an RA lead who expects their own file.

**N10 - The golden's mask is `manifest.numpy`, not run_id / started / duration_s.** Measured:
an unmasked render differs from the golden in exactly two lines, both the
`<tr><th scope="row">numpy</th>...` row (`2.5.1` vs `x.y.z`); `run_id`
(`test-only-assembler`), `started` (`2026-09-18T00:00:00Z`) and `duration_s` (`—`) are
constants the assembler writes, not masked fields. The test docstring says so; the brief's
wording ("masking touches only run_id, started and duration_s") does not match what the
test does. Not a defect - recorded so the next lens does not chase it. The golden also
embeds `ProofPack v0.1.0.dev1` in four places and `test_the_footer_repeats_on_every_page_
section_and_once_in_print` asserts the literal `ProofPack v0.1.0.dev1 on
2026-09-18T00:00:00Z`: a version bump regenerates the golden and edits that line.

**N11 - `narrative_integrity` computes `halts` and the template never prints it** (`T8.html`
section 7 prints ten `data-count` cells; `integrity.halts` is unused). D4 section 11 item 7
does not ask for it; either print it or drop it.

**N12 - Two note figures differ from the tree.** `ruff format --check` reports `126 files
already formatted` in the clean `29fc04e` worktree and in the main tree (the note: 124); the
day-8 sweep took 122 s here (the note: 110 s). Neither changes a result.

**N13 - The wheel test carries a `pytest.skip` path** (`_build_wheel`: "no wheel builder
available in this environment") - the one skip/xfail addition in the diff (`git diff
7b2ca2a 29fc04e | grep -nE "^\+.*(skip|xfail|\.only)"` -> the two mutant ids containing
`_skipped`, the walker's `self.skip` counter, and this line). On this machine the test ran
(`uv build` succeeded; the suite's one skip is `test_doctor_cli.py:57`). In CI `uv` is not a
locked package, so `python -m uv build` fails and the fallback is `python -m pip wheel`
(`pip` is in `uv.lock`, line 877, via pip-audit); I could not run CI (see below). `ci.yml`
separately asserts `resource_path("tokens.json")` resolves under `_schema` in the built
wheel (the E8 diff adds it to that list), so the property is gated twice. A skip in a gate
test should fail loudly instead; `pytest.fail` with the two error tails is the one-line change.

## What I could not break

Every attack below was run in a worktree with `proofpack.__file__` proved first.

- **The suite and the markers.** Git Bash: `946 passed, 1 skipped, 1 xfailed in 103.35s`
  (the worktree, with the sweep and the pre-build run in parallel); PowerShell 5.1: `946
  passed, 1 skipped, 1 xfailed in 65.48s`. `--collect-only`: day1 60, day2 40, day3 30, day4
  182, day5 54, day6 285, day7 139, day8 158 (of 948) at `29fc04e`; day1..day7 the same
  seven counts of 790 at `7b2ca2a`, day8 none. `-m day8` `158 passed` (11.60 s Bash, 9.53 s
  PowerShell); `-m day7` `139 passed`; `-m day6` `285 passed`; `-m day5` `54 passed`. `ruff
  check` `All checks passed!` and `ruff format --check` `126 files already formatted` in both
  shells. `doctor --offline` exit 0, last line `Next step: proofpack declare --out
  criteria.yaml, then proofpack map --input test.csv --criteria criteria.yaml` in both.
  `git diff --name-status 7b2ca2a 29fc04e -- tests/`: 96 `A`, 6 `M`, 0 `D`; removed
  `pytest.mark` lines 0.
- **Fails pre-build.** The six new test files copied into the `7b2ca2a` worktree (with the
  corpus and the golden): `test_claims`, `test_overall_carried`, `test_render_format`,
  `test_render_t8`, `test_render_theme` abort at collection (`No module named
  'proofpack.narrate'` / `'proofpack.render'`; `cannot import name 'CLUSTERED_REFUSED_2X2'`),
  which is the expected mode for feature tests; `test_sweep_day8.py` alone fails on its
  assertions (`assert 0 >= 12`; `assert {...run.py, ...} <= set()`). The four modified test
  files with the new `assembler.py` at `7b2ca2a`: `6 failed, 179 passed` - the six are
  exactly the six functions the diff changed (`test_the_document_validates_and_is_
  canonical_json`, `test_the_status_words_appear_only_under_criteria_results`, `test_a_y_
  pred_only_table_gives_calibration_null_with_no_score_column`, `test_a_clustered_run_has_a_
  cluster_bootstrap_overall_block_and_cells`, the day-6 and day-7 verdict walks). The OLD
  forms of the day-7 clustered test and the y-pred-only test (`git show 7b2ca2a:tests/
  test_run_cli.py`) on the new tree: `2 failed` on `assert doc["overall"] is None` with the
  populated block in the assertion message - the change is exactly as the note says.
- **The day-8 sweep**, in the worktree with `PYTHONPATH` re-forced to the copy by the script:
  every one of the fifteen `killed`; `15 planted, 15 killed, 0 survived; 122 s`; `exit 0`.
- **The footer with the macro emptied** (base.html, `page_footer` body removed):
  `test_the_footer_repeats_on_every_page_section_and_once_in_print` and both parametrisations
  of the one-/two-page test fail on `assert 0 == 3` / `0 == 1` / `0 == 2` and the watermark
  test on `assert (0 == 3)`.
- **A map row without the qualifier** (`FDA_AIDSF_PERF_VALIDATION` status set to `draft`):
  `test_every_fda_aidsf_anchor_carries_the_draft_label_in_data_and_on_the_page` goes red as an
  ERROR in the module fixture - `AnchorError: guidance map row 'FDA_AIDSF_PERF_VALIDATION'
  is a draft without the 'not for implementation' qualifier in its status ('draft');
  refusing to render` - the renderer refuses before the assertion is reached. A second row
  (`FDA_AIDSF_SUBGROUP_PERF`, status `draft (January 2025)`) fails `test_the_guidance_map_
  draft_rows_all_carry_the_qualifier_and_are_the_fda_aidsf_rows` on `assert not True`.
- **The force-include line removed**, wheel rebuilt with `uv build`, installed
  `--no-deps --no-index --target` into a `--without-pip` venv: `FileNotFoundError: packaged
  resource 'tokens.json' not found` from inside the venv's `site-packages\proofpack\
  resources.py`, `assert 1 == 0` on the return code; `1 failed`. With the line restored:
  the venv's `site-packages` holds `bin`, `proofpack`, `proofpack-0.1.0.dev1.dist-info` and
  no `.pth` file anywhere under the venv; `proofpack.__file__` and `resource_path("tokens.
  json")` both print venv paths (`...\venv_probe\Lib\site-packages\proofpack\_schema\
  tokens.json`) with and without `PYTHONNOUSERSITE=1`; `unzip -l` lists
  `proofpack/_schema/tokens.json` and the three `proofpack/templates/*.html`.
- **The golden.** Rendered from the same assembler document, LF-normalised: 39,638 bytes,
  `equal: True`; a second render equal to the first. The committed file is `i/lf w/lf`.
- **D5 section 3.1 versus `tokens.json`.** Every hex value, role, scale step (`0.72 / 0.78 /
  0.85 / 0.92 / 1 / 1.15 / 1.4 / clamp(1.8rem, 4.2vw, 2.7rem)`), line-height (`1.6 / 1.25 /
  1.45`), tracking `0.06em`, spacing `0.25 .. 3rem`, radii `4 / 6 / 8`, `68ch / 74rem /
  44rem`, `1px`, `3px solid` + `2px`, and the section 3.5 print values `A4`, `20mm 18mm 26mm`,
  `0.72rem` match the D5 text. My own sRGB-luminance script (no repo code): ink 16.46,
  ink-soft 7.09, ink-faint 4.57, line 1.34, on-brand/brand 11.69, brand/brand-soft 9.97,
  honesty 6.80, stop 10.02, ok 9.11 - each equal to the file's `contrast_computed`; the
  three D5 figures that differ (6.2, 8.7, 7.9) differ by +0.60, +1.32, +1.21 from the formula,
  so the note's needs-from-Josh 1 is real.
- **The corpus.** 85 `.json` files, no other file in the directory; `CORPUS_FILES = sorted(
  CORPUS.glob("*.json"))` is what the parametrised test reads, so 85 collected = 85 files
  (the day-8 collection count 158 = 85 corpus + 73 other); every file has `name`, `rule`,
  `expected_reason_code`; the 85 codes cover all 36 of `REASON_CODES` (the largest class
  `free_text_verdict_word` 12, then `free_text_certification_word` and `relation_mismatch`
  5 each). D4 section 8: 52 table rows carrying 55 ids; the library holds 56 (`SUBGROUP_
  ESTIMATE` the recorded addition); `test_the_library_transcribes_d4_section_8...` pins
  every id.
- **Imports with third-party modules hidden.** `jinja2`, `markupsafe`, `cryptography` (six
  modules), `scipy` (three), `statsmodels`, `sklearn` set to `None` in `sys.modules`:
  `proofpack`, `.stats`, `.narrate`, `.narrate.checker`, `.narrate.claims`, `.render`,
  `.render.theme`, `.render.format`, `.render.anchors`, `.render.html`, `.criteria`, `.run`,
  `.cli` all import; no hidden module loaded; `html.environment()` raises
  `RendererUnavailable ... needs the package 'jinja2'`. `grep` for `socket|urllib|http|
  requests` imports under `src/proofpack`: none. `uv lock --check --offline`: resolved 63
  packages, no complaint; `uv.lock` carries `jinja2 3.1.6` and `markupsafe 3.0.3` (+77
  lines); `ci.yml` installs with `uv sync --all-groups --locked` and its marker loop reads
  `pyproject.toml`, where `day8` is declared.
- **The two-shell `run`** on the E7 fixture `scratchpad/e2e_shell/` (400 rows, S3 = 30, the
  `file`-confirmed mapping), each shell with its own empty `PROOFPACK_HOME`. Plain CLI, no
  licence: identical six lines in both shells ending `HTML not written: licence refused
  (no_file); run.json only (D1 section 7: after grace, JSON only)` / `Next step: proofpack
  licence install FILE, then run again for T8.html (docs: /docs/run)`, `exit=4`, the pack
  holding `ingest_report.json` and `run.json` only. With the test-only registry licence
  (`cli.main(..., registry=ephemeral_registry())`, a driver in the scratchpad): `exit 0`,
  `licence ok (valid)`, `document written: ...\T8.html`, `Next step: open T8.html beside
  run.json; T1 and T7 land on E9`, 70 claims, 0 rejections, three `guidance_refs`, `T8.html`
  39,983 bytes with no CRLF in both shells; the two `run.json` differ only in `duration_s`,
  `run_id`, `started` (0 top-level blocks differ once blanked); the two `T8.html` differ in
  24 lines, every one a `run_id`, `Started (UTC)`, `Duration (s)` or footer-date line.
- **Numbers on the page against primary tools**, on that run: `overall.op1.sensitivity`
  96/128, engine Wilson `[0.6684443704768314, 0.8169871513864144]` versus statsmodels
  `proportion_confint(96, 128, method="wilson")` `[0.6684443704768313, 0.8169871513864144]`
  (`|dlo| 1.11e-16, |dhi| 0`); AUROC engine `0.8353343290441176` versus
  `sklearn.metrics.roc_auc_score` on `test.csv` `0.8353343290441176` (`|d| 0`). All nine
  criteria cells on the page re-formatted by hand from `run.json` with `format()` only
  (D4 section 1.2 rules typed out): `96/128 (75.0%) [66.8, 81.7]`, `21/30 (70.0%) [52.1,
  83.3]ᶜ`, `—` ×3 (the three `C_f1_site` rows, no Number), `0.835 [0.795, 0.876]`, `—`,
  `—`, `+7.0 [−7.9, +21.7]` - 9/9 equal; `run.json` keeps `C_n30` at `est 0.7` and the
  compared value at full precision (`0.6684443704768314`).
- **The verdict grep on the two documents the golden does not cover.** T8 rendered for the
  clustered document (`C_over` met) and the y-pred-only document (no criteria): 3 sections,
  3 footers each; 0 status words outside `.status` cells; 0 forbidden words outside the
  disclaimer and `.customer-text`; status cells `['criterion met']` and `[]`; the y-pred-only
  page prints `No acceptance criteria were declared; estimates and intervals only.` (D4
  section 5.6). `WARN_CODES` texts carry none of the forbidden words.
- **Typed absences on the page.** A criteria row whose status is not in the enum (`"PASS"`
  planted) makes `render_t8` raise `KeyError: 'PASS'` - a refusal, not a rendered word
  (unreachable: `criteria.py` emits the enum). A Number with a typed reason *and* an interval
  prints `n.e. (single_class)` - the reason wins. A Number with `est None` and an interval
  raises `TypeError` (unreachable: every engine Number with an interval has an estimate).

## What I could not check

- **CI on the reference platform.** The engine is six commits ahead of `origin/main` and was
  not pushed (never push), so no ubuntu / Python 3.12 run of the golden, the marker loop or
  the wheel test exists. The golden's numbers are closed-form (Wilson, DeLong, Newcombe-10;
  the synthetic document is i.i.d. and T8 prints no bootstrap or calibration cell), so I
  expect it to hold there; not measured. N13's skip path in CI: not measured.
- **The builder's per-commit figures** quoted in the note from commit messages (`796 passed`
  at `86b5fdd`, `1 failed, 943 passed` at `afe59b9` with the unparsable sweep file): the
  unparsable file is not in git; not re-run.
- **A real-licence `run --format json,html` from the plain CLI.** The signing key is not on
  this machine; the HTML path was measured through `cli.main(..., registry=...)` and the
  test-only licence (the same code path after `resolve`), in both shells.
- **DEC-34 / DEC-35 / DEC-36 on the page.** T8 prints no calibration cell and no IPA; the
  renderer reads the row tier through `fmt.tiers` (the `ᶜ` on `C_n30` above), but the
  calibration-null-beside-reason rendering and the IPA annotation are T1 / T7 (E9) lines.

## Re-run these

```bash
W=<scratchpad>/lens-E8-r1-regression
git -C C:/Users/joshs/GPS/ProofPack/proofpack worktree add --detach $W/eng-29fc04e 29fc04e
cd $W/eng-29fc04e && export PYTHONPATH=$W/eng-29fc04e/src
python -c "import proofpack;print(proofpack.__file__)"          # must print the worktree
python -m pytest -q -p no:cacheprovider                          # 946 passed, 1 skipped, 1 xfailed
python -m pytest -q -p no:cacheprovider -m day8                  # 158 passed
python scripts/mutation_sweep.py --marker day8                   # 15 planted, 15 killed, 0 survived
python -m ruff check . && python -m ruff format --check .        # clean / 126 files
# N1 / N2 / N4 counter-examples: the three probes in the "Non-blocking" text above, run from
# the worktree's tests/ directory with sys.path[0] = "." (they import assembler and conftest).
git -C C:/Users/joshs/GPS/ProofPack/proofpack worktree remove --force $W/eng-29fc04e
```

## Sentences refused

The builder wrote no note, so nothing was refused at build time. In the diff, the three
sentences N1-N3 assert what a check guarantees without a counter-example on record; N1 and
N2 have counter-examples above that were run and did what the sentence says cannot happen.
Sentences that generalise but which a run counter-example in the diff or in this note
supports, left standing: "the renderer never prints an FDA draft anchor without the
qualifier" (`anchors.py`; the planted row above); "the test cannot pass by reading the source
tree" (`test_render_theme.py`; the force-include attack above); "``check`` never emits a
code outside this dictionary" (`checker.py`; the `assert code in REASON_CODES` in `reject`
and the schema enum equal to the dictionary - an inspection, stated as one). In this note I
refused to write "the checker rejects every semantically false claim" (85 literal cases are
rejected; nothing is known about the 86th) and "the page is safe against injection" (two
literal payloads are escaped on the bytes; N2 shows what the bytes do not decide).
