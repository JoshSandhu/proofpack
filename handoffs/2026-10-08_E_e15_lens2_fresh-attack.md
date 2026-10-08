**Verdict: PASS. 0 blockers, 2 record-and-carry findings. Both are false sentences: L2-N1 in the new docstring, and L2-N2 in a docstring line the diff touched.**

Figures:
- **Gate.** GREEN on `0fb6f71`: run 37795608374, `ci: success`, all 7 jobs succeeded; `ls-remote` afterwards lists no `ci/0fb6f71*` branch.
- **Suite.** 2441 passed, 5 skipped in a scratch tree; the fifth skip is the confusables path. `-m day15` 22, `day14` 84, `day13` 133, `day12` 199 + 3 skipped, `ap4` 201.
- **Lint.** ruff check is clean. ruff format: 369 files.
- **Repair tests.** All 7 tests of `test_e15_repair1.py` fail at `e5319e0`.
- **Sources.** All seven documents re-fetched; all seven SHA-256 values equal the YAML's. 80 of 81 quoted headings and quotes are on the named page (the 81st is the recorded footnote). All 30 filled rows were read against the TOC and the body, and are on topic.
- **Versions.** The AI-DSF draft is still the current FDA page ("Content current as of: 01/07/2025"). The MDCG index lists the same 2022-21 and 2020-8 versions.
- **Rendered packs.** Run T1/T7/T8 and compare T2/T7/T8, HTML and DOCX, licensed and `--offline`, with every socket call denied (0 recorded). 0 `to confirm`, 0 unmarked regulatory notes, 0 AI-DSF notes without the draft label.
- **Render diff.** The render at `0fb6f71` equals the render at `e5319e0` apart from run ids and the duration.
- **Regression lens 1 B1** is closed as a record.
- **L2-N1.** The new `with_note_fields` docstring says "The site ports this rule". The site's port implements the effc5c7 rule: 64 of 64 fields differ on the tip's map.
- **L2-N2.** "A gap is printed, never hidden" is false for a section of only U+200B, U+2060, U+FEFF or U+180E. Not reachable on the shipped map; FA-R3/FA-R4 class.

# E15 lens 2 (cold fresh-attack) on engine 0fb6f71 - Thursday 8 October 2026

This lens attacks E15 repair 1, the single commit `0fb6f71` on `e5319e0`, and the repair note `scratchpad/notes/E15_repair1.md`. It also re-checks the whole E15 package from `effc5c7`: the 30 transcribed sections against the documents, the rendered packs, the goldens and the gate.

Method:
- **Worktrees.** Four detached worktrees under `scratchpad/lens-E15-r2-fresh-attack/`: `tip` (`0fb6f71`, full suite), `mut` (`0fb6f71`, mutants, markers, renders, doctor, fixtures), `base` (`e5319e0`), `pre` (`effc5c7`). All were removed at close.
- **PYTHONPATH.** Set to each tree's `src` and checked each time with `python -c "import proofpack;print(proofpack.__file__)"`, which printed `...\lens-E15-r2-fresh-attack\<tree>\src\proofpack\__init__.py`. One check printed the MAIN tree (a `;`-joined Unix path in Git Bash); I discarded that run and re-ran with `cygpath -w` paths, which printed `mut\src`.
- **PROOFPACK_HOME.** An empty directory under my label for every run. The render script makes its own home with an ephemeral-signed licence (`tests/conftest.py::write_licence`).
- **Platform.** Windows 11 Home 10.0.26200, Python 3.14.6, Git Bash. I did not run PowerShell 5.1.
- **No commits.** I made none. The only ref pushed is the gate's own throwaway branch, through `workflows/ci_gate.sh`.

## Blockers

None. Under this lens's rule a blocker is: a wrong or unsourced section, a lost marking, a failing gate, a test that cannot fail, or a test that passes at `e5319e0` where it claims to pin a change. Each attack below found none of these.

## Non-blocking (record-and-carry)

### L2-N1. A new docstring sentence says the site ports the rule it does not port (sentence violation)

