"""The four tests required by the brief. Fill in the bodies yourself.

Run: python3 -m pytest -v
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pipeline  # noqa: E402,F401


def test_dedupe_keeps_first_duplicate():
    events = [
        {"event_id": "E08", "value": "first", "note": "original"},
        {"event_id": "E08", "value": "different", "note": "duplicate"},
        {"event_id": "E09", "value": "other", "note": ""},
    ]

    assert pipeline.dedupe(events) == [events[0], events[2]]


def test_load_decisions_trims_and_parses_maturity_day(tmp_path):
    path = tmp_path / "decisions.csv"
    path.write_text(
        " id, action, maturity_day, expected_metric \n"
        " D1, hold, 7, contribution \n"
        " D2, reduce, unknown, contribution \n",
        encoding="utf-8",
    )

    decisions = pipeline.load_decisions(path)

    assert decisions["D1"] == {
        "id": "D1",
        "action": "hold",
        "maturity_day": 7,
        "expected_metric": "contribution",
    }
    assert decisions["D2"]["maturity_day"] == "unknown"


def test_load_decisions_missing_maturity_column(tmp_path):
    path = tmp_path / "decisions.csv"
    path.write_text("id,action\nD1,hold\n", encoding="utf-8")

    assert pipeline.load_decisions(path)["D1"]["maturity_day"] == ""


def test_load_events_trims_fields_and_keeps_input_order(tmp_path):
    path = tmp_path / "events.csv"
    path.write_text(
        " event_id, decision_id, day, type, value, evidence, note \n"
        " E02, D1, 2, execution, full, S02, executed \n"
        " E01, D1, malformed, grade, favorable|observational, S01, note text \n",
        encoding="utf-8",
    )

    events = pipeline.load_events(path)

    assert [event["event_id"] for event in events] == ["E02", "E01"]
    assert events[0]["day"] == "2"
    assert events[1]["day"] == "malformed"
    assert events[1]["note"] == "note text"


def test_sort_events_numeric_day_then_id_with_malformed_days_last():
    events = [
        {"event_id": "E10", "day": "10"},
        {"event_id": "E2B", "day": "2"},
        {"event_id": "Ebad2", "day": "invalid"},
        {"event_id": "E2A", "day": "2"},
        {"event_id": "Ebad1"},
    ]

    sorted_events = pipeline.sort_events(events)

    assert [event["event_id"] for event in sorted_events] == [
        "E2A",
        "E2B",
        "E10",
        "Ebad1",
        "Ebad2",
    ]
    assert events[0]["event_id"] == "E10"


def test_build_history_sample_correction_and_note():
    decisions = pipeline.load_decisions(pipeline.DATA_DIR / "decisions.csv")
    events = pipeline.load_events(pipeline.DATA_DIR / "events.csv")
    history = pipeline.build_history(
        decisions, pipeline.sort_events(pipeline.dedupe(events))
    )
    by_id = {row["event_id"]: row for row in history}

    assert len(history) == 9
    assert by_id["E03"]["disposition"] == "accepted"
    assert by_id["E03"]["reason"] == "superseded_by:E08"
    assert by_id["E08"]["disposition"] == "accepted"
    assert by_id["E08"]["reason"] == "supersedes:E03"
    assert by_id["E07"]["disposition"] == "review"
    assert by_id["E07"]["reason"] == "grade_before_maturity"
    assert by_id["E09"]["disposition"] == "note"


def test_grade_requires_earlier_full_execution_and_valid_value():
    decisions = {
        "D1": {"id": "D1", "maturity_day": 1},
        "D2": {"id": "D2", "maturity_day": 1},
    }
    events = pipeline.sort_events(
        [
            {
                "event_id": "E01",
                "decision_id": "D1",
                "day": "2",
                "type": "execution",
                "value": "full",
            },
            {
                "event_id": "E02",
                "decision_id": "D1",
                "day": "2",
                "type": "grade",
                "value": "favorable|observational",
            },
            {
                "event_id": "E03",
                "decision_id": "D1",
                "day": "3",
                "type": "grade",
                "value": "favorable|observational",
            },
            {
                "event_id": "E04",
                "decision_id": "D1",
                "day": "4",
                "type": "grade",
                "value": "favorable|",
            },
            {
                "event_id": "E05",
                "decision_id": "D2",
                "day": "2",
                "type": "grade",
                "value": "favorable|observational",
            },
            {
                "event_id": "E06",
                "decision_id": "D2",
                "day": "3",
                "type": "execution",
                "value": "full",
            },
        ]
    )

    history = pipeline.build_history(decisions, events)
    by_id = {row["event_id"]: row for row in history}

    assert by_id["E02"]["reason"] == "execution_not_previously_full"
    assert by_id["E03"]["disposition"] == "accepted"
    assert by_id["E04"]["reason"] == "invalid_grade_value"
    assert by_id["E05"]["reason"] == "execution_not_previously_full"


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
