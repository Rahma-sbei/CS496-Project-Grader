# The Grader — Email Quality Evaluation Harness

CS496 AI Engineering project. A dashboard that generates AI emails from a
scenario, judges them against a fixed rubric with a second LLM call, and a
reproducible evaluation harness that runs the same pipeline over a 150+ item
golden dataset, measures LLM-judge reliability against human labels, and
reports cost.

The point of this project is the **evaluation harness**, not the email
generator. Read `postmortem.md` for what actually went wrong while building
it.

---

## 1. Project description

```
User selects category + scenario → LLM generates an email → LLM judge scores
it against a 5-criterion rubric (0-10) → dashboard shows the email, scores,
and reasoning.
```

The same generator + judge pipeline also runs in batch, offline, over the
golden dataset (`python run_eval.py`) to produce reproducible aggregate
statistics, independent of the web UI.

## 2. Architecture

```
frontend/   Next.js + TypeScript + Tailwind dashboard (5 pages)
backend/    FastAPI app - the only thing that holds the API key
harness/    generator.py, judge.py, runner.py, scorer.py, schema.py,
            + the 3 reliability experiments (human_agreement, position_bias,
            verbosity_bias)
data/       scenario catalog, golden/dev/test sets, labeling guide, labels
prompts/    versioned prompt files + changelog
results/    JSONL output from harness runs (generated, not committed)
report/     space for a written report/analysis if you add one
```

The frontend never talks to the LLM directly - every model call happens in
`backend/app/main.py` or `harness/*.py`, so the API key never reaches the
browser. The backend and the CLI harness both import the *same* `harness/`
modules, so "what the dashboard does when you click Evaluate" and "what
`run_eval.py` does for item #47" are guaranteed to be the same code path.

```
frontend (Next.js, :3000)
   │  fetch('/api/...')  → rewritten to backend
   ▼
backend (FastAPI, :8000)
   │  imports
   ▼
harness/ (generator.py, judge.py, schema.py, scorer.py, runner.py)
   │  reads / writes
   ▼
data/*.jsonl, prompts/*.txt, results/*.jsonl
```

## 3. Installation

Requirements: Python 3.10+, Node 18+.

```bash
git clone <this-repo>
cd email-grader
cp .env.example .env        # then add your ANTHROPIC_API_KEY
pip install -r requirements.txt
cd frontend && npm install && cd ..
python data/generate_dataset.py   # regenerates golden_set/dev/test.jsonl (already committed, but reproducible)
```

## 4. Environment variables

Set in `.env` (never committed - see `.gitignore`):

| Variable | Required | Description |
|---|---|---|
| `ANTHROPIC_API_KEY` | Yes | Your Anthropic API key. Used by both the generator and judge. |
| `DEFAULT_MODEL` | No | Overrides the default model (`claude-sonnet-5`) for generation and judging. |

## 5. Running the frontend

```bash
cd frontend
npm run dev
```

Opens at `http://localhost:3000`. It proxies `/api/*` to the backend (see
`frontend/next.config.js`) - the backend must be running too.

## 6. Running the backend

```bash
uvicorn backend.app.main:app --reload --port 8000
```

API docs are auto-generated at `http://localhost:8000/docs`.

## 7. Running the evaluation harness

```bash
python run_eval.py                                  # full golden set (160 items)
python run_eval.py --dataset data/dev.jsonl          # dev set only
python run_eval.py --dataset data/test.jsonl --output test_run
python run_eval.py --limit 10                        # quick smoke test
```

Writes `results/<name>.jsonl` (one line per item, generation + judge output,
or the recorded error if either step failed) and `results/<name>.stats.json`
(aggregate statistics). No item is ever silently dropped - a failed
generation or an invalid judge response is recorded with `status` set to
`generation_failed` or `judge_failed` and the reason in `error`.

### Reliability experiments

```bash
python -m harness.human_agreement                                        # human1 vs human2
python -m harness.human_agreement --results results/full_run.jsonl       # + judge vs human (Experiment A)
python -m harness.position_bias   --results results/full_run.jsonl       # Experiment B
python -m harness.verbosity_bias  --results results/full_run.jsonl       # Experiment C
```

Each writes a JSON report to `results/`, which `GET /api/statistics` reads
and the **Judge Reliability** page renders.

## 8. Dataset description

`data/scenarios.py` is the single source of truth for the 4 categories × 8
scenarios each (32 scenarios). `data/generate_dataset.py` deterministically
expands each scenario into 5 items (different context/tone/length
combinations, fixed random seed) for **160 total items**, then splits them
70/30 into `dev.jsonl` (112 items, used while iterating on prompts) and
`test.jsonl` (48 items, touched only once per prompt version, per
`prompts/CHANGELOG.md`). The split is stratified by category and
reproducible - re-running the generator produces byte-identical output.

## 9. Evaluation methodology

- **Generation**: one Anthropic API call per item, forced structured output
  via a tool call (`generator.py`), prompt in `prompts/generator_v1.txt`.
- **Judging**: one Anthropic API call per item, forced structured output via
  a tool call (`judge.py`), prompt in `prompts/judge_v1.txt`, mirrors the
  rubric in `data/LABELING_GUIDE.md` field-for-field. On an invalid/malformed
  response the harness retries once, then records the failure - it never
  guesses at a score.
- **Human labeling**: two independent evaluators label every golden-set item
  by hand, per `data/LABELING_GUIDE.md`. Agreement is computed with exact
  match, per criterion and overall (`harness/human_agreement.py`).
- **Judge reliability**: three experiments -
  - **A. Human agreement** - judge scores vs. the human-labeled average.
  - **B. Position bias** - same pair of emails compared as (A,B) and (B,A);
    measures how often the verdict flips.
  - **C. Verbosity bias** - an email vs. a padded version with no added
    substance; measures whether padding increases the score.

## 10. Results

Results are not baked into this README because they depend on which model
and prompt version you run. After `python run_eval.py`, check:
- The dashboard's **Judge Reliability** page for human agreement / bias /
  cost, or
- `results/<name>.stats.json` directly.

**Note on the shipped demo data:** `data/human_labels/simulate_human_labels.py`
generates *simulated* human labels so the dashboard isn't empty on a clean
clone. These are clearly not real human judgment - replace them with actual
labels collected per `data/LABELING_GUIDE.md` before treating any numbers
here as real results. See `postmortem.md` for why this project ships without
real human labels.

## 11. Cost model

Cost is estimated from the Anthropic API's reported `input_tokens` /
`output_tokens` per call at the per-model prices in
`harness/llm_client.py::PRICING_PER_MTOK` (update if pricing changes). The
dashboard reports total cost, cost per evaluated email, and extrapolations
to 1,000 and 100× the current dataset size. This is an estimate, not a bill
- always check your Anthropic Console for actual spend.

## 12. Contributions

Solo CS496 project. LLM assistance (Claude) was used for scaffolding this
codebase; the rubric design, dataset scenarios, and methodology choices are
the author's.

## API reference

| Endpoint | Description |
|---|---|
| `POST /api/generate` | Generate one email from a scenario |
| `POST /api/evaluate` | Judge one (scenario, email) pair |
| `POST /api/run-evaluation` | Run the harness over a dataset file |
| `GET /api/results` | List stored results, filterable by category/score/status |
| `GET /api/results/{id}` | One full result |
| `GET /api/statistics` | Dataset counts, performance, human agreement, bias experiments, cost |
| `GET /api/categories` | The scenario catalog |
| `GET /api/prompt-versions` | Available prompt versions + changelog |

## Repository structure

See the tree in the assignment spec / `postmortem.md` - matches exactly.