`src/proofpack/render/anchors.py`, `with_note_fields` docstring, added in `0fb6f71`: "from E15 each field carries its own words and the templates print it bare. The site ports this rule in ``proofpack-site/src/data/guidance-notes.mjs`` ..."

At site HEAD `576bd09` the port implements the effc5c7 rule, not this one. Lines 70-71 read `String(row.section ?? '').trim() || 'to confirm'` and `... || 'to confirm'`, and line 95 adds the words `section ` and `eSTAR: ` itself.

Counter-example, run. I copied `guidance-notes.mjs` from `git show 576bd09:` into my label, replaced its `papaparse` import with a stub (the two functions I call do not use it), and fed it every row of the tip's map next to the tip's `with_note_fields` output (`siteport/cmp.mjs`):

    rows 32 field mismatches 64 [["FDA_AIDSF_DATA_MGMT","section","VIII. Data Management","section VIII. Data Management"],["FDA_AIDSF_DATA_MGMT","estar","to confirm","[unverified] eSTAR section not mapped"], ...]
    port noteText with engine fields: maps to FDA draft guidance, ... not for implementation · section section VIII. Data Management · eSTAR: [unverified] eSTAR section not mapped

So 64 of 64 section/eSTAR fields differ. The second half of the sentence is true: S10-S3-2 compares the fields and S10-S3-2b compares the note text (`tests/day10-demo-screen3.test.mjs` lines 103-167 at `576bd09`).

- **Why not a blocker.** The record B1 asked for is complete: the repair note's "Changes for other lanes" items 1-7 name the contract change, `guidance-notes.mjs` lines 13-14, 70-71 and 95, S10-S3-2/2b, the re-vendor and the sample pack. I checked each line reference read-only at `576bd09`, and the sample-pack counts (`grep -c "to confirm"`: T1.html 18, T7.html 4, T8.html 3) reproduce. Only the docstring's present tense is wrong.
- **Suggested wording.** "The site's port, ``proofpack-site/src/data/guidance-notes.mjs`` (lines 70-71 and 95 at site 576bd09), still implements the effc5c7 rule; its tests S10-S3-2 and S10-S3-2b compare it with this function, field by field and as the note's text, and fail against E15 until lane S ports this rule."
- **Repro:** `node siteport/cmp.mjs out/port_in.json` prints `field mismatches 64`.
- **Mutant D1** removes "field by field and as the note's text" from the docstring. Result: `55 passed`. The RG-B1 test does not read that phrase. This is harmless, but it is recorded.

### L2-N2. "A gap is printed, never hidden (E9), and is marked [unverified]" is false for a section made only of invisible characters (sentence violation; FA-R3/FA-R4 class)

The diff touches this line: its closing quotes moved. `with_note_fields` tests emptiness with `str.strip()`, and `strip()` leaves U+200B, U+2060, U+FEFF and U+180E in place.

Counter-example, run on the tip, with `FDA_AIDSF_CALIBRATION`'s `section` and `estar_section` set to each value:

| value | `section` returned | `estar` returned | marked |
|---|---|---|---|
| U+200B | `'section \u200b'` | `'eSTAR: \u200b'` | no |
| U+2060 | `'section \u2060'` | `'eSTAR: \u2060'` | no |
| U+FEFF | `'section \ufeff'` | `'eSTAR: \ufeff'` | no |
| U+180E | `'section \u180e'` | `'eSTAR: \u180e'` | no |
| U+00A0 | `[unverified] section not transcribed` | the eSTAR gap | yes |
| U+3000 | `[unverified] section not transcribed` | the eSTAR gap | yes |

As a consistent edit (the CSV and `guidance_sections.yaml` both given `section: "\u200b"`, heading `"\u200b"`), run over the 36 test files that touch the map, the anchors, the goldens or the margin notes (`759 passed, 1 skipped` unmutated):

| row | result |
|---|---|
| `GB_PMS_44ZL` | `759 passed, 1 skipped` |
| `FDA_AIDSF_CALIBRATION` | `2 failed`: only the T1 and T7 golden byte comparisons |

