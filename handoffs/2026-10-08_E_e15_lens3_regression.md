**Verdict: PASS. 0 blockers. Every suite, marker, lint, doctor and fixtures figure in the E15 repair 2 note reproduces at `6f49dc1` in `wt-e15`, in Git Bash and in PowerShell 5.1: full suite 2448 passed, 4 skipped (Git Bash 385.75s; PowerShell 487.00s); `-m day15` 28, `day14` 84, `day13` 133, `day12` 199 + 3 skipped, `ap4` (`PROOFPACK_REQUIRE_DOCX=1`) 201; the three E15 test files 28 passed; ruff clean, 372 files (369 at `0fb6f71`). `tests/test_e15_repair2.py` copied into `0fb6f71` gives `2 failed, 4 passed`, as the note says: the two docstring tests fail on their own `not in` assertion, with no import abort. The 4 that pass there are mutant killers and a data inspection, which the note states; with mutant M3 applied at `0fb6f71` the blank-cell cases go `2 failed, 1 passed`. The only `src/` change is a docstring: the AST of `anchors.py` at `0fb6f71` and `6f49dc1` is equal once docstrings are blanked. Lens 2's two sentence findings (FA-L2-N1/RG-N1 and FA-L2-N2) are fixed as sentences, and its surviving mutant D1 is now killed. I re-measured the site port against the tip: `rows 32 field mismatches 64`, byte-for-byte the note's line. CI gate GREEN on `6f49dc1`: run 37802619513, `ci: success`, 7 jobs; the note's run 37799340823 is also `success` on the same sha. Three non-blocking items follow, two of them sentences.**

# E15 lens 3 (cold regression and record) on engine 6f49dc1 - Thursday 8 October 2026

This is a cold lens on `e15-sections` at `6f49dc1`, one commit on `0fb6f71`. It checks the repairer's note `scratchpad/notes/E15_repair2.md` and re-checks the four earlier E15 lens notes committed in the tip.

Method:
- **Worktrees.** Three detached worktrees under `scratchpad/lens-E15-r3-regression/`: `tip` (`6f49dc1`), `pre` (`0fb6f71`, for the fails-before runs and the CSV counter-example), `mut` (`6f49dc1`, for mutants). All removed at close.
- **PYTHONPATH.** Set to each tree's `src` and checked each time with `python -c "import proofpack;print(proofpack.__file__)"`, which printed `...\lens-E15-r3-regression\<tree>\src\proofpack\__init__.py`. In `wt-e15` it printed `C:\Users\joshs\GPS\ProofPack\wt-e15\src\proofpack\__init__.py` in both shells.
- **PROOFPACK_HOME, TEMP, TMP.** Empty directories under my label for every run; concurrent runs had separate directories.
- **`wt-e15`.** HEAD `6f49dc1840deabdf4c533221c0d0078597d9de96`; `git status --porcelain` gave 0 lines before my runs and after them (until this note was written).
- **Mutants.** Applied by `scripts/mut.py` (writes `anchors.py`, runs pytest, writes the original bytes back). `git status --short` in `mut` was empty after every run; in `pre` it listed only the copied-in test file.
- **Platform.** Windows 11 Home 10.0.26200, Python 3.14.6, ruff 0.16.6, PowerShell 5.1, Git Bash, node (for the site port, run from my label only).
- **Commits and refs.** I made no commits. The only ref pushed was the gate's own throwaway branch, which the gate deleted.

## Blockers

None.

## Status of earlier findings at 6f49dc1

