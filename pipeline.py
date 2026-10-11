"""Evidence-to-review pipeline (Niti take-home, Exercise 1).

Reads data/decisions.csv and data/events.csv, writes:
  output/history.csv  - event history with disposition + reason
  output/queue.csv    - latest-state review queue, one row per decision

Run:  python3 pipeline.py
"""

from __future__ import annotations

import csv
from pathlib import Path

ASSESSMENT_DAY = 10

ROOT = Path(__file__).resolve().parent
DATA_DIR = ROOT / "data"
OUTPUT_DIR = ROOT / "output"

HISTORY_COLUMNS = [
    "event_id",
    "decision_id",
    "day",
    "type",
    "value",
    "evidence",
    "disposition",
    "reason",
]
QUEUE_COLUMNS = [
    "decision_id",
    "approval_state",
    "execution_state",
    "latest_accepted_grade",
    "evidence_quality",
    "outcome_state",
    "next_step",
]


def _read_csv_rows(path: Path) -> list[dict]:
    with path.open(newline="", encoding="utf-8") as file:
        return [
            {
                key.strip(): (value or "").strip()
                for key, value in row.items()
                if key is not None
            }
            for row in csv.DictReader(file)
        ]


def load_decisions(path: Path) -> dict[str, dict]:
    """Read decisions.csv, keyed by id; parse valid maturity days as integers."""
    decisions = {}
    for row in _read_csv_rows(path):
        maturity_day = row.get("maturity_day", "")
        try:
            row["maturity_day"] = int(maturity_day)
        except ValueError:
            row["maturity_day"] = maturity_day
        decisions[row.get("id", "")] = row
    return decisions


def load_events(path: Path) -> list[dict]:
    """Read trimmed event rows in input order without interpreting their values."""
    return _read_csv_rows(path)


def dedupe(events: list[dict]) -> list[dict]:
    """Return one row per event_id, keeping the first copy encountered."""
    seen = set()
    unique_events = []
    for event in events:
        if event["event_id"] not in seen:
            seen.add(event["event_id"])
            unique_events.append(event)
    return unique_events


def sort_events(events: list[dict]) -> list[dict]:
    """Sort by numeric day, then event_id; place malformed days last."""

    def sort_key(event: dict) -> tuple[int, int, str]:
        try:
            day = int(event.get("day", ""))
        except (TypeError, ValueError):
            return (1, 0, event.get("event_id", ""))
        return (0, day, event.get("event_id", ""))

    return sorted(events, key=sort_key)


def _grade_review_reason(
    value: object,
    day: int,
    decision: dict,
    assessment_day: int,
    full_execution_days: list[int],
) -> str | None:
    parts = value.split("|") if isinstance(value, str) else []
    if len(parts) != 2 or not all(part.strip() for part in parts):
        return "invalid_grade_value"
    if day > assessment_day:
        return "event_after_assessment"
    try:
        maturity_day = int(decision.get("maturity_day", ""))
    except (TypeError, ValueError):
        return "invalid_maturity_day"
    if day < maturity_day:
        return "grade_before_maturity"
    if not any(execution_day < day for execution_day in full_execution_days):
        return "execution_not_previously_full"
    return None


