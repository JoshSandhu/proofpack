# Lens 5 (regression and record) - build day 8, lane E, repair 4 at `375719c` - 2026-09-23

**Verdict: PASS.** No blockers. Each of the four lens-4 fresh-attack blockers (FA-B1 to FA-B4) no
longer reproduces on its literal inputs, and neither do lens-4 regression N1, N2 and N5. Every
figure in the repair-4 note that I re-ran matched, except two that were measured before the final
commit (N2 below). Full suite: `1146 passed, 1 skipped, 1 xfailed`, in Git Bash and in PowerShell 5.1
(with `PROOFPACK_TR39_FULL` set; without it the worktree gives `1145 passed, 2 skipped, 1 xfailed`,
see N4). Markers: `day8` 358, `day7` 139, `day6` 285, `day5` 54, `ap2` 88 in both shells; `day4` 182,
`day3` 29 + 1 xfailed, `day2` 40, `day1` 59 + 1 skipped in Git Bash. `--collect-only` gives
60 / 40 / 30 / 182 / 54 / 285 / 139, the `7b2ca2a` counts. The day-8 sweep at `375719c` gives
`92 planted, 92 killed, 0 survived; 1297 s`, exit 0 (76 day-8 + 16 `ap2`, run on the committed tree with `PROOFPACK_TR39_FULL` set). With the new and changed test files copied into `23f3d9f`, the run gives
`20 failed, 183 passed`, the note's figure, and each first `E` line equals the note's quote.
Seven non-blocking items follow. N1 is an output change on `y_pred`-only runs that the S4 list
omits, under a sentence ("Nothing else") that is false. N3 is a non-equivalent mutant of mine
(the second TR39 pass dropped) that survives `-m day8`.

Worktrees under `scratchpad/lens-E8-r5-regression/`: `head` at `375719c`, `base` at `23f3d9f`,
`mut` at `375719c` for my mutations, and `sweep` at `375719c` for the sweep. I forced
`PYTHONPATH=<worktree>/src` and checked, before each figure, that
`python -c "import proofpack;print(proofpack.__file__)"` printed that worktree's own
`src\proofpack\__init__.py`; each probe script asserts or prints the path. All four worktrees
are removed. In the main tree I ran read-only commands, wrote only this note and committed nothing.

## Blockers

None.

## Non-blocking

**N1 - A `y_pred`-only (or `lower_is_positive`) run loses the calibration guidance anchor, and the
S4 list omits it under "Nothing else" (sentence violation).** `run.json` `guidance_refs` is built from
the claims' `guidance_ref`s. With no `CALIB_NA` claim, `FDA_AIDSF_CALIBRATION` is no longer resolved.
Measured on `make_cohort(n=300, with_y_pred=True)` without the score column (`probe/refs.py`):
`guidance_refs` is `['FDA_AIDSF_PERF_VALIDATION', 'FDA_AIDSF_SUBGROUP_PERF']` at `375719c` and
`[..., 'FDA_AIDSF_CALIBRATION']` at `23f3d9f`; T8 carries `FDA_AIDSF_CALIBRATION` 0 times against 3,
and the page is 30,037 bytes against 30,576. The same holds for a probability declared
`lower_is_positive` (`score_not_positive_class_probability`, 200 rows, 59 claims against 60). The
repair-4 note ("4. **Nothing else.** No CLI flag, default, output path or JSON key changed") and the
handoff's S4 list name the claim-id shift but not the `guidance_refs` row or the T8 anchor row. No key
changed, so DEC-43's letter ("every ... JSON key") is met; the "Nothing else" sentence is not. Whether
dropping the calibration anchor is wanted on a run whose calibration section still prints its
suppression reason is Josh's (it follows from open question 1 of the r4 handoff).
Repro (in `head`): `PYTHONPATH=$L/head/src python $L/probe/refs.py $L/head`, then the same with `base`.

**N2 - Two figures in the note were measured before the committed tree.** (a) `fp.py` reads the main
tree's `README.md`, which the repair edited after the measurement: at `375719c` it gives **3,257**
sentences, **2,911** accepted at `23f3d9f` and at `375719c`, 0 newly rejected, 0 codes changed (note:
3,253 / 2,907 / 0 / 0). The four extra sentences are the rewritten README lines; my JSON differs from
the repairer's `fp/new.json` in those keys only. (b) `ruff format --check .` gives
`160 files already formatted` in both shells and in the main tree (note: 159). Ruff 0.16.6 counts
the 69 `.md` files as well as the 91 `.py`; the handoff `2026-09-23_E_r4.md` joined after the count.
The "0 newly rejected" and "no reformat needed" conclusions hold.

