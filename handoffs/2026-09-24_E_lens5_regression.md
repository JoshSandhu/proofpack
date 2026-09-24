# Lens 5 (regression and record) - build day 9, lane E, repair 4 at `e62d329` against `f72a9af` - 2026-09-24

**Verdict: PASS. No blockers.** Lens 4's blocker FA-B1 does not reproduce at `e62d329`. I tested it on lens 4's own CLI input, on the repairer's CLI input and on an 11-criterion CLI input of my own with 7 `paired_difference_vs_prior` variants. On my input, F5 draws 0 of the 7 paired criteria and 3 of the 3 lines my probe expects; at `f72a9af` it drew 4 of the 7. The suite, marker, lint, sweep, sample-pack and repro figures in the repair-4 note equal mine in both shells. The one exception is a 1-byte `run.json` difference, which I did not isolate (N5). `tests/test_e9_repair4.py` gives `3 failed, 1 passed` at `f72a9af`, the same as the note. The failing three fail on the assertions the note quotes. The passing one is a disclosed pin (N3).

I raise six non-blocking items. N1 is a repaired sentence finding that still partly reproduces: lens-4 FA-N1 = RG-N1 is fixed in the note, but its replacement sentence points to a second file that does not carry the lines.

Worktrees, all under `scratchpad/lens-E9-r5-regression/`, all removed at the end:

| Worktree | Commit | Used for |
|---|---|---|
| `wt-e62` | `e62d329` | Git Bash suite, markers, lint, the re-run block in both shells, repros, sample pack in both shells, timing in both shells, my CLI probe |
| `wt-f72` | `f72a9af` | pre-fix run of `test_e9_repair4.py`; my CLI probe at the old commit |
| `wt-952` | `952bddc` | the `e62d329` copy of `test_e9_repair3.py` run alone (the docstring's `5 failed`) |
| `wt-1d1` | `1d19e62` | the note's baseline-slip repro (`handoffs/` removed) |
| `wtmut` | `e62d329` | my 12 mutants; the committed day-9 sweep in both shells |
| `wtgold` | `e62d329` | PowerShell suite, markers, lint; golden regeneration |

In each worktree, `PYTHONPATH=<wt>/src python -c "import proofpack;print(proofpack.__file__)"` printed that worktree's `src\proofpack\__init__.py` before I used a figure from it. Every CLI and sample-pack run either carried `--offline` or ran with `socket.socket` and `socket.create_connection` replaced by a function that raises. Every run printed `socket calls 0`. I committed nothing. The only file I wrote in the main tree is this note. Before I wrote it, `git status --short` in the main tree printed nothing, and HEAD was `e62d329`.

## Blockers

None.

## Non-blocking

**N1 (sentence_violation, minor; lens-4 FA-N1 = RG-N1 marked fixed, still partly reproduces). `tests/test_e9_repair3.py` lines 4-6.** The docstring says: "the first ``E`` line of each is quoted under "Pre-fix" in ``handoffs/2026-09-24_E_lens4_regression.md`` and in the repair-4 note."

- The first half is true. The lens-4 regression note has `**Pre-fix.**` once and `**\`5 failed\`**` once, and it quotes the five lines.
- The second half is false. The repair-4 note (`scratchpad/notes/E9_repair4.md`) quotes none of the five. `grep -c` prints `0` for each of `C3 (A, 2026-01-01)`, `For F versu`, `written to` and `state_what_they_inspect`. That note is also not in the repository, so a reader of the test file cannot follow the pointer.
- The note's "Sentences refused" says the "repair note" sentence was "Replaced by the pointer to the lens-4 regression note". The replacement kept a repair-note clause.
- The rest of that sentence is true. I ran the `e62d329` copy of the file alone at `952bddc` with `PYTHONPATH` forced: `5 failed in 2.41s`, each on an assertion.
- Repro: `grep -c "state_what_they_inspect" scratchpad/notes/E9_repair4.md` prints `0`.

**N2 (sentence_violation, minor; new in repair 4). `tests/test_e9_repair4.py` module docstring.**

- "Each test feeds the input a lens fed". Lens 4 fed `Cpd` with `C3` (op2) and `FAIRNESS`, and in `probe/p3.py` `Cpd` 0.6 with `Cauc_pd`. The test's fixture adds `Cpt`, `Cauc` and `Cref`, which no lens fed. The two sentence tests feed no input. The docstring's bullet then lists the literal input, which is accurate.
- "The first ``E`` line of each test, run in an ``f72a9af`` worktree ..., is quoted in the message of the commit that added this file". One of the four tests passes at `f72a9af` and has no `E` line. The `1d19e62` message says so ("3 failed, 1 passed (the T1-11 pin describes behaviour f72a9af already had)").
- Repro: copy `tests/test_e9_repair4.py` into a `f72a9af` worktree and run it: `3 failed, 1 passed in 2.13s`.

**N3 - one new test passes before the fix (disclosed pin).** `test_the_sex_t1_11_rows_still_print_the_paired_rows_status_and_not_cref` passes at `f72a9af`, so it does not pin repair 4's change. The note and the commit message both say so. It is not idle: it is the only test that kills my mutant `t1_11_drops_paired_rows`, which adds `and row.get("reason_code") != "requires_compare"` to the T1-11 filter (the wrong fix applied to the table as well: `1 failed, 157 passed`). It also kills `t1_11_prints_reference_level` (`2 failed`). Record only.

**N4 - note commands that fail in a shell as written.**

- `python <scratch>/E9handoff/b1_repro.py <repo>`, with stdout piped and no `PYTHONIOENCODING`:
  - Git Bash: `UnicodeEncodeError: 'charmap' codec can't encode character '\u2192'`.
  - PowerShell: the same, `exit=1`.
  - With `PYTHONIOENCODING=utf-8`, both shells print the note's three lines.
- The re-run block's PowerShell script (`rerun/rerun.ps1`), which the note did not run ("not run"):
  - The `k1` line prints nothing and the script exits 1. `LENS_WT=(Get-Location).Path` holds backslashes. `lens-E8-r7-fresh-attack/prev/prev3/harness.py` line 7 compares it with a forward-slash `proofpack.__file__` and raises `AssertionError`.
  - With `$env:LENS_WT` set to the forward-slash path, the output is identical to Git Bash's: `engine claims rejected: 0` and the same 15 `free_text accepted` words.
  - The `nolicence` and `licence show` lines print `exit=-1` because `Select-Object -First` stops the process. This is known and recorded in the E9 handoff's table. Run without it, each gives `exit=4`.

**N5 - `run.json` of the no-licence e2e run: 253,937 bytes in my Git Bash run, 253,938 in my PowerShell run and in the note.** The rest of the `runjson.py` line is identical (`20 keys 70 claims 0 rejections 3 refs [0, 1, 2, 2, 2, 3, 4, 5, None] CRLF 0 BOM False`). I did not isolate the byte. The sample pack, built once per shell, gives 236,843 bytes in both shells. Those two `run.json` files differ only at `/manifest/duration_s`, `/manifest/run_id` and `/manifest/started`.

**N6 - the golden fixtures pin `manifest.numpy` as well as the three volatile values.** The brief asks for "masking touches only run_id, started and duration_s". The golden tests set run_id, started and duration_s through the assembler, and also set `manifest.numpy` to `x.y.z` (`tests/test_render_t1.py` line 54, and the same in T7). This is documented in the test docstrings and unchanged by repair 4. The sample-pack masking I ran touches only the three values (below). Record only.

**Carried and re-measured.** `f5_dedupe_by_id_only` (lens-4 FA-N4) still survives: `158 passed, 1259 deselected` against `-m "day9 and not slow"`. The note carries it.

## Measured against the note

**Suite** (`PROOFPACK_TR39_FULL=C:/Users/joshs/GPS/ProofPack/workflows/data/confusables-18.0.0.txt`):

| Command | Git Bash (`wt-e62`) | PowerShell 5.1 (`wtgold`) | Note |
|---|---|---|---|
| `python -m pytest -q -p no:cacheprovider` | `1415 passed, 1 skipped, 1 xfailed in 137.52s` | `1415 passed, 1 skipped, 1 xfailed in 130.92s` | `1415 passed, 1 skipped, 1 xfailed` (both) |
| `-m day9` / `day8` / `day7` / `day6` | `159` / `468` / `139` / `285 passed` | the same | the same |
| `-m day5` / `ap2` | `54` / `88 passed` | the same | - |
| `--collect-only -m` day9 / day8 / day7 / day6 / day5 / ap2 | `159` / `468` / `139` / `285` / `54` / `88` of `1417` | - | - |
| `ruff check .` / `ruff format --check .` | `All checks passed!` / `198 files already formatted` | the same | the same |

- The skip is `test_doctor_cli.py:57` ("write access cannot be revoked for this user"). The xfail is `test_f13_matches_proc_on_the_asah_dataset` (the day-12 R capture).
- `day5` 54, `day6` 285, `day7` 139, `day8` 468 and `ap2` 88 equal the counts collected at `eda8a35`.
- `day9` 159 = lens 4's 155 + the 4 tests of `test_e9_repair4.py`. 1415 = 1411 + 4.
- `day9` is declared in `pyproject.toml` (line 86). The CI step "pytest every declared day marker" reads the marker list from `pyproject.toml` (`.github/workflows/ci.yml` lines 35-46). `git diff --stat f72a9af e62d329 -- .github pyproject.toml` prints nothing.

**Pre-fix.** I copied `tests/test_e9_repair4.py` from `e62d329` alone into `wt-f72` and got `3 failed, 1 passed in 2.13s`. The first `E` line of each failure equals the one quoted in the note and in `1d19e62`'s message:

- `E       AssertionError: assert {'F5-sex-sens...01-01): 0.5']} == {'F5-sex-sens...01-01): 0.5']}`. The differing items: `F5-sex-sensitivity` carries `'customer criterion Cpd (A, 2026-01-01): \u22120.05'` ahead of `Cpt` and `Cref`, and `F5-sex-auroc` carries `'customer criterion Cauc_pd (A, 2026-01-01): 0.55'` ahead of `Cauc`.
- `E       assert 'the first \`... repair note' not in '"""Build da...d(" in src\n'`.
- `E       assert '(an \`\`auroc\`\` criterion' not in '"""T1, the ...urn target\n'`.

None failed on an import or attribute. The passing test is the pin (N3).

**The baseline slip.** In a `1d19e62` worktree with `handoffs/` deleted, `tests/test_e9_repair4.py` gives `1 failed, 3 passed in 1.81s`, and the failure is `E       FileNotFoundError: [Errno 2] No such file or directory: ...`. This is the note's figure. `scripts/mutation_sweep.py` line 60 sets `COPIED = ("src", "tests", "schema", "fixtures", "design", "scripts", "pyproject.toml", "README.md")`, with no `handoffs`. `git diff 1d19e62 e62d329` is the two removed lines.

**Nothing weakened.**

- `git diff --name-status f72a9af e62d329 -- tests/` gives `M tests/test_e9_repair3.py` and `A tests/test_e9_repair4.py`. There is no `D`.
- In `tests/`, `scripts/` and `src/`, the only skip/xfail/`.only`/todo/marker line added or removed is `+pytestmark = pytest.mark.day9`.
- The edit to `test_e9_repair3.py` is the module docstring plus one rename, with the body unchanged.

**No statistics.**

- `git diff --name-status f72a9af e62d329 -- src/proofpack/stats/ src/proofpack/gates.py` prints nothing.
- `git diff --stat f72a9af e62d329` prints nothing over each of these: `stats`, `gates.py`, `criteria.py`, `narrate`, `egress`, `io`, `schema`, `render/format.py`, `run.py`, `cli.py`, `pyproject.toml`, `uv.lock`, `design`, `.github` and `src/proofpack/templates`.
- `git diff --stat eda8a35 e62d329 -- src/proofpack/stats/ src/proofpack/gates.py src/proofpack/criteria.py design/tokens.json` prints nothing.

**S4 list (DEC-43), against the diff.** The diff over `cli.py`, `run.py`, `schema/`, `render/format.py`, the templates and `design/` is empty. The note's "No CLI flag, default, output path or JSON key changed" is what the diff shows. The only page change is in `render/figures.py::_criterion_lines`, which is what the note's T1-only bullet names. Sample-pack sizes equal lens 4's `f72a9af` figures (below). The note's list of repair-3 output changes matches lens-4 N6 item for item.

**Sweep.**

- `python scripts/mutation_sweep.py --list` prints 292 lines in both shells: ap2 16, day5 34, day6 112, day7 25, day8 87, day9 18.
- `--marker day9`, Git Bash: `18 planted, 18 killed, 0 survived; 179 s`, exit 0. `f5_criterion_line_for_paired_difference` is killed with `1 failed, 23 passed`.
- `--marker day9`, PowerShell: `18 planted, 18 killed, 0 survived; 174 s`, exit 0. The note did not run the PowerShell sweep.

**The re-run block** (`rerun.sh`, copied with the tr39 path made absolute because it was run from a worktree; tag `r5lensbash`, Git Bash). Each line equals the note's:

- tr39 `vendored subset matches`, exit 0;
- doctor exit 0, 17 `[ok` lines;
- no-licence run exit 4 (N5 for the byte count);
- nomap `exit=3 dir=no`;
- `licence show` exit 4;
- `html_run` `T8.html bytes 43961`;
- repros5 B1-B4 and repros6 B1-B3, then the `HALT H08 ... U+0000` line and the known `FileNotFoundError`;
- p3_fair, p2_star and p7_site S02 halts, with `sex` H07;
- alias `exit 3`, `pack exists: False`;
- `socket calls 0`;
- `imports ok; loaded: []`;
- verdict grep `5 passed, 1412 deselected`;
- E6 schema `1 passed`;
- k1 `engine claims rejected: 0` and the same 15 free_text words.

The PowerShell copy (`w_r5lensps`) gives the same results except for the N4 lines.

**Repros, both shells.**

- `b1_repro.py`, with `PYTHONIOENCODING=utf-8` (N4) in both shells, prints `F5 C3 line count: 0`, `T1-11 plain 'C3 (row 1)': 1 ['C3 (row 1) → criterion met']` and `F5 caption op: op1`.
- `twoop_cli.py` prints `rc 0 socket calls 0`, and both `FAIRNESS_GAP` sentences end `AUROC gap (no operating point) +0.079 [−0.002, +0.160].`
- `E9r4/cli_b1.py` prints `rc 0 socket calls 0`, all three sex F5 plots `[] 0`, T1-11 op1 `Cpd 1 not assessable`, `Cauc_pd 2 not assessable`, `fairness:tpr_gap 4 criterion not met`, and op2 `Cauc_pd 2`, `C3 3 criterion met`, `fairness:tpr_gap 5`. This equals the repairer's `cli_b1.txt` main-tree block line for line.

**100,000-row timing** (`tests/test_render_timing.py -s`, `wt-e62`):

- Git Bash: `run --templates T1,T7,T8 4.82 s; T1+T7+T8 renders from run.json 0.31 s; T1 3693048 bytes`.
- PowerShell: `6.05 s; 0.32 s; T1 3693048 bytes`, measured while the PowerShell sweep was running.

T1's size equals lens 4's.

## What I could not break

- **Lens-4 FA-B1, three inputs, both commits, through the CLI** (`probe_pd.py`). The probe reads `run.json` (`criteria_results` and `declarations.criteria[declaration_index].type`) and `T1.html`, and imports no render code. For each F5 figure it recomputes each expected line's x from the figure's `data-map` (x0 + (v − xmin)/(xmax − xmin) × w) and compares ids and x. For each T1-11 row it compares the printed `(id, row, status)` with `criteria_results` by position.
  - Lens 4's input (`Cpd` −0.05 on op1 sex = F, `C3` op2, `FAIRNESS`, op2 at 0.3). At `e62d329`: `F5 lines drawn 0 F5 defects 0; T1-11 printed 4 T1-11 defects 0`. At `f72a9af`: `F5-sex-sensitivity drawn=[('Cpd', 178.5)] expected=[] DEFECT`.
  - My input: 11 criteria (17 rows) on op1, op2 and none. The seven paired ones are:
    - `Pstar`: sensitivity, sex = `*`;
    - `Pspec`: specificity, sex = F;
    - `Pop2`: op2;
    - `Pauc`: auroc, age = `*`;
    - `Psite`: site = `*`;
    - `Pub`: `ci_upper_bound`;
    - `Pov`: overall.

    The four controls are `Ppt` (`type: point`), `Pnone` (no type, sex = `*`), `Pauc2` (auroc, age = `*`) and `Pop2pt` (op2).
    - At `e62d329`: `F5 lines drawn 3 F5 defects 0; T1-11 printed 14 T1-11 defects 0`. The lines drawn are `Pauc2` at 309.6 and `Ppt` at 270.5 and `Pnone` at 247.5, each equal to my recomputed x.
    - At `f72a9af`: `F5 lines drawn 7 F5 defects 4`. The extra lines were `Pstar` 282.0, `Pspec` 259.0, `Psite` 293.5 and `Pauc` 330.3.
    - Every paired row is `not_assessable` / `requires_compare` at both commits. T1-11 prints each with its own status at both commits.
  - The repairer's input (`cli_b1.py`): as above.
- **The filter's reach.** `schema/criteria_schema.json` allows two values of `type`, `point` and `paired_difference_vs_prior` (`$defs/criterion/allOf[1]/properties/type`). `run.json` carries `declarations: decl.raw` (`run.py` line 496), so the renderer reads the declared type from the file it renders.
- **My mutants of repair 4's code and the lens targets** (`wtmut`, each against `-m "day9 and not slow"`, the file restored after each; `git status --short` in `wtmut` was empty at the end):

  | Mutant | Result |
  |---|---|
  | type read from the criteria row instead of the entry | `3 failed` (`test_a_paired_difference_criterion_draws_no_f5_line` + the two sweep-pattern tests) |
  | paired rows skipped on the AUROC plot only | `3 failed` (the same) |
  | paired rows skipped on threshold plots only | `3 failed` (the same) |
  | `entries[i + 1]` (off-by-one declaration index) | `3 failed` (the repair-4 F5 test, the repair-3 F5 test, `test_f5_draws_the_criterion_line_only_where_a_lower_bound_criterion_names_it`) |
  | `entry.get("type") in (None, "point")` | 2 failed, sweep-pattern tests only. Equivalent on schema-valid input: the enum has two values. |
  | `f5_dedupe_by_id_only` (lens-4 FA-N4) | **survived**, `158 passed` (carried) |
  | T1-11 also drops `requires_compare` rows | `1 failed` (the pin, N3) |
  | T1-11 prints the reference level | `2 failed` (the pin, the T1 golden) |
  | last `{{ page_footer() }}` removed from `templates/T1.html` | `5 failed`: `test_the_footer_helper_counts_per_page_and_refuses_the_lens_mutant`, `test_each_furniture_element_is_on_t1_and_t8`, the T1 golden, `test_the_footer_is_on_every_page_and_once_in_print`, `test_every_page_of_every_document_is_marked_synthetic` |
  | `FDA_AIDSF_SUBGROUP_PERF` status `draft - not for implementation` changed to `final` in `guidance_map_v1.csv` | `4 failed`: `test_every_caption_repeats_n_the_interval_method_and_the_anchor`, the T1 golden, `test_every_fda_draft_anchor_is_labelled_in_every_margin_note`, the T7 golden |
  | `PlotMap.x` + 1 unit | `6 failed` (the F2, F3, F4 and F5 inversion tests, the F5 criterion-line test, the T1 golden) |
  | `PlotMap.y` + 1 unit | `6 failed` (the F2, F3 and F4 inversion tests, the T1 golden, the two sweep-pattern tests) |

- **Goldens.** Running the three golden tests with `PROOFPACK_REGEN_GOLDEN=1` in `wtgold` gave `3 passed`, and `git diff --stat` printed nothing. The LF-normalised md5 of each regenerated file equals the committed one: T1 `cf3081f2`, T7 `2dfdb6c8`, T8 `ddfc6250`, the same as lens 4's. I restored the files.
- **Sample pack and masking** (`scripts/build_sample_pack.py --out`, sockets refused, one build per shell). Each build gave exit 0, `socket calls 0`, and run.json 236,843, T1 142,924, T7 47,666 and T8 35,178 bytes. These equal the note's figures and lens 4's `f72a9af` figures.
  - The two `run.json` files differ only at `/manifest/duration_s`, `/manifest/run_id` and `/manifest/started`.
  - After masking only those (the full `run_id`, its first 8 characters, `started`, and T8's one `Duration (s)` cell), T1, T7 and T8 are identical. Occurrences masked: T1 `run_id` 1, `rid8` 10, `started` 10; T7 0, 4, 4; T8 2, 4, 5 and the duration cell 1.
  - `SYNTHETIC - illustrative` / `NO LICENCE - not for submission` counts: T1 12 / 11, T7 5 / 5, T8 7 / 7.
  - T7 carries 18 `[unverified]` beside 18 `pending verification`.
- **Library against D4 section 8.** Parsing the section-8 table gives 55 ids. `templates.LIBRARY` has 56; missing: none; extra: `SUBGROUP_ESTIMATE`, the recorded engine addition. `all_skeletons()` returns 83. `tests/test_claims.py` lines 317 and 325 compare the schema enum with `list(templates.LIBRARY)` and with the id set of `all_skeletons()`.
- **Forbidden words and anchors.** I scanned T1, T7 and T8 of four packs: my two probe packs at `e62d329`, the sample pack and the two-op pack. The scan covers text outside `.status`, `.disclaimer` and `.customer-text`, against `FORBIDDEN_ON_PAGE` ∪ `VERDICT_WORDS` ∪ `CERTIFICATION_WORDS` ∪ the brief's words (50). The only hit is `endorsed`, once per page (carried). Every `<a href="#FDA_AIDSF_*">` is followed within its element by "draft guidance (January 2025), not for implementation": T1 27/27, T7 3/3, T8 6/6 on the probe and sample packs.

## What I could not check

- The day-8 sweep (about 25 minutes per shell). `git diff --stat f72a9af e62d329` over `narrate`, `egress`, `run.py` and `cli.py` is 0 lines. Carried row 106 stays open.
- A wheel in a fresh venv. Repair 4 changes no packaged non-Python resource (`design/` and `src/proofpack/templates` diff empty).
- Browser rendering.
- The source of N5's one byte.
- Lens 1-3's clustered-page phrase greps. I did not build a clustered document. Repair 4's code change is confined to `_criterion_lines`, and the full suite, which carries those pins, passes in both shells.

## Cut and carried, against what I measured

The note's carried list covers every lens-4 item: FA-N4, FA-N5 = RG-N4, RG-N5, RG-N6, RG-N7 / row 100, row 110, FA-N6, the `f72a9af` commit-message parenthetical, DEC-55 gate_h05 and row 49. I found nothing open that the note omits, apart from N1, N2, N4 and N5 above, which are new. RG-N7 is now wider, as the note says: a `paired_difference_vs_prior` criterion is drawn on no F5 plot, and no caption says so.

## Sentences I refused to write

- "F5 never draws a paired-difference criterion." Written instead: on 7 named paired variants and lens 4's input, F5 at `e62d329` drew none of them.
- "Every repair-4 test fails before the fix." One passes at `f72a9af` (N3).
- "The note's commands all run in both shells." Two do not as written (N4).
- "The re-run block matches byte for byte." One `run.json` byte count differs (N5).
- "Repair 4 closed every lens-4 sentence finding." N1 closes only the pointer to the lens-4 note.
