**Verdict: FAIL. 2 blockers, both in repair 2's DOCX meta-test (`tests/test_e14_repair2.py`); no behaviour defect found in what a buyer receives. B1: the meta-test's name, docstring and the `ae23aa5` commit message say it takes the E14 tests "module level and in Test classes" whose code names docx "directly or through a same-module function"; three constructed DOCX tests that do name docx (a nested `Test*` class, a module-level `def` under `if True:`, a lambda helper) are collected by pytest, are not selected by `-m ap4`, skip silently under `PROOFPACK_REQUIRE_DOCX=1` with the extra hidden, and the meta-test stays `1 passed, 11 deselected`. That is lens 2's B1 again, inside the repair that closed it. B2: repair 2 deleted e67c5fa's `"importorskip" not in inspect.getsource(fn)` check and did not replace it; with `pytest.importorskip("docxtpl")` re-added to both E14 DOCX tests, e67c5fa's E14 files give `1 failed, 72 passed` and ae23aa5's give `84 passed`, and under `-m ap4` with the extra hidden and `PROOFPACK_REQUIRE_DOCX=1` both tests print `SKIPPED ... could not import 'docxtpl'`, the RG-N3 line. A guard that killed this mutant at e67c5fa no longer does, which reopens the lens-1 FA-B1 / RG-N3 blocker class. Behaviour at `ae23aa5` held under my own probes: cover row (licensed T1 3 entries, base 19; T8 2, base 7; compare T2 2, base 14; compare T8 2, base 10; a several-document page 7 on T1, T8 and T2), margin notes (T1 19 lines, base 21, 0 repeats, 0 wrong merges; DOCX 19 rows carrying 21 ids), flags (153 parses per tree, 0 refused on 3.14.6 and 3.12.10; base 42 refused), 0 socket attempts with `--offline` last on 8 commands, prompt (33 answers, only `a`/`accept` in any case and spacing accept), fixtures (46 rows, 35 matched at base and tip). Suite `2419 passed, 5 skipped`; ruff clean. My gate run 37652193768: `GREEN ae23aa5`, 7 jobs `success`.**

# E14 lens 3 (cold fresh-attack) on engine ae23aa5 - Wednesday 7 October 2026

Cold lens on `e14-lw01` at `ae23aa5` (repair 2, one commit on `e67c5fa`; 7 commits on `3ee5601`). Inputs read:
- `git diff e67c5fa ae23aa5`; `git diff 3ee5601 ae23aa5` for the behaviour;
- the repair note `scratchpad/notes/E14_repair2.md`;
- the four earlier lens notes (lens 1 and lens 2, fresh-attack and regression);
- `handoffs-orchestrator/2026-10-07_LW01_log.md`, `2026-10-07_user_review_notes.md`.

Method. Four detached worktrees under `scratchpad/lens-E14-r3-fresh-attack/`: `tip` and `mut` (`ae23aa5`), `prev` (`e67c5fa`), `base` (`3ee5601`); a fifth, `a18` (`a1840fc`), for the corrections file's figures. `PYTHONPATH` was set to each tree's `src` (Windows form) and checked with `python -c "import proofpack;print(proofpack.__file__)"`, which printed `...\lens-E14-r3-fresh-attack\<tree>\src\proofpack\__init__.py` each time. My scripts (`probe_pack.py`, `probe_multi.py`, `probe_flags.py`, `probe_socket.py`, `probe_prompt.py`, `mut_r2.py`) read `design/guidance_map_v1.csv`'s columns and python-docx directly; they do not call `label_for`, `cover_documents`, `distinct_notes`, `e14_pages` or `cell_texts`. Repository test helpers were used only to build inputs and licences (`make_cohort`, `make_criteria`, `write_licence`, `ephemeral_registry`, `confirmed_mapping`, `synthetic_document`, `compare_document`). Every mutant was reverted with `git checkout -- .`; `git status --short` was empty afterwards. No commits. The only file I created outside my worktrees is this note. Platform: Windows 11 Home 10.0.26200, Python 3.14.6 (3.12.10 for the argparse walk), Git Bash.

## Blockers

### B1. False sentences (test name, docstring, commit message): the repair-2 meta-test does not take every E14 test "at module level and in Test classes" whose code names docx

