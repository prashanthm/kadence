# Review Tiers

> Companion to [`pr-gate.md`](pr-gate.md). It clarifies **who must review** a PR — not *whether*
> the gate applies. The pr-gate applies to **every** PR; this only sets review depth.

## Principle

Review depth scales with **blast-radius**, not with whether the change is "the product" vs
"process/tooling." *"Not the shipped software" does not mean "low risk"* — CI workflows, secrets,
permissions, and infrastructure state are high-impact even though they are "process."

## Tier 1 — Peer review required

A human **other than the author** approves before merge. Applies to any change touching:

- **Identity & access** — IAM roles, trust / OIDC policies, RBAC, authentication.
- **Infrastructure resources & state** — anything producing a non-empty IaC plan
  (Terraform / CloudFormation), and any committed state file.
- **Secrets & permissions** — adding or widening a secret, token, or CI permission scope.
- **CI/CD that handles secrets or permissions** — workflow definitions that read secrets or set
  `permissions:` / deployment environments.
- **Dependencies with runtime or build reach** — supply-chain surface.
- **Irreversible operations** — data migration, deletion, or anything not safely revertable.

## Tier 2 — Self-review + operator merge

The author runs a self-review; a single human merges. When the author is an AI agent, the **human
operator** merges — so *author ≠ approver* always holds. Applies to:

- Docs, runbooks, comments, formatting.
- Issue/PR templates, labels, and project-board / status conveniences that do **not** add or widen
  secrets or permissions.

## Rules

- **When in doubt, escalate to Tier 1.**
- A Tier-2 change that **introduces or widens** a secret/token/permission is **Tier 1 for that
  change** (e.g., the first PR that adds a new CI secret), even if the rest is cosmetic.
- AI-authored PRs always require a human in the loop; the author and the approver must never be the
  same human.
- This **complements** `pr-gate.md` and waives no gate item. Board **gate-status transitions remain
  human-only** (see `../agent-rules/sdlc-lifecycle.md`).
- Repos **SHOULD** map their concrete Tier-1 paths into `CODEOWNERS` so GitHub auto-requests the
  required reviewer on those paths.
