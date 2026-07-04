---
name: release-approval
description: Record the R5 governance + R6 dual sign-off for a release, assembling the evidence bundle the CI preflight reads before crane-copying a candidate digest to an immutable vX.Y.Z tag. Use after release-review-batch (R4) passes.
---

# Release Approval Skill

## Purpose

Drive **R5 (governance)** and **R6 (tag authorization)** of the release gate
(the `release-gate` feature): assemble the traceability + provenance + SBOM, capture the dual
PO + Builder sign-off, and produce the `release-evidence.json` bundle that
[`release_tag_preflight.sh`](../../scripts/release_tag_preflight.sh) validates as
the CI hard block. This skill **prepares and records** approval; it never creates
the tag — promotion is the `release-tag` dispatch after the preflight passes.

## When to Use

- After `release-review-batch` (R4) returns an overall `PASS`
- Orchestrator `release-approval` stage
- Before the `release-tag` CI dispatch

## Required Inputs

- The run manifest `release{}` block (candidate digest pinned at R1)
- `test-evidence.json` (R2 — suites vs candidate digest)
- `release-review-summary.md` (R4 fan-in)
- Release AC list (manifest or feature md)

## Required Workflow

1. **R5 — governance.** Attach/produce: traceability matrix (`traceability_path`),
   provenance draft (`provenance_path`), SBOM (`sbom_path`). Confirm each path exists.
2. **Collect evidence.** Run
   `collect_release_evidence.py --candidate-digest <d> --test-evidence <te.json> --out release-evidence.json`,
   then add the R1–R5 gate statuses + artifact paths and the dual-sign-off block to it
   (the preflight checks `gates.*` and `signoff.{product_owner,builder}`).
3. **R6 — dual sign-off.** Record PO + Builder authorization in
   `release-approval-record.md`; set `signoff` in the evidence bundle.
4. **Preflight (dry-run gate).** Run
   `release_tag_preflight.sh --evidence release-evidence.json --digest <candidate-digest> --version <vX.Y.Z> --release-ac <manifest>`.
   It must exit 0. If it refuses, **stop** — remediate (re-run the failing suite/gate)
   and re-collect; never hand-edit the bundle to force a pass.
5. **Mark `release-tag-authorized` (R6) passed** in the manifest only after the
   preflight passes.

## Rules

- **Never create or push a tag.** This skill produces the *authorization*; the
  `release-tag` dispatch crane-copies the validated digest.
- **Digest is immutable through the gate** — `candidate_digest` set at R1 is the only
  anchor; never change it during approval.
- **No forced pass.** A refusing preflight means remediate-and-re-run, not override.
- Release AC verification is **operator/human-tier** — run its `verify:`
  commands as a human/reviewer; do not route them through the auto-tier loop path.

## Verification

- [ ] R5 artifacts (traceability, provenance, SBOM) exist and are referenced in the manifest
- [ ] `release-evidence.json` produced; all R1–R5 gates `passed`; dual sign-off recorded
- [ ] `release_tag_preflight.sh` exits 0 against the bundle
- [ ] `release-tag-authorized` marked passed only after the preflight passes
