# E8 lens 7 (fresh attack, after repair 6) - build day 8, lane E, at `d36c767` - 23 September 2026

**Verdict: PASS.** No blocker under this lens's grading rule. Nine non-blocking findings follow: four
are sentence violations in repair 6's text (N2-N5), and five of my thirteen mutants survive `-m day8`
(N6). I graded one class as record-and-carry although the attack block's literal rule would call it a
blocker: fifteen of my twenty-seven new `free_text` checker cases are accepted (N1). They include the
British spelling `unbiassed` and certification verbs such as `approves`. N1 gives the grounds; Josh may
regrade it.

Lens-6's two blockers no longer reproduce on their own literals or on the ones I added. FA-B1: the
`p2_star`, `p3_fair`, `p7_site` and `p1b_cells` inputs (U+0000, U+0001, U+001B, U+0085 and U+009F in
`race`, `attr_colour`, `site` and `device` cells) now halt S02 at ingest, exit 3, nothing written.
N8 names the columns the check does not read. RG-B1: `zz_extra: &a [*a]` and the six other
self-referential shapes under "could not break" halt H08, exit 3. The overall block (a statistical
gate) has no code change: `git diff 941f8a7 d36c767 -- src/proofpack/stats` is 0 lines. The site's synthetic cohort gives a byte-identical `run.json` at both
commits once the volatile manifest fields are removed.

Every figure below was measured in this session, in Git Bash unless marked. Worktrees under
`<scratchpad>/lens-E8-r7-fresh-attack/`:

- `new` at `d36c767`: suite, markers, lint and probes;
- `old` at `941f8a7`: pre-repair comparisons;
- `mut` at `d36c767`: my mutants and the committed sweep.

For each worktree I forced `PYTHONPATH=<worktree>/src`. Before trusting a figure, I checked that
`python -c "import proofpack;print(proofpack.__file__)"` printed that worktree's
`src\proofpack\__init__.py`. The probe harness `att/harness.py` asserts the same. Scripts are in
`att/`, and lens 3-6 scripts re-run as `prev/`. Nothing was committed. This note is the only file I
wrote in the main tree. All three worktrees are removed.

## Blockers

None.

## Non-blocking (record and carry)

**N1 - `free_text` accepts plain-ASCII inflections and spellings of the forbidden words (extends
carried row 20).** `att/k1_checker.py` builds the synthetic document (70 engine claims, 0 rejected).
It feeds 27 new texts as `free_text` on engine claim 0; 15 are `ACCEPTED`. Verbatim:

- `The estimate is unbiassed.` and `The subgroup estimate is biassed.` (the British spellings;
  `unbiased` and `biased` are in `VERDICT_WORDS`);
- `The model does meet the criterion.` and `The model is meeting the criterion.` (`meets` and `met`
  are in the list; `meet` and `meeting` are not);
- `The model satisfies the criterion.` and `The model succeeds on the criterion.`;
- `The agency approves the device.`, `The body certifies the device.`, `The society endorses the
  device.`, `The agency clears the device.`, `The device is authorised for marketing.`, `The device
  is authorized for marketing.` and `The De Novo request was granted.` (`CERTIFICATION_WORDS` holds
  `approved`, `approval`, `certified`, `certification`, `endorsed`, `endorsement`, `cleared` and
  `clearance` only);
- `see &sect;` and `The guidances say so.`, both already carried as row 20.

The other 12 are rejected with a specific code. Among them are `FDA cleared` with a space, `calibrated
well`, `well- calibrated`, the en-dash spelling, ZWJ inside `safe`, `P A S S`, a soft hyphen inside
`passes`, U+0085 inside `acceptable`, full-width `fail`, `‰`, U+2167 and `cfr`.

Structural cases: 16 fed, 15 rejected with a specific code. Those fed include `met ` with a trailing
space, upper-case status, a lower-case `template_id`, a trailing slash, a double slash, a ref to a
list, `value_refs` as None or a string, a NUL in `claim_id`, `criterion_index` -1, 999 and `"0"`, an
extra key, and a difference claim whose two refs are the same cell (`value_ref_duplicate`). One is
accepted: `claim_id` `CL-００００１` in full-width digits. Its root is lens-4 item 6 (`\d` matches Unicode
digits), which is carried.