| finding | status | evidence (measured here) |
|---|---|---|
| FA-L2-N1 / RG-N1: "The site ports this rule" | **closed (sentence)** | The phrase is gone. The new sentence says the port "still implemented the effc5c7 rule at site 576bd09 (lines 70-71 and 95)". Read-only, `git show 576bd09:src/data/guidance-notes.mjs` (site HEAD `576bd09`, `git status --porcelain` 0 lines): line 70 `section: internal ? 'n/a' : String(row.section ?? '').trim() \|\| 'to confirm',`, line 71 the same for `estar_section`, line 95 `` return `maps to ${note.label} · section ${note.section} · eSTAR: ${note.estar}`; ``. The site test file at `576bd09`: S10-S3-2 (line 103) asserts `mine.section == theirs.section` and `mine.estar == theirs.estar` (lines 134-135); S10-S3-2b (line 149) compares `noteText(...)` with a string built from the engine's fields (line 166). My own run of the port (copied to my label, `papaparse` import replaced by `const Papa = null;`) against the tip's `with_note_fields` on all 32 rows printed `rows 32 field mismatches 64 [["FDA_AIDSF_DATA_MGMT","section","VIII. Data Management","section VIII. Data Management"],["FDA_AIDSF_DATA_MGMT","estar","to confirm","[unverified] eSTAR section not mapped"]]`, the note's line exactly. |
| FA-L2-N2: "A gap is printed, never hidden (E9)" | **closed (sentence)**; the behaviour stays carried | The phrase is gone. The replacement says the gap test is `str.strip()` only and a cell of only U+200B, U+2060, U+FEFF or U+180E prints unmarked. Run at the tip on `FDA_AIDSF_CALIBRATION`: those four give `'section \u200b'` / `'eSTAR: \u200b'` (and the same for the others); U+00A0, U+3000, `"   "`, `"\t "` and `""` give both gap strings. In Python 3.14.6, `ch.strip()` returns `ch` and `ch.isspace()` is `False` for each of the four. So the new sentence is true by my run. |
| Lens 2 surviving mutant D1 (drop "field by field and as the note's text") | **killed** | `1 failed, 12 passed` over `test_e15_repair2.py` + `test_e15_repair1.py`, first line `AssertionError: field by field and as the note's text`. |
| RG-N3 / FA-R4 (M3: `.strip()` removed survived) | **closed by a run** | In `pre` (`0fb6f71`) with the new file: M3 gives `4 failed, 2 passed` = the 2 docstring tests + `three-spaces` and `tab-space`; `empty` passes, as the note says. At the tip over 13 tests: M3 `2 failed, 11 passed`, first line `AssertionError: assert 'section    ' == '[unverified]...t transcribed'`. Section-strip only and estar-strip only: each `2 failed, 11 passed`. My extra mutant `.strip(" ")` (spaces only): `1 failed`, killed by `tab-space`. `SECTION_GAP` without `[unverified]`: `3 failed`. |
| RG-N4: re-run block Git Bash only | **closed** | The note gives both forms. I ran the PowerShell form (with `$env:` assignments, as written) and every row reproduces (table below). |
| RG-N2: lane-S record lives in scratch notes | **still open, carried by the note** | `git ls-files handoffs` at the tip has the four lens notes only; no E15 build, repair or merge handoff. The new test module's docstring adds a second pointer outside the repository: "(the run is in the repair-2 note)". The merge handoff must carry repair 1's items 1-7 and the repair-2 M3 run. |
| RG-B1 (lens 1) | still closed as a record | `test_e15_repair1.py` 7 of 7 pass at the tip (inside the 28 below). |
| FA-R3, FA-R5, FA-R6, FA-R7, RG-N5, RG-N6 | carried, still open | `git diff --stat 0fb6f71 6f49dc1 -- design src/proofpack/templates tests/fixtures` is empty, so nothing that could close them changed. |

## Non-blocking

