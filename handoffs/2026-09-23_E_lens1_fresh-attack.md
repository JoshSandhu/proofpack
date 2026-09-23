# Lens 1 (fresh attack) - build day 9, lane E, at `71b00d2` - 2026-09-23

**Verdict: FAIL.** Three blockers. Each is on a page rendered from a real `proofpack run` or from the sample-pack script:

- **B1.** Forbidden words reach the rendered pages outside every exempt scope.
- **B2.** On a clustered run, four fixed captions and one T7 sentence name interval methods the run did not use.
- **B3.** The figures plot the `est` of a Number that carries a typed reason, as a bare estimate.

The suite, the markers, the builder's sweep and my re-derivations of every table cell and sentence slot all come out as the note says. The blockers are on paths no E9 test feeds:

- T7's conventions paragraphs, read by any word grep;
- a clustered T1;
- a derived threshold;
- a typed-reason Number that carries `est`.

Worktrees were under `scratchpad/lens-E9-r1-fresh-attack/`; all three are now removed:

- `wt71` at `71b00d2`: suite, markers, lint, probes and the builder's sweep;
- `wteda` at `eda8a35`: the day-9 tests run against the old source;
- `wtmut` at `71b00d2`: my own mutants.

In each worktree, `PYTHONPATH=<wt>/src python -c "import proofpack;print(proofpack.__file__)"` printed that worktree's `src\proofpack\__init__.py` before I trusted any number. Every run outside pytest carried `--offline`. All figures below were measured in Git Bash in this session. I did not use PowerShell.

## Blockers

### B1 - forbidden words on T7 (every run, including the public sample pack) and on T1 (derived threshold)

`narrate/checker.py::VERDICT_WORDS` holds `verdict`, `effective` and `biased`. The task's rule is that no rendered page carries them except where a criteria table prints the three status words. The brief's acceptance line is "forbidden grep = 0".

I used the builder's own page grep: `text_nodes`, `words` and `FORBIDDEN_ON_PAGE` from `tests/test_render_t8.py`, with the T1 test's exemptions (`.status`, `.disclaimer`, `.customer-text`). It returns:

- **T7, i.i.d. run: 4 text nodes with `verdict`.** They come from `design/conventions_T7.md`, which T7 inserts verbatim for the first time today:
  - "z and the two-sided p are detail, never a verdict";
  - "Nothing here is a verdict: no target is compared to and no word describes the calibration";
  - the test id `test_no_verdict_word_appears_in_any_key_or_engine_string_of_the_day6_output`;
  - "for the verdict words the brief names".
- **T7, clustered run: 5 text nodes.** The four above, plus `effective` in "an effective-units floor per cell".
- **T1 with `operating_points[].provenance: derived_from_this_dataset`: 1 text node.** The T1-7 caption, in `<span class="provenance">`, reads "derived from this dataset and is therefore optimistically biased". This is D4's mandated THRESH_PROVENANCE wording. The builder exempted it in the skeleton grep only, and no page test feeds a derived threshold.
- **The public `/sample-pack`.** `scripts/build_sample_pack.py --out sp1` gives an `sp1/T7.html` that carries "a verdict." / "a verdict:" / "the verdict".

At `eda8a35` no rendered page carried any of these. T8's grep over my i.i.d. T8 finds none.

Repro, from `tests/` with `PYTHONPATH` forced: `render_t7(assemble(cohort_with_a_thirty_row_site(), make_criteria(criteria=CRITERIA, fairness=FAIRNESS)))`, then for each `(text, scope)` in `text_nodes(page)`, `words(text) & FORBIDDEN_ON_PAGE`. The result is 4 hits in the `conventions` scope. For T1, set every `operating_points[i].provenance = "derived_from_this_dataset"` and call `render_t1`; the result is 1 hit, `['biased']`.

"optimistically biased" is D4 section 2 row 7 verbatim, so that half needs Josh's reading: exempt it in `.provenance`, or reword D4. The T7 half is vendor prose that can be reworded.

### B2 - clustered run: captions and T7 name methods the run did not use

