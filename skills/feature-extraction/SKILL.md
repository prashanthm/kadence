---
name: feature-extraction
description: Recover the AS-IS deliverables under each extracted epic as features in assessments/<system>/features/, citing evidence. Use to complete the capability inventory the parity baseline checks against.
---

# Feature Extraction Skill

## Purpose

Recover the concrete deliverables an existing system provides under each extracted epic, and record them as AS-IS features under `assessments/<system>/features/`. This completes the AS-IS capability inventory — the line-item list the `parity-baseline` uses as the no-regression gate, and the set the decommission plan decides keep/retire on.

A **feature** is a shippable, independently verifiable unit of behavior: something a user or system can do, produce, or observe today. It is finer-grained than an epic (which spans a capability area) but coarser than a task (which is implementation work). The test of a feature: "can a QA engineer verify it against the running system without reading the code?"

This mirrors the forward `feature-generation` skill but recovers *shipped behavior* instead of deriving new deliverables. Completeness matters more than brevity — a missed AS-IS feature is a silent regression risk the migration will not catch.

**Quality bar:** Every feature's behavioral claim must trace to at least one evidence ledger ID. Features confirmed only in docs/tickets but not in code carry Low confidence and must say so. Features that are partially implemented must be explicitly marked `Partial`.

---

## When to Use

- Immediately after `epic-extraction`, to itemize the deliverables under each AS-IS epic
- To build the capability inventory the `parity-baseline` skill consumes
- To give the migration plan a per-feature unit to map AS-IS → TO-BE (keep / change / retire / add)

---

## Required Inputs

- `assessments/<system>/epics/` (from `epic-extraction`) — the Features table in each epic is the starting candidate list
- `assessments/<system>/system-overview.md` (from `current-state-assessment`)
- `assessments/<system>/evidence-ledger.md` (from `context-acquisition`)
- `assessments/<system>/source-inventory.md` (from `context-acquisition`)
- `assessments/<system>/adrs/` (from `adr-recovery`) — ADRs that constrain specific features
- Code/IaC repos (local clones, paths from Source Inventory) — to confirm each feature's behavior
- graphify (optional): `graphify query "<feature behavior>"` if `graphify-out/graph.json` exists; fall back to direct file reads otherwise
- Originating Jira stories/tasks from the ledger (EV-Jxx) — original story ACs as cross-reference
- Template: `templates/feature.md`
- Reference: `samples/assessments/edi-express/features/asis-edi-express-portal-provisioning.md`

If the epic files or Evidence Ledger are missing, run `epic-extraction` and `context-acquisition` first. Do not proceed without them.

---

## Corroboration Rule

Every AS-IS feature and every behavioral claim within it must carry an explicit confidence level. Assign confidence as follows:

| Level | Rule |
|-------|------|
| **High** | Behavior confirmed in code/IaC **and** corroborated by a Jira story, Confluence page, or integration test (2+ independent sources) |
| **Medium** | Behavior confirmed in code/IaC (1 source), OR 2+ doc/ticket/Slack sources that agree, with no contradicting code read |
| **Low** | Behavior described in docs/tickets/Slack only — code not read or source was a Gap. Must name the specific file or function that would confirm it. |

**Low is not a failure.** A Low-confidence feature is better than a missing feature: missing features become invisible regression risks. Low signals "this needs a code read before the parity gate closes."

---

## Anti-Hallucination Rules

These rules are absolute. Invented feature behavior will produce a false parity baseline and undercount migration risk.

1. **No behavioral claim without a ledger evidence ID.** If you cannot cite `EV-Cxx`, `EV-Jxx`, `EV-CFxx`, or `EV-Sxx`, the claim does not go in the feature — either invoke the Sparse Evidence Protocol or omit it.
2. **No invented acceptance criteria.** Every AC in an AS-IS feature must reflect a condition the system *currently meets*, confirmed by code or a cited ledger entry. Do not write ACs that describe desired behavior.
3. **No forward-state leakage.** Words like "will", "should be", "planned" do not belong in an AS-IS feature. If a Jira story describes intent, label it `[intent, not confirmed in code]` and assign Low confidence.
4. **Code beats docs.** When code and a ticket/doc disagree about what the feature does, write the code-authoritative behavior and add: `[Conflicts with EV-Jxx: <summary>; code is authoritative]`.
5. **No invented API signatures, table names, or endpoint paths.** Copy them verbatim from code reads or ledger entries. Do not construct them from pattern-matching.
6. **No section filled from memory.** Every behavioral paragraph must trace back to a read or a cited ledger entry performed in this session.
7. **Partial implementations must be explicit.** If a Jira story is `In Progress` or `To Do` but partial code exists, the feature is `Partial` — not `Shipped`. The AC that is not yet met must be `[ ]` with `[partial — EV-Jxx]`.

