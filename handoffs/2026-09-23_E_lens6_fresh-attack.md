# E8 lens 6 (fresh attack, after repair 5) - build day 8, lane E, at `ea2f743` - 23 September 2026

**Verdict: FAIL.** One blocker. Lens-5 FA5-B4 reads "C0 control characters in customer text are
written raw into T8.html (NUL, SOH, ESC), through the CLI". Its literal input, the criteria.yaml model
name, now halts H08, so that literal no longer reproduces. The same bytes still reach `T8.html` raw
from a **table cell**. A level label from the input table is printed in the criteria table's scope
cell when a criterion declares `level: "*"`, and on the fairness-bound row. This goes through the CLI
with a licence and `--offline`, and exits 0. Repair 5 carried "control characters in table cells"
as outside DEC-65, and its measured figure ("`T8.html` 0 raw") covers one input only: site cells
with no criterion naming the site attribute. I grade this a blocker under this lens's rule ("an
unescaped injection"), as lens 5 graded FA5-B4. If Josh reads DEC-65 as covering declarations only,
it becomes record-and-carry. The decision is his (see "What the repair needs").

Every figure below was measured in this session. Worktrees under
`<scratchpad>/lens-E8-r6-fresh-attack/`:

- `wt` at `ea2f743`: suite, markers, lint, committed sweep and probes;
- `pre` at `2a9a6e2`: pre-repair comparisons;
- `mut` at `ea2f743`: my mutants.

For each worktree I forced `PYTHONPATH=<worktree>/src`. Before trusting a figure, I printed
`proofpack.__file__` and checked that it was that worktree's `src\proofpack\__init__.py`. The probe
harness `att/harness.py` asserts the same thing. Scripts are in `att/`. Re-runs of the lens-3/4/5
scripts are in `prev3/`, `prev4/` and `prev5/`, with outputs in `prev34_out.txt` and
`prev5_out.txt`. Nothing was committed. This note is the only file I wrote in the main tree. All
three worktrees are removed.

## Blockers

### B1 - C0 and C1 control characters in a table cell reach T8.html raw, through the CLI, exit 0 (FA5-B4's bytes, another input)

`render/html.py::criteria_rows` prints each row's scope through `_scope_text` (line 236):
`attribute = level`. For a `level: "*"` criterion, and for the fairness-bound row, the level comes
from the table's cells, not from criteria.yaml. `validate_dict` never sees that level. The renderer
escapes markup (`<script>` is written 0 times raw) and writes bidi controls as references. It does not
refuse or escape C0 or C1 controls.

`att/p2_star.py`: `make_cohort(n=400)` plus one attribute column whose levels alternate between two
labels, the attribute declared in `subgroups`, and one criterion
`{metric: sensitivity, operating_point: op1, scope: {attribute: <a>, level: "*"}, ...}`. The run
used a licence and `--offline`.

| Attribute | Levels fed | rc | Raw bytes in `T8.html` (verbatim) |
|---|---|---|---|
| `attr_colour` | `re\x01d`, `bl\x1bue` | 0 | `<td class="customer-text">attr_colour = re\x01d</td>` and `... = bl\x1bue</td>` |
| `attr_colour` | `re\x85d`, `bl\x9fue` | 0 | `attr_colour = re\xc2\x85d`, `attr_colour = bl\xc2\x9fue` |
| `attr_colour` | `re\x00d`, `blue` | 0 | `attr_colour = re\x00d` |
| `race` | the same three pairs | 0 | `race = re\x01d`, `race = bl\x1bue`, `race = re\xc2\x85d`, `race = re\x00d` |
| `site` (`att/p7_site.py`) | `S\x001`, `S\x1b2`, `S3` | 0 | `site = S\x001`, `site = S\x1b2` |
| `device` (`att/p7_site.py`) | `dev\x00A`, `devB` | 0 | `device = dev\x00A` |

There is also a route with no `"*"` criterion (`att/p3_fair.py`). A fairness block
`{criterion_of_interest: tpr_gap, attribute: race, bound: 0.2, statistic: point_estimate,
comparator: "<="}` on `race` levels `re\x01d` / `bl\x1bue` gives rc 0, and `T8.html` holds
`mono">fairness:tpr_gap</td>\n<td>tpr_gap</td>\n<td class="customer-text">race = re\x01d</td>` at
byte 25,164.

