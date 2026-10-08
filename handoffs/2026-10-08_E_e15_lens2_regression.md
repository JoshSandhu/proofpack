**Verdict: PASS. 0 blockers. Every suite, marker, lint, doctor and fixtures figure in the E15 repair 1 note reproduces at `0fb6f71` in `wt-e15`, in Git Bash and in PowerShell 5.1: full suite 2442 passed, 4 skipped (Git Bash 318.08s, PowerShell 337.66s); `-m day15` 22, `day14` 84, `day13` 133, `day12` 199 + 3 skipped, `ap4` (`PROOFPACK_REQUIRE_DOCX=1`) 201; the two E15 test files 22 passed; ruff clean, 369 files. `tests/test_e15_repair1.py` copied into `e5319e0` gives 7 failed, each on its own assertion, with no import abort. Regression lens 1's blocker B1 is closed as the record fix it asked for: the contract change, the port's lines, the re-vendor and S10-S3-2/2b are listed, and every line number and count in that list matches the site at `576bd09`. The site's two tests still fail against the new engine, and the repair says so: `pass 0, fail 2` pointed at `0fb6f71` and `e5319e0`, `pass 2, fail 0` at `effc5c7`. The fresh-attack lens's R2 sentence and regression lens 1's N1 sentence are replaced, and I re-measured the replacement figures at `effc5c7`. CI gate GREEN on `0fb6f71`: run 37795001932, `ci: success`, 7 jobs; the note's run 37792272671 is also `success` on the same sha. Four non-blocking items follow, two of them sentences.**

# E15 lens 2 (cold regression and record) on engine 0fb6f71 - Thursday 8 October 2026

This is a cold lens on `e15-sections` at `0fb6f71`, one commit on `e5319e0`. It checks the repairer's note `scratchpad/notes/E15_repair1.md` and re-checks the two lens-1 notes committed in the tip.

Method:
- **Worktrees.** Four detached worktrees under `scratchpad/lens-E15-r2-regression/`:
  - `tip` (`0fb6f71`) for the full suite;
  - `pre` (`e5319e0`) for the fails-before runs;
  - `base` (`effc5c7`) for the pre-build runs;
  - `mut` (`0fb6f71`) for mutants, doctor and fixtures.
- **PYTHONPATH.** Set to each tree's `src`. Each time I checked it with `python -c "import proofpack;print(proofpack.__file__)"`, which printed `...\lens-E15-r2-regression\<tree>\src\proofpack\__init__.py`. In `wt-e15` it printed `C:\Users\joshs\GPS\ProofPack\wt-e15\src\proofpack\__init__.py` in both shells.
- **PROOFPACK_HOME.** Set to an empty directory under my label for every run. TEMP and TMP also pointed there.
- **Mutants.** Each was reverted with `git checkout -- .`, and `git status --short` was empty after every run.
- **Platform.** Windows 11 Home 10.0.26200, Python 3.14.6, PowerShell 5.1.26100.9444, Git Bash, node v24.18.0.
- **Commits and refs.** I made no commits. The only ref pushed was the gate's own throwaway branch, which the gate deleted.

## Blockers

None.

## Lens-1 findings: status at 0fb6f71

