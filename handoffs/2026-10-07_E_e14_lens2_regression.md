**Verdict: PASS. No blockers. Every figure in the E14 repair 1 note reproduces at `e67c5fa`, in both Git Bash and PowerShell 5.1. In `wt-e14` the full suite gave 2409 passed, 4 skipped; `-m day14` 73, `day13` 133, `day12` 199 + 3 skipped, `ap4` 200. ruff check and format are clean (358 files). All 7 new tests of `test_e14_repair1.py` fail at `a1840fc`, on the lines the note quotes. The FA-B1 counter-example reproduces: with the T1 cover loop cut to `cover_guidance[:1]`, the old test passed and the new one failed. I ran 10 more DOCX cover mutants (5 per template) and the new test killed all 10. Each of the four lens-1 blockers is closed. The rendered T1/T8 HTML and DOCX bytes are identical between `a1840fc` and `e67c5fa`. My gate run 37642117620 on `e67c5fa` was GREEN, 7 jobs, all success. Three findings are non-blocking: a quoted failure line in the commit message that does not appear at `a1840fc` as quoted, a regression test that inspects less than its name says, and one docstring word. One item is open: the E14 handoff does not exist yet.**

# E14 lens 2 (cold regression and record) on engine e67c5fa - Wednesday 7 October 2026

Cold lens on `e14-lw01` at `e67c5fa` (one commit on `a1840fc`). It checks the repairer's note `scratchpad/notes/E14_repair1.md` and closes out the two lens-1 notes (`2026-10-07_E_e14_lens1_fresh-attack.md`, `2026-10-07_E_e14_lens1_regression.md`).

Method:
- **Worktrees.** I used two detached worktrees under `scratchpad/lens-E14-r2-regression/`: `tip` (`e67c5fa`) and `pre` (`a1840fc`). `PYTHONPATH` was set to each tree's `src`, and I checked it each time with `python -c "import proofpack;print(proofpack.__file__)"`. It printed `...\lens-E14-r2-regression\<tree>\src\proofpack\__init__.py`, and `C:\Users\joshs\GPS\ProofPack\wt-e14\src\proofpack\__init__.py` for `wt-e14`.
- **wt-e14.** I ran tests only there, with `PYTHONDONTWRITEBYTECODE=1`. Afterwards `git status --short` showed only two untracked files: this note and the parallel fresh-attack lens's note.
- **Mutants.** I applied them by scratch scripts in `pre` or `tip` and restored each with `git checkout -- .`. `git status --short` was empty after every run.
- **Platform.** Windows 11 Home 10.0.26200, Python 3.14.6. I made no commits.

## Blockers

None.

## Non-blocking

### N1. Commit message `e67c5fa` quotes a failure line that `a1840fc` does not print as quoted

The message says: "test_e14_repair1.py inspects those marks; it fails at a1840fc ("assert 'ap4' in set()")". At `a1840fc`, `test_fa_b1_rg_n3_...` fails first on the set equality:

```
E         Extra items in the left set:
E         ('test_e14_cover_row', 'test_docx_cover_row_names_the_distinct_documents')
```

`assert 'ap4' in set()` appears only after the expected set is edited to `a1840fc`'s test names. With that edit I got `1 failed, 6 deselected`. The repairer's note states both cases correctly; only the commit message merges them. The repair is one line in the handoff.

Repro: copy `tests/test_e14_repair1.py` alone into a tree at `a1840fc`, then run `python -m pytest -q -p no:cacheprovider tests/test_e14_repair1.py -k fa_b1`.

### N2. `test_fa_b1_rg_n3_every_e14_docx_test_is_selected_by_ap4_and_takes_the_extra_rule` inspects only the E14 tests whose source contains the text `render_docx`

The name says "every E14 DOCX test". That is true of today's tree: the only two E14 tests that touch DOCX are the two it lists. The module docstring gives the narrower scope accurately, except that it says "calls" where the test matches a substring.