The same scripts at `2a9a6e2` give the same bytes, so repair 5 did not introduce this; it did not
close it either. With `sex`, `M\x01` halts H07 (mapping confidence drops), which matches the repair
note.

Repro: `LENS_WT=<wt> PYTHONPATH=<wt>/src PYTHONIOENCODING=utf-8 python att/p3_fair.py` prints
`0 {... 'T8.html': 1}` and the byte context above.

The repair note's carried row ("Control characters in **table cells** ... site column cells prefixed
U+0001 ... `T8.html` 0 raw, 0 escaped") is literally true for its input. That input had no criterion
naming the site attribute. The r5 handoff's carried table must not reuse the figure as evidence that
table cells stay off the page.

## Non-blocking (record and carry)

**N1 - Five non-equivalent mutants of repair 5 survive `-m day8` (425 passed, 1 skipped each).**
`att/my_mutants.py` runs in `mut`. Before each run it deletes `src/**/__pycache__` and sets
`PYTHONDONTWRITEBYTECODE=1`. The first pass without that step could not be trusted: one mutant keeps
the file size, and a stale `.pyc` served the old code. `att/mutdemo.py` gives one literal
counter-example per mutant. Each is H08 at `ea2f743` and passes under the mutant:

| Mutant | Literal | At `ea2f743` | Under the mutant |
|---|---|---|---|
| `m_multiline_c1_dropped` (`_CONTROL_MULTILINE` loses `\x7f-\x9f`) | justification `a\x9b31mb` (C1 CSI) | `H08 ... criteria/0/justification: control character U+009B` | accepted, and the justification is printed on T8 |
| `m_key_check_multiline` (keys checked with `_CONTROL_MULTILINE`) | key `x\ty` in `model` | `H08 ... model (key): control character U+0009` | accepted |
| `m_mapping_decided_by_unread` (`decided_by` not walked) | `decided_by: "file\x1b[31m"` | `H08 mapping.json invalid at decided_by: ... U+001B` | `Mapping.read` accepted |
| `m_control_after_authored` (DEC-65 walk moved after the authored-field loop) | criterion id `C\x1b[31m1`, author `""` | `H08 ... criteria/0/id: ... U+001B` | `H08 'criterion C\x1b[31m1 lacks author'`: raw ESC in the printed halt |
| `m_mapping_detail_prefix` (detail `field` loses `mapping.json `) | any mapping hit | detail `mapping.json roles/...` | detail `roles/...` (cosmetic) |

`m_multiline_cr_allowed` (CR allowed in multi-line fields) is killed. The first row is the one that
matters. No test feeds a C1 character to `justification`, `description` or `source`, and the
committed mutant `declare_dec65_c1_and_del_dropped` mutates `_CONTROL` only. The fourth row's
behaviour is what the code comment "before any message below that prints a criterion id" describes,
but no test pins it.

**N2 - Sentence violations in the repair-5 code comments (DEC-65 wording).**
- `io/declare.py` module docstring, line 6: "and so is a string holding a control character". Two
  counter-examples: `justification: "a\tb"` is accepted (by design;
  `::test_tab_and_line_feed_are_accepted_in_the_three_free_text_fields`), and `clustering.unit:
  "pat\x00ient"` halts `E01 clustering.unit names 2 columns; reduce your case key to one column`, not
  H08 (`att/p4_yaml.py`, `clustering_unit_ctrl`).
- `io/declare.py` line 45: "C0 controls ..., DEL ... and C1 controls ... in a string of
  `criteria.yaml`, key or value, are H08 naming the field". Counter-example: any C0/C1 character
  strictly inside `clustering.unit`, or inside a string under `clustering.columns`, `column`, `key`,
  `keys`, `units` or `fields`, halts E01, which names neither the field nor the code point. A leading
  one (`"\x01none"`) is H08. The test asserts E01 for `clustering/unit`, so the code is deliberate.
  The sentence is not.

  DEC-65 says "H08 naming the field". Exit 3, nothing written.

**N3 - The S4 precedence bullet names one case of four.** The note says "a document that lacks a
criterion's author and names a composite case key now halts E01". Measured with `unit: "a and b"`:
`criteria: "x"`, `criteria: [5]` and `fairness: "x"` each halt E01 at `ea2f743`. At `2a9a6e2` they
halted `H08 criteria block must be a list`, `H08 criteria[0] is not a mapping` and
`H08 fairness block is not a mapping`. Any authored-field or block-shape H08 now yields to DEC-11's
E01. S4 should carry all four.

