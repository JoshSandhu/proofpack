**Verdict: PASS. No blockers. Every behavioural claim of the E14 note reproduces at `a1840fc` in both shells: the cover row (T1 19 -> 3 entries, T8 7 -> 2), the section-7 margin lines (4 -> 2), `licence verify nonexistent.lic --offline` (exit 2 -> exit 4), and the re-prompt line; 32 of the 66 new tests fail at `3ee5601` and 34 pass, as the note says; all 14 mutants I planted were killed. Four non-blocking findings must still be fixed in the handoff or the next commit: the note's golden line count is wrong (N1); one test docstring sentence is half false (N2, a hard-rule violation, counter-example run below); the two new DOCX tests never run in CI (N3); and one note sentence says a test "guards the merge" without a recorded counter-example (N4; I ran one and the sentence holds).**

# E14 lens 1 (cold regression and record) on engine a1840fc - Wednesday 7 October 2026

Cold lens on `e14-lw01` at `a1840fc` (5 commits on `3ee5601`), against the builder's note `scratchpad/notes/E14_build.md`, the LW-01 log and the user review notes of 7 October.

Method. Three detached worktrees under the session scratchpad (`lens-E14-r1-regression/`): `tip` and `mut` at `a1840fc`, `base` at `3ee5601`. `PYTHONPATH` was set to each tree's `src`, and I checked it each time with `python -c "import proofpack;print(proofpack.__file__)"`. Each printed `...\lens-E14-r1-regression\<tree>\src\proofpack\__init__.py`; for `wt-e14` it printed `C:\Users\joshs\GPS\ProofPack\wt-e14\src\proofpack\__init__.py`. In `wt-e14` I ran tests only, with `PYTHONDONTWRITEBYTECODE=1`; `git status --short` there was empty before and after. Mutants were applied by a scratch script (`mutate.py`) and restored with `git checkout -- .`, and `git status --short` was empty after each one. Platform: Windows 11 Home 10.0.26200, Python 3.14.6. I made one slip and reversed it. A `git stash -u` in the `base` tree (to get a clean ruff-format count) wrote a `refs/stash` entry in the shared engine repo. It held only my five copied test files. I popped it within a minute, and `git stash list` has been empty since. All three lens worktrees are removed.

## Blockers

None.

## Non-blocking

### N1. The note's golden line count does not reproduce: 9 lines out and 6 in, not "6 lines out, 3 in"

The note says: "Goldens (3ee5601 -> a1840fc): 3 files, 6 lines out, 3 in." Measured with `git diff --numstat 3ee5601 a1840fc -- tests/fixtures/golden`:

```
3	5	tests/fixtures/golden/T1.html
2	3	tests/fixtures/golden/T2.html
1	1	tests/fixtures/golden/T8.html
```

That is 9 lines removed and 6 added (a net loss of 3). The per-file bullets underneath are right: the hunks are `-147 +147`, `-283,4 +283,2` (T1), `-152 +152`, `-380,2 +380` (T2) and `-146 +146` (T8), and the link counts (19 -> 3, 14 -> 2, 7 -> 2) match. Only the summary line is wrong. The handoff should print 9 out, 6 in.
Repro: `git -C C:/Users/joshs/GPS/ProofPack/proofpack diff --numstat 3ee5601 a1840fc -- tests/fixtures/golden`.

### N2. Hard-rule violation (sentence half false): `tests/test_e14_global_flags.py` docstring, "so a parser added later is covered without editing this file"

The note records no counter-example for this sentence, so I ran two in `mut`:
- **A new subcommand without the common parent**: `sub.add_parser("probe", help="x")` inserted before `licence`. 7 tests fail: the 6 `probe` cases (`unrecognized arguments: --offline` / `--quiet` / `--json-log`) and the walk test. So the "covered" half is true.
- **A correctly built new subcommand**: `sub.add_parser("probe", help="x", parents=[common])`. Result: `1 failed, 56 passed`, the failure being `test_the_walk_finds_every_command_and_the_nested_licence_parsers`. That test pins the exact set of 8 leaves, so no parser can be added, correct or not, without editing this file. The "without editing this file" half is false.

