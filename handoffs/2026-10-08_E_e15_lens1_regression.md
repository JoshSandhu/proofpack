**Verdict: FAIL. 1 blocker. Every suite, marker, lint, doctor and fixtures figure in the E15 build note reproduces at `e5319e0`, in Git Bash and in PowerShell 5.1. Full suite at the tip: 2435 passed, 4 skipped in PowerShell, and 2434 passed, 5 skipped in Git Bash (the extra skip is the confusables path of a scratch worktree, as the note says). At `effc5c7`: 2420 passed, 4 skipped, with the confusables file supplied. `-m day15` 15, `day14` 84, `day13` 133, `day12` 199 + 3 skipped, `ap4` 201 in both shells. ruff is clean (366 files). The new test file gives `14 failed, 1 passed` at `effc5c7`. With the new CSV, YAML and goldens copied in it gives `11 failed, 4 passed`. Every quoted heading and topic quote in `design/guidance_sections.yaml` is in the document I fetched, on the page it names: 80 of 81, and the 81st is the footnote case the file records. All seven SHA-256 values match my own downloads. CI run 37783680895 (`ci`, head `e5319e0`) concluded success, 7 jobs. B1: E15 changes what `anchors.with_note_fields` returns, and the note's Carried list does not record it. The site's JS port and its tests S10-S3-2 and S10-S3-2b compare against that function. Pointed at `e5319e0` they give `fail 2`; at `effc5c7` they give `pass 2`. The site's local suite reads the sibling `../proofpack` HEAD, so it goes red when E15 lands on engine main.**

# E15 lens 1 (cold regression and record) on engine e5319e0 - Thursday 8 October 2026

This is a cold lens on `e15-sections` at `e5319e0`, four commits on `effc5c7`. It checks the builder's note `scratchpad/notes/E15_build.md`.

Method:
- **Worktrees.** Three detached worktrees under `scratchpad/lens-E15-r1-regression/`:
  - `tip` (`e5319e0`) for the full suites;
  - `mut` (`e5319e0`) for mutants, markers, fixtures and doctor;
  - `base` (`effc5c7`) for the pre-build runs.
- **PYTHONPATH.** Set to each tree's `src`. Each time I checked it with `python -c "import proofpack;print(proofpack.__file__)"`, which printed `...\lens-E15-r1-regression\<tree>\src\proofpack\__init__.py`.
- **PROOFPACK_HOME.** Set to an empty directory under my label for every run.
- **The note's own re-run block.** I ran it verbatim in `wt-e15`, in both shells. Both printed `C:\Users\joshs\GPS\ProofPack\wt-e15\src\proofpack\__init__.py`, and `git status --porcelain` there gave 0 lines.
- **Mutants.** Each was applied by a script and reverted with `git checkout -- .`. `git status --short` was empty after every run.
- **Platform.** Windows 11 Home, Python 3.14.6. I made no commits and pushed no ref.

## Blockers

### B1. The `with_note_fields` contract change and the site's port of it are missing from the record (DEC-43)

At `effc5c7`, `anchors.with_note_fields()` returned bare values:
- `section`: the row's section, or `to confirm`;
- `estar`: the row's eSTAR section, or `to confirm`;
- both `n/a` on an internal row.

At `e5319e0` each field carries its own words:
- `section`: `section <...>`, or `[unverified] section not transcribed`, or `section n/a`;
- `estar`: `eSTAR: <...>`, or `[unverified] eSTAR section not mapped`, or `eSTAR: n/a`.

`base.html` and the three DOCX templates no longer print the words `section` and `eSTAR:` themselves.

The site depends on the old contract in three places:
- `proofpack-site/src/data/guidance-notes.mjs` lines 70-71 port the old rule (`|| 'to confirm'`, `'n/a'`).
- Line 95 of the same file prints `maps to ${label} · section ${section} · eSTAR: ${estar}`.
- `tests/day10-demo-screen3.test.mjs` S10-S3-2 compares the port's `section` and `estar` fields to the engine's `with_note_fields` output, field by field. S10-S3-2b compares the full note text built from the engine's fields.