- **Reachability.** Not reachable on the shipped map. A CSV-only edit fails `test_every_filled_section_has_a_source_row_with_url_date_and_version`.
- **Carry.** Carry with FA-R4 (mutant M3). A test that feeds `"   "` and `"\u200b"` to `with_note_fields` would inspect both cases. I have not built or run it, so I make no claim about what it would close.

### Carried items re-checked: none is marked fixed, and each still reproduces as carried
- **FA-R4** (mutant M3, `.strip()` removed). My S1 mutant gives `304 passed` under `-m "day15 or day14 or ap4"`.
- **FA-R3, FA-R5, FA-R6, FA-R7, RG-N5, RG-N6.** Unchanged: `0fb6f71` touches no CSV, YAML, template or render code.

## What I could not break (with figures)

**1. Suite and lint at `0fb6f71`.**

| command | result |
|---|---|
| full suite (`tip`, Git Bash) | `2441 passed, 5 skipped in 405.65s`. The fifth skip is `test_e8_repair4.py:405` (confusables file absent in a scratch tree), so this equals the note's `2442 passed, 4 skipped` in `wt-e15` |
| `-m day15` | `22 passed, 2424 deselected` |
| `-m day14` | `84 passed` |
| `-m day13` | `133 passed` |
| `-m day12` | `199 passed, 3 skipped` |
| `PROOFPACK_REQUIRE_DOCX=1 -m ap4` | `201 passed` |
| `ruff check .` | `All checks passed!` (0.16.6) |
| `ruff format --check .` | `369 files already formatted` at the tip, `366` at `e5319e0`. `ruff format --check` on the two lens notes plus `test_e15_repair1.py` gives `3 files already formatted`, so the note's Markdown explanation holds |
| `doctor --offline` | exit 0, "All essential checks passed." |
| `fixtures --offline` | exit 0, `rows 46: matched 35, not matched 0, no oracle recorded 0, no independent oracle 0, not built 4, suite only ... 7` |

**2. The repair's tests fail where they claim to pin a change.**
- `tests/test_e15_repair1.py` copied into `e5319e0`: `7 failed in 0.39s` (all 7).
- `tests/test_e15_sections.py` at `effc5c7`: copy-only `14 failed, 1 passed`; the pass is the draft-row test, which its new docstring says passes at effc5c7. With the tip's CSV, YAML and five goldens also copied in: `11 failed, 4 passed`. Both equal the corrected build note.

**3. Mutants on the repair (`mut`, 5 files: `test_e15_sections`, `test_e15_repair1`, `test_render_furniture`, `test_e14_margin_notes`, `test_e11_aidsf_header`; 55 tests).**

| mutant | change | result |
|---|---|---|
| K | label = bare document and `draft` False when the section is filled | `7 failed, 48 passed`: test (b), the furniture test, the section-7 test, `test_e11` T1 html and T1/T7/T8 docx. The draft-row test passes, as its new docstring says |
| D2 | `(DEC-43, lane S)` -> `(lane S)` | 1 failed (RG-B1 test) |
| D3 | module docstring back to `30 of the 32 rows` | 2 failed |
| D4 | `were bare` -> `carried their words` | 1 failed |
| D5 | port path renamed | 1 failed |
| D1 | see L2-N1 | survived |

After every mutant, `git status --short` was empty.

