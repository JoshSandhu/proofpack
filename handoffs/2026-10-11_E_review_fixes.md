# 2026-10-11 E: fixes for the defects the independent review confirmed

Branch `fix-1011-engine`, base `b664500`. Source: `handoffs-orchestrator/2026-10-11_INDEPENDENT_REVIEW.md`
sections 5 and 6, engine rows E1, E3 to E9 and the README line. Every fix has a regression test in
`tests/test_fix1011_engine.py`, marker `fix1011` (registered in `pyproject.toml`; every test also carries `day15`
because the invariants test wants a day marker).

**These fixes reach buyers only after a site pin move.** The site serves the wheel built at `b664500`. Until the
site's `ENGINE_REF` pin moves to a build that contains this branch and the site is redeployed, the live demo,
the quickstart and the sample pack run the old engine. The PyPI `0.1.0.dev1` is unaffected by anything here.

## What landed

| id | change | where |
|---|---|---|
| E1 | The missing-`[docx]` line names the three packages with the minimum versions from the `docx` extra (`pip install "docxtpl>=0.19" "python-docx>=1.1" "matplotlib>=3.9"`), not `proofpack[docx]`. The README sentence says the same. The only `proofpack[stats]` hint was a docstring; it now names `scipy>=1.14`. The jinja2 error text quoted its specifier so a shell does not read `>=3.1` as a redirect. A test compares `docx.EXTRA_PACKAGES` with `pyproject.toml`. | `render/docx.py`, `README.md`, `fixtures.py`, `render/html.py` |
| E3 | New optional `criteria.yaml` key `y_pred_operating_point` (schema, `io.declare`, `gates.gate_h04`). `y_pred` beside a score and more than one operating point with no declaration: HALT H04, message says to declare it, detail `reason: y_pred_operating_point_undeclared` and the point ids. With it declared: `y_pred` is checked at that point only (a mismatch there still halts H04 naming it). An id that is not an operating point: H09. One operating point: unchanged. `errors.py` is untouched. | `schema/criteria_schema.json`, `io/declare.py`, `gates.py` |
| E4 | `datetime.date` and `datetime.datetime` anywhere in the loaded criteria become their ISO text before schema validation, in place and iteratively (an alias chain is entered once). An integer date still halts H08 `type`; a timestamp still halts H08 `pattern`. | `io/declare.py` |
| E5 | `model.version` and `model.prior_version` that PyYAML read as numbers are replaced by the text in the file (those two scalars re-read with `yaml.BaseLoader`). `2.10` stays `"2.10"`, `3` becomes `"3"`; nothing else in the document is touched. `run.json` records `"2.10"`. | `io/declare.py` |
| E6 | `additionalProperties: false` on model, classes, score, operating point, reference_standard, indeterminates, clustering, prevalence entry, subgroup, criterion scope object, ledger, period, egress and egress.suppression; `unevaluatedProperties: false` on criterion and fairness (their `allOf` with the authored block is kept, so `test_criteria` still reads `allOf[1]`). An unknown key halts H08 as `declaration invalid at <path>/<key>: unknown key; correct its spelling or remove it`. The key name is echoed (truncated to 64 characters), never a value. | `schema/criteria_schema.json`, `io/declare.py` |
| E7 | Customer-facing text no longer prints DEC ids, lens and repair numbers, FA-N ids, script paths, build-day labels, E11 item numbers, test names or `D4 section` / `R2 section` references: `design/conventions_T7.md`, the `source` strings of `design/citations.yaml` (the `[unverified]` marks and "citation pending verification" are untouched; no citation was marked verified), the T1/T2/T7/T8/T12 captions and footnotes, `_criteria.html`, the `PP_SCOPE` guidance-map label, the Wilson method description in T7 and the fairness `impossibility_citation` (still `[unverified - ...]`). The DOCX templates are regenerated from the edited generator. Goldens regenerated for T1, T2, T7, T8, T12. | see the table in the note |
| E8 | `ledger.counted` now means "this run added one to the test-set ledger": true only when the run carried criteria, wrote a document and the ledger could be read. Whether the stored count could be read is `acceptance_runs` being an integer. `output_schema_v1.json` still validates (same key, same type; descriptions say what it means). T8 and the DOCX T8 print `yes (this run is included in the count above)`, `no (this run added nothing to the ledger; the count above is the stored count)` or `no (the ledger could not be read or written; see the warning log)`. | `io/ledger.py`, `render/html.py`, `T8.html`, generator, schema |
| E9 | `auroc_wald`'s description now says it is the interval that is not primary: Wald when the logit interval is primary (AUROC above 0.9 or fewer than 30 cases in a class), logit when Wald is primary; the Number's `method` says which. Key not renamed. | `schema/output_schema_v1.json` |
| README | Status says sales opened on 9 October 2026 and to install from the site's install page, not PyPI. | `README.md` |

