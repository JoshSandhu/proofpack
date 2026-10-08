**Verdict: PASS for the E15 fresh-attack package, 0 blockers under this lens's grading rule. That does not clear the merge: regression lens 1's B1 (`handoffs/2026-10-08_E_e15_lens1_regression.md`) still stands. I re-derived its source half read-only (R1 below) and carry it as a finding here.**

Figures:
- **Sources.** I downloaded all seven documents myself. The six PDF SHA-256 values equal the ones in `design/guidance_sections.yaml`.
- **Headings and quotes.** The provenance file quotes 81 headings and topic phrases. Each one is found in my own extraction on the page it names, except one. That one is the `2. Avoid elimination of equivocal5 results` heading, whose footnote digit the file records it dropped.
- **Topics.** All 30 filled sections are about their row's topic.
- **Rendered packs.** I rendered T1, T7 and T8 (run) and T2, T7 and T8 (compare) on the 5,000-row synthetic cohort with `--offline` and every socket connect and DNS lookup denied. The socket calls recorded were `[]`. There is 0 `to confirm` in any HTML or DOCX. Every AI-DSF note carries the draft label. Every regulatory note carries its section, and every FDA note carries `[unverified] eSTAR section not mapped`.
- **CI gate.** GREEN on `e5319e0`: run 37788120819, `ci: success`, and `ls-remote` afterwards lists no `ci/e5319e0*` branch.

# E15 lens 1 (cold fresh-attack) on engine e5319e0 - Thursday 8 October 2026

This lens attacks the four commits `63d09bf`..`e5319e0` on `effc5c7`. It also checks the builder's note `scratchpad/notes/E15_build.md`.

Method:
- **Worktrees.** Three detached worktrees under `scratchpad/lens-E15-r1-fresh-attack/`:
  - `tip` (`e5319e0`);
  - `base` (`effc5c7`);
  - `mut` (`e5319e0`, for mutants).
- **PYTHONPATH.** Set to each tree's `src` and checked with `python -c "import proofpack;print(proofpack.__file__)"`. That printed `...\lens-E15-r1-fresh-attack\tip\src\proofpack\__init__.py` (and `base\...` for base).
- **PROOFPACK_HOME.** An empty directory under my label for every run.
- **Platform.** Windows 11 Home, Python 3.14, Git Bash.
- **No commits.** I made none. The only ref I pushed is the gate's own throwaway branch, through `workflows/ci_gate.sh`, which deleted it.

## Blockers

None under this lens's rule. The rule counts as a blocker:
- a wrong or unsourced section;
- a lost marking;
- a failing gate;
- a test that cannot fail;
- a test that passes at `effc5c7` where it claims to pin a change.

## Record-and-carry

### R1. `anchors.with_note_fields` changed its return shape. The site's JS port still prints the old shape, and the note's Carried list does not name it (DEC-43). This agrees with regression lens 1, B1.

- **At `effc5c7`.** The function returned bare `section` and `estar` values: the row's text, or `to confirm`, or `n/a`.
- **At `e5319e0`.** Each value carries its own words:
  - `section <...>`, `[unverified] section not transcribed` or `section n/a`;
  - `eSTAR: <...>`, `[unverified] eSTAR section not mapped` or `eSTAR: n/a`.
- **The site.** I read `proofpack-site` and ran nothing there. `src/data/guidance-notes.mjs` lines 70-71 still read:

      section: internal ? 'n/a' : String(row.section ?? '').trim() || 'to confirm',
      estar: internal ? 'n/a' : String(row.estar_section ?? '').trim() || 'to confirm',

  `tests/day10-demo-screen3.test.mjs` (S10-S3-2, S10-S3-2b) asserts `mine.section == theirs.section` against the engine's `with_note_fields`.
- **The note.** Its Carried list names only the sample pack and `index.astro`.
- **Repro:** `grep -n "to confirm" proofpack-site/src/data/guidance-notes.mjs` gives lines 13, 14, 70 and 71. Then `PYTHONPATH=<tip>/src python -c "from proofpack.render import anchors as a; print(a.with_note_fields(a.guidance_ref_item('PP_SCOPE')))"` prints `'section': 'section n/a'`, where the port prints `n/a`.
- **Grading.** This lens's rule does not make it a blocker. Regression lens 1 graded it a blocker, and that grading holds for the merge.