**4. Each new or changed sentence, checked against a measurement.**
- **"At effc5c7 all 32 rows ... empty section; ... 30 regulatory rows gave section to confirm; the 21 FDA AI-DSF and PCCP rows gave estar to confirm, and the 4 FDA_STAT2007_* rows and the 5 UK and EU rows gave n/a."** Measured at `effc5c7` through `with_note_fields`: `rows 32 empty section 32`; section `to confirm` 30 and `n/a` 2. estar values: `FDA_AIDSF` to confirm 12, `FDA_PCCP_` to confirm 9, `FDA_STAT2` n/a 4, `GB_PMS` n/a 2, `EU_MDR_ART86` n/a 1, `MDCG_*` n/a 2, `PP` n/a 2. True.
- **"at effc5c7 both fields were bare (...) and the templates printed the words section and eSTAR:".** The `effc5c7` `with_note_fields` returns `row...strip() or "to confirm"` and `"n/a"`. `base.html` line 14 prints `· section {{ ref.section }} · eSTAR: {{ ref.estar }}` at `effc5c7` and `· {{ ref.section }} · {{ ref.estar }}` at the tip. True.
- **"Inspects the CSV only ... It passes at effc5c7 and calls no label code. The draft label on the page is inspected by test (b) below and by test_e11_aidsf_header.py."** The body reads `status`, `version_date` and `section`. Test (b) is below it and asserts `draft and DRAFT_LABEL in text`. Mutant K kills four `test_e11` cases. True.
- **The `test_e15_repair1.py` docstring figures** (32 of 32; 21 / 9; mutant K leaves the draft-row test passing). True, by the measurements above.
- **The note's "No rendered byte changed".** I rendered at `e5319e0` and `0fb6f71` with the same script. After normalising run UUIDs, timestamps and hashes:
  - every HTML page differs only in the run-id line and the `<title>` run prefix;
  - the DOCX `document.xml` of T1, T7 (run and compare) is equal;
  - T8 differs in one value only, `0.938` -> `0.998` (run) and `1.260` -> `1.073` (compare), which is the duration.
- **The note's site line references.** `guidance-notes.mjs` lines 13-14, 70-71 and 95, and S10-S3-2b at line 166 of the test file, are where the note says at `576bd09` (read with `git show`, nothing run in the site tree).

**5. Sources (attack 1).** I fetched all seven documents myself on 8 October 2026 (curl, browser UA) into my label. The bytes and SHA-256 equal the YAML for all seven:

| document | bytes | SHA-256 |
|---|---|---|
| AI-DSF | 1,590,866 | `62e83e0f...7520bc` |
| STAT2007 | 344,921 | `4a5c66b8...51bd0b` |
| PCCP | 666,195 | `80f0f423...e4d9` |
| SI 2024/1368 HTML | 139,552 | `9b81984c...3c24` |
| MDR OJ print | 1,517,689 | `71f1b6b6...6db9` |
| MDCG 2022-21 | 1,426,146 | `d1dc8af7...3f4` |
| MDCG 2020-8 | 697,086 | `3ea53b2e...3f21` |

- **Extraction.** `pdftotext -enc UTF-8 -layout`, split at form feeds into PDF page indexes; the SI went through `html.parser`.
- **My own checker** (`tools/vy.py`) looks each YAML heading and topic quote up on its named page. It normalises curly apostrophes, dashes, AI-DSF margin numbers and whitespace, and keeps curly double quotes. Result: `ok 80 bad 1 rows 30`. The miss is `2. Avoid elimination of equivocal results`: page 18 prints `equivocal5`, the footnote the YAML records.
- **Rows read against the table of contents and body.** All 30 filled rows, across all seven documents:
  - **AI-DSF.**
    - The TOC on PDF p3 gives VIII p18, X p26, X.A p27, XI p32, XIII p37, App C p44, App E p50 (printed), which is PDF +3.
    - VIII's subheadings in order are Data Collection (p23), Data Cleaning/Processing, Reference Standard (p24), Data Annotation, Data Storage, Management and Independence of Data (p25), Representativeness (p25). The "three geographically diverse" text is on p26, before IX on p27.
    - VI.B Labeling (p15) holds Device Performance Metrics on p17 ("All performance estimates should be provided with confidence intervals.").
    - X.A starts on p30. The subgroup paragraph is on p30. The calibration bullet is on p32 line 1191, after "Assessing the Performance of the Human-Device Team" (p31) and before XI (p35), so X.A is a correct ancestor.
  - **STAT2007.** The TOC gives 5 at p14 and 6 at p17. On p15, "Reporting study results" (by site) and "Measures of accuracy" ("two-sided 95 percent confidence intervals") are both subheadings of 5. On p17 is 6.1, with curly U+201C/U+201D quotes as in the CSV; 6.2 is on p18.
  - **PCCP.** The TOC on pp3-4 is printed page +4.
    - V.C is on p17, with the labeling statement on p18 before V.D on p19. (4) Update procedures, on p32, footnote 106 points labeling recommendations to V.C.
    - VI is on p24; VII.B(1)-(4) are on pp29-32. The post-market surveillance sentence is on p32 inside (4), before VII.C on p33. VIII is on p34.
  - **SI.** It has the crosshead "New Part 4A (post-market surveillance requirements)", then 44ZL "Post-market surveillance report", 44ZM "Periodic safety update report", and 44ZM(3) "The PSUR must include—". It comes into force "6 months after the day on which they are made" (made 16 December 2024), which matches the CSV's `in force 2025-06-16`.
  - **MDR.** PDF p72 prints `L 117/72` and "Article 86 / Periodic safety update report / 1. Manufacturers of class IIa, class IIb and class III devices".
  - **MDCG 2022-21.** "ANNEX I: Template for the PSUR" is on p21 (contents p2).
  - **MDCG 2020-8.** "Post-market clinical follow-up evaluation report Template" is on p4 (contents p3).