The sentences:
- test name: `test_fa_b1_other_e14_modules_tests_naming_docx_or_importorskip_carry_ap4_and_needs_extra`;
- module docstring: "takes the ``test*`` functions of the ``test_e14_*`` modules (this file excluded), module level and in ``Test*`` classes, whose code ... holds a name, attribute, import or string containing ``docx`` in any case, or the name ``importorskip``, directly or through a module-level function of the same module that the test names or takes as an argument";
- commit `ae23aa5`: "the DOCX meta-test takes the E14 tests (its own file excluded) whose code names docx or importorskip" and "takes the test functions of the other test_e14_* modules (module level and in Test classes) ... directly or through a same-module function they name".

What the scanner reads (`docx_tests_in_source`): `FunctionDef`s directly in `tree.body`, `FunctionDef`s directly in a top-level `ClassDef` named `Test*`, and helpers that are `FunctionDef`s directly in `tree.body`.

Counter-examples, each appended alone to `tests/test_e14_cover_row.py` in `mut`, none carrying `ap4`:

| id | the test | meta-test (`tests/test_e14_repair2.py -k fa_b1`) | pytest collects it | `-m ap4 --collect-only tests/test_e14_cover_row.py` | extra hidden + `PROOFPACK_REQUIRE_DOCX=1` |
|---|---|---|---|---|---|
| K1 | `class TestLens3Outer:` / `class TestInner:` / `def test_lens3_nested_docx(self, tmp_path): d = pytest.importorskip("docx")` | `1 passed, 11 deselected` | `TestLens3Outer::TestInner::test_lens3_nested_docx` | `1/6 tests collected (5 deselected)` | `SKIPPED [1] tests\test_e14_cover_row.py:115: could not import 'docx': import of docx halted; None in sys.modules` |
| K5 | `if True:` / `def test_lens3_under_if(): d = pytest.importorskip("docx")` (a module-level function) | `1 passed, 11 deselected` | `test_lens3_under_if` | `1/6` | the same `SKIPPED` line |
| K2 | `_lens3_open = lambda: __import__("importlib").import_module("docx")` and `def test_lens3_lambda_helper(): assert _lens3_open().Document is not None` (a module-level function of the same module that the test names) | `1 passed, 11 deselected` | `test_lens3_lambda_helper` | `1/6` | not run |

K1 and K5 name `docx` directly and are a test in a `Test*` class and a module-level test; K2 reaches `docx` through a same-module function it names. The meta-test leaves all three out of its set and passes, and each is a DOCX test the docx-extra job would never select and that skips silently when the extra is missing. That is the FA-B1/RG-N3 class the test was written for, and lens 2's B1 shape (a name and docstring that claim more than the check reads).

Repair, either: (a) say what it reads ("functions defined directly in the module body or directly in a top-level `Test*` class; helpers defined with `def` directly in the module body") in the name, docstring and a correction line for the commit message; or (b) take pytest's own collection (`pytest --collect-only -q tests/test_e14_*.py` items, then `inspect.getsource` per item) so nested classes and conditional defs are in scope. K1 and K5 are the counter-examples to run first.

Repro: `cat k1_nested.txt >> tests/test_e14_cover_row.py` at `ae23aa5`, then `python -m pytest -q -p no:cacheprovider tests/test_e14_repair2.py -k fa_b1` (`1 passed`).

### B2. Repair 2 dropped e67c5fa's importorskip guard: a mutant killed at e67c5fa survives at ae23aa5 and reopens the RG-N3 blocker class

e67c5fa's deleted meta-test asserted `"importorskip" not in inspect.getsource(fn)` for each E14 DOCX test (lens 2 regression's T3 mutant, "importorskip re-added", was killed by it). Repair 2's replacement asserts the set, the `ap4` mark and the `skipif` identity, and nothing about the body. Neither the note nor the docstring records that the check was removed.

Mutant: `pytest.importorskip("docxtpl")` inserted as the first body line of both `test_docx_cover_row_text_equals_the_html_cover_labels_in_order` and `test_docx_t1_prints_each_repeated_line_once_naming_every_id`.
- `prev` (`e67c5fa`), `python -m pytest -q tests/test_e14_*.py`: `1 failed, 72 passed` (killed).
- `mut` (`ae23aa5`), the same: `84 passed in 5.17s` (survives).
- Both trees, with docxtpl, docx and matplotlib hidden by a `-p` plugin (`sys.modules[name] = None`), `PROOFPACK_REQUIRE_DOCX=1 python -m pytest -q -p hidedocx -m ap4 tests/test_e14_cover_row.py tests/test_e14_margin_notes.py -rs`: `2 skipped, 9 deselected`, with `SKIPPED [1] tests\test_e14_cover_row.py:99: could not import 'docxtpl': import of docxtpl halted; None in sys.modules` and the same for `test_e14_margin_notes.py:99`.

