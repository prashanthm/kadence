You are doing a production-grade PR review. Review PR: <https://github.com/<owner>/<repo>/pull/<N>> in repo <owner>/<repo>.
Find ADRs/epics in the initiatives repo (`initiatives/<initiative>/`) or in GH issues <https://github.com/<owner>/<repo>/issues>.

Review objectives:
1. Perform a code-review-first assessment (findings first, severity ordered).
2. Cross-check alignment with:
   - linked issue(s) (story/bug/chore/docs/refactor),
   - epic requirements,
   - ADR references mentioned in PR/issue/body/comments.
3. Validate behavior, not just style:
   - regressions, edge cases, retry/error handling, logging, security implications.
4. Evaluate tests:
   - coverage of changed behavior,
   - missing negative-path and integration scenarios.
5. Check CI/readiness:
   - status checks, review requirements, merge blockers.

Output format (strict):
- Findings
  - Critical: ...
  - High: ...
  - Medium: ...
  - Low: ...
  For each finding include:
  - file and line reference (if available),
  - why it matters,
  - concrete fix.
- Cross-check Matrix
  - Requirement | Source (Issue/Epic/ADR) | PR Evidence | Status (Met/Partial/Missing)
- Open Questions / Assumptions
- Merge Recommendation
  - Approve / Request Changes / Comment-only
  - short rationale
- Optional follow-ups (non-blocking)

Review rules:
- If no defects are found, explicitly say “No blocking findings found.”
- Do not give generic praise without evidence.
- Distinguish blocking issues from nice-to-have improvements.
- If ADRs/issues are referenced but not present, flag as “traceability gap” and propose exact follow-up.
- Keep conclusions concise and actionable.

Review Loop Discipline (apply when iterating across multiple rounds, or when the review is being driven by an automated pre-check that scans the open PR set):

- **Refresh toolkit conventions before reviewing.** Before producing the review, ensure your local `product-workspace` checkout is on `main` and up to date (`git checkout main && git pull`). The `kadence/` directory is the source of the templates, prompts, ADR conventions, and the very `pr-review.prompt.md` you are following — reviewing against a stale toolkit produces stale feedback. If a PR you are reviewing modifies the toolkit itself, refresh after the PR's branch is checked out so you are reading the version under review.
- **Skip self-PRs.** A reviewer (human or automation) acting on behalf of the PR author should not post a review on that PR. Engage via comments or commits instead.
- **Skip adjacent-reviewer reviewed at HEAD.** If a reviewer outside the merge-authority team has already reviewed the current head commit, do not pile on with a second review on the same head. Their signal is informative; another review at the same commit is noise.
- **Gate re-review on explicit re-request.** After posting "Request Changes," do **not** re-review on every subsequent push. Wait for the author to click "Re-request review" (i.e., the reviewer is re-added to GitHub's `reviewRequests` array). This lets the author batch multiple commits to address the findings without each push triggering a new round, and it preserves the author's signal that they consider themselves done.
- **Defer to CI.** If CI is mid-run or has not yet executed on the head commit, wait. The exception: if absent CI runs are *themselves* the finding (e.g., the branch has no CI history at all), call that out as a High finding rather than reviewing substance against a green-unknown baseline.
- **Findings continuity across rounds.** Every Round-N+1 review begins with a disposition table for the prior round's findings — `Fixed` / `Not addressed` / `Acceptable, deferred` — citing the commit(s) and file:line evidence that closed each item, before raising new findings. This prevents finding-drift where the conversation churns.
- **Cite the head commit short SHA** in the review title or first line so reviewers and author can see at a glance which state was reviewed (rounds beyond Round 1 are easy to misattribute).
- **Supersession comments are first-class.** When a PR is closed in favor of a refile elsewhere, post a comment on the superseded PR that links to the successor, maps the original work to its new home, and explicitly suggests closure. Do not silently let it go stale.
- **Distinguish merge authority from informative reviews.** An approval from a reviewer adjacent to (but not on) the merge-authority team is signal, not sufficient. The merge decision rests with the team that owns the consequence; record this in the rationale rather than treating any approval as "ready to merge."

Optional Provenance Footer (for retrospective analysis, not promotion):

- A reviewer running with model/agent assistance MAY append a single-line metadata trailer to the review body in the form `_Review tooling: family=<vendor>, tier=<model-class>, mode=<assist|primary>_`. This is metadata to enable later analysis of which configurations correlate with rework, latency, or merge outcomes — not an endorsement or advertisement. Teams should agree on whether to enable this per repo. Omit entirely when in doubt.