D4 section 1.2 says the "CI method printed once per table in the caption". D4 section 5.3b says: "Newcombe 10 (unpaired difference) or cluster bootstrap; Δ AUROC: unpaired DeLong / cluster bootstrap".

My run: `make_cohort(n=400, with_case_id=True)`, `case_id = c{i//2}`, `clustering: {unit: case_id}`, `proofpack run --offline --templates T1,T7,T8`, exit 0. In that `run.json`:

- every subgroup Se/Sp/PPV/NPV/accuracy/AUROC Number is `cluster_bootstrap_percentile` (9 of each) or `none` with `cases_span_both_groups` (15 of each);
- every `diff_vs_reference` is `none` / `cases_span_both_groups`;
- the decile bins are `cluster_bootstrap_percentile` (9) and `none` / `boundary_estimate` (bin 1).

The page prints:

- **T1-10 caption, three times:** "Wilson score for proportions, DeLong for AUROC". This is fixed text in `templates/T1.html`, and T1-10 has no Method column.
- **T1-11 caption, three times:** "(Newcombe method 10 for proportions in percentage points, unpaired DeLong for AUROC; ...)". This is fixed text too.
- **F4 caption:** "bar interval: no interval method". `figures.f4_calibration` reads only `bins[0]`'s method, while the 9 bars it draws are cluster-bootstrap intervals.
- **T7 section 4, `X1_SENTENCE`:** "both use Newcombe (1998) method 10 for proportions and unpaired DeLong for AUROC", on a page whose own methods table lists only `cluster_bootstrap_percentile` (95) and `none` (310).

On the i.i.d. run the captions happen to be true: `wilson`, `newcombe10`, `delong_logit` / `delong_wald`.

My mutant `f4_caption_last_bin` (read `bins[-1]` instead of `bins[0]`) survives both `-m day9` (131 passed) and `-m day8` (467 passed, 1 skipped).

Repro: the run above, then `grep -o "Wilson score for proportions, DeLong for AUROC\|bar interval: [^;]*" pack/T1.html`.

### B3 - a typed-reason Number plotted as a bare estimate

- **F4 on the clustered run above.** Decile bin 1's rendered Number is `{"est": 0.0, "ci_lo": null, "ci_hi": null, "not_estimable_reason": "boundary_estimate", "method": "none"}`. The decile table prints `n.e. (boundary_estimate)`. F4 draws 10 `data-role="decile"` points and 9 bars; bin 1's point is at `cx=120.770848 cy=340.0`, which inverts through `data-map` to (0.1057726, 0.0). The difference from `mean_pred` is 1.4e-17 and from `est` is 0. The figure prints no reason for that bin. `f4_calibration` tests `_is_num(obs.get("est"))`, not `fmt.has_interval`.
- **F5 reference line (constructed).** Setting the overall AUROC to `ci_lo/ci_hi None, not_estimable_reason "boundary_estimate", method "none"`, with `est` kept at 0.8353343, still draws `F5-sex-auroc`'s dashed overall line. It inverts to x = 0.8353343290441178. The engine carries `est` beside `boundary_estimate`, as in the decile bin.
- **F2 marker (constructed).** An overall sensitivity with a typed reason still gets its operating-point marker, placed by that Number's `est`.

The binding rule is that a Number with a typed reason prints the reason, never a bare estimate. Repro: the clustered run above, then `re.findall(r'data-role="decile" data-bin="1" cx="([^"]+)" cy="([^"]+)"', T1)`.

## Non-blocking (record-and-carry)

- **N1 (sentence_violation) - T7 prints internal and stale text from `design/conventions_T7.md` on a regulator-facing page and on the public sample pack.** The quotes are:
  - "That is an open decision for Josh (day-5 note) ... Until it is taken, this paragraph is the honest one and T7 should carry it". DEC-18 decided this on 15 September.
  - "the decision whether to add a case-count floor for the calibration route is Josh's (repair round 1 note, needs 1 ...)". DEC-34 decided: no floor.
  - "Whether the few-events tier should ride on those cells too is an open decision (needs-from-Josh in the repair round 2 note)". DEC-35 decided it.
  - Test ids, lens rounds and repair notes are named throughout.

  The conventions intro says "Every number here comes from a committed script's output, named with its version and seed". The same page contradicts it with "Those are the lens's figures from its own script, not re-run here" and "Lens 2 (15 September 2026, FA-B1) measured ... 0.295 ... 0.615", which name no script. "Josh" occurs 2 times in the i.i.d. and sample-pack T7 and 3 times in the clustered T7.