**Why I did not grade this a blocker.** No code at `d36c767` prints `free_text` on T8:
`src/proofpack/templates/T8.html` and `src/proofpack/render/html.py` reference `free_text` 0 times,
and the synthetic cohort's `run.json` holds 66 claims, all with `free_text` null. The E8 handoffs
carry this class as row 20 ("Number words, inflections and derived words accepted"; Needs 2, open),
and lenses 4-6 recorded their own row-20 literals as non-blocking. Separately,
DEC-64 carries look-alike spellings such as `unbiassed` to E9. The certification verbs are the part
Josh should see before E9 puts a sentence in `free_text`. CLAUDE.md forbids a claim of approval
"anywhere, ever". The house style is British English, and `unbiassed` is one of its spellings.

Repro: `LENS_WT=<wt> PYTHONPATH=<wt>/src python att/k1_checker.py` prints
`free_text accepted: ['unbiassed (British)', 'biassed (British)', 'meet (base form)', ...]`.

**N2 - Sentence violation: `design/tokens.json` `source`, "Each token's surface is in its on key"
(new in repair 6).** `brand-strong` is `"role": "text"` with no `on` key. The decorative
`stop-line` and `ok-line` and the seven surfaces have no `on` key either. Loading the committed file prints
`brand-strong #0c2740 text None`. `brand-strong` is therefore a text token that no contrast test
checks (`tests/test_render_theme.py`'s `D5_CONTRAST` has nine pairs, none for `brand-strong`). T8
does not use it (0 hits in `templates/` and `render/`). A sentence that is true: "honesty, stop and
ok carry their `-bg` surface in `on`; brand-strong, a text token, carries none".

Repro: `git show d36c767:design/tokens.json | python -c "import json,sys;print(json.load(sys.stdin)['color']['brand-strong'])"`.

**N3 - Sentence violation: `io/schema.py::columns_read_by_validate` docstring, "The column keys
:func:`validate` reads cells from ... the canonical names of `schema_v1.json`" (and the test name
`test_the_plants_cover_every_column_validate_reads_from_the_table`).** `canonical_columns()` holds
19 names, `event_date` and `period` among them. `validate` does not read `period`'s cells when the
declared period column is `event_date`. It does not read `event_date`'s cells when no period is
declared (`att/t3_reads.py`):

| Input to `validate` | `941f8a7` | `d36c767` |
|---|---|---|
| `period` = `x\x01` x6, `event_date` = `2024-01-01`, period declared on `event_date` | accepted, `Table.period=['2024-Q1']` (no cell of `period` read) | `HALT S02: column role 'period' holds a control character (U+0001) in 6 row(s)` |
| `event_date` = `2024-01-01\x01`, no period declared | accepted, `Table.period=None` | S02 on `event_date` |
| the same, period declared on `event_date` | accepted, `2024-Q1` (`coarsen_date` reads the ISO prefix) | S02 on `event_date` |

The code halts on more inputs than the sentence describes; the sentence names columns `validate` does
not read. A sentence that is true: "the canonical names, which include `event_date` and `period`
whether or not `validate` reads them".

**N4 - Sentence violation: `io/schema.py::check_control_characters` docstring, "its twelve rows
H01-H12 are gates on declarations and aggregates".** H03 halts on one table value, and so does H05
(`att/h_codes.py`, `make_cohort(n=200)`):

- one `score` cell set to `1.5` gives rc 3,
  `HALT H03: score.type is probability but values lie outside [0, 1]`;
- one `row_id` duplicated gives rc 3, `HALT H05: duplicate row_id values`.

This matters beyond wording. DEC-66 asked for "the halt code D1 section 5.6 assigns to a malformed
table value". D1 has no section 5.6. Section 5 step 6 is the HALT table at lines 261-272. H02, H03,
H04 and H05 (lines 262-265) each read table values. The repair chose S02 and put the choice to
Josh (its Needs 1), which is right. The docstring's reason for ruling the table out is the false
part.

**N5 - Sentence violation: `io/declare.py::_check_control_characters` docstring, "U+0001 after the
first character of `clustering.unit` halts E01".** Measured with `validate_dict`:

- `c\x01ase_id` gives `E01 clustering.unit names 2 columns`;
- `case_id\x01` gives `H08 declaration invalid at clustering/unit: control character U+0001`. The
  character is after the first character, but the result is H08;