def build_history(
    decisions: dict[str, dict], events: list[dict], assessment_day: int = ASSESSMENT_DAY
) -> list[dict]:
    """Classify deduped, sorted events while keeping superseded grades visible."""
    history = []
    full_execution_days = {}
    latest_grade_index = {}

    for event in events:
        row = {column: event.get(column, "") for column in HISTORY_COLUMNS[:6]}
        event_id = row["event_id"]
        decision_id = row["decision_id"]
        event_type = row["type"]
        value = row["value"]
        disposition = "review"

        try:
            day = int(row["day"])
        except (TypeError, ValueError):
            day = None

        if decision_id not in decisions:
            reason = "unknown_decision"
        elif day is None:
            reason = "invalid_day"
        else:
            match event_type:
                case "approval":
                    if value == "approved":
                        disposition, reason = "accepted", "valid_approval"
                    else:
                        reason = "unsupported_value"
                case "execution":
                    if value not in {"full", "partial"}:
                        reason = "unsupported_value"
                    else:
                        disposition, reason = "accepted", "valid_execution"
                        if value == "full":
                            full_execution_days.setdefault(decision_id, []).append(day)
                case "note":
                    if value == "none":
                        disposition, reason = "note", "free_text_ignored"
                    else:
                        reason = "unsupported_value"
                case "grade" | "grade_correction":
                    reason = _grade_review_reason(
                        value,
                        day,
                        decisions[decision_id],
                        assessment_day,
                        full_execution_days.get(decision_id, []),
                    )
                    previous_index = latest_grade_index.get(decision_id)
                    if reason is None and event_type == "grade_correction":
                        if previous_index is None:
                            reason = "correction_without_accepted_grade"
                        else:
                            previous_id = history[previous_index]["event_id"]
                            history[previous_index]["reason"] = (
                                f"superseded_by:{event_id}"
                            )
                            reason = f"supersedes:{previous_id}"
                            disposition = "accepted"
                    elif reason is None:
                        disposition, reason = "accepted", "eligible"
                    if disposition == "accepted":
                        latest_grade_index[decision_id] = len(history)
                case _:
                    reason = "unsupported_type"

        row["disposition"] = disposition
        row["reason"] = reason
        history.append(row)

    return history


def build_review_queue(
    decisions: dict[str, dict],
    history: list[dict],
    assessment_day: int = ASSESSMENT_DAY,
) -> list[dict]:
    """Fold history into one latest-state row per decision."""
    states = {
        decision_id: {
            "approval_state": "not_recorded",
            "execution_state": "not_recorded",
            "latest_accepted_grade": "",
            "evidence_quality": "",
        }
        for decision_id in decisions
    }

    for event in history:
        decision_id = event.get("decision_id")
        if not isinstance(decision_id, str):
            continue
        state = states.get(decision_id)
        if state is None or event.get("disposition") != "accepted":
            continue

        match event.get("type"):
            case "approval":
                state["approval_state"] = event.get("value", "")
            case "execution":
                state["execution_state"] = event.get("value", "")
            case "grade" | "grade_correction":
                if event.get("reason", "").startswith("superseded_by:"):
                    continue
                parts = event.get("value", "").split("|")
                if len(parts) == 2:
                    state["latest_accepted_grade"] = parts[0].strip()
                    state["evidence_quality"] = parts[1].strip()

    queue = []
    next_steps = {
        "partial": "complete execution",
        "not_executed": "record approval/execution",
        "too_early": "await maturity",
        "no_grade": "collect grade",
        "graded": "monitor",
    }
    for decision_id, decision in decisions.items():
        state = states[decision_id]
        try:
            maturity_day = int(decision.get("maturity_day", ""))
        except (TypeError, ValueError):
            maturity_day = None

        if state["execution_state"] == "partial":
            outcome_state = "partial"
        elif state["execution_state"] != "full":
            outcome_state = "not_executed"
        elif maturity_day is not None and assessment_day < maturity_day:
            outcome_state = "too_early"
        elif not state["latest_accepted_grade"]:
            outcome_state = "no_grade"
        else:
            outcome_state = "graded"

        queue.append(
            {
                "decision_id": decision_id,
                **state,
                "outcome_state": outcome_state,
                "next_step": next_steps[outcome_state],
            }
        )

    return queue


def write_csv(rows: list[dict], columns: list[str], path: Path) -> None:
    """Write rows to path as CSV with the given column order.

    TODO: create parent dir if needed; write blanks for missing values.
    """
    raise NotImplementedError


def run(
    data_dir: Path = DATA_DIR, output_dir: Path = OUTPUT_DIR
) -> tuple[list[dict], list[dict]]:
    """Run the full pipeline and return (history, queue).

    TODO: load -> dedupe -> sort -> build_history -> build_review_queue -> write.
    """
    raise NotImplementedError


def main() -> None:
    """CLI entry point."""
    run()


if __name__ == "__main__":
    main()
