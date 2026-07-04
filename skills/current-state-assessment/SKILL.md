---
name: current-state-assessment
description: Recover the AS-IS picture of an existing system from the evidence ledger — components, runtime topology, integration seams, dependencies, identity, data stores, tech debt, contradictions, and discovered ADRs — written to assessments/<system>/system-overview.md. Use after context-acquisition to baseline a brownfield system before planning a migration.
---

# Current-State Assessment Skill

## Purpose

Produce a deep, evidence-grounded, descriptive snapshot of an existing system — components, runtime topology, integration seams, external/cloud dependencies, identity, data stores, tech debt, and discovered architectural decisions — as `assessments/<system>/system-overview.md`. This is the entry document of the AS-IS reference model. Epics, features, and discovered ADRs build on it.

**It is descriptive, not a charter.** The AS-IS records current reality, not a program of work. It must not carry `Status`/`Success Criteria`/`Timeline` — those belong in initiative.md. Every claim must be traceable to a ledger evidence ID. Claims without evidence are not allowed.

---

## When to Use

- Baselining a brownfield system before a migration or re-platform initiative
- Refreshing an existing `system-overview.md` after significant system changes
- Establishing the AS-IS that the forward migration plan deltas against

---

## Required Inputs

- Evidence Ledger: `assessments/<system>/evidence-ledger.md` (from `context-acquisition`)
- Source Inventory: `assessments/<system>/source-inventory.md` (from `context-acquisition`)
- Template: `templates/system-overview.md`
- Code repos (local clones, paths from Source Inventory)
- graphify (optional): `graphify query "<topic>"` / `graphify-out/GRAPH_REPORT.md` — use if `graphify-out/graph.json` exists in the repo; fall back to direct file reads if not

If the Evidence Ledger or Source Inventory is missing, run `context-acquisition` first. Do not proceed without them.

---

## Corroboration Rule

Every claim in the system-overview must carry an explicit confidence level. Assign confidence as follows:

| Level | Rule |
|-------|------|
| **High** | 2+ independent sources agree (e.g. code + Jira, or code + Confluence), OR claim is directly read from code/IaC with no contradicting evidence |
| **Medium** | 1 code/IaC source, OR 2+ doc/ticket/Slack sources that agree, with no contradicting code |
| **Low** | 1 doc/ticket/Slack source only (code not read or not available), OR inferred from indirect evidence, OR code and doc conflict (code is authoritative but the doc claim is preserved) |

**Low is not a failure** — it is an honest signal that a code read or a source that was marked Gap in the inventory would raise it. Name the missing source.

---

## Anti-Hallucination Rules

These rules are absolute. Violating them produces an unreliable AS-IS that will corrupt downstream migration planning.

1. **No claim without a ledger evidence ID.** If you cannot cite `EV-Cxx`, `EV-Jxx`, `EV-CFxx`, or `EV-Sxx`, the claim does not go in the document — it either triggers the Sparse Evidence Protocol or is omitted entirely.
2. **No invented version numbers, port numbers, URLs, table names, or config values.** If you did not read it from code or a cited source, do not write it.
3. **No "likely", "probably", "may be", or "appears to".** These phrases hide un-evidenced inference. If you are uncertain, assign `Low` confidence and name what evidence is missing.
4. **No forward-state leakage.** Words like "will", "should be", "planned" do not belong in the AS-IS. If a Jira ticket describes intent rather than what is built, label it `[intent, not confirmed in code]` and assign Low confidence.
5. **Code beats docs and tickets.** When code and a doc/ticket disagree, write the code-authoritative claim at the stated confidence level and add a bracketed conflict note: `[Conflicts with EV-Jxx: <summary>; code is authoritative]`.
6. **No section may be filled from memory.** Every section must trace back to a read operation or a cited ledger entry performed in this session.

---

## AS-IS Deep-Dive Protocol

Before writing any section, interrogate the evidence ledger using these targeted questions. For each question, identify the specific EV-ids that answer it. If none do, invoke the Sparse Evidence Protocol.

