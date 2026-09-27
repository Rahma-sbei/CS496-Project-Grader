# Prompt Changelog

Every prompt change must be linked to a before/after eval score. Log both
system and judge prompt versions here.

## judge_prompt_v1

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

Validation run (`--split dev`, n=35):

```
score_exact_match_rate: 0.31
score_within_1_rate:    0.74
per_rule_agreement:
  structure.greeting                    0.74
  structure.body                        0.97
  structure.sign_off                    0.74
  tone.professional_register            0.86
  tone.no_slang                         0.89
  tone.formality_matches_relationship   0.74
  content.no_invented_facts             1.00
  content.addresses_all_points          0.74
  content.correct_names                 0.91
  form.grammatical                      0.86
  form.concise                          0.97
  form.well_paragraphed                 0.97
avg_latency_s: 14.5 (max 24.9)
```

vs v1 (all, n=50): correct_names 0.80->0.91, grammatical 0.72->0.86, concise
0.90->0.97 — all three targeted fixes worked. formality_matches_relationship
barely moved (0.72->0.74): manual re-inspection showed the halo effect
persisted despite the explicit "score independently" instruction — e.g.
item_003's judge reason still read "Missing greeting, sign-off, and formal
tone for client," conflating a structure gap with a formality judgment the
prompt explicitly told it not to make. Plain-language "don't do X" framing
was not sufficient to override the model's natural inference; needed a more
mechanical rule (see v3).

Note: this run's n=35/dev is not directly comparable to v1's n=50/all —
different item sets, since v1 was run before the dev/test split was in use
for iteration. score_exact/within_1 dropping here reflects both the harder
dev subset and a still-unresolved formality issue, not a regression from the
other 3 fixes.

## judge_prompt_v3

Change: rewrote scoring section to explicitly bind each overall_score band to
specific rule failures (5=all pass, 4=exactly 1 formatting issue, 3=exactly 1
tone failure OR 1 missing structural component, 2=invented facts/missing core
details/severe hostility, 1=unusable) instead of leaving overall_score
holistic and unanchored. Also: (a) greeting/sign_off explicitly "false ONLY
if missing" to stop over-flagging; (b) moved blunt/demanding/aggressive tone
out of professional_register and into formality_matches_relationship
specifically, since v2 was still splitting this inconsistently; (c)
addresses_all_points now explicitly counts clearly-implied points, not just
literal restatement; (d) well_paragraphed given a concrete, checkable
definition (single line with no \n breaks = fail) instead of "not a wall of
text."

Validation run (`--split dev`, n=22):

```
score_exact_match_rate: 0.41
score_within_1_rate:    0.95
per_rule_agreement:
  structure.greeting                    0.91
  structure.body                        1.00
  structure.sign_off                    0.86
  tone.professional_register            0.86
  tone.no_slang                         0.86
  tone.formality_matches_relationship   0.86
  content.no_invented_facts             1.00
  content.addresses_all_points          0.73   <- remaining weak rule
  content.correct_names                 1.00
  form.grammatical                      0.91
  form.concise                          0.95
  form.well_paragraphed                 0.82
```

vs v2 (dev, n=35): score_exact 0.31->0.41, score_within_1 0.74->0.95,
correct_names 0.91->1.0, grammatical 0.86->0.91, formality_matches_relationship
0.74->0.86 (finally moved, once the mapping was made mechanical rather than
just instructional). Binding overall_score explicitly to specific rule
failures was the single biggest lever — most of the score_within_1 jump came
from removing ambiguity in how the 12 booleans map to the 1-5 number, not
from the booleans themselves changing much.

Decision: NOT changing score_exact_match_rate methodology to a field-match
percentage threshold. score_exact stays intentionally strict (does the
judge's overall_score match the human's exactly) and score_within_1 stays as
the designed secondary, more forgiving metric — this is by design, not a gap
to close. Evidence: our own golden set shows human-human disagreement on
overall_score too (resolution_note on items 004, 009, 019, 029, 044 —
"Labelers disagreed... averaged the score"). Requiring the judge to hit exact
agreement with a number our own labelers had to negotiate would be an unfair
bar. per_rule_agreement (already reported per field) is the correct metric
for "does the judge apply each individual rule correctly," and is already at
0.86-1.00 for 11 of 12 rules.

Remaining weak rule: content.addresses_all_points (0.73). Root cause
(confirmed on 6/6 mismatches: items 004, 016, 021, 026, 027, 030, all
violation_injected="content"): judge marks a key_point NOT addressed when the
email states something factually WRONG about it (e.g. claims a dashboard is
"fully complete" instead of "80% done"); reconciled labels instead treat that
as addressed-but-inaccurate, letting content.no_invented_facts alone carry
the penalty for the same defect. Root-caused but NOT fixed in a v4 — judge is
being frozen here to move on to system-prompt work; documented as a known
limitation for report.pdf's judge reliability section rather than chased
further.

DECISION: judge frozen at v3. `validate-judge --split test` will be run once,
at the very end (after system-prompt work is also done, not before), for the
final reliability number reported in report.pdf.

## system_prompt_v1

Baseline. Plain restatement of the style guide, structured JSON output
{subject, email}.

First eval run (`python -m harness.runner run-system --system-version v1
--judge-version v3`, n=50, 0 technical errors, briefs.jsonl = all 50
golden-set brief scenarios, no ground truth — judge-scored only):

```
average_overall_score: 5.0
pct_scored_4_or_5:     1.0
per_rule_pass_rate:    1.0 on all 12 rules, no exceptions
```

FINDING — not trusted as-is. A flat 1.0 across every rule for every item on
a 12-rule subjective rubric is not a credible result; the judge itself
showed real variance (73-100% per-rule agreement, overall_score spanning
1-5) when grading human-written candidate_emails in the same run structure.
Root cause identified: system.py and judge.py were both calling
llm_client.call_json(), which defaults both the email-writer and the grader
to the SAME model (GROQ_MODEL). This is self-preference bias — a model
tends to score its own outputs, or outputs in its own house style, more
favorably than an independent grader would. The judge was effectively
grading its own writing.

FIX: added harness/llm_client_sys.py, a second client pointed at a separate
model via GROQ_MODEL_SYS (distinct default from the judge's GROQ_MODEL, so
this can't silently collapse back to one model). Reuses
llm_client._extract_json for the JSON-shape guarantees (dict-only parsing,
same defensive handling that fixed the earlier crash — see llm_client.py's
own changelog notes) rather than duplicating that logic. system.py now
imports call_json_sys from llm_client_sys instead of call_json from
llm_client; judge.py is unchanged and still uses llm_client directly.

NEXT: re-run `run-system --system-version v1 --judge-version v3` with the
model split in place and record the new numbers here. Expect
average_overall_score and per_rule_pass_rate to come down from 1.0 to
something with real variance — that will be the first trustworthy baseline
for system_prompt_v1, and the number future system_prompt_v2+ changes get
compared against, not this one.