---

## Feature Discovery Protocol

The starting candidate list for each epic is the Features table in its epic file. **Do not treat this as complete** — the epic Features table was a first-pass draft. Use this protocol to confirm, extend, and prune it.

For each epic, ask:

### Step 1: Enumerate entry points
- What are the **entry points** for this capability? (React routes, API endpoints, Lambda event sources, CRD specs, CLI commands, systemd timers)
- Each distinct entry point is a feature candidate. Read the handler/route to understand what it does.

### Step 2: Enumerate data mutations
- What **data mutations** does this capability produce? (create/read/update/delete per entity)
- Each distinct mutation type that a user initiates is a feature candidate (e.g. "User creates subscription" and "User deactivates subscription" are two features if they have different behaviors).

### Step 3: Enumerate integrations triggered
- What **integrations** does this capability trigger? (downstream API calls, events published, emails sent, reports generated)
- Each integration that represents a user-observable outcome is a feature candidate.

### Step 4: Enumerate failure / error paths
- Are there documented **retry, dead-letter, or fallback** behaviors?
- If the retry/fallback is user-observable (e.g. SQS dead-letter reprocessing, simulate mode in non-prod), it is a feature in the `Platform Operations` or `Reliability` category.

### Step 5: Enumerate configuration surfaces
- What **configuration or feature-flag** surfaces does this capability expose?
- Each flag that gates a distinct behavior (not just an env var that sets a value) is a feature candidate (e.g. `ENABLE_M25`, `EXTERNAL_IDP_REPLACEMENT_ENABLED`).

### Step 6: Cross-check against the epic's Jira stories
- Pull the Jira stories in the ledger (EV-Jxx) that belong to this epic's original Jira counterpart.
- Each "Done" story that has code confirmation maps to a feature. Each "In Progress" or "To Do" story maps to a Partial or Low-confidence feature.

### Step 7: Cross-check against integration seams in the system-overview
- Every integration seam in the system-overview that is owned by this epic's capability area must appear as a feature.
- A seam without a feature is a missing feature candidate.

### Step 8: Identify parity-critical features
- Mark features that are blockers for migration parity — i.e., without them the migrated system regresses on user-visible behavior — with `Parity-Critical: true` in the Source Evidence & Confidence section.

---

## Feature Granularity Rules

- **Too coarse**: "User management" (covers CRUD users + roles + permissions = 3+ features)
- **Right**: "Admin creates a user account" or "Admin assigns a role to a user"
- **Too fine**: "HTTP POST handler validates Content-Type header" (implementation detail, not a verifiable user behavior)
- **Test**: can a QA engineer write a test for this feature without reading the implementation? If yes, it is the right size. If not, it is too fine.
- **Degenerate**: if two "features" always ship and break together, merge them into one.

---

## Sparse Evidence Protocol

When a feature candidate's behavior cannot be confirmed from existing ledger entries, **do not draft a fictional feature**. Instead:

1. Present a structured gap prompt to the user:

```
FEATURE EVIDENCE GAP: <candidate feature title>  (Epic: <epic-slug>)
Unanswerable: <the behavioral claim that has no ledger support>
What I looked for: <EV-ids checked>
What's missing: <specific handler, endpoint, schema, or Jira story>

Options:
  A) Point me at the source — I will read it, add ledger entries, and draft the feature
  B) Skip this feature — I will log it as a candidate in the feature index with Low confidence
  C) Draft at Low confidence — you accept the caveat that the behavior is not code-confirmed
```

2. Use `AskQuestion` tool when available (interactive IDE). In non-interactive environments, output the gap block as plaintext and wait for the next message.
3. Do not draft the feature until the user responds.
4. If the user provides a source: read it, add the evidence entry to the ledger (with a new EV-id), then draft the feature.
5. If the user skips: log the candidate in an `## Feature Candidates (Unconfirmed)` section in the feature index. Do not write a file for it.
6. If the user accepts Low confidence: draft the feature, mark every unconfirmed behavior `[unconfirmed — code read pending]`, and assign Low.

