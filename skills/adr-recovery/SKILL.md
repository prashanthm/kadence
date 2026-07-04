---
name: adr-recovery
description: Recover the de-facto architecture decisions embedded in an existing system as ADRs with Status Discovered in assessments/<system>/adrs/. Use to capture the AS-IS decision baseline that migration ADRs will supersede.
---

# ADR Recovery Skill

## Purpose

Surface the decisions a brownfield system already embodies — even though no one wrote them down — and record them as ADRs with `Status: Discovered`. Examples: "OSDU operator manages the full platform lifecycle on EKS", "auth via Cognito for end-users / Keycloak for platform", "MinIO-fronted signer for S3-on-Outposts compatibility", "VPC CIDR 172.20.0.0/16 forced by S3 Outposts CreateEndpoint API".

A **Discovered** ADR captures a decision that is *already true in the running system*, recoverable from code, IaC, tickets, or docs. It is distinct from `Proposed` (recommended, not yet built) and `Accepted` (approved going forward). Every Discovered ADR records the original rationale where recoverable — the "why it ended up this way" that will inform whether to supersede or preserve each decision in the forward migration.

**Quality bar:** A Discovered ADR is a verifiable fact about the running system, not a guess. Every claim must be traceable to an evidence ledger ID. An ADR whose Decision cannot be confirmed in code or IaC carries Low confidence and must say so.

---

## When to Use

- Immediately after `current-state-assessment`, to capture the AS-IS decision baseline behind the system-overview
- Before writing migration/forward ADRs, so each can explicitly name the discovered ADR it supersedes
- Whenever a re-platform initiative needs a record of "what we are moving away from and why it was that way"

---

## Required Inputs

- `assessments/<system>/system-overview.md` (from `current-state-assessment`)
- `assessments/<system>/evidence-ledger.md` (from `context-acquisition`)
- `assessments/<system>/source-inventory.md` (from `context-acquisition`)
- Code/IaC repos (local clones, paths from Source Inventory) — to confirm decisions are real in running code
- graphify (optional): `graphify query "<decision area>"` if `graphify-out/graph.json` exists; fall back to direct file reads otherwise
- Template: `templates/adr.md` (use `Status: Discovered`)
- Reference: `samples/assessments/edi-express/adrs/001-osdu-on-aws-r3m25.md`

If `system-overview.md` or the Evidence Ledger is missing, run `current-state-assessment` and `context-acquisition` first. Do not proceed without them.

---

## Corroboration Rule

Every Discovered ADR must carry an explicit confidence level. Assign confidence as follows:

| Level | Rule |
|-------|------|
| **High** | Decision confirmed in code/IaC **and** original rationale recoverable from Jira, Confluence, Slack, or architecture doc |
| **Medium** | Decision confirmed in code/IaC but original rationale is inferred from indirect evidence (TODOs, commit messages, architecture docs that describe the outcome without the discussion) |
| **Low** | Decision inferred from docs/tickets/Slack only — code read not possible or source was a Gap in the inventory. Must flag what read would raise confidence to Medium/High. |

**Low is not a failure** — it is an honest signal. Name the specific file or source that would confirm the decision in code.

---

## Anti-Hallucination Rules

These rules are absolute. Invented ADR rationale is more harmful than a missing ADR — a migration team will act on it.

1. **No claim without a ledger evidence ID.** If you cannot cite `EV-Cxx`, `EV-Jxx`, `EV-CFxx`, or `EV-Sxx`, the claim does not belong in the ADR — either invoke the Sparse Evidence Protocol or omit the claim.
2. **No invented rationale.** Do not construct a plausible-sounding "why this was decided" from first principles. If the rationale is not in the ledger, state it is not recoverable and mark it `[rationale not recovered — inferred from code shape]`.
3. **No invented version numbers, port numbers, config values, or constraint details.** Copy them from evidence; do not guess.
4. **No forward-state leakage.** An ADR that says "the system should" or "the plan is to" is not a Discovered ADR — it is a Proposed one. If a Jira ticket describes intent rather than a shipped decision, label it `[intent, not confirmed in code]`.
5. **Code beats docs and tickets.** When code and a doc/ticket disagree about what decision is in effect, write the code-authoritative claim and add: `[Conflicts with EV-Jxx: <summary>; code is authoritative]`.
6. **No section may be filled from memory.** The Context and Decision Drivers must trace back to reads or cited ledger entries performed in this session.
7. **One decision per ADR.** Do not bundle two independent decisions into one. If you find yourself writing "and also", split.

