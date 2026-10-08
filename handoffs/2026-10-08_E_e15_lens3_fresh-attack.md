**Verdict: PASS. 0 blockers, 5 record-and-carry findings (4 of them sentences). Gate GREEN on `6f49dc1`: run 37806643252, `ci: success`, 7 jobs, exit 0. My first gate invocation's CI run 37804590882 also concluded success, but the script exited 2 on a syntax error: `workflows/ci_gate.sh` was rewritten on disk (16:57:17) while it ran. Details under "CI gate".**

Figures:
- **Suite** at `6f49dc1` in a scratch tree: `2447 passed, 5 skipped in 396.60s`. The fifth skip is `test_e8_repair4.py:405` (confusables file absent from a scratch tree), so this equals the note's `2448 passed, 4 skipped`. Markers: `day15` 28, `day14` 84, `day13` 133, `day12` 199 + 3 skipped, `ap4` (`PROOFPACK_REQUIRE_DOCX=1`) 201. `ruff check` clean (0.16.6). `ruff format --check`: 372 files at the tip, 369 at `0fb6f71`.
- **Fails-before.** `tests/test_e15_repair2.py` copied into `0fb6f71`: `2 failed, 4 passed`. The 2 are the two docstring tests.
- **Sources.** I fetched all seven documents myself. All seven SHA-256 values equal the YAML's. 80 of 81 quoted headings and topic quotes are on the page named; the 81st is the recorded footnote heading.
- **Consolidated MDR, newly checked.** EUR-Lex served the consolidated text this time (HTTP 200, 1,629,329 bytes; "02017R0745 — EN — 10.01.2025"). Article 86 there has the same heading and paragraph 1 opening as the OJ print, with no amendment marker inside the article.
- **Rendered packs.** I rendered run T1/T7/T8 and compare T2/T7/T8 on the 5,000-row synthetic cohort, in HTML and DOCX, `--offline`, with every socket call denied. 0 socket calls were recorded. Results: 0 `to confirm`; 0 regulatory notes without `[unverified]`; 0 AI-DSF mentions without the draft label within 250 characters. The render at `6f49dc1` equals the render at `0fb6f71` apart from the run id and the duration.
- **Earlier lens findings.** FA-L2-N1 / RG-N1 is closed: the docstring is now true, and the site port, fed every row, still differs in 64 of 64 fields. FA-L2-N2 is closed as a sentence and still carried as behaviour. FA-R4 (mutant M3) is closed.
- **New.** L3-N1: a non-equivalent mutant survives 765 map-touching tests. It prints a blank `section` unmarked whenever `estar_section` is filled. The repair-2 test name says "section or estar", but the test only ever blanks both together.

# E15 lens 3 (cold fresh-attack) on engine 6f49dc1 - Thursday 8 October 2026

This lens attacks E15 repair 2, the single commit `6f49dc1` on `0fb6f71`, and the repairer's note `scratchpad/notes/E15_repair2.md`. It also re-attacks the whole E15 package from `effc5c7`: the sections against the documents, the rendered packs, the goldens, the network and the gate.

Method:
- **Worktrees.** Four detached worktrees under `scratchpad/lens-E15-r3-fresh-attack/`:
  - `tip` (`6f49dc1`) for the full suite, markers and lint;
  - `mut` (`6f49dc1`) for mutants, counter-examples, doctor and fixtures;
  - `base` (`0fb6f71`) for fails-before;
  - `e14` (`effc5c7`) for the pre-E15 render.
- **PYTHONPATH.** Set to each tree's `src` (Windows form, via `cygpath -w`). Each time I checked it with `python -c "import proofpack;print(proofpack.__file__)"`, which printed `...\lens-E15-r3-fresh-attack\<tree>\src\proofpack\__init__.py`.
- **PROOFPACK_HOME.** An empty directory under my label for every run. The render script writes its own ephemeral-signed licence (`tests/conftest.py::write_licence`).
- **Mutants.** Each was reverted with `git checkout -- .`. Afterwards `git status --short` was empty in `mut`. In `base` it listed only the copied-in test file, which I then removed.
- **Platform.** Windows 11 Home 10.0.26200, Python 3.14.6, Git Bash, node (site port only). I did not run PowerShell 5.1.
- **Commits and refs.** I made no commits. The only ref pushed was the gate's own throwaway branch.

