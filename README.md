# Project 1 — The Grader (CS496 AI Engineering)

An evaluation harness, an LLM judge, and a prompted system for one task:
**writing professional emails that follow a 12-rule style guide.**

- The **system under test** writes an email from a short brief: recipient,
  relationship, purpose, key points, and an optional sender.
- The **LLM judge** grades each email against the style guide. There are 12
  pass/fail rules in 4 bands (structure, tone, content, form), plus an
  overall 1–5 score and a short reason, all in a fixed JSON schema.
- The **harness** runs any system/judge version on the data with one command
  and writes one result row per item plus a summary to `results/`.

Exact match does not work for this task: many different emails are
correct for the same brief. That is why we need a validated judge.

| Document | What it contains |
|---|---|
| [`report.pdf`](report.pdf) | The 4-page report: task, golden set, harness, judge reliability, system score history, cost model |
| [`postmortem.md`](postmortem.md) | What went wrong and what we learned |
| [`prompts/CHANGELOG.md`](prompts/CHANGELOG.md) | Every prompt version, linked to the score before and after |
| [`data/labelling_guide.md`](data/labelling_guide.md) | The labelling rules used by the human labellers and the judge |

---

## Team and contributions

| Member | Contributions |
|---|---|
| Nadia Ben Njima | _…_ |
| Ahmed Brini | _…_ |
| Rahma Sbei | _…_ |
| Mariem Lahmer | _…_ |

---

## Repository layout

```
data/
  golden_set.jsonl      50 human-labelled items (brief + candidate email + 2 labels + reconciled label), dev/test split
  briefs.jsonl          30 briefs for the system under test (20 dev / 10 test), distinct from the golden set
  labelling_guide.md    the 12 rules and the 1-5 score definition
harness/
  runner.py             command-line entry point (all modes below)
  system.py             the system under test: brief -> {"subject", "email"}
  judge.py              the LLM judge + the verbosity- and order-bias probes
  scorer.py             turns per-item rows into summary numbers (counts and rates)
  schema.py             the fixed JSON contracts for the judge and the system
  rule_checks.py        deterministic checks next to the judge (unfilled placeholders)
  llm_client.py         Groq client for the JUDGE      (model: GROQ_MODEL)
  llm_client_sys.py     Groq client for the SYSTEM     (model: GROQ_MODEL_SYS)
prompts/
  judge_prompt_v1..v3.txt    judge prompts (v3 is locked)
  system_prompt_v1..v2.txt   system prompts (v2 is current)
  CHANGELOG.md               every prompt change + before/after scores
results/                one .jsonl (per item) + one _summary .json per run
docs/report.html        source of report.pdf
report.pdf              the report
postmortem.md           what went wrong and what we learned
```

---

## Setup