### Checks of existing criteria files before E6 closed the schema

Validated with the new schema, none breaks: `tests/fixtures/f5/criteria.yaml`; the site's
`proofpack-site/public/demo/synthetic_cohort.criteria.yaml` and its `dist` copy;
`workflows/notes-day10/ap4-review/{criteria,in}/criteria.yaml`; the site's `test-results/blank-cells/decl_a.yaml`
and `decl_b.yaml`. `tests/fixtures/mapping/mimic_composite_key.criteria.yaml` halts E01 before and after, as it was
written to. The in-browser demo builds its declarations in `screen2.mjs` (`buildDeclarations`): every key it writes
is in the schema, and it declares one operating point, so E3 does not touch it.

## Failure on the base, and the pass on the tip

```
git worktree add --detach ../wt-efix-base b664500
cp tests/test_fix1011_engine.py ../wt-efix-base/tests/
cd ../wt-efix-base && PYTHONPATH="$PWD/src" ../proofpack/.venv/Scripts/python -m pytest -q -p no:cacheprovider tests/test_fix1011_engine.py
  -> 39 failed, 6 passed
```

The 6 that pass on the base are guards written to show the fix did not widen anything: the H04 meaning string is
unchanged, a table without `y_pred` is unaffected by several operating points, every shipped criteria file still
validates, the fully populated declaration is valid before an unknown key is added, the leak scanner finds what it is
meant to find, and the `[unverified]` markings survive. On the tip: `45 passed`. The base worktree was removed.

## Suite

Full suite at the tip, main `.venv` with every extra: `2492 passed, 5 skipped` (2,447 at the base plus the 45 new).
`ruff check .` clean, `ruff format --check .` clean. The five skips are environmental (no `uv` module, the R
vectors that exist only in the r-captures job, a read-only-directory test).

Existing tests I had to change, each because it asserted the defect or the old text, not because a check was loosened:

* `test_pypi_workflow.py::test_the_readme_status...` asserted "not yet on sale"; it now asserts the sales line.
* `test_mapping_repair1.py` and `test_mapping_repair2.py` (12 cases) fed `clustering.columns` and five sibling keys with
  one entry and expected "no halt"; those keys are not declared clustering keys, so under E6 they halt H08 naming
  the key. The E01 assertions beside them are unchanged.
* `test_e8_repair6.py` (2 tests) fed an alias payload under `model.extra`; `model` is closed now, so the alias walks
  still accept the document in under 2 s and the schema then halts on the key (asserted by path, and asserted not to
  be a self-reference or control-character halt).
* `test_ap4_roundtrip.py`: the T7 floor on decimal tokens explained by a Number went from 20 to 15 (19 remain of 86);
  one coincidental match left with the internal section references. The orphan scan itself is unchanged.
* `test_render_t1.py` and `test_render_t7.py` asserted the printed `DEC-34` and `R2` strings; they now assert those are
  absent and that the sentence they were cited for is present.
* The PyPI project page for `0.1.0.dev1` is fixed per version and still carries the old README until a release.

## What was cut and why

* **T12 still prints engineering references.** The software assurance record (T12) lists tests, fixtures and decision
  ids in its fixture and tolerance rows (about 33 hits: `DEC-11`, `DEC-75 (d)`, `tests/test_telemetry.py::...`,
  `D1 section 9`, `build day 11`). They come from `fixtures.py` and `halt_fixtures.py` row text and from
  `errors.py` meaning strings that gps-automation mirrors, which this task forbids changing. The review named T7;
  I fixed T7, T1, T2 and T8 and the two T12 captions that sat in the template. T12 is the next job; it needs a
  coordinated change with gps-automation.
* **Site documentation of `y_pred_operating_point`.** The site's `/docs/criteria` and `/docs/halt-gates` pages should
  list the new key and the new H04 wording. That is the site lane's file; not touched.
* **E2 (no non-interactive route to a first confirmed mapping)** is not in this brief.
* **The reader findings in section 6** (undeclared numeric age column banded by engine defaults, `run.json` carries no
  engine commit, and the rest) are not in this brief.

## Re-run

```
cd C:/Users/joshs/GPS/ProofPack/wt-efix
PYTHONPATH="$PWD/src" ../proofpack/.venv/Scripts/python -c "import proofpack;print(proofpack.__file__)"   # must print the wt-efix path
PYTHONPATH="$PWD/src" ../proofpack/.venv/Scripts/python -m pytest -q -p no:cacheprovider -m fix1011
PYTHONPATH="$PWD/src" ../proofpack/.venv/Scripts/python -m pytest -q -p no:cacheprovider
../proofpack/.venv/Scripts/python -m ruff check . && ../proofpack/.venv/Scripts/python -m ruff format --check .
```