**N4 - Failures that print `internal error` (exit 5) rather than a typed halt, on the new walk.**
- A recursive YAML alias (`extra: &r [*r]` under `model`) is exit 5 `RecursionError` at `ea2f743`.
  It was exit 5 `ValueError: Circular reference detected` at `2a9a6e2`. Neither writes a file.
- An alias chain of depth 20 under `model.extra`, with 1,048,576 expanded leaves: `validate_dict`
  takes 0.51 s at `ea2f743` against 0.00 s at `2a9a6e2` (`att/p9_laughs.py`). The walk is linear in
  the expanded size. At `2a9a6e2` the same document would expand later, in `json.dumps` of
  `run.json`.
- The YAML escape `"\ud800"` in the model name (a lone surrogate, not C0/C1) is exit 5
  `UnicodeEncodeError` at both commits, with no file written.

**N5 - Carried classes re-measured; no change under DEC-64.**
- The lens-5 corpus (`corpus_new.py`) gives `accepted 12`, the same list as lens 5.
- My new `free_text` cases (`prev3/l6_checker.py`, 20): 18 are rejected. Two are accepted:
  - the regional-indicator spelling of `pass` (U+1F1F5 U+1F1E6 U+1F1F8 U+1F1F8), a look-alike
    carried under DEC-64;
  - `ninety per cent`, a number word, carried since lens 2.
- Structural cases (17): 16 are rejected with a specific code. `claim_id` `CL-٠٠٠١`
  (Arabic-Indic digits) is accepted, which is the root cause of lens-4 item 6 (`\d` matches Unicode
  digits), still carried.
- Lens 3's `b2_checker.py` still shows CRITERION_STATUS relabelled ATTAINABILITY_NOTE accepted
  (carried since lens 3).

**N6 - Mapping fields outside the walk.** `mapping.json` `source`, `value_summaries` keys and unknown
top-level keys holding ESC give exit 0 with 0 control bytes in any output file (`att/p6_mapping.py`).
Nothing is read from them onto the page. I record this against DEC-65's "the mapping".

## What I could not break (evidence)

- **Suite and lint (`wt`, Git Bash).** Full suite: `1213 passed, 2 skipped, 1 xfailed in 96.72s`.
  The second skip is the TR39 regeneration test, which looks for `workflows/data` beside the
  worktree. With `PROOFPACK_TR39_FULL` set it gives `1 passed`, which accounts for the repair
  note's 1214.
  - Markers: `day8` 425 + 1 skipped; `day7` 139; `day6` 285; `day5` 54; `day4` 182; `day3` 29 + 1
    xfailed; `day2` 40; `day1` 59 + 1 skipped; `ap2` 88.
  - `ruff check`: `All checks passed!`. `ruff format --check`: `163 files already formatted`, and
    162 at `2a9a6e2`.
- **The repair's own claims, re-measured.**
  - `tests/test_e8_repair5.py` copied into `pre`: `64 failed, 4 passed`.
  - Planting U+0001 in each of the 43 string fields (`att/p5_fields.py`): at `2a9a6e2`, 16 reach
    `run.json`, 11 reach `T8.html`, and the rc split is 16 × 0 and 27 × 3. At `ea2f743` all 43 give
    rc 3: 42 are H08 naming the field and `clustering/unit` is E01.
  - The 14 named literals at `2a9a6e2`: 13 pass `validate_dict`, and `op\x001` is H09.
  - The three mapping literals at `2a9a6e2`: `notes` and `timestamp` give rc 0 with 0 control bytes;
    `role` gives rc 3 with `HALT H07: mapping.json maps a column to attr_colour\n but ...`.
  - `map --criteria`, `compare` and `map --yes` (with a notes hit) each give rc 3 H08, with no
    directory written. The `map --yes` file's SHA-256 is unchanged (`att/p8_paths.py`).
  - Lens 5's `nul_cli.py` now halts
    `H08 ... model/name: control character U+0000`, and `nul.py` halts H08 through the assembler.
  - The PyYAML facts: `a: |` with CRLF loads as `'x\ny\n'`, and `"x\ry"` loads as `'x y'`.
  - `_IDENT` matches `attr_x\n`: `True`.
  - `grep` for the three old sentences in `src tests scripts README.md`: 0 lines.
  - `mutation_sweep.py --list`: 270 lines (34/112/25/83/16).
  - The three demo YAML files (`tests/fixtures/mapping/mimic_composite_key.criteria.yaml` and the two
    site `synthetic_cohort.criteria.yaml`): `control_character_at` returns `None` for each.