### System Summary
- What does this system do for its users today, in one paragraph?
- Who operates it (team/org)? Who are its external users?
- What are its deployment environments (prod, staging, testlab, etc.)?
- What is its maturity level (PoC, pilot, production)?

### Components
For each component/service identified in the ledger:
1. What is its **primary responsibility** — what single thing does it do?
2. What **language/runtime** does it run on? (from code/dependency manifest — EV-Cxx)
3. What **frameworks** does it use? (from dependency manifest)
4. What is its **deployment unit** — Lambda, container, ECS task, Kubernetes Deployment, EC2?
5. What are its **configuration surfaces** — env vars, SSM params, k8s ConfigMaps, Secrets?
6. What are its **health/monitoring** endpoints or metrics?
7. Does it have a **test suite**? What is the coverage target and test strategy?

### Runtime Topology
1. How does a request or event flow from end to end? (trace at least one happy path)
2. Which components are **stateless** (can be scaled horizontally without coordination) and which are **stateful** (have PVCs, local disk, or in-memory state)?
3. Which components are **critical path** (unavailability breaks user-facing function) vs **optional** (degraded but not broken without them)?
4. What are the **deployment orchestrators** — Kubernetes operator, ECS service, Lambda event source?
5. What **namespaces / AWS accounts / VPCs / regions** do components run in?
6. Draw a mermaid flowchart: entry points → components → data stores → external dependencies.

### Integration Seams
A seam is any boundary the system crosses to talk to something it does not own. Name every one — these are the cut points a migration will touch.

For each seam, answer:
1. **From → To**: which component calls which other component or external service?
2. **Protocol**: HTTP/REST, gRPC, SNS/SQS, DynamoDB Streams, EventBridge, WebSocket, SMTP, LDAP?
3. **Contract**: is there an OpenAPI spec, Avro schema, or is the contract implicit in code?
4. **Auth at the seam**: bearer token, IAM SigV4, mTLS, API key, none?
5. **Failure mode**: what happens when the upstream is down — circuit breaker, retry, silent failure, user-visible error?
6. **Direction**: is it synchronous (caller blocks) or asynchronous (event-driven)?

### External & Cloud Dependencies
1. List every AWS service, third-party SaaS, or external API the system contacts.
2. For each: what data or function does the system depend on it for?
3. Is the dependency **hard** (system fails without it) or **soft** (degraded)?
4. Is there a **mock/simulate mode** in non-prod (e.g. `SimulatedMarketplaceClient`)?
5. Are credentials static (access keys, root creds) or dynamic (IRSA, Pod Identity, OIDC)?

### Identity & Auth
1. How do **end users** authenticate? (Cognito, Keycloak, OIDC, SAML, API key?)
2. How do **services** authenticate to each other? (IRSA, mTLS, bearer token, API key, none?)
3. What is the **authorization model**? (RBAC, ABAC, IAM policies, permission table in DB?)
4. Are there **multiple IdPs** in play, or a single one?
5. Are there **known credential hygiene issues** (shared root creds, static keys, no rotation)?

### Data Stores
For each store:
1. **Engine and version** (from code/IaC — not guessed)
2. **What data lives here** (from schema, code reads, or migration evidence)
3. **Who reads/writes** (which components)
4. **Durability and backup posture** (from IaC or runbook)
5. **At-rest encryption** (from IaC or doc)
6. **Known data quality issues or schema debt** (from TODO/FIXME grep, Jira, Slack)

### Tech Debt & Risks
Surface three categories:
1. **Evidence-backed debt** — items explicitly called out in TODO/FIXME grep (EV-Cxx inline notes), Jira (EV-Jxx), Slack (EV-Sxx), or architecture docs.
2. **Structural risks** — fragility visible in code (shared root creds, no retry, single-replica stateful, unencrypted in-transit, hardcoded IDs).
3. **Assessment risks** — sections or components whose confidence is Low because a source in the Source Inventory was a Gap. Name the gap and what it prevents knowing.

### Contradictions
List every item from the Evidence Ledger's `## Contradictions` section. For each:
- State what the conflict is
- Which source is authoritative (code beats docs)
- What the downstream risk is if unresolved

---

## Sparse Evidence Protocol

