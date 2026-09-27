"""
tools/label.py — label new golden-set items in the terminal, then merge the
two labellers' work into data/golden_set.jsonl.

  python tools/label.py label --labeler 1    # person 1 labels (resumes where they stopped)
  python tools/label.py label --labeler 2    # person 2 labels, on their own, without looking at 1
  python tools/label.py merge                # reconcile disagreements, append to golden_set.jsonl

Reads data/new_items.jsonl. Labels are saved after every item to
data/labels/labeler_<n>.jsonl. Rules follow data/labelling_guide.md.
"""
import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from harness.schema import ALL_RULE_PATHS  # noqa: E402

NEW_ITEMS = ROOT / "data" / "new_items.jsonl"
LABELS_DIR = ROOT / "data" / "labels"
GOLDEN = ROOT / "data" / "golden_set.jsonl"
DROPPED = ROOT / "data" / "dropped_items.jsonl"


def load(path):
    if not path.exists():
        return []
    return [json.loads(l) for l in path.read_text(encoding="utf-8").splitlines() if l.strip()]


def append(path, row):
    path.parent.mkdir(exist_ok=True)
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(row, ensure_ascii=False) + "\n")


def empty_label():
    label = {}
    for band, field in ALL_RULE_PATHS:
        label.setdefault(band, {})[field] = True
    return label


def ask(prompt, valid=None):
    while True:
        ans = input(prompt).strip()
        if valid is None or ans in valid:
            return ans
        print(f"  please type one of: {', '.join(sorted(valid))}")


def label(labeler):
    out = LABELS_DIR / f"labeler_{labeler}.jsonl"
    done = {r["id"] for r in load(out)}
    todo = [it for it in load(NEW_ITEMS) if it["id"] not in done]
    print(f"{len(done)} done, {len(todo)} to go. Rules: data/labelling_guide.md\n")
    for n, it in enumerate(todo, 1):
        print("=" * 72)
        print(f"[{n}/{len(todo)}] {it['id']}")
        print("BRIEF:", json.dumps(it["brief"], ensure_ascii=False, indent=2))
        print("-" * 72)
        print(it["candidate_email"])
        print("-" * 72)
        for i, (band, field) in enumerate(ALL_RULE_PATHS, 1):
            print(f"  {i:2}. {band}.{field}")
        ans = input("Numbers of FAILED rules, comma-separated (Enter = all pass, d = drop item, q = quit): ").strip()
        if ans == "q":
            return
        if ans == "d":
            append(out, {"id": it["id"], "dropped": input("Why drop it? ").strip() or "no reason given"})
            continue
        lab = empty_label()
        for tok in filter(None, (t.strip() for t in ans.split(","))):
            if not tok.isdigit() or not 1 <= int(tok) <= len(ALL_RULE_PATHS):
                print(f"  ignored '{tok}'")
                continue
            band, field = ALL_RULE_PATHS[int(tok) - 1]
            lab[band][field] = False
        lab["overall_score"] = int(ask("overall_score 1-5: ", {"1", "2", "3", "4", "5"}))
        lab["notes"] = input("Short note (optional): ").strip()
        append(out, {"id": it["id"], "label": lab})


def merge():
    l1 = {r["id"]: r for r in load(LABELS_DIR / "labeler_1.jsonl")}
    l2 = {r["id"]: r for r in load(LABELS_DIR / "labeler_2.jsonl")}
    already = {r["id"] for r in load(GOLDEN)} | {r["id"] for r in load(DROPPED)}
    merged = dropped = waiting = 0
    for it in load(NEW_ITEMS):
        if it["id"] in already:
            continue
        a, b = l1.get(it["id"]), l2.get(it["id"])
        if not a or not b:
            waiting += 1
            continue
        if "dropped" in a or "dropped" in b:
            reason = " / ".join(x["dropped"] for x in (a, b) if "dropped" in x)
            append(DROPPED, {"id": it["id"], "reason": reason})
            dropped += 1
            continue
        la, lb = a["label"], b["label"]
        rec, disagreements = empty_label(), []
        for band, field in ALL_RULE_PATHS:
            if la[band][field] == lb[band][field]:
                rec[band][field] = la[band][field]
            else:
                disagreements.append(f"{band}.{field}")
        score_differs = la["overall_score"] != lb["overall_score"]
        if disagreements or score_differs:
            print("=" * 72)
            print(it["id"], json.dumps(it["brief"], ensure_ascii=False))
            print(it["candidate_email"])
            print(f"  notes 1: {la.get('notes')}\n  notes 2: {lb.get('notes')}")
            for path in disagreements:
                band, field = path.split(".")
                ans = ask(f"  {path}: labeler_1={la[band][field]} labeler_2={lb[band][field]} -> final (t/f): ", {"t", "f"})
                rec[band][field] = ans == "t"
        if score_differs:
            rec["overall_score"] = int(ask(f"  overall_score: labeler_1={la['overall_score']} labeler_2={lb['overall_score']} -> final: ",
                                           {"1", "2", "3", "4", "5"}))
        else:
            rec["overall_score"] = la["overall_score"]
        if disagreements or score_differs:
            rec["resolution_note"] = input("  resolution_note (what you decided and why): ").strip()
        append(GOLDEN, {
            "id": it["id"], "brief": it["brief"], "candidate_email": it["candidate_email"],
            "human_labels": {"labeler_1": la, "labeler_2": lb}, "reconciled_label": rec,
            "split": it["split"], "violation_injected": it["violation_injected"],
            "disagreement_flag": bool(disagreements or score_differs),
        })
        merged += 1
    print(f"\nmerged {merged}, dropped {dropped}, still waiting for a second label: {waiting}")


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    sub = p.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("label")
    s.add_argument("--labeler", required=True, choices=["1", "2"])
    sub.add_parser("merge")
    args = p.parse_args()
    label(args.labeler) if args.cmd == "label" else merge()
