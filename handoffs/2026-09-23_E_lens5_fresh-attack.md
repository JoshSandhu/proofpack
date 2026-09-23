# E8 lens 5 (fresh attack, after repair 4) - build day 8, lane E, at `375719c` - 23 September 2026

**Verdict: FAIL.** Four blockers. Three of them are look-alike spellings of listed words that
`free_text` accepts although Unicode TR39 18.0.0 lists every character in them:

- B1: TR39 entries whose target is a non-ASCII Latin letter were left out of the vendored map
  (`oк`, `мeets`, `cerтified`).
- B2: characters whose TR39 skeleton equals that of ASCII capital `I` are accepted in an `i`
  position (`unbꓲased`, `faӀl`), while `unbIased` and `faIl` are rejected.
- B3: TR39 is applied before decomposition, so a precomposed letter whose base TR39 lists is
  accepted (`appѓoved`), while the decomposed spelling of the same text is rejected.

The fourth (B4) predates repair 4. A criteria.yaml model name holding `\0`, `\x01` or `\x1b`
reaches `T8.html` as raw NUL, SOH and ESC bytes, through the CLI, with exit 0. The four lens-4
blockers FA-B1, FA-B2 and FA-B3, and the 35 FA-B4 literals, no longer reproduce. FA-B4's
class does reproduce (B1-B3). Under DEC-60 that class is TR39-listed, so I report it as a
blocker.

Every figure below was measured in this session. Worktrees under
`<scratchpad>/lens-E8-r5-fresh-attack/`:

- `wt` at `375719c` (suite, markers, lint, committed sweep);
- `wt0` at `23f3d9f` (base comparisons and the pre-fix run);
- `mut` at `375719c` (my mutants);
- `ro` at `375719c` (read-only probes while the sweep ran).

For each worktree I forced `PYTHONPATH=<worktree>/src` and printed `proofpack.__file__` as that
worktree's `src\proofpack\__init__.py` before trusting a figure. All four worktrees are removed,
and `git status` in the main tree is empty. Nothing was committed. This note is the only file I
wrote in the main tree. Probe scripts are in `<scratchpad>/lens-E8-r5-fresh-attack/att/`, and
outputs are in `out/`. The lens-3 and lens-4 scripts, re-run unchanged against `375719c`, are
in `prev3/` and `prev4/`.

## Blockers

### B1 - TR39 sources whose target is a non-ASCII Latin letter are not mapped: 826 of 1,264 texts accepted, including `oк`, `мeets`, `cerтified`

`scripts/tr39_subset.py::subset` keeps an entry only when its target, with its marks removed,
matches `[A-Za-z]+`. TR39 18.0.0 maps some common letters to a non-ASCII Latin prototype
instead. Measured from `workflows/data/confusables-18.0.0.txt`:

| Source | TR39 target |
|---|---|
| Cyrillic `к` U+043A | `ĸ` (kra) |
| Cyrillic `т` U+0442 | `ᴛ` |
| Cyrillic `в` U+0432 | `ʙ` |
| Cyrillic `н` U+043D | `ʜ` |
| Cyrillic `м` U+043C | `ʍ` |
| Cyrillic `ԍ` U+050D | `ɢ` |
| Cherokee `ꭰ` U+AB70 | `ᴅ` |
| Cherokee `ꭱ` U+AB71 | `ʀ` |
| Cherokee `ꭺ` U+AB7A | `ᴀ` |
| Coptic `ⲧ` U+2CA7 | `ᴛ` |
| Coptic `ⲛ` U+2C9B | `ɴ` |

91 distinct single non-ASCII Latin targets occur. The hand small-capital map reads the target
(`ᴛ`, `ʙ` ...) but never sees it, because the source is not mapped to it. DEC-60 reads "maps
every character that the Unicode TR39 confusables data lists as confusable with a Latin letter
to that letter".

