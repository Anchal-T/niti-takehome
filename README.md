# Evidence-to-Review Pipeline

## Setup / run

Python 3.10+. Tests need pytest (`python3 -m pip install pytest`). Run `python3 pipeline.py`; test with `python3 -m pytest -v`.

## Outputs

- `output/history.csv`: sorted, deduplicated event history with status and reason.
- `output/queue.csv`: latest state for every decision.

## Assumptions

- First non-empty event ID wins; conflicting duplicate contents are dropped without a warning. Notes do not change state.
- `too_early` compares assessment day 10 with the decision's maturity day.
- A grade needs non-empty `label|quality`, maturity reached on its event day, full execution on an earlier day, and event day no later than 10. Approval is not required. Corrections follow the same rules; accepted corrections supersede but do not delete the old grade.
- The queue uses the latest accepted approval and execution. `next_step`: partial → complete execution; not_executed → record approval/execution; too_early → await maturity; no_grade → collect grade; graded → monitor.

## Tests

`python3 -m pytest -q`: 18 passed. Duplicate replay, D3 early grade, D2 partial, D1 correction: all pass.

## Time spent

About three hours in multiple sessions.

## Known gaps

Grade words are not checked (`banana|xyz` can pass if eligibility checks pass). A later partial does not cancel an earlier full execution for grade eligibility. Approval values other than `approved` go to review. Event IDs sort as text within a day (`E10` before `E9`). Events without IDs stay in review but cannot be deduplicated across replays. Outputs overwrite local CSVs; there is no persistent store.

## AI assistance

Grok Bot set up the scaffold, copied the brief/CSVs, and wrote the work plan and stubs (per `PLAN.md`). Zed AI coding agent (GPT-6 Luna) discussed rules, implemented/refactored code and tests, ran checks, and drafted this README. I chose and approved the rules as we went.
