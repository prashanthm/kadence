---
name: release-closeout
description: Backfill an audit trail for an already-published ad-hoc release tag (e.g. edi-mcp-server v1.0.0) that bypassed the test-evidence gate. Produces a gap register that blocks the next patch release until resolved. The immutable tag is never mutated.
---

# Release Closeout Skill

## Purpose

Bring a **brownfield, already-published** release tag into the `release-gate` audit
model **without mutating the immutable tag**. For a tag created before this gate
existed (the edi-mcp-server `v1.0.0` incident: a production tag with no test-evidence
gate, no traceability, single-actor dispatch), this skill backfills the audit
artifacts, classifies the gaps, and produces a **gap register** that is a *blocking
gate on the next patch release*.

## When to Use

- An ad-hoc / pre-gate production tag exists and must be brought under governance
- Orchestrator `release-closeout` stage
- Before authorizing the next release of a closed-out artifact

## Required Inputs

- The published tag + its repo (e.g. `your-org/edi-mcp-server` `v1.0.0`)
- The artifact digest the tag points at (read-only)
- The `release-gate` model (R1–R6)

## Required Workflow

1. **Classify.** Record the gap class — e.g. *"production release tag created without
   test-evidence gate or approval trail."*
2. **Backfill audit artifacts** under `initiatives/<slug>/.sdlc/releases/<ver>/` (as
   an audit record, not a rerun of the gate): `release-scope.md`, traceability,
   provenance, and an approval record reconstructed from history.
3. **Open the gap register** (`release-closeout-gap-register.md`): each gap with a
   class, owner, and status (`open` / `resolved` / `waived` — a waiver needs a
   recorded owner). The register is **blocking**: gaps must be `resolved`/`waived`
   before the next tag can pass R6.
4. **Never mutate the tag.** The immutable `vX.Y.Z` is not re-tagged, moved, or
   republished. Closeout produces *audit artifacts about* it.
5. **Wire forward.** Reference the gap register from the next release's
   `release-scope.md` so R1 of the next cycle inherits the blocking gaps.

## Rules

- **Immutable tag is untouched** — audit only; no re-tag/move/republish.
- **Gap register is a forward gate**, not a historical advisory: open gaps block the
  next patch release through R6 preflight.
- **Ownership:** Builder remediates; PO signs off / authorizes any waiver — the same
  dual authority that signs R6.

## Verification

- [ ] Gap register produced with each gap classified + owned
- [ ] Backfilled audit artifacts present under `.sdlc/releases/<ver>/`
- [ ] The published immutable tag is unchanged (digest identical to before)
- [ ] Next release's `release-scope.md` references the gap register
