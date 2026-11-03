# Repository Governance And CI

## Objective

Establish reproducible pull-request checks and mutual Hugo/Farid review ownership before any change can reach `main`.

## Context

- Parent dependency remediation: `c6ab972`.
- Branch: `chore/repository-governance`.
- Canonical repository: `turkaym/conciliador-financiero`.
- Contributors: `@turkaym` and `@HugoTcach`.
- GitHub prevents pull-request authors from approving their own pull requests, but repository files alone cannot enforce required approvals; remote branch protection or a ruleset is also required.

## Tasks

- [x] **GOV-01 — Add CODEOWNERS and reproducible PR checks**
  - Route: delegated direct.
  - Acceptance: all repository paths request both contributors; PR checks prove frontend clean install/build/contracts/audit threshold, focused backend tests, Python compilation, and Compose configuration without committing secrets; workflow permissions are minimal and third-party actions are pinned to supported versions.
  - Checks: local parity commands, workflow syntax, secret exposure review, changed-path behavior, and rollback proof.

- [ ] **GOV-02 — Enable protected-main approval policy**
  - Route: remote configuration after explicit authorization.
  - Acceptance: `main` requires a pull request, one approving review from someone other than the author, stale approvals are dismissed after new commits, the latest reviewable push requires approval, conversations are resolved, required checks pass, force-push/deletion are blocked, and no actor receives an undocumented bypass.
  - Checks: read back effective repository rule and validate with a non-destructive pull-request workflow.

## Delivery Strategy

- GOV-01 is a local, versioned work unit and does not mutate GitHub settings.
- GOV-02 requires separate authorization for destination, operation, and authenticated session.
- No push or pull request without separate authorization.

## Current Next Step

Complete local parity and validation for GOV-01, then configure GOV-02 only after explicit remote authorization.

## GOV-01 Implementation

- `.github/CODEOWNERS` assigns every path to `@turkaym` and `@HugoTcach`. Either owner can satisfy a required Code Owner review, while GitHub prevents author self-approval.
- `Quality gates` runs for pull requests and pushes to `main` with only `contents: read`, per-ref concurrency cancellation, 15-minute job limits and no artifacts or secrets.
- `Frontend quality` performs a lockfile clean install, two dependency-free contracts, production build, and an audit threshold that fails only for high/critical findings.
- `Backend and governance` rejects newly tracked sensitive/runtime/generated paths, installs an explicit focused import closure without AI model packages, runs feature composition and AI Rules tests, compiles/imports Python boundaries, and validates Compose.
- Compose validation copies `.env.example` to a temporary `.env`, appends only CI placeholders, never prints it, and restores any prior local `.env` through an exit trap.
- General lint remains outside required checks because its known debt is non-green.

## Required GOV-02 Settings

Protect `main` with pull request required, one approval, stale approval dismissal, approval of the latest reviewable push, Code Owner review, resolved conversations, and required checks `Frontend quality` plus `Backend and governance`. Block force-push and deletion; grant no undocumented bypass. Confirm private-repository plan support and read back the effective rule before non-destructive PR validation.

## Boundary And Rollback

GOV-02 remains unchecked and owns all GitHub ruleset/branch-protection mutation and effective-rule validation. GOV-01 performs no push, PR, settings, remote or Git identity operation. Roll back GOV-01 by reverting its single work-unit commit; no secret, persisted data, running container, volume or remote rule is affected.

## GOV-01 Verification Evidence

- `npm ci` added 428 packages and audited 429; both dependency-free contracts passed; the production build transformed 2,030 modules.
- `npm audit --audit-level=high` passed with 0 high/critical while reporting 2 low and 14 moderate findings.
- The focused Python environment installed from `requirements-ci.txt`; `pip check` found no broken requirements. All 14 backend tests passed in 2.759s; compilation and import smoke passed.
- Compose config passed with no output. The generated temporary `.env` was removed, the prior local file was restored byte-for-byte, and no backup remained.
- Workflow YAML structure, event filters, check names, `contents: read`, concurrency cancellation, and action inventory (`actions/checkout@v4`, `actions/setup-node@v4`, `actions/setup-python@v5`) passed local validation.
- CODEOWNERS is exactly `* @turkaym @HugoTcach`. The sensitive-path guard passed against the staged tree and allows a benign documentation CSV while rejecting sensitive examples.
- Existing Compose services remained running: API and frontend were healthy and returned HTTP 200; the disabled Reconciliation probe returned 404. No container was stopped or recreated.
- Staged `git diff --check` passed. The cohesive work unit is below the 400-line review budget; final commit identity and clean-status evidence follow in the commit record.