- **N2 (sentence_violation) - `render/t7.py::TOLERANCE_POLICY` (D1 section 9 text) on every T7:** "Same image + same inputs → identical manifest hash and byte-identical JSON (F17)". I made two CLI runs of the same input. They differ at `/manifest/run_id` and `/manifest/duration_s`; the bytes are equal only after masking those and `started`. The manifest carries `run_id`, so its hash cannot be identical.
- **N3 (sentence_violation, pre-existing, now also on T1 page 2) - long-form item 6:** "the choice of Wilson (no continuity correction) with Clopper-Pearson alongside at k = 0 or k = n". The y_pred-only T1 prints `12/12 (100.0%) [75.8, 100.0]` with no CP, and T7's own `wilson` row says CP is not printed (row 49; builder need 2).
- **N4 - surviving lens mutants.** I planted 17 in `wtmut`, with `-m day9` first and `-m day8` on a survivor. 9 were killed and 8 survived:

  | Mutant | Outcome |
  |---|---|
  | `f4_caption_last_bin` | Non-equivalent; see B2 |
  | `ne_tiers_dropped` | `format.estimate` drops the tier superscript on `n.e. (...)`. Non-equivalent when a typed-reason Number carries a tier flag, against DEC-08 "annotate, never omit" |
  | `f5_ref_line_other_op` | F5's reference line comes from the last operating point while the points come from the first. Non-equivalent with two operating points; no figure test has two |
  | `prev_row_label_pi_dropped` | "PPV at π = (label)" loses the declared prevalence |
  | `dev_note_always` | Equivalent while `table1.dev` is always null |
  | `hetero_tests_other_op` | Equivalent on single-operating-point runs |
  | `f5_draws_typed_reason_points` | Equivalent under Number's interval-or-reason invariant |
  | `auroc_phrase_default_logit` | Equivalent on engine inputs |

  The default in `AUROC_METHOD_PHRASE_KEYS.get(method, "iid_wald")` is a silent fallback. An AUROC Number with any method outside the map would print "DeLong, Wald interval".