### R2. A sentence in the new test's module docstring is false (sentence violation)

`tests/test_e15_sections.py` lines 3-5 read: "At effc5c7, 30 of the 32 rows ... had an empty ``section`` (the other two are ProofPack's own text) and every ``estar_section`` was empty or ``n/a``, so every regulatory margin note printed ``section to confirm · eSTAR: to confirm``."

Two counter-examples, both run:
- **Empty rows.** At `effc5c7` the CSV has **32 of 32** rows with an empty `section`, not 30. My count: `base rows 32 empty section 32`. The day-1 test asserted every section blank.
- **The note text.** At `effc5c7`, T7 from my synthetic run printed `... (2007-03-13, final) · section to confirm · eSTAR: n/a` for `FDA_STAT2007_CI`. So the four `FDA_STAT2007_*` notes did not print `eSTAR: to confirm`, and neither did the GB, EU and MDCG rows, whose `estar_section` was `n/a`.

**Repro:** `python marks.py out/render_base base`. The T7 entry shows `section to confirm · eSTAR: n/a`.

### R3. A wrong section that is consistent between the CSV and the YAML passes every test that touches the map

These two mutants each changed the map CSV and `guidance_sections.yaml` together. Each was run against the 29 test files that read the map, anchors, goldens or margin notes.

| mutant | result |
|---|---|
| M8: `EU_MDR_ART86_1` changed to `Article 85 (Periodic safety update report), paragraph 1` | `760 passed, 1 skipped` |
| M9: `GB_PMS_44ZM3` changed to `regulation 44ZL (Periodic safety update report), paragraph (3)` | `760 passed, 1 skipped` |

- **What the tests inspect.** `test_every_quoted_heading_appears_in_the_section_in_order` checks the YAML's headings against the YAML's own `section`. `test_every_filled_section_has_a_source_row_with_url_date_and_version` checks the CSV against the YAML. No test checks either file against the document. That is by design (no network in tests).
- **Why the UK and EU rows are uncovered.** None of `GB_PMS_*`, `EU_MDR_*` or `MDCG_*` is an anchor in any shipped template (grep of `src/` and the goldens). So no golden covers those five rows.
- **What a test can still catch.** An FDA row that is wrong in both files is caught only if it appears in a golden.
- **Carry.** A cheap closing step that needs no network would store, per row, a short extracted text window (heading plus the next line) with its page and the PDF's SHA-256, and assert the section's last heading occurs in that window. It still would not re-read the PDF.

### R4. Surviving mutant: whitespace-only `section`

- **The mutant.** M3 removes `.strip()` from `section = row.get("section", "").strip()` in `anchors.with_note_fields`. Result: `760 passed, 1 skipped`.
- **At the tip.** My counter-example CE2 (`section = "   "`) prints `[unverified] section not transcribed`.
- **Under the mutant.** It would print `section    `, with no marking.
- **The gap.** No test feeds a blank-but-not-empty section.

### R5. Surviving mutant: a UK or EU row with an empty `estar_section` prints the eSTAR gap

- **The mutant.** M7 empties `GB_PMS_44ZL`'s `estar_section`. Result: `760 passed, 1 skipped`.
- **Why it survives.** `test_no_fda_row_claims_an_estar_section_while_none_was_read` explicitly allows `""` for non-FDA rows. So a UK regulation can print `[unverified] eSTAR section not mapped`, which is meaningless for a programme that is FDA's.
- **Effect today.** No shipped template renders those rows.

### R6. The GB section names a regulation of the 2002 Regulations under the 2024 SI's document

- **What the note says.** The `GB_PMS_44ZM3` note will read "maps to ... SI 2024/1368 ... · section New Part 4A (post-market surveillance requirements) > regulation 44ZM (Periodic safety update report), paragraph (3)".
- **What the SI says.** Its regulation 4 ("New Part 4A (post-market surveillance requirements)") inserts regulations 44ZC-44ZR into the Medical Devices Regulations 2002. I checked `si.txt`: line 81 says "After regulation 44ZB(4) ... insert—", and lines 346-351 show "Periodic safety update report / 44ZM.—(1) ... (3) The PSUR must include—".
- **Grading.** The section is correctly transcribed and on topic. A reader could still cite "SI 2024/1368 regulation 44ZM", which is not that instrument's own numbering. The provenance file's `extraction` line says this, but the page does not.
- **Effect today.** No template renders the row.

