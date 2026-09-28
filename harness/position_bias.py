"""
Experiment B — Position bias.

Takes pairs of already-generated emails (from a prior run_eval.py output),
pairs up items within the same scenario, and asks the judge to pick the
better email twice: once as (A=first item, B=second item) and once swapped
(A=second item, B=first item). If the judge is unbiased, the *content*
winner shouldn't change just because of presentation order.

    python -m harness.position_bias --results results/full_run.jsonl --pairs 30
"""
import argparse
import json
import random
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent / ".env")

from . import llm_client

REPO_ROOT = Path(__file__).parent.parent
PROMPTS_DIR = REPO_ROOT / "prompts"

COMPARE_TOOL_SCHEMA = {
    "type": "object",
    "properties": {
        "winner": {"type": "string", "enum": ["A", "B", "tie"]},
        "reason": {"type": "string", "description": "1-2 sentence justification"},
    },
    "required": ["winner", "reason"],
}


def load_prompt() -> str:
    path = PROMPTS_DIR / "judge_pairwise_v1.txt"
    return path.read_text()


def email_text(email: dict) -> str:
    return f"Subject: {email['subject']}\n\n{email['greeting']}\n\n{email['body']}\n\n{email['closing']}"


def compare(item: dict, email_a: dict, email_b: dict, model: str = None) -> dict:
    system = load_prompt()
    required = "\n".join(f"- {r}" for r in item["required_information"])
    user_message = (
        f"Scenario: {item['scenario']}\nRecipient: {item['recipient']}\n"
        f"Context: {item['context']}\nRequired information:\n{required}\n\n"
        f"## Email A\n{email_text(email_a)}\n\n## Email B\n{email_text(email_b)}\n"
    )
    result = llm_client.call_with_tool(
        system=system,
        user_message=user_message,
        tool_name="pick_winner",
        tool_description="Pick which email better satisfies the scenario.",
        tool_input_schema=COMPARE_TOOL_SCHEMA,
        model=model,
        max_tokens=300,
    )
    return llm_client.extract_tool_input(result, "pick_winner")


def build_pairs(results: list[dict], n_pairs: int, seed: int = 7) -> list[tuple]:
    ok = [r for r in results if r.get("status") == "ok"]
    by_scenario = {}
    for r in ok:
        by_scenario.setdefault(r["input"]["scenario_id"], []).append(r)

    rng = random.Random(seed)
    pairs = []
    scenario_ids = list(by_scenario.keys())
    rng.shuffle(scenario_ids)
    for sid in scenario_ids:
        items = by_scenario[sid]
        if len(items) >= 2:
            rng.shuffle(items)
            pairs.append((items[0], items[1]))
        if len(pairs) >= n_pairs:
            break
    return pairs


def main(argv=None):
    parser = argparse.ArgumentParser(description="Run the position-bias experiment")
    parser.add_argument("--results", required=True, help="Path to a run_eval.py results/*.jsonl file")
    parser.add_argument("--pairs", type=int, default=20)
    parser.add_argument("--model", default=None)
    parser.add_argument("--output", default=str(REPO_ROOT / "results" / "position_bias.json"))
    args = parser.parse_args(argv)

    results = [json.loads(l) for l in open(args.results)]
    pairs = build_pairs(results, args.pairs)

    cases = []
    flips = 0
    for r1, r2 in pairs:
        e1, e2 = r1["generated_email"], r2["generated_email"]
        item = r1["input"]  # both share the same scenario/context shape closely enough for comparison

        try:
            first_order = compare(item, e1, e2, model=args.model)  # A=e1, B=e2
            second_order = compare(item, e2, e1, model=args.model)  # A=e2, B=e1
        except llm_client.LLMError as e:
            cases.append({"pair": [r1["id"], r2["id"]], "error": str(e)})
            continue

        # Map back to "which underlying item won" for both orderings
        winner_first_order = {"A": r1["id"], "B": r2["id"], "tie": "tie"}[first_order["winner"]]
        winner_second_order = {"A": r2["id"], "B": r1["id"], "tie": "tie"}[second_order["winner"]]
        flipped = winner_first_order != winner_second_order
        if flipped:
            flips += 1

        cases.append(
            {
                "pair": [r1["id"], r2["id"]],
                "winner_original_order": winner_first_order,
                "winner_swapped_order": winner_second_order,
                "flipped": flipped,
            }
        )

    n_valid = len([c for c in cases if "error" not in c])
    flip_rate = round(100 * flips / n_valid, 1) if n_valid else None

    output = {
        "n_pairs_tested": len(cases),
        "n_valid": n_valid,
        "n_flipped": flips,
        "flip_rate_pct": flip_rate,
        "cases": cases,
    }
    Path(args.output).parent.mkdir(exist_ok=True)
    with open(args.output, "w") as f:
        json.dump(output, f, indent=2)

    print(f"Tested {len(cases)} pairs, {n_valid} valid comparisons.")
    print(f"Verdict flipped after swapping order in {flips} cases ({flip_rate}%).")
    print(f"Wrote report to {args.output}")


if __name__ == "__main__":
    main()
