# The Grader: email style-guide compliance (CS496 Project 1)

**Task.** An LLM writes a professional email from a short brief (recipient,
relationship, purpose, key points). Many different emails are correct, so
exact match can't grade it. We grade each email against a 12-rule style
guide (`data/labelling_guide.md`) using a golden set labelled by two people
and an LLM judge whose agreement with those labels we measure.

## Setup (one command)

```bash
python -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt && cp .env.example .env
```

Then open `.env` and put your Groq key in `GROQ_API_KEY`. `.env` is in
`.gitignore`; never commit it.

## Run (one command per job)

```bash
python -m harness.runner run-system --system-version v1 --judge-version v3 --split test
```

| Command | What it does | API calls |
|---|---|---|
| `python -m harness.runner label-agreement` | Agreement between the two human labellers | none |
| `python -m harness.runner validate-judge --judge-version v3 --split dev` | Judge vs human labels, per item | 1 per item |
| `python -m harness.runner check-judge-bias --judge-version v3 --pairwise-version v1 --split dev` | Verbosity (padding) and position (A/B swap) bias | 2 per item + 2 per pair |
| `python -m harness.runner run-system --system-version v1 --judge-version v3 --split dev` | System writes emails, judge grades them | 2 per brief |

Add `--limit 5` to any command for a quick, cheap try. Every run writes one
row per item (`input`, `output`, `score`, `reason`, full verdict) to
`results/<kind>_<versions>_<timestamp>.jsonl` and a summary with counts,
percentages, latency and cost to `results/<kind>_summary_..._<timestamp>.json`.

## Repo layout

```
data/        golden_set.jsonl (labelled), new_items.jsonl (waiting for labels),
             briefs.jsonl (40 unique briefs + split), labelling_guide.md
harness/     runner.py (CLI), system.py (email writer), judge.py (judge + bias probes),
             scorer.py (metrics + cost), schema.py (fixed JSON schemas), llm_client*.py
prompts/     system_prompt_vN.txt, judge_prompt_vN.txt, judge_pairwise_v1.txt, CHANGELOG.md
tools/       label.py (two-person labelling + merge)
results/     per-item results of every run
report.pdf   max 4 pages      postmortem.md
```

Models (Groq, set in `.env`): judge `openai/gpt-oss-120b`, system
`openai/gpt-oss-20b`. Both at temperature 0, JSON output enforced with
`response_format={"type": "json_object"}` and checked by `harness/schema.py`.

## Results

Fill in from `results/*summary*.json` after the final runs.

| Measure | Value |
|---|---|
| Golden set | 150 items (90 dev / 60 test), N dropped |
| Labeller agreement (all 12 rules equal) | x / 150 (x%) |
| Judge vs humans, test set: overall score within 1 | x / 60 (x%) |
| Judge vs humans, test set: per-rule agreement (range) | x%-x% |
| Position bias: verdict flipped after swap | x / N pairs (x%) |
| Verbosity bias: score went up after padding | x / N (x%) |
| System v1 → vN on test: average score | x → x |
| Judge cost per 1k items (today / at 100× volume) | $x / $x |
| System cost per 1k emails (today / at 100× volume) | $x / $x |

Score history for every prompt version: `prompts/CHANGELOG.md`.

## Contributions

- **Rahma Sbei**: TODO
- **Ahmed Brini**: TODO
- **Member 3**: TODO
- **Member 4**: TODO
