---
name: context-acquisition
description: Gather brownfield context from every available source (code, git, Jira, Confluence, Slack, web/URL crawling, and screenshot analysis) via MCP and record it as a Source Inventory plus an Evidence Ledger. Use first in any brownfield assessment, before extracting the AS-IS system.
---

# Context Acquisition Skill

## Purpose

Gather the raw evidence a brownfield assessment reasons over and make it traceable. Code shows *what is*; the *why* — intent, tradeoffs, abandoned paths, incident history — lives in Jira, Confluence, Slack, git history, published documentation sites, and captured screenshots. This skill pulls from every reachable source and records each item, with provenance, into a reusable Source Inventory and Evidence Ledger that every downstream reverse skill cites.

This skill gathers and provenances. It does not interpret the system — `current-state-assessment` and the extraction skills do that, using the ledger this skill produces.

## When to Use

- First step of any brownfield initiative, before AS-IS extraction
- Re-running an assessment to capture newly available sources or a later date range
- Establishing the evidence base a migration plan must trace back to

## Required Inputs

- Source Brief filled out by the user (see Source Brief below — collect this first, before any querying)
- MCP servers connected in the IDE: Atlassian MCP (Jira + Confluence), Slack MCP, Playwright MCP (optional — needed only for JS-rendered web pages)
- Screenshots dropped into `assessments/<system>/screenshots/` before the skill runs (optional — skip silently if absent)
- Templates: [`templates/source-inventory.md`](../../templates/source-inventory.md) and [`templates/evidence-ledger.md`](../../templates/evidence-ledger.md)

## Source Brief (collect before querying)

**Present this form to the user at the start of the skill and wait for answers before proceeding.** Do not probe sources speculatively — ask once, then pull everything in one pass.

```
System slug (used for assessments/<system>/):

Code repos (paths or org/repo, one per line):

Jira project keys (e.g. EDI, PLAT):

Confluence spaces (space keys or space names):

Slack channels (e.g. #edi-platform, #ops):

Git history date range (e.g. "last 24 months" or "2024-01-01 to today"):

Web / doc URLs to crawl (one per line; append ":2" for depth-2 crawl, default is 1):

Screenshots folder: assessments/<system>/screenshots/
(drop images here before running; leave blank / skip if none)

Topics / component names to search across all sources (e.g. "OSDU provisioning", "auth", "multi-tenant"):

Any known sources to skip (and why):
```

If the user provides a partial brief, **do not proceed to querying**. First complete the Gap Resolution Protocol (see below) for every unanswered field. Code and git are always accessible without the brief, but all other sources require explicit confirmation before querying or skipping.

Once the brief is complete and all gaps are resolved, run all source adapters in parallel against the declared scope. Do not ask the user to repeat information already in the brief.

## Gap Resolution Protocol

**Every gap blocks progress.** A gap is any source that is (a) undeclared in the brief, (b) unreachable when queried, or (c) accessible but returned no usable content. Gaps must be resolved before the skill moves on to the next source.

### When to invoke

1. **After the Source Brief** — identify every field the user left blank or ambiguous. Present all Brief gaps together in one round before querying anything.
2. **During execution** — when any source adapter fails to reach its target (MCP not connected, repo path wrong, project key returns 404, channel ID not found, URL unreachable), stop that adapter and invoke this protocol immediately before continuing other adapters.

### How to present a gap

Present each gap as a structured prompt:

```
GAP: <source-name>
Reason: <why it is missing — blank in brief / MCP not connected / 404 / etc.>
What I need: <the specific information required — URL, path, project key, channel ID, credentials, or explicit skip>

Options:
  A) Provide: <describe what value to supply>
  B) Skip this source — it will be marked as "Gap (user skipped)" in the Source Inventory and no evidence from it will be included
```

Use the `AskQuestion` tool when available (interactive IDE). In non-interactive environments, output the gap block as plaintext and wait for the user's next message before continuing.

### Gap resolution rules

- **One round per phase** — collect all Brief gaps in a single presentation before querying starts; collect all runtime gaps as they arise one at a time (since they are discovered sequentially during execution).
- **No silent skipping** — a source cannot be marked "Gap" in the inventory unless the user explicitly chose Option B or confirmed the source does not exist.
- **No partial proceeding** — do not start writing the Evidence Ledger or Source Inventory until all gaps from the current phase are resolved.
- **Explicit skip is final** — once the user says to skip a source, record it as `Gap (user skipped)` and do not re-prompt.
- **Provided info is retried immediately** — as soon as the user supplies a missing value (e.g., correct repo path, channel ID), retry the adapter before moving on.

## Source Adapters

Each source **must be resolved** — if it is not reachable, invoke the Gap Resolution Protocol (below) before continuing. The user decides whether to supply credentials/paths or explicitly skip. A skipped source is recorded as `Gap (user skipped)` in the Source Inventory.