Requirements: **Python 3.12** and a **Groq API key**
(https://console.groq.com → API Keys). Everything else is in `requirements.txt`.

### 1. Clone and create a virtual environment

Windows (PowerShell):
```powershell
git clone <repo-url>
cd CS496-Project-Grader
python -m venv venv
venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

macOS / Linux:
```bash
git clone <repo-url>
cd CS496-Project-Grader
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

If PowerShell blocks `Activate.ps1`, you can skip activation. Call the
venv's Python directly instead, e.g. `venv\Scripts\python.exe -m harness.runner ...`.

### 2. Add your API key

Copy the example file and put your key in it:

```powershell
copy .env.example .env        # Windows
```
```bash
cp .env.example .env          # macOS / Linux
```

Then edit `.env`:

```
GROQ_API_KEY=gsk_your_key_here
GROQ_MODEL=openai/gpt-oss-120b      # judge model (locked with judge_prompt_v3)
GROQ_MODEL_SYS=qwen/qwen3.8-27b     # system model (different family from the judge)
```

`.env` is git-ignored. **Never commit a real key.** The harness stops with
a clear message if the key is missing, instead of sending failing requests.

**Do not set `GROQ_MODEL` and `GROQ_MODEL_SYS` to the same model or model
family.** A judge that grades its own model's writing scores it too
generously (self-preference bias; see the report, §5).

### 3. Check the setup (no API calls)

```bash
python -m harness.runner label-agreement
```

This computes inter-labeller agreement on the golden set and writes it to
`results/`. If it runs, the setup is correct.

---

## Running

**The one run command.** It runs the current system (prompt v2) on the
held-out test briefs and grades them with the locked judge (v3):

```bash
python -m harness.runner run-system --split test
```

The defaults are the current versions: `--system-version v2`,
`--judge-version v3`. Every command accepts `--limit N` to try a few items
first.

### The full pipeline, in order

| # | Step | Command | API calls |
|---|---|---|---|
| 1 | Inter-labeller agreement on the golden set | `python -m harness.runner label-agreement` | 0 |
| 2 | Validate the judge against human labels (dev) | `python -m harness.runner validate-judge --judge-version v3 --split dev` | 35 |
| 3 | Judge bias checks (verbosity + order) | `python -m harness.runner check-judge-bias --judge-version v3 --limit 20` | 3 per item |
| 4 | System score on dev (iterate prompts here) | `python -m harness.runner run-system --system-version v2 --split dev` | 2 per brief (40) |
| 5 | **Final:** system score on test (once) | `python -m harness.runner run-system --system-version v2 --split test` | 20 |
| 6 | **Final:** judge reliability on test (once) | `python -m harness.runner validate-judge --judge-version v3 --split test` | 15 |

Rules we follow (see `prompts/CHANGELOG.md`, "Evaluation workflow"):

- The judge is evaluated **only** against the human labels (step 2), plus
  the bias checks (step 3). Then it is **locked**. Changing the judge prompt
  or the judge model reopens the lock.
- System prompts are compared with the locked judge on **dev** (step 4).
- The **test** split is used once, at the end (steps 5–6).
- Every prompt change is logged in `prompts/CHANGELOG.md` with its score
  before and after.

### Rate limits

Groq enforces requests- and tokens-per-minute/day limits, and the free tier
is low. What we learned:

- Don't run two commands against the same model at the same time.
- `check-judge-bias` is the most expensive command (3 judge calls per
  item). Run it in batches and resume with `--start`:
  ```bash
  python -m harness.runner check-judge-bias --start 1  --limit 10
  python -m harness.runner check-judge-bias --start 11 --limit 10
  ```
- If you press Ctrl-C or a run crashes, every finished item is still
  written to `results/`, and failed calls print their error reason.

### Adding a new prompt version

1. Copy the latest prompt to a new version file, e.g.
   `prompts/system_prompt_v3.txt`, and make **one** targeted change. Keep the
   `<<BRIEF_JSON>>` (and, for the judge, `<<EMAIL_TEXT>>`) placeholders.
2. Run it on dev: `python -m harness.runner run-system --system-version v3 --split dev`.
3. Record what changed, why, and the before/after numbers in `prompts/CHANGELOG.md`.

---

## Output files

Each run writes two files to `results/`:

- `<mode>_<version>_<timestamp>.jsonl`: one row per item. For
  `run-system` a row has `input` (brief), `system_output`,
  `judge_verdict` (12 booleans + `overall_score` + `reason`),
  `rule_checks`, `split`, `tests`, and `_meta` (model, latency, tokens).
- `<mode>_summary_<version>_<timestamp>.json`: counts and rates. These
  include per-rule pass rate or agreement, score distribution, per-brief-tag
  breakdown, placeholder counts, latency and tokens.

---

## Results (details in `report.pdf` and `prompts/CHANGELOG.md`)

| What | Result |
|---|---|
| Inter-labeller agreement (50 items) | 590/600 rule labels agree (98.3%); overall score exact 40/50 (80%), within 1 50/50; 0 items dropped |
| Judge v3 vs humans (dev, n=35) | score exact 12/35 (34.3%), within 1 33/35 (94.3%); per-rule agreement 77–100% |
| Judge bias (v3, partial n=7) | padding raised the score 0/7; swapping order changed the score 0/7 |
| System v1 on dev (n=20) | judge average 4.80; 7/20 emails add content not in the brief |
| System v2 on dev (n=20) | judge average 4.95; 0/20 add content; 15/15 sender rule followed |
| **System v2 on test (n=10)** | **judge average 4.40 (5×8, 2×2); both 2s are judge false positives; 0/10 placeholders** |
| Cost (system + judge) | ≈ $1.59 per 1,000 emails; ≈ $159 at 100× volume |

Known judge limitations (report §4): the judge is lenient on subtle
additions and placeholders, and it produces false "wrong name" failures on
correct "Title Surname" greetings. Its score bands have no band for a
correct_names failure.

---

## Regenerating `report.pdf`

The report source is `docs/report.html`. Edit it (for example, to fill in
the team names), then print it to PDF with Edge or Chrome in headless mode.

Windows:
```powershell
& "C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe" --headless=new --no-pdf-header-footer --print-to-pdf="$PWD\report.pdf" "$PWD\docs\report.html"
```

macOS:
```bash
"/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" --headless=new --no-pdf-header-footer --print-to-pdf="$PWD/report.pdf" "$PWD/docs/report.html"
```

You can also open `docs/report.html` in a browser and use Print → Save as
PDF with headers and footers turned off. The report must stay within 4
pages; it is currently 3.

---

## No secrets in the repo

API keys live only in `.env` (git-ignored). `.env.example` contains
placeholders only.
