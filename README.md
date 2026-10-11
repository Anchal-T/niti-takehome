# Evidence-to-Review Pipeline

## Setup / run

Requires Python 3.10+ and pytest. Run `python3 pipeline.py` to generate outputs. Run `python3 -m pytest -v` to test.

## Outputs

- `output/history.csv`: sorted, deduplicated event history with status and reason.
- `output/queue.csv`: one latest-state row per decision.

## Assumptions

- The first row for an `event_id` wins. Notes do not change state.
- A grade or correction counts only if its value has two non-empty parts separated by `|`, its day is at or after maturity and no later than day 10, and full execution happened on an earlier day. Same-day execution is not enough.
- A correction follows the same rules and replaces the latest accepted grade. The old grade remains in history.
- The latest accepted approval and execution set the queue state. The grade label and evidence quality are split into separate fields.

## Tests

`python3 -m pytest -q`: 14 passed. Duplicate replay: pass. D3 early grade: pass. D2 partial execution: pass. D1 correction history: pass.

## Time spent

Around 2 and half hours were spent on this project.

## Known gaps

Outputs are local CSV files and are overwritten on each run. Replay protection uses the current input file; there is no persistent event store. Events without IDs are kept for review but cannot be deduplicated across replays.

## AI assistance

I used an AI assistant to discuss design choices and help write the implementation, tests, and this README. Grok Bot created the initial scaffold and work plan.