- **Versions (checked beyond lens 1).**
  - The FDA guidance page for the AI-DSF draft (HTTP 200) still says "Draft", "Not for implementation", Docket FDA-2024-D-4488, "Content current as of: 01/07/2025", and links `/media/184856/download`. So no final version had replaced the draft on 8 October 2026.
  - The Commission's MDCG index (HTTP 200) lists "MDCG 2022-21 ... December 2022" and "MDCG 2020-8 ... April 2020", with the same file links the YAML records, and no revision.

**6. Topic (attack 2).** For each row I read the section's text against `internal_id` and the note's D4 seed. None is off topic. `FDA_AIDSF_CALIBRATION` (X.A) stays the weakest, as FA-R7 carries.

**7. Markings (attack 3).** `tools/render.py` runs a licensed `--offline` `run` (T1, T7, T8) and a `compare` (T2, T7, T8; prior `make_cohort(n=5000, separation=1.2)`) of the 5,000-row synthetic cohort, in json, html and docx. Socket `connect`, `connect_ex`, `getaddrinfo` and `create_connection` all raise. Result: `rc 0 0 socket calls []`.

| page | notes | with `[unverified]` | `to confirm` | AI-DSF title lines without the draft label |
|---|---|---|---|---|
| run T1.html | 21 | 20 | 0 | 0 |
| cmp T2.html | 10 | 9 | 0 | 0 |
| run T7.html / cmp T7.html | 6 / 6 | 4 / 4 | 0 | 0 |
| run T8.html / cmp T8.html | 6 / 6 | 3 / 3 | 0 | 0 |

- **HTML notes.** Every regulatory note carries `· section <the CSV's section> ·`, every FDA note ends with `[unverified] eSTAR section not mapped`, and every draft-row note has the `draft` class and `draft guidance (January 2025), not for implementation`. The notes without `[unverified]` are the `PP_*` notes (`section n/a · eSTAR: n/a`).
- **T1.** 50 AI-DSF title mentions, 52 draft labels.
- **DOCX** (`PPMarginNote` paragraphs): T1 21 notes (20 regulatory), T7 6 (4), T8 6 (3), for both run and compare. 0 bad, 0 `to confirm`, 0 `section section`, `eSTAR: eSTAR` or `eSTAR: [unverified]`.
- **Goldens.** Regulatory notes, each carrying the gap: T1 20/20, T2 9/9, T7 4/4, T8 3/3, T12 1/1.

**8. Network and goldens (attack 4).**
- **Network.** With my `nosock` plugin, `-m day15` gave `22 passed`, `NOSOCK calls=0`. Six files (`test_e15_sections`, `test_e15_repair1`, `test_e14_margin_notes`, `test_e11_aidsf_header`, `test_render_furniture`, `test_claims`) gave `216 passed`, `NOSOCK calls=0`.
- **Goldens.** `git diff e5319e0 0fb6f71` touches no golden. `git diff -U0 effc5c7 0fb6f71 -- tests/fixtures/golden` has 72 changed lines, 0 outside a `margin-note` aside.