`att/chain_sweep.py` put each source of 14 such targets (`ĸ ᴛ ʜ ɢ ʙ ʟ ʀ ᴇ ᴘ ᴀ ᴅ ɴ ʍ ᴊ`, read as
`k t h g b l r e p a d n m j`) in place of that letter in every listed word (`VERDICT_WORDS`,
`CERTIFICATION_WORDS`, `well calibrated`). Each text was fed bare and inside
`The model was {} here.`. Result: **1,264 texts, 826 accepted.**

Through `checker.check` on corpus 141's `OVERALL_ESTIMATE` claim (`att/corpus_new.py`), each of
these is ACCEPTED:

- `The result was oк.`
- `It мeets the bar.`
- `It is cerтified.`
- `It is unвiased.`
- `The verdicⲧ.`
- `It was approveꭰ.`

The same texts are accepted at `23f3d9f`.

Repro:
`python -c "from proofpack.narrate.checker import free_text_reason as f;print([f(t) for t in ('o\u043a','\u043ceets','cer\u0442ified','un\u0432iased','approve\uab70')])"`
prints `[None, None, None, None, None]`. It prints the same in a fresh venv built from the wheel:
`proofpack.__file__` inside the venv, 1,905 entries, `ꓑass` rejected, `oк` and `cerтified`
accepted.

### B2 - TR39's I/l asymmetry: an I-shaped character in an `i` position is accepted, 2,803 of 4,674 texts

TR39 maps ASCII `I` to `l`, and it maps 114 other sources to `l`, for example:

- Lisu `ꓲ` U+A4F2 (LISU LETTER I);
- Cyrillic `Ӏ` U+04C0 (palochka);
- Coptic `Ⲓ` U+2C92;
- Runic `ᛁ` U+16C1;
- Latin `Ɩ` U+0196;
- `|`.

Under TR39, then, `unbꓲased` has the same skeleton as `unbIased`, and the engine rejects
`unbIased`. Repair 4's readings take ASCII `I` as `l` (so `faiI` is rejected). No reading takes
an l-prototype character as `i`.

`att/i_as_l.py` took the 32 listed words that contain `i`. At each `i` it placed each of the
114 sources, after asserting that the ASCII-`I` control spelling is rejected. Result:
**4,674 texts, 2,803 accepted.** Examples, each `None`:

- `unbꓲased`, `faꓲl`, `certꓲfꓲed` (Lisu I);
- `faӀl`, `unbӀased`, `verdӀct` (palochka);
- `faⲒl`, `faᛁl`, `faƖl`.

The controls `unbIased` and `faIl` give `free_text_verdict_word`. Repair 4 now rejects lens-4's
own literal `faiƖ` (`Ɩ` in the `l` position). In the `i` position, `faƖl` is accepted. The same
texts are accepted at `23f3d9f`.

Repro:
`python -c "from proofpack.narrate.checker import free_text_reason as f;print([f(t) for t in ('unb\ua4f2ased','fa\u04c0l','verd\u04c0ct','unbIased','faIl')])"`
prints `[None, None, None, 'free_text_verdict_word', 'free_text_verdict_word']`.

### B3 - TR39 is applied before decomposition: a precomposed letter whose base TR39 lists is accepted, while its decomposed spelling is rejected

`_tr39_mapped` looks each raw character up in the TR39 map, applies NFKC, then looks each
character up again. `normalise_free_text` decomposes (NFD) and drops marks later, but it applies
only the hand maps. A precomposed character that TR39 does not list therefore keeps its
non-Latin base in every reading, although TR39 lists that base. Examples:

- Cyrillic `ѓ` U+0453 decomposes to `г` + acute, and TR39 maps `г` to `r`.
- `ќ` U+045C decomposes to `к` + acute.
- `ǿ` U+01FF decomposes to `ø` + acute, and TR39 maps `ø` to `o̸`.
- Greek `ή` U+03AE decomposes to `η` + tonos, and TR39 maps `η` to `n`.

`att/precomposed.py` sweeps every character from U+0080 to U+2FFFF whose NFD base is a TR39
source that is not hand-mapped: **3,084 texts, 1,550 accepted.** Many are Greek capitals with
iota subscripts. The clear lower-case cases, each `None`:

- `appѓoved` and `ceѓtified` (certification words);
- `oќ`;
- `apprǿval`;
- `certificatioή`.

The same words typed decomposed (`appг\u0301oved`, `ceг\u0301tified`) give
`free_text_certification_word` at `375719c`. At `23f3d9f`, `appѓoved` gives `None`.

Repro:
`python -c "from proofpack.narrate.checker import free_text_reason as f;print([f(t) for t in ('app\u0453oved','ce\u0453tified','o\u045c','app\u0433\u0301oved')])"`
prints `[None, None, None, 'free_text_certification_word']`.

### B4 - C0 control characters in customer text are written raw into T8.html (NUL, SOH, ESC), through the CLI

I wrote a criteria.yaml whose model name is the double-quoted YAML scalar
`"Tri\0age \x01\x1b[31m"`, with YAML escapes rather than raw bytes, and ran it with a licence
and `--offline` (`att/nul_cli.py`). Result:

- `rc 0`;
- `run.json` `declarations.model.name` is `'Tri\x00age \x01\x1b[31m'`;
- `T8.html` holds `b'\x00'` 4 times, `b'\x01'` 4 times and `b'\x1b'` 4 times: the three page
  headers (`<span class="customer-text">Tri\x00age ...`) and the manifest's Model row.

Through the assembler, the same NUL reaches the page from the version, the author and the
justification (`att/nul.py`: 4, 4, 1 and 1 bytes). The page writes U+202E as `&#x202e;`, and
`test_html_injection_in_a_justification_and_a_level_label_is_escaped` asserts that byte check.
C0 controls are not escaped or refused. The bytes are also present at `23f3d9f` (5 per field
there, because the `<title>` carried the name), so this is E8's renderer, not repair 4.

Lens 3 reported "no NUL byte". Its NUL payload was a raw byte, and a raw NUL in the YAML stream
halts H08 (`ReaderError`), which I reproduced. The YAML escape `\0` is not a raw NUL and passes.

I grade this a blocker under this lens's rule ("an unescaped injection"). A NUL or ESC in a
regulator-facing HTML file can truncate or recolour what a C-string or terminal consumer
shows. Browsers substitute U+FFFD. If Josh reads the rule as markup injection only, this is
record-and-carry.

Repro (Python, in the repository): write `criteria.yaml` with
`name: "Tri\0age \x01\x1b[31m"` and run `python -m proofpack.cli run --input <csv> --criteria
criteria.yaml --out pack --offline` with a licence. Then
`python -c "b=open('pack/T8.html','rb').read();print(b.count(b'\x00'),b.count(b'\x1b'))"`
prints `4 4`.

## Non-blocking (record and carry)

1. **Sentence violations in the shipped handoff and note** (each falsified above):
   - `handoffs/2026-09-23_E_r4.md` table, FA-B4 row: "52,694 single-letter TR39 substitutions
     into the listed words: 21,948 accepted at `23f3d9f`, **0 now**". The note restricts the
     figure to sources "whose target is one ASCII letter". The handoff sentence carries no such
     restriction. B1 feeds 826 accepted single-letter substitutions by TR39-listed characters.
   - The same handoff, carried item 2: "**Look-alikes outside TR39 18.0.0 and the hand maps.**
     155 ... accepted". This places the accepted remainder outside TR39. B1-B3's characters are
     all TR39 sources, or bases of TR39 sources.
   - "`ruff format --check`: `159 files already formatted`" (the handoff and the note). I
     measured `160 files already formatted` in the main tree and in `wt`, both at `375719c`,
     with the main tree clean.
2. **`unmet` stays rejected.** The orchestrator named `unmet` among ordinary clinical prose
   that must stay accepted. The repair kept it in `VERDICT_WORDS` and recorded that choice in
   the test docstring and the note. `An unmet clinical need.` gives `free_text_verdict_word`.
   That is Josh's decision to confirm.