Counter-example (T5), run in `pre` with the tip's E14 test files: I appended this test to `test_e14_global_flags.py`:

```
def test_extra_docx_via_cli(tmp_path):
    pytest.importorskip("docx")
    ...
```

It uses python-docx directly and carries no `ap4`. The regression test gave `1 passed`. A future E14 DOCX test that renders through the CLI (`--format docx`) or python-docx would therefore escape it.

My other four mutants were all killed:
- T1, `ap4` removed from the margin test: `assert 'ap4' in {'skipif'}`.
- T2, `@needs_extra` removed from the cover test: `assert [] == [...]`.
- T3, `importorskip` re-added: `'importorskip' not in ...`.
- T4, a new E14 test that mentions `render_docx`: `Extra items in the left set`.

Suggested repair: rename the test to "...every_e14_test_naming_render_docx..." or widen the match to `docx`.

### N3. Docstring word in `tests/test_e14_repair1.py`: "so every CI job skipped them"

In the main `test` job they were skipped. In the `docx-extra` job, `-m ap4` deselected them, so they never reached a skip. "No CI job ran them" is what the record supports.

I could not re-read the log of run 37631774505 for the quoted `SKIPPED [1] tests/test_e14_cover_row.py:90: could not import 'docxtpl'` line, because GitHub returned `HTTP 403: API rate limit exceeded` (a secondary limit; core showed 5000/5000). Lens 1 (regression) quoted the same line from run 37629330981.

## Open items the note does not list

- **No E14 handoff exists on the branch yet.** `handoffs/` holds only the lens notes. The note says the 834634c correction ("The handoff should carry this correction") belongs there, and it does not say who writes the handoff.
- **Commit `834634c`'s false sentence stays in the history that will reach public `main`.** The sentence is "in the walk-through a buyer typing 'y' was told nothing about how to accept". It is corrected in `e67c5fa`'s message and is disclosed in the note.
- **FA-N1 is carried and still survives.** In `tip`, `t8_context` calling `anchors.cover_documents(refs)` without `guidance_map` gave `117 passed` over the five E14 files, `test_render_t8.py` and `test_ap4_roundtrip.py`. The new DOCX cover test compares DOCX with HTML under the same shipped map, so it does not reach this mutant.

## Lens-1 blockers: each is closed (re-run, not read)

- **FA-B1 (cover test checked too little).**
  - In `pre`, I cut `build_t1`'s loop (line 1176 of `scripts/make_docx_templates.py`) to `cover_guidance[:1]` and regenerated `T1.docx`. The old test gave `1 passed, 4 deselected`. The tip's test failed with `AssertionError: ('T1', 'FDA draft guidance, Artificial Intelligence-Enabled Device Software Functions: ...` against labels that end `(2024-12-04, updated 2025-08-18, final)`.
  - Further mutants, each applied to T1 (line 1176) and T8 (line 759) and regenerated. All 10 were killed (`1 failed`):
    - C1, order reversed;
    - C2, `; ` changed to `, `;
    - C3, the loop reading `guidance_refs`;
    - C4, `, not for implementation` stripped from the label;
    - C5, `cover_guidance[1:]`.
  - A slip and its re-run: my first C4 attempt broke the generator's string literal, and the template did not change. I fixed the quoting and re-ran C4; the results above are from that re-run.
  - Line 759 is in `build_t8` and line 1176 in `build_t1`. The note names `build_t1`, which is right.
- **RG-N3 (the tests never ran in CI).**
  - `pytest -m ap4 --collect-only` on the two files gave `2/11 tests collected (9 deselected)`, in both shells.
  - With docxtpl, docx and matplotlib hidden by my own `-p` plugin (`sys.modules[name] = None`): `2 skipped`, both with `SKIP_REASON`.
  - The same with `PROOFPACK_REQUIRE_DOCX=1`: `2 failed`, both `proofpack.render.docx.DocxExtraMissing`.
  - Control: `test_e14_repair1.py` under the same plugin gave `7 passed`.
  - The `ap4` count went from 198 (`pre`) to 200 (`tip`) collected. The CI `docx-extra` job read `199 passed, 1 skipped, 2213 deselected` in both run 37638635127 and my run 37642117620; the one skip is `tests/test_ap4_templates.py:73` (`python -m uv is not available`).
