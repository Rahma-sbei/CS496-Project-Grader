# Postmortem

Honest account of what went wrong (or is still unresolved) building The
Grader, for the write-up requirement in the assignment spec.

## 1. Human labels are simulated, not real - this is the biggest gap

The assignment requires two human evaluators to independently label every
golden-set item. This repository ships `data/human_labels/simulate_human_labels.py`,
which generates *statistically plausible but entirely synthetic* labels so
the dashboard and the human-agreement/judge-agreement pipeline have
something to show immediately after cloning. **These are not real human
judgments** and the agreement numbers they produce should not be reported
as this project's actual human-agreement results. Before submitting:

1. Delete `data/human_labels/human1.jsonl` and `human2.jsonl`.
2. Have two people independently label the golden set per
   `data/LABELING_GUIDE.md`.
3. Re-run `python -m harness.human_agreement`.

Shipping a working pipeline with clearly-labeled placeholder data seemed
more honest than either leaving the dashboard empty or quietly presenting
synthetic numbers as real - but it's a real limitation, not a solved
problem, and it's called out here so it doesn't get missed.

## 2. Structured output reliability took more than one attempt

Early on, asking the judge model to "return JSON" in plain text produced
outputs that were *almost* valid JSON - trailing commentary before/after the
JSON block, occasional markdown code fences, one run where it explained its
reasoning before the JSON object instead of after. Switching to forced tool
use (`tool_choice: {"type": "tool", "name": "submit_scores"}`) in
`harness/llm_client.py` fixed this completely - the model can no longer
respond with anything except a call to that tool, so `schema.py`'s validator
only ever has to deal with type/range errors, not parsing errors. The
retry-once-then-record-failure behavior in `judge.py` exists for the
type/range case (e.g. the model returning `3` for a 0-2 field), which still
happens occasionally.

## 3. The judge and generator share a model family - untested for self-bias

Both the generator and the judge default to the same model
(`claude-sonnet-5`, via `DEFAULT_MODEL`). This project does not test whether
a same-family judge is systematically more lenient toward its own family's
outputs than a different judge model would be. If pursuing this further, an
easy follow-up experiment would be running the judge with a different model
than the generator and comparing score distributions.

## 4. Position-bias and verbosity-bias experiments assume a working harness run first

Both `harness/position_bias.py` and `harness/verbosity_bias.py` read
already-generated emails out of a `results/*.jsonl` file rather than
generating fresh ones. This was a deliberate simplification to avoid
tripling API cost (generate once, reuse for both bias experiments), but it
means the bias experiments are only as diverse as whatever dataset slice you
ran the harness over - running them against `--limit 10` will produce noisy
percentages. Run the full golden set first if the bias numbers need to be
meaningful.

## 5. Cost figures are estimates, not billing data

`harness/llm_client.py::PRICING_PER_MTOK` hardcodes per-model prices at the
time this was written. If Anthropic's pricing changes, or you swap in a
different model via `DEFAULT_MODEL` that isn't in that dict, the harness
falls back to a default rate rather than failing - which means the cost
panel can silently under- or over-estimate if you're not paying attention.
The dashboard doesn't currently warn you when it's using the fallback price.

## 6. Dataset size and diversity

160 items across 32 scenarios (5 contexts × tone/length variation per
scenario) satisfies the 150+ item requirement, but the *contexts* per
category are drawn from a fixed list of 6 per category
(`data/scenarios.py::CONTEXTS_BY_CATEGORY`), reused across the 8 scenarios
in that category. That means some items share nearly identical context text
with a different scenario wrapped around it. It's enough to exercise the
full harness and get real signal on judge reliability, but a production
version of this dataset would want independently-written contexts per item,
not a shared pool.

## 7. What would be next

- Replace simulated human labels with real ones (see #1).
- Run a same-vs-different-model judge comparison (see #3).
- Expand `CONTEXTS_BY_CATEGORY` so no two items in a category share context
  text.
- Track cost drift by pinning `PRICING_PER_MTOK` to a source and warning
  when a model isn't in that table.