3. **DEC-62 and the `<title>`.** DEC-62 names the `<title>` among the places to mark as
   customer text. A title cannot hold an element, so the repair removed the model name and
   version from it: `<title>T8 · ProofPack v0.1.0.dev1 · run test-onl</title>`. This is
   reasonable, but it is not the decision as written, and Josh should confirm it.
4. **My mutants** (`att/my_mutants.py`, `-m day8`, 12 planted in `mut`, tree clean afterwards).
   Killed: 6. Survived, with the literal each lets through:
   - `fairness_auroc_gap_path_dropped` (the `auroc_gap` entry removed from
     `metric_ref_pointers`). **Not equivalent:** with fairness `criterion_of_interest:
     auroc_gap`, T8 prints `—` beside `criterion not met`, where `375719c` prints
     `+0.079 [−0.002, +0.160]`. The engine's own claim `CL-0062` is also rejected
     `status_recomputation_mismatch`. No day-8 test feeds an `auroc_gap` criterion row. This
     would reopen FA-B1's dash-beside-a-status shape.
   - `tr39_rn_both_dropped`. **Not equivalent:** `ՠeets` (U+0560, TR39 target `rn`) is
     rejected only by readings 5 and 6. With the mutant, it would be accepted.
   - `ingest_dec61_call_dropped`. Equivalent on `run`, because `overall_block` halts the same
     run. On `compare`, which ingests only, `ingest` is the only guard: at `375719c`,
     `proofpack compare` on a `y_pred`-only table with two operating points prints
     `HALT H08 ...` and exits 3. The repair note says this call is not pinned.
   - `tr39_first_pass_dropped` and `tr39_second_pass_dropped`. 70 and 62 single characters,
     respectively, normalise differently without the pass (for example `ſ`, `Ⅰ`, `ʱ`, `ᵚ`). I
     found no listed word that depends only on those characters.
   - `ambiguous_ignored`. Equivalent: no two Numbers produce the same dotted path, because
     metric names hold no dot and each prefix is fixed.
5. **The TR39 regeneration test is skipped wherever `../workflows/data/confusables-18.0.0.txt`
   is absent.** That covers CI and any clone of the public repository. In `wt`, the full suite
   gives `1145 passed, 2 skipped` against the main tree's `1146 passed, 1 skipped`. With
   `PROOFPACK_TR39_FULL` set, `tests/test_e8_repair4.py` gives `18 passed`, and
   `scripts/tr39_subset.py ... --check` prints `vendored subset matches`.
6. **Carried and still reproducing:**
   - `ninety`, `Stage IV.` and `See &sect; eight.` are accepted (needs-from-Josh 2);
   - the lens-2 single-field sweep gives `mutations: 8988 accepted: 11` (4 `CALIB_HIERARCHY`
     `metric_id`, 4 `CRITERION_STATUS` `template_id`, 3 `FAIRNESS_GAP` `metric_id`);
   - derived words (`unbiasedness`, `safely`, `approvals` ...) are accepted;
   - a run with no licence file is watermarked `LICENCE EXPIRED - not for submission`;
   - section 7 prints the three status words on a document with no criteria;
   - T8 prints no calibration section, so `calibration_suppressed_reason` does not reach the
     page (carried to E9, repair-4 carried item 4).

## What I could not break (evidence)

- **Suite, markers and lint** (`wt`, Git Bash).
  - Full suite: `1145 passed, 2 skipped, 1 xfailed in 138.16s`. The second skip is the TR39
    regeneration test (item 5).
  - Markers: `day8` `357 passed, 1 skipped` (PowerShell 5.1 in `ro`: the same), `day7` 139,
    `day6` 285, `day5` 54, `day4` 182, `day3` `29 passed, 1 xfailed`, `day2` 40, `day1`
    `59 passed, 1 skipped`, `ap2` 88. Days 1-7 equal lens 4's counts.
  - `ruff check`: `All checks passed!`. `ruff format --check`: `160 files already formatted`.
  - `git diff 23f3d9f 375719c -- src/proofpack/stats src/proofpack/criteria.py
    src/proofpack/cli.py src/proofpack/errors.py pyproject.toml uv.lock
    schema/egress_schema.json src/proofpack/render/format.py src/proofpack/io/declare.py` is
    empty. The `io/schema.py` hunk is docstring only.