Fix: "the parametrised cases are generated from that walk; the walk test pins the 8 leaves, so a new parser is added to its set". Not customer-facing, hence not a blocker.
Repro: in a tree at `a1840fc`, add `sub.add_parser("probe", help="x", parents=[common])` above `lic = sub.add_parser("licence"` in `src/proofpack/cli.py`, then run `python -m pytest -q -p no:cacheprovider tests/test_e14_global_flags.py`.

### N3. The two E14 DOCX regression tests are skipped in every CI job; CI's `-m day14` reads 64 passed, 2 skipped

`test_e14_cover_row.py::test_docx_cover_row_names_the_distinct_documents` and `test_e14_margin_notes.py::test_docx_t1_prints_each_repeated_line_once_naming_every_id` start with `pytest.importorskip("docxtpl")` and carry only the `day14` marker. The main CI job is written without the `[docx]` extra, and the `docx-extra` job runs `-m ap4` only. Gate run 37629330981 log, job `pytest + ruff`:

```
SKIPPED [1] tests/test_e14_cover_row.py:90: could not import 'docxtpl': No module named 'docxtpl'
SKIPPED [1] tests/test_e14_margin_notes.py:94: could not import 'docxtpl': No module named 'docxtpl'
...
64 passed, 2 skipped, 2340 deselected in 3.88s      (the -m day14 step)
```

The second test is the repair's own regression test for the RED gate on `834634c`. The behaviour is still pinned in CI by the `ap4` tests, which run in the `docx-extra` job:
- Reverting the whole `T1.docx` to `3ee5601` (mutant M5) fails `test_ap4_roundtrip.py::test_draft_anchor_labels_survive_in_the_html_count[T1]`.
- Reverting only `build_t1`'s cover loop to `guidance_refs` and regenerating `T1.docx` (M15), run with `PROOFPACK_REQUIRE_DOCX=1 -m ap4`, gives `2 failed, 196 passed` (`..._html_count[T1]` and `test_ap4_templates.py::test_the_regenerated_template_equals_the_committed_one_part_by_part[T1]`).

So nothing is unpinned on Linux. But the note's "-m day14: 66 passed" is a Windows figure only, and these two tests skip the `tests/ap4_docx.py::needs_extra` route, under which `PROOFPACK_REQUIRE_DOCX=1` refuses the skip. Fix: mark both `ap4` and use `needs_extra`, or say in the handoff that they run locally only.
Repro: `gh run view 37629330981 --repo JoshSandhu/proofpack --log | grep test_e14`.

### N4. Note sentence without a recorded counter-example: "`test_every_block_still_cites_every_anchor_it_names` passes there and guards the merge"

The note gives no failing run for "guards". I ran two:
- M1: `base.html` with the `data-also` attribute removed.
- M14: `distinct_notes` never appends to `also`.

The test fails under both (M1 failed 11 tests in my set, among them this one, `test_render_t1.py::test_every_fda_draft_anchor_is_labelled_in_every_margin_note` and `test_e10_t2.py::test_every_pccp_anchor_is_labelled_from_the_map_and_every_aidsf_anchor_is_draft`). The sentence holds, but only now that a counter-example has been run. The handoff should cite M1/M14 or say "inspects that every anchor id of each block appears in a line's href or data-also".

### N5. Minor wording, `src/proofpack/cli.py` comment on `ALL_HIGH_REPROMPT`: "re-prompted without being told how to accept"

The old line `  answer a or q` did name `a`. The LW-01 record (review note 17) says only that `y` re-prompts and asks for "type a to accept". "Without being told to press Enter, or what a and q do" is what the record supports.

### N6. 4 of the 32 tests that fail at 3ee5601 fail on a missing name, not on a behavioural assertion

These are `test_cover_documents_unit` (`AttributeError: ... no attribute 'cover_documents'`), `test_lines_that_differ_in_any_visible_part_stay` (`distinct_notes`), `test_the_reprompt_line_is_pinned` and `test_y_then_q_halts_and_y_never_accepted` (`ALL_HIGH_REPROMPT`). Collection succeeded in each case (no import abort).
- The first two pin the new functions' rules, and their mutants were killed (M2, M3, M4, M12, M14).
- `test_y_then_q_halts_and_y_never_accepted` asserts behaviour that already held at `3ee5601`: `y` re-prompts, `q` is H07, `decided_by` stays `proposed`. What it pins is the constant's name.

