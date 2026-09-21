"""DEC-12(ii): the mutation sweep as a committed script.

Plants a declared list of mutants - each ``(id, file, regex, replacement, expected count)``
- one at a time into a *copy* of the working tree, runs the named pytest marker there,
and prints killed / survived per mutant. A mutant is **killed** when the marker's tests
fail against it and **survived** when they all pass. A surviving mutant that is not
equivalent (i.e. it changes behaviour) is a coverage gap: close it with a test, or carry
it in the handoff note with the reason.

Why a copy and not a worktree: the sweep must run against the *working tree* (the code
being handed off, committed or not), and a git worktree can only check out a commit. The
copy holds ``src``, ``tests``, ``schema``, ``fixtures``, ``design`` and
``pyproject.toml``; ``PYTHONPATH`` is forced to the copy's ``src`` for every subprocess.
What is inspected before any mutant runs: one ``python -c "import proofpack"``
subprocess with that environment and the copy as its working directory, whose
``proofpack.__file__`` must resolve under the copy's ``src`` or the sweep exits. That is
a check on one import in one subprocess with the same environment the pytest
subprocesses receive; it is not a check inside pytest. Attempts to defeat it recorded by
the day-5 regression lens (2026-09-15, RG-N6): ``PYTHONPATH`` pre-set to the main tree's
``src`` and the working directory set to the main tree - both resolved to the copy,
because ``env_for`` overwrites ``PYTHONPATH`` and ``cwd`` is the copy.

Usage::

    python scripts/mutation_sweep.py --marker day5            # every mutant declared for day 5
    python scripts/mutation_sweep.py --marker day6            # the day-6 A mapper list
    python scripts/mutation_sweep.py --marker day5 --only ref_largest_to_smallest
    python scripts/mutation_sweep.py --list
    python scripts/mutation_sweep.py --marker day5 --fail-on-survivor   # exit 1 if any survive

The round-7 repair of build day 4 ran this by hand as a scratch file; it found that the
two changes that round's commit narrated most prominently were unobservable, which is
why it is a script now (DEC-12, Josh, 13 September 2026).
"""

from __future__ import annotations

import argparse
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
COPIED = ("src", "tests", "schema", "fixtures", "design", "pyproject.toml")
SUBGROUPS = "src/proofpack/stats/subgroups.py"
DISCRIMINATION = "src/proofpack/stats/discrimination.py"
OUTPUT_SCHEMA = "schema/output_schema_v1.json"


@dataclass(frozen=True)
class Mutant:
    id: str
    file: str
    pattern: str
    replacement: str
    count: int = 1  # how many matches the pattern must have (all are replaced)
    what: str = ""  # the behaviour it changes, for the report
    marker: str = "day5"  # the pytest marker whose tests are meant to observe it