### R7. Topic choice for `FDA_AIDSF_CALIBRATION` is the weakest of the 30

- **Where the quote sits.** X.A's only calibration text (p32, line 1191) is an example bullet about prognostic decision-support devices. Appendix C (p49) names "calibration plot" among evaluation methods.
- **Grading.** X.A is a correct ancestor and on topic, so this is not a blocker. Appendix C is an arguably closer second location. That is the builder's open question 2; I add Appendix C p49 as a candidate.

## What I could not break (with figures)

**1. Suite and lint at `e5319e0` (`tip`, Git Bash).**

| command | result |
|---|---|
| full suite | `2434 passed, 5 skipped in 374.44s` (the extra skip is `test_e8_repair4` confusables, absent in a scratch worktree, as in the note) |
| `-m day15` | 15 passed |
| `-m day14` | 84 |
| `-m day13` | 133 |
| `-m day12` | 199 + 3 skipped |
| `-m ap4` (`PROOFPACK_REQUIRE_DOCX=1`) | 201 |
| `ruff check` | `All checks passed!` |
| `ruff format --check` | `366 files already formatted` |

All of these equal the note's figures.

**2. Prefix runs at `effc5c7`.**
- `tests/test_e15_sections.py` copied in alone: `14 failed, 1 passed`. The pass is `test_the_draft_row_keeps_its_status_and_the_sections_do_not_carry_it`, which is a guard on the CSV, not a claim to pin E15.
- With the tip's CSV, YAML and goldens also copied in: `11 failed, 4 passed`. The four passes are the three data-only provenance tests plus the draft guard.

**3. Sources (attack 1).** I fetched the seven documents on 8 October 2026 with curl and extracted them with `pdftotext 4.06 -layout`. For the SI I used `html.parser`.
- **Hashes.** The six PDF hashes equal the YAML's:
  - AI-DSF `62e83e0f...7520bc`
  - STAT2007 `4a5c66b8...51bd0b`
  - PCCP `80f0f423...e4d9`
  - MDR OJ `71f1b6b6...6db9`
  - MDCG 2022-21 `d1dc8af7...3f4`
  - MDCG 2020-8 `3ea53b2e...3f21`
- **Headings and quotes.** `verify_yaml.py` normalises quotes, dashes, the AI-DSF margin line numbers and whitespace, then looks up each heading and each topic quote on its named page. Result: 80 OK, 1 BAD across 30 rows. The BAD one is the footnote heading the YAML records.
- **Rows I read against the table of contents and the body.** All 30 filled rows (AI-DSF 12, STAT2007 4, PCCP 9, SI 2, MDR 1, MDCG 2), across all seven documents:
  - **AI-DSF.** VIII (p21), VIII > Reference Standard (p24), VIII > Management and Independence of Data (p25), VIII > Representativeness (p25; the three-sites quote p26, before IX at p27), VI.B > Device Performance Metrics (p17, between B. Labeling p15 and VII p19), X.A (p30), XI (p35), XIII (p40), Appendix C (p47), Appendix E (p53).
  - **STAT2007.** 5 > Measures of accuracy and 5 > Reporting study results (p15), 6 > 1. (p17), 6 > 2. (p18). The TOC places 5 at p14 and 6 at p17.
  - **PCCP.** V.C (p17; the labeling statement p18, before V.D p19), VI (p24), VII.B (1)-(4) (pp29-32), VII.C (p33), VIII (p34). This matches the TOC on PDF pp3-4.
  - **SI 2024/1368.** 44ZL and 44ZM(3), with "The PSUR must include—".
  - **MDR OJ.** PDF page 72 prints `L 117/72` and "Article 86 / Periodic safety update report / 1. Manufacturers of class IIa, class IIb and class III devices".
  - **MDCG 2022-21.** "ANNEX I: Template for the PSUR" (p21; contents p2).
  - **MDCG 2020-8.** "Post-market clinical follow-up evaluation report Template" (p4; contents p3).
