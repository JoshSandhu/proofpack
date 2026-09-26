"""A-P4 item 0 (build day 10, lane A): the seven sentence violations the A-P3 CI handoff
left open (``handoffs/2026-09-24_A_ci.md``, "What did not land"), each made true or
deleted in shipped files. One of the seven (lens 2 FA N6) was in a handoff note only and
shipped nothing; the five below plus FA3-S1 (``tests/test_workflows.py``, its own
counter-examples in ``LENS_COUNTER_EXAMPLES``) are the six in the tree.

* Lens 2 FA N3: ``test_fan7_ci_runs_the_oracle_check_after_pytest_unless_cancelled`` said
  what CI does; the test reads the YAML. Renamed to what it reads.
* Lens 2 FA N4 = RG N2: the ``ci.yml`` comment said the step's lines "reach the job log";
  the step has not run. It now says the step is written to print them and has not run.
* Lens 2 FA N5 = RG N2: the ``Dockerfile`` comment said docker-smoke "greps the base
  reference from its build log"; the grep step has not run. The qualifier is back.
* RG3-S1: ``test_the_zap_upload_step_runs_after_a_failed_scan`` read one YAML key. Renamed
  to ``test_the_zap_upload_step_carries_if_always``.
* FA3-S3: ``test_no_secret_looking_env_or_arg_and_no_key_material`` stated more than it
  inspects (a ``LABEL`` holding key bytes passes). Renamed to what it inspects.
"""

from __future__ import annotations

from pathlib import Path

import pytest

pytestmark = [pytest.mark.day10, pytest.mark.ap4]
REPO = Path(__file__).resolve().parent.parent

OLD_FAN7 = "test_fan7_ci_runs_the_oracle_check_after_pytest_unless_cancelled"
ABSENT = [
    ("tests/test_ap3_r3_repair1.py", OLD_FAN7),
    (".github/workflows/ci.yml", OLD_FAN7),
    (".github/workflows/ci.yml", "reach the job log"),
    ("Dockerfile", "greps the base reference from its build log"),
    ("tests/test_ap3_repair2.py", "test_the_zap_upload_step_runs_after_a_failed_scan"),
    ("tests/test_dockerfile.py", "test_no_secret_looking_env_or_arg_and_no_key_material"),
]
PRESENT = [
    (
        "tests/test_ap3_r3_repair1.py",
        "def test_fan7_the_oracle_step_follows_pytest_and_carries_if_not_cancelled():",
    ),
    (".github/workflows/ci.yml", "this step has not run yet"),
    ("Dockerfile", "has not yet run with that step"),
    ("tests/test_ap3_repair2.py", "def test_the_zap_upload_step_carries_if_always():"),
    (
        "tests/test_dockerfile.py",
        "def test_no_secretish_env_or_arg_name_no_lic_pem_key_copy_and_no_begin_private_key(",
    ),
]


@pytest.mark.parametrize("name,phrase", ABSENT)
def test_the_false_sentence_is_absent(name: str, phrase: str):
    assert phrase not in (REPO / name).read_text(encoding="utf-8")


@pytest.mark.parametrize("name,phrase", PRESENT)
def test_the_corrected_sentence_is_present(name: str, phrase: str):
    assert phrase in (REPO / name).read_text(encoding="utf-8")


def test_fa3_s1_the_offline_flag_refuses_the_four_lens_forms():
    """FA3-S1: ``--out=--offline``, ``OPT=--offline``, ``>--offline.log`` and ``& echo
    --offline`` each passed ``offline_violations`` at 5b1b1f4; each is one violation now."""
    import test_workflows as tw

    for line in (
        "proofpack run --input a --criteria b --out=--offline",
        "OPT=--offline proofpack run --input a --criteria b",
        "proofpack run --input a --criteria b >--offline.log",
        "proofpack run --input a --criteria b & echo --offline",
    ):
        rel = tw._load("release.yml")
        rel["jobs"]["build"]["steps"].append({"run": line})
        assert len(tw.offline_violations(rel)) == 1, line
    # the flag as a word of its own is still accepted
    assert tw.OFFLINE_FLAG.search("proofpack run --input a --offline")
    assert tw.OFFLINE_FLAG.search("proofpack --offline run --input a")