## Blockers

None. Under this lens's rule a blocker is:
- a wrong or unsourced section;
- a lost marking;
- a failing gate;
- a test that cannot fail;
- a test that passes at `0fb6f71` where it claims to pin a change.

Each attack below found none of these. The gate result is under "CI gate".

## Non-blocking (record-and-carry)

### L3-N1. A blank `section` beside a filled `estar_section` can lose its `[unverified]` marking with every test green; the repair-2 test name says "section or estar" but feeds only both-blank (sentence violation)

- **The name.** `tests/test_e15_repair2.py::test_rg_n3_a_blank_section_or_estar_cell_prints_the_unverified_gap` sets `section` and `estar_section` of `FDA_AIDSF_DATA_MGMT` to the same blank value **together**. It never blanks one cell while the other is filled.
- **The other empty-section test.** `test_e15_sections.py::test_an_empty_section_prints_the_unverified_gap_not_to_confirm` blanks `FDA_AIDSF_CALIBRATION`, whose `estar_section` is already empty.
- **Mutant M-or**, run in `mut`. In `with_note_fields` I changed

      "section": f"section {section}" if section else SECTION_GAP,

  to

      "section": f"section {section}" if (section or estar) else SECTION_GAP,

  and ran the 37 test files that touch the map, the anchors, the goldens or the margin notes (`grep -l -E "guidance_map|margin|golden|anchors|guidance_sections" tests/*.py`). Unmutated, they give `765 passed, 1 skipped`. Under the mutant they give **`765 passed, 1 skipped in 88.89s`**.
- **What the mutant prints.** With `GB_PMS_44ZL`'s `section` set to `""` (its `estar_section` is `n/a`), `with_note_fields` returns `'section '`. That is a gap with no `[unverified]`. The same holds for every UK, EU and MDCG row, and for any FDA row whose eSTAR cell is filled.
- **Why not a blocker.**
  - The shipped code is correct: at the tip the same input returns `[unverified] section not transcribed`.
  - Every regulatory row of the shipped map has a filled section.
  - So no page loses a marking today. This is a coverage gap in the class of FA-R4.
- **Carry.** Add one case to the RG-N3 test that blanks `section` alone on a row whose `estar_section` is `n/a`, and run M-or against it. I have not built or run that test.
- **Repro:** in a tip worktree, apply the one-line change above, then `python -m pytest -q $(grep -l -E "guidance_map|margin|golden|anchors|guidance_sections" tests/*.py)` gives `765 passed, 1 skipped`.

### L3-N2. `with_note_fields` docstring: "(``eSTAR: n/a`` for a non-FDA row)" is false for a non-FDA row with an empty cell (sentence violation; FA-R5 class)

The diff re-wrapped this line. The code does not know whether a row is FDA or not; it prints whatever the cell holds. Counter-examples run at the tip, with `with_note_fields` on a modified map:

| row | change | `estar` returned |
|---|---|---|
| `GB_PMS_44ZL` | `estar_section = ""` | `[unverified] eSTAR section not mapped` |
| `EU_MDR_ART86_1` | `estar_section = "  "` | `[unverified] eSTAR section not mapped` |
| `FDA_STAT2007_CI` | `estar_section = "n/a"` | `eSTAR: n/a` |

What the code actually does: it prints `eSTAR: <cell>` whenever the cell is non-blank after `str.strip()`. Today's map holds `n/a` in all five non-FDA regulatory rows. Mutant D-c changed the parenthetical to "for every non-FDA row, whatever its cell": `28 passed` over the three E15 test files. Not reachable on the shipped map.