The behavioural fail-at-base assertions the note quotes reproduce exactly: `('T1 (render)', 19, 3)`, `assert 19 == 3`, `4 == 2` (section 7), `2 == 1` (T2 section 5), `0 == 1` (DOCX bracket), `unrecognized arguments: --offline`, and `'  answer a or q' != '  type a and press Enter to accept, or q to quit'`.

### N7. Open item the note omits (it predates E14): `proofpack fixtures --offline` reports a run-dependent `small_only_values` for the F19 synthetic cohort

In 15 runs at `3ee5601` it read `7 6 7 7 7 7 6 7 7 7 7 7 7 7 7`. At `a1840fc` it read 6 in 1 run of 12. `src/proofpack/f19.py` is unchanged by E14. The row summary (`rows 46: matched 35, not matched 0, ... not built 4, suite only 7`) and the exit code (0) did not vary. The most likely cause (not proven) is that a run-dependent float elsewhere in `run.json` sometimes equals a small-cell value, which moves it into `shared`. One fixtures-report field therefore differs between two runs of the same commit. This is for lane E's list, not this package.

## Re-run figures (all measured in this session)

| command | Git Bash | PowerShell 5.1 | note |
|---|---|---|---|
| full suite, `wt-e14` at a1840fc | 2402 passed, 4 skipped (315 s) | 2402 passed, 4 skipped (312 s) | 2402 / 4 both: reproduces |
| full suite, scratch `tip` at a1840fc | 2401 passed, 5 skipped (322 s) | not run | the extra skip is `test_e8_repair4.py:405` (no sibling `workflows/data`), the path dependence the note describes |
| full suite, scratch `base` at 3ee5601 | 2335 passed, 5 skipped (321 s; the same `test_e8_repair4.py:405` path skip) | not run | reproduces the note's scratch-tree 2335 / 5 (the note's figure is PowerShell); the note's 2336 / 4 was in `wt-e14` |
| `-m day14` / `day13` / `day12` at a1840fc | 66 / 133 / 199 + 3 skipped | 66 / 133 / 199 + 3 skipped | reproduces |
| the four E14 files, a1840fc | 66 passed | 66 passed | reproduces |
| the four E14 files copied into 3ee5601 | 32 failed, 34 passed | 32 failed, 34 passed | reproduces (4 + 5 + 20 + 3) |
| `ruff check .` / `ruff format --check .` at a1840fc | All checks passed! / 355 files already formatted | same | reproduces (350 at 3ee5601) |
| `licence verify nonexistent.lic --offline` | 3ee5601 exit 2 `unrecognized arguments: --offline`; a1840fc exit 4 `status: refused (no_file)` | same in both trees | reproduces |
| `doctor --offline` | exit 0 both trees | exit 0 both trees | output identical apart from the tree path |
| `fixtures --offline --out <dir>` | exit 0; rows 46: matched 35, not matched 0, not built 4, suite only 7, both trees | same | reproduces; `fixtures_report.json` differs only in tree path, time, `git_sha` and N7 |
| `measure.py <tree>` (site's 5,000-row CSV) | 3ee5601: T1 324,900 B, cover 19 (AI-DSF 12, internal 2), table 19, 3 documents; T8 cover 7 for 2; section 7 4 lines, 2 distinct, 2 repeats. a1840fc: T1 320,859 B, cover 3 (AI-DSF 1, internal 0), table 19; T8 cover 2; section 7 2 lines, 0 repeats | identical figures | reproduces |
| `bash workflows/ci_gate.sh C:/Users/joshs/GPS/ProofPack/wt-e14 a1840fc` (my run) | `gate: run 37634363986 ci: success`, `gate: GREEN a1840fc`, exit 0. Branch `ci/a1840fc-1791382169-18586` deleted (`git ls-remote origin "refs/heads/ci/*"` printed nothing). All 7 jobs success on head sha a1840fca | - | the note's run 37629330981 `ci: success` is confirmed separately below |

The recorded gate run, read from GitHub (`gh run view 37629330981`): head sha `a1840fca9425b301bb5393aa8b978b1a1f5eb0ff`, branch `ci/a1840fc-1791379957-14742`, conclusion `success`. All 7 jobs were success: wheel artefact, pip-audit, import proofpack (scipy uninstalled), proofpack run inside unshare -rn, pytest -m ap4 with the [docx] extra (197 passed, 1 skipped), Docker image smoke, pytest + ruff (2267 passed, 139 skipped). The RED run 37627915858 on `834634c` is in the builder's gate log as `test_ap4_roundtrip.py::test_draft_anchor_labels_survive_in_the_html_count[T1]`. I re-ran that pair at `834634c` locally: `test_docx_t1_prints_each_repeated_line_once_naming_every_id` and `..._html_count[T1]` both fail, 2 failed, 24 passed.

## What I could not break

- **Nothing weakened.** `git diff --name-status 3ee5601 a1840fc` lists 23 modified files and 5 added (`tests/e14_pages.py` and the four `test_e14_*.py`), none deleted. The diff adds no `skip`, `xfail` or `.only` and removes no marker. The new `importorskip` lines are N3. `.github/` is untouched. The only loosened assertion is `test_render_t1.py`'s floor, 20 -> 19. I measured 21 margin lines at `3ee5601` and 19 at `a1840fc` (`probe_docx.py`). The same test now also checks every `data-also` id for the draft class (killed by M1 and M14).
- **14 mutants, all killed** (each run on the E14 files plus `test_render_t1`, `test_e10_t2`, `test_ap4_roundtrip`, `test_mapping_repair2/3` and `test_render_t8`; baseline 187 passed):
  - M1: `data-also` removed.
  - M2: `distinct_notes` keyed on the label only. Killed by the unit test alone; no page has two notes with one label and different sections.
  - M3: internal rows kept on the cover.
  - M4: cover deduped by id.
  - M5: `T1.docx` reverted.
  - M6: T2 `notes()` without the filter.
  - M7: `licence show` without `common`.
  - M8: `y` added to `ACCEPT_ANSWERS`.
  - M9: T8.html cover back to `guidance_refs`.
  - M10: T2.html cover back to `guidance_refs`.
  - M11: `T8.docx` reverted.
  - M12: cover order reversed.
  - M13: a new subcommand without `common` (N2).
  - M14: merged ids dropped.
- **The DOCX templates are generated, not hand-edited.** `python scripts/make_docx_templates.py --out <dir>` at `a1840fc` writes T1.docx 53,092 B, T7.docx 40,591 B and T8.docx 42,719 B, each byte-identical (`cmp`) to the committed file.
- **Draft label and register.** On every page the cover carries the AI-DSF label once, with "draft guidance (January 2025), not for implementation". `run.json` `guidance_refs` keeps `draft: true` on every AI-DSF entry (`test_the_draft_status_stays_in_the_structured_data` passes at both shas). The guidance table keeps 19 rows (T1) and 7 (T8).
- **Golden changes.** They are limited to items 1 and 2: three cover rows and two margin blocks. The T7 and T12 goldens are unchanged.
- **Site copy.** A grep of `proofpack-site` (excluding `node_modules`) found no `answer a or q`.

## What I could not check

- **The Linux-only paths.** I could not run the reference-image determinism and the network-namespace run on this machine. I read them from the recorded run's job conclusions and from my own gate run (above).
- **The licence email's `--templates T1,T7,T8` buyer path.** I did not re-run it end to end with a site-issued licence; the measurement used an ephemeral-signed licence, as the note's did.
- **The root cause of N7.** Not proven.
- **The base full suite in PowerShell.** Not re-run; the Git Bash base figure is above.

## Changes for other lanes (site pin move past 8ef3266)

These are as the note lists them, plus what I measured:
- the cover row of T1, T2 and T8 (HTML and DOCX);
- one margin line fewer in T1 section 7 and in T2 section 5, and a new `data-also="..."` attribute on a merged `aside.margin-note`;
- the DOCX margin bracket can now hold several ids (`[FDA_STAT2007_CI, FDA_STAT2007_INDETERMINATE]`);
- the re-prompt string `  type a and press Enter to accept, or q to quit`;
- the usage line of `licence verify --help` went from `usage: proofpack licence verify [-h] file` to `usage: proofpack licence verify [-h] [--offline] [--quiet] [--json-log] file`. I measured `verify` only; `show` and `install` take the same parent;
- T1.html of the 5,000-row run went from 324,900 B to 320,859 B, and T8.html from 37,807 B to 36,804 B.

No CLI default, path or JSON key changed.