- **YAML edge cases (`att/p4_yaml.py`, `wt` against `pre`).**
  - `\N` (U+0085) in the name: H08 U+0085. At `2a9a6e2` it was rc 0 with `Tri\xc2\x85age` in T8 5
    times.
  - An int key `7: "a\x01"`: H08 `model/7`. At `2a9a6e2` it was exit 5 `TypeError`.
  - `!!binary` version: H08 `type`.
  - A raw U+0080 in the stream: H08 `ReaderError`. A raw U+0085 in a plain scalar: H08
    `ScannerError`.
  - `clustering.declared_by` holding ESC: H08. At `2a9a6e2` it was rc 0 with raw ESC on T8.
  - U+2028 (`\L`) passes and reaches T8 raw. It is outside DEC-65's ranges and was carried by the
    repair.
- **Mutation sweep (committed, `wt`):** `--marker day8` gives
  `99 planted, 99 killed, 0 survived; 1188 s`, exit 0. The seven `*_dec65_*` mutants are killed,
  and `git status` in `wt` is empty afterwards.
- **The overall block (a statistical gate, unchanged).** `git diff 2a9a6e2 ea2f743 --
  src/proofpack/{stats,render,narrate,templates,run.py,cli.py,errors.py,criteria.py} pyproject.toml
  uv.lock schema design` is empty. Lens 5's `overall.py` gives:
  - clustered, 300 rows in 100 cases, seed 777: engine two-by-two `{tp 80, fn 15, fp 48, tn 157}`,
    equal to my numpy count. The est deviation is `0.0` for all four proportions, and k/n are equal.
    Each interval is equal to a direct `proportion_ci` call with the same cell key;
  - LR+, LR-, DOR, F1, MCC, Youden and balanced accuracy are
    `clustered_data_analytic_ci_invalid`, with `None None none`;
  - the one-stratum subgroup: est equal, and interval deviations up to 0.0181. These are the same
    four figure pairs as lens 5, from the subgroup's own cell-key seed;
  - one cluster: `insufficient_clusters`, no interval. Two: `[0.8367, 0.8478]` with
    `not_evaluable_shown_for_transparency`. Each row its own cluster: `[0.7579, 0.9158]`;
  - `y_pred`-only: normal, one class, all 1 and integer `y_pred` equal the hand counts, the last
    under string comparison;
  - two operating points: `HALT H08 ... (a, b)`.

  Lens 4's `c3_pe.py`: the four clustered point-estimate rows print
  `n.e. (clustered_data_analytic_ci_invalid)` and `not assessable`.
- **Renderer (lens 3's `c_renderer.py`, `c2_render.py`; lens 5's `cells.py`, `inject62.py`,
  `dec62*.py`).**
  - Page: 0 `@import`, `url(`, `<link`, `<script`, `http:`, `https:`. 19 hex colours and 7 px
    literals, 0 not in tokens. Font families are `var(--pp-type-*)` only. 0 `@font-face`.
  - Footers 3/3/3 on 0, 1 and 40 rows. `render_pages` 0/1/5 gives 0/1/5 footers.
  - `[unverified]` 7 times.
  - The draft label on 14 AI-DSF mentions. The one unlabelled line is the disclaimer sentence
    lens 5 explained.
  - Watermarks `TRIAL`, `LICENCE EXPIRED - not for submission` and `NO LICENCE - not for
    submission`: 4 tags each. None or empty: 0.
  - Golden: 40,030 bytes, equal. The same document twice is identical.
  - 22 observed cells re-derived by D4 section 1.2: 0 mismatches. `cells.py`: 23 cells, 0
    mismatches. A typed-reason cell prints `n.e. (insufficient_positives)` with no `0.75`.
  - Digit runs untraced: 7, each `04` inside fixed guidance or disclaimer text.
  - Injections: `<script>`, `<img`, `&lt;`, `{{ 7*7 }}`, `{% raw %}`, U+202E, emoji, 10,000
    characters, `"><b>`. Each is escaped or literal, with no `49` and 0 raw U+202E. The NUL
    payload now halts H08.
  - Forbidden words outside `.customer-text`: 0.
