"""
Very small results store. Results already live as JSONL files under
results/ (written by the harness / run-evaluation endpoint) - this module
just reads them back for the API, and appends single ad-hoc evaluations
(from POST /api/evaluate in the interactive "Evaluate" page) to
results/interactive.jsonl so they show up in the Results table too.
"""
import json
from pathlib import Path
from typing import Optional

REPO_ROOT = Path(__file__).parent.parent.parent
RESULTS_DIR = REPO_ROOT / "results"
INTERACTIVE_FILE = RESULTS_DIR / "interactive.jsonl"


def list_result_files():
    RESULTS_DIR.mkdir(exist_ok=True)
    return sorted(RESULTS_DIR.glob("*.jsonl"))


def load_all_results() -> list[dict]:
    """Loads and merges every results/*.jsonl file, de-duplicated by id (last write wins)."""
    merged = {}
    for path in list_result_files():
        with open(path) as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    row = json.loads(line)
                except json.JSONDecodeError:
                    continue
                merged[row["id"]] = row
    return list(merged.values())


def get_result(item_id: str) -> Optional[dict]:
    for row in load_all_results():
        if row["id"] == item_id:
            return row
    return None


def append_interactive_result(result: dict):
    RESULTS_DIR.mkdir(exist_ok=True)
    with open(INTERACTIVE_FILE, "a") as f:
        f.write(json.dumps(result) + "\n")