**Repro:** `with_note_fields(guidance_ref_item('GB_PMS_44ZL', rows), rows)` with that row's `estar_section` set to `""` returns `'[unverified] eSTAR section not mapped'`.

### L3-N3. `test_no_section_or_estar_cell_of_the_shipped_map_is_only_characters_strip_keeps` inspects four characters; other invisible characters `str.strip()` keeps still print unmarked (test-name sentence; FA-L2-N2 class)

- **What the test inspects.** `KEPT_BY_STRIP = ("\u200b", "\u2060", "\ufeff", "\u180e")`. `str.strip()` keeps every character that is not whitespace, so the test name claims more than these four.
- **Counter-examples run at the tip.** Each character below was set as both `section` and `estar_section` of `FDA_AIDSF_CALIBRATION`. Each printed `section <char>` and `eSTAR: <char>` with no marking:
  - U+200C, U+200D, U+3164;
  - U+00AD, U+2800, U+115F;
  - U+034F, U+2061.
- **Consistent edits.** These used my script `tools/invis.py`, which sets the CSV cell and the YAML `section`/`headings` of `GB_PMS_44ZL` to one character. Each was run over the 37 map-touching files:

  | character | result |
  |---|---|
  | U+200B | `1 failed, 764 passed, 1 skipped`. The failure is the new test (`Left contains one more item: ('GB_PMS_44ZL', 'section', '\u200b')`), so lens 2's surviving U+200B mutant is now killed |
  | U+200C | `765 passed, 1 skipped`. It prints `'section \u200c'`, `eSTAR: n/a` |
  | U+3164 | `765 passed, 1 skipped` |

- **Why not a blocker.** The docstring's own claim is narrower ("it keeps U+200B, U+2060, U+FEFF and U+180E, so a cell made only of those prints ... with no marking"), and that is true. The note's "Sentences refused" names U+3164. Only the test name overstates. Not reachable on the shipped map: a CSV-only edit fails the provenance test (lens 2).
- **Repro:** `python tools/invis.py <mut> GB_PMS_44ZL 200c && python -m pytest -q $(cat out/mapfiles.txt)` gives `765 passed, 1 skipped`.

### L3-N4. The docstring tests pin chosen phrases, not the absence of a false guarantee (surviving docstring mutants)

Mutants on the new docstring, run over `test_e15_repair2.py`, `test_e15_repair1.py` and `test_e15_sections.py` (28 tests, `28 passed` unmutated):

| mutant | result |
|---|---|
| D-a: `U+200B, U+2060, U+FEFF and U+180E` -> `U+200B and U+FEFF` | 1 failed |
| D-b: `Both gap strings begin ``[unverified]``.` -> `Every gap reaches the page marked ``[unverified]``.` (false: U+200C, above) | **28 passed** |
| D-c: non-FDA parenthetical -> "for every non-FDA row, whatever its cell" (false: L3-N2) | **28 passed** |
| D-d: the three named inputs -> `feeds every blank cell` (false: the test feeds three values) | **28 passed** |
| C2: `SECTION_GAP` without `[unverified]` | 4 failed |
| C3: `ESTAR_GAP` without `[unverified]` | 7 failed |

- **What the tests read.** They read for the absence of the two old sentences only (`The site ports this rule`, `never hidden`). A false guarantee in other words survives.
- **The note.** It says what its own mutant table ran ("append `A gap is printed, never hidden.`" gave 1 failed). It does not claim more. Recorded, not graded.

### L3-N5. The YAML's eSTAR reason quotes a column heading with a straight apostrophe where the document prints U+2019 (character-level quote mismatch; not a section value, not rendered)

- **The YAML.** In `design/guidance_sections.yaml`, `estar.reason` reads `"Recommended Section in Sponsor's Marketing Submission"`, with U+0027.
- **The document.** AI-DSF PDF page 43 (Appendix A) prints `Sponsor’s`, with U+2019.
- **Grading.** The `section` values in the CSV keep the document's characters (`FDA_STAT2007_PPA_NPA` keeps U+201C/U+201D, as in the PDF). This quote lives only in prose that no page prints. It is carried from the build commit `17501c3`; repair 2 did not touch it.