So under exactly the job conditions `SKIP_REASON` says refuse the skip ("runs -m ap4 with PROOFPACK_REQUIRE_DOCX=1, where this skip is refused"), both E14 DOCX tests skip and nothing in the suite fails. This is the CI line lens 1 recorded at `a1840fc` (`SKIPPED [1] tests/test_e14_cover_row.py:90: could not import 'docxtpl'`). Graded a blocker under "a surviving mutant that reopens a blocker class" and "a repair that weakened a guard".

Repair: restore the body check in the new meta-test (no `importorskip` in the code of the tests it finds), and add a regression case that fails on this mutant.

Repro: in an `ae23aa5` tree, add `    pytest.importorskip("docxtpl")` as the first line of both bodies; `python -m pytest -q -p no:cacheprovider tests/test_e14_*.py` gives `84 passed`.

## Non-blocking (record and carry)

- **N1. 7 of 10 scanner mutants survive the committed tests of `test_e14_repair2.py`.** `mut_r2.py`, each run as `python -m pytest -q tests/test_e14_repair2.py`:
  - survive (`12 passed`): `no_importorskip_arm` (drop `or t == "importorskip"`), `no_lower` (match `docx` case-sensitively), `no_identity` (drop `assert skips[0] is needs_extra.mark`), `no_decorators` (stop reading decorators), `no_attribute` (stop reading attribute names), `no_alias` (stop reading import aliases), `no_module_marks` (ignore module-level `pytestmark`);
  - killed: `no_helpers` (`2 failed`), `no_docstring_skip` (`1 failed`), `no_classes` (`1 failed`).
  Each surviving branch is a part the docstring describes. Every literal source in `FLAGGED` holds a lower-case `docx` string, so the `importorskip` arm and the case-folding are never needed by any case. The identity check is supported by the note's hand-run figure only (I reproduced that figure below), not by a committed case.