---

## Required Workflow

1. **Read the template** at `templates/feature.md`. Every `<!-- AGENT: ... -->` block is an authoring rule. Every `<!-- REPLACE: ... -->` block is a fill target. These are not text to copy.

2. **Read all epic files, the system-overview, and the Evidence Ledger in full.** Build a working index: which EV-ids cover which behaviors, what the contradictions are, which sources are Gap.

3. **Process one epic at a time.** Pick the most foundational epic first (usually provisioning or platform operator).

4. **Run the Feature Discovery Protocol** (Steps 1–8) for the selected epic. Produce the expanded candidate list.

5. **Apply Feature Granularity Rules** to the candidate list: merge too-fine candidates, split too-coarse ones, drop implementation details.

6. **Confirm each candidate in code or IaC.** For each:
   - If `graphify-out/graph.json` exists: run `graphify query "<feature behavior>"` to locate the handler, then read it to confirm the exact behavior.
   - If graphify is not available: directly read the handler function, Lambda event source, React route, Kubernetes CRD reconciler, or Terraform module that implements the behavior. **Do not skip this step.**
   - Locate the originating Jira story (EV-Jxx) as a cross-reference. Check whether the story's ACs are met in code.
   - Assign confidence per the Corroboration Rule.
   - Mark parity-critical features (Step 8 of the Discovery Protocol).

7. **Invoke the Sparse Evidence Protocol** for any candidate whose behavior cannot be confirmed from existing ledger entries. Block until the user responds.

8. **Assign feature slugs.** Each AS-IS feature is named by a **descriptive slug** — no positional feature numbers. Slug format: `<epic-slug>-<kebab-case-behavior>` (e.g. `asis-edi-express-portal-provisioning`). File: `assessments/<system>/features/<slug>.md`. Order for review by dependency (happy-path features first → error/retry features → configuration/flag features), but the slug carries the identity, not a sequence number.

9. **Draft each AS-IS feature** from the template with these adaptations:
   - **Header**: `Part of epic: <epic-slug>`. `Slug: <feature-slug>`. `Type: AS-IS (reference — describes shipped behavior)`.
   - **What** (present tense, one paragraph): the exact behavior the system delivers, end-to-end. Include: who initiates it, what the system does, what the observable output is. Cite EV-ids for every behavioral claim. Do not pad.
   - **Why**: the specific epic acceptance criterion this feature satisfies (cite the AC text from the epic by exact wording).
   - **Acceptance Criteria**: present-tense, verifiable conditions the running system currently meets. Use `[x]` for confirmed; `[ ]` with `[partial — EV-Jxx]` for partially shipped; `[ ]` with `[intent, not confirmed in code]` for Jira-only.
   - **Depends On**: real runtime dependencies (other features, ADRs, AWS services, in-cluster services). No aspirational dependencies.
   - **Diagrams**: include a mermaid sequence or flow diagram *only* for interaction-heavy features (auth flows, multi-step API chains, async event sequences). Skip for simple CRUD behavior.
   - **Tasks**: omit entirely or leave explicitly blank. AS-IS features are reference, not scheduled work.
   - **Source Evidence & Confidence**: ledger ids (code + Jira/Confluence), confidence level, parity-critical flag if applicable, and any known behavior debt (e.g. "rate limiting absent", "no retry on downstream failure", "CORS wildcard").

10. **Update the parent epic's Features table** to reference each feature by its descriptive slug and path `assessments/<system>/features/<slug>.md`. The link is by slug — no positional feature ID.

11. **Present all feature drafts to the user for review** (per epic, not all at once). The user must confirm:
    - Every behavioral claim exists in at least one Reachable source
    - No feature describes future intent as current behavior
    - Confidence levels feel calibrated to the actual evidence quality
    - Parity-critical flags are correctly applied

12. **Write the files** to `assessments/<system>/features/` only after the user approves each batch. Strip all `<!-- AGENT -->` and `<!-- REPLACE -->` blocks — none may survive. Repeat steps 3–12 for each remaining epic.

13. **Produce a feature index.** After all epics are processed, write `assessments/<system>/features/README.md` (or `index.md`) listing all AS-IS features with: ID, slug, epic, one-line behavior summary, confidence, parity-critical flag, and implementation status (Shipped / Partial / Low confidence). Include an `## Feature Candidates (Unconfirmed)` section if any candidates were skipped. Communicate next step: `parity-baseline`.

