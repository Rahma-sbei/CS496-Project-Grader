"""
IMPORTANT: This script produces SIMULATED human labels, not real ones.

Two real human evaluators are a hard requirement of the assignment
(see ../LABELING_GUIDE.md). This script only exists so the dashboard,
`harness/human_agreement.py`, and the demo have non-empty numbers to show
immediately after a clean clone, before real labeling has happened.

Before submitting the assignment, delete human1.jsonl / human2.jsonl and
replace them with real labels collected per LABELING_GUIDE.md.

The simulation works by scoring each golden item with simple heuristics
(does the required info appear, roughly how long is the "email", etc. —
here we don't even have a generated email yet at dataset-build time, so
we instead sample plausible rubric scores from a distribution that mimics
realistic human behavior: mostly high scores, occasional disagreement,
correlated between the two raters but not identical.
"""
import json
import random
from pathlib import Path

SEED_H1 = 101
SEED_H2 = 202
DATA_DIR = Path(__file__).parent.parent

CRITERIA = ["requirement_fulfillment", "accuracy", "tone", "clarity", "conciseness"]


def sample_score(rng, base_quality):
    # base_quality in [0,1] biases toward higher scores, like real emails
    # from a competent generator usually score well with occasional misses.
    r = rng.random()
    if r < base_quality * 0.75:
        return 2
    elif r < base_quality * 0.75 + 0.20:
        return 1
    else:
        return 0


def make_labels(seed, items, disagreement_rate):
    rng = random.Random(seed)
    labels = []
    for item in items:
        base_quality = 0.8 + rng.random() * 0.15
        row = {"id": item["id"]}
        for c in CRITERIA:
            score = sample_score(rng, base_quality)
            # small chance to nudge by 1 to simulate rater disagreement noise
            if rng.random() < disagreement_rate:
                score = max(0, min(2, score + rng.choice([-1, 1])))
            row[c] = score
        labels.append(row)
    return labels


def main():
    items = [json.loads(l) for l in open(DATA_DIR / "golden_set.jsonl")]

    h1 = make_labels(SEED_H1, items, disagreement_rate=0.10)
    h2 = make_labels(SEED_H2, items, disagreement_rate=0.10)

    with open(DATA_DIR / "human_labels" / "human1.jsonl", "w") as f:
        for row in h1:
            f.write(json.dumps(row) + "\n")
    with open(DATA_DIR / "human_labels" / "human2.jsonl", "w") as f:
        for row in h2:
            f.write(json.dumps(row) + "\n")

    print(f"Wrote SIMULATED labels for {len(items)} items to human1.jsonl / human2.jsonl")
    print("Replace these with real human labels before submitting the assignment.")


if __name__ == "__main__":
    main()