- **FA-B2 / RG-N5 (the cli.py comment).**
  - At `3ee5601`, `cli.py` line 309 reads `say("  answer a or q")`, under line 304's `[a]ccept / [q]uit? `.
  - `user_review_notes.md` line 26 is note 17, quoted exactly. `LW01_log.md` line 7 is `y` re-prompts.
  - The new comment matches these sources.
- **FA-B3 (the anchors docstring).** `render/docx.py` line 301 passes `anchors.distinct_notes` into the DOCX context. The generator's line 487 prints `[{{ ref.id }}{% for other in ref.also %}, {{ other }}{% endfor %}]`. The docstring now matches.
- **FA-B4 / RG-N1 (the golden line count).**
  - `git diff --numstat 3ee5601 e67c5fa -- tests/fixtures/golden`: T1 `3 5`, T2 `2 3`, T8 `1 1`. That is 9 out and 6 in, and `E14_build.md` line 50 now says so.
  - `a1840fc..e67c5fa` changes no file under `tests/fixtures` or `src/proofpack/templates`.
- **RG-N2 (the global-flags docstring).** In `pre`, with the tip's `test_e14_global_flags.py`:
  - `sub.add_parser("probe", parents=[common])`: `1 failed, 56 passed` (the walk test).
  - The same with `help="x"`: `1 failed, 56 passed`.
  - Without `common`: `7 failed, 50 passed`.
  - The docstring's figure reproduces.
- **RG-N4 ("guards the merge").**
  - M1 (`data-also` removed from `base.html`): `test_every_block_still_cites_every_anchor_it_names` fails with `AssertionError: t1-s7`.
  - M14 (`distinct_notes` never appends to `also`): the same error.

## What I could not break (with figures)

- **Fails pre-build.** `test_e14_repair1.py` copied alone into `pre` gave `7 failed`:
  - fa_b1, on the set equality;
  - the 3 `..._found_false_are_gone[...]` tests, e.g. `assert 're-prompted...ow to accept' not in ...` and `assert 'the DOCX te...on each line' not in ...`;
  - the 3 `..._replacement_sentences_are_present[...]` tests.

  No test aborted on import. The replaced cover test passes at `a1840fc`. That is expected: `T1.docx` is right there, and the test's failing case is the `[:1]` mutant above.
- **Nothing weakened.**
  - `git diff --name-status a1840fc e67c5fa`: 3 added (2 lens notes, `test_e14_repair1.py`), 5 modified, 0 deleted.
  - The diff removes two `pytest.importorskip("docxtpl")` lines and adds `@pytest.mark.ap4` + `@needs_extra` (a named reason). It adds no `xfail`, `.only` or bare skip, and removes no marker.
  - `.github/` and `pyproject.toml` are unchanged in this commit; `day14` was declared at `a1840fc`.
- **No behaviour changed.** The `src/` diff is one `#:` comment block (`cli.py`) and one docstring (`anchors.py`). For the synthetic document, my own script rendered the same bytes in `pre` and in `tip`:

  | file | bytes | sha256 (first 16 hex digits) |
  |---|---|---|
  | T1.html | 153,831 | 46df47a6c393fb7b |
  | T8.html | 43,905 | 4725f8f09d1e6139 |
  | T1.docx | 679,556 | a7e84d63597dff5f |
  | T8.docx | 48,722 | 63884cbcd8d02c6a |

  Other checks in the same script:
  - `licence verify x.lic --offline`, `licence show --quiet --json-log` and `licence install x.lic --offline` parse with the flags `True`.
  - `ALL_HIGH_REPROMPT` is unchanged and `ACCEPT_ANSWERS == ('a', 'accept')`.