- **N5 - rounding at exact halves** (E8's documented rule in `format.py`, now visible in T1 prose):
  - claim CL-0037 prints `51/80 (63.7%)`, but 51/80 is 63.75% exactly, and a half-up or half-even hand check gives 63.8;
  - Table T1-3 prints `113 (28.2)` / `81 (20.2)` / `185 (46.2)` where half-up gives 28.3 / 20.3 / 46.3.

  The engine rounds the binary double. Josh should confirm that is the rule a regulator's recomputation will meet.
- **N6 - F5 criterion lines.** A `ci_lower_bound` criterion with value −0.03 is drawn at x = 183.1, left of the plot origin at 190, over the level labels. A criterion scoped to `site = S3` is drawn across every site row.
- **N7 - T1-11's criterion column.** It skips the reference level: C_f1_site row 3 (`site = S1`, the reference) is absent from T1-11 while rows 4 and 5 appear. It is present in section 12.
- **N8 - row 81 exposure grows.** A site level `S3 <b>x</b>​` through the CLI gives exit 0. T1 then carries 11 raw U+2028 and 11 raw U+200B; the `<b>` is escaped 11 times with 0 raw.
- **N9 - FDA AI-DSF named without the map label.** The T1 `<h1>` reads "T1 · FDA AI-DSF performance evidence attachment set" and section 15 has "model cards are not required per draft guidance (Jan 2025), not for implementation". Both are D4 verbatim, not anchors. Every `<a href="#FDA_AIDSF_*">` carries the full label: T1 27 of 27, T7 3 of 3.
- **N10 - T7 section numbering gaps:** i.i.d. prints 1 2 3 4 5 7 8 9 10; clustered 1 2 3 4 5 6 8 9 10; y_pred-only 1 2 3 4 5 8 9 10.
- **N11 - D5 section 3.5 asks for a page counter in the print footer.** T1 has 0 `counter(`.
- **N12 (sentence_violation, minor) - `format.py`'s new comment** "so a sentence and a table state one figure one way". The sentence prints `30/38 (78.9%ᶜ) [66.6, 89.5]` where the table prints `30/38 (78.9%) [66.6, 89.5]ᶜ`. The digits agree; the annotation moves.
- **N13 - the IPA footnote** "The IPA row's tier superscript is ..." prints on the clustered run, where the IPA row carries no superscript.
- **N14 - the exit-4 line "Next step: ... then run again for T8.html"** prints unchanged when `--templates T1,T7` was asked for.
- **N15 - T7 prints URLs in citation text:** `http://www.stats.org.uk/...Newcombe1998.pdf`, `https://link.springer.com/...`. They are text, not resources. No `@import`, `url(`, `<link` or `<script` appears in any output.

## What I could not break (with figures)

- **Suite and lint** (wt71): `1387 passed, 1 skipped, 1 xfailed in 130.27s`. By marker: `-m day9` 131 passed, `day8` 468, `day7` 139, `day6` 285, `day5` 54, all equal to the note's counts. `ruff check`: `All checks passed!`; `ruff format --check`: `185 files already formatted`.
- **Old source:** the day-9 tests at `eda8a35`, with 71b00d2's `tests/` and `synthetic.py` overlaid, give 16 collection errors and `test_sweep_day9.py` 3 failed. No day-9 test passes at `eda8a35`.
- **Builder's sweep** `--marker day9` (wt71): `15 planted, 15 killed, 0 survived; 131 s`.
- **No statistics changed:** `git diff --stat eda8a35 71b00d2` over `stats/`, `gates.py`, `criteria.py`, `egress/`, `narrate/checker.py`, `narrate/claims.py`, `io/` and `design/tokens.json` is empty. `format.py` has additions only.
- **Table cells:** my own D4 section 1.2 formatter works from `Decimal(repr(x))` with half-even and never calls `render.format`. It re-derived every `data-ref` cell against its `run.json` pointer: i.i.d. 142 cells, clustered 136, y_pred 117, comparator 142. The only mismatch per run is `/overall/threshold_free/auprc`, whose printed text "not computed in this run (v1.1)" is intended; the other 141 / 135 / 116 / 141 matched character for character.
- **Sentence slots:** each claim sentence was re-derived slot by slot (k/n, est, bounds, difference, facet order in CALIB_HIERARCHY and FAIRNESS_GAP, criterion observed value and status word). Checks per run: i.i.d. 160, clustered 138, y_pred 142, comparator 158. The one mismatch per run is N5's 51/80 tie.
- **Digit runs:** every digit run in the visible text of i.i.d. and clustered T1 traces to a `run.json` value or to a fixed-text reference: 2007, 510(k), 21 CFR 807.92, SHA-256, GB SI 2024/1368, 5.10. This check is weak: small integers match by coincidence.
- **Figures** (inverted through `data-map`):
  - F2: 401 vertices against 401 `roc` rows, maximum deviation 1.11e-16; op1 marker 2.78e-17.
  - F4 (i.i.d.): 10 points, 10 bars, 10 strip rects; deviation at most 1.4e-17.
  - Across F2-F5 there is no `<rect>` outside `fig-hist`, and every `fill` is `none`.
  - 40 extra levels give 43 F5 rows and a 1198-unit viewBox.
- **Injection:** I put `<img src=x onerror=alert(1)>{{ 7*7 }}{% raw %}<script>alert(2)</script>` + U+202E U+2028 U+200B, plus 10,000 `A`, into the model name, version, operating-point id, a site level, criterion ids, author, date, justification, reference-standard description, subgroup sources, fairness fields, and threshold source and rule. Results:
  - T1: 0 raw `<img`, 0 raw `<script`; `{{ 7*7 }}` stays literal 259 times; U+202E only as `&#x202e;` (259); the 10k string is kept 12 times. `html.parser` finds no attribute named `on*` in T1, T7 or T8.
  - A planted `[unverified] planted-customer` survives 8 times in T1 and 14 in T8; `[unverified] planted-source` 3 times each.
  - The T7 planted-citation test also passes.
- **Watermarks and furniture:**
  - trial: `TRIAL` on all 9 / 3 / 3 pages of T1 / T7 / T8, with a footer on each;
  - grace: `LICENCE EXPIRED - not for submission` on every page;
  - expired past grace, no licence file, and a tampered signature (`models: 99`): exit 4, `run.json` only. Marks: `LICENCE EXPIRED`, `NO LICENCE - not for submission` (DEC-48), and `LICENCE EXPIRED` (a refused file) respectively;
  - sample pack: `SYNTHETIC - illustrative` and `NO LICENCE - not for submission` on every page of all three documents.
- **`--templates`:**
  - `T9` and `T1;T7` give `error: unknown --templates id ...`, exit 5, no traceback;
  - `T1,T1`, ` T1` and `t1` write T1 only;
  - `T1,,T8` writes T1 and T8;
  - `''` writes T8.
- **Offline:** with `socket.socket` and `socket.create_connection` raising, `run --offline --templates T1,T7,T8` exits 0 with 0 socket calls, and the sample-pack script makes 0 socket calls.
- **jinja2 hidden:** with `jinja2` and `markupsafe` imports refused, `import proofpack, proofpack.stats, proofpack.cli, proofpack.run, proofpack.narrate.templates, proofpack.synthetic, proofpack.render.sentences, proofpack.render.figures` all succeed.
- **Determinism:**
  - Sample pack twice: the only differences are `run_id`, `started` and `duration_s` (T8 prints `0.783` / `0.830`).
  - F17: two CLI runs differ at `/manifest/run_id` and `/manifest/duration_s` only; the `run.json` bytes are identical after masking (253,889 each), and T1 and T7 are identical after masking.
- **Timing:** `test_render_timing.py` gives 100,000 rows in 6.42 s for the whole run and 0.40 s for the three renders. T1 is 3,690,190 bytes.
- **r6 re-run:**
  - `e2e_shell` with no licence: exit 4, `253938 bytes 20 keys 70 claims 0 rejections 3 refs [0, 1, 2, 2, 2, 3, 4, 5, None] CRLF 0 BOM False`. The note says 253,937; the byte count moves with the digits of `duration_s`.
  - `html_run.py`: `T8.html bytes 44010`, as the note says.
- **Calibration null:**
  - logit score: `calibration: null - reason score_not_probability`, the F4 omission line, and the CALIB_NA sentence;
  - `lower_is_positive`: the reason and the F4 line;
  - y_pred-only: `no_score_column`, with AUROC `n.e. (not_computed_this_run)` and the F2/F3 no-data lines.
- **Colours and fonts:** every hex colour on T1 appears in `design/tokens.json`. The only `font-family` values are `var(--pp-type-text)` and `var(--pp-type-mono)`.

## What I could not check

- **PowerShell 5.1:** every figure above is Git Bash only.
- **Browser rendering** of the SVG and print CSS: whether `@page { size: var(...) }` applies, and how the fixed footer overlaps content.
- **The day-8 sweep:** not re-run (1,600+ s). The builder's day-9 sweep was re-run.
- **A wheel install into a fresh venv** with the two new `_schema` files.
- **Several operating points and `report_both_ways`:** a real run with two operating points was not made; for B-class figure behaviour I read the code. The same goes for a `report_both_ways` run.
- **Suppressed Numbers with `k`/`n` in a sentence.** A constructed `SUBGROUP_ESTIMATE` would print `k/n (‡)`. `egress.suppress.suppressed_number()` nulls `k` and `n` and `run.json` carries no suppressed Number, so I found no real path.

## Sentences I refused to write

- "T7 is free of forbidden words once the conventions file is reworded": no reworded file was run.
- "The captions are correct on i.i.d. runs": measured on one i.i.d. run and one comparator run only.
- "No other figure plots a typed-reason estimate": F2, F4 and F5 were fed; F3 has no v1 data.
