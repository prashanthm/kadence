# PR Gate Checklist

> Must pass before a pull request can be merged.

## Quality

- [ ] Unit tests pass
- [ ] Coverage meets project threshold
- [ ] Code reviewed by a human (see [`review-tiers.md`](review-tiers.md) for *who* must review — peer vs operator)
- [ ] PR linked to task issue

## Security

- [ ] SAST scan passes
- [ ] No secrets in code (secrets scan clean)
- [ ] Dependency scan clean (no known CVEs)

## Compliance

- [ ] License check passes (no unapproved licenses)
- [ ] Commit is signed
- [ ] Change is traceable: PR → task issue → feature → epic

## Observability

- [ ] Logging/tracing instrumented for new code paths