**N3 - My own mutants (`probe/my_mutants.py`, `-m day8`, `mut` worktree, tree clean after).** Twelve
planted; seven killed (`gate_two_ops_allowed`, `dash_marked_customer_text`, `hand_map_alpha_removed`,
`hand_map_tlv_removed`, `letters_only_keeps_space`, `tr39_ascii_letters_mapped`, and lens-4's
`second_earlier_reading_dropped` and `rn_first_only`, now killed by
`test_each_reading_has_a_literal_that_pins_it` - lens-4 N5 is closed). Survived:
- `tr39_second_pass_dropped` (`_tr39_mapped` returns `NFKC(once)` without the second map):
  **non-equivalent**. Among single-letter substitutions into the listed words by a character that is
  not in `_TR39` but whose NFKC form contains one that is, **1,167** texts are rejected at `375719c`
  and accepted under the mutant, for example `satisfactorˠ` (U+02E0 MODIFIER LETTER SMALL GAMMA) and
  `faևl` (U+0587). `358 passed`. No test feeds such a literal, and the sweep has no mutant for the
  line. The docstring's reason for the pass ("NFKC can produce a character the map lists") is true
  on these inputs.
- `calib_na_seq_gap` (the `seq += 1` moved above the reason check): non-equivalent. On a
  `y_pred`-only document the ids would keep a gap instead of shifting down by one, which is the S4
  sentence "the later claim ids shift by one"; no test pins it. I measured the ids contiguous
  (`CL-0001`..`CL-0059`) at `375719c`.
- `ingest_dec61_call_removed`: survives, as the note declares (carried 5). With it, the CLI still
  exits 3 with no directory, through `overall_block` (the DEC-61 test asserts both and passed).
- `ambiguous_kept_first` (`metric_ref_pointers` keeps the first of two Numbers sharing a string):
  equivalent on every document I fed; I could not construct a shared string (below).

**N4 - The TR39 regeneration test skips wherever `workflows/data/` is absent: CI, every worktree,
and the sweep's copies.** It ran in the main tree (the note's `1 skipped` is day 1's) and in my runs
with `PROOFPACK_TR39_FULL` set. On a public-repo CI run the committed subset is compared with no
source. With the file present, one tampered entry (`0x0399: "l"` -> `"i"`) gives
`vendored subset DIFFERS`, rc 1, and `1 failed` on the regeneration test. The orchestrator asked for
this test "when present", so this is a record, not a defect.

**N5 - `unmet`.** The orchestrator's list says `unmet` "must stay accepted". It is in `VERDICT_WORDS`
and is rejected at `23f3d9f` and at `375719c` (`test_prose_the_new_readings_leave_accepted` asserts
the rejection). The repair-4 note records this and keeps the rejection; the committed handoff
`2026-09-23_E_r4.md` does not mention it and does not put it to Josh ("unmet clinical need" is
ordinary clinical prose).

**N6 - Five new tests pass at `23f3d9f`; the note says "as their docstrings say", and three
docstrings do not.** Passing at `23f3d9f`: `test_the_tables_dec61_leaves_running_still_run`,
`test_calib_na_...[score2-score_not_probability-True]`,
`test_each_hand_mapped_letter_has_a_literal_the_tr39_readings_do_not_reject`,
`test_prose_the_new_readings_leave_accepted`, `test_a_dev_row_with_a_blank_y_pred_counts_under_dev_rows`.
The DEC-61 guard and the `dev`-row test say so; the hand-map test, the prose test (it says so of
`unmet` only) and the calibration case's shared docstring do not. Two of the 20 pre-fix failures are
`ImportError` (the module is absent at `23f3d9f`); the note says so.

**N7 - Records.**
- New functions whose docstring names a decision or lens id but no D1 / D4 / D5 line or oracle:
  `claims.calibration_suppression`, `claims.criteria_row_pointers`, `checker._tr39_mapped`,
  `gates.gate_h08_y_pred_operating_points` (DEC-61 only). `html.header_parts` names D4 section 1.5.
