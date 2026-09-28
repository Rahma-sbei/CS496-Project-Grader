"""
FastAPI backend for The Grader.

Run with:
    uvicorn backend.app.main:app --reload --port 8000

All LLM calls happen here or in harness/*, never in the frontend, so the
API key never reaches the browser.
"""
import json
import sys
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

REPO_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(REPO_ROOT))

from dotenv import load_dotenv  # noqa: E402

load_dotenv(REPO_ROOT / ".env")

from data.scenarios import CATEGORIES  # noqa: E402
from harness import generator, judge, scorer  # noqa: E402
from harness.runner import run_evaluation, load_dataset  # noqa: E402
from backend.app import results_store  # noqa: E402

app = FastAPI(title="The Grader API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------
class ScenarioInput(BaseModel):
    category: str
    scenario: str
    recipient: str
    purpose: str
    context: str
    required_information: list[str]
    tone: str
    max_length: str
    generator_version: Optional[str] = "v1"
    model: Optional[str] = None


class EvaluateRequest(BaseModel):
    scenario: ScenarioInput
    generated_email: dict
    judge_version: Optional[str] = "v1"
    model: Optional[str] = None


class RunEvaluationRequest(BaseModel):
    dataset: Optional[str] = "data/golden_set.jsonl"
    output_name: Optional[str] = None
    generator_version: Optional[str] = "v1"
    judge_version: Optional[str] = "v1"
    model: Optional[str] = None
    limit: Optional[int] = None


# ---------------------------------------------------------------------------
# Categories
# ---------------------------------------------------------------------------
@app.get("/api/categories")
def get_categories():
    return {"categories": CATEGORIES}


# ---------------------------------------------------------------------------
# Interactive generate / evaluate (the "Evaluate" page)
# ---------------------------------------------------------------------------
@app.post("/api/generate")
def api_generate(payload: ScenarioInput):
    item = payload.model_dump()
    gen = generator.generate_email(
        item, prompt_version=payload.generator_version, model=payload.model
    )
    if gen["error"]:
        raise HTTPException(status_code=502, detail=gen["error"])
    return {"email": gen["email"], "usage": gen["usage"]}


@app.post("/api/evaluate")
def api_evaluate(payload: EvaluateRequest):
    item = payload.scenario.model_dump()
    jr = judge.evaluate_email(
        item, payload.generated_email, prompt_version=payload.judge_version, model=payload.model
    )
    if jr["error"]:
        raise HTTPException(status_code=502, detail=jr["error"])

    result = {
        "id": f"interactive_{uuid.uuid4().hex[:10]}",
        "input": item,
        "generated_email": payload.generated_email,
        "scores": jr["scores"],
        "total_score": jr["scores"]["total_score"],
        "reason": jr["scores"]["reason"],
        "status": "ok",
        "error": None,
        "judge_usage": jr["usage"],
        "generation_usage": None,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    results_store.append_interactive_result(result)
    return result


# ---------------------------------------------------------------------------
# Batch harness run over the golden dataset (or dev/test subsets)
# ---------------------------------------------------------------------------
@app.post("/api/run-evaluation")
def api_run_evaluation(payload: RunEvaluationRequest):
    dataset_path = REPO_ROOT / payload.dataset
    if not dataset_path.exists():
        raise HTTPException(status_code=400, detail=f"Dataset not found: {payload.dataset}")

    output_name = payload.output_name or f"run_{int(time.time())}"
    outcome = run_evaluation(
        dataset_path=str(dataset_path),
        output_name=output_name,
        generator_version=payload.generator_version,
        judge_version=payload.judge_version,
        model=payload.model,
        limit=payload.limit,
    )
    return {
        "output_name": output_name,
        "statistics": outcome["statistics"],
        "n_results": len(outcome["results"]),
    }


# ---------------------------------------------------------------------------
# Results
# ---------------------------------------------------------------------------
@app.get("/api/results")
def api_list_results(category: Optional[str] = None, min_score: Optional[int] = None, status: Optional[str] = None):
    rows = results_store.load_all_results()
    if category:
        rows = [r for r in rows if r["input"].get("category") == category]
    if min_score is not None:
        rows = [r for r in rows if (r.get("total_score") or 0) >= min_score]
    if status:
        rows = [r for r in rows if r.get("status") == status]
    return {"results": rows, "count": len(rows)}


@app.get("/api/results/{item_id}")
def api_get_result(item_id: str):
    row = results_store.get_result(item_id)
    if not row:
        raise HTTPException(status_code=404, detail="Result not found")
    return row


# ---------------------------------------------------------------------------
# Statistics / dashboard
# ---------------------------------------------------------------------------
@app.get("/api/statistics")
def api_statistics():
    rows = results_store.load_all_results()
    stats = scorer.compute_statistics(rows)

    dataset_counts = {}
    for name in ["golden_set", "dev", "test"]:
        path = REPO_ROOT / "data" / f"{name}.jsonl"
        if path.exists():
            dataset_counts[name] = len(load_dataset(str(path)))

    human_agreement = None
    ha_path = REPO_ROOT / "results" / "human_agreement.json"
    if ha_path.exists():
        human_agreement = json.loads(ha_path.read_text())

    position_bias = None
    pb_path = REPO_ROOT / "results" / "position_bias.json"
    if pb_path.exists():
        position_bias = json.loads(pb_path.read_text())

    verbosity_bias = None
    vb_path = REPO_ROOT / "results" / "verbosity_bias.json"
    if vb_path.exists():
        verbosity_bias = json.loads(vb_path.read_text())

    return {
        "dataset": dataset_counts,
        "performance": stats,
        "human_agreement": human_agreement,
        "position_bias": position_bias,
        "verbosity_bias": verbosity_bias,
    }


@app.get("/api/prompt-versions")
def api_prompt_versions():
    prompts_dir = REPO_ROOT / "prompts"
    versions = sorted({p.stem.split("_")[-1] for p in prompts_dir.glob("generator_*.txt")})
    changelog = (prompts_dir / "CHANGELOG.md").read_text() if (prompts_dir / "CHANGELOG.md").exists() else ""
    return {"versions": versions, "changelog": changelog}


@app.get("/api/health")
def health():
    return {"status": "ok"}