The site resolves the engine through `scripts/build-wheel.mjs` `engineDir()`: `PROOFPACK_ENGINE_DIR`, else the sibling `../proofpack`, at its HEAD.

Measured. I ran only those two tests, with TEMP, TMP and TMPDIR pointed into my label, `PROOFPACK_ENGINE_NO_SIBLING=1`, and `git status --porcelain` in the site at 0 lines before and after:

| `PROOFPACK_ENGINE_DIR` | S10-S3-2 | S10-S3-2b |
|---|---|---|
| `effc5c7` worktree | pass | pass |
| `e5319e0` worktree | **fail**: `actual: 'to confirm', expected: '[unverified] section not transcribed'` | **fail**: `actual: '... · section to confirm · eSTAR: to confirm'`, `expected: '... · section [unverified] section not transcribed · eSTAR: [unverified] eSTAR section not mapped'` |

The second expected string also shows a doubled `section [unverified] section`. That is what the site's current `noteText` would print if someone pointed it at the new fields without porting the rule.

What the note's Carried list has:
- the sample pack's 18 `section to confirm` (I counted 18);
- the `index.astro` wording (lines 134-136).

What it does not have:
- the `with_note_fields` return-value change;
- `guidance-notes.mjs`, which is the live `/demo` screen-3 notes, still printing `section to confirm · eSTAR: to confirm` with no `[unverified]`;
- the vendored `src/data/guidance_map_v1.csv`, which S10-S3-1 ties to the engine file at a recorded commit;
- the two tests that go red.

Site CI stays green while it pins `effc5c7` (`ENGINE_REF`). The site's local `npm run test:unit` on this machine reads the sibling HEAD. So the first local site run after E15 merges to engine main fails two tests that no handoff mentions.

Repro: `cd proofpack-site && PROOFPACK_ENGINE_DIR=<e5319e0 tree> PROOFPACK_ENGINE_NO_SIBLING=1 TEMP=<scratch> TMP=<scratch> node --test --test-reporter=spec --test-name-pattern="S10-S3-2" tests/day10-demo-screen3.test.mjs` gives `pass 0, fail 2`. The same command on an `effc5c7` tree gives `pass 2, fail 0`.

Repair: a record fix. List the contract change, the port in `guidance-notes.mjs` (lines 13-14, 70-71, 95), the re-vendor of `guidance_map_v1.csv`, and S10-S3-2/2b under changes for lane S. Keep the sample pack and `index.astro` items. No engine code needs to change.

## Non-blocking

**N1. One new test passes at `effc5c7`, and its docstring states a guarantee it does not inspect (hard-rule sentence).**
- `test_the_draft_row_keeps_its_status_and_the_sections_do_not_carry_it` passes at `effc5c7`. It is the "1 passed" in the note's `14 failed, 1 passed`, but the note does not name it or say that it pins no E15 change. It reads three CSV columns and never calls `label_for`.
- Its docstring says filling ``section`` "cannot drop" the draft words.
- My counter-example (mutant K): `with_note_fields` replaces the label with the bare document name and sets `draft` False whenever the section is filled. This test **still passes**. 7 other tests fail (7 failed, 41 passed over `test_e15_sections`, `test_render_furniture`, `test_e14_margin_notes`, `test_e11_aidsf_header`):
  - test (b), `test_t1_of_the_synthetic_cohort_names_every_section_and_marks_every_gap`;
  - `test_each_furniture_element_is_on_t1_and_t8`;
  - `test_t1_section_7_prints_each_distinct_line_once_and_keeps_every_anchor`;
  - four `test_e11_aidsf_header` cases.
- So the property holds, but not because of this test. Suggested wording: "inspects that each FDA_AIDSF_ row's status is `draft - not for implementation`, its version_date `2025-01-07`, and its section free of the word draft; the draft label on the page is test (b)'s and test_e11_aidsf_header's."

