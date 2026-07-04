<!--
AGENT: Evidence Ledger — one row per item pulled from any source during a brownfield assessment. Produced by the context-acquisition skill; lives at assessments/<system>/evidence-ledger.md.

Every downstream reverse artifact (system-overview, extracted epics/features, discovered ADRs) cites these ids. Assign stable ids (EV-001, EV-002, ...) — they never change once issued.

Locator by source-type: code -> code:path#Lstart-Lend; git -> commit SHA or org/repo#PR; jira -> issue key; confluence -> page URL/ID; slack -> message permalink; web -> url:https://...; screenshot -> screenshot:assessments/<system>/screenshots/<filename>.

Summarize, do not dump — one line per item, no full bodies (Slack/Confluence may hold sensitive data).

Strip this entire HTML comment when writing to assessments/ or anywhere outside templates/ — scaffolding only.
-->

# Evidence Ledger: <!-- REPLACE: System Name -->

> Traceable record of evidence gathered for the AS-IS assessment. Downstream artifacts cite the `ID` column.

| ID | Source type | Locator | Summary | Relevance | Retrieved |
|----|-------------|---------|---------|-----------|-----------|
| <!-- REPLACE: EV-001 --> | <!-- REPLACE: code/git/jira/confluence/slack --> | <!-- REPLACE: locator --> | <!-- REPLACE: one-line summary --> | <!-- REPLACE: what it evidences --> | <!-- REPLACE: date --> |
| <!-- REPLACE: EV-002 --> | <!-- REPLACE --> | <!-- REPLACE --> | <!-- REPLACE --> | <!-- REPLACE --> | <!-- REPLACE --> |

## Contradictions

<!-- REPLACE: Log any conflicts between sources here (e.g. EV-004 Confluence page says X but EV-002 code shows Y). Do not resolve them — flag for the assessment. If none, state "None observed". -->
