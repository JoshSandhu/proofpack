**Verdict: FAIL. 1 blocker. Every figure in the E14 repair 2 note reproduces at `ae23aa5`, in Git Bash and in PowerShell 5.1. In `wt-e14` the full suite gave 2420 passed, 4 skipped in both shells; `-m day14` 84, `day13` 133, `day12` 199 + 3 skipped, `ap4` 200. ruff check and format are clean (362 files). The new test file gives `4 failed, 8 passed` at `e67c5fa`, on the lines the note quotes. Lens 2's counter-examples T3 and T5, and the `skipif(True, reason=SKIP_REASON)` copy, each give `1 passed` on the old meta-test and `1 failed` on the new one. My gate run 37650538581 on `ae23aa5` was GREEN, 7 jobs, all success. B1: the repair deleted an assertion of the old meta-test, `assert "importorskip" not in inspect.getsource(fn)`, and the new meta-test does not replace it. The note, the commit message and the new docstring do not say so; the docstring calls the new test the old one's "replacement". The mutant the old assertion killed (importorskip put back inside a DOCX test that keeps `ap4` and `needs_extra`) now passes the meta-test. With the extra missing and `PROOFPACK_REQUIRE_DOCX=1`, that DOCX test then gives `1 skipped` where it gave `1 failed` (`DocxExtraMissing`). That is the silent-skip class FA-B1/RG-N3 was opened for.**

# E14 lens 3 (cold regression and record) on engine ae23aa5 - Wednesday 7 October 2026

Cold lens on `e14-lw01` at `ae23aa5`, which is one commit on `e67c5fa`. It checks the repairer's note `scratchpad/notes/E14_repair2.md` and closes out the lens-2 notes `2026-10-07_E_e14_lens2_fresh-attack.md` and `2026-10-07_E_e14_lens2_regression.md`.

Method:
- **Worktrees.** I used four detached worktrees under `scratchpad/lens-E14-r3-regression/`: `tip` (`ae23aa5`) for the full suite, `mut` (`ae23aa5`) for mutants and markers, `pre` (`e67c5fa`) and `a18` (`a1840fc`).
- **PYTHONPATH.** It was set to each tree's `src` (Windows form, through `cygpath -w`, in Git Bash). I checked it each time with `python -c "import proofpack;print(proofpack.__file__)"`, which printed `...\lens-E14-r3-regression\<tree>\src\proofpack\__init__.py`. For `wt-e14` it printed `C:\Users\joshs\GPS\ProofPack\wt-e14\src\proofpack\__init__.py`.
  - A slip and its re-run: my first IOS run in Git Bash joined two POSIX paths with `;`, and `proofpack.__file__` printed the main tree. I discarded that output and re-ran with `cygpath -w`; the IOS figures below come from the re-run.
- **wt-e14.** I ran tests only, with `-p no:cacheprovider` and `PYTHONDONTWRITEBYTECODE=1`.
- **Mutants.** Each was applied by a scratch script and reverted with `git checkout -- .`. `git status --short` was empty after every run.
- **Platform.** Windows 11 Home 10.0.26200, Python 3.14.6. I made no commits.

## Blockers

### B1. A deleted gate assertion that no record mentions: `importorskip` inside an E14 DOCX test is no longer refused

At `e67c5fa`, `tests/test_e14_repair1.py`'s meta-test ended with:

```
-        assert "importorskip" not in inspect.getsource(fn), (module, name)
```

`ae23aa5` deletes that test. Its replacement, `tests/test_e14_repair2.py::test_fa_b1_other_e14_modules_tests_naming_docx_or_importorskip_carry_ap4_and_needs_extra`, uses `importorskip` only to choose which tests to inspect. It never asserts that an inspected test is free of it. None of these records the dropped check:
- the note's "What landed", which describes the deleted test only as "It took only the E14 test functions whose source held the text `render_docx`";
- the commit message;
- the new module docstring ("It is deleted. Its replacement below, ...").

Counter-example, constructed and run. Mutant IOS adds `pytest.importorskip("docx")` as the first statement after the docstring of `test_e14_cover_row.py::test_docx_cover_row_text_equals_the_html_cover_labels_in_order`, and keeps `@pytest.mark.ap4` and `@needs_extra`.

| tree | meta-test | result |
|---|---|---|
| `e67c5fa` (`pre`) | old, `tests/test_e14_repair1.py -k fa_b1` | `1 failed, 6 deselected`, `AssertionError: ('test_e14_cover_row', 'test_docx_cover_row_text_equals_the_html_cover_labels_in_order')` |
| `ae23aa5` (`mut`) | new, `tests/test_e14_repair2.py -k fa_b1` | `1 passed, 11 deselected` |
| `ae23aa5` (`mut`) | the whole of `tests/test_e14_repair2.py` | `12 passed` |

