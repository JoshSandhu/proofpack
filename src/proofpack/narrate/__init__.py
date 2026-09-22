"""Narrative (build day 8, E8): claims, the sentence-skeleton library and the claim-binding
checker (D1 section 4.4, D4 section 8). No prose is written here: :mod:`claims` binds
JSON pointers into the run document to template ids, :mod:`templates` holds the fixed
skeletons whose ``{slot}`` values the renderer fills from the Numbers the pointers
resolve, and :mod:`checker` accepts or rejects each claim with a typed reason. Nothing
in this package imports jinja2 or numpy; ``import proofpack.narrate`` works with both
hidden (``tests/test_render_theme.py``).
"""
