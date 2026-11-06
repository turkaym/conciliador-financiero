# Operational README

## Objective

Restore the root README as a trustworthy operator and contributor entry point for the current advanced MVP.

## Context

- Parent governance record: `e423620`.
- Branch: `docs/operational-readme`.
- The advanced snapshot removed the prior root README.
- The current application runs through Docker Compose with feature-gated backend, frontend, navigation, workers and scheduled tasks.
- Local secrets belong only in ignored `.env` files; no real credential or financial/tenant dataset may enter documentation.

## Tasks

- [x] **DOC-01 — Restore the operational README**
  - Route: delegated direct because accurate instructions require mapping Compose, environment, feature flags, tests and governance files before writing.
  - Acceptance: a new contributor can understand product scope, active/disabled modules, architecture, prerequisites, secure local setup, startup/stop commands, URLs, health checks, feature-flag changes, quality gates, test commands, data/secret boundaries, troubleshooting and contribution policy without relying on undocumented knowledge.
  - Checks: execute safe quick-start/parity commands where practical; verify every referenced path, service, port and command; scan for secrets; verify links and Markdown structure.

## Constraints

- Use neutral professional Spanish because the product and primary documentation are Spanish-language.
- Never publish a real password, token, key, tenant financial datum, generated `.env`, or misleading default credential.
- Clearly distinguish repository defaults from current machine-specific port overrides.
- Do not claim hosted deployment, passing general lint, enabled Reconciliation, remote branch protection or GitHub Actions execution until proven.
- Link detailed governance rather than duplicating unstable policy.

## Current Next Step

Submit the documentation work unit for review when remote operations are separately authorized. Reconciliation remains disabled until a reviewed feature-manifest change authorizes it.

## DOC-01 Evidence

### Repository Mapping

- `config/feature_flags.json` enables B2B Directory, Expenses and Payments, Tax Registries, Team and deterministic AI Rules; Reconciliation, AI Copilot and B2B Integrations are disabled.
- `config/feature_flags.py` requires exactly eight boolean identifiers at manifest version 1 and derives `usable` as `enabled && implemented`; malformed or contradictory input aborts import/startup.
- `services/api-gateway/main.py`, `frontend/app/src/App.tsx` and `core/tasks/celery_config.py` gate API routers, UI routes/navigation, task registration and Beat schedules. Tenant entitlement and RBAC remain separate layers.
- `docker-compose.yml` automatically runs `alembic -n master upgrade head && python init_db.py` in the one-shot `migrate` service before API/workers start. `init_db.py` idempotently provisions the local tenant and operator-selected admin credentials from ignored environment values.
- Dockerfiles and CI evidence Python 3.11, Node.js 24 and Nginx 1.27; Compose pins PostgreSQL 16, Redis 7, RabbitMQ 3 and the MinIO image.
- `.gitignore`, `.env.example`, `.github/workflows/quality-gates.yml`, `.github/CODEOWNERS` and `docs/github-governance.md` support the documented security, quality and governance boundaries.

### Documentation Outcome

- Restored `README.md` in neutral professional Spanish as the concise operator/contributor entry point for the advanced MVP.
- Documented purpose, active/disabled module semantics, fail-closed behavior, service responsibilities, evidenced prerequisites, secure secret generation, automatic migrations/bootstrap, default ports and local overrides.
- Added health/capability checks, project-scoped logs/restart/down guidance that preserves named volumes, verified authentication onboarding, cross-layer feature workflow, CI-parity commands and troubleshooting for Windows, Git Bash and PowerShell.
- Recorded tenant/financial data boundaries, secret rotation, CODEOWNERS/governance status, npm advisory threshold, known lint debt, absent public deployment and pending remote rules.

### Verification (2026-11-04)

- Branch/parent: `docs/operational-readme` at `e423620`; the only initial change was this untracked ODD task.
- `docker compose -p conciliador-financiero-dev config --quiet`: pass against the current ignored environment.
- `C:\Program Files\Git\bin\bash.exe scripts/ci/check_compose_config.sh`: pass; the script restored the local `.env` through its cleanup trap.
- Compose service/image and source mapping: all documented services, nine ordinary published ports and corresponding environment variables matched `docker-compose.yml` and `.env.example`.
- Runtime: `api-gateway`, `frontend`, PostgreSQL, PgBouncer, Redis, RabbitMQ and MinIO healthy; frontend returned HTTP 200 and API `/health` returned `status=online`.
- Live capability parity: eight records matched the manifest; all five enabled modules were usable and the three disabled modules were not usable. `/v1/matching`, `/v1/ai` and `/v1/b2b` returned HTTP 404.
- Frontend: `npm ci` audited 429 packages; both dependency-free contract proofs and `npm run build` passed.
- Dependency audit: `npm audit --audit-level=high` passed with no high/critical findings and reported 16 remaining advisories (2 low, 14 moderate).
- Backend: focused unittest suite passed 14/14 after installing `services/api-gateway/requirements-ci.txt`; compileall and the feature/router import smoke passed.
- Known caveat confirmation: `npm run lint` failed with 156 findings (142 errors, 14 warnings); lint remains outside the required gate and is not represented as green.
- Markdown validation: all repository links exist; one H1, valid heading progression and 26 balanced fence markers were verified without adding a dependency.
- Sensitive review: README pattern scan found no private-key headers, certificate blocks, cloud/GitHub/OpenAI token shapes or real generated values. Only explicit placeholders and generation logic are present.
- `git diff --check`: pass before staging.

### Unexecuted Boundary And Limitations

- A destructive clean-volume or separate fresh-clone startup was not run because it would recreate or compete with the healthy persistent stack. Configuration, automated bootstrap wiring and all non-destructive commands were validated instead; the README states this boundary.
- Hosted GitHub Actions, public deployment, remote rulesets and branch protection were not executed or configured.
- General frontend lint debt and 16 low/moderate npm advisories remain outside DOC-01.
- The first local backend attempt lacked CI dependencies (`python-jose` and `redis`); after the documented requirements installation, the complete focused suite passed.

### Rollback

Revert the single DOC-01 work-unit commit to remove only `README.md` and this task record. Rollback does not modify application/config behavior, secrets, tenant data, Docker volumes, Git remotes, hosted CI or GitHub settings.

### Commit Record

- Parent: `e423620`.
- Subject: `docs: restore operational project guide`.
- Scope: only `README.md` and `odd/tasks/operational-readme.md`.
- The exact object ID is the commit containing this record and is reported in the delivery result; a commit cannot embed its own hash without changing that hash.
