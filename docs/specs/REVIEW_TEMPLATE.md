# Human Intelligence Review — template

One per candidate before it becomes a STRIKE. Keep it short and honest. Confidence and attractiveness
are **separate** and must never be collapsed. Do not promote unless you would put it in front of a
skeptical VP Capture with the Pyrnova name attached.

---

**Candidate:** <title>
**Target company:** <name>   **Source(s):** <USAspending award id / SAM notice id + link>
**Precursor class:** recompete_expiry | sources_sought | rfi | presolicitation | special_notice

**FACT — what the evidence actually establishes**
> Only what the cited records literally say (award, POP end date, notice type, deadline). No inference here.

**CUSTOMER FIT — why this could matter to *this* company**
> Capability / agency / NAICS / incumbency overlap, in one or two sentences.

**TIMING — why now**
> Lead time to the next observable event (expiry, response deadline, expected solicitation).

**INCUMBENCY / HISTORY — what award history suggests**
> Who holds it, prior period, option pattern if visible.

**FALSIFICATION — why this might NOT be an opportunity** (pick all that apply, be specific)
> market research only · incumbent strongly positioned · wrong capability · wrong contract size ·
> set-aside mismatch · timing unrealistic · follow-on effectively committed · insufficient evidence ·
> no meaningful lead advantage.

**ACTION — what the customer's Capture/Growth team should do next**
> One concrete next move.

**CONFIDENCE (in the interpretation): __%**   — how sure Pyrnova is the reading is correct.
**ATTRACTIVENESS (commercial): __%**          — separately, how good the opportunity looks.

**DECISION:** accept (→ STRIKE) | reject   **Reviewer:** <name>   **Date:** <YYYY-MM-DD>
**Reason:** <one line — recorded as a benchmark label>

---
Recording: the CLI logs every candidate's recommendation + reason to `var/state/reviews.jsonl`
automatically. Use `--reviewer "<name>"` to upgrade a recommendation to a confirmed STRIKE. This
template is for the human judgement that goes into that decision (and into the Signal Brief prose).