### Carried items re-checked

| item | status at `6f49dc1` | evidence (measured here) |
|---|---|---|
| FA-L2-N1 / RG-N1 (site-port sentence) | **closed** | The new sentence says the port "still implemented the effc5c7 rule at site 576bd09 (lines 70-71 and 95)". `git show 576bd09:src/data/guidance-notes.mjs`: line 70 is `section: internal ? 'n/a' : String(row.section ?? '').trim() \|\| 'to confirm',`, line 71 is the `estar` twin, and line 95 is ``return `maps to ${note.label} · section ${note.section} · eSTAR: ${note.estar}`;``. My own `siteport/cmp.mjs` fed the port every row of the tip's map: `rows 32 field mismatches 64 label mismatches 0`. S10-S3-2 is at test line 103 and S10-S3-2b at 149 (its expected string at 166). The site HEAD is still `576bd09`. |
| FA-L2-N2 (sentence "never hidden") | **closed as a sentence**; behaviour carried (L3-N3) | `grep` of `src tests design scripts` finds `never hidden` and `ports this rule` only in `test_e15_repair2.py`'s own assertions. |
| FA-R4 (mutant M3, `.strip()` removed) | **closed** | `test_e15_repair2.py` at `0fb6f71` with M3 (both strips removed): `4 failed, 2 passed` (2 docstring tests + the three-spaces and tab-space cases). With only the `estar` strip removed: `4 failed, 2 passed`. With only the `section` strip removed: `4 failed, 2 passed`. |
| RG-B1 (the lane-S record) | closed as a record in lens 2 | The docstring now says what the site does; items 1-7 remain in scratch notes only (RG-N2, carried to the merge handoff). |
| FA-R3, FA-R5, FA-R6, FA-R7, RG-N5, RG-N6 | carried, unchanged | `git diff --stat 0fb6f71 6f49dc1 -- tests/fixtures src/proofpack/templates design scripts` is empty. |

## What I could not break (with figures)

**1. Suite, markers, lint, doctor and fixtures at `6f49dc1`.**

| command | result |
|---|---|
| full suite (`tip`, Git Bash) | `2447 passed, 5 skipped in 396.60s` (skips: 3 `test_day12_r_captures`, 1 `test_doctor_cli.py:58`, 1 confusables) |
| `-m day15` | `28 passed, 2424 deselected` |
| `-m day14` | `84 passed` |
| `-m day13` | `133 passed` |
| `-m day12` | `199 passed, 3 skipped` |
| `PROOFPACK_REQUIRE_DOCX=1 -m ap4` | `201 passed` |
| `ruff check .` | `All checks passed!` |
| `ruff format --check .` | `372 files already formatted`; `369` at `0fb6f71`. `ruff format --check` on the two lens-2 notes plus `test_e15_repair2.py` gives `3 files already formatted`, so the note's 369 + 3 holds |
| `doctor --offline` | exit 0, "All essential checks passed." |
| `fixtures --offline` | `rows 46: matched 35, not matched 0, no oracle recorded 0, no independent oracle 0, not built 4, suite only ... 7` |

All equal the repair note's figures.

**2. Fails-before.** `test_e15_repair2.py` copied into `0fb6f71`: `2 failed, 4 passed in 0.43s`. Both failures are the docstring tests: `assert 'The site ports this rule' not in ...` and `assert 'never hidden' not in ...`. The 4 passes are the shipped-map inspection and the three blank cases, which the test module's docstring says pass at `0fb6f71`.

