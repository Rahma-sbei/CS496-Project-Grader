# Postmortem: Project 1, The Grader

Draft. Add what goes wrong in the final runs before the freeze.

## What went wrong

1. **Harness crash lost a whole run.** A model reply of bare `null` passed
   JSON parsing and crashed deep in `judge.py`, losing all rows already
   computed. Fixed: `_extract_json` only accepts a JSON object, every item
   runs in its own try/except, and results are written in a `finally` block.

2. **A missing or empty API key.** A missing key silently sent requests that
   all failed with 401. We added a fail-fast message, but an *empty*
   `GROQ_API_KEY=` still crashed at import, even for `label-agreement`, which
   makes no API call. Fixed with `os.getenv(...) or placeholder`.

3. **Test set leakage.** The first split was per item, so 12 of 15 briefs had
   emails in both dev and test. We tuned judge v1-v3 on dev while sibling
   emails of the same briefs sat in test. Fixed: split by brief, all old items
   moved to dev, and 60 new items from 15 unseen briefs became the test set.

4. **System scored a perfect 5.0 on everything.** The system and the judge
   used the same model. We split them (`GROQ_MODEL_SYS`), but gpt-oss-20b and
   gpt-oss-120b are the same family, so some self-preference may remain.
   `briefs.jsonl` also repeated the same 15 briefs 50 times, so the "50 runs"
   were really 15. Fixed: 40 unique briefs.

5. **Changelog numbers did not match the result files.** The judge v3 entry
   said n=22, score_within_1 0.95. The only v3 result file says n=35, 0.94.
   Fixed by copying numbers straight from `results/`. Lesson: never type
   numbers by hand; copy them from the summary file.

6. **The position-bias test was not the one asked for.** The first version
   swapped brief and email inside one prompt. The slides ask to swap two
   *answers*. Fixed with a pairwise judge (`judge_pairwise_v1.txt`).

7. **Some "judge errors" were label errors.** item_004 says "I don't yet have
   a firm new date", but its label says all key points were addressed. The
   judge was right. TODO: re-check the 6 flagged items and report what changed.

8. **Cost was reported as $0.** Prices were placeholders (0.0). Fixed with
   real Groq prices per model in `harness/scorer.py`.

9. **Hit Groq's free daily limit mid-run.** The free tier allows 200k tokens
   per day for gpt-oss-120b, and one judge call uses about 1,700 tokens
   (roughly 115 calls a day). A dev run died at item 14 of 50, and the harness
   kept firing 24 more requests that all failed. Fixed: a per-day 429 now stops
   the run at once (rows so far are saved), and per-minute 429s wait for the
   time Groq asks for, then retry. We planned the remaining runs around the
   daily budget.

## What we learned

- Look at the per-item rows, not only the summary number. Every problem
  above was found by reading rows.
- A judge result is only as good as the labels it is compared to.
- Decide the dev/test split before any tuning, and split by scenario, not by row.

## Known limits (for the demo)

- TODO after the bias run: which inputs flip the judge, and does padding
  change the score?
- `addresses_all_points` is the weakest rule: the judge and the humans treat
  "mentioned but wrong" differently.
- Single-email judge scores are absolute, so they drift more than
  pairwise comparisons.
