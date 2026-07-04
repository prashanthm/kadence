---
name: epic-extraction
description: Recover the AS-IS capability areas of an existing system as epics in assessments/<system>/epics/, reusing the epic shape and citing evidence. Use to build the capability map a migration plan deltas against.
---

# Epic Extraction Skill

## Purpose

Recover the capability areas an existing system already delivers and record them as AS-IS epics under `assessments/<system>/epics/`. A mature system is many initiatives accreted over time; this capability map — not a reconstructed charter — is what the forward migration expresses a delta against (keep / change / add / retire). AS-IS epics use the same shape as forward epics so reviewers read them without a mental context switch.

This mirrors the forward `epic-generation` skill but recovers what exists instead of proposing what to build. Every AS-IS epic must describe *what the system does today* — verifiable against code, IaC, and Jira — not what was planned, aspirationally described, or partially implemented.

**Quality bar:** Every epic's capability claim must trace to at least one evidence ledger ID. A capability that exists only in docs/tickets but has no code confirmation carries Low confidence and must say so explicitly.

---

## When to Use

- Immediately after `current-state-assessment` (and optionally after `adr-recovery`), to map the AS-IS capability surface
- Before forward planning, so target epics can be framed as deltas ("what changes relative to `asis-<system>-<capability>`")
- To establish the inventory the `parity-baseline` skill checks for no-regression during migration

---

## Required Inputs

- `assessments/<system>/system-overview.md` (from `current-state-assessment`) — primary source of component groupings, integration seams, and data stores
- `assessments/<system>/evidence-ledger.md` (from `context-acquisition`)
- `assessments/<system>/source-inventory.md` (from `context-acquisition`)
- `assessments/<system>/adrs/` (from `adr-recovery`) — ADRs that constrain specific capability areas
- Code/IaC repos (local clones, paths from Source Inventory) — to confirm capability boundaries
- graphify (optional): `graphify query "<capability>"` if `graphify-out/graph.json` exists; fall back to direct file reads otherwise
- Originating Jira epics and Confluence pages from the ledger (EV-Jxx, EV-CFxx) — original epic charter as cross-reference
- Template: `templates/epic.md`
- Reference: `samples/assessments/edi-express/epics/asis-edi-express-provisioning.md`

If `system-overview.md` or the Evidence Ledger is missing, run `current-state-assessment` first. Do not proceed without them.

---

## Corroboration Rule

Every AS-IS epic and every capability claim within it must carry an explicit confidence level. Assign confidence as follows:

| Level | Rule |
|-------|------|
| **High** | Capability confirmed in code/IaC **and** corroborated by a Jira epic, Confluence page, or originating ticket (2+ independent sources) |
| **Medium** | Capability confirmed in code/IaC (1 source), OR 2+ doc/ticket/Slack sources that agree, with no contradicting code read |
| **Low** | Capability described in docs/tickets/Slack only — code not read or source was a Gap. Must name the specific code read that would raise confidence. |

**Low is not a failure** — it is an honest signal that the capability needs code confirmation. A missed AS-IS epic is worse than a Low-confidence one: an uncounted capability becomes an invisible regression risk.

---

## Anti-Hallucination Rules

These rules are absolute. Invented epics corrupt the parity baseline and mislead migration planning.

1. **No capability claim without a ledger evidence ID.** If you cannot cite `EV-Cxx`, `EV-Jxx`, `EV-CFxx`, or `EV-Sxx`, the claim does not go in the epic — either invoke the Sparse Evidence Protocol or omit it.
2. **No invented acceptance criteria.** Acceptance criteria in an AS-IS epic must reflect conditions the system *currently meets*, confirmed by code or a cited ledger entry. Do not write ACs that describe desired future behavior.
3. **No forward-state leakage.** Words like "will", "should be", "planned" do not belong in an AS-IS epic. If a Jira ticket describes intent rather than what is shipped, label it `[intent, not confirmed in code]` and assign Low confidence.
4. **Code beats docs.** When code and a ticket/Confluence page disagree about what capability exists, write the code-authoritative claim and add: `[Conflicts with EV-Jxx: <summary>; code is authoritative]`.
5. **No invented feature names or IDs.** Every feature listed in the Features table must exist in code, IaC, or Jira — confirmed by an EV-id. Do not pre-create features based on what the system "probably" has.
6. **No section filled from memory.** Every paragraph must trace back to a read or cited ledger entry from this session.
7. **Do not split a running system by org chart.** Capability areas must follow functional boundaries (what users can do), not team or repo boundaries. A capability that spans 3 repos is one epic if it serves one user need.

