#!/usr/bin/env python3
"""
Entry point for running the full evaluation harness, per the assignment spec:

    python run_eval.py
    python run_eval.py --dataset data/test.jsonl --output test_run
    python run_eval.py --limit 10   # quick smoke test

See harness/runner.py for the implementation.
"""
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).parent / ".env")

from harness.runner import main  # noqa: E402

if __name__ == "__main__":
    main()