- **Heading characters.** The PPA/NPA heading's curly quotes are U+201C/U+201D in the PDF, as in the CSV. The version lines "Document issued on January 7, 2025.", "Document issued on August 18, 2025." / "Document originally issued on December 4, 2024." and "Made 16th December 2024" are in the documents.
- **eSTAR.** The eSTAR Program page returned HTTP 200 with "Content current as of: 09/21/2026". Its 15 "section" mentions are about eSTAR's own form sections (Standards, Classification, Additional Information Response); none maps a section to a guidance topic. The AI-DSF Appendix A on p43 says "One way this documentation may be submitted is through the eSTAR Program."

**4. Topic (attack 2).** For each row I read the section's text against `internal_id` and the D4 seed in `notes`. None is off topic. R7 is the weakest.

**5. Markings (attack 3).** `render.py` runs a licensed `--offline` `run` (T1, T7, T8; json, html, docx) and a `compare` (T2, T7, T8; prior = `make_cohort(n=5000, separation=1.2)`) of the 5,000-row synthetic cohort.

| page | margin notes | notes with `[unverified]` | `to confirm` (base -> tip) |
|---|---|---|---|
| T1.html | 21 | 20 | 32 -> 0 |
| T2.html | 10 | 9 | 18 -> 0 |
| T7.html | 6 | 4 | 7 -> 0 |
| T8.html | 6 | 3 | 6 -> 0 |

- **HTML.** The notes without `[unverified]` are all `PP_*` (`section n/a · eSTAR: n/a`). Every AI-DSF mention (50 on T1) has the draft label beside it.
- **DOCX.** In T1.docx, 21 note paragraphs, 0 AI-DSF notes without `draft guidance (January 2025), not for implementation`, 0 regulatory notes unmarked, 0 `to confirm`. The same holds for T7.docx and T8.docx from both run and compare.
- **Outside the margin notes.** With run ids, timestamps, hashes and paths normalised, the pages differ between base and tip only in two blank lines in T1 and in `Duration (s)`. `run.json` differs only in `duration_s`, `mapping_sha256` (a path), `run_id` and `started`.
- **Other `[unverified]` markings.** Those outside the notes are unchanged: T7 has 19 at base and 19 at the tip.

**6. Network and goldens (attack 4).**
- The plugin `plug/nosock.py` denies `socket.connect`, `connect_ex` and `getaddrinfo`. With it loaded, `tests/test_e15_sections.py` gave `15 passed`, `NOSOCK calls=0`. That file plus `test_e14_margin_notes.py` and `test_doctor_cli.py` gave `31 passed, 1 skipped`.
- `git diff -U0 effc5c7 e5319e0 -- tests/fixtures/golden` has 72 changed lines, all `<aside class="margin-note...`, and 0 others.
- Regulatory notes in the goldens: T1 20, T2 9, T7 4, T8 3, T12 1. So the parametrised golden test is not vacuous for any template.

**7. Counter-examples on the note fields.** These are monkeypatched maps rendered through `render_t1` and `render_docx_bytes`.

| case | input | outcome |
|---|---|---|
| CE1 | `section = 'X. Validation & <A> "Perf"'` | HTML escaped (`&amp; &lt;A&gt; &#34;`); DOCX `document.xml` well-formed |
| CE2 | section `"   "` | prints the `[unverified] section not transcribed` gap |
| CE3 | estar `" \t "` | prints the eSTAR gap |
| CE4 | `PP_SCOPE` given section `7.2` | prints `section n/a · eSTAR: n/a` |
| CE5 | an FDA row with estar `n/a` | prints `eSTAR: n/a` unmarked; the CSV test `test_no_fda_row_claims_an_estar_section_while_none_was_read` covers this case |
| CE6 | an AI-DSF row set `final` | M10 below shows `test_claims` fails |

**8. Mutants.** Each was run on the 29 files in `out/mutfiles.txt`, which give `760 passed, 1 skipped` unmutated.