When the AS-IS Deep-Dive questions for a section cannot be answered from existing ledger entries, **do not fill the section with inference**. Instead:

1. Present a structured gap prompt to the user:

```
SECTION GAP: <section name>
Unanswered questions:
  - <specific question that has no evidence>
  - ...
What I need: <the missing read — a specific file, a Jira query, a Confluence page>

Options:
  A) Point me at the source — I will read it and add ledger entries before continuing
  B) Skip this question — I will mark it Low confidence and note the gap
```

2. Use `AskQuestion` tool when in Cursor. In non-interactive environments, output the gap block as plaintext and wait for the next message.
3. Do not proceed to write that section until the user responds.
4. If the user provides a source: read it, add the evidence entry to the ledger (with a new EV-id), then use it.
5. If the user skips: write the section with only the available evidence, mark every unanswered question `Low` confidence, and note what source would raise it.

---

## Required Workflow

1. **Read the template** at `templates/system-overview.md`. Every `<!-- AGENT: ... -->` block is an authoring rule. Every `<!-- REPLACE: ... -->` block is a fill target. These are not text to copy.

2. **Read the Evidence Ledger and Source Inventory in full.** Build a working index: which EV-ids cover which components, which sources are marked Gap, and what contradictions exist.

3. **Map components from code** — for each repo in the Source Inventory marked Reachable:
   - If `graphify-out/graph.json` exists: run `graphify query "<component name>"` to get the dependency subgraph. Confirm with targeted file reads.
   - If graphify is not available: directly read the repo's entry point(s), dependency manifest, and IaC files. Do not skip this step.
   - Answer the AS-IS Deep-Dive questions for **Components** and **Data Stores** from these reads.

4. **Trace runtime topology** — follow a request or event from entry point to persistence layer across every component. Read enough code/IaC to trace at least one end-to-end flow. Produce the mermaid flowchart.

5. **Enumerate integration seams** — for each outbound call or event in the code (HTTP client, AWS SDK call, SNS publish, EventBridge rule, DynamoDB stream), record it as a seam entry. Do not list seams from docs alone unless confirmed in code.

6. **Extract external dependencies and auth** from IaC (Terraform provider blocks, IAM roles, SSM params) and code (AWS SDK calls, auth middleware). Cross-check with `EV-C` (code) and `EV-CF`/`EV-S` (docs) entries.

7. **Compile tech debt** from three sources in parallel:
   - Inline ADR/TODO grep entries from the ledger (EV-Cxx "Inline Notes" or "Inline Docs")
   - Jira items marked In Progress / To Do that describe known deficiencies
   - Architecture docs that explicitly call out production gaps, follow-ups, or risks

8. **Invoke the Sparse Evidence Protocol** for any AS-IS Deep-Dive question that remains unanswered after steps 3–7. Block until resolved or explicitly skipped.

9. **Draft the system-overview** in template section order. For every table row and every paragraph, cite the EV-ids and assign a confidence level per the Corroboration Rule. Surface all contradictions in the `## Contradictions` section.

10. **Present the draft to the user for review.** The user must confirm:
    - No section is filled with invented facts
    - All named components exist in at least one Reachable source
    - Confidence levels feel calibrated to the actual evidence quality
    - Contradictions are correctly characterized (code-authoritative claim identified)

11. **Write the file** to `assessments/<system>/system-overview.md` only after the user approves the draft. Strip all `<!-- AGENT -->` and `<!-- REPLACE -->` blocks — none may survive in the shipped file.

12. **Queue the companion artifacts** — after writing, inform the user what to run next:
    - `adr-recovery` skill → produces `assessments/<system>/adrs/` (discovered ADRs with `Status: Discovered`)
    - `epic-extraction` skill → produces `assessments/<system>/epics/` (recovered epics from code + Jira)
    - `feature-extraction` skill → produces `assessments/<system>/features/` (recovered features per epic)

---

## Assessment Rules