| Source | What it yields | Access | Locator format | On failure |
|--------|----------------|--------|----------------|------------|
| Code / IaC / config | Ground truth of *what is* — entry points, data models, API contracts, config, pipelines | graphify (`graphify query "<topic>"`) + structured per-repo deep-dive (see Code Deep-Dive Protocol below) | `code:path#Lstart-Lend` | Gap Resolution Protocol |
| Git history / PRs | When and why things changed | shell `git log`, `gh pr list/view` | commit SHA / `org/repo#PR` | Gap Resolution Protocol |
| Jira | Original epics/stories, intent, acceptance criteria, backlog, status | Atlassian MCP | issue key (e.g. `EDI-1234`) | Gap Resolution Protocol |
| Confluence | Design docs, runbooks, ADR-likes, architecture pages | Atlassian MCP | page URL or page ID | Gap Resolution Protocol |
| Slack | Tribal decisions, rationale, incident threads | Slack MCP | message permalink | Gap Resolution Protocol |
| Web / URLs | Published docs, runbooks, architecture pages, API references | WebFetch (always); Playwright MCP (JS-rendered pages, if connected) | `url:https://...` | Gap Resolution Protocol if WebFetch fails and Playwright not connected |
| Screenshots | Architecture diagrams, dashboards, UI flows, exported PDF/Confluence pages | Vision read of files in `assessments/<system>/screenshots/` | `screenshot:assessments/<system>/screenshots/<filename>` | Silent skip if folder absent/empty (not a gap) |

## Code Deep-Dive Protocol

**Do not stop at README.md.** For every repo in scope, execute all steps below in order. Each step adds evidence rows — skip a step only if the artifact does not exist in that repo.

### Step 1 — Repo Map
Run `ls -R <repo>/` (or `find <repo> -maxdepth 3 -type f`) to build the full directory tree. Record the tree as one ledger entry. Identify which directories correspond to: source code, IaC, tests, CI/CD, docs, contracts/schemas, scripts.

### Step 2 — Dependency Manifest
Read every dependency/build file present: `pyproject.toml`, `go.mod`, `go.sum`, `package.json`, `requirements.txt`, `Pipfile`, `uv.lock`, `poetry.lock`, `Makefile`. Extract: language/runtime version, key libraries and their versions, build targets. Record each file as a ledger entry with the tech stack summary.

### Step 3 — Entry Points and Handlers
Locate and read the files that define what the service *does*:
- Python: `handlers.py`, `main.py`, `app.py`, `lambda_function.py`, files under `src/` with route or handler definitions
- Go: `main.go`, `cmd/`, `internal/controller/`, `pkg/`
- Node/TS: `index.ts`, `server.ts`, `routes/`
- Terraform: `main.tf`, `variables.tf`, `outputs.tf` in every module directory
Read each fully. Capture: what functions/handlers exist, what they accept and return, what external services they call (AWS SDK calls, HTTP clients, DB access). One ledger entry per file or handler group.

### Step 4 — Data Models and Schemas
Find and read all data model definitions:
- Database schemas, ORM models, Pydantic/dataclass models, Go structs tagged with json/db
- DynamoDB table definitions in Terraform (`aws_dynamodb_table` resources) — capture table name, partition key, sort key, GSIs, TTL
- OpenAPI / Swagger specs (`openapi.yaml`, `swagger.json`, `contracts/`)
- Protobuf / Avro / JSON Schema files
One ledger entry per model file or schema group. Summarise field names and types — do not dump entire files.

### Step 5 — API Contracts and Routes
Read all route/endpoint definitions. For REST APIs: path, HTTP method, auth requirement, request body shape, response shape. For event-driven: event source (EventBridge rule, SQS queue, SNS topic, Kafka topic), handler function, payload structure. Record as a ledger entry with a table of routes or events.

### Step 6 — IaC Deep-Read
For Terraform repos: read every `.tf` file in each deployment/module directory. Capture:
- Resource types created (`aws_lambda_function`, `aws_dynamodb_table`, `aws_ecs_service`, `helm_release`, etc.)
- Key variable values (`terraform.tfvars`, `variables.tf` defaults)
- Outputs (what gets exported for other modules to consume)
- Hard-coded account IDs, ARNs, region names — flag each as a portability risk
- Provider versions and Terraform version constraints
For Helm/Kubernetes: read `Chart.yaml`, `values.yaml`, CRD manifests. Capture chart dependencies, image refs, replica counts, resource limits. One ledger entry per module or chart.

