# Postmortem — Project 1: The Grader

**Outcome:**
- We have a working harness, a judge locked at judge_prompt_v3 (on
  openai/gpt-oss-120b), and system_prompt_v2 (on qwen/qwen3.8-27b).
- System v2 on test scored a judge average of 4.40/5 (8×5, 2×2). Both 2s
  are judge errors.
- Most of what went wrong was in the measurement, not in the system. Our
  first scores were a perfect 5.0 and we could not trust them. Fixing that
  took most of the effort.

---

## What went wrong

### 1. The judge graded its own model's writing (self-preference bias)
`system.py` and `judge.py` both called `llm_client.call_json()`, so the
email writer and the grader were the same model (`GROQ_MODEL`). The first
system run scored **5.0 on all 50 items and all 12 rules**. That is not
credible for a subjective rubric.
**Fix:** a separate client (`llm_client_sys.py`, `GROQ_MODEL_SYS`) for the
system.

### 2. Our first fix did not fix it
We moved the system to `gpt-oss-20b` and the judge stayed on
`gpt-oss-120b`. Both are **OpenAI gpt-oss**: same vendor, training recipe
and writing style. The re-run still scored 5.0 everywhere. We had assumed
"different model" meant "no self-preference". It has to be a different
model **family**.
**Fix:** system → `qwen/qwen3.8-27b`. Llama models were not an option:
they are Enterprise-only on Groq now. Qwen is a *preview* model, which is
a risk: it can be withdrawn at short notice.

### 3. The eval set could not show a difference
- `briefs.jsonl` was just the golden set's **15 scenarios repeated 3–4
  times** (50 rows). At temperature 0, repeated briefs gave word-for-word
  identical emails, so the effective sample was about 15, not 50. The Qwen
  smoke run of 9 items had only 3 distinct emails.
- Every brief had 3 easy key points, so the scores hit a ceiling of 5.
- The judge had been tuned on those same scenarios (leakage), and there
  was no dev/test split for the system.

**Fix:** 30 new, distinct, harder briefs with a 20/10 dev/test split: 5–6
key points, exact numbers, "do not…" constraints, unknown names and given
senders.

### 4. The judge misses subtle failures
- In run 1, the judge passed **8/8 emails with unfilled placeholders**
  ("Dear [Client Name]", "[Your Name]") and invented commitments ("We have
  resolved the matter").
- The golden set only has loud, deliberately injected violations. The
  judge learned to catch those, but not the small additions that a
  capable LLM actually makes.
- Agreement on the golden set did not carry over to real system output.

**Mitigation:** a deterministic placeholder check (`rule_checks.py`) and a
manual review for added content. **Not fixed in the judge itself.**

### 5. The judge also fails correct emails
- On correct "Dear Ms. Ben Amor," / "Dear Mr. Dridi," greetings, it marked
  `correct_names` false because the first name was left out. It also called
  "Hi Sarra," misspelled when it matched the brief exactly.
- judge_prompt_v3's score bands have **no band for a correct_names
  failure**, so the same non-defect was scored 2 in one email and 4 in
  another.
- The same greeting went 4 → 5 between two runs (run-to-run noise).
- **Every sub-5 score in the final dev and test runs is one of these false
  positives.** As a result, the judge's 4.80 → 4.95 dev gain is noise, not
  evidence that v2 is better.

### 6. We changed the judge the wrong way before going back to v3
- We drafted a stricter judge prompt with **seven changes at once**, before
  adding any human-labelled examples of the failures it targeted.
- On the first 10 dev items it matched humans exactly on 3, where v3
  matched on 6. It also failed a clean email that humans scored 5. We
  abandoned it and kept v3.
- We also briefly compared two judges on unlabelled system emails. That
  cannot show which judge is right, so we removed it.

**Lesson:** a judge is judged only against human labels. Add labelled
examples of a failure first, then change one thing at a time.

### 7. The bias check hit the API rate limit
- `check-judge-bias` made **4 judge calls per item** (80 for 20 items), and
  one of them was a duplicate.
- We ran it while a validation run was using the same model, so every
  call failed. The console printed `None`, with no reason shown.
- The re-run was stopped at **7/20** items because of the request volume.
  The runner only wrote results at the very end, so the per-item scores
  were lost. We rebuilt a partial file from the console output, with the
  unknown fields left as `null`.
- The client retries once after 1 s and has no backoff.

**Fix:** 3 calls per item (shared baseline), error reasons printed,
results saved on Ctrl-C or a crash, and `--start` to resume. The bias
result (0/7 on both probes) is still **only 7 items**.

### 8. Results and documentation drifted
- The changelog quoted a v3 validation run (n=22) whose files had been
  deleted.
- Run 1's result files were later deleted from the working tree. Run 2's
  per-item file was never committed and is lost.
- Cost constants in `scorer.py` are 0.0, so every summary shows $0. We
  computed the cost by hand.
- `requirements.txt` was saved as UTF-16 (PowerShell `pip freeze >`).
- `.pyc` files were committed, and `.env.example` was missing.
- The runner's default versions were v1, so a missing flag silently used
  an old prompt.

**Fix:** all of the above cleaned up (see CHANGELOG "Harness clean-up").
The deleted runs remain gaps.

### 9. System prompt v2 introduced side effects
Fixing additions (7/20 → 0/20) and sender names (4/15 → 15/15 first name
only) caused new, smaller problems:
- "Please let me know if you have any questions" appeared in 16/20 emails
  (the prompt's example became a template).
- Names were copied too literally ("Dear Prof. Mourad Ellouze,").
- Name and title were put on one line.
- Emails got 30% shorter.
- On test, one email was signed "Manager".
The locked judge sees none of these.

### 10. Things we did not finish
- The golden set is **50 items**, not the 150+ the brief asks for (team
  decision).
- The judge's **test-split validation** has not been run yet.
- The bias check covers **7/20** items and has no no-change noise baseline.
  The verbosity probe only counts score increases.
- Counts of "content not in the brief" come from **our own review**, not
  from the two labellers.
- The order-bias check swaps brief and email, because our judge grades one
  email at a time. It is an adaptation, not true pairwise position bias.
- The candidate email is inserted into the judge's system message. The
  only defence against prompt injection is an instruction.
- In all 10 labeller disagreements, reconciliation took the **lower**
  score. The "human" standard leans strict.

---

## What went well
- The one-command harness with per-item rows made every problem above
  visible and traceable.
- Reading the actual emails, not just the averages, found the false
  positives, the placeholders and the added content.
- The judge was locked early, so the system prompts were compared on a
  fixed yardstick.
- We set acceptance criteria before each run, and wrote down "no
  improvement" results honestly.

## What we would do differently
1. Use a different model **family** for the system and the judge from day
   one.
2. Build system briefs separately from the golden set, with a dev/test
   split, before the first run.
3. Put realistic LLM failures (placeholders, small additions) in the golden
   set *before* tuning the judge.
4. Make one prompt change per version.
5. Budget API calls up front: count calls per command, run expensive checks
   in resumable batches, and never run two jobs against the same model at
   the same time.
6. Commit every results file immediately after the run.