- **Committed sweep, the 14 repair-4 mutants** (`--marker day8 --only ...` in `wt`):
  `14 planted, 14 killed, 0 survived; 249 s`.
- **Pre-fix.** I copied `test_e8_repair4.py`, `test_claims.py`, corpus `141`-`146` and the
  golden into `wt0` at `23f3d9f`. With `PROOFPACK_TR39_FULL` set: `20 failed, 183 passed`. The
  five passing repair-4 tests are the five the note declares as guards.
- **The overall block (a statistical gate; DEC-61)**, re-derived with my own numpy
  (`att/overall.py`):
  - Clustered, 300 rows in 100 cases, seed 777: my two-by-two `{tp 80, fn 15, fp 48, tn 157}`
    equals the engine's. Sensitivity, specificity, PPV and NPV deviate from my `k/n` by `0.0`.
    Each carries the same `(k, n)`, `cluster_bootstrap_percentile` and
    `wilson_refused_clustered`.
  - `proportion_ci` on the same rows, ids, seed, B and cell key gives an interval equal to the
    block's on all four. Youden, balanced accuracy, LR+, LR-, DOR, F1 and MCC each carry
    `clustered_data_analytic_ci_invalid` with `ci (None, None)` and method `none`.
  - A one-stratum subgroup on the same rows gives equal estimates. The intervals differ by
    0.0026 to 0.0181, because the subgroup cell draws its own bootstrap stream (the
    `overall_block` docstring says so).
  - One cluster gives `insufficient_clusters` and no interval. Two clusters give
    `[0.8367, 0.8478]` with `not_evaluable_shown_for_transparency`. Every row as its own cluster
    gives `[0.7579, 0.9158]`.
  - `y_pred`-only, 200 rows: the two-by-two equals my count on the normal table, on one class
    (sensitivity `zero_denominator`), on `y_pred` all `1`, and on integer `y_pred`.
  - DEC-61:
    - two operating points at the same threshold give `HALT H08 ... (a, b)`;
    - two with the same id give H08 `operating point ids are not unique`;
    - one operating point runs;
    - through the CLI, `op_lo` 0.1 / `op_hi` 0.9 on 300 rows give `rc 3`, no directory and
      the named detail;
    - a mapped score column that is entirely blank beside a `y_pred`, with two operating
      points, gives `HALT H06: no analysable rows after exclusions`.
  - Lens 4's `a4_clu.py` re-run: each clustered `y_pred`-only case equals its own count; a
    blank `case_id` halts S05.
- **FA-B1 (lookup, not split).** Lens 4's `a2_dotted.py` through the CLI:
  - `t0.5` gives `85/101 (84.2%) [75.8, 90.0]`;
  - `[0]` gives `29/101 (28.7%) [20.8, 38.2]`;
  - `a[0` gives `rc 0` and its own cell;
  - claim rejections `[]` in each.

  My own 23 cells, re-derived with a `Decimal` half-even formatter from the Number (with tier
  superscripts), cover operating points `0`, `[0]`, `t0.5`, `a.b` and `x]y`, four proportions
  each, plus a `level: *` row (`att/cells.py`): **0 mismatches**, 0 claim rejections. Lens 3's
  `c_renderer.py` C9 gives 22 cells and 0 mismatches. `c2_render.py` P2 gives 60 Wilson cells,
  with a worst deviation of `2.22e-16`.
- **FA-B3.**
  - `y_pred`-only on 200 rows: 59 claims, no `CALIB_NA`, 0 rejections (60 claims with
    `CALIB_NA` at `23f3d9f`).
  - `logit`: 60 claims with `CALIB_NA`.
  - Lens 4's `b5_calibna.py` gives `CALIB_NA claims []`.