#: The day-5 list. Every one changes behaviour; none is intended to be equivalent.
MUTANTS: tuple[Mutant, ...] = (
    Mutant(
        "ref_largest_to_smallest",
        SUBGROUPS,
        r"largest = max\(lv\.n for lv in candidates\)",
        "largest = min(lv.n for lv in candidates)",
        what="reference-level choice: 'largest' picks the smallest level",
    ),
    Mutant(
        "ref_tie_last_in_order",
        SUBGROUPS,
        r"return tied\[0\]\.label,",
        "return tied[-1].label,",
        what="reference tie rule: last in level order instead of first",
    ),
    Mutant(
        "unknown_row_can_be_reference",
        SUBGROUPS,
        r"candidates = \[lv for lv in levels if not lv\.is_unknown\]",
        "candidates = list(levels)",
        what="the Unknown row becomes a candidate reference level",
    ),
    Mutant(
        "complement_excludes_unknown",
        SUBGROUPS,
        r"np\.concatenate\(\[lv\.rows for lv in attr\.levels\]\)\n            if attr\.levels",
        "np.concatenate([lv.rows for lv in attr.levels if not lv.is_unknown])\n"
        "            if attr.levels",
        what="complement definition: the Unknown row is left out of every complement",
    ),
    Mutant(
        "unknown_row_not_marked",
        SUBGROUPS,
        r"levels\.append\(_Level\(attribute, UNKNOWN_LEVEL, unknown_rows, True\)\)",
        "levels.append(_Level(attribute, UNKNOWN_LEVEL, unknown_rows, False))",
        what="Unknown row membership: missing rows form a level not marked is_unknown_row",
    ),
    Mutant(
        "tier_counts_rows_not_units",
        SUBGROUPS,
        r"tier_flags = precision_flags\(n_units, event_units\)",
        "tier_flags = precision_flags(n, events)",
        what="tier thresholds measured in rows instead of resampling units",
    ),
    Mutant(
        "evaluability_ten_to_five",
        SUBGROUPS,
        r"^AUROC_EVALUABLE_CLASS = 10$",
        "AUROC_EVALUABLE_CLASS = 5",
        what="the 10/10 AUROC evaluability rule loosened to 5",
    ),
    Mutant(
        "evaluability_off_by_one",
        SUBGROUPS,
        r"if n_pos < AUROC_EVALUABLE_CLASS:",
        "if n_pos <= AUROC_EVALUABLE_CLASS:",
        what="the 10/10 rule refuses a level with exactly ten positives",
    ),
    Mutant(
        "difference_sign_flipped",
        SUBGROUPS,
        r"number = difference_unpaired\(k1, n1, k2, n2, level\)",
        "number = difference_unpaired(k2, n2, k1, n1, level)",
        what="the sign of a proportion difference (other minus level)",
    ),
    Mutant(
        "holm_no_running_maximum",
        SUBGROUPS,
        r"running = max\(running, min\(1\.0, pvalues\[i\] \* \(m - rank\)\)\)",
        "running = min(1.0, pvalues[i] * (m - rank))",
        what="Holm ordering: the step-down monotonicity is dropped",
    ),
    Mutant(
        "holm_unsorted",
        SUBGROUPS,
        r"order = sorted\(range\(m\), key=lambda i: pvalues\[i\]\)",
        "order = list(range(m))",
        what="Holm ordering: p-values are not sorted before the step-down",
    ),
    Mutant(
        "fpr_gap_sign",
        SUBGROUPS,
        r'"fpr_gap": _mirror_cell\(d\[arrays\.sp_key\]\),',
        '"fpr_gap": d[arrays.sp_key],',
        what="fpr_gap emitted as the specificity difference instead of its mirror",
    ),
    Mutant(
        "clustered_span_refusal_off",
        SUBGROUPS,
        r"if _shared_cases\(ids_a, ids_b\):",
        "if False and _shared_cases(ids_a, ids_b):",
        count=2,
        what="the clustered refusal: cases spanning both sides no longer refuse",
    ),
    Mutant(
        "proportion_cells_lose_cluster_ids",
        SUBGROUPS,
        r"cluster_ids=arrays\.ids_for\(rows\),(\n        level=arrays\.level,\n    \)"
        r"\n\n\ndef _proportion_difference)",
        r"cluster_ids=None,\1",
        what="DEC-10 / X2: proportion cells reach Wilson on clustered rows",
    ),
    Mutant(
        "fisher_branch_removed",
        SUBGROUPS,
        r"if n_levels == 2 and min_expected < fisher_below:",
        "if False:",
        what="Fisher exact never replaces the chi-square",
    ),
    Mutant(
        "selection_rate_label",
        SUBGROUPS,
        r'^SELECTION_RATE_LABEL = "descriptive_not_target"$',
        'SELECTION_RATE_LABEL = "target"',
        what="the selection-rate gap loses its R2 section 4 label",
    ),
    Mutant(
        "undeclared_not_exploratory",
        SUBGROUPS,
        r"if spec is not None else EXPLORATORY\)",
        'if spec is not None else "declared")',
        what="an undeclared attribute is no longer labelled exploratory",
    ),
    Mutant(
        "default_age_bands_changed",
        SUBGROUPS,
        r"\(\(0, 40\), \(40, 65\), \(65, 80\), \(80, 200\)\)",
        "((0, 18), (18, 40), (40, 65), (65, 80), (80, 200))",
        what="the engine-default age bands drift from D1's",
    ),
    Mutant(
        "age_bands_closed_on_the_right",
        SUBGROUPS,
        r"\(a < float\(hi\)\)",
        "(a <= float(hi))",
        what="age banding becomes [lo, hi] instead of [lo, hi)",
    ),
    # ---- day-5 repair round 1: the lens's survivors that this round's tests observe
    Mutant(
        "ppv_indicator_inverted",
        SUBGROUPS,
        r"sel = pred\n        ind = pos\[sel\]",
        "sel = pred\n        ind = ~pos[sel]",
        what="per-level PPV becomes 1 - PPV (regression lens RG-B1)",
    ),
    Mutant(
        "npv_indicator_inverted",
        SUBGROUPS,
        r"sel = ~pred\n        ind = ~pos\[sel\]",
        "sel = ~pred\n        ind = pos[sel]",
        what="per-level NPV becomes 1 - NPV (regression lens RG-B1)",
    ),
    Mutant(
        "accuracy_inverted",
        SUBGROUPS,
        r"ind = pos == pred",
        "ind = pos != pred",
        what="per-level accuracy becomes 1 - accuracy (regression lens RG-B1)",
    ),
    Mutant(
        "ppv_conditioned_on_positives",
        SUBGROUPS,
        r'elif metric == "ppv":\n        sel = pred',
        'elif metric == "ppv":\n        sel = pos',
        what="per-level PPV computed on the reference-positive rows (fresh-attack lens N4)",
    ),
    Mutant(
        "heterogeneity_ignores_the_plan",
        SUBGROUPS,
        r"heterogeneity_footnote\(per_op, clustering_route=arrays\.plan\.route\)",
        'heterogeneity_footnote(per_op, clustering_route="none")',
        what="the chi-square runs on the rows of a clustered table (fresh-attack lens B1)",
    ),
    Mutant(
        "unpaired_delong_renders_with_a_frozen_arm",
        DISCRIMINATION,
        r"if var_a <= 0\.0 or var_b <= 0\.0:",
        "if var_a <= 0.0 and var_b <= 0.0:",
        what="delong_wald rendered when one arm's DeLong variance is zero (fresh-attack lens B2)",
    ),
    Mutant(
        "two_sided_bootstrap_side_b_from_a_fixed_generator",
        SUBGROUPS,
        r"values_b\[b\] = stat_b\(res_b\.draw\(rng\)\)",
        "values_b[b] = stat_b(res_b.draw(np.random.default_rng(b)))",
        what="side b of the two-sided bootstrap is not drawn from the cell's generator (RG-N2)",
    ),
    Mutant(
        "h09_message_names_observed_levels",
        SUBGROUPS,
        r'"subgroup reference_level is not a level of the analysed rows"',
        '"subgroup reference_level is not an observed level"',
        what="the H09 halt on an excluded reference level says it was not observed (FA-N7)",
    ),
    # ---- day-5 repair round 2: lens 2's blocker and the survivors this round's tests observe
    Mutant(
        "two_sided_bootstrap_frozen_side_check_removed",
        SUBGROUPS,
        r"if frozen or lo == hi:",
        "if lo == hi:",
        what="a difference with one side frozen renders the other side's interval (lens 2 FA-B1)",
    ),
    Mutant(
        "two_sided_bootstrap_frozen_check_side_a_only",
        SUBGROUPS,
        r'frozen = _frozen_sides\(\{"a": values_a, "b": values_b\}, level\)',
        'frozen = _frozen_sides({"a": values_a}, level)',
        what="the frozen-side check inspects side a only (lens 2 FA-B1, side b)",
    ),
    Mutant(
        "two_sided_bootstrap_side_b_drawn_before_side_a",
        SUBGROUPS,
        r"values_a\[b\] = stat_a\(res_a\.draw\(rng\)\)\n"
        r"        values_b\[b\] = stat_b\(res_b\.draw\(rng\)\)",
        "values_b[b] = stat_b(res_b.draw(rng))\n        values_a[b] = stat_a(res_a.draw(rng))",
        what="side b consumes the cell's generator before side a (lens 2 FA-N4)",
    ),
    Mutant(
        "clustered_proportion_difference_sign",
        SUBGROUPS,
        r"    d = k1 / n1 - k2 / n2\n    if not arrays\.clustered:",
        "    d = k2 / n2 - k1 / n1\n    if not arrays.clustered:",
        what="the clustered proportion difference estimate is other minus level (lens 2 FA-N6)",
    ),
    Mutant(
        "heterogeneity_clustered_refusal_before_the_level_count",
        SUBGROUPS,
        r"if clustered and len\(counts\) >= 2",
        "if clustered",
        what="fewer than two levels under clustering reports the clustered reason (lens 2 FA-N8)",
    ),
    Mutant(
        "schema_extension_missing_reason",
        OUTPUT_SCHEMA,
        r'"cases_span_both_groups", "insufficient_levels"',
        '"cases_span_both_groups"',
        what="the output schema no longer accepts one of the day-5 typed reasons",
    ),
    Mutant(
        "schema_extension_missing_flag",
        OUTPUT_SCHEMA,
        r'"wilson_refused_clustered", "newcombe_refused_clustered",',
        '"wilson_refused_clustered",',
        what="the output schema no longer accepts the day-5 flag",
    ),
)