**N2. The note's reasons for the pre-build failures are incomplete.**
- Copy-only run (14 failed): four tests fail on `FileNotFoundError: ...design\guidance_sections.yaml`, a missing data file, not an assertion:
  - `test_every_filled_section_has_a_source_row_with_url_date_and_version`;
  - `test_every_quoted_heading_appears_in_the_section_in_order`;
  - `test_no_regulatory_row_is_left_empty_without_a_reason`;
  - `test_no_fda_row_claims_an_estar_section_while_none_was_read`.
- Hybrid run (11 failed). The note says each failed "because `to confirm` was on the page or because `ESTAR_GAP` was absent". Measured, two failed for other reasons:
  - `test_a_transcribed_row_prints_its_section_and_the_estar_gap` failed on `assert 'VIII. Data Management' == 'section VIII...ta Management'`;
  - `test_an_empty_section_prints_the_unverified_gap_not_to_confirm` failed on `AttributeError: ... no attribute 'SECTION_GAP'`.
- The five golden tests fail in the hybrid only on `AttributeError ... 'ESTAR_GAP'`: with the new goldens copied in, nothing else in them is old.

**N3. The fixtures diff list is incomplete.** The note says the key-by-key diff of `fixtures_report.json` differs "only in the tree path, the `generated` time and the HEAD sha quoted in the F13 reason". Measured, there are five differing keys:
- `/doctor[12]/info` (the path);
- `/generated`;
- `/rows[36]/reason` (the sha);
- `/git_sha` (top level);
- `/duration_s` (2.104 vs 2.065).

The rows and counts are identical: 46 rows, matched 35, not built 4, suite only 7. `run.json` of a licensed `--offline` 5,000-row run differs only in `manifest.started`, `run_id`, `duration_s` and `mapping_sha256`. The `mapping_sha256` difference is the mapping file's `timestamp` line, and nothing else in that file differs.

**N4. The note's re-run block sets no `PROOFPACK_HOME`.** Anyone who re-runs the suite from it uses the real licence in `%LOCALAPPDATA%\proofpack`.

**N5. No behaviour test now exercises a merged draft line in DOCX.**
- The DOCX merge assertions on `[FDA_AIDSF_PERF_VALIDATION, FDA_AIDSF_LABELING_METRICS]` were removed. The planted map copy exercises only the final (`FDA_STAT2007_*`) branch.
- Mutant J removes the `also` loop from all 15 draft branches of `T1.docx` (15 replaced). Under `-m "ap4 or day14 or day15"` with `PROOFPACK_REQUIRE_DOCX=1` it gives `1 failed, 296 passed`. The one failure is `test_the_regenerated_template_equals_the_committed_one_part_by_part[T1]`, the template-equals-script check, not a behaviour test.
- On the shipped map no draft line merges: the only `data-also` in any golden is T2's PCCP line. So this is not reachable today.

**N6. The EU, GB and MDCG sections never reach a page.**
- `grep` of `src` finds no template or code citing `EU_MDR_ART86_1`, `GB_PMS_*` or `MDCG_*`.
- The MDR was read as adopted (OJ L 117/72). I reproduced EUR-Lex's `202` with a 0-byte body on the consolidated CELEX URL.

## What I could not break

- **Sources.** I downloaded all seven documents myself (curl, browser UA). The bytes and SHA-256 match the YAML for every one: AI-DSF 1,590,866 `62e83e0f...520bc`, STAT2007 344,921, PCCP 666,195, SI 139,552, MDR 1,517,689, MDCG 2022-21 1,426,146, MDCG 2020-8 697,086.
- **Headings and quotes.** Every quoted heading and topic quote is in the pdftotext or pypdf text of the page it names: 80 of 81.
  - The miss is `2. Avoid elimination of equivocal results`. The PDF prints `equivocal5 results` on page 18, which is the footnote the YAML records.
  - The TOCs confirm the nesting: AI-DSF VIII/X.A/XI/XIII/App. C/App. E; PCCP V.C, VII.B(1)-(4), VII.C, VIII; MDCG 2022-21 ANNEX I.
  - SI 2024/1368 has the crosshead `New Part 4A (post-market surveillance requirements)`, 44ZL `Post-market surveillance report`, 44ZM `Periodic safety update report`, and 44ZM(3) `The PSUR must include`.
  - The eSTAR page returned 200 with `Content current as of: 09/21/2026`.
