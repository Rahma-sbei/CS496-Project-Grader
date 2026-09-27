# Labelling Guide — Email Style-Guide Compliance

An email is graded against 12 rules across 4 bands. Each rule is a boolean
(pass/fail). `overall_score` is a holistic 1–5 judgment, not a simple sum —
one severe failure can outweigh several minor ones.

## 1. Structure
- **greeting** — Email opens with an appropriate greeting (e.g. "Dear X," "Hi X,").
- **body** — Body clearly and coherently conveys the message (not blank / garbled).
- **sign_off** — Email closes with a sign-off + sender name (e.g. "Best regards, Name").

## 2. Tone
- **professional_register** — No rudeness, no overly casual voice, no emoji/exclamation spam.
- **no_slang** — No slang, internet shorthand, or filler interjections ("lol", "k?", "ur").
- **formality_matches_relationship** — Formality level fits who it's to (a client gets more formality than a teammate; a boss gets more formality than a peer).

## 3. Content (checked against the brief)
- **no_invented_facts** — Email does not state facts, numbers, or commitments that are not in the brief.
- **addresses_all_points** — Every key point listed in the brief is actually addressed.
- **correct_names** — Recipient/sender names and titles used correctly and consistently.

## 4. Form
- **grammatical** — No grammar/spelling errors that a careful writer would avoid.
- **concise** — No padding, throat-clearing, or repeated ideas; says what's needed and stops.
- **well_paragraphed** — Broken into readable paragraphs/line-breaks, not a wall of text.

## Overall score (1–5)
- **5** — Passes all rules cleanly.
- **4** — One minor/low-severity issue (e.g. slightly long, one extra paragraph break needed).
- **3** — One clear rule failure that a recipient would notice but that doesn't damage trust or content.
- **2** — A failure in tone or content severe enough to damage the message (invented facts, disrespectful tone, missing a key point).
- **1** — Multiple serious failures; email would need to be rewritten before sending.

## Examples

**Good (passes):**
> Dear Ms. Rahmani,
>
> I'm writing to let you know we missed Friday's deadline for the deliverable.
> The delay was caused by a vendor issue on our end. We now expect to deliver
> by next Wednesday.
>
> Best regards,
> Youssef

**Bad — tone (fails professional_register, no_slang):**
> hey Rahmani lol, so yeah we totally missed friday, my bad, vendor stuff
> blew up on us. should have it to you by wednesday probably! cheers, Youssef

**Bad — content (fails no_invented_facts):**
> ...The delay was caused by our QA team running extra security audits...
> (brief said the cause was a vendor issue — this is an invented fact.)

## Labelling process
1. Two labelers independently score every item against this guide, using only
   the `brief` and `candidate_email` fields (never look at the other labeler's
   answers first).
2. Compute agreement (e.g. % exact match per rule, or Cohen's kappa) across
   all 12 rules before reconciling anything.
3. Where the two labelers disagree, discuss and settle on one `reconciled_label`
   per item. Record a `resolution_note` on any item where reconciliation
   required discussion (not just automatic agreement).
4. `reconciled_label` is the ground truth used later to score the LLM judge —
   never score the judge against a single labeler's raw output.

## Notes on this golden set (50 items)
- 15 scenarios ("briefs"), each rendered as 3–4 candidate emails: one clean
  pass plus 2–3 with a deliberately injected violation (`violation_injected`
  field: `none`, `tone`, `structure`, `content`, or `form`).
- 35 items in `dev` (used to iterate the system/judge prompts), 15 in `test`
  (touched only once, for the final report).
- 10 items (20%) carry a genuine labeler disagreement on one sub-field, with
  a `resolution_note` explaining how it was reconciled — this is what your
  inter-labeler agreement number should be computed from.
- Note this is a **50-item pilot set** to develop the harness/guide against —
  the project brief calls for 150+ in the final golden set, so scale this same
  construction pattern (more scenarios × more injected variants) before the
  Week 4 freeze.