---

## ADR Discovery Protocol

Before drafting any ADR, systematically scan the system-overview and evidence ledger for decisions using these categories. For each category, answer: Is there a non-obvious choice here that a different team might have made differently? If yes — that is an ADR candidate.

### Compute & Orchestration
- What runtime does the system run on? (Lambda, ECS, EKS, EC2, bare-metal, Outpost rack?) — Was that a deliberate choice?
- Who manages the platform lifecycle? (Terraform direct-apply? A Kubernetes operator? A shell script orchestrator?) — Why that approach?
- What autoscaling strategy is used? (Karpenter, KEDA, ECS service auto-scaling, none?) — Was that driven by a constraint?

### Networking & Connectivity
- What IP CIDR ranges are used, and why? (Were specific ranges ruled out?)
- Is there a service mesh? (Istio, Linkerd, none?) — What drove the decision?
- How does ingress work? (ALB, NLB, IGW direct, no NAT?) — Why no NAT if cost-driven?
- What is the inter-component communication pattern? (In-cluster, VPC peering, PrivateLink, cross-region?)

### Identity & Authentication
- How do end-users authenticate? (Cognito, Keycloak, SAML, API key?) — Was another IdP considered?
- How do services authenticate to each other? (IRSA, mTLS, bearer token, none?)
- Is there a credential rotation strategy or is it PoC-grade shared credentials?
- Are there multiple IdPs, and why are they not federated?

### Storage & Data
- What object storage strategy is used? (S3-direct, S3-on-Outposts via signer, MinIO hot tier + cold tier?) — What problem does the signer solve?
- What database engines are used, and why? (RDS vs in-cluster PostgreSQL? DynamoDB vs RDBMS?)
- What is the hot/cold data tiering strategy, if any?
- What encryption approach is used at rest and in transit? (SSE-S3 vs KMS, HTTP vs HTTPS in-cluster)

### Messaging & Events
- What messaging backbone is used? (SNS/SQS, RabbitMQ, Kafka/MSK, EventBridge, DynamoDB Streams?) — Why?
- Is the event bus managed or self-hosted?
- What is the dead-letter / retry strategy?

### Observability & Monitoring
- What monitoring stack is used? (Prometheus + Grafana, Loki + Tempo, Zabbix, CloudWatch?) — Are multiple stacks in play?
- How are alerts and reports delivered? (SES, PagerDuty, Slack, email?) — Why that delivery path?
- Is monitoring in the same region as the system it monitors? (CON-04 type decision)

### Deployment & CI/CD
- What is the deployment orchestrator? (Helm + Terraform? Shell script? GitOps?) — Why not GitOps if shell scripts are used?
- What is the CI pipeline strategy? (Bitbucket Pipelines backplane, GitHub Actions, managed builds?)
- What is the image registry strategy? (ECR, Docker Hub, Quay?) — Why ECR-mirrored?

### Product & Billing Integration
- How is billing integrated with the cloud marketplace? (WRC, SaaS contracts, direct invoicing?)
- How are product codes and subscription tiers managed? (Static config file, database, API?)
- What is the simulate/mock mode strategy for non-prod environments?

### Platform & OSDU
- Which OSDU release milestone is pinned, and why?
- What OSDU runtime mode is used? (In-cluster dependencies vs ACK-managed AWS deps?)
- Which optional OSDU modules are deployed? (GCZ, DDMS, Wellbore DDMS, etc.)

---

## Sparse Evidence Protocol

When a candidate ADR's Decision cannot be confirmed from existing ledger entries, **do not draft the ADR with invented claims**. Instead:

1. Present a structured gap prompt to the user:

```
ADR EVIDENCE GAP: <candidate decision title>
Unanswerable question: <what needs confirming>
What I looked for: <EV-ids checked>
What's missing: <specific file, IaC block, Jira comment, Confluence page>

Options:
  A) Point me at the source — I will read it, add a ledger entry, and draft the ADR
  B) Skip this ADR — I will log it as a candidate in the ADR index with Low confidence
  C) Mark it Low confidence and draft with what I have — you accept the caveat
```