### Step 7 — CI/CD and Build Pipelines
Read every pipeline definition: `bitbucket-pipelines.yml`, `.github/workflows/*.yml`, `Jenkinsfile`, `Makefile` targets, `deploy.sh`, `destroy.sh`, `buildscripts/`. Capture: trigger conditions, build stages, test steps, deploy targets, quality gate steps (SonarQube, Black Duck), secrets/variables referenced by name (not value). One ledger entry per pipeline file.

### Step 8 — Configuration and Environment
Read all config files: `.env.example`, `config.env`, `variables.env`, `sonar-project.properties`, `pyproject.toml` tool sections, `settings.py` / `config.go`. Capture: required environment variables, feature flags, external service endpoints, auth config patterns. Flag any hard-coded credentials or non-parametrised values. One ledger entry per config group.

### Step 9 — Tests
Read the test directory structure: `tests/`, `__tests__/`, `*_test.go`. Capture: what components have tests, test types (unit / integration / e2e / load), coverage target if stated, any fixtures or mocks that reveal data shapes. Do not read individual test bodies unless they reveal undocumented behaviour. One ledger entry per test module or test type.

### Step 10 — Changelog and Version History
Read `CHANGELOG.md`, `VERSION`, `RELEASE_NOTES.md` if present. Capture: current version, release cadence, significant recent changes. One ledger entry.

### Step 11 — Inline Documentation and ADR-like Comments
Grep for inline architectural decisions: comments containing `TODO`, `FIXME`, `HACK`, `NOTE`, `ADR`, `decision`, `rationale`, `workaround`. Read the surrounding 10 lines for each hit. One ledger entry per cluster of related inline notes.

```bash
grep -rn "TODO\|FIXME\|HACK\|NOTE\|ADR\|decision\|rationale\|workaround" \
  <repo>/src/ <repo>/internal/ <repo>/cmd/ \
  --include="*.py" --include="*.go" --include="*.ts" --include="*.tf" \
  -l   # list files first, then read the top hits
```

## Required Workflow

1. **Present the Source Brief form** (above) and wait for the user to fill it.
2. **Resolve all Brief gaps** — for every field left blank or ambiguous, invoke the Gap Resolution Protocol. Present all Brief gaps together in one round using `AskQuestion`. Do not begin querying until every gap is either filled or explicitly skipped by the user.
3. Read both templates and treat every `<!-- AGENT: ... -->` block as authoring rules — not text to copy.
4. Create `assessments/<system>/` and `assessments/<system>/screenshots/` if they do not exist.
5. Using the declared scope from the resolved Source Brief, pull from every source. Run external sources (Jira, Confluence, Slack) in parallel with the code deep-dive. Do not wait for one to finish before starting another:
   - **Code / IaC**: for each repo, execute all 11 steps of the Code Deep-Dive Protocol above. Do not stop at README. If graphify is available (`graphify-out/graph.json` exists), run `graphify query "<topic>"` first to orient, then use the deep-dive protocol to fill the gaps graphify does not surface (data models, IaC resource details, pipeline configs). **If a repo path does not exist or is not accessible → invoke Gap Resolution Protocol immediately.**
   - **Git**: `git log --since="<date-range>" --all --oneline` for each repo. Then read the 5 most recent merge commits in full (`git show <sha>`) to surface rationale. Also run `git log --all --oneline -- <path>` for key files identified in the deep-dive to see their change history. **If a repo is not a git repository → invoke Gap Resolution Protocol.**
   - **Jira**: query each declared project key via Atlassian MCP, retrieving all issues with `summary`, `description`, `status`, `issuetype`, `assignee`, `labels`, `components`. Read the description field of every Epic and Task — not just summary lines. **If the MCP is not connected, returns 401, or the project key does not exist → invoke Gap Resolution Protocol.**
   - **Confluence**: search each declared space via Atlassian MCP for the declared topics. For pages returned, fetch full page body with `getConfluencePage` for the top 5 most relevant results. **If the MCP is not connected or the space returns 0 results → invoke Gap Resolution Protocol.**
   - **Slack**: read the full declared channel history (up to 100 messages) with `slack_read_channel`, then run targeted searches per topic with `slack_search_public_and_private`. Follow up on threads for any message where a decision or architectural choice is made (`slack_read_thread`). **If the MCP is not connected or the channel ID is invalid → invoke Gap Resolution Protocol.**
   - **Web / URLs**: for each declared URL, fetch with WebFetch; extract main content and collect linked page URLs from the same domain up to the declared depth (default 1 level). If a page returns blank or JS-rendered content, retry via Playwright MCP if it is connected; if not connected, mark that URL as WebFetch-only in the inventory and continue. **If WebFetch returns a non-200 or empty body and Playwright is not connected → invoke Gap Resolution Protocol.**
   - **Screenshots**: if `assessments/<system>/screenshots/` contains image files, read each with the vision tool; describe what is visible (topology, services, flows, labels, error messages, data values); record one ledger entry per file. If the folder is absent or empty, skip silently — this is not a gap.
   - For any source the user explicitly said to skip in the brief, record it as `Gap (user skipped)` in the Source Inventory and do not re-prompt.
