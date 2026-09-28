# Prompt Changelog

Every prompt change is versioned as a new file (`generator_v2.txt`,
`judge_v2.txt`, ...) — never edit a version in place, since the harness and
past results reference specific version strings. Record every change here
before merging it, including the measured effect on dev score. **Never
modify a Test score retroactively** — if you re-run the test set, add a new
dated entry, don't overwrite the old one.

## v1 — 2026-09-27

**Changed:**
Initial versions of `generator_v1.txt` and `judge_v1.txt`, matching the
rubric in `data/LABELING_GUIDE.md` field-for-field.

**Reason:**
Baseline for the project. Not yet compared against anything.

**Dev score:** —
**Test score:** —

---

<!--
Template for future entries — copy this block for each new version.

## v2 — YYYY-MM-DD

**Changed:**
<what actually changed in the prompt text>

**Reason:**
<what problem this was meant to fix - cite the specific evidence, e.g.
"human/LLM disagreement was highest on Tone (62% agreement) - added
explicit examples of tone violations to the judge prompt">

**Dev score before → after:**
X.X → X.X

**Test score:**
X.X
(Only measure test score once per version, after the dev score change is
locked in. Do not iterate against the test set.)
-->