2. Use `AskQuestion` tool when in Cursor. In non-interactive environments, output the gap block as plaintext and wait for the next message.
3. Do not draft the ADR until the user responds.
4. If the user provides a source: read it, add the evidence entry to the ledger (with a new EV-id), then draft the ADR.
5. If the user skips: log the candidate title and unanswered question in an `## ADR Candidates (Unconfirmed)` section at the end of the ADR index file. Do not write a file for it.
6. If the user accepts Low confidence: draft the ADR, mark every unconfirmed claim `[unconfirmed — code read pending]`, and assign Low.

---

## Required Workflow

1. **Read the template** at `templates/adr.md`. Understand every `<!-- AGENT: ... -->` and `<!-- REPLACE: ... -->` block — these are authoring rules, not text to copy.

2. **Read the system-overview, Evidence Ledger, and Source Inventory in full.** Build a working index: which EV-ids cover which components, what the contradictions are, and which sources are marked Gap.

3. **Run the ADR Discovery Protocol** for all 9 decision categories. For each category, list every candidate decision as a numbered working list. A candidate is: any non-obvious choice visible in code/IaC/docs that a different team could plausibly have made differently.

4. **Eliminate non-candidates.** Filter out: universal defaults (every system uses IAM), decisions that are forced by the cloud provider with no alternative, and capabilities that are features (not decisions).

5. **Confirm each surviving candidate in code or IaC.** For each:
   - If `graphify-out/graph.json` exists: run `graphify query "<decision area>"` to locate the relevant files, then read them to confirm.
   - If graphify is not available: directly read the relevant IaC modules, dependency manifests, configuration files, or entry-point code. **Do not skip this step.**
   - Locate the originating rationale: search ledger for `EV-Jxx` (Jira), `EV-CFxx` (Confluence), `EV-Sxx` (Slack), or inline architecture doc entries that explain *why* this choice was made.
   - Assign confidence per the Corroboration Rule.

6. **Invoke the Sparse Evidence Protocol** for any candidate whose Decision cannot be confirmed in code/IaC. Block until the user responds.

7. **Assign ADR numbers and titles.** Sequence: `001`, `002`, `003`… ordered by impact (most fundamental decisions first: compute platform → networking → auth → storage → messaging → observability → deployment → product). Title format: `NNN-<kebab-case-short-title>.md`. Title rule: start with what was decided, not why ("osdu-operator-manages-platform-lifecycle", not "why-we-chose-operator").

8. **Draft each ADR** from the template with `Status: Discovered`:
   - **Context**: the situation/forces that made this decision necessary. Cite EV-ids. Include the ledger's rationale (Jira epic, Confluence page, Slack thread, architecture doc) where recovered. Explicitly note if rationale is not recoverable.
   - **Decision Drivers**: numbered list of the specific forces that shaped the decision. Each driver must cite an EV-id. Do not invent drivers.
   - **Decision**: one testable, present-tense sentence. "X uses Y for Z." Confirm it against code or IaC. No qualifications, no "likely".
   - **Consequences → Becomes Easier**: what the decision made feasible that wouldn't have been otherwise.
   - **Consequences → Becomes Harder**: the real constraints and tech debt the system now lives with — including what motivates the migration if applicable.
   - **Applies To**: the AS-IS epics (`ASIS-<SYSTEM>-xx`) and any system-overview sections this decision governs. If a forward ADR already supersedes this, note it.
   - Assign confidence at the bottom: `**Confidence:** High / Medium / Low — <reason if not High>`.

9. **Surface contradiction-linked ADRs.** For every contradiction in the Evidence Ledger (`CON-xx`), check whether the conflict represents two competing decisions in force. If so, draft one ADR for the code-authoritative decision and reference the contradiction ID in its Context.

10. **Present all drafts to the user for review.** The user must confirm:
    - No ADR Decision was invented — every Decision is visible in code or IaC
    - No rationale was fabricated — Context cites real ledger entries
    - Confidence levels feel calibrated to the actual evidence quality
    - Bundled decisions have been correctly split into separate ADRs

11. **Write the files** to `assessments/<system>/adrs/` only after the user approves. Strip all `<!-- AGENT -->` and `<!-- REPLACE -->` blocks — none may survive in the shipped files.