Golden pages: `PROOFPACK_REGEN_GOLDEN=1` with `tests/test_e10_t2.py tests/test_render_t1.py tests/test_render_t7.py
tests/test_render_t8.py tests/test_t12.py`. DOCX templates: `python scripts/make_docx_templates.py`.

## Tomorrow needs

1. Move the site's `ENGINE_REF` pin to the merge of this branch, rebuild the wheel, rerun the site gates, redeploy.
2. Site docs: list `y_pred_operating_point` and the H04 wording; note that unknown criteria keys now halt H08; note that
   dates may be written unquoted and versions are kept as written.
3. The site still tells readers to `pip install "proofpack[docx]"` in `src/content/docs/docs/quickstart.md`,
   `src/content/docs/docs/run.md` and `src/data/demo_strings.mjs` (found by grep; site lane files, not touched).
   gps-automation has no such text. HALT meaning strings, which gps-automation mirrors, are unchanged.
4. T12 scrub (above).

## Needs from Josh

Nothing today. The decision to move the site pin is the orchestrator's.

## Open questions

1. `ledger.counted` changed meaning rather than gaining a second field. A consumer outside this repository that read
   `counted` as "the count could be read" would now see `false` for an estimate-only run. A grep of the
   site and gps-automation sources finds none; say if you want a separate `count_readable` field added instead.
2. `y_pred_operating_point` sits at the root of `criteria.yaml`. If you would rather it sat under `score:`, the move is
   one schema edit and one line in `declare.py`.

## Repair round 1 (lens 1 blocker B1: T8 ledger table)

**B1, E8 half fixed.** Two contradictions remained in T8 after the `counted` change.

* A licensed run with no criteria wrote `counted: false`, `acceptance_runs: 0`, but the row label still read
  "Acceptance runs recorded (including this run)". The label is now conditional on `ledger.counted` in
  `src/proofpack/templates/T8.html` and in `scripts/make_docx_templates.py` (T8.docx regenerated; T1 and T7 are
  byte-identical on regeneration): "including this run" when counted, "stored count; this run not included" otherwise.
* A run whose `ledger.commit` returned W15 after the documents were written left `run.json` at `counted: true` and the
  rendered T8 at "yes (this run is included ...)". The pages are rendered before the commit, so the engine cannot
  know the outcome when it writes them. Two changes: `proofpack.run.restamp_ledger_after_failed_commit` (called from
  `cmd_run` and `cmd_compare` when `record_ledger` returns a finding) rewrites `run.json` with `counted: false`,
  `acceptance_runs` and `manifest.ledger_count` at the stored count; and the `yes` branch now says the ledger is
  written after the document and that a write that does not succeed is reported as W15 on the console, not in the
  document. The word "failed" is avoided because the forbidden-word scan treats it as a verdict word.
* Not done: the rendered HTML/DOCX pages of a W15 run still print "yes" with that qualification, because they are
  written before the commit. Moving the commit before the render would reintroduce the DEC-47 defect (a run counted
  with no document on disk). Say if you would rather have a second pass that re-renders the pages after a W15.
* `scripts/mutation_sweep.py`: the two day-11 mutant patterns that quote the `finally:` block now include the two
  restamp lines. Golden `tests/fixtures/golden/T8.html` regenerated (one label line).

Regression tests (`tests/test_fix1011_engine.py`, `-k b1`): label by `counted`, the yes wording, `run.json` after a
patched W15 commit (`counted` false, count 0, manifest 0), the unpatched run still `counted` true with count 1, and the
DOCX T8 label and yes wording from a real `--format docx` run (including the licensed no-criteria run).

Proof they fail on the base (src and scripts stashed, tests kept):

```
git stash push -q -- src scripts
PYTHONPATH="$PWD/src" ../proofpack/.venv/Scripts/python -m pytest -q -p no:cacheprovider tests/test_fix1011_engine.py -k b1
FAILED ...test_b1_the_runs_row_label_says_including_this_run_only_when_it_was_counted
FAILED ...test_b1_the_yes_branch_does_not_claim_a_write_the_engine_cannot_know_of
FAILED ...test_b1_a_failed_ledger_commit_leaves_run_json_counted_false_and_the_stored_count
FAILED ...test_b1_the_docx_t8_carries_the_same_label_and_counted_wording_as_the_html
4 failed, 1 passed, 45 deselected
git stash pop
```

On the tip: `5 passed` for `-k b1`; full suite `2497 passed, 5 skipped`; `ruff check` and `ruff format --check` clean.
