"""The four tests required by the brief. Fill in the bodies yourself.

Run: python3 -m pytest -v
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pipeline  # noqa: E402,F401


def test_duplicate_replay():
    """Replaying the full input must not add new history rows.

    Must assert: history built from events (incl. the duplicated E08) has exactly
    one row per event_id, and running again / feeding the events twice produces
    an identical history (same row count, same rows).
    """
    pytest.skip("TODO")


def test_d3_early_grade():
    """D3's grade arrives before maturity_day.

    Must assert: E07 is preserved in history with disposition 'review' (and a reason),
    its grade is NOT used as D3's latest_accepted_grade, and D3's outcome_state
    follows the brief's ordering.
    """
    pytest.skip("TODO")


def test_d2_partial_execution():
    """D2 was approved but only partially executed.

    Must assert: D2's execution_state reflects the partial execution, outcome_state is
    derived per the brief's order (partial first), approval alone does not
    produce a grade/success, and no outcome is invented.
    """
    pytest.skip("TODO")


def test_d1_correction_history():
    """D1 has a grade (E03) later corrected (E08).

    Must assert: both E03 and E08 remain visible in history (append-only, ordered by
    day then event_id), E03 is marked as superseded rather than deleted, and D1's
    latest_accepted_grade in the queue comes from the correction.
    """
    pytest.skip("TODO")