**N1. A new test name says more than its body inspects (hard-rule sentence).**
- Test: `tests/test_e15_repair2.py::test_no_section_or_estar_cell_of_the_shipped_map_is_only_characters_strip_keeps`. Its body removes only the four characters in `KEPT_BY_STRIP` (U+200B, U+2060, U+FEFF, U+180E) before stripping. `str.strip()` keeps many other invisible characters.
- Counter-example, run in `mut` (CSV-only edit, `GB_PMS_44ZL`'s `section` set to one character, then `git checkout -- design`):

  | character | `with_note_fields(...)["section"]` | this test |
  |---|---|---|
  | U+200C | `'section \u200c'` | 1 passed |
  | U+200D | `'section \u200d'` | 1 passed |
  | U+00AD | `'section \xad'` | 1 passed |
  | U+3164 | `'section \u3164'` | 1 passed |
  | U+2800 | `'section \u2800'` | 1 passed |

- The control: the same edit with U+200B fails this test with `Left contains one more item: ('GB_PMS_44ZL', 'section', '\u200b')` (and also fails `test_every_filled_section_has_a_source_row_with_url_date_and_version`), as the note says.
- The docstring sentence it supports ("a cell made only of those [four] ... the shipped map has no such cell") is true, and so are the note's figures. Only the test name overreaches. Suggested name: `..._is_only_the_four_characters_strip_keeps`. Not reachable on the shipped map. The same CSV-only edit with these five characters also breaks the provenance test, which compares the CSV section with the YAML character for character (FA-R3 class).

**N2. Four of the six new tests pass at `0fb6f71`.**
- The two docstring tests are the fix; the other 4 tests (the shipped-map inspection and the three blank-cell cases) pass before and after. The note says this ("mutant killers, not fixes") and does not claim they pin a change in `6f49dc1`. I measured their killing power (table above: M3, section-only, estar-only, `.strip(" ")`, an unmarked `SECTION_GAP`). The shipped-map test kills the U+200B CSV edit. Recorded so the merge handoff does not count them as fails-before tests.

**N3. One docstring clause describes the map's data as if it were the rule (informational, older sentence).**
- "``eSTAR: n/a`` for a non-FDA row" is in the docstring at `0fb6f71` and at the tip. The function prints `eSTAR: n/a` because the five non-FDA rows hold `n/a` in the CSV (measured: EU 1, GB 2, MDCG 2, all `'n/a'` -> `eSTAR: n/a`); a non-FDA row with an empty cell prints the eSTAR gap. This is lens 1's FA-R5 (carried). Repair 2 did not change the clause; I record it because it sits in the paragraph this repair rewrote.

## What I could not break

- **Suites, both shells, `wt-e15` at `6f49dc1`.** The note's table, row by row:

  | command | Git Bash | PowerShell 5.1 | note |
  |---|---|---|---|
  | full | 2448 passed, 4 skipped in 385.75s | 2448 passed, 4 skipped in 487.00s | 2448 / 4 in 320.87s |
  | `-m day15` | 28 passed, 2424 deselected | same | same |
  | `-m day14` | 84 passed, 2368 deselected | same | same |
  | `-m day13` | 133 passed, 2319 deselected | same | same |
  | `-m day12` | 199 passed, 3 skipped, 2250 deselected | same | same |
  | `-m ap4`, `PROOFPACK_REQUIRE_DOCX=1` | 201 passed, 2251 deselected | same | same |
  | the three E15 test files | 28 passed | 28 passed | 28 passed |
  | `ruff check .` | All checks passed! | All checks passed! | same |
  | `ruff format --check .` | 372 files already formatted | 372 | 372 |
  | `doctor --offline` | exit 0, "All essential checks passed." | same | same |
  | `fixtures --offline --out <empty>` | exit 0, rows 46: matched 35, not matched 0, no oracle recorded 0, no independent oracle 0, not built 4, suite only 7 | same | same |

  - The 4 skips are `test_day12_r_captures.py:156` ×3 (DEC-77, aSAH vectors not committed) and `test_doctor_cli.py:58`.
  - ruff format at `0fb6f71` (`pre`, the copied-in test file excluded): 369 files, so 372 = 369 + the new test file + the two lens-2 notes, as the note says.
  - Both re-run blocks of the note work in their own shell (PYTHONPATH check printed the `wt-e15` path in each).
- **Fails before.** `tests/test_e15_repair2.py` alone in `pre`: `2 failed, 4 passed in 0.35s`. First lines: `E       assert 'The site ports this rule' not in "``item`` (f...note's text."` and `E       assert 'never hidden' not in "``item`` (f...note's text."`, the note's quoted lines. No import abort.
- **Mutants on the new docstring** (tip `anchors.py`, 13 tests, unmutated `13 passed`). All five of the note's mutants reproduce at `1 failed, 12 passed`: D1 (`by some means`), `ports this rule`, `empty` for `empty after ``str.strip()```, `FA-L2-N2` without `, carried`, and an appended `A gap is printed, never hidden.`. Mine: `U+180E` -> `U+00A0` in the list, `1 failed`. Dropping "; the shipped map has no such cell" survives (`13 passed`); that clause is inspected by the data test, not by a docstring test, which the note says.
- **Nothing weakened.** `git diff --name-status 0fb6f71 6f49dc1`: A for the two lens-2 notes, M `src/proofpack/render/anchors.py`, A `tests/test_e15_repair2.py`. Nothing deleted. In the diff, the only added marker lines are the new file's `pytestmark = pytest.mark.day15` and one `parametrize`; the other matches are lens-note prose ("skipped" counts). No marker, skip or xfail was removed or added elsewhere. Across E15 (`effc5c7..6f49dc1`) no test file is deleted.
- **No behaviour change.** `ast.dump` of `anchors.py` at `0fb6f71` and `6f49dc1`, with every docstring blanked: equal. No golden, template, CSV or YAML in the repair diff. Across E15 the goldens have 72 changed lines, 0 outside a `class="margin-note` aside.
- **Fixtures.** `fixtures --offline` at `pre` and at the tip, key-by-key diff of `fixtures_report.json`: `/doctor[12]/info` (tree path), `/duration_s`, `/generated`, `/git_sha`, and `/rows[36]/reason`, which differs only in the HEAD sha it quotes (`0fb6f71...` -> `6f49dc1...`).
- **Network.** `-m day15` at the tip with my `nosock` plugin (socket `connect`, `connect_ex`, `getaddrinfo`, `create_connection` raise): `28 passed`, `NOSOCK calls=0 []`.
- **Provenance, all filled rows.** At the tip: 32 rows, 30 filled `section` cells, 30 YAML rows, no extra YAML row; the unfilled rows are `PP_SCOPE` and `PP_METHODS`. For each row the YAML `section` equals the CSV's, the document's `map_document` equals the CSV `document`, and `url`, `date_read`, `version_line`, `fetch` are non-empty; each row has headings. Problems: none.
- **Sources (fetched today, curl with a browser UA, into my label, read-only, nothing committed).** All seven match the YAML's byte count and SHA-256: AI-DSF 1,590,866 (`62e83e0f...7520bc`), STAT2007 344,921 (`4a5c66b8...51bd0b`), PCCP 666,195 (`80f0f423...e4d9`), MDR 1,517,689 (`71f1b6b6...6db9`), MDCG 2022-21 1,426,146 (`d1dc8af7...3f4`), MDCG 2020-8 697,086 (`3ea53b2e...3f21`), SI 2024/1368 HTML 139,552 (`9b81984c...3c24`). My own checker (`pdftotext -enc UTF-8`, split at form feeds; the SI through tag stripping; text and quote both reduced to lowercase letters only) found 80 of 81 quoted headings and topic quotes on the named page. The 81st is `(3)` under `GB_PMS_44ZM3`, which my letters-only reduction empties; read raw, the SI text has `... preparing a single PSUR for those devices. (3) The PSUR must include`. The `equivocal5` footnote heading passes under this reduction because it drops digits.

## What I could not check

- **The site's S10-S3-2/2b against the tip.** `proofpack-site` is lane S's tree today and read-only for me, so I did not run its tests. I ran the port's `noteFor` from a copy in my label instead (64 of 64 fields differ). Lenses 1 and 2 ran the site tests against `e5319e0` and `0fb6f71` (`pass 0, fail 2`). Repair 2 changed no behaviour (AST equal), so I expect the same result at `6f49dc1`; I did not run it.
- **Rendered packs.** I did not render T1/T2/T7/T8 at the tip. With the AST equal and no template, CSV, YAML or golden changed, the renders of lens 2 at `0fb6f71` stand. I did not measure them again.
- **CI on Python 3.12 / Linux** beyond the gate run below.

## Gate

`bash C:/Users/joshs/GPS/ProofPack/workflows/ci_gate.sh C:/Users/joshs/GPS/ProofPack/wt-e15 HEAD` printed:
- `gate: JoshSandhu/proofpack 6f49dc1 -> ci/6f49dc1-1791473993-43034`
- `gate: run 37802619513 ci: success`
- `gate: GREEN 6f49dc1`, exit 0

`gh run view 37802619513`: head sha `6f49dc1840deabdf4c533221c0d0078597d9de96`, conclusion `success`, 7 of 7 jobs `success` (pytest -m ap4 with the [docx] extra installed; pytest + ruff; Docker image smoke (linux/amd64, no push); wheel artefact; proofpack run inside unshare -rn (no network); pip-audit; import proofpack (scipy uninstalled)). The note's run 37799340823: head sha `6f49dc1840deabdf4c533221c0d0078597d9de96`, conclusion `success`. `git ls-remote origin 'refs/heads/ci/6f49dc1*'` printed 0 lines afterwards.

## Commands (re-run)

Git Bash:

    S=<scratch label>
    cd /c/Users/joshs/GPS/ProofPack/wt-e15
    export PYTHONPATH=C:/Users/joshs/GPS/ProofPack/wt-e15/src PYTHONDONTWRITEBYTECODE=1 PROOFPACK_HOME=$S/home TEMP=$S/tmp TMP=$S/tmp
    python -c "import proofpack;print(proofpack.__file__)"
    python -m pytest -q -p no:cacheprovider                               # 2448 passed, 4 skipped
    for m in day15 day14 day13 day12; do python -m pytest -q -p no:cacheprovider -m $m | tail -1; done
    PROOFPACK_REQUIRE_DOCX=1 python -m pytest -q -p no:cacheprovider -m ap4 | tail -1   # 201 passed

PowerShell 5.1:

    Set-Location C:\Users\joshs\GPS\ProofPack\wt-e15
    $env:PYTHONPATH = 'C:\Users\joshs\GPS\ProofPack\wt-e15\src'; $env:PYTHONDONTWRITEBYTECODE = '1'; $env:PROOFPACK_HOME = '<empty dir>'
    python -m pytest -q -p no:cacheprovider

Fails before (Git Bash): `git -C C:/Users/joshs/GPS/ProofPack/proofpack worktree add --detach $S/pre 0fb6f71`, copy `tests/test_e15_repair2.py` in, `PYTHONPATH=$S/pre/src python -m pytest -q -p no:cacheprovider tests/test_e15_repair2.py` -> `2 failed, 4 passed`.

## Sentences I refused to write

- "The shipped-map test proves no invisible-only cell can reach the page." N1's five characters pass it.
- "The site port matches the engine at E15." 64 of 64 fields differ on my run.
- "Repair 2 leaves the rendered packs unchanged." I did not render; I measured the AST and the absent template, CSV, YAML and golden changes, nothing wider.
- "The site tests fail at 6f49dc1." Not run by me (see could not check).
