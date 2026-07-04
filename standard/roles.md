# Roles & Accountability

The AI-SDLC defines accountability boundaries, not job titles. These boundaries hold whether the team is one person or twenty.

## Accountability Framework

| Accountability | Owns | Decides |
|---------------|------|---------|
| **Product Owner** | Product brief, Epic Index (release order), epic definition, release approval | What to build, why, and when |
| **Builder** | ADRs, architecture, features, tasks, specs, code, CI/CD, deployment | How to build, what's technically sound, when it's ready to ship |
| **Agent** | Drafts, expands detail, implements, syncs to GitHub | Nothing — always supervised by a human |

## Feature Identification Is Shared

Identifying features is not solely a Product Owner responsibility. Builders see technical opportunities and constraints that the Product Owner may not:

- A **Builder** discovers that a data validation layer could be reused across three workflows — they propose it as a feature
- A **Builder** identifies a performance bottleneck that requires a dedicated caching feature — they propose it
- A **Product Owner** identifies a user-facing capability gap — they propose it
- Either can propose ADRs that create or constrain features

**The rule:** anyone can propose a feature or epic. The Product Owner decides whether it enters the Epic Index and which phase/milestone it belongs to. The Builder decides how it's built and whether the implementation is sound.

## Gate Ownership

| Gate / transition | Who | Mechanical or gate |
|-------------------|-----|--------------------|
| Feature → `Ready for Dev` | Product Owner / Builder | **the one human gate** (before the loop builds) |
| PR opened → `In review` | — | mechanical (`project-status-on-pr.yml`) |
| PR merged → `Done` | Builder (reviewer merges) | mechanical, via `Closes #` |
| Release → Ship | Product Owner + Builder | human |

> v2 has a single build gate (`Ready for Dev`). The old per-task `Ready for Spec` / `Approved`
> gates are gone — the Feature is the build unit and its spec is authored by the loop into the
> code repo, reviewed as part of the PR.

## Accountability Rules

- Every stage has exactly one human owner — the agent is never the owner
- The agent drafts; the human approves, rejects, or redirects
- Gate transitions (status changes on GitHub Issues) can only be made by humans
- Anyone can propose work; the accountable owner decides whether it advances