12. **Produce an ADR index.** Write `assessments/<system>/adrs/README.md` (or `index.md`) listing all recovered ADRs with: number, title, one-line decision summary, confidence, and the forward ADR that supersedes it (when known). Include an `## ADR Candidates (Unconfirmed)` section if any candidates were skipped. Communicate next steps to user: `epic-extraction`.

---

## ADR Recovery Rules

- **Status is `Discovered`** — never `Proposed` or `Accepted` for a decision recovered from a running system.
- **One decision per ADR.** If a single ADR would have two `Decision` sentences, it needs to be split.
- **Code is authoritative.** When code and a doc/ticket disagree about what decision is in effect, the code wins. Record the conflict with `[Conflicts with EV-Jxx: <summary>; code is authoritative]`.
- **Rationale non-recovery is honest.** If you cannot find why the decision was made, say so: `[Rationale not recovered — the decision is confirmed in code (EV-Cxx) but no originating Jira/Confluence/Slack record was identified]`.
- **Supersession links belong in forward ADRs.** Do not pre-write the migration outcome in a Discovered ADR. State what IS and note it is a candidate for supersession.
- **No placeholder template text** — the shipped file must contain no `<!-- AGENT -->`, `<!-- REPLACE -->`, or example-row text.
- **Forward-state leakage is forbidden.** If a Jira ticket describes intent, label it `[intent, not confirmed in code — not included in this Discovered ADR]`.
- **Contradictions map to ADRs.** Every `CON-xx` entry in the Evidence Ledger should be examined: if it represents a decision in conflict with intent, it is an ADR candidate.

---

## Contradiction Handling

For every contradiction from the Evidence Ledger's `## Contradictions` section:

1. Check whether the non-authoritative source represents a competing *decision* that was made (e.g., a Jira ticket that approved one approach while code implements another).
2. If yes: draft the code-authoritative decision as the Discovered ADR. Reference the contradiction ID in the Context: `[See CON-xx in the Evidence Ledger — the non-code source conflicts with what is shipped; code is authoritative]`.
3. Note the contradiction in the ADR index under a `## Decision Conflicts` column.

---

## Reference Examples

- `samples/assessments/edi-express/adrs/001-osdu-on-aws-r3m25.md` — Discovered ADR format, rationale from code + Jira + runbook, Consequences describing the migration motivation

---

## Verification

Before presenting drafts and before writing files, confirm every item:

### Discovery completeness
- [ ] All 9 ADR Discovery Protocol categories were examined
- [ ] At least one ADR candidate was considered per category (even if filtered out with a reason)
- [ ] Every contradiction in the Evidence Ledger was checked for ADR candidacy
- [ ] Bundled decisions were split (no ADR Decision contains "and" referring to two independent choices)

### Evidence integrity
- [ ] Every ADR's Decision is confirmed in code or IaC (cited EV-Cxx or EV-Jxx + code read)
- [ ] Every cited EV-id exists in the Evidence Ledger (no phantom citations)
- [ ] Rationale non-recovery is explicitly stated where the "why" could not be found
- [ ] No ADR Driver was invented — every driver cites a real EV-id

### Anti-hallucination
- [ ] No invented version numbers, port numbers, or config values in any ADR
- [ ] No forward-state leakage ("will", "should", "planned") without `[intent, not confirmed in code]` label
- [ ] No fabricated rationale — Context either cites the original ticket/doc or admits the rationale is not recovered
- [ ] All contradiction-linked ADRs reference the CON-xx ID from the Evidence Ledger

### Confidence calibration
- [ ] Every ADR carries an explicit confidence level (High / Medium / Low)
- [ ] Every Low-confidence ADR names the specific source that would raise it
- [ ] Jira/Slack/Confluence-only decisions (no code confirmation) are marked Low
- [ ] Decisions confirmed in code + originating ticket are marked High

### Output hygiene
- [ ] All ADR files are under `assessments/<system>/adrs/`
- [ ] All files use `Status: Discovered`
- [ ] ADR index file (`README.md` or `index.md`) lists all ADRs and any unconfirmed candidates
- [ ] No `<!-- AGENT -->` or `<!-- REPLACE -->` text remains in any shipped file
- [ ] User explicitly approved all drafts before files were written
- [ ] Next step (`epic-extraction`) communicated to user