---

## Capability Discovery Protocol

Before drafting any epic, systematically scan the system-overview and evidence ledger using these capability area prompts. Each prompt produces one or more epic candidates. Eliminate overlapping candidates; merge only when the user story is genuinely the same.

### Self-Service & Lifecycle Management
- Can users subscribe, provision, or onboard themselves without ops intervention? → subscription / provisioning epic
- Can users upgrade, downgrade, or decommission a deployment from a portal? → lifecycle management epic
- Is there a marketplace integration (billing, entitlements, product codes)? → marketplace billing epic

### Platform Operations
- Is there an operator or orchestrator that manages the full platform lifecycle? → platform operator epic
- Can the platform be deployed end-to-end from a single command or pipeline? → deployment orchestration epic
- Is there a configuration or upgrade mechanism for the running platform? → platform configuration management epic

### Data & Storage Operations
- What does the system do for data ingestion, indexing, or search? → data ingestion / search epic
- Is there a tiered storage strategy (hot/cold, EBS/S3/Outposts)? → storage management epic
- Is there a special-purpose storage adapter (e.g. S3 compatibility proxy)? → storage compatibility epic
- Are there data partition management operations? → partition management epic

### Identity, Access & Roles
- How do users log in, and how is that login experience managed? → authentication / IdP integration epic
- Can admins manage user accounts, roles, and permissions through a UI or API? → user management epic
- Are there platform-level entitlements or RBAC policies? → authorization management epic

### Monitoring, Observability & Reporting
- Is there availability monitoring for platform endpoints? → platform monitoring epic
- Are there automated reports (availability, billing, usage) delivered to stakeholders? → reporting epic
- Is there a logging or tracing stack? → observability infrastructure epic

### API Surface & Console
- Is there a management console UI? → platform console epic
- Are there APIs that external systems or customers consume? → API surface epic
- Is there a spatial or search query capability (GCZ, Elasticsearch)? → spatial / search epic

### Security & Regulatory Reporting
- Is there a credential management or rotation strategy? → credential management epic (if partial, still a Low-confidence epic)
- Is there an audit or regulatory-reporting capability? → audit / regulatory-reporting epic
- Is there encryption at rest or in transit beyond AWS defaults? → encryption management epic

### Developer & Operator Tools
- Is there a deployment runbook or operator tooling? → operator tooling epic
- Is there a CI/CD pipeline integration? → continuous deployment epic
- Are there test / simulation modes for non-prod? → test environment management epic

---

## Sparse Evidence Protocol

When the Discovery Protocol produces a candidate epic but ledger entries cannot substantiate the capability claim, **do not draft a fictional epic**. Instead:

1. Present a structured gap prompt to the user:

```
EPIC EVIDENCE GAP: <candidate capability title>
Unanswerable: <what the epic would claim that has no ledger support>
What I looked for: <EV-ids checked>
What's missing: <specific file, Jira epic, Confluence page, or code path>

Options:
  A) Point me at the source — I will read it, add ledger entries, and draft the epic
  B) Skip this epic — I will log it as a candidate with Low confidence in the epic index
  C) Draft at Low confidence — you accept the caveat that the capability is not code-confirmed
```

2. Use `AskQuestion` tool when in Cursor. In non-interactive environments, output the gap block as plaintext and wait for the next message.
3. Do not draft the epic until the user responds.
4. If the user provides a source: read it, add the evidence entry to the ledger (with a new EV-id), then draft the epic.
5. If the user skips: log the candidate title in an `## Epic Candidates (Unconfirmed)` section in the epic index. Do not write a file for it.
6. If the user accepts Low confidence: draft the epic, mark every unconfirmed capability `[unconfirmed — code read pending]`, and assign Low.