| finding | status | evidence (measured here) |
|---|---|---|
| RG-B1 / FA-R1: the `with_note_fields` contract change is missing from the record | **closed as a record**; the site port is not changed (lane S's tree) | The record is in three places: the docstring, the repair note's "Changes for other lanes" items 1-7, and `E15_build.md` line 96 ("Added in repair 1"). At site HEAD `576bd09` (0 commits after it, `git status --porcelain` 0 lines): `guidance-notes.mjs` lines 13, 14, 70 and 71 hold `to confirm`, and line 95 is the `noteText` return; S10-S3-2b's expected string is on test line 166; `index.astro` lines 134-136 hold the caption; `grep -c "to confirm"` on `public/sample-pack/T1.html`, `T7.html` and `T8.html` gives 18, 4 and 3. Site S10-S3-2/2b, TAP reporter: `fail 2` against `tip` and against `pre`, `pass 2` against `base` (see below). |
| FA-R2: the module docstring of `test_e15_sections.py` is false | closed | At `effc5c7`, `with_note_fields` over the shipped map: `rows 32 empty section 32`. It gave 21 × (`to confirm`, `to confirm`), 9 × (`to confirm`, `n/a`) and 2 × (`n/a`, `n/a`). The 9 `n/a` rows are the 4 `FDA_STAT2007_*`, `GB_PMS_44ZM3`, `GB_PMS_44ZL`, `EU_MDR_ART86_1` and the two `MDCG_*` rows. The row families are AIDSF 12 and PCCP 9, so 21. The new sentence matches these figures. `grep` of the tip (excluding `handoffs/`) finds the three removed phrases only in `test_e15_repair1.py`'s own list. |
| RG-N1: the draft-row docstring says "cannot drop them" | closed | Mutant K at the tip (when `section` is filled, the item's `label` becomes the row's `document` and `draft` becomes `False`) gives **7 failed, 41 passed** over `test_e15_sections`, `test_render_furniture`, `test_e14_margin_notes` and `test_e11_aidsf_header`. The draft-row test is among the 41. The 7 failures are the same tests the note names: test (b), the furniture test, the section-7 test, `..._without_its_qualifier[T1]` (html), and the DOCX cases `[T1]`, `[T7]` and `[T8]`. With the tip's test file copied into `effc5c7`, the draft-row test is the 1 pass of `14 failed, 1 passed`. So the new wording ("passes at effc5c7 and calls no label code"; "inspected by test (b) ... and by `test_e11_aidsf_header.py`") holds against both runs. |
| RG-N2: the pre-build failure reasons are incomplete | closed (build note) | At `effc5c7` with only the test file copied in: 14 failed, 1 passed. Four of the failures are on `FileNotFoundError` for `guidance_sections.yaml`. In the hybrid (the tip's CSV, YAML and goldens also copied in): **11 failed, 4 passed**. The 11 break down as `AttributeError ... 'ESTAR_GAP'` 7, `'SECTION_GAP'` 1, `assert 'VIII. Data Management' == 'section VIII...ta Management'` 1, and `'to confirm' not in ...` 2. That equals `E15_build.md` line 58 as corrected. |
| RG-N3: the fixtures diff list is incomplete | closed (build note) | `fixtures --offline` at `base` and at the tip: 46 rows, matched 35, not built 4, suite only 7, both exit 0. My key-by-key diff of the two `fixtures_report.json` gives exactly `/doctor[12]/info`, `/duration_s`, `/generated`, `/git_sha`, `/rows[36]/reason`. |
| RG-N4: no `PROOFPACK_HOME` in the re-run block | closed | The repair note's block exports it. `E15_build.md` line 119 adds it. |
| RG-N5, RG-N6, FA-R3..R7 | carried, still open | The repair changed no code, CSV, YAML, template or golden (`git diff --stat e5319e0 0fb6f71 -- tests/fixtures src/proofpack/templates design` is empty), so the lens-1 mutants M3, M7, M8 and M9 survive by construction. I re-ran M3 only (below). |

### The site measurement (RG-B1 repro, re-run)

`cd proofpack-site && PROOFPACK_ENGINE_DIR=<tree> PROOFPACK_ENGINE_NO_SIBLING=1 TEMP=<scratch> TMP=<scratch> node --test --test-reporter=tap --test-name-pattern="S10-S3-2" tests/day10-demo-screen3.test.mjs`. The site's `git status --porcelain` was 0 lines before and after.

| engine tree | S10-S3-2 | S10-S3-2b |
|---|---|---|
| `tip` 0fb6f71 | not ok: `actual: 'to confirm', expected: '[unverified] section not transcribed'` | not ok: `... · section to confirm · eSTAR: to confirm` vs `... · section [unverified] section not transcribed · eSTAR: [unverified] eSTAR section not mapped` |
| `pre` e5319e0 | not ok | not ok |
| `base` effc5c7 | ok | ok |

One trap for whoever re-runs this. With `PROOFPACK_ENGINE_DIR` given as a Git Bash path built with `\\` inside double quotes in a loop, both tests reported **skipped** (`# pass 0`, `# fail 0`, `# skipped 2`). The default spec reporter then prints `pass 0 / fail 0`, which can read as green. Pass a `cygpath -m` path, as above, and read the `skipped` count.

## Non-blocking

**N1. A docstring sentence in the diff states the site's port as current (sentence).**
- `anchors.with_note_fields`, new paragraph: "from E15 each field carries its own words and the templates print it bare. The site ports this rule in ``proofpack-site/src/data/guidance-notes.mjs``".
- At site HEAD `576bd09` the port implements the **effc5c7** rule (`|| 'to confirm'`, bare `'n/a'`, lines 70-71). Against this function it gives `fail 2` (table above).
- The second half ("its tests S10-S3-2 and S10-S3-2b compare that port with this function, field by field and as the note's text") is true. I read both tests: S10-S3-2 compares `label`, `draft`, `section`, `estar` and `url`, and S10-S3-2b compares `noteText` with a string built from the engine's fields.
- Suggested wording: "The site ported the effc5c7 rule in ... and must re-port it when its pin moves past E15; its tests S10-S3-2 and S10-S3-2b compare that port with this function, field by field and as the note's text."

**N2. Part of the lane-S record lives outside the repository.**
- `test_e15_repair1.py`'s module docstring says "The record is in the function's docstring and in the repair note's changes for lane S". The repair note is `scratchpad/notes/E15_repair1.md`, not a committed file. `git ls-files handoffs` at the tip has no E15 build or repair handoff, only the two lens-1 notes.
- The docstring alone names the shape change, the port's path and the two test ids. It does not carry the re-vendor of `guidance_map_v1.csv` (S10-S3-1), the sample-pack counts or `index.astro`.
- Carry: the merge handoff (`handoffs/2026-10-08_E15.md`, as E14's was) should carry the repair note's items 1-7 verbatim.

**N3. One sentence in the note claims what an unwritten test would catch, with no run recorded (hard rule).**
- FA-R4: "A test feeding `"   "` would kill it."
- I built and ran the counter-example in `mut`. The test sets `FDA_AIDSF_DATA_MGMT`'s `section` to `"   "` and asserts `with_note_fields(...)["section"] == anchors.SECTION_GAP`.
  - At the tip: `1 passed`.
  - With M3 (`.strip()` removed): it fails on `AssertionError: section    ` / `assert 'section    ' == '[unverified]...t transcribed'`.
- So the sentence is true by my run, not by the note's. Separately, no section in the shipped CSV is whitespace-only (0 of 32), which supports the note's "not reachable".

**N4. The note's re-run block is Git Bash only.**
- Its first line, `export PYTHONPATH=...`, fails in PowerShell 5.1: "The term 'export' is not recognized as the name of a cmdlet...".
- The note says PowerShell was not run. With `$env:` assignments (my `scripts/ps_rerun.ps1`), every row of its table reproduces in PowerShell (figures in the verdict).

**Informational.**
- The RG-B1 regression test pins four phrases of a docstring (`at effc5c7 both fields were bare`, the port's path, `S10-S3-2 and S10-S3-2b`, `DEC-43`). It records the change. It does not inspect behaviour: no engine test inspects the site's port, and that is lane S's S10-S3-2 once the pin moves.
- My Git Bash run in `wt-e15` printed `370 files already formatted` and `status lines 1`. The cause was the parallel lens's untracked `handoffs/2026-10-08_E_e15_lens2_fresh-attack.md` (16:03), which appeared mid-run. The PowerShell run before it printed 369 and 0 lines.
- My own process: for M3 I used `sed -i` on `src/proofpack/render/anchors.py` inside my scratch `mut` worktree, then ran `git checkout -- .` (status empty). No tracked file outside my worktrees was touched.

## What I could not break

- **Suites, both shells, `wt-e15` at `0fb6f71`.** I ran the note's table row by row:

  | command | Git Bash | PowerShell 5.1 | note |
  |---|---|---|---|
  | full | 2442 passed, 4 skipped in 318.08s | 2442 passed, 4 skipped in 337.66s | 2442 / 4 in 330.39s |
  | `-m day15` | 22 passed, 2424 deselected | same | same |
  | `-m day14` | 84, 2362 deselected | same | same |
  | `-m day13` | 133, 2313 deselected | same | same |
  | `-m day12` | 199 + 3 skipped, 2244 deselected | same | same |
  | `-m ap4`, `PROOFPACK_REQUIRE_DOCX=1` | 201, 2245 deselected | same | same |
  | `test_e15_repair1.py test_e15_sections.py` | 22 passed | 22 passed | 22 passed |
  | `ruff check .` | All checks passed! | All checks passed! | same |
  | `ruff format --check .` | 370 (see Informational) | 369 | 369 |
  | `doctor --offline` | exit 0 | exit 0, "All essential checks passed." | same |
  | `fixtures --offline` | exit 0, 46 / 35 / 0 / 0 / 0 / 4 / 7 | same | same |

  - **Scratch `tip` tree, Git Bash:** 2441 passed, 5 skipped in 404.73s. The extra skip is `test_e8_repair4.py:405`, because `confusables-18.0.0.txt` is absent from a scratch tree.
  - **ruff (0.16.6) file counts:** 366 at `e5319e0` and 369 at the tip. Its verbose output lists `handoffs/*.md` as included, so the note's "plus the new test file and the two lens notes" holds.
- **Fails before.**
  - `test_e15_repair1.py` alone in `pre`: 7 failed, 0 passed.
  - The six sentence tests fail on `assert '<phrase>' not in` or `in '"""Build day 15 ...'`. The RG-B1 test fails on `AssertionError: at effc5c7 both fields were bare`. These are the note's quoted first lines.
  - With the tip's `test_e15_sections.py` also copied in: 1 failed (RG-B1), 21 passed. So each docstring test is pinned by the docstring edit and nothing else.
- **Nothing weakened.**
  - `git diff --name-status e5319e0 0fb6f71` gives A for the two lens notes, M for `src/proofpack/render/anchors.py`, A for `tests/test_e15_repair1.py`, and M for `tests/test_e15_sections.py`. Nothing is deleted.
  - The `test_e15_sections.py` change is two docstrings only.
  - A `grep` of the diff for skip/xfail/only/todo/marker lines finds only lens-note prose and the new file's `pytestmark = pytest.mark.day15` and two `parametrize` lines. No marker was removed.
- **No rendered byte.** No golden, template, CSV or YAML is in the repair diff. Across the whole of E15 (`effc5c7..0fb6f71`), the goldens have 72 changed lines, all `class="margin-note` asides, and 0 others.
- **Provenance, all 30 filled rows.**
  - My script finds: 30 filled `section` cells, 30 YAML rows, no extra YAML row.
  - For each row: the YAML `section` equals the CSV's character for character; the YAML `map_document` equals the CSV `document`; the document entry has a non-empty `url`, `date_read`, `version_line` and `fetch`; and the row has at least one heading. Problems: none.
  - The two empty rows are `PP_SCOPE` and `PP_METHODS`.
- **Sources (fetched today with curl and a browser UA, read-only, nothing committed).** All seven match the YAML byte count and SHA-256:

  | document | bytes |
  |---|---|
  | AI-DSF | 1,590,866 (`62e83e0f...7520bc`) |
  | STAT2007 | 344,921 |
  | PCCP | 666,195 |
  | SI 2024/1368 HTML | 139,552 (`9b81984c...463c24`) |
  | MDR OJ PDF | 1,517,689 |
  | MDCG 2022-21 | 1,426,146 |
  | MDCG 2020-8 | 697,086 |

  - **Headings and quotes.** My own checker (`scripts/check_all.py`, pypdf 6.14.2, text normalised for quotes, dashes, margin line numbers and whitespace) looks for every quoted heading and topic quote on the page it names. Result: **80 found, 1 missing** over 30 rows.
  - The miss is `2. Avoid elimination of equivocal results` (p18), the footnote case the YAML records.
  - An earlier pass of my checker also missed `the data used for testing is sequestered from the development process` (p25). I printed the page: it reads `sequestered901 \nfrom the development process.902`, so the miss was my normaliser and the text is there.
- **Mutant K** (above): 7 killed tests named, and the draft-row test survives, as the repair note says.
- **CI gate.**
  - `bash workflows/ci_gate.sh C:/Users/joshs/GPS/ProofPack/wt-e15 HEAD` printed `gate: JoshSandhu/proofpack 0fb6f71 -> ci/0fb6f71-1791470693-33466`, `gate: run 37795001932 ci: success`, `gate: GREEN 0fb6f71`, exit 0.
  - `gh run view 37795001932`: head `0fb6f71dad358e6dd0a5a2ef818fa86f859ad736`, `success`. Jobs: unshare -rn, wheel, ap4 docx-extra, pytest + ruff, pip-audit, scipy-uninstalled import, Docker smoke. All 7 succeeded.
  - The note's run 37792272671: same head, `success`, 7 jobs `success`, branch `ci/0fb6f71-1791469496-28852`.
  - `git ls-remote origin 'refs/heads/ci/0fb6f71-1791470693*'` printed nothing afterwards.
  - A third run, 37795608374 on `ci/0fb6f71-1791470957-34416`, was in progress when I listed runs. It is another session's gate, not mine.

## What I could not check

- **The rest of the site suite against `0fb6f71`.** I ran only S10-S3-2/2b, as lens 1 did. Lane S's tree is read-only for me today, and lens 1 reports that other engine-touching site tests write into the engine directory or licence paths; I did not verify that.
- **The consolidated MDR.** I read only the OJ print hash; I did not retry EUR-Lex.
- **Topic fit of the 30 sections.** I checked that the quotes are present, not that each section is the best location. FA-R7 (`FDA_AIDSF_CALIBRATION`, Appendix C p49) stays the builder's open question.
- **Linux and Python 3.12** outside CI (the gate's runs cover them).

## Sentences I refused to write

- "RG-B1 is fixed." The record is fixed. The site's port and S10-S3-2/2b still fail against this engine (`fail 2`).
- "The new regression tests pin the cross-lane contract." They pin docstring text.
- "No wrong section can pass the tests." Lens 1's M8 and M9 are unchanged by this repair.
- "The sections are correct." What I can say is narrower: 80 of 81 quotes are on the page named, the 81st is the recorded footnote case, and all seven hashes match.

## Re-run

    S=C:/Users/joshs/AppData/Local/Temp/claude/C--Users-joshs-GPS-ProofPack/912d4d3b-b592-4cf7-adea-d5d99fc553d8/scratchpad/lens-E15-r2-regression
    git -C C:/Users/joshs/GPS/ProofPack/proofpack worktree add --detach $S/pre e5319e0
    cp C:/Users/joshs/GPS/ProofPack/wt-e15/tests/test_e15_repair1.py $S/pre/tests/
    cd $S/pre && PYTHONPATH=$S/pre/src PROOFPACK_HOME=<empty dir> python -m pytest -q -p no:cacheprovider tests/test_e15_repair1.py   # 7 failed
    powershell -File $S/scripts/ps_rerun.ps1    # PowerShell form of the note's table, writes $S/ps_rerun.txt
    cd $S/scripts && python check_all.py $S <tree>   # needs $S/dl/*.pdf and si.html from the fetch

The worktrees were removed at close. The scripts and downloads stay in my scratch label.
