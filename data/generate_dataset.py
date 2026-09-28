"""
Generates the golden dataset from the scenario catalog in scenarios.py.

Usage:
    python generate_dataset.py

This is deterministic (fixed seed, fixed ordering) so re-running it produces
the exact same golden_set.jsonl / dev.jsonl / test.jsonl every time - required
so prompt-development scores and test scores stay comparable across runs.
"""
import json
import random
from pathlib import Path

from scenarios import CATEGORIES, TONES, CONTEXTS_BY_CATEGORY, MAX_LENGTHS

SEED = 42
ITEMS_PER_SCENARIO = 5  # 32 scenarios * 5 = 160 items, satisfies the 150+ requirement
DEV_FRACTION = 0.7

OUT_DIR = Path(__file__).parent


def build_items():
    rng = random.Random(SEED)
    items = []
    counter = 1
    for category in CATEGORIES:
        cat_id = category["id"]
        contexts = CONTEXTS_BY_CATEGORY[cat_id]
        for scenario in category["scenarios"]:
            for i in range(ITEMS_PER_SCENARIO):
                item_id = f"email_{counter:03d}"
                context = contexts[i % len(contexts)]
                tone = TONES[rng.randrange(len(TONES))]
                max_length = MAX_LENGTHS[rng.randrange(len(MAX_LENGTHS))]
                items.append(
                    {
                        "id": item_id,
                        "category": cat_id,
                        "scenario": scenario["label"],
                        "scenario_id": scenario["id"],
                        "recipient": scenario["recipient"],
                        "purpose": scenario["purpose"],
                        "context": context,
                        "required_information": scenario["required_information"],
                        "tone": tone,
                        "max_length": max_length,
                    }
                )
                counter += 1
    return items


def split_items(items):
    # Reproducible split: shuffle with fixed seed, then slice. Stratified by
    # category so dev/test both cover all four categories proportionally.
    by_category = {}
    for item in items:
        by_category.setdefault(item["category"], []).append(item)

    rng = random.Random(SEED + 1)
    dev, test = [], []
    for cat_items in by_category.values():
        cat_items = cat_items[:]
        rng.shuffle(cat_items)
        split_at = round(len(cat_items) * DEV_FRACTION)
        dev.extend(cat_items[:split_at])
        test.extend(cat_items[split_at:])

    dev.sort(key=lambda x: x["id"])
    test.sort(key=lambda x: x["id"])
    return dev, test


def write_jsonl(path, items):
    with open(path, "w") as f:
        for item in items:
            f.write(json.dumps(item) + "\n")


def main():
    items = build_items()
    dev, test = split_items(items)

    write_jsonl(OUT_DIR / "golden_set.jsonl", items)
    write_jsonl(OUT_DIR / "dev.jsonl", dev)
    write_jsonl(OUT_DIR / "test.jsonl", test)

    print(f"Golden set: {len(items)} items")
    print(f"Dev set:    {len(dev)} items")
    print(f"Test set:   {len(test)} items")
    for cat in CATEGORIES:
        n = sum(1 for i in items if i["category"] == cat["id"])
        print(f"  {cat['label']}: {n} items")


if __name__ == "__main__":
    main()