MAPPING = "src/proofpack/io/mapping.py"
SCHEMA_IO = "src/proofpack/io/schema.py"
PROFILE = "src/proofpack/io/profile.py"
DECLARE = "src/proofpack/io/declare.py"
CLI = "src/proofpack/cli.py"

#: Day 6 A (the full mapper). Run with ``--marker day6``.
MUTANTS_DAY6_A: tuple[Mutant, ...] = (
    Mutant(
        "synonym_label_to_y_pred",
        MAPPING,
        r'^    "label": "y_true",$',
        '    "label": "y_pred",',
        count=2,  # the synonym table and the partial-token table both carry the row
        marker="day6",
        what="synonym lookup: 'label' resolves to y_pred",
    ),
    Mutant(
        "unit_interval_upper_bound_100",
        PROFILE,
        r"lo >= 0\.0 and hi <= 1\.0",
        "lo >= 0.0 and hi <= 100.0",
        marker="day6",
        what="the [0, 1] score rule accepts values up to 100",
    ),
    Mutant(
        "suppression_k_nine",
        PROFILE,
        r"^SUPPRESSION_K = 10$",
        "SUPPRESSION_K = 9",
        marker="day6",
        what="the suppression floor drops to 9 (a count of 9 is shown)",
    ),
    Mutant(
        "sample_rows_10001",
        PROFILE,
        r"^SAMPLE_ROWS = 10_000$",
        "SAMPLE_ROWS = 10_001",
        marker="day6",
        what="the type-inference sample reads row 10,001",
    ),
    Mutant(
        "every_role_high_becomes_any",
        MAPPING,
        r'return all\(r\.confidence == "high" for r in self\.roles if r\.role is not None\)',
        'return any(r.confidence == "high" for r in self.roles if r.role is not None)',
        marker="day6",
        what="the every-role-high rule passes when any role is high",
    ),
    Mutant(
        "hash_comparison_always_true",
        MAPPING,
        r"if prior is not None and prior\.header_set_sha256 == current:",
        "if prior is not None:",
        marker="day6",
        what="a prior mapping.json is accepted whatever its header-set hash",
    ),
    Mutant(
        "composite_key_needs_three",
        MAPPING,
        r"if len\(case_claims\) >= 2:",
        "if len(case_claims) >= 3:",
        marker="day6",
        what="two headers resolving to case_id no longer halt E01",
    ),
    Mutant(
        "composite_declaration_needs_three",
        DECLARE,
        r"    if n >= 2:\n        raise HaltError\(",
        "    if n >= 3:\n        raise HaltError(",
        marker="day6",
        what="a two-column clustering.unit no longer halts E01",
    ),
    Mutant(
        "tty_check_always_true",
        CLI,
        r"            if not tty:\n                raise HaltError\(",
        "            if False:\n                raise HaltError(",
        marker="day6",
        what="a non-terminal stdin is prompted instead of halting H07",
    ),
    Mutant(
        "binary_set_yes_no_removed",
        MAPPING,
        r'^    frozenset\(\{"yes", "no"\}\),$',
        "",
        marker="day6",
        what="yes/no columns are no longer y_true candidates",
    ),
    Mutant(
        "free_text_threshold_never",
        PROFILE,
        r"^FREE_TEXT_UNIQUE_SHARE = 0\.5$",
        "FREE_TEXT_UNIQUE_SHARE = 5.0",
        marker="day6",
        what="a free-text column lists its values",
    ),
    Mutant(
        "date_values_not_event_date",
        MAPPING,
        r'    if sig\.get\("date"\):\n        return "event_date"',
        '    if sig.get("date"):\n        return None',
        marker="day6",
        what="a date-valued column is no longer an event_date candidate",
    ),
    Mutant(
        "sex_12_is_high",
        MAPPING,
        r'return RoleMapping\(h, role, "medium", c\.source, notes\)',
        'return RoleMapping(h, role, "high", c.source, notes)',
        marker="day6",
        what="sex coded 1/2 or 0/1 is high instead of medium",
    ),
    Mutant(
        "e01_message_truncated",
        MAPPING,
        r'columns resolve to case_id; reduce your case key to one column"',
        'columns resolve to case_id; reduce your case key"',
        marker="day6",
        what="the DEC-11 message no longer ends with the mandated sentence",
    ),
    Mutant(
        "label_with_floats_stays_high",
        MAPPING,
        r's\.n_unique > 2:\n            return \(\n                "conflict",',
        's.n_unique > 2:\n            return (\n                "consistent",',
        marker="day6",
        what="a label column holding continuous scores keeps high confidence",
    ),
    Mutant(
        "duplicate_fold_check_removed",
        MAPPING,
        r"if len\(set\(folded\)\) != len\(folded\):",
        "if False:",
        marker="day6",
        what="two headers identical after case-folding no longer halt H07",
    ),
    Mutant(
        "binary_rule_case_sensitive",
        MAPPING,
        r"if len\(lowered\) == 2 and any\(lowered == b for b in BINARY_LABEL_SETS\):",
        "if s.n_unique == 2 and any(lowered == b for b in BINARY_LABEL_SETS):",
        marker="day6",
        what="the two-valued label rule becomes case-sensitive",
    ),
    # Day 6 A repair 1: the lens's eight survivors are observed by tests/test_mapping_repair1.py
    # (pins); the ten below change the repair's own gates.
    Mutant(
        "min_max_floor_removed",
        PROFILE,
        r"return _fmt_num\(x\) if rows >= SUPPRESSION_K else SUPPRESSED",
        "return _fmt_num(x)",
        marker="day6",
        what="a numeric min/max held by fewer than k rows is printed (FA-B1)",
    ),
    Mutant(
        "min_max_floor_off_by_one",
        PROFILE,
        r"if rows >= SUPPRESSION_K else SUPPRESSED",
        "if rows >= SUPPRESSION_K - 1 else SUPPRESSED",
        marker="day6",
        what="a min/max held by 9 rows is printed",
    ),
    Mutant(
        "proposed_prior_accepted_by_yes",
        MAPPING,
        r'CONFIRMED_DECIDED_BY = frozenset\(\{"interactive", "file"\}\)',
        'CONFIRMED_DECIDED_BY = frozenset({"interactive", "file", "proposed"})',
        marker="day6",
        what="--yes accepts a mapping.json that proofpack run wrote unconfirmed (FA-N1)",
    ),
    Mutant(
        "slash_no_longer_splits_the_case_key",
        DECLARE,
        r'\[\^A-Za-z0-9_\]\+"\)',
        '[^A-Za-z0-9_/]+")',
        marker="day6",
        what="subject_id/hadm_id falls through to the schema's H08 enum halt (FA-B2)",
    ),
    Mutant(
        "clustering_list_keys_need_three",
        DECLARE,
        r"if isinstance\(value, \(list, tuple\)\) and len\(value\) >= 2:",
        "if isinstance(value, (list, tuple)) and len(value) >= 3:",
        marker="day6",
        what="clustering.columns: [a, b] passes silently",
    ),
    Mutant(
        "all_high_prompt_removed",
        CLI,
        r"^    if not pending:$",
        "    if not pending and False:",
        marker="day6",
        what="an all-high table is written as interactive with no keypress (FA-N2)",
    ),
    Mutant(
        "held_role_edit_accepted",
        CLI,
        r"holder = held_by\(r, new_role\)\n                if holder is not None:",
        "holder = held_by(r, new_role)\n                if holder is not None and False:",
        marker="day6",
        what="an edit to a role another column holds is written (FA-N4)",
    ),
    Mutant(
        "dash_date_shape_removed",
        PROFILE,
        r'^    re\.compile\(r"\^\\d\{1,2\}-\\d\{1,2\}-\\d\{4\}\$"\),\n',
        "",
        marker="day6",
        what="15-03-2024 values are free text again and pass H11 (FA-N7)",
    ),
    Mutant(
        "console_not_tolerant",
        CLI,
        r'stream\.reconfigure\(errors="backslashreplace"\)',
        "pass",
        marker="day6",
        what="a CJK header on a cp1252 stdout is exit 5 again (FA-N8)",
    ),
    Mutant(
        "quiet_hides_the_table_at_a_terminal",
        CLI,
        r"if not args\.json_log and \(not args\.quiet or tty\):",
        "if not args.json_log and not args.quiet:",
        marker="day6",
        what="--quiet at a terminal prompts with no table (FA-N12)",
    ),
    # repair 2 (the lens-2 findings; tests/test_mapping_repair2.py)
    Mutant(
        "apply_two_case_id_columns_h07_not_e01",
        MAPPING,
        r"if n_case >= 2:",
        "if n_case >= 3:",
        marker="day6",
        what="patient_nbr + mrn_local through run is H07, not the DEC-11 E01 (FA-B1)",
    ),
    Mutant(
        "partial_case_id_tokens_counted_by_map_headers_e01",
        MAPPING,
        r'if c and c\.role == "case_id" and c\.source != "partial"',
        'if c and c.role == "case_id"',
        marker="day6",
        what="patient_weight + patient_height halt E01 in map_headers (lens-2 M05)",
    ),
    Mutant(
        "accept_of_a_held_role_taken",
        CLI,
        r"holder = held_by\(r, r\.role\) if r\.role is not None else None",
        "holder = None",
        marker="day6",
        what="'a' at both case_id prompts writes two holders (FA-B1)",
    ),
    Mutant(
        "all_high_prompt_takes_any_answer",
        CLI,
        r'say\("  answer a or q"\)',
        "break",
        marker="day6",
        what="'n' at the all-high prompt is an accept (RG-N1)",
    ),
    Mutant(
        "attr_twins_not_single_holder",
        MAPPING,
        r'return role in SINGLE_HOLDER_ROLES or role\.startswith\(\("attr_", "rater_"\)\)',
        "return role in SINGLE_HOLDER_ROLES",
        marker="day6",
        what="'Attr Site' beside attr_site are both high (FA-N7)",
    ),
    Mutant(
        "prior_role_type_unchecked",
        MAPPING,
        r"if role is not None and not isinstance\(role, str\):",
        "if False:",
        marker="day6",
        what="a prior with role 123 reaches run --yes as exit 5 (RG-B1)",
    ),
    Mutant(
        "list_key_string_not_split",
        DECLARE,
        r"if isinstance\(value, str\):",
        "if False:",
        marker="day6",
        what="clustering.columns: 'subject_id, hadm_id' passes silently (FA-N8)",
    ),
    Mutant(
        "and_separator_lower_case_only",
        DECLARE,
        r"\[Aa\]\[Nn\]\[Dd\]",
        "and",
        marker="day6",
        what="'a AND b' counts three tokens (RG-N3)",
    ),
    Mutant(
        "dotted_date_shape_removed",
        PROFILE,
        r'^    re\.compile\(r"\^\\d\{1,2\}\\\.\\d\{1,2\}\\\.\\d\{4\}\$"\),\n',
        "",
        marker="day6",
        what="15.03.2024 values are categorical again and pass H11 (FA-N2)",
    ),
    Mutant(
        "out_dir_check_off",
        CLI,
        r"if not out_dir\.is_dir\(\):",
        "if False:",
        marker="day6",
        what="--out into a missing directory is exit 5 after the prompts (FA-N6)",
    ),
    Mutant(
        "hash_is_the_column_count",
        SCHEMA_IO,
        r'joined = "\\n"\.join\(sorted\(h\.strip\(\) for h in headers\)\)',
        "joined = str(len(headers))",
        marker="day6",
        what="a header renamed at the same width keeps the hash (lens-2 M24)",
    ),
    # repair 3: the four lens-3 survivors (L08, L11, L13, L14; L20 was a dead clause and
    # is deleted) and one observer per new gate.
    Mutant(
        "date_type_on_any_value",
        PROFILE,
        r"if all\(any\(p\.match\(v\) for p in DATE_PATTERNS\) for v in values\):",
        "if any(any(p.match(v) for p in DATE_PATTERNS) for v in values):",
        marker="day6",
        what="one date among sixty cells types the column date (lens-3 L08)",
    ),
    Mutant(
        "affix_case_id_claims_not_counted",
        MAPPING,
        r'if c and c\.role == "case_id" and c\.source != "partial"',
        'if c and c.role == "case_id" and c.source in ("canonical", "synonym")',
        marker="day6",
        what="patient_id + pt_subject_id is not E01 in map_headers (lens-3 L11)",
    ),
    Mutant(
        "fold_header_without_strip",
        MAPPING,
        r'header\.replace\("\\ufeff", ""\)\)\.strip\(\)\.casefold\(\)',
        'header.replace("\\\\ufeff", "")).casefold()',  # a re.sub template: \\ is one \
        marker="day6",
        what="' Label ' and 'label' are two headers after folding (lens-3 L13)",
    ),
    Mutant(
        "apply_e01_counts_non_high_case_id_only",
        MAPPING,
        r'if mapping\.role_of\(original\) == "case_id"\)',
        'if mapping.role_of(original) == "case_id"\n'
        '        and mapping.entry(original).confidence != "high")',
        marker="day6",
        what="two high case_id columns pass apply_mapping (lens-3 L14)",
    ),
    Mutant(
        "empty_answer_accepts",
        CLI,
        r'^ACCEPT_ANSWERS = \("a", "accept"\)$',
        'ACCEPT_ANSWERS = ("a", "accept", "")',
        marker="day6",
        what="Enter alone accepts at both prompts (lens-3 FA-B1)",
    ),
    Mutant(
        "ignore_collision_unchecked_on_a_prior",
        MAPPING,
        r"pair = ignore_collision\(prior\.roles\)",
        "pair = None",
        marker="day6",
        what="a prior ignoring 'score' beside prob -> score reaches apply_mapping (DEC-31)",
    ),
    Mutant(
        "accept_does_not_record_confirmed",
        CLI,
        r"^                r\.confirmed = True$",
        "                r.confirmed = False",
        marker="day6",
        what="'a' leaves confirmed False so --yes refuses the file (DEC-28)",
    ),
    Mutant(
        "date_month_floor_removed",
        PROFILE,
        r"shown_lo = keys\[0\] if months\[keys\[0\]\] >= SUPPRESSION_K else SUPPRESSED",
        "shown_lo = keys[0]",
        marker="day6",
        what="a month held by one row prints as min (DEC-39)",
    ),
    Mutant(
        "yes_role_difference_unchecked",
        MAPPING,
        r"if p\.role != f\.role:",
        "if False:",
        marker="day6",
        what="a prior 'age' on a column now holding bands passes --yes (carried 7)",
    ),
    Mutant(
        "roles_list_check_removed",
        MAPPING,
        r'if not isinstance\(data\["roles"\], list\):',
        "if False:",
        marker="day6",
        what="roles: {} reads as an empty list again (lens-3 RG-B1)",
    ),
    Mutant(
        "originals_not_checked_against_the_table",
        MAPPING,
        r"unknown = sum\(1 for r in prior\.roles if r\.original not in header_set\)",
        "unknown = 0",
        marker="day6",
        what="original: NOT_A_HEADER passes --yes (DEC-29)",
    ),
    Mutant(
        "out_is_dir_check_off",
        CLI,
        r"if out_path\.is_dir\(\):",
        "if False:",
        marker="day6",
        what="--out naming a directory reaches the prompt (carried 6)",
    ),
    Mutant(
        "recursion_error_not_caught",
        MAPPING,
        r"except \(ValueError, RecursionError\) as exc:",
        "except ValueError as exc:",
        marker="day6",
        what="100,000 nested '[' is exit 5 again (lens-3 FA-B4)",
    ),
)