- `\x01case_id` gives H08.

The test it cites (`test_e8_repair5.py`, "U+0001 after the first character of each of the 43 string
fields") inserts the character at index 1. The docstring should say "at index 1".

**N6 - Five of my thirteen mutants of repair 6 survive `-m day8` (468 passed each; `att/mut.py`, `mut`
worktree, `PYTHONDONTWRITEBYTECODE=1`, no `.pyc` under `src/proofpack/io`).**

| Mutant | Literal it lets through | `d36c767` | Under the mutant |
|---|---|---|---|
| `walk_skips_tuples` (`control_character_at` enters dict/list only) | `model.extra: !!omap [{k: "v\x01"}]` (PyYAML builds a list of tuples) | rc 3 `H08 ... model/extra/0/1: control character U+0001` | rc 0, all four files written, 0 raw control bytes in `T8.html` |
| `selfref_skips_tuples` (`self_reference_at` enters dict/list only) | `model.extra: &a !!omap [{k: *a}]` | rc 3 `H08 ... model/extra/0/1: the value contains itself` | rc 5 `internal error: ValueError: Circular reference detected` (RG-B1's exit 5 back on a `!!omap` alias) |
| `pcol_clause_dropped` (`or h == pcol` removed) | a declared period column whose role is neither canonical nor `attr_` | S02 | not checked (`coarsen_date` keeps the ISO prefix only, so no byte reaches the Table) |
| `ident_clause_dropped` (`attr_` names not matching `_IDENT` also checked) | `attr_Colour` holding U+0001 | accepted (parked in `unused_columns`) | S02 (stricter) |
| `root_not_entered` (`entered = set()`) | none reaches it through `validate_dict`: `self_reference_at` halts a self-referential root first | - | - (equivalent on that route) |

Eight were killed: `first_hit_to_last`, `fast_path_removed` (an `IndexError`, not an equivalent
mutant), `cell_range_starts_at_x01`, `cell_check_after_score`, `finished_not_recorded`,
`open_not_discarded`, `selfref_after_control`, and `key_check_dropped`. No test feeds `!!omap` or
`!!pairs`, and those two survivors are the ones that matter. At `d36c767` both inputs halt correctly
(`att/y3_tuples.py`); at `941f8a7` `omap_self` and `pairs_self` were exit 5 `RecursionError`.

**N7 - `criteria.yaml` inputs that still end in `internal error` (exit 5, nothing written), the same
at both commits (`att/y1_yaml.py`, `att/y2_cli.py`).**

- A flow list nested 500 or more deep under `model.extra` raises `RecursionError` inside
  `yaml.safe_load`, not in the DEC-65 walk: 300 and 400 load; 500, 600, 900 and 1,000 do not.
  `load_yaml` catches `yaml.YAMLError` only. Row 74 asked for the walk to be guarded, and the walk
  is; the loader is not.
- A `!!set`, a `!!binary` value or an unquoted timestamp (`2024-01-01T10:00:00`) under `model.extra`
  gives `TypeError: Object of type set|bytes|datetime is not JSON serializable`. The DEC-65 walk also
  does not enter a `set`, so a string inside `!!set` is never checked; the run ends at `json.dumps`
  before anything is written.

**N8 - DEC-66's scope as built, and the message.**

- The check reads only the columns `validate` reads. `ingest` also profiles every column
  (`map_headers(raw.headers, raw.columns)`). `notes` = `n\x01`, `rater_1` = `x\x1b` and an unmapped
  `zz_free` = `z\x85` (`att/t1_cells.py` A) give rc 0. In `T8.html`, `run.json`, `ingest_report.json`
  and `pseudonyms.json` there are 0 raw control bytes and 0 `\u00xx` escapes. The orchestrator's gloss
  was "every cell the engine reads", and the repair recorded its narrower choice under "Decisions
  taken". Josh should confirm it.
- The halt names the canonical role (`'site'`), not the customer's header. On `compare` it does not
  say which table holds the character: with ESC only in the prior's `site`, the output is
  `HALT S02: column role 'site' holds a control character (U+001B) in 74 row(s)`, exit 3, no
  directory.
- A JSON table cell holding a list, `["a\u0001"]`, is read through `str()` as `"['a\\x01']"` (no
  control byte) and accepted.

**N9 - Characters outside DEC-66's range still reach documents (`att/t1_cells.py` B,
`att/t2_invis_t8.py`).**

- With `race` levels `re<ch>d` / `blue` and a fairness `tpr_gap` block on `race`: U+2028 and U+200B
  each appear once raw in `T8.html`, and U+202E 0 times.
- U+2028, U+2029, U+202E, U+200B, U+FEFF, U+00AD, U+2066 and U+061C each appear 8 times in
  `run.json` and once in `pseudonyms.json`.
- U+2028 was carried by lens 6 as outside DEC-65's range. The rest are the same class. Record only.

## What I could not break (evidence)

- **Suite and lint (`new`, Git Bash).** Full suite: `1256 passed, 1 skipped, 1 xfailed in 144.94s`,
  with `PROOFPACK_TR39_FULL` set. Markers: `day8` 468, `day7` 139, `day6` 285, `day5` 54, `day4`
  182, `day3` 29 + 1 xfailed, `day2` 40, `day1` 59 + 1 skipped, `ap2` 88. `ruff check`:
  `All checks passed!`. `ruff format --check`: `167 files already formatted`. PowerShell 5.1,
  `-m day8`: `468 passed`. All counts equal the repair note's.
- **The repair's pre-fix claim.** `tests/test_e8_repair6.py` plus the new `test_render_theme.py`,
  copied into `old`, give `42 failed, 13 passed`, and the repair-6 file alone gives `39 failed, 3
  passed`. The three that pass are the three guards whose docstrings say they pass at `941f8a7`. The
  three theme failures are `assert 6.8 == 6.189...`, `9.11 == 7.880...` and `10.02 == 8.652...`.
  `test_a_shared_but_not_self_referential_alias_is_accepted` fails at `941f8a7` only on
  `AttributeError`, as its docstring says.
- **DEC-66 counter-examples the tests do not feed (`att/t1_cells.py`, `att/t4_paths.py`).**
  - A leading U+0001 (`\x01red`) halts S02 U+0001, 200 rows. `r\x7fed` halts U+007F. `re\rd` halts
    U+000D. A leading U+001F is stripped by `str.strip()` and gives rc 0 with 0 bytes in any output.
  - U+0001 only in the 20 `dev` rows halts S02 `site`, 20 rows.
  - ESC only in the `compare` prior halts S02, with no directory written.
  - A JSON list-of-rows table with U+0001 in `race` halts S02, 100 rows.
  - A halted run leaves `PROOFPACK_HOME` holding `proofpack.lic` only; a clean run adds
    `ledger.json`.
  - Timing on 100,000 rows x 19 read columns: 0.041 s clean, 0.048 s with one hit in the last row.
- **An ordinary table is unaffected.**
  - Every CSV under `tests/fixtures/` plus the site's six demo CSVs: `files 41 cells 82451 hits 0
    check halts 0`.
  - The site's synthetic cohort through `run --offline --format json,html` (`att/t5_cohort.py`):
    rc 0 at both commits, 66 claims. `run.json` with `run_id`, `started`, `duration_s` and
    `mapping_sha256` removed is byte-identical (436,668 bytes as sorted JSON; `cmp` silent).
  - `T8.html`, 33,262 bytes at both commits, differs only in the run id (title and two headers), the
    mapping SHA-256 row and the duration row.
- **RG-B1 and FA-N4 (`att/y1_yaml.py`, `att/y3_tuples.py`).** Each of these is H08 naming the path,
  exit 3:
  - `extra: &a {me: *a}`;
  - `extra: &a [[[*a]]]` (at `model/extra/0/0/0`);
  - `clustering: &c` with `again: *c`;
  - `criteria: &cl` with `- *cl`;
  - `&a !!omap [{k: *a}]` and the `!!pairs` form (exit 5 `RecursionError` at `941f8a7`).

  A shared `!!omap` under two keys gives rc 0. `&a {k: 1, <<: *a}` gives rc 0. Alias-chain timing in `validate_dict`:

  | Chain | `d36c767` | `941f8a7` |
  |---|---|---|
  | list chain, depth 20 | 0.015 s | 0.574 s |
  | list chain, depth 22 | 0.001 s | 2.658 s |
  | mapping chain, depth 22 | 0.001 s | 4.181 s |
- **DEC-67 tokens.** I recomputed the ratios with the sRGB relative-luminance formula, written
  without repo code:
  - honesty/honesty-bg 6.1890 (D5 6.2, file 6.19);
  - stop/stop-bg 8.6520 (8.7, 8.65);
  - ok/ok-bg 7.8809 (7.9, 7.88).

  The other six declared pairs match `contrast_computed` to 2 dp. `git grep` for `do not match`,
  `errat`, `6.80`, `10.02` or `9.11` in `src design tests/*.py scripts` finds only the repair-6 test
  and the test comment that quote the old figures. The site references `tokens.json` only in
  `src/styles/docs.css`.
- **Packaging (`att/e_packaging7.py`, `uv build --offline`).**
  - With jinja2, markupsafe, scipy, cryptography, statsmodels and sklearn hidden, all eight modules
    import, and `environment()` raises `RendererUnavailable`.
  - The wheel holds the three templates and `proofpack/_schema/tokens.json`. That file equals
    `design/tokens.json` after LF normalisation, with `on` `honesty-bg` / `stop-bg` / `ok-bg` and
    6.19 / 8.65 / 7.88.
  - In a fresh venv: 0 `.pth` files, and `proofpack.__file__` and `tokens.json` resolve inside the
    venv with and without `PYTHONNOUSERSITE=1`.
  - The lock names jinja2 3.1.6. `uv lock --check --offline`: rc 0. `ci.yml` has `uv sync
    --all-groups --locked` 3 times. `test_render_theme.py`: 13 passed.
- **Lens 3-6 probe battery at both commits (`battery.sh`, 55 scripts; outputs diffed after masking
  run ids, temp paths and timings).** The only differences are the lens-6 closures:
  - `p2_star` `attr_colour` and `race` soh/c1/nul: rc 0 with raw bytes in `T8.html` becomes rc 3
    S02;
  - `p3_fair`: raw ESC at byte 25,164 becomes rc 3 S02;
  - `p7_site` `site`/`device`: rc 0 becomes rc 3;
  - `p1b_cells` `nul`/`c1`: rc 0 becomes rc 3 S02 on `attr_colour`;
  - `p4_yaml` `recursive_extra`: rc 5 becomes rc 3 H08 `model/extra/0`;
  - two traceback line numbers.

  Every other line is equal, including:
  - the overall block (`prev5/overall.py`, clustered, 300 rows in 100 cases): engine two-by-two
    `{tp 80, fn 15, fp 48, tn 157}` equals the numpy count, and the est deviation is `0.0` for
    sensitivity, specificity, PPV and NPV. LR+, LR-, DOR, F1, MCC, Youden and balanced accuracy are
    `clustered_data_analytic_ci_invalid None None none`. The one-stratum subgroup has equal
    estimates, and its interval deviations of up to 0.0181 are the same figures lens 5 and lens 6
    explained. One cluster gives `insufficient_clusters`; two give `[0.8367, 0.8478]`; each row its
    own cluster gives `[0.7579, 0.9158]`. The `y_pred`-only normal, one-class and all-1 cases
    equal the hand counts. For integer `y_pred`, the engine's `{tp 38, fn 14, fp 39, tn 109}`
    equals the normal case; the script's hand count compares strings, as lens 6 recorded;
  - the renderer: 0 `@import`, `url(`, `<link`, `<script`, `http:` and `https:` on the page, 19
    hex colours and 7 px values all in tokens, footers 3/3/3 on 0, 1 and 40 rows,
    `render_pages` 0/1/5, `[unverified]` 7 times, the draft label on 14 AI-DSF mentions (the one line
    without it is the disclaimer sentence lens 5 explained), 22 observed
    cells re-derived by D4 section 1.2 with 0 mismatches, the golden at 40,030 bytes equal, and the
    injections escaped;
  - the wiring: valid rc 0 with `T8.html` 40,375 bytes; grace with the watermark 7 times; past grace
    and no file rc 4, JSON only; `TRIAL` 7 times; `--format docx` rc 5; `--offline` with sockets
    raising, 0 calls; two runs with claims, rejections, `guidance_refs` and `criteria_results`
    equal and the manifest differing in `duration_s`, `ledger_count` and `run_id` only; `run.json`
    validates.
- **Other checks.**
  - `git diff 941f8a7 d36c767 --` `src/proofpack/{stats,render,narrate,templates}`,
    `cli.py`, `run.py`, `errors.py`, `criteria.py`, `gates.py`, `pyproject.toml`, `uv.lock` and
    `schema/`: 0 lines.
  - The E7 verdict grep: `5 passed`. E6's output-schema test: `1 passed`. `doctor --offline`:
    `All essential checks passed.`
  - `mutation_sweep.py --list`: 274 lines (34 day5, 112 day6, 25 day7, 87 day8, 16 ap2).
  - Committed sweep (`mut`, `--marker day8`): `103 planted, 103 killed, 0 survived; 1315 s`, exit 0,
    and `git status --short` empty afterwards. The four repair-6 mutants were each killed with one
    failure.

## What I could not check

- CI on the reference platform. The engine is not pushed.
- A browser or terminal consumer of the U+2028 and U+200B bytes in N9. I read bytes only.
- The site's Pyodide demo against this engine. The site is pinned at `a0c9abc`.
- Row 86's `run.json` expansion (155 MB at 20 levels, per the repair note). I did not re-run it. My
  timings cover `validate_dict` only.
- Whether Josh reads DEC-66's "table cells" as every column `ingest` profiles, or as the columns
  `validate` types (N8).

## Sentences I refused to write

- "Control characters in table cells can no longer reach a document." Written instead: the
  literals in N8/N9 and under "could not break", with the files and byte counts.
- "The self-reference guard handles every YAML construct." Written instead: the alias shapes listed
  under "could not break", the loader's depth limit (N7) and the two tuple mutants that survive
  (N6).
- "The checker rejects every inflection." Written instead: N1's 15 accepted literals.
- "Repair 6 introduced no regression." Written instead: the battery diff, whose only changed lines
  are the lens-6 closures.

## Re-run these

```bash
cd C:/Users/joshs/GPS/ProofPack/proofpack
L=<scratchpad>/lens-E8-r7-fresh-attack
git worktree add --detach $L/new d36c767 && git worktree add --detach $L/old 941f8a7
PYTHONPATH=$L/new/src python -c "import proofpack;print(proofpack.__file__)"   # must print $L/new
cd $L/new
LENS_WT=$L/new PYTHONPATH=$L/new/src PYTHONIOENCODING=utf-8 python $L/att/k1_checker.py    # N1: 15 free_text accepted
LENS_WT=$L/new PYTHONPATH=$L/new/src python $L/att/t3_reads.py                            # N3 (run in old too)
LENS_WT=$L/new PYTHONPATH=$L/new/src PYTHONIOENCODING=utf-8 python $L/att/h_codes.py      # N4: H03, H05
LENS_WT=$L/new PYTHONPATH=$L/new/src PYTHONIOENCODING=utf-8 python $L/att/y3_tuples.py    # N6 inputs
LENS_WT=$L/mut python $L/att/mut.py                                                       # N6: 5 SURVIVED
LENS_WT=$L/new PYTHONPATH=$L/new/src PYTHONIOENCODING=utf-8 python $L/att/y2_cli.py       # N7: rc 5 rows
LENS_WT=$L/new PYTHONPATH=$L/new/src PYTHONIOENCODING=utf-8 python $L/att/t1_cells.py     # N8, N9
$L/battery.sh $L/new $L/battery_new.txt; $L/battery.sh $L/old $L/battery_old.txt           # diff after masking
git -C C:/Users/joshs/GPS/ProofPack/proofpack worktree remove --force $L/new   # and old, mut
```

## What the next repair needs (if Josh takes any of these into scope)

- **N2-N5:** four sentences corrected to name the literals above.
- **N6:** a test feeding `!!omap [{k: "v\x01"}]` and `&a !!omap [{k: *a}]`, and the two matching
  sweep mutants.
- **N1:** a decision on inflections and the certification verbs before E9 writes `free_text` (row
  20, Needs 2).
- **N7:** optionally, `load_yaml` could catch `RecursionError` and the JSON `TypeError` as H08. That
  would be a new typed halt, so it needs a decision.