- **Descriptive only** — no target-state design, no migration steps, no "we should". Those are forward artifacts.
- **Code is ground truth** for "what exists." When code and a doc/ticket disagree, the code claim wins; write the doc claim as a bracketed conflict note with `Low` confidence.
- **Integration seams are first-class.** Every place the system crosses a boundary is a seam a strangler-fig migration will swap. Do not omit them because they seem obvious.
- **Every claim cites evidence.** A claim with no EV-id is not allowed.
- **Uncorroborated claims are marked `Low` confidence** and identify what source would raise them.
- **No placeholder text** — the shipped file must contain no `<!-- AGENT -->`, `<!-- REPLACE -->`, or "lorem ipsum" scaffolding.
- **Contradictions are preserved, not resolved.** Name the conflict, name the authoritative source, leave both claims visible.
- **Assessment risks from Gaps are explicit.** Every source marked `Gap (user skipped)` or `Gap (does not exist)` in the Source Inventory must appear as an assessment risk in Tech Debt, lowering confidence for any claim that would require that source.
- **Forward-state leakage is forbidden.** If a Jira ticket describes intent, label it `[intent, not confirmed in code]` and assign Low confidence. Never present a planned feature as an existing one.

---

## Contradiction Handling

Every contradiction from the Evidence Ledger's `## Contradictions` section must appear in the system-overview in **two places**:

1. **Inline** at the point of first mention — add a bracketed conflict note: `[Conflicts with EV-Jxx — see Contradictions section]`.
2. **`## Contradictions` section** at the end of the document — one row per contradiction using this format:

| ID | Conflict | Authoritative source | Non-authoritative source | Risk if unresolved |
|----|---------|---------------------|--------------------------|-------------------|
| CON-xx | <what disagrees> | <code/IaC EV-id> | <doc/ticket EV-id> | <downstream impact> |

---

## Reference Examples

- [`samples/assessments/edi-express/system-overview.md`](../../samples/assessments/edi-express/system-overview.md) — minimal example (pre-deep-dive style)
- [`samples/assessments/edi-express/adrs/001-osdu-on-aws-r3m25.md`](../../samples/assessments/edi-express/adrs/001-osdu-on-aws-r3m25.md) — discovered ADR format

---

## Verification

Before presenting the draft and before writing the file, confirm every item:

### Content completeness
- [ ] All 8 template sections are present: System Summary, Components, Runtime Topology, Integration Seams, External & Cloud Dependencies, Identity & Auth, Data Stores, Tech Debt & Risks
- [ ] A mermaid flowchart is present in Runtime Topology
- [ ] A `## Contradictions` table is present (even if it only says "None identified")
- [ ] Every component listed in the Source Inventory as Reachable appears in the Components table
- [ ] At least one end-to-end request/event flow is traced in Runtime Topology
- [ ] Every integration seam was confirmed in code/IaC (not inferred from docs alone)

### Evidence integrity
- [ ] Every table row cites at least one EV-id
- [ ] Every cited EV-id exists in the Evidence Ledger (no phantom citations)
- [ ] Every claim carries an explicit confidence level (High / Medium / Low)
- [ ] No sentence contains "likely", "probably", "may be", "appears to", or "seems" without a bracketed `[Low confidence — <reason>]` note

### Anti-hallucination
- [ ] No invented version numbers, port numbers, URLs, table names, or config values
- [ ] No forward-state leakage ("will", "should", "planned") without `[intent, not confirmed in code]` label
- [ ] Every Jira/Slack/Confluence-only claim is marked Medium or Low
- [ ] All contradictions from the Evidence Ledger appear in both the inline conflict note and the Contradictions table

### Gaps and risks
- [ ] Every source marked Gap in the Source Inventory appears as an assessment risk in Tech Debt
- [ ] Sections with Low-confidence claims name the specific source that would raise confidence
- [ ] The Sparse Evidence Protocol was invoked (and user responded) for any section with zero supporting EV-ids

### Output hygiene
- [ ] File written to `assessments/<system>/system-overview.md`
- [ ] No `<!-- AGENT -->` or `<!-- REPLACE -->` text remains in the shipped file
- [ ] User explicitly approved the draft before the file was written
- [ ] Companion artifacts queue communicated to user (adr-recovery, epic-extraction, feature-extraction)