**3. Repair 2 changes no behaviour.**
- `git diff 0fb6f71 6f49dc1 -- src` is one hunk inside the `with_note_fields` docstring.
- I rendered both commits with the same script (`tools/render.py`, below). After normalising UUIDs, hashes and timestamps, `tools/rdiff.py` finds only two kinds of difference:
  - the run id (`<title>` and footer);
  - `Duration (s)` / `duration_s`, e.g. `1.259` -> `1.189`.
- DOCX `document.xml`: T1 0 lines and T7 0 lines changed. T8 changed 2 lines, the duration only.
- No statistic moved, so there is nothing to re-derive in this commit.

**4. Sources (attack 1).** I fetched all seven documents on 8 October 2026 with curl into `src/`:

| document | HTTP, bytes | SHA-256 = YAML |
|---|---|---|
| AI-DSF | 200, 1,590,866 | `62e83e0f...7520bc` yes |
| STAT2007 | 200, 344,921 | `4a5c66b8...51bd0b` yes |
| PCCP | 200, 666,195 | `80f0f423...e4d9` yes |
| SI 2024/1368 (HTML) | 200, 139,552 | `9b81984c...3c24` yes |
| MDR OJ print | 200, 1,517,689 | `71f1b6b6...6db9` yes |
| MDCG 2022-21 | 200, 1,426,146 | `d1dc8af7...3f4` yes |
| MDCG 2020-8 | 200, 697,086 | `3ea53b2e...3f21` yes |

- **Extraction.** `pdftotext -enc UTF-8 -layout`, split at form feeds; the SI went through `html.parser`.
- **Heading check.** `tools/chk.py` normalises dashes, apostrophes, whitespace and the AI-DSF margin line numbers, keeps curly double quotes, and looks each YAML heading and topic quote up on its named page. Result: `ok 80 bad 1 rows 30`. The miss is `2. Avoid elimination of equivocal results`: page 18 prints `equivocal5`, the footnote the YAML records.
- **Rows I read against the table of contents and the body.** 19 rows across all seven documents:
  - **AI-DSF.** The TOC (PDF p3) gives VI p10, VI.B p12, VIII p18, IX p24, X p26, X.A p27, XI p32, XIII p37, App C p44, App E p50; PDF = printed + 3.
    - `FDA_AIDSF_LABELING_METRICS`: "Device Performance Metrics" is line 606 on p17, after "B. Labeling" (line 538, p15) and before VII (line 672). It reads "All performance estimates should be provided with confidence intervals."
    - `FDA_AIDSF_TEST_INDEPENDENCE`: "Management and Independence of Data" is line 897; the sequestration bullet is line 901; "Representativeness" is line 908.
    - `FDA_AIDSF_SITE_DIVERSITY`: "at least three geographically diverse US clinical sites" is line 931 (p26), before IX at line 966.
    - `FDA_AIDSF_CALIBRATION`: "calibration analysis" is line 1191 (p32), inside X.A (line 1089) and before XI (line 1287). The YAML note's sentence "An explanation of any calibration of the model output." is line 1031 (p29), before "X. Validation" at line 1041. So it is under IX Model Development, as the note says.
    - `FDA_AIDSF_SUBGROUP_PERF`: "subgroups of interest" is line 1100 (p30), under X.A.
    - `FDA_AIDSF_MODEL_CARD`: Appendix E is line 1917, p53.
  - **STAT2007.** The TOC gives 5 at p14 and 6 at p17.
    - `FDA_STAT2007_BY_SITE` and `FDA_STAT2007_CI`: p15 carries "Reporting study results" ("report all results by ... clinical site or specimen collection site") and "Measures of accuracy" ("two-sided 95 percent confidence intervals"). They are flat subheadings of 5, between "Descriptions of comparative results and methods" (p14) and "Underlying quantitative result".
    - `FDA_STAT2007_PPA_NPA`: 6.1 on p17, with U+201C/U+201D in both the PDF text and the CSV (compared by codepoint).
    - `FDA_STAT2007_INDETERMINATE`: 6.2 on p18.
  - **PCCP.** "Document issued on August 18, 2025. / Document originally issued on December 4, 2024." The TOC (PDF pp3-4) gives V.C at printed 13, V.D at 15 and VII.B(1)-(4) at 25-28; PDF = printed + 4.
    - `FDA_PCCP_LABELING`: V.C is on p17 and V.D on p19. "FDA recommends that the labeling include a statement that the device has an authorized PCCP." is on p18, inside V.C.
    - `FDA_PCCP_PMS_PLANS`: the post-market surveillance sentence is on p32 inside "(4) Update procedures", before VII.C on p33.
    - `FDA_PCCP_MP3_PERF_EVAL`: (3) is on p31.
    - `FDA_PCCP_TRACEABILITY`: VII.C is on p33.
    - `FDA_PCCP_IMPACT`: VIII is on p34.
  - **SI.** Line 80 "New Part 4A (post-market surveillance requirements)". Line 327 "Post-market surveillance report" and line 328 "44ZL.—(1) ... the manufacturer must produce a post-market surveillance report". Line 346 "Periodic safety update report" and line 347 "44ZM.—(1)". Line 351 "(3) The PSUR must include—". "come into force 6 months after the day on which they are made", with "Made 16th December 2024", matches the CSV's `in force 2025-06-16`.
  - **MDR.** PDF p72 prints `L 117/72` and "Article 86 / Periodic safety update report / 1. Manufacturers of class IIa, class IIb and class III devices".
  - **MDCG 2022-21.** "ANNEX I: Template for the PSUR" is on p21 (contents p2).
  - **MDCG 2020-8.** "Post-market clinical follow-up evaluation report Template" is on p4 (contents p3).