- The `metric_ref_pointers` docstring generalises ("an operating-point id holding `.`, `[` or `]` is
  read as the whole id"). I tried to falsify it and could not (below).
- DEC-62 names the `<title>` among the places the manufacturer's words sit inside `.customer-text`.
  A title cannot hold an element, so the repair removed the words from it (decision 5 of the note).
  That is a deviation from the decision's letter, recorded, for Josh.
- The golden's mask is still `manifest.numpy` only; `run_id`, `started` and `duration_s` are assembler
  constants (lens-3 N7, lens-4 N7).
- `python -m ruff format --check .` counts Markdown, so each untracked lens-5 note in `handoffs/` adds one
  to the main tree's count.

## What I could not break

- **The four lens-4 blockers on their literal inputs**, in `head`, both shells:
  - FA-B1: `repros5.py` prints `('C_br', '29/101 (28.7%) [20.8, 38.2]', '0.287', 'criterion not met')`
    and `('C_dot', '85/101 (84.2%) [75.8, 90.0]', '0.842', 'criterion met')`; lens 4's `a2_dotted.py`
    gives rc 0 and claim rejections `[]` for `t0.5`, `0` / `[0]` and `a[0`, each T8 row with its own
    engine Number (`[0]`: `est 0.287129 [0.207976, 0.381880]`). On the E7 e2e `run.json`, the
    synthetic document and a document with a criterion on each of the five calibration keys plus
    `auroc` and `prevalence`, `criteria_row_pointers` equals the old split pointers row for row, and no
    non-null `metric_ref` is unresolved. I could not construct two Numbers sharing one dotted string:
    metric names hold no `.`, the prefixes differ per family, and `threshold_free` / `auroc` / `brier`
    are reserved ids.
  - FA-B2: `repros5.py` prints `HaltError H08: ... (op_lo, op_hi) ... {'field': 'operating_points',
    'reason': 'no_score_column', 'operating_points': ['op_lo', 'op_hi']}`; lens 4's `a3_ypred_ops.py`
    CLI part gives rc 3, `No document was written.`, no directory (the script itself then raises on
    the missing directory, which is the halt).
  - FA-B3: `b5_calibna.py` gives `CALIB_NA claims []`, `accepted: []`; the hand-built claim gives
    `template_mismatch`.
  - FA-B4: `b3_homo.py` gives `ACCEPTED 2 of 37` (`үes`, `ᎠᎪᎪᎠ`, neither a listed word);
    `repros5.py` gives five `free_text_verdict_word` and `None` for `&sect; eight` (carried 1).
- **The statistical gate (DEC-61, DEC-12(i)) changes nothing else.** Five documents assembled in
  `head` and `base` (synthetic with CRITERIA + FAIRNESS; 300 rows with a score and ops 0.1 / 0.9;
  300 rows `y_pred`-only, one op; the 120-row `dev` / blank table; 200 rows `logit`), compared as
  sorted JSON without `claims`, `claim_rejections` and the four run-varying manifest fields: every
  top-level key is equal except `guidance_refs` on the two `y_pred`-only documents (N1). The
  `y_pred`-only block re-derived with my numpy count and statsmodels
  `proportion_confint(method="wilson")`: two-by-two `{tp 85, fn 16, fp 39, tn 160}` equal;
  sensitivity 85/101, specificity 160/199, PPV 85/124, NPV 160/176, max deviation `2.22e-16`.
  `git diff 23f3d9f 375719c -- src/proofpack/stats src/proofpack/criteria.py src/proofpack/cli.py
  src/proofpack/errors.py pyproject.toml schema/egress_schema.json uv.lock .github` is empty.
- **DEC-60, the vendored subset**, re-derived from the full file without repo code
  (`probe/tr39_own.py`): 763,128 bytes, SHA-256 `6ed3ee96...5b92`, 6,712 entries, 1,451 to one ASCII
  letter, 1,661 to ASCII letters only, 1,905 to ASCII letters once `Mn` marks are removed; my 1,905
  equal the vendored dict. The header lines (`Date`, `Version: 18.0.0`, copyright, trademark, terms URL)
  are the file's. `tr39_subset.py --check`: `vendored subset matches`, rc 0, in both shells and from
  the main tree with the note's relative path. The six corpus claims about TR39 targets (U+0399 `l`,
  U+A4D1 `P`, U+2C9F `o`, U+FF29 `l`, U+007C `l`) match the data. No listed word contains `rn`
  (40 verdict words, 8 certification words).
- **The note's measurements**, re-run: `subst.py` `52694` / `21948` at `fe35332` / **0** now;
  `fuzz.py` `650760` texts, 0 lost, 0 newly rejected; lens-2 `b_checker.py` 130 lines, byte-equal after
  the path line to both lens-4's `b_checker_head.txt` and the repairer's `b_checker_r4.txt`,
  `mutations: 8988 accepted: 11`, `swaps: 42849 accepted: 0`; claim counts 59 / 0 (`y_pred`-only,
  200 rows; 60 at `23f3d9f`) and 60 / 0 with `CALIB_NA` (`logit`).
