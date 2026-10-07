# E14 (build day 14, lane E): corrections to two commit messages on `e14-lw01`

Wednesday 7 October 2026. The branch history is not rewritten (it has been gated through
`workflows/ci_gate.sh`, and interactive rebase is not available here). Each sentence below is
in a commit message that will reach public `main` with the branch; the correction beside it
is what was measured. `tests/test_e14_repair2.py::test_rg_o1_fa_b2_the_commit_message_corrections_are_on_the_branch`
reads this file for the quoted phrases.

## Commit 834634c (E14 item 4, the all-high map prompt)

- The message says: "in the walk-through a buyer typing 'y' was told nothing about how to
  accept".
- What the sources show: at `3ee5601` the prompt line read
  `every role is high (N columns): [a]ccept / [q]uit? ` and a non-answer was re-prompted with
  `  answer a or q` (`src/proofpack/cli.py`, lines 304 and 309 at `3ee5601`). The LW-01 log
  (`handoffs-orchestrator/2026-10-07_LW01_log.md`, line 7) records that the prompt takes `a`
  and that `y` re-prompts; user review note 17 asks for "type a to accept" in the prompt's
  first line, or for `y` to be accepted.
- Lens 1 found this (FA-B2 / RG-N5); `e67c5fa`'s message recorded it.

## Commit e67c5fa (E14 repair 1)

- The message says: "test_e14_repair1.py inspects those marks; it fails at a1840fc
  ("assert 'ap4' in set()")".
- Measured in repair 2 (a detached worktree at `a1840fc` with `e67c5fa`'s
  `tests/test_e14_repair1.py` copied in, `PYTHONPATH` set to that tree's `src`):
  `python -m pytest -q -p no:cacheprovider tests/test_e14_repair1.py -k fa_b1` gave
  `1 failed, 6 deselected`, and the first failing line was the set comparison:
  `Extra items in the left set: ('test_e14_cover_row', 'test_docx_cover_row_names_the_distinct_documents')`.
  `assert 'ap4' in set()` appeared only after the expected set was edited to `a1840fc`'s
  test names (`1 failed, 6 deselected`). The repair 1 note stated both cases; the commit
  message merged them.
- Lens 2 found this (FA-B2 / RG-N1).
- The test that message describes,
  `test_fa_b1_rg_n3_every_e14_docx_test_is_selected_by_ap4_and_takes_the_extra_rule`, was
  named for more than it inspected (lens 2 FA-B1 / RG-N2). Repair 2 deleted it; its
  replacement is in `tests/test_e14_repair2.py`.