What it lets through. I hid docxtpl, docx and matplotlib with a `-p` plugin that sets `sys.modules[name] = None`, set `PROOFPACK_REQUIRE_DOCX=1`, and ran `-m ap4 -rs tests/test_e14_cover_row.py` in `mut`:
- unmutated: `1 failed, 4 deselected`, `proofpack.render.docx.DocxExtraMissing: --format docx needs the [docx] extra ...`;
- IOS: `1 skipped, 4 deselected`, `SKIPPED [1] tests\test_e14_cover_row.py:99: could not import 'docx': import of docx halted; None in sys.modules`.

So under the variable whose purpose is to refuse the skip, the DOCX test skips silently and the meta-test stays green. Lens 2 (regression) counted this exact mutant ("T3, `importorskip` re-added: `'importorskip' not in ...`") among the ones the old test killed. The repair therefore removes a kill that a lens had measured, with no line in the record.

Today no E14 test calls `importorskip` (`grep -c importorskip` gives 0 in `test_e14_cover_row.py`, `test_e14_margin_notes.py`, `test_e14_global_flags.py` and `test_e14_map_prompt.py`). The shipped tests are not under-run. The defect is a weakened gate plus a record that omits it.

Repair, either of:
- put the assertion back in the new meta-test (an `importorskip` call in an inspected test's code fails it), with IOS as the counter-example to run first;
- or record the removal in the note and the handoff, and drop "replacement".

Repro: in a tree at `ae23aa5`, add `    pytest.importorskip("docx")` after the docstring of `test_docx_cover_row_text_equals_the_html_cover_labels_in_order`, then run `python -m pytest -q -p no:cacheprovider tests/test_e14_repair2.py`. Result: `12 passed`.

## Non-blocking

- **N1. At `e67c5fa` the new meta-test fails only because it finds the old meta-test.** The first failing line there is `Extra items in the left set: ('test_e14_repair1', None, 'test_fa_b1_rg_n3_every_e14_docx_test_is_selected_by_ap4_and_takes_the_extra_rule')`. `e67c5fa`'s two DOCX tests already carry `ap4` and `needs_extra`, so the "fails pre-build" run pins nothing about them. The note says so ("Side effect measured at e67c5fa"). The pinning evidence is the mutant table, and it reproduces (below).
- **N2. Two of the scanner's described behaviours are not pinned by any committed test.** I mutated `test_e14_repair2.py` itself:
  - S4, `or t == "importorskip"` deleted: `12 passed`;
  - S5, `"docx" in t.lower()` made case-sensitive: `12 passed`;
  - S6, the `is needs_extra.mark` assertion deleted: `12 passed`. Here the committed tests do not fail, but the SK mutant (`skipif(True, reason=SKIP_REASON)`) does fail it when run.

  Every FLAGGED source also contains lower-case `docx`, so the "or importorskip" and "in any case" parts of the name and docstring are implemented but unpinned. The code does what the sentences say, so these are not false sentences.

  Killed, for comparison:
  - S1, the docstring not stripped: `docstring_only` fails;
  - S2, no helper recursion: `helper` and `fixture_argument` fail;
  - S3, no class scan: `class_method` fails;
  - S7, the whole unparsed function text: 3 fail.
- **N3. The `comment_only` control cannot fail for any AST-based scanner.** Comments are not in the AST, so no mutant I made could fail it (S1-S7: 0 failures of `[comment_only]`).
- **N4. Survivors outside the stated scope.** A test that builds its format from a module-level constant (`FMT_X = "do" + "cx"`, then `cli.main(["run", "--format", FMT_X, ...])`) passes the new meta-test (`1 passed`). Each of these is out of scope as stated in the docstring and the note: the test names no `docx` text, fixtures from other modules are not read, and its own file is excluded. Not a false sentence; recorded.

## Lens-2 blockers and findings: each is closed except where B1 says otherwise (re-run, not read)

- **FA-B1 / RG-N2 (the meta-test was named for more than it inspected).** Mutants at `ae23aa5` on the new meta-test, and at `e67c5fa` on the old one:

  | mutant | old meta-test (`e67c5fa`) | new meta-test (`ae23aa5`) |
  |---|---|---|
  | T3 (lens 2's `EXTRA_TEST`, copied from `lens-E14-r2-fresh-attack/mutate.py`) appended to `test_e14_cover_row.py` | `1 passed, 6 deselected` | `1 failed, 11 deselected`; `Extra items in the left set: ('test_e14_cover_row', None, 'test_lens2_docx_cover_via_the_cli')` |
  | T5 appended to `test_e14_global_flags.py` | `1 passed` | `1 failed`; `('test_e14_global_flags', None, 'test_extra_docx_via_cli')` |
  | `@needs_extra` -> `@pytest.mark.skipif(True, reason=SKIP_REASON)` on the cover test | `1 passed` | `1 failed`; `AssertionError: (..., (True,))` |
  | `@pytest.mark.ap4` removed from the cover test | `1 failed` | `1 failed`; `assert 'ap4' in {'day14', 'skipif'}` |
  | `@needs_extra` removed from the margin test | `1 failed` | `1 failed`; `assert [] == ['the [docx] ...p is refused']` |
  | IOS (B1) | `1 failed` | **`1 passed`** |
  | module-level `FMT_X` (N4) | `1 passed` | `1 passed` |

  The note's table reproduces row for row. The new name now matches what the test inspects.
- **FA-B2 / RG-N1 (the `e67c5fa` commit-message quote).** In `a18` (`a1840fc`), with `e67c5fa`'s `tests/test_e14_repair1.py` copied in, `-k fa_b1` gave `1 failed, 6 deselected`, first on `Extra items in the left set`. With the expected name edited to `test_docx_cover_row_names_the_distinct_documents` it gave `1 failed, 6 deselected`, `assert 'ap4' in set()`. The corrections file says exactly this.
- **834634c correction.** `git show 3ee5601:src/proofpack/cli.py`: line 304 is the `[a]ccept / [q]uit? ` prompt and line 309 is `say("  answer a or q")`. `LW01_log.md` line 7 reads "prompt takes `a` (`y` re-prompts)". `user_review_notes.md` line 26 is note 17. The corrections file matches all three.
- **RG-N3 (the docstring "every CI job skipped them").** I read run 37631774505 (head `a1840fca9425...`) from GitHub in this session:
  - job `pytest + ruff`: `SKIPPED [1] tests/test_e14_cover_row.py:90: could not import 'docxtpl': No module named 'docxtpl'`, and the same for `tests/test_e14_margin_notes.py:94`;
  - job `pytest -m ap4 with the [docx] extra installed`: `197 passed, 1 skipped, 2208 deselected`.

  The new wording matches.
- **Sentence guards.** `[every_e14_docx_test_is_selected_by_ap4]` and `[every CI job skipped them]` each fail at `e67c5fa` with `assert '...' not in ...`. They are literal substrings, as the note says (lens-2 FA-N3, carried).
- **RG-O1.** The corrections file is on the branch. The E14 handoff is still absent, which the note records as carried.

## What I could not break (with figures)

- **Fails pre-build.** `tests/test_e14_repair2.py` from `ae23aa5`, copied alone into `pre` (`e67c5fa`): `4 failed, 8 passed` in Git Bash (1.01 s) and in PowerShell 5.1 (0.68 s). The 4 that fail are the meta-test (`Extra items in the left set`), the corrections test (`FileNotFoundError ... 2026-10-07_E14_commit_message_corrections.md`) and the two sentence guards. No test aborted on import. This matches the note.
- **Nothing weakened, apart from B1.**
  - `git diff --name-status e67c5fa ae23aa5`: 4 added (3 handoffs, `test_e14_repair2.py`), 1 modified (`test_e14_repair1.py`), 0 deleted. `git diff --name-status 3ee5601 ae23aa5 | grep ^D` printed nothing.
  - `git diff --stat e67c5fa ae23aa5 -- src scripts tests/fixtures .github pyproject.toml README.md design` printed nothing.
  - The diff adds no `xfail`, `.only` or bare skip, and removes no marker. The removed lines are the old meta-test, including the assertion in B1.
  - `day14` sits in `pyproject.toml` beside `day13`. CI run 37650538581's main job ran `-m day14`: `82 passed, 2 skipped`.
- **No behaviour changed.** There is no `src/` diff. `fixtures --offline` at `e67c5fa` and at `ae23aa5` each exited 0 with 46 rows: 35 matched, 0 not matched, 4 not built and 7 suite only. Of the 2,486 leaves of `fixtures_report.json` on each side, 5 differ: `duration_s`, `generated`, `git_sha`, F13's `reason` (it embeds the sha) and `doctor[12].info` (the tree's path).
- **CLI spot checks at `ae23aa5`.**
  - `licence verify` and `licence install` with `nonexistent.lic --offline --quiet --json-log`: exit 4 each, so the flags parse after the sub-subcommand.
  - `licence show --offline`: exit 0.
  - `cli.ALL_HIGH_REPROMPT == '  type a and press Enter to accept, or q to quit'` and `ACCEPT_ANSWERS == ('a', 'accept')`.
  - My `licence show nonexistent.lic` gave exit 2 because `show` takes no file. That was my error, not a finding.

## Re-run figures (all measured in this session; PYTHONPATH forced and printed each time)

| command | Git Bash | PowerShell 5.1 | note says |
|---|---|---|---|
| full suite, `wt-e14` | 2420 passed, 4 skipped in 306.31 s | 2420 passed, 4 skipped in 330.15 s | 2420 / 4: reproduces |
| full suite, scratch `tip` | 2419 passed, 5 skipped in 341.77 s | not run | the 5th skip is `test_e8_repair4.py:405` (`confusables-18.0.0.txt` not present, because a scratch tree has no sibling `workflows/data`); 2424 collected, as in `wt-e14` |
| `-m day14` / `day13` / `day12` / `ap4` | 84 / 133 / 199 + 3 skipped / 200 (`mut`) | 84 / 133 / 199 + 3 skipped / 200 (`wt-e14`) | reproduces |
| `-m ap4` with `PROOFPACK_REQUIRE_DOCX=1` | 200 passed (`mut`) | - | - |
| `tests/test_e14_repair1.py tests/test_e14_repair2.py` | 18 passed | 18 passed | reproduces |
| `ruff check .` / `ruff format --check .` | All checks passed! / 362 files already formatted | same | reproduces |
| `python -m proofpack.cli doctor --offline` | exit 0 | exit 0 | reproduces |
| `python -m proofpack.cli fixtures --offline --out <dir>` | exit 0, rows 46: matched 35, not built 4, suite only 7 | same | reproduces |
| `bash workflows/ci_gate.sh C:/Users/joshs/GPS/ProofPack/wt-e14 HEAD` (my run) | `gate: run 37650538581 ci: success`, `gate: GREEN ae23aa5`, exit 0 | - | see below |

No command in the note failed in either shell.

**The note's gate runs, read from GitHub.**
- Run 37646260598 (branch `ci/ae23aa5-1791387807-36662`, head `ae23aa54975a...`): `success`, 7 jobs each `success`. This agrees with the note: the first gate's RED came from the polling call (a 403), not from a job.
- Run 37648774580 (branch `ci/ae23aa5-1791388898-39588`): `success`, 7 jobs each `success`. Its logs match every count the note quotes:
  - `pytest + ruff` `2285 passed, 139 skipped`;
  - `-m day12` `199 passed, 3 skipped`, `-m day13` `133 passed`;
  - `-m day14` `82 passed, 2 skipped`, the two skips at `tests/test_e14_cover_row.py:90` and `tests/test_e14_margin_notes.py:91`, each with `SKIP_REASON`;
  - the ap4 job `199 passed, 1 skipped, 2224 deselected`.

**My run 37650538581.** Branch `ci/ae23aa5-1791389696-40685`, head `ae23aa54975a3222e9fe75473227b0c13e81ec18`, conclusion `success`. All 7 jobs were `success`: pip-audit, import without scipy, wheel, ap4 with [docx], pytest + ruff, unshare -rn and Docker smoke. Afterwards, `git ls-remote origin "refs/heads/ci/ae23aa5*"` printed nothing.

## Cut and carried, against what I measured

The note's carried list matches what I found open:
- FA-N1 to FA-N5 of lens 2;
- RG-O1's first half (no E14 handoff);
- item 5 (`80+`), the section numbers, note 19;
- lens-1 FA-N4 (`ci_gate.sh` under a secondary rate limit; my gate run did not hit it).

The one open item the note omits is B1.

## What I could not check

- The Linux-only paths (reference image, network namespace, Docker). I read them only from the job conclusions of runs 37648774580 and 37650538581.
- Whether the two E14 DOCX tests individually passed in the ap4 job. CI runs `-q`; the evidence is the count (`199 passed, 1 skipped`) under `PROOFPACK_REQUIRE_DOCX=1`.
- Lens-2 FA-N1, FA-N5 and RG-N7. They are carried and I did not re-run them. `ae23aa5` changes no `src/`, so their state is that of `e67c5fa`.

## Changes for other lanes (site pin move from 8ef3266)

None from `ae23aa5`. No CLI flag, default, path, JSON key, golden, template or rendered string changed (the `src`, `scripts`, `tests/fixtures`, `.github` and `pyproject.toml` diff is empty). The builder's list for `3ee5601..a1840fc` stands.

## Sentences I refused to write

- "The new meta-test covers everything the old one did." B1: IOS passes the new one and failed the old one.
- "The scanner's importorskip and case-insensitive matching are tested." N2: S4 and S5 leave all 12 passing.
- "No gate was weakened." B1.