- **N2. Two DOCX tests outside what the docstring claims also escape** (no false sentence: the docstring does not claim these): K3, a test whose `--format` comes from a module constant `LENS3_FORMATS = ("html", "docx")` and which checks `T1.docx` exists through `f"T1.{ext}"`, runs a real DOCX render (`1 passed, 5 deselected` with the extra) and the meta-test gives `1 passed`; K4, a `Test*` class method reaching `docx` through `self._open()`, gives `1 passed`. A constant-driven `--format` test is a likely future shape.
- **N3. Carried from lens 2, not re-run by me:** FA-N1 (two drafts of one document in the same month merge on the cover, planted map); FA-N2 (internal rule is status equality; `internal (ProofPack)` reaches the cover on a planted map); FA-N3 (sentence guards are literal substrings); FA-N4 (review note 17's first-line ask is not met; my probe confirms `y` still re-prompts); FA-N5 (footer internal entries, the `t8_context` mutant without `guidance_map`, F19 `small_only_values`).

## Lens 2's blockers: closed?

- **Lens 2 FA-B1 (old meta-test name).** The old test is deleted. At `e67c5fa`, with lens 2's T3 text (copied verbatim from `lens-E14-r2-fresh-attack/mutate.py`) appended to `test_e14_cover_row.py`: old meta-test `1 passed, 6 deselected`; the tip's meta-test (both tip repair files copied in) `1 failed, 11 deselected`, `Extra items in the left set`. The same for lens 2 regression's T5 appended to `test_e14_global_flags.py` (`1 passed` / `1 failed`). With the cover test's `@needs_extra` replaced by `@pytest.mark.skipif(True, reason=SKIP_REASON)`: old `1 passed`, new `1 failed` on `assert Mark(name='skipif', args=(True,), ...) is Mark(name='skipif', args=(False,), ...)`. The docstring's three figures reproduce. **This closes lens 2's specific counter-examples, but B1 above is the same defect class with new counter-examples.**
- **Lens 2 FA-B2 (commit-message quote).** `handoffs/2026-10-07_E14_commit_message_corrections.md` exists. In `a18` (`a1840fc`) with e67c5fa's `tests/test_e14_repair1.py` copied in, `-k fa_b1`: `1 failed, 6 deselected`, first failure `Extra items in the left set: ('test_e14_cover_row', 'test_docx_cover_row_names_the_distinct_documents')`; with the expected name edited to a1840fc's: `1 failed, 6 deselected`, `assert 'ap4' in set()`. The file's sources check out: `git show 3ee5601:src/proofpack/cli.py` line 304 is the `[a]ccept / [q]uit? ` prompt and line 309 `say("  answer a or q")`; `LW01_log.md` line 7 reads "prompt takes `a` (`y` re-prompts)"; review-notes line 26 is note 17. Closed.
- **Lens 2 regression RG-N3 (docstring "every CI job skipped them").** Read from GitHub in this session: run 37631774505, head `a1840fca9425...`, 7 jobs `success`; job `pytest + ruff` (112827599516) logs `SKIPPED [1] tests/test_e14_cover_row.py:90: could not import 'docxtpl'` and the same for `test_e14_margin_notes.py:94`; job `pytest -m ap4 with the [docx] extra installed` (112827599666) logs `197 passed, 1 skipped, 2208 deselected` and no `test_e14` line. The new wording matches. Closed.

## What I could not break (what I tried, with figures)

- **Suite and lint (`tip`, Git Bash):** `2419 passed, 5 skipped in 342.37s`. The 5 skips: 3 × `test_day12_r_captures.py:156` (DEC-77), `test_doctor_cli.py:57`, `test_e8_repair4.py:405` (no sibling `workflows/data` beside a scratch tree). Total 2424 = the note's 2420 + 4. Markers: `day14` 84, `day13` 133, `day12` 199 + 3 skipped, `ap4` 200, `fixture` 178 (the note's figures; `fixture` not in the note, 178 per lens 2 at e67c5fa). `ruff check .`: All checks passed!; `ruff format --check .`: 362 files already formatted.
- **Cover (attack 1).** Licensed CLI runs in `tip` and `base`: `run --templates T1,T7,T8 --format json,html,docx --offline --quiet --json-log` on `make_cohort(n=5000)` with `egress.telemetry: true`; `compare` of F5 with `--templates T2,T7,T8 --format json,html,docx` and the same flags last, telemetry on. Sockets (`connect`, `connect_ex`, `create_connection`, `getaddrinfo`) patched to record and raise. Both exit 0, 0 attempts; the control without `--offline` made 1 `create_connection` attempt per command. My expectation: the guidance table's ids in order, internal rows (status `internal`) dropped, distinct (document, version_date, status) from the CSV.

  | page | table rows | documents | cover tip (base) | equals mine | `#` links, broken | margin lines tip (base) | repeats | bad merges | ids per block = base |
  |---|---|---|---|---|---|---|---|---|---|
  | run T1.html | 19 | 3 | 3 (19) | yes | 22, 0 | 19 (21) | 0 (2) | 0 | yes, 21 |
  | run T8.html | 7 | 2 | 2 (7) | yes | 8, 0 | 6 (6) | 0 | 0 | yes, 6 |
  | compare T2.html | 14 | 2 | 2 (14) | yes | 12, 0 | 10 (11) | 0 (1) | 0 | yes, 11 |
  | compare T8.html | 10 | 2 | 2 (10) | yes | 8, 0 | 6 (6) | 0 | 0 | yes, 6 |
  | run T1.docx | - | - | 3 (19), = HTML labels joined `"; "` | yes | - | 19 rows, 21 ids (21 rows) | 0 (2) | 0 | - |
  | run/compare T8.docx | - | - | 2 (7 / 10), = HTML | yes | - | 6 rows, 6 ids | 0 | 0 | - |

  Base covers carry `PP_SCOPE` and `PP_METHODS`; tip covers carry none. No duplicate element id on any page. The AI-DSF cover entry ends `draft guidance (January 2025), not for implementation` on every tip page.
  - **Several documents** (shipped map; the synthetic document's refs with `GB_PMS_44ZM3`, `GB_PMS_44ZL`, `EU_MDR_ART86_1`, `MDCG_2022_21`, `MDCG_2020_8`, `FDA_PCCP_IMPACT`, `FDA_PCCP_TRACEABILITY`, `PP_SCOPE`, `PP_METHODS`, `FDA_STAT2007_BY_SITE` put first in `guidance_refs`): T1 26 table rows, 7 documents, cover 7 (base 26), equals mine, 0 broken of 26 links, DOCX cover 7 = HTML; T8 15 rows, cover 7 (base 15), DOCX = HTML; T2 21 rows, cover 7 (base 21). Cover order follows the table, not the input order.
- **Margin notes (attack 2).** For every `data-also` id I compared the CSV row's document, version_date, status, section and estar_section with the linked id's, and its draft status with the aside's `draft` class: 0 mismatches on every page above. DOCX: every row's ids share one draft status, and `PP Margin Note Draft` appears exactly on draft rows (`bad_rows` 0). The three golden blocks that changed since `3ee5601` (T1 section 7, two pairs; T2 section 5, one pair) each merge lines whose visible text was identical.
- **Flags (attack 3).** `probe_flags.py` walks `_build_parser()` and finds 8 leaves (`doctor`, `map`, `run`, `compare`, `fixtures`, `licence show|verify|install`). Each of the three global flags goes in every slot between words and required arguments (not between an option and its value), plus a repeat, plus all 6 orders of the three after the last word: 153 parses per tree. `ae23aa5`: 0 refused, 0 wrong on 3.14.6 and 3.12.10. `3ee5601`: 42 refused, all `licence show|verify|install` (`unrecognized arguments`). `probe_socket.py`, `--offline` last, all three last, and all three reversed, on `doctor`, `map --yes`, `licence install|verify|show`, `fixtures`: rc 0 and 0 socket attempts in all 18 runs (plus `run`/`compare` above).
- **Map prompt (attack 4).** Each answer followed by `q`: `y Y yes n no e x`, empty, `"  "`, tab, `aa ok accept! a.`, Cyrillic `а`, full-width `ａ`, `ａccept`, `á`, `a`+U+200B, `1 true edit ye` each printed `  type a and press Enter to accept, or q to quit` once and halted H07 with `decided_by` `proposed`. Accepted: `a`, `A`, `a `, `ACCEPT`, `  Accept `. `q Q quit abort QUIT` halted without a re-prompt.
- **Fixtures (attack 5).** `python -m proofpack.cli fixtures --offline --out <dir>`: exit 0 at `3ee5601` and `ae23aa5`, `rows 46: matched 35, not matched 0, ... not built 4, suite only 7`. Every row matched at base matches at tip; the only differing field across rows is F13's `reason` (embeds the sha). Goldens since base: `git diff --numstat 3ee5601 ae23aa5 -- tests/fixtures` gives T1 `3 5`, T2 `2 3`, T8 `1 1`, all cover rows and merged margin notes (items 1-2). `e67c5fa..ae23aa5` touches no file under `src`, `tests/fixtures`, `.github`, `scripts` or `pyproject.toml`.
- **Scanner (attack on repair 2).** Killed mutants listed in N1. The meta-test's three documented counter-examples reproduce (above).

## CI (attack 6)

`bash workflows/ci_gate.sh C:/Users/joshs/GPS/ProofPack/wt-e14 ae23aa5` printed:
- `gate: JoshSandhu/proofpack ae23aa5 -> ci/ae23aa5-1791390454-41985`
- `gate: run 37652193768 ci: success`
- `gate: GREEN ae23aa5`, exit 0

`gh run view 37652193768`: head `ae23aa54975a3222e9fe75473227b0c13e81ec18`, conclusion `success`; all 7 jobs `success` (ap4 with [docx], Docker image smoke, import without scipy, run inside `unshare -rn`, pip-audit, pytest + ruff, wheel artefact). `git ls-remote origin "refs/heads/ci/ae23aa5-1791390454*"` printed nothing afterwards, so my gate branch was deleted. The gate is green, but CI cannot see B1 or B2: both need a test that does not yet exist, or a missing extra under `PROOFPACK_REQUIRE_DOCX=1`.

## What I could not check

- PowerShell 5.1: Git Bash only.
- The Linux-only jobs (Docker reference image, `unshare -rn`): read from the gate run's job conclusions only.
- A site-issued licence on the buyer path: ephemeral-signed licences only.
- Lens 2's carried planted-map items (N3): not re-run.

## Changes for other lanes (site pin move from 8ef3266)

None from `ae23aa5`: no CLI flag, default, path, JSON key, golden or rendered string changed (`e67c5fa..ae23aa5` touches tests and handoffs only). The builder's list for `3ee5601..a1840fc` stands: the T1/T2/T8 cover row; one margin line fewer per merged pair (T1 section 7 two, T2 section 5 one); `data-also`; the DOCX bracket with several ids; the re-prompt string; the `licence show|verify|install --help` usage lines.

## Sentences I refused to write

- "Every E14 DOCX test is now checked for ap4 and needs_extra." B1: K1, K2, K5 pass the meta-test.
- "Repair 2 keeps every guard e67c5fa had." B2: the importorskip check is gone.
- "The scanner's documented branches are tested." N1: 7 of 10 mutants survive.
- "The cover lists every distinct guidance version." Lens 2 FA-N1 (same-month drafts) is still open; I did not re-run it.