---

## Feature Extraction Rules

- **Present tense throughout.** "The metering Lambda reports WRC units..." not "...will report..."
- **Verifiable behavior only.** If it cannot be verified against the running system, it is not a feature — it is either a task or an intent.
- **AS-IS features are reference, not work.** No owner, no status, no Tasks table.
- **Every feature maps to exactly one epic** via `Part of epic: <epic-slug>`. A feature cannot belong to two epics. If it crosses a boundary, place it in the most relevant epic and reference the other in `Depends On`.
- **Every feature cites evidence and carries a confidence level.** A behavior confirmed only in docs is Low and flagged.
- **Descriptive slugs are stable.** The parity baseline, migration plan, and decommission plan reference features by their descriptive slug — never by a positional number.
- **Partial features must be explicit.** Mark them `Partial` in the index; ACs not yet met are `[ ]` with `[partial]`. Do not present partial behavior as fully shipped.
- **Known behavior debt belongs in each feature.** If the feature area has documented limitations (no retry, no rate limiting, PoC-grade auth, missing encryption), record them in `Source Evidence & Confidence`. Omitting debt produces a false parity baseline.
- **No placeholder template text** — the shipped file must contain no `<!-- AGENT -->`, `<!-- REPLACE -->`, or example-row text.
- **Parity-critical features must be labeled.** Any feature whose absence in the migrated system would represent a user-visible regression must be explicitly flagged.

---

## Contradiction Handling

For every contradiction from the Evidence Ledger's `## Contradictions` section:

1. Check whether the conflict affects a behavioral claim in a draft feature.
2. If yes: add a bracketed conflict note in the feature's `What` or AC: `[Conflicts with EV-Jxx — see CON-xx in Evidence Ledger; code is authoritative]`.
3. Assign Medium or Low confidence to the affected feature or AC depending on severity.
4. Note the contradiction in the feature's `Source Evidence & Confidence` section.

---

## Reference Examples

- `samples/assessments/edi-express/features/asis-edi-express-portal-provisioning.md` — AS-IS feature with present-tense What, code-confirmed ACs, real Depends On, evidence note

---

## Verification

Before presenting drafts and before writing files, confirm every item per epic batch:

### Discovery completeness
- [ ] All 8 Feature Discovery Protocol steps were run for the selected epic
- [ ] Every integration seam in the system-overview owned by this epic has a corresponding feature
- [ ] Every "Done" Jira story in the ledger for this epic maps to at least one feature
- [ ] Every configuration/feature-flag surface is represented as a feature or documented in a feature's evidence note
- [ ] Parity-critical features are explicitly flagged

### Evidence integrity
- [ ] Every feature's `What` section cites at least one EV-id per behavioral claim
- [ ] Every cited EV-id exists in the Evidence Ledger (no phantom citations)
- [ ] Every feature carries an explicit confidence level (High / Medium / Low)
- [ ] Every confirmed AC is marked `[x]`; partial ACs are `[ ]` with `[partial — EV-Jxx]`; intent-only ACs are `[ ]` with `[intent, not confirmed in code]`

### Anti-hallucination
- [ ] No invented API signatures, endpoint paths, table names, or config values
- [ ] No forward-state leakage without `[intent, not confirmed in code]` label
- [ ] No feature's behavior was filled from memory — every claim traces to a read or ledger entry in this session
- [ ] Partial features are correctly labeled `Partial` (not `Shipped`)

### Completeness
- [ ] Parent epic's Features table updated with stable IDs after each batch
- [ ] All discovered ADRs that constrain feature behavior are referenced in `Depends On`
- [ ] Known behavior debt is recorded in `Source Evidence & Confidence` for each feature
- [ ] Every source marked Gap in the Source Inventory appears as a confidence caveat in the affected features

### Output hygiene
- [ ] All feature files are under `assessments/<system>/features/`
- [ ] Feature index file lists all features and any unconfirmed candidates
- [ ] Descriptive slugs (`<epic-slug>-<behavior>`) are unique and stable — no positional numbers used as identity; each feature links its epic via `Part of epic: <epic-slug>`
- [ ] No `<!-- AGENT -->` or `<!-- REPLACE -->` text remains in any shipped file
- [ ] User explicitly approved each epic batch before files were written
- [ ] Next step (`parity-baseline`) communicated to user