- **Versions.**
  - The FDA AI-DSF guidance page (HTTP 200, 36,182 bytes): "Draft Guidance ... January 2025", "Not for implementation", "Content current as of: 01/07/2025", one link `/media/184856/download`.
  - The PCCP page (HTTP 200): "Final", "Content current as of: 08/18/2025", `/media/166704/download`.
- **Consolidated MDR (not reached by lenses 1-2).** `https://eur-lex.europa.eu/legal-content/EN/TXT/HTML/?uri=CELEX:02017R0745-20250110` returned HTTP 200, 1,629,329 bytes (SHA-256 `b16dec92...ddc78`), headed "Consolidated TEXT: 32017R0745 — EN — 10.01.2025". Article 86 reads "Article 86 Periodic safety update report 1. Manufacturers of class IIa, class IIb and class III devices shall prepare a periodic safety update report ...". The text from the Article 85 tail to "Article 87" has 0 `▼` amendment markers. So paragraph 1 is unamended to that consolidation. The YAML still says "later amendments were not read"; that is now out of date, not false.

**5. Topic (attack 2).** For the 19 rows above I read the section's text against `internal_id` and the note's D4 seed. None is off topic. `FDA_AIDSF_CALIBRATION` (X.A) stays the weakest, as FA-R7 carries.

**6. Markings (attack 3).** `tools/render.py` runs a licensed `--offline` `run` (T1, T7, T8) and `compare` (T2, T7, T8; prior `make_cohort(n=5000, separation=1.2)`) of the 5,000-row synthetic cohort, in json, html and docx. Socket `connect`, `connect_ex`, `getaddrinfo` and `create_connection` all raise. Result: `rc 0 0 socket calls []`.

`tools/marks.py` checks every margin note: its shape, its section against the CSV, the FDA eSTAR gap, the draft label, and `to confirm` anywhere on the page.

| page | notes | regulatory | with `[unverified]` | `to confirm` | bad |
|---|---|---|---|---|---|
| run T1 html / docx | 21 / 21 | 20 / 20 | 20 / 20 | 0 / 0 | 0 / 0 |
| cmp T2 html | 10 | 9 | 9 | 0 | 0 |
| run and cmp T7 html / docx | 6 | 4 | 4 | 0 | 0 |
| run and cmp T8 html / docx | 6 | 3 | 3 | 0 | 0 |