- **Mutants.** Seven mutants at the tip, each killed by `tests/test_e15_sections.py`:
  - A: the gap without `[unverified]`;
  - B: `base.html` drops `{{ ref.estar }}`;
  - C: the internal row back to `n/a`;
  - F: section without the `section ` prefix;
  - G: an empty section hidden as `""`;
  - H: estar ignores the map;
  - I: `FDA_STAT2007_CI` estar set to `n/a`.
- **DOCX templates.** For T1, T7 and T8 only `word/document.xml` differs. The base XML with `· section {{` and `· eSTAR: {{` replaced equals the tip XML (30, 12 and 12 replacements).
- **Rendered DOCX** (synthetic document):

  | | eSTAR gap | `to confirm` | `section n/a · eSTAR: n/a` |
  |---|---|---|---|
  | T1 | 20 | 0 | 1 |
  | T7 | 4 | 0 | 2 |
  | T8 | 3 | 0 | 3 |

  No `section section`, `eSTAR: eSTAR` or `eSTAR: [unverified]` appears in the DOCX output, the licensed HTML packs or the goldens.
- **The note's T1 table.** `measure.py` gives `notes 19 | 'to confirm' 32 | [unverified] 0` at `effc5c7` and `21 | 0 | 20` at `e5319e0`. Licensed run, base to tip:
  - T1: 19/32/0 to 21/0/20;
  - T7: 6/7/0 to 6/0/4;
  - T8: 6/6/0 to 6/0/3.
- **Goldens.** `git diff -U0 effc5c7 e5319e0 -- tests/fixtures/golden` has no changed line outside a `margin-note` aside (72 changed aside lines). Regulatory notes per golden, each carrying the gap:

  | T1 | T2 | T7 | T8 | T12 |
  |---|---|---|---|---|
  | 20 | 9 | 4 | 3 | 1 |

  No golden test is vacuous.
- **Nothing weakened.**
  - `--name-status` shows two added files and no deletion.
  - No `skip`, `xfail` or `only` was added, and no marker was removed.
  - The removed asserts are the old note shape and the day-1 blank-section rule. That rule is now "a filled section has a provenance row", as the note's Needs-from-Josh 1 says.
- **Fixtures and doctor.** `fixtures --offline` and `doctor --offline` exit 0 in both shells, with the same counts at base and tip.
- **CI.**
  - Run 37783680895: head `e5319e0`, branch `ci/e5319e0-1791465672-5710`, `success`. Jobs: ap4 docx-extra, unshare -rn, pip-audit, pytest + ruff, Docker smoke, scipy-uninstalled import, wheel. All 7 succeeded.
  - Run 37782252562: head `26e75ff`, `failure`.
  - `gh run list --commit e5319e0...` lists only 37783680895.
  - `git ls-remote origin 'refs/heads/ci/*'` is empty.

## What I could not check

- **The CI gate.** I did not re-run `ci_gate.sh` myself, so as not to push a ref from a lens. I read the note's run ids with `gh run view` instead.
- **The rest of the site suite against `e5319e0`.** I ran only S10-S3-2/2b. Other engine-touching site tests write into the engine directory or licence paths, and the site is read-only for me today.
- **The MDR as amended.** Whether Article 86(1) has been amended since adoption: EUR-Lex refused automated reads (HTTP 202, empty body).
- **Linux, Python 3.12** outside CI.
