# Human Labeling Guide — The Grader

This guide is for the two human evaluators who independently score every item
in `golden_set.jsonl`. Read this in full before labeling. Do not discuss
scores with the other evaluator until both of you have finished — the whole
point of having two independent labels is to measure real disagreement.

## What you're scoring

For each golden-set item, an email was generated from the scenario's
`recipient`, `purpose`, `context`, `required_information`, `tone`, and
`max_length`. You are scoring the **generated email**, not the scenario.
Read the scenario first, then the email, then score.

## The rubric

Every criterion is scored 0, 1, or 2. Never use half points. Maximum total
is 10.

### 1. Requirement Fulfillment (0-2)
Does the email cover every item in `required_information`?

- **0** — One or more required pieces of information is missing entirely.
- **1** — All items are present but at least one is underdeveloped, vague,
  or handled in a single throwaway clause.
- **2** — Every required item is clearly and adequately addressed.

*Good example (score 2):* Scenario requires "apologize, explain the
problem, request a two-day extension, thank the professor." The email
opens with an apology, states the laptop failed, explicitly asks for two
extra days, and closes with thanks.

*Bad example (score 0):* The email apologizes and explains the laptop
problem but never actually asks for an extension — it just says "I hope
this is okay."

### 2. Accuracy (0-2)
Does the email invent facts not present in the `context`, or contradict
the scenario?

- **0** — Invents specific facts (a professor's name that wasn't given, a
  fabricated appointment time, a made-up order number) or directly
  contradicts the scenario (claims the extension was already granted).
- **1** — A minor overreach, e.g. adding a plausible but unstated detail
  that doesn't materially change the request.
- **2** — Stays fully within what the scenario actually states.

*Bad example (score 0):* Context says only "my laptop stopped working."
The email adds "as I explained on the phone yesterday" — a phone call
that was never mentioned.

### 3. Tone (0-2)
Does the email match the requested `tone`?

- **0** — Tone is inappropriate for the relationship (e.g. overly casual
  with a professor, aggressive with support staff, or so stiff it reads
  as a form letter when "warm and friendly" was requested).
- **1** — Broadly matches but has a jarring phrase or slips register at
  least once.
- **2** — Consistently matches the requested tone throughout.

### 4. Clarity (0-2)
Is the email easy to read and unambiguous?

- **0** — Confusing structure, unclear ask, or run-on sentences that
  require re-reading.
- **1** — Understandable but has a clarity issue (buried ask, awkward
  phrasing, unclear referent).
- **2** — Clear, well organized, the ask is obvious on first read.

### 5. Conciseness (0-2)
Does the email respect `max_length` and avoid padding?

- **0** — Excessively verbose, repeats the same point multiple times, or
  clearly exceeds the requested length.
- **1** — Slightly longer than necessary or has some redundant phrasing.
- **2** — Concise, focused, respects the requested length.

## Total score
Sum the five criteria (max 10). Record scores per-criterion, not just the
total — the harness needs per-criterion agreement, not just overall.

## How to record your labels

Copy `data/human_labels/TEMPLATE.jsonl`, rename it to `human1.jsonl` (or
`human2.jsonl`), and fill in one line per golden-set item:

```json
{"id": "email_001", "requirement_fulfillment": 2, "accuracy": 2, "tone": 2, "clarity": 2, "conciseness": 1}
```

Label every item in `golden_set.jsonl` — do not skip any. Once both
`human1.jsonl` and `human2.jsonl` are complete, run:

```bash
python harness/human_agreement.py
```

to compute exact agreement, per-criterion agreement, and the list of
disagreements.

## Tips for consistent labeling

- Score against the rubric text, not your gut feeling about "a good
  email" in general.
- If you're between two scores, re-read the 0/1/2 definitions above before
  defaulting to the higher one.
- Label in one sitting where possible; fatigue drifts scores.
- If an email is empty or clearly broken (an API failure that produced
  garbage), leave the row out rather than guessing — the harness already
  tracks failed generations separately.