- **The checker can fail.** On the `effc5c7` render it reports `bad 54` on T1.html and `to confirm` 32 on T1.html.
- **Draft label.** `tools/draftscan.py` finds the AI-DSF title or "AI-DSF draft/guidance" 50 times on T1.html, 12 on T2.html and 13 on cmp T8.html (40 in T1.docx). Each one has "draft" and "not for implementation" within 250 characters: 0 without, on every page.
- **`[unverified]` outside the notes.** T7 has 19 at `effc5c7` and 19 at the tip; the other pages have 0 and 0.
- **run.json.** It carries no `to confirm` and no `[unverified]`, and no eSTAR field.

**7. Network and goldens (attack 4).**
- **Network.** My `plug/nosock3.py` denies the four socket calls. I proved it records calls first: a probe test calling `create_connection` gave `NOSOCK calls=1`. With it loaded:
  - `-m day15`: `28 passed`, `NOSOCK calls=0`;
  - `test_e14_margin_notes`, `test_render_furniture`, `test_claims` and `test_e11_aidsf_header`: `194 passed`, `NOSOCK calls=0`.
- **Goldens.** `git diff 0fb6f71 6f49dc1` touches no golden. `git diff -U0 effc5c7 6f49dc1 -- tests/fixtures/golden` has 72 changed lines, 0 outside a `margin-note` aside.

**8. Counter-examples on `with_note_fields` (at the tip, modified maps).**

