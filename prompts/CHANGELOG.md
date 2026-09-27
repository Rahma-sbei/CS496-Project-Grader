# Prompt Changelog

Every prompt change must be linked to a before/after eval score. Log both
system and judge prompt versions here.

# judge_prompt_v1

Baseline. Rules taken directly from data/labelling_guide.md, 12 booleans +
overall_score + reason, JSON-only output enforced via response_format.

Validation run (`python -m harness.runner validate-judge --judge-version v1
--split all`, n=50, 0 technical errors):

```
score_exact_match_rate: 0.42
score_within_1_rate:    0.76
per_rule_agreement:
  structure.greeting                    0.86
  structure.body                        1.00
  structure.sign_off                    0.86
  tone.professional_register            0.86
  tone.no_slang                         0.90
  tone.formality_matches_relationship   0.72   <- weakest
  content.no_invented_facts             0.98
  content.addresses_all_points          0.76
  content.correct_names                 0.80
  form.grammatical                      0.72   <- weakest (tied)
  form.concise                          0.90
  form.well_paragraphed                 0.88
avg_latency_s: 9.1 (max 20.96)
```

Below target (score_within_1 >= 0.85, per-rule >= 0.85-0.90 each). Manually
inspected every mismatch on the four weakest rules across the 50-item run.
Findings (see judge_prompt_v2 below for the fixes):

1. `content.correct_names` — judge fails this whenever a name is simply
   ABSENT (no greeting/sign-off at all), not just when a name is wrong.
   Confirmed on 2/2 relevant items (item_003, item_013): judge=false,
   reconciled=true, in both cases the email has no greeting/sign-off so no
   name appears anywhere. Judge is double-penalizing the same defect under
   structure AND content.
2. `form.grammatical` — judge fails this for casual register or trivial
   single-word omissions that aren't real grammar errors. Confirmed on 3/3
   relevant items (item_002, item_015, item_017); item_015's own judge
   `reason` field cites a missing word "that" as the failure.
3. `tone.formality_matches_relationship` (halo effect) — judge fails this
   whenever ANY other rule in the email is bad, even when the formality
   level itself is fine. Clearest case: item_014 is written "Dear Mr.
   Trabelsi... Best," (properly formal) but is missing a key point; judge
   still marks formality_matches_relationship=false with a reason that
   describes the missing content, not formality. Same pattern (all 3 tone
   sub-rules failed together as a bloc) on item_002 and item_006.
4. `form.concise` under-detects real padding. Both padding-injected items
   inspected (item_008, item_028, `violation_injected: "form"`) were scored
   concise=true by the judge despite genuinely repetitive/padded text;
   reconciled=false on both.

NOT changed in v2: `structure.greeting` / `structure.sign_off` also showed
disagreement (0.86 each), but the mismatches inspected (item_003, item_013,
item_017, item_023) look like inconsistent/noisy reconciled labels rather
than a judge error — e.g. item_023's candidate email has no greeting or
sign-off text at all, yet its reconciled label marks greeting=false,
sign_off=TRUE, which is backwards from what the email shows. Flagged for the
team to spot-check against data/labelling_guide.md before touching structure
rules in a future version — do not tune the prompt to match a label that may
itself be wrong.

## judge_prompt_v2

Change: targeted edits only, based on the four confirmed patterns above —
(1) correct_names now only fails on a WRONG name, not an absent one, with an
explicit pointer to let structure carry that failure instead; (2) grammatical
now explicitly excludes casual register and single-word omissions that don't
change meaning; (3) added an explicit relationship->formality mapping and an
instruction to score all rules independently, to stop one bad rule from
dragging down unrelated ones; (4) concise now includes 2 concrete examples of
what padding looks like. No other rules or the scoring rubric were touched.

Validation run (dev split only — test held out for the final report):
`python -m harness.runner validate-judge --judge-version v2 --split dev`

--- SUMMARY ---
{
"n_items": 35,
"n_errors": 0,
"n_scored": 35,
"error_reasons": [],
"per_rule_agreement": {
"structure.greeting": 0.7428571428571429,
"structure.body": 0.9714285714285714,
"structure.sign_off": 0.7428571428571429,
"tone.professional_register": 0.8571428571428571,
"tone.no_slang": 0.8857142857142857,
"tone.formality_matches_relationship": 0.7428571428571429,
"content.no_invented_facts": 1.0,
"content.addresses_all_points": 0.7428571428571429,
"content.correct_names": 0.9142857142857143,
"form.grammatical": 0.8571428571428571,
"form.concise": 0.9714285714285714,
"form.well_paragraphed": 0.9714285714285714
},
"score_exact_match_rate": 0.3142857142857143,
"score_within_1_rate": 0.7428571428571429,
"judge_latency_and_cost": {
"n_with_meta": 35,
"avg_latency_s": 14.464,
"max_latency_s": 24.893,
"total_prompt_tokens": 50133,
"total_completion_tokens": 33882,
"estimated_cost_usd": 0.0,
"estimated_cost_per_1k_items_usd": 0.0
},
"judge_version": "v2",
"split": "dev"
}

## system_prompt_v1

Baseline. Plain restatement of the style guide, structured JSON output
{subject, email}. Eval run: not yet run. Run `python -m harness.runner
run-system --system-version v1 --judge-version v1` and paste the resulting
average_overall_score / per_rule_pass_rate here.