- **Fails pre-build.** `test_e8_repair4.py`, `test_claims.py`, corpus `141`-`146` and the golden copied
  into `base`: `20 failed, 183 passed in 5.47s`. First `E` lines equal the note's table (the `C_br`
  index-1 diff, `assert 5 in (0, 2)` with `internal error: ValueError`, `DID NOT RAISE HaltError`, the
  two `CALIB_NA in [...] is False`, `'fai|'`, `'well calibratedness'`, `('\ua4d1assIng', [])`, two
  `ImportError`, the customer-text hits, the README literal, the sweep set, corpus `141`-`146`
  accepted, the golden).
- **Nothing weakened.** `git diff --name-status 23f3d9f 375719c -- tests/`: 7 `A`, 2 `M`, no `D`.
  Added `skip` / `xfail` / `mark`: `pytestmark = pytest.mark.day8`, one `parametrize`, and the
  regeneration test's `pytest.skip` when the full file is absent (N4). No marker removed. The changed
  expectation in `test_claims.py` is the corpus count 140 -> 146. The old `test_run_cli.py` from
  `7b2ca2a` against `375719c`: `4 failed, 19 passed`, lens 4's figure, including
  `test_a_clustered_run_has_no_overall_block_and_cluster_bootstrap_cells`.
- **The corpus.** 146 files, all `.json`, each with a `rule` and an `expected_reason_code` in
  `REASON_CODES` (44); `CORPUS_FILES = sorted(CORPUS.glob("*.json"))` and the parametrised test
  collects 146.