6. Record every pulled item as a row in `evidence-ledger.md`: `id | source-type | locator | summary | relevance | retrieved-at`. Assign a stable `id` (e.g. `EV-001`) — downstream skills cite these ids.
7. Note any contradictions between sources directly in the ledger. Do not resolve them.
8. Summarize, do not dump: one-line summary and locator per item, not full bodies (Slack/Confluence/web pages may contain sensitive data). Exception: data model field lists and API route tables are worth including in full — they are the raw material for feature extraction.
9. Present both files for review before writing them.

## Provenance and Confidence Rules

These rules originate here and are inherited by every reverse skill that cites the ledger:

- **Provenance** — every downstream artifact must cite concrete evidence ids and locators (`code:path#L`, `JIRA-1234`, Confluence URL, Slack permalink, commit SHA, `url:https://...`, `screenshot:...`).
- **Confidence by corroboration** — `High` = in code + ticket/doc; `Medium` = code only, or screenshot corroborated by another source; `Low` = doc/web/Slack/screenshot only and NOT found in code (a claim to verify, not a fact).
- **Precedence / conflict rule** — code wins for "what exists"; Jira/Confluence/Slack/web/screenshots supply rationale and may be stale. Log contradictions in the ledger; never silently resolve them.

## Rules

- MCP-first: name the MCP server used for each external source. If a server is not connected, invoke the Gap Resolution Protocol — do not silently skip or continue without user confirmation.
- **Gaps block — they do not degrade.** No source may be silently dropped. Every gap requires an explicit user decision (fill or skip) before the skill proceeds past that source.
- Scope discipline: pull only in-scope projects/spaces/channels/repos. Web crawl is scoped to the declared seed URL domains — do not follow links to other domains.
- Screenshots are read at assessment time only; do not modify or delete them.
- Sensitivity: keep summaries, not bulk exports; flag any source likely to contain secrets or PII.
- Stable ids: ledger ids never change once assigned — extraction artifacts depend on them.
- No placeholder template text in the shipped files.

## Reference Examples

- [`samples/assessments/edi-express/source-inventory.md`](../../samples/assessments/edi-express/source-inventory.md)
- [`samples/assessments/edi-express/evidence-ledger.md`](../../samples/assessments/edi-express/evidence-ledger.md)

## Verification

- [ ] All Source Brief gaps were presented to the user and resolved (filled or explicitly skipped) before querying began
- [ ] All runtime gaps (unreachable sources discovered during execution) were presented to the user and resolved before continuing
- [ ] No source is listed as a gap in the Source Inventory unless the user explicitly chose to skip it or confirmed it does not exist
- [ ] `assessments/<system>/source-inventory.md` written with every source marked `Reachable`, `Gap (user skipped)`, or `Gap (does not exist)` — not just "gap" without cause
- [ ] `assessments/<system>/evidence-ledger.md` written with stable ids, locators, and summaries
- [ ] **Code deep-dive completed for every in-scope repo** — all 11 steps executed; README was not the only file read
- [ ] Repo directory tree captured (Step 1) for each repo
- [ ] Dependency manifests read; tech stack + library versions recorded (Step 2)
- [ ] Entry points / handlers read in full; external service calls captured (Step 3)
- [ ] Data models, DynamoDB table schemas, OpenAPI/contract files read and field lists recorded (Step 4)
- [ ] API routes or event sources enumerated as a table in the ledger (Step 5)
- [ ] IaC files read; resource types, hard-coded values, and portability risks flagged (Step 6)
- [ ] CI/CD pipeline files read; stages, quality gates, and secrets references captured (Step 7)
- [ ] Config / env files read; required env vars and external service endpoints captured (Step 8)
- [ ] Test structure and coverage targets noted (Step 9)
- [ ] CHANGELOG / VERSION read if present (Step 10)
- [ ] `TODO`/`FIXME`/`HACK`/`ADR` grep run; inline architectural notes captured (Step 11)
- [ ] Git merge commits read (not just `--oneline`); rationale captured
- [ ] Jira issue descriptions read in full for all Epics and Tasks (not just summary lines)
- [ ] Confluence top results fetched with full body via `getConfluencePage`
- [ ] Slack channel read (up to 100 messages) + thread follow-ups on decision messages
- [ ] MCP server named for each external source; gaps recorded for unreachable ones
- [ ] Web URLs fetched; Playwright MCP fallback noted in inventory if WebFetch-only
- [ ] Screenshots read and described if folder had images; silently skipped if absent/empty
- [ ] Contradictions between sources logged, not resolved
- [ ] No `<!-- AGENT -->` or `<!-- REPLACE -->` text remains