- **Wiring (lens 3's `d_wiring.py`, lens 4's `d_wire.py`, lens 5's `cli61.py`).**
  - Valid licence: rc 0, `T8.html` 40,375 bytes, no CRLF, no BOM.
  - Grace: HTML with the watermark 7 times. Expired past grace, and no file: rc 4, JSON only.
  - `--templates T1`: rc 0 and the typed line. `--format docx`, `pdf,json` and `--templates T9`:
    rc 5, no directory.
  - `--offline` with telemetry: 0 network calls. The second run: 0 calls.
  - F17: the manifest differs only in `duration_s`, `mapping_sha256`, `run_id` and `started`
    (the script rewrites the mapping between runs). 70 claims equal. `run.json` validates.
- **Packaging (lens 3's `e_packaging.py` pointed at `wt`).**
  - With jinja2, markupsafe, scipy, cryptography, statsmodels and sklearn hidden: all eight
    modules import, and `environment()` raises `RendererUnavailable`.
  - `uv build`: rc 0. The wheel holds the three templates and `_schema/tokens.json`, and names
    `Requires-Dist: jinja2>=3.1`.
  - The fresh venv has no `.pth`. `proofpack.__file__` and `tokens.json` resolve inside the venv
    with `PYTHONNOUSERSITE=1`.
  - The lock names jinja2 3.1.6. `uv lock --check --offline` gives rc 0. `ci.yml` has
    `uv sync --all-groups --locked` 3 times. The wheel test gives `13 passed`.

## What I could not check

- A browser or terminal consumer of the raw bytes in B1. I read the bytes only.
- Whether DEC-65's "labels" was meant to include table level labels. The DEC row names customer text
  "in criteria.yaml or the mapping". The orchestrator's summary lists "labels" without saying which.
- CI on the reference platform. The engine is not pushed.
- PowerShell 5.1 runs. All my figures are from Git Bash.

## Sentences I refused to write

- "Control characters can no longer reach T8." Written instead: B1's inputs and bytes.
- "The DEC-65 gate covers every customer string." Written instead: the 43 fields and 14 literals
  re-measured, the E01 exception (N2) and the table-cell route (B1).
- "The repair's mutants pin the gate." Written instead: seven committed mutants killed, and my five
  survivors with literals (N1).
- "The look-alike class is closed." Not written (DEC-64). N5 lists the two new accepted spellings.

## What the repair needs

- **B1:** either refuse C0/C1 in level labels at ingest (H07 or H08 naming the attribute, exit 3),
  or have the renderer refuse or escape C0/C1 in every string it prints. The second option is the one
  lens 5 offered for FA5-B4. Josh decides which; DEC-65 as written names criteria.yaml and the
  mapping. Pin it with `make_cohort(n=400)`, `race` levels `re\x01d` / `bl\x1bue`, a fairness block
  `tpr_gap` on `race` with bound 0.2, and a `level: "*"` criterion on `race`. Assert 0 bytes matching
  `[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]|\xc2[\x80-\x9f]` in `T8.html`, or the halt.
- **N1:** add C1 in a multi-line field, a tab in a key, `decided_by` with ESC, and a control id with
  an empty author to the tests, and add the matching sweep mutants.
- **N2 and N3:** correct the two comments and the S4 bullet.

## Re-run these

```bash
cd C:/Users/joshs/GPS/ProofPack/proofpack
git worktree add --detach <wt> ea2f743
PYTHONPATH=<wt>/src python -c "import proofpack;print(proofpack.__file__)"   # must print <wt>
A=<scratchpad>/lens-E8-r6-fresh-attack/att
LENS_WT=<wt> PYTHONPATH=<wt>/src PYTHONIOENCODING=utf-8 python $A/p2_star.py   # B1: 'T8.html': 2, raw bytes
LENS_WT=<wt> PYTHONPATH=<wt>/src PYTHONIOENCODING=utf-8 python $A/p3_fair.py   # B1: fairness row, byte 25164
LENS_WT=<wt> PYTHONPATH=<wt>/src PYTHONIOENCODING=utf-8 python $A/p7_site.py   # B1: site, device
R5_TEST=<wt>/tests/test_e8_repair5.py LENS_WT=<wt> PYTHONPATH=<wt>/src python $A/p5_fields.py  # 43 x rc 3
git worktree add --detach <mut> ea2f743 && MUT_WT=<mut> python $A/my_mutants.py   # N1: 5 SURVIVED, 1 KILLED
git -C C:/Users/joshs/GPS/ProofPack/proofpack worktree remove --force <wt>
```