- **The sweep.** `--list`: 263 lines, 34 day5, 112 day6, 25 day7, 76 day8, 16 ap2, no duplicate id.
  `--marker day8` on the committed tree (the note's full run preceded two test edits): `92 planted,
  92 killed, 0 survived; 1297 s`, exit 0; each of the 13 repair-4 mutants and the re-targeted
  `checker_well_calibrated_substring_dropped` is `killed`. The `sweep` tree was clean after.
- **tokens.json against D5 section 3.1** (`probe/tokens_diff.py`, my parser of the table): 19 names,
  19 hex values, 0 differ, none extra; my WCAG recomputation equals every `contrast_computed`; the
  type and layout literals are in the section. The file is unchanged since `23f3d9f`.
- **The wheel.** `python -m uv build --wheel` holds `proofpack/narrate/tr39_confusables.py`, the three
  templates and the seven `_schema` files including `tokens.json`. Unpacked into
  `python -m venv --without-pip`: `Lib/site-packages` holds `proofpack` and
  `proofpack-0.1.0.dev1.dist-info`, 0 `.pth` files; with `PYTHONPATH` unset and `PYTHONNOUSERSITE=1`,
  `proofpack.__file__`, `resource_path("tokens.json")` and `tr39_confusables.__file__` resolve inside
  the venv, 1,905 entries, `free_text_reason('ꓑass')` gives `free_text_verdict_word`,
  `site.ENABLE_USER_SITE False`, and none of jinja2 / scipy / cryptography is loaded. The committed
  wheel test passes (`1 passed`). With `"design/tokens.json" = "proofpack/_schema/tokens.json"` removed
  from `pyproject.toml` in `mut`, it fails with `FileNotFoundError(f"packaged resource {name!r} not found")`.
- **The golden.** Rendered in `head` with `numpy` masked: 40,030 bytes, equal to the committed LF bytes.
  Unmasked, one line differs (`x.y.z` against `2.5.1`). The golden diff since `23f3d9f` is 13 lines:
  the `<title>`, three headers, seven operating-point cells (`op1`).
- **The footer removed** (the `<footer ...>` line of `base.html` emptied in `mut`): `5 failed, 19 passed`
  on `test_render_t8.py`, with `assert 0 == 3`, `assert 0 == 1`, `assert 0 == 2`, `assert (0 == 3)` and
  the golden.
- **The draft label removed.** `label_for` returning the document name for a draft row:
  `test_every_fda_aidsf_anchor_carries_the_draft_label_in_data_and_on_the_page` fails with
  `assert ('draft guidance (January 2025), not for implementation' in 'FDA draft guidance, ...`.
  The map rows' status edited from `draft - not for implementation` to `draft` (12 rows): the renderer
  refuses with `AnchorError: guidance map row 'FDA_AIDSF_DATA_MGMT' is a draft without the
  'not for implementation' qualifier ...` and the test errors.
- **Imports.** With jinja2, cryptography and scipy blocked by a meta-path finder and removed from
  `sys.modules`, `import proofpack, proofpack.stats, proofpack.narrate.checker,
  proofpack.narrate.claims, proofpack.gates` succeeds and loads none of the three.
- **CI and the lock.** `day8` is declared at `pyproject.toml` line 82; `ci.yml` reads the marker list
  (lines 41-50) and runs `uv sync --all-groups --locked` (lines 25, 84, 116); `uv.lock` has
  `name = "jinja2"` (line 497); `python -m uv lock --check --offline` gives `Resolved 63 packages`.
- **The note's commands, both shells.** `doctor --offline`: 17 `[ok` lines, `All essential checks
  passed.`, rc 0. E7 e2e run without a licence: `analysed 400 of 400 rows; criteria rows: 2 met, 2 not
  met, 5 not assessable`, exit 4, three files, `run.json` 253,943 bytes, 20 keys, 70 claims, 0
  rejections, 3 refs, `declaration_index [0, 1, 2, 2, 2, 3, 4, 5, None]`, no CRLF, no BOM. Without the
  mapping file: `HALT H07`, exit 3, no directory. `html_run.py`: exit 0, four files,
  `T8.html bytes 40375 CRLF False BOM False`. `repros5.py`: identical in both shells after the path
  line. (A first PowerShell attempt printed `exit=-1` because I piped the CLI into
  `Select-Object -First 2`, which stops the process; re-run without it: exit 4.)
- **The S4 list** otherwise: `cli.py`, `errors.py`, `criteria.py`, `pyproject.toml` and
  `egress_schema.json` are unchanged; the two schema changes are description text; the new H08 and its
  detail, the `CALIB_NA` absence and the T8 header / title / cell changes are as the note says. N1 is
  the one omission I found.

## What I could not check

- The sweep in PowerShell: I ran it in Git Bash, as the note did. `--list` I ran in Git Bash only.
- CI on ubuntu / Python 3.12: the engine is not pushed.
- A real-licence plain-CLI HTML run: no signing key on this machine; the HTML path ran through
  `main(..., registry=ephemeral_registry())`.
- Whether the three header lines of `confusables.txt` satisfy the Unicode licence: [unverified], as the
  note says (needs-from-Josh 1).

## Sentences I refused to write

- "The lookup reads every operating-point id correctly." Written instead: the ids fed and the four
  documents on which lookup equals the old split.
- "DEC-61 leaves every other table unchanged." Written instead: the five documents compared and the
  one key that differs.
- "The S4 list is complete." Refused: N1.
- "Every repair-4 line is pinned." Refused: N3.

## Re-run these

```bash
S=C:/Users/joshs/AppData/Local/Temp/claude/C--Users-joshs-GPS-ProofPack/a743e7e5-3be8-4d70-9ed0-681f5784a106/scratchpad
L=$S/lens-E8-r5-regression
git -C C:/Users/joshs/GPS/ProofPack/proofpack worktree add --detach $L/head 375719c
git -C C:/Users/joshs/GPS/ProofPack/proofpack worktree add --detach $L/base 23f3d9f
git -C C:/Users/joshs/GPS/ProofPack/proofpack worktree add --detach $L/mut 375719c
git -C C:/Users/joshs/GPS/ProofPack/proofpack worktree add --detach $L/sweep 375719c
cd $L/head && PYTHONPATH=$L/head/src python -c "import proofpack;print(proofpack.__file__)"
export PROOFPACK_TR39_FULL=C:/Users/joshs/GPS/ProofPack/workflows/data/confusables-18.0.0.txt
PYTHONPATH=$L/head/src python -m pytest -q -p no:cacheprovider              # 1146 passed, 1 skipped, 1 xfailed
cd $L/sweep && PYTHONPATH=$L/sweep/src python scripts/mutation_sweep.py --marker day8       # 92 planted, 92 killed, 0 survived
PYTHONPATH=$L/head/src python $L/probe/refs.py $L/head                      # N1: 2 refs, 0 CALIBRATION on page
PYTHONPATH=$L/base/src python $L/probe/refs.py $L/base                      # N1: 3 refs, 3
python $L/probe/my_mutants.py $L/mut tr39_second_pass_dropped calib_na_seq_gap   # N3: both SURVIVED
python $L/probe/tr39_own.py $L/head/src/proofpack/narrate/tr39_confusables.py      # 1905, equal
for w in head base mut sweep; do git -C C:/Users/joshs/GPS/ProofPack/proofpack worktree remove --force $L/$w; done
```

## What the next repair (or E9) needs

N1: add the `guidance_refs` / T8 anchor change to the S4 list (or decide the anchor stays). N3: a
literal such as `satisfactorˠ` in a repair-4 test and a sweep mutant for the second TR39 pass; a test
that the claim ids stay contiguous on a `y_pred`-only document. N5: put `unmet` to Josh.
