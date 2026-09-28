"""
Experiment C — Verbosity bias.

Takes already-generated emails from a prior run_eval.py output, creates a
padded version of each (unnecessary filler added, no new information), then
runs the *same* per-item judge (judge.py) on both versions and compares
scores. If the judge rewards length over substance, padded scores will be
higher than original scores.

    python -m harness.verbosity_bias --results results/full_run.jsonl --n 20
"""
import argparse
import json
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent / ".env")

from . import judge

REPO_ROOT = Path(__file__).parent.parent

FILLER_OPENERS = [
    "I hope this email finds you well and that things have been going smoothly on your end. ",
    "I wanted to take a moment to reach out regarding the following matter, which I believe is important to address. ",
]
FILLER_CLOSERS = [
    " Once again, I really do appreciate your time and attention to this matter, and I look forward to hearing from you whenever it is convenient for you.",
    " Please don't hesitate to let me know if there is anything else at all that you might need from my side in order to move forward with this.",
]
FILLER_MID = (
    " As I'm sure you can understand, situations like this one can sometimes be a little bit "
    "complicated, and I just wanted to make sure I was being as clear and thorough as possible "
    "in explaining everything to you."
)


def pad_email(email: dict) -> dict:
    padded = dict(email)
    padded["greeting"] = email["greeting"]
    padded["body"] = (
        FILLER_OPENERS[0] + email["body"] + FILLER_MID + FILLER_CLOSERS[0]
    )
    return padded


def main(argv=None):
    parser = argparse.ArgumentParser(description="Run the verbosity-bias experiment")
    parser.add_argument("--results", required=True)
    parser.add_argument("--n", type=int, default=20)
    parser.add_argument("--model", default=None)
    parser.add_argument("--output", default=str(REPO_ROOT / "results" / "verbosity_bias.json"))
    args = parser.parse_args(argv)

    results = [json.loads(l) for l in open(args.results) if json.loads(l).get("status") == "ok"]
    subset = results[: args.n]

    cases = []
    increased = 0
    n_valid = 0
    for r in subset:
        item = r["input"]
        original_email = r["generated_email"]
        padded_email = pad_email(original_email)

        original_score = r["total_score"]  # reuse the already-computed judge score
        padded_result = judge.evaluate_email(item, padded_email, model=args.model)

        if padded_result["error"] or not padded_result["scores"]:
            cases.append({"id": r["id"], "error": padded_result["error"]})
            continue

        padded_score = padded_result["scores"]["total_score"]
        diff = padded_score - original_score
        if diff > 0:
            increased += 1
        n_valid += 1

        cases.append(
            {
                "id": r["id"],
                "original_score": original_score,
                "padded_score": padded_score,
                "score_diff": diff,
                "original_word_count": len(original_email["body"].split()),
                "padded_word_count": len(padded_email["body"].split()),
            }
        )

    pct_increased = round(100 * increased / n_valid, 1) if n_valid else None

    output = {
        "n_tested": len(cases),
        "n_valid": n_valid,
        "n_padding_increased_score": increased,
        "pct_padding_increased_score": pct_increased,
        "cases": cases,
    }
    Path(args.output).parent.mkdir(exist_ok=True)
    with open(args.output, "w") as f:
        json.dump(output, f, indent=2)

    print(f"Tested {len(cases)} items, {n_valid} valid.")
    print(f"Padding increased the score in {increased} cases ({pct_increased}%).")
    print(f"Wrote report to {args.output}")


if __name__ == "__main__":
    main()