| mutant | change | result | first failing tests |
|---|---|---|---|
| M1 | `SECTION_GAP` -> `"section to confirm"` | 3 failed | `test_an_empty_section_prints_the_unverified_gap_not_to_confirm` and both markings tests |
| M2 | `ESTAR_GAP` -> `"eSTAR: to confirm"` | 13 failed | `test_ap4_repair1` T7 count, `test_e10_t2` golden |
| M3 | strip removed | survived | R4 |
| M4 | internal row returns bare `n/a` | 9 failed | |
| M5 | `base.html` drops `{{ ref.estar }}` | 10 failed | `test_ap4_roundtrip` html count |
| M6 | `FDA_STAT2007_CI` estar back to `n/a` | 7 failed | `test_no_fda_row_claims_an_estar_section_while_none_was_read` |
| M7 | GB 44ZL estar emptied | survived | R5 |
| M8, M9 | consistent wrong section | survived | R3 |
| M10 | an AI-DSF row set `final` | 13 failed | `test_claims::test_the_guidance_map_draft_rows_all_carry_the_qualifier_and_are_the_fda_aidsf_rows` |
| M11 | DOCX generator back to `· section {{ ... }} · eSTAR: {{` without regenerating | 3 failed | `test_the_regenerated_template_equals_the_committed_one_part_by_part[T1,T7,T8]` |
| M12 | `MDCG_2020_8` section emptied | 2 failed | `test_every_filled_section_has_a_source_row_with_url_date_and_version`, `test_no_regulatory_row_is_left_empty_without_a_reason` |

After every mutant, `git status --short` in `mut` was empty.

**9. CI gate (attack 5).**
- **Command:** `bash workflows/ci_gate.sh C:/Users/joshs/GPS/ProofPack/wt-e15 HEAD`, with HEAD `e5319e030c63d8c278f9fcffba293b9b84beccad`.
- **Output:** `gate: JoshSandhu/proofpack e5319e0 -> ci/e5319e0-1791467672-11813`, `gate: run 37788120819 ci: success`, `gate: GREEN e5319e0`, exit 0.
- **Branch.** `git ls-remote origin 'refs/heads/ci/e5319e0*'` printed nothing afterwards.

**10. Note sentences checked and found true.** Each was checked against the figures above:
- the provenance URLs and hashes;
- the 21/20 note counts;
- 32 -> 0 `to confirm` on T1;
- section 7 from 2 lines to 4;
- the T2 section-5 merge of `FDA_PCCP_MP4_UPDATE`/`FDA_PCCP_PMS_PLANS` (one `(4) Update procedures` line in my T2);
- `run.json` unchanged apart from run-specific keys;
- goldens changed only inside margin notes;
- the eSTAR page date;
- the Appendix A p43 wording;
- "This is the original version" on the SI page.

## What I could not check

- **The consolidated MDR.** Article 86 is checked only in the as-adopted Official Journal text. Three EUR-Lex requests (curl to `TXT/HTML/?uri=CELEX:02017R0745-20250110` and `ALL/?uri=CELEX:32017R0745`, and WebFetch of the first) returned HTTP 202 with an empty body, the same challenge the builder met. I did not bypass it.
- **Whether a later AI-DSF version exists.** I did not check for a final version or revision on fda.gov after January 2025. The `/media/184856/download` file still hashes to the draft.
- **The site.** I did not run the site's suite: lane S's tree, read-only today. R1 rests on reading `guidance-notes.mjs` and the test file, plus regression lens 1's measured `fail 2`.
- **PowerShell.** I did not run the suite in PowerShell 5.1. Regression lens 1 did.

## Sentences I refused to write

- "The transcribed sections are correct." What I can say is narrower: each of 80 quoted headings and quotes is in my extraction on the page named, the 81st is the recorded footnote case, and I read all 30 filled rows against the table of contents and the body.
- "No wrong section can pass the tests." R3 is the counter-example.
- "The UK and EU sections reach the buyer's page." No template anchors them.

## Re-run

    S=C:/Users/joshs/AppData/Local/Temp/claude/C--Users-joshs-GPS-ProofPack/912d4d3b-b592-4cf7-adea-d5d99fc553d8/scratchpad/lens-E15-r1-fresh-attack
    PYTHONPATH=$S/tip/src python -c "import proofpack;print(proofpack.__file__)"
    PROOFPACK_HOME=<empty dir> PYTHONPATH=$S/tip/src python -m pytest -q -p no:cacheprovider
    python $S/verify_yaml.py $S $S/tip/design/guidance_sections.yaml   # needs $S/src/*.txt from the fetch
    PYTHONPATH=$S/tip/src python $S/render.py $S/tip $S/out/render_tip && python $S/marks.py $S/out/render_tip $S/tip
    python $S/mutate.py $S/mut $S M3 M7 M8 M9                                # the survivors

The scripts stay in my scratch label. The worktrees were removed at close, so recreate them with `git -C proofpack worktree add --detach <path> e5319e0` before re-running.