- **DEC-62.**
  - The synthetic criteria and fairness document with model `Safe`, version `verdict`, operating
    points `pass` and `fail`, and prevalence and reference-standard labels `consistent` and
    `acceptable`: 0 forbidden-word hits outside `.customer-text` and the disclaimer.
  - Sex level `unbiased` and site level `pass`: 0 outside, 5 inside.
  - Ten payloads in model name, version and operating-point id: no raw `<script>`, no `<img`,
    no `49`, no raw U+202E, and 3 `span.customer-text` headers each. The NUL is B4.
- **The checker.**
  - Lens 2's named cases and structural cases are each rejected with the expected code: list
    target, trailing and double slash, `met `, `MET`, template case, metric mismatch, duplicate
    difference refs, comparator mismatch, `guidance` key, and fullwidth or lower-case ids.
  - `swaps: 42849 accepted: 0`.
  - Lens 4's `b3_homo.py`: `ACCEPTED 2 of 37` (`үes`, `ᎠᎪᎪᎠ`; neither spells a listed word).
  - My 27 new free_text cases: 15 rejected, including
    - soft hyphen, all-Cyrillic `pass`, mathematical monospace, fullwidth;
    - `wełł calibrated`, em space and newline in `well calibrated`, non-breaking-hyphen
      `FDA‑cleared`;
    - ZWSP, CGJ and VS16 inside a word, the `fi` ligature, small-capital `oᴋ`;
    - `unmet` (item 2).

    12 accepted: B1-B3's literals and the three carried ones.
- **False positives of the new readings**, `375719c` against `23f3d9f`:
  - 36,038 word forms (lower, upper, title and as written) from `spec/`, the engine handoffs,
    the README and the site sources: 0 newly rejected, 0 newly accepted.
  - 21,971 sentences from the handoffs, site sources, plan and briefs, with digits, `%`, `§` and
    `‰` removed: 12 newly rejected, each a lens literal quoted in a handoff (`faił`, `ꓑass`,
    `well calibratedness` ...). There are 0 others.