---

## Required Workflow

1. **Read the template** at `templates/epic.md`. Every `<!-- AGENT: ... -->` block is an authoring rule. Every `<!-- REPLACE: ... -->` block is a fill target. These are not text to copy.

2. **Read the system-overview, Evidence Ledger, Source Inventory, and discovered ADRs in full.** Build a working index: components, seams, data stores, tech debt, contradictions, and which sources are Gap.

3. **Run the Capability Discovery Protocol** for all 8 area groups. For each prompt, list every candidate capability as a working list. A candidate is: a distinct user-facing or operator-facing function the system enables.

4. **Cluster candidates into epics.** Merge candidates that serve the same user need into one epic. Do not split by repo, team, or component if they serve one capability. Assign a draft epic title.

5. **Confirm each epic's capability in code or IaC.** For each draft epic:
   - If `graphify-out/graph.json` exists: run `graphify query "<capability>"` to get relevant files, then read the entry-point code or IaC that implements the capability.
   - If graphify is not available: directly read the relevant handler, Lambda function, Kubernetes CRD, Terraform module, or React route that implements the capability.
   - Locate the originating Jira epic from the ledger (EV-Jxx) that maps to this capability area as a cross-reference.
   - Assign confidence per the Corroboration Rule.

6. **Invoke the Sparse Evidence Protocol** for any candidate epic whose core capability claim cannot be confirmed from existing ledger entries. Block until the user responds.

7. **Assign epic slugs.** Each AS-IS epic is named by a **descriptive slug** — no positional numbers. Slug format: `asis-<system>-<kebab-case-capability>` (e.g. `asis-edi-express-provisioning`, `asis-edi-express-platform-operator`). File: `assessments/<system>/epics/<slug>.md`. Order for review by dependency (foundational platform capabilities first: provisioning, operator → user-facing capabilities → observability → developer tooling), but the slug carries the identity, not a sequence number.

8. **Draft each AS-IS epic** from the template with these adaptations:
   - **Metadata**: Replace `Initiative` with `System overview` link and `Evidence ledger` link. Add `Type: AS-IS (reference — not tracked work)`. Reference epics are identified by their descriptive slug — no GitHub Epic link and no positional ID.
   - **Problem** (present tense): the gap users would face without this capability TODAY. Root in real evidence.
   - **What We're Building** header: replace with `## What the System Delivers` and write in present tense. Every sentence cites EV-ids.
   - **Who It's For**: the real user/operator role (from Jira personas, Confluence, or code).
   - **Value**: outcomes the system delivers today (confirmed), not aspirations.
   - **Acceptance Criteria**: use `[x]` for criteria the system currently meets, `[ ]` for criteria from the Jira epic that are not yet confirmed in code. Mark `[ ]` items `[intent, not confirmed in code — EV-Jxx]`.
   - **Features table**: list AS-IS deliverables this epic bundles. These become the inputs to `feature-extraction`. Name each feature by a **descriptive slug** (`asis-<system>-<kebab-case-feature>`) — no positional feature IDs. Each extracted feature links back with `Part of epic: asis-<system>-<capability>`. Phase = `Shipped` unless a feature is partially implemented (then `Partial`).
   - **Source Evidence & Confidence**: one section with the ledger ids used (code + Jira/Confluence), the assigned confidence level, and known tech debt in this capability area.
   - **Relevant ADRs**: link the discovered ADRs that govern this capability area.

9. **Surface contradiction-linked epics.** For every contradiction in the Evidence Ledger (`CON-xx`), check whether it affects a capability claim. If it does, note it inline and assign Medium/Low confidence to the affected epic or AC.

10. **Present all drafts to the user for review.** The user must confirm:
    - Every capability claim exists in at least one Reachable source
    - No epic describes future intent as current capability
    - Confidence levels feel calibrated to the actual evidence quality
    - Every component in the system-overview maps to at least one epic's Features table

11. **Write the files** to `assessments/<system>/epics/` only after the user approves. Strip all `<!-- AGENT -->` and `<!-- REPLACE -->` blocks — none may survive.

