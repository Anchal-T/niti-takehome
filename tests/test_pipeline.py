"""The four tests required by the brief. Fill in the bodies yourself.

Run: python3 -m pytest -v
"""

import csv
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pipeline


def test_write_csv_creates_parent_and_blanks_missing_values(tmp_path):
    path = tmp_path / "nested" / "output.csv"

    pipeline.write_csv([{"first": "value"}, {"first": None}], ["first", "second"], path)

    with path.open(newline="", encoding="utf-8") as file:
        rows = list(csv.DictReader(file))
    assert rows == [
        {"first": "value", "second": ""},
        {"first": "", "second": ""},
    ]


def test_run_writes_repeatable_outputs(tmp_path):
    output_dir = tmp_path / "results"

    first_history, first_queue = pipeline.run(output_dir=output_dir)
    history_text = (output_dir / "history.csv").read_text(encoding="utf-8")
    queue_text = (output_dir / "queue.csv").read_text(encoding="utf-8")
    second_history, second_queue = pipeline.run(output_dir=output_dir)

    assert first_history == second_history
    assert first_queue == second_queue
    assert (output_dir / "history.csv").read_text(encoding="utf-8") == history_text
    assert (output_dir / "queue.csv").read_text(encoding="utf-8") == queue_text
    assert len(first_history) == 9
    assert len(first_queue) == 6


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
    decisions = pipeline.load_decisions(pipeline.DATA_DIR / "decisions.csv")
    events = pipeline.load_events(pipeline.DATA_DIR / "events.csv")

    first_run = pipeline.build_history(
        decisions, pipeline.sort_events(pipeline.dedupe(events))
    )
    replay = pipeline.build_history(
        decisions, pipeline.sort_events(pipeline.dedupe(events + events))
    )

    assert first_run == replay
    assert len(first_run) == len({row["event_id"] for row in first_run})


def test_d3_early_grade():
    decisions = pipeline.load_decisions(pipeline.DATA_DIR / "decisions.csv")
    events = pipeline.load_events(pipeline.DATA_DIR / "events.csv")
    history = pipeline.build_history(
        decisions, pipeline.sort_events(pipeline.dedupe(events))
    )
    queue = pipeline.build_review_queue(decisions, history)
    early_grade = next(row for row in history if row["event_id"] == "E07")
    d3 = next(row for row in queue if row["decision_id"] == "D3")

    assert early_grade["disposition"] == "review"
    assert early_grade["reason"] == "grade_before_maturity"
    assert d3["approval_state"] == "not_recorded"
    assert d3["latest_accepted_grade"] == ""
    assert d3["outcome_state"] == "too_early"


def test_d2_partial_execution():
    decisions = pipeline.load_decisions(pipeline.DATA_DIR / "decisions.csv")
    events = pipeline.load_events(pipeline.DATA_DIR / "events.csv")
    history = pipeline.build_history(
        decisions, pipeline.sort_events(pipeline.dedupe(events))
    )
    d2 = next(
        row
        for row in pipeline.build_review_queue(decisions, history)
        if row["decision_id"] == "D2"
    )

    assert d2["approval_state"] == "approved"
    assert d2["execution_state"] == "partial"
    assert d2["latest_accepted_grade"] == ""
    assert d2["outcome_state"] == "partial"


def test_review_queue_uses_latest_execution_and_outcome_order():
    decisions = {
        "D1": {"id": "D1", "maturity_day": 1},
        "D2": {"id": "D2", "maturity_day": 1},
        "D3": {"id": "D3", "maturity_day": 14},
        "D4": {"id": "D4", "maturity_day": 1},
    }
    events = pipeline.sort_events(
        [
            {
                "event_id": "E01",
                "decision_id": "D1",
                "day": "1",
                "type": "execution",
                "value": "full",
            },
            {
                "event_id": "E02",
                "decision_id": "D1",
                "day": "2",
                "type": "execution",
                "value": "partial",
            },
            {
                "event_id": "E03",
                "decision_id": "D2",
                "day": "1",
                "type": "execution",
                "value": "full",
            },
            {
                "event_id": "E04",
                "decision_id": "D3",
                "day": "1",
                "type": "execution",
                "value": "full",
            },
        ]
    )

    history = pipeline.build_history(decisions, events)
    queue = {
        row["decision_id"]: row
        for row in pipeline.build_review_queue(decisions, history)
    }

    assert queue["D1"]["execution_state"] == "partial"
    assert queue["D1"]["outcome_state"] == "partial"
    assert queue["D2"]["outcome_state"] == "no_grade"
    assert queue["D3"]["outcome_state"] == "too_early"
    assert queue["D4"]["execution_state"] == "not_recorded"
    assert queue["D4"]["outcome_state"] == "not_executed"


def test_d1_correction_history():
    decisions = pipeline.load_decisions(pipeline.DATA_DIR / "decisions.csv")
    events = pipeline.load_events(pipeline.DATA_DIR / "events.csv")
    history = pipeline.build_history(
        decisions, pipeline.sort_events(pipeline.dedupe(events))
    )
    queue = pipeline.build_review_queue(decisions, history)
    d1 = next(row for row in queue if row["decision_id"] == "D1")
    e03 = next(row for row in history if row["event_id"] == "E03")
    e08 = next(row for row in history if row["event_id"] == "E08")

    assert history.index(e03) < history.index(e08)
    assert e03["reason"] == "superseded_by:E08"
    assert e08["reason"] == "supersedes:E03"
    assert d1["latest_accepted_grade"] == "neutral"
    assert d1["evidence_quality"] == "observational"
