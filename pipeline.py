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
    "event_id", "decision_id", "day", "type", "value", "evidence",
    "disposition", "reason",
]
QUEUE_COLUMNS = [
    "decision_id", "approval_state", "execution_state", "latest_accepted_grade",
    "evidence_quality", "outcome_state", "next_step",
]


def load_decisions(path: Path) -> dict[str, dict]:
    """Read decisions.csv and return {decision_id: row}.

    Columns: id, action, maturity_day, expected_metric.
    TODO: strip whitespace, parse maturity_day as int, handle malformed rows.
    """
    raise NotImplementedError


def load_events(path: Path) -> list[dict]:
    """Read events.csv and return a list of raw event dicts (input order kept).

    Columns: event_id, decision_id, day, type, value, evidence, note.
    TODO: strip whitespace; do NOT interpret the `note` field.
    """
    raise NotImplementedError


def dedupe(events: list[dict]) -> list[dict]:
    """Return events with one row per event_id.

    TODO: decide and document which copy wins when duplicates differ.
    Replaying the full input must not add new history rows.
    """
    raise NotImplementedError


def sort_events(events: list[dict]) -> list[dict]:
    """Order events by day (as int) then event_id.

    TODO: decide how events with a malformed day are ordered.
    """
    raise NotImplementedError


def build_history(decisions: dict[str, dict], events: list[dict],
                  assessment_day: int = ASSESSMENT_DAY) -> list[dict]:
    """Classify every (deduped, sorted) event into a history row.

    Each row has HISTORY_COLUMNS; disposition is one of accepted / review / note,
    with a short reason. Grades are append-only: superseded grades stay visible.
    TODO: implement the rules from BRIEF.md (see PLAN.md section 3).
    """
    raise NotImplementedError


def build_review_queue(decisions: dict[str, dict], history: list[dict],
                       assessment_day: int = ASSESSMENT_DAY) -> list[dict]:
    """Fold history into one latest-state row per decision (QUEUE_COLUMNS).

    Every decision in decisions.csv appears, including ones with no events.
    TODO: approval/execution states, latest accepted grade, evidence_quality,
    outcome_state (in the brief's order), next_step.
    """
    raise NotImplementedError


def write_csv(rows: list[dict], columns: list[str], path: Path) -> None:
    """Write rows to path as CSV with the given column order.

    TODO: create parent dir if needed; write blanks for missing values.
    """
    raise NotImplementedError


def run(data_dir: Path = DATA_DIR, output_dir: Path = OUTPUT_DIR) -> tuple[list[dict], list[dict]]:
    """Run the full pipeline and return (history, queue).

    TODO: load -> dedupe -> sort -> build_history -> build_review_queue -> write.
    """
    raise NotImplementedError


def main() -> None:
    """CLI entry point."""
    run()


if __name__ == "__main__":
    main()
