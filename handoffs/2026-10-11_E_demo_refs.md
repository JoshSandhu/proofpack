# 2026-10-11 E: internal references removed from customer-visible engine strings

Base ccaa768, branch fix-demo-refs-engine. Josh asked for the DEC- ids, spec section numbers and test paths a buyer reads on /demo to go, with every substantive sentence kept.

## What landed
Eight strings lost their internal reference; the wording otherwise is unchanged.

| Where | Old | New |
|---|---|---|
| errors.py E01 | composite case key: two or more columns identify a case (DEC-11) | composite case key: two or more columns identify a case |
| errors.py W06 | single-class site(s) present; site-level metrics limited (D1 section 5) | single-class site(s) present; site-level metrics limited |
| cli.py `map` help | map original headers to canonical roles (D1 section 5) | map original headers to canonical roles |
| cli.py `run --mapping` help | ...beside the input (DEC-26: run never proposes a mapping itself) | ...beside the input (run never proposes a mapping itself) |
| cli.py `compare --mapping` help | ...beside the new table (DEC-26) | ...beside the new table |
| cli.py ~338 prompt refusal | ...would hold (DEC-31); give one of them another role | ...would hold; give one of them another role |
| run.py ~445 | run.json only (D1 section 7: after grace, JSON only) | run.json only (after grace, JSON only) |
| io/mapping.py ~952 H07 | ...another column to {role} (DEC-31); run proofpack map again... | ...another column to {role}; run proofpack map again... |

Moved, not dropped: tests/test_mapping_repair3.py (DEC31_PRIOR, DEC31_PROMPT) and the T12 golden rows for E01 and W06 pin the new text. New tests/test_fix1011_no_internal_refs.py (markers day15, fix1011) asserts that no error or warning meaning, no --help text (top level, map, run, compare) and no non-docstring string literal in cli.py, run.py or io/mapping.py carries DEC-<n>, "D1 section" or "D1 §"; 8 of its 9 cases fail against the old code.

## Cut
Comments and docstrings (not customer-visible). fixtures.py row text (a separate item). README.md still names DEC-11 and DEC-26 in prose; it is not a /demo string, so it was left.

## Re-run
cd wt-efix2 && PYTHONPATH="$PWD/src" ../proofpack/.venv/Scripts/python -m pytest -q -p no:cacheprovider
then python -m ruff check . and python -m ruff format --check .
The one full run found only the missing day marker on the new test (fixed); the affected files and the golden tests were re-run after.

## Tomorrow / needs from Josh
The site's pinned engine ref and the Pyodide bundle must move to this commit before /demo shows the new text. Nothing needed from Josh beyond that merge.