| case | input | outcome |
|---|---|---|
| CE-e | section `" \u200b "` | `'section \u200b'` (the docstring's carried case, true) |
| CE-f | section `None` | the gap (`_rows` maps `None` to `""`) |
| CE-g | FDA row, section `n/a` | `'section n/a'`, unmarked. A CSV edit; not reachable without failing the provenance test |
| CE-h | FDA row, status `Internal ` | `section n/a · eSTAR: n/a`. The AI-DSF label loses its draft words, which `test_claims` catches (lens 1 M10) |
| CE-i | section `[unverified] X` | `'section [unverified] X'` |

**9. Note sentences checked and found true.**
- "the only `src/` change is the docstring";
- "no template, CSV, YAML or golden is in the commit";
- `2 failed, 4 passed` at `0fb6f71`;
- the M3 and estar-only `2 failed, 1 passed` for the RG-N3 test (my whole-file runs give `4 failed, 2 passed` = 2 docstring + 2 blank cases);
- `rows 32 field mismatches 64`;
- port lines 70-71 and 95;
- 372/369 formatted;
- U+3164 is `Lo`, `isspace()` False (`unicodedata`: `Lo False HANGUL FILLER`);
- the U+200B counter-example fails the new shipped-map test.

## CI gate (attack 5)

**First invocation.** `bash workflows/ci_gate.sh C:/Users/joshs/GPS/ProofPack/wt-e15 HEAD` (HEAD `6f49dc1840deabdf4c533221c0d0078597d9de96`) printed:

    gate: JoshSandhu/proofpack 6f49dc1 -> ci/6f49dc1-1791474874-45382
    gate: run 37804590882 ci: success
    C:/Users/joshs/GPS/ProofPack/workflows/ci_gate.sh: line 71: syntax error near unexpected token `)'

and exited 2.

- **Why.** The script's mtime is `2026-10-08 16:57:17`. Its new LOCAL MODE block, for private repos, was added while my invocation was waiting. Bash reads a script as it runs, so it resumed at a shifted offset.
- **The CI run itself.** `gh run view 37804590882`: head `6f49dc1...`, conclusion `success`, all 7 jobs `success`.
- **The branch.** The crash skipped the branch deletion, and `ls-remote` still listed `ci/6f49dc1-1791474874-45382`. I deleted exactly that branch, `git push origin --delete ci/6f49dc1-1791474874-45382`, the step the gate would have run.
- **Not an E15 defect.** It is a hazard for any gate running while the script is being edited. `bash -n` on the edited script prints no error. The engine repo is public, so the new block does not apply to it.

**Second invocation**, on the edited script:

    gate: JoshSandhu/proofpack 6f49dc1 -> ci/6f49dc1-1791475797-47008
    gate: run 37806643252 ci: success
    gate: GREEN 6f49dc1

exit 0.
- **The run.** `gh run view 37806643252`: head `6f49dc1840deabdf4c533221c0d0078597d9de96`, conclusion `success`, 7 jobs, all `success`:
  - pytest + ruff;
  - wheel artefact;
  - pip-audit;
  - import proofpack (scipy uninstalled);
  - Docker image smoke;
  - pytest -m ap4 with [docx];
  - unshare -rn.
- **Branches.** `git ls-remote origin 'refs/heads/ci/6f49dc1*'` printed 0 lines afterwards.
- **Other runs on this sha.** The repairer's run 37799340823 and a third run 37802619513 (another session's gate) are also `success` on the same sha.
- **Refs.** I pushed no other ref.

## What I could not check

- **The site's own tests.** I did not run them: lane S's tree is read-only today. The 64-field figure comes from the port copied out with `git show 576bd09:` and run in my label with `papaparse` stubbed (`noteFor` does not use it).
- **Consolidations after 10.01.2025.** I did not look for a later consolidation of the MDR, or for an amending act touching Article 86 after that date.
- **Rows not read in the body.** 11 of the 30 filled rows I checked only by the heading lookup (on the named page), not by reading the body. Lenses 1 and 2 read all 30.
- **PowerShell 5.1, and Linux / Python 3.12.** I did not run PowerShell 5.1. Linux and Python 3.12 are covered only by the gate's CI run.

## Sentences I refused to write

- "No unfilled row can reach the page unmarked." L3-N1 (mutant M-or, `765 passed`) and L3-N3 (U+200C, `765 passed`) are the counter-examples for what the tests would let through. What I can say: on today's map and code, the six rendered pages and five DOCX files carry 0 unmarked regulatory notes.
- "The transcribed sections are correct." What I can say: 80 of 81 quotes are on the named page of bytes that hash to the YAML's values, the 81st is the recorded footnote, and I read 19 rows against the TOC and body.
- "Article 86 has never been amended." I read one consolidation (10.01.2025).
- "The site now matches the engine." 64 of 64 fields differ.

## Re-run

    S=C:/Users/joshs/AppData/Local/Temp/claude/C--Users-joshs-GPS-ProofPack/912d4d3b-b592-4cf7-adea-d5d99fc553d8/scratchpad/lens-E15-r3-fresh-attack
    git -C C:/Users/joshs/GPS/ProofPack/proofpack worktree add --detach $S/mut 6f49dc1
    export PYTHONPATH=$(cygpath -w $S/mut/src) PROOFPACK_HOME=<empty dir>; python -c "import proofpack;print(proofpack.__file__)"
    python -m pytest -q -p no:cacheprovider                                    # 2447 passed, 5 skipped in a scratch tree
    python $S/tools/chk.py $S $S/mut                                           # needs $S/txt from the fetch; ok 80 bad 1
    python $S/tools/render.py $(cygpath -w $S/mut) $(cygpath -w $S/out/r) && python $S/tools/marks.py $S/out/r $S/mut && python $S/tools/draftscan.py $S/out/r
    (cd $S/siteport && node cmp.mjs)                                           # field mismatches 64 (in.json from the tip)
    # L3-N1: apply M-or (see above) in mut, then
    python -m pytest -q -p no:cacheprovider $(cat $S/out/mapfiles.txt); git -C $S/mut checkout -- .   # 765 passed, 1 skipped
    python $S/tools/invis.py $S/mut GB_PMS_44ZL 200c && python -m pytest -q $(cat $S/out/mapfiles.txt); git -C $S/mut checkout -- .   # L3-N3

The scripts stay in my scratch label. The worktrees were removed at close.