MUTANTS = MUTANTS + MUTANTS_DAY6_A


def make_copy() -> Path:
    tmp = Path(tempfile.mkdtemp(prefix="proofpack-mutants-"))
    for item in COPIED:
        src = REPO / item
        if src.is_dir():
            shutil.copytree(src, tmp / item, ignore=shutil.ignore_patterns("__pycache__"))
        else:
            shutil.copy2(src, tmp / item)
    return tmp


def env_for(copy: Path) -> dict[str, str]:
    env = dict(os.environ)
    env["PYTHONPATH"] = str(copy / "src")
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    return env


def assert_imports_from_copy(copy: Path) -> None:
    out = subprocess.run(
        [sys.executable, "-c", "import proofpack, sys; print(proofpack.__file__)"],
        cwd=copy,
        env=env_for(copy),
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()
    if Path(out).resolve().parent.parent != (copy / "src").resolve():
        raise SystemExit(f"proofpack resolves to {out}, not the copy under {copy / 'src'}")


def plant(copy: Path, mutant: Mutant) -> None:
    target = copy / mutant.file
    original = (REPO / mutant.file).read_text(encoding="utf-8")
    mutated, n = re.subn(mutant.pattern, mutant.replacement, original, flags=re.M)
    if n != mutant.count:
        raise SystemExit(
            f"mutant {mutant.id}: pattern matched {n} time(s) in {mutant.file}, expected "
            f"{mutant.count} - the code moved; update the mutant list"
        )
    target.write_text(mutated, encoding="utf-8")


def restore(copy: Path, mutant: Mutant) -> None:
    shutil.copy2(REPO / mutant.file, copy / mutant.file)


def run_marker(copy: Path, marker: str) -> tuple[int, str]:
    proc = subprocess.run(
        [sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider", "-x", "-m", marker],
        cwd=copy,
        env=env_for(copy),
        capture_output=True,
        text=True,
    )
    tail = "\n".join((proc.stdout + proc.stderr).strip().splitlines()[-3:])
    return proc.returncode, tail


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="plant declared mutants and run a pytest marker")
    ap.add_argument("--marker", default="day5")
    ap.add_argument("--only", action="append", help="mutant id(s) to run")
    ap.add_argument("--list", action="store_true")
    ap.add_argument("--fail-on-survivor", action="store_true")
    args = ap.parse_args(argv)
    # --only picks by id across every list; otherwise the marker picks its own list
    chosen = [
        m for m in MUTANTS if ((m.id in args.only) if args.only else (m.marker == args.marker))
    ]
    if args.list:
        for m in MUTANTS:
            print(f"{m.marker:<5} {m.id:<36} {m.file:<36} {m.what}")
        return 0
    copy = make_copy()
    try:
        assert_imports_from_copy(copy)
        rc, tail = run_marker(copy, args.marker)
        if rc != 0:
            print(f"baseline (no mutant) does not pass -m {args.marker}; refusing to sweep\n{tail}")
            return 2
        print(f"baseline: -m {args.marker} passes in the copy at {copy}\n")
        survivors = []
        t0 = time.time()
        for m in chosen:
            plant(copy, m)
            rc, tail = run_marker(copy, args.marker)
            restore(copy, m)
            status = "killed" if rc != 0 else "SURVIVED"
            if rc == 0:
                survivors.append(m)
            print(f"{status:<9} {m.id:<36} {m.what}")
            if rc != 0:
                print(f"          {tail.splitlines()[-1][:110]}")
        killed = len(chosen) - len(survivors)
        print(
            f"\n{len(chosen)} planted, {killed} killed, {len(survivors)} survived; "
            f"{time.time() - t0:.0f} s"
        )
        for m in survivors:
            print(f"  survivor: {m.id} - {m.what}")
        return 1 if survivors and args.fail_on_survivor else 0
    finally:
        shutil.rmtree(copy, ignore_errors=True)


if __name__ == "__main__":
    raise SystemExit(main())
