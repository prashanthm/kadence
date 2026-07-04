<!--
AGENT: ADR research & rubric doc — the evidence and option-scoring behind one ADR. Lives at initiatives/<slug>/research/adr-NNN-<short-title>.md and is linked from that ADR's `## Research & Rubric` section. The ADR stays the durable decision; this doc holds the research, the scored rubric, and the verdict. One research doc per option-weighing ADR. Skip for inherited/charter decisions with no options.

This is a house convention, not an external standard. Prior art: MADR's "Considered Options" + "Pros and Cons of the Options" and systems-engineering trade studies — the difference here is keeping the scored options in a linked doc so the Nygard-style ADR stays terse.

Evidence bar (the point of this doc): a rubric is only as good as the research under it. Every option score must trace to a cited source, a measured/observed fact, or named prior art — NOT to assumption or vibe. Mark each source's strength. If the evidence is too thin to score an option honestly, say so in Open Risks and either narrow the decision, gather more, or record the choice as provisional — do not manufacture a verdict. No invented benchmarks, versions, costs, or quotes.

Strip this entire HTML comment when writing outside templates/ — scaffolding only.
-->

# Research & Rubric — ADR-<!-- REPLACE: NNN -->: <!-- REPLACE: Decision Title -->

> Backs [ADR-<!-- REPLACE: NNN -->](../adrs/adr-<!-- REPLACE: NNN-short-title -->.md). <!-- REPLACE: one-line scope -->

## Decision question

<!-- REPLACE: The specific decision the ADR must make, as a question. -->

## Research method & sources

<!-- REPLACE: How the evidence was gathered (e.g. fan-out web search, PoC findings, prior-art review, upstream ADR reading, benchmark) and how claims were verified (e.g. multiple independent sources, reproduced locally). Then list each source with its strength so a reviewer can judge whether the rubric stands on real evidence. -->

| # | Source | What it supports | Strength |
|---|--------|------------------|----------|
| 1 | <!-- REPLACE: title / URL / repo path / PoC run --> | <!-- REPLACE: the specific claim or finding --> | <!-- REPLACE: Strong (measured/reproduced or ≥2 independent sources) / Moderate (single credible source) / Weak (vendor claim, anecdote — flag in Open Risks) --> |

<!-- REPLACE: Remove any option or criterion you cannot back with at least one Moderate+ row above. An unsupported score is worse than an absent one. -->

## Options considered

<!-- REPLACE: The candidate approaches, one short paragraph each. Name them so the rubric can score them. -->

1. **<!-- REPLACE: Option A -->** — <!-- REPLACE -->
2. **<!-- REPLACE: Option B -->** — <!-- REPLACE -->

## Rubric

<!-- REPLACE: The criteria used to choose, scored per option. Pick criteria that matter for THIS decision (examples: fit-to-charter, operability, cost, security, reversibility, time-to-ship). Weight only if it changes the outcome. This matrix is the rubric — it does not belong in the ADR body. -->

| Criterion (weight) | Option A | Option B |
|--------------------|----------|----------|
| <!-- REPLACE: e.g. Fit to charter --> | <!-- REPLACE: score + 1-line reason --> | <!-- REPLACE --> |
| <!-- REPLACE: e.g. Operability --> | <!-- REPLACE --> | <!-- REPLACE --> |
| **Verdict** | <!-- REPLACE --> | <!-- REPLACE --> |

## Verdict & rationale

<!-- REPLACE: Which option won and why, tied back to the rubric. State explicitly what was rejected and the rejection reason (these become the ADR's rejected alternatives). -->

## Open risks / follow-ups

<!-- REPLACE: Residual risks the chosen option carries, and any decisions deferred to a later ADR. -->