**9. Earlier lens blockers.**
- **Regression lens 1 B1** (the record) is closed as a record. Every item its repair paragraph asked for is in the repair note's "Changes for other lanes" and in the build note's Carried list ("Added in repair 1"); the docstring sentence is L2-N1.
- **FA-R2 and RG-N1** sentences are replaced, and the replacements are true (item 4).
- **RG-N2 to RG-N4** are corrected in `E15_build.md` (lines 58, 78, 96, 119); I reproduced RG-N2's `14 failed, 1 passed` and `11 failed, 4 passed`.

**10. The builder's gate run.** `gh run view 37792272671`: head `0fb6f71dad358e6dd0a5a2ef818fa86f859ad736`, branch `ci/0fb6f71-1791469496-28852`, conclusion `success`. All 7 jobs succeeded:
- pip-audit;
- pytest + ruff;
- wheel artefact;
- Docker image smoke;
- ap4 with [docx];
- unshare -rn;
- scipy uninstalled.

## CI gate (attack 5)

`bash workflows/ci_gate.sh C:/Users/joshs/GPS/ProofPack/wt-e15 HEAD` (HEAD `0fb6f71`) printed:

    gate: JoshSandhu/proofpack 0fb6f71 -> ci/0fb6f71-1791470957-34416
    gate: run 37795608374 ci: success
    gate: GREEN 0fb6f71

The script exited 0.

`gh run view 37795608374`: head `0fb6f71dad358e6dd0a5a2ef818fa86f859ad736`, conclusion `success`. All 7 jobs succeeded:
- wheel artefact;
- pytest -m ap4 with the [docx] extra installed;
- Docker image smoke (linux/amd64, no push);
- pytest + ruff;
- pip-audit;
- import proofpack (scipy uninstalled);
- proofpack run inside unshare -rn (no network).

`git ls-remote origin 'refs/heads/ci/0fb6f71*'` printed nothing afterwards. I pushed no other ref.

## What I could not check

- **The consolidated MDR.** EUR-Lex `TXT/HTML/?uri=CELEX:02017R0745-20250110` returned HTTP 202 with 0 bytes again, and I did not bypass it. Article 86(1) is checked in the as-adopted OJ print only.
- **The site's own tests.** I did not run them: lane S's tree is read-only today. L2-N1 rests on the port copied out with `git show` and run in my label.
- **PowerShell 5.1.** I did not run the suite there.
- **Linux and Python 3.12** are covered only by the gate's CI run.

## Sentences I refused to write

- "The transcribed sections are correct." What I can say: 80 of 81 quoted headings and quotes are on the named page of the bytes the YAML hashes, the 81st is the recorded footnote, and I read all 30 rows against the TOC and body.
- "A gap can never reach the page unmarked." L2-N2 is the counter-example.
- "The site now matches the engine." 64 of 64 fields differ (L2-N1).
- "No wrong section can pass the tests." FA-R3 still stands, and so does the `GB_PMS_44ZL` invisible-section mutant at `759 passed`.

## Re-run

    S=C:/Users/joshs/AppData/Local/Temp/claude/C--Users-joshs-GPS-ProofPack/912d4d3b-b592-4cf7-adea-d5d99fc553d8/scratchpad/lens-E15-r2-fresh-attack
    git -C C:/Users/joshs/GPS/ProofPack/proofpack worktree add --detach $S/mut 0fb6f71
    export PYTHONPATH=$(cygpath -w $S/mut/src) PROOFPACK_HOME=<empty dir>; python -c "import proofpack;print(proofpack.__file__)"
    python -m pytest -q -p no:cacheprovider                                  # 2441 passed, 5 skipped in a scratch tree
    python $S/tools/render.py $S/mut $S/out/r_tip && python $S/tools/marks.py $S/out/r_tip $S/mut && python $S/tools/marks_docx.py $S/out/r_tip $S/mut
    python $S/tools/vy.py $S $S/mut                                           # needs $S/txt from the fetch; ok 80 bad 1
    node $S/siteport/cmp.mjs $S/out/port_in.json                              # L2-N1: field mismatches 64
    python $S/tools/zwsp.py GB_PMS_44ZL && python -m pytest -q $(cat $S/out/mutfiles.txt); git checkout -- .   # L2-N2

The scripts stay in my scratch label. The worktrees were removed at close.