- **Fixtures `--offline`.** Exit 0 in both shells, `rows 46: matched 35, not matched 0, ... not built 4, suite only 7`. Across all 2,486 leaves of `fixtures_report.json`, `tip` and `pre` differ in 4: `duration_s`, `generated`, `git_sha`, and F13's `reason` (which embeds the sha). F19's `small_only_values` was equal on this pair (RG-N7 stays carried).

## Re-run figures (all measured in this session)

| command (PYTHONPATH forced) | Git Bash | PowerShell 5.1 | note says |
|---|---|---|---|
| full suite, `wt-e14` | 2409 passed, 4 skipped (451.88 s) | 2409 passed, 4 skipped (408.68 s) | 2409 / 4: reproduces |
| full suite, scratch `tip` | 2408 passed, 5 skipped (421.49 s) | not run | the 5th skip is `test_e8_repair4.py:405` (no sibling `workflows/data`), the known path skip |
| `-m day14` / `day13` / `day12` / `ap4`, `wt-e14` | 73 / 133 / 199 + 3 skipped / 200 | 73 / 133 / 199 + 3 skipped / 200 | reproduces |
| `-m day14` / `ap4` collected, `pre` vs `tip` | 66 vs 73 / 198 vs 200 | - | 66 -> 73, 198 -> 200: reproduces |
| `tests/test_e14_repair1.py` | 7 passed | 7 passed | reproduces |
| `ruff check .` / `ruff format --check .` | All checks passed! / 358 files already formatted | same | reproduces |
| `doctor --offline` | exit 0 | exit 0 | reproduces |
| `fixtures --offline --out <dir>` | exit 0, 35 matched / 7 suite only / 4 not built | same | reproduces |
| `bash workflows/ci_gate.sh C:/Users/joshs/GPS/ProofPack/wt-e14 e67c5fa` (my run) | `gate: run 37642117620 ci: success`, `gate: GREEN e67c5fa`, exit 0 | - | see below |

**The note's gate run, read from GitHub.** Run 37638635127: head `e67c5fac058d673d1e7ffc42a89c01b1cf3c9f57`, branch `ci/e67c5fa-1791384002-23856`, conclusion `success`, 7 jobs each `success`. Its log matches every figure the note quotes:
- `2274 passed, 139 skipped`;
- `-m day14` `71 passed, 2 skipped` (the 2 skips are the E14 DOCX tests, with `SKIP_REASON`);
- `day13` `133 passed`;
- `day12` `199 passed, 3 skipped`;
- ap4 `199 passed, 1 skipped`.

**My run 37642117620.** Head `e67c5fa...`, 7 jobs each `success`, the same counts. My branch `ci/e67c5fa-1791385516-29091` was deleted. `ci/e67c5fa-1791385600-29284` was still on origin when I looked; it is not mine (the stamp differs), most likely the parallel lens's gate.

## What I could not check

- The run 37631774505 log line quoted in `test_e14_repair1.py`'s docstring (GitHub secondary rate limit, N3).
- The Linux-only paths (unshare, Docker, reference image). I read them from the job conclusions of runs 37638635127 and 37642117620 only.
- Whether the two E14 DOCX tests individually passed in CI. The job runs `-q`, so the evidence is the count: 197 -> 199 passed in the `ap4` job, under `PROOFPACK_REQUIRE_DOCX=1`, where the skip branch cannot be taken.
- The note's PowerShell figures. The note ran none; mine are above.

## Changes for other lanes (site pin move from 8ef3266)

None from `e67c5fa`. No golden, template, CLI flag, default, path, JSON key or rendered byte changed between `a1840fc` and `e67c5fa` (byte-identical renders above). The builder's list for `3ee5601..a1840fc` stands.

## Sentences I refused to write

- "The regression test catches every E14 DOCX test that CI would skip." T5 passes it (N2).
- "The E14 DOCX tests are proven to run in CI by name." The CI log is quiet; only the count moved.
- "The FA-N1 hook is now covered." The mutant still survives (117 passed).
