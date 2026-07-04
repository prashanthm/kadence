# Foundation Readiness Checklist

> Must pass before the first line of product code is written.

## Tier 1 ADRs

- [ ] Repo structure — mono vs split, folder layout
- [ ] Branching strategy — trunk-based vs feature branches, PR rules
- [ ] Auth strategy — identity, access control, token handling
- [ ] API design standard — REST vs GraphQL, versioning, error format
- [ ] Data storage — database(s), what goes where
- [ ] Deployment model — cloud, containers, infra-as-code

## Architecture

- [ ] System context documented (`docs/architecture/`)
- [ ] Container/component diagram documented
- [ ] Architecture reviewed by team

## Dev Environment

- [ ] Repo created with folder structure from SETUP.md
- [ ] Branch protection rules enforced on main
- [ ] CI/CD pipeline runs green (pr-gate workflow)
- [ ] Agent rules installed for team's IDE

## Compliance

- [ ] License policy ADR accepted
- [ ] Signed commits enforced
- [ ] Dependency scanning enabled in CI