12. **Produce an epic index.** Write `assessments/<system>/epics/README.md` (or `index.md`) listing all AS-IS epics with: ID, slug, one-line capability summary, confidence, number of features, and any relevant discovered ADRs. Include an `## Epic Candidates (Unconfirmed)` section if any candidates were skipped. Communicate next step: `feature-extraction`.

---

## Epic Extraction Rules

- **Present tense throughout.** "The system provisions..." not "The system will provision..."
- **Functional boundaries, not repo/team boundaries.** A capability that spans 3 repos is one epic if it serves one user need.
- **AS-IS epics are reference, not work.** They have no GitHub issue, no owner, no status tracker. They describe what exists.
- **Every epic cites evidence and carries a confidence level.** A capability only in docs/Slack but not in code is Low and flagged.
- **Descriptive slugs are stable.** Forward delta epics and migration ADRs reference AS-IS epics by their descriptive slug — never by a positional number.
- **Known tech debt belongs in each epic.** If the capability area has documented debt or Jira items flagging deficiencies, record them in the `Source Evidence & Confidence` section. Omitting debt leads to silent migration risk.
- **No placeholder template text** — the shipped file must contain no `<!-- AGENT -->`, `<!-- REPLACE -->`, or example-row text.
- **Contradictions are preserved.** If a capability claim conflicts with a Jira or Confluence description, preserve the conflict inline and in the epic's evidence note.
- **Every system-overview component maps to an epic.** Verify the Components table in the system-overview is fully covered. An orphan component is a missing epic candidate.

---

## Contradiction Handling

For every contradiction from the Evidence Ledger's `## Contradictions` section:

1. Check whether the conflict affects a capability claim in a draft epic.
2. If yes: add a bracketed conflict note inline in the affected AC or capability description: `[Conflicts with EV-Jxx — see CON-xx in Evidence Ledger; code is authoritative]`.
3. Assign Medium or Low confidence to the affected epic or AC depending on the severity.
4. Note the contradiction in the `Source Evidence & Confidence` section of the epic.

---

## Reference Examples

- `samples/assessments/edi-express/epics/asis-edi-express-provisioning.md` — AS-IS epic with evidence note, present-tense ACs, Features table, and tech debt note

---

## Verification

Before presenting drafts and before writing files, confirm every item:

### Discovery completeness
- [ ] All 8 Capability Discovery Protocol groups were examined
- [ ] Every component in the system-overview's Components table maps to at least one epic's Features table
- [ ] Every integration seam in the system-overview maps to at least one epic as a capability or dependency
- [ ] No epic describes future capability without `[intent, not confirmed in code]` label

### Evidence integrity
- [ ] Every epic's `What the System Delivers` section cites at least one EV-id per capability claim
- [ ] Every cited EV-id exists in the Evidence Ledger (no phantom citations)
- [ ] Every epic carries an explicit confidence level (High / Medium / Low)
- [ ] Every currently-met AC is marked `[x]`; unconfirmed ACs are marked `[ ]` with `[intent, not confirmed in code]`

### Anti-hallucination
- [ ] No invented feature names or IDs in any Features table
- [ ] No forward-state leakage without `[intent, not confirmed in code]` label
- [ ] All contradiction-linked epics reference the CON-xx ID from the Evidence Ledger
- [ ] No epic was filled from memory — every claim traces to a read or ledger entry in this session

### Completeness
- [ ] All discovered ADRs are linked from the relevant epics
- [ ] Every source marked Gap in the Source Inventory appears as a confidence caveat in the affected epics
- [ ] Known tech debt in each capability area is recorded in `Source Evidence & Confidence`
- [ ] Epic candidates skipped via Sparse Evidence Protocol are logged in the epic index

### Output hygiene
- [ ] All epic files are under `assessments/<system>/epics/`
- [ ] Epic index file lists all epics and any unconfirmed candidates
- [ ] Descriptive slugs (`asis-<system>-<capability>`) are unique and stable — no positional numbers used as identity
- [ ] No `<!-- AGENT -->` or `<!-- REPLACE -->` text remains in any shipped file
- [ ] User explicitly approved all drafts before files were written
- [ ] Next step (`feature-extraction`) communicated to user