- **Renderer** (lens 3's `c_renderer.py` re-run):
  - 0 `@import`, `url(`, `<link`, `<script`, `http:` or `https:` on the page;
  - 19 hex colours and 7 px values, all from `tokens.json`;
  - footers 3/3/3 on 0, 1 and 40 rows, and `render_pages` 0/1/5 giving 0/1/5 footers;
  - `[unverified]` 7 times;
  - the draft label on 14 AI-DSF mentions and on the three structured `guidance_refs`. The
    four unlabelled mentions are the PCCP guidance, which is final, and the disclaimer
    sentence, which itself reads "(January 2025), it is a draft, not for implementation".
  - Watermarks `TRIAL`, `LICENCE EXPIRED - not for submission` and `NO LICENCE - not for
    submission`: 4 tags each;
  - the same document rendered twice is identical, and the golden is equal (40,030 bytes).
- **Wiring** (lens 3's `d_wiring.py`, `d3_cli.py`):
  - valid licence: `T8.html` is 40,375 bytes, with no CRLF and no BOM, and `run.json` validates
    (70 claims, 0 rejections);
  - grace: HTML with the watermark 7 times; expired past grace: `rc 4`, JSON only; no licence
    file: `rc 4`;
  - `--templates T1`: `rc 0` and the typed line; `docx`, `pdf,json` and `T9`: `rc 5`, no
    directory;
  - `--offline --format json,html` with every socket entry point raising: `rc 0`, 0 calls;
  - two runs: claims, rejections, `guidance_refs` and `criteria_results` are equal.
- **Packaging.**
  - With jinja2, markupsafe, scipy, cryptography, statsmodels and sklearn hidden, all eight
    modules import, and `environment()` raises `RendererUnavailable`.
  - `uv build` gives a wheel holding `proofpack/narrate/tr39_confusables.py`, the three
    templates and `_schema/tokens.json`, with `Requires-Dist: jinja2>=3.1`.
  - In a fresh venv (no `.pth`, `PYTHONNOUSERSITE=1`), `proofpack.__file__` is inside the venv,
    and the TR39 table has 1,905 entries.
  - The lock names jinja2 3.1.6. `uv lock --check --offline` gives rc 0. `ci.yml` runs
    `uv sync --all-groups --locked` 3 times. The wheel test gives `13 passed`.
- **The vendored data.** From the full file, measured independently:
  - SHA-256 `6ed3ee96...5b92`, 763,128 bytes, 6,712 entries, every source a single character;
  - 1,661 targets of ASCII letters only, 1,905 with marks stripped, and 1,451 targets that are
    a single ASCII letter;
  - the header's Version, Date and three notice lines as the module carries them;
  - the five corpus rules' TR39 targets (U+0399 `l`, U+A4D1 `P`, U+2C9F `o`, U+FF29 `l`, U+007C
    `l`) and the `_HOMOGLYPHS_R3` comment's five keys, all present in the file.

  The `templates.py` list of skeletons that differ from D4 section 8 matches my comparison
  exactly: `FLOW_COUNTS`, `CRITERION_STATUS` and `KS_RESULT`.

## What I could not check

- Whether any listed word can be spelled only through the 70 and 62 characters that the two
  `_tr39_mapped` passes handle (item 4). I did not enumerate multi-character combinations.
- A browser rendering of the NUL and ESC bytes (B4). I read the bytes only.
- CI on the reference platform (the engine is not pushed); a plain-CLI run with a real licence
  (there is no signing key).
- The full Unicode License v3 text (not fetched; the repair's needs-from-Josh 1).

## Sentences I refused to write

- "free_text now covers the TR39 confusables." Written instead: the vendored subset's filter,
  B1-B3's counts, and 36,038 word forms with 0 new rejections.
- "The overall block is correct." Written instead: the fixtures fed and their deviations.
- "DEC-61 closes the y_pred-only case." Written instead: the tables fed and the halts.
- "The renderer escapes every injection." Written instead: the payloads fed, the bytes counted,
  and B4.

## Re-run these

```bash
cd C:/Users/joshs/GPS/ProofPack/proofpack
git worktree add --detach <path> 375719c
PYTHONPATH=<path>/src python -c "import proofpack;print(proofpack.__file__)"   # must print <path>
S=<scratchpad>/lens-E8-r5-fresh-attack/att
PYTHONPATH=<path>/src PYTHONIOENCODING=utf-8 python $S/chain_sweep.py   # B1: texts 1264 accepted 826
PYTHONPATH=<path>/src PYTHONIOENCODING=utf-8 python $S/i_as_l.py        # B2: 4674 / 2803
PYTHONPATH=<path>/src PYTHONIOENCODING=utf-8 python $S/precomposed.py   # B3: 3084 / 1550
LENS_WT=<path> PYTHONPATH=<path>/src PYTHONIOENCODING=utf-8 python $S/nul_cli.py      # B4: 4 NUL, 4 SOH, 4 ESC
LENS_WT=<path> PYTHONPATH=<path>/src PYTHONIOENCODING=utf-8 python $S/corpus_new.py   # accepted 12
git -C C:/Users/joshs/GPS/ProofPack/proofpack worktree remove --force <path>
```

## What the repair needs

- **B1:** close the TR39 map over its own targets. Map a source whose target is a Latin
  prototype to the letter that prototype reads as, for example `к` to `ĸ` to `k` and `т` to `ᴛ`
  to `t`. Alternatively, keep entries whose target is any Latin letter, and let the hand maps
  finish the chain. Pin `oк`, `мeets` and `cerтified`.
- **B2:** add a reading that takes every character whose TR39 target is `l` as `i` as well (the
  inverse of the ASCII-`I` reading). Pin `unbꓲased` and `faӀl`, and run the prose check again.
- **B3:** apply the TR39 map after NFD too, or map each character's NFD base. Pin `appѓoved` and
  `oќ`.
- **B4:** refuse C0 and C1 controls in customer strings at declaration, or escape them at
  render. Assert the page's bytes, as the U+202E test does.
- The two non-equivalent survivors: an `auroc_gap` fairness-criterion row on T8, and `ՠeets`.
