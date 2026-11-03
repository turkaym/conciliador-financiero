# MVP Feature Flags

## Objective

Control MVP module composition through a versioned, fail-closed feature manifest shared by backend capabilities, frontend routing/navigation, and scheduled work.

## Context

- Parent runtime recovery: `d59dc7b`.
- Branch: `feat/mvp-feature-flags`.
- The imported advanced application currently mounts all API routers and UI modules unconditionally.
- Reconciliation must remain implemented but disabled until enabled through a reviewed pull request.

## Authorized Feature State

| Feature | Default |
| --- | --- |
| B2B Directory | Enabled |
| Expenses and Payments | Enabled |
| Tax Registries | Enabled |
| Team | Enabled |
| Deterministic AI Rules | Enabled |
| Reconciliation | Disabled |
| AI Copilot | Disabled |
| B2B Integrations | Disabled |

Expenses and Payments includes local treasury, attachments/MinIO, multi-currency, and Interbanking capabilities.

## Requirements

- Feature state is versioned so changing Reconciliation requires a pull request.
- Invalid, unknown, or contradictory manifest values fail application startup.
- Backend does not mount disabled module routers.
- Scheduled tasks for disabled modules are not registered.
- Frontend does not mount or advertise disabled module routes.
- Direct navigation to a disabled module returns a deterministic unavailable/not-found experience.
- Tenant authorization remains separate: a globally enabled feature still requires the user's tenant entitlement and RBAC permission.
- The capabilities response exposes no secrets or internal credentials.
- Flags distinguish enabled state from actual implementation readiness; no unavailable feature may be represented as usable.

## Task

- [x] **FLAGS-01 — Establish end-to-end MVP feature composition**
  - Route: delegated direct.
  - Trigger evidence: coordinated backend, frontend, worker schedule, configuration, and tests across multiple non-trivial files.
  - Acceptance: authorized defaults are enforced across API, UI, and schedules; Reconciliation, AI Copilot, and B2B Integrations are unavailable by default; changing the versioned flag and rebuilding activates the intended composition; invalid configuration fails closed.
  - Checks: manifest validation tests, router/capability tests, schedule tests, frontend build and route/navigation checks, Compose startup, API capability response, disabled-route probes, `git diff --check`, and clean post-commit status.

## Delivery Strategy

- Stacked-to-main child of Docker runtime recovery.
- Keep the cross-layer flag transaction cohesive; target approximately 400 authored lines without suppressing tests or clarity.
- No push, pull request, or remote ruleset change without separate authorization.

## Current Next Step

Obtain a `size:exception` decision for the cohesive work unit, then create the pending Conventional Commit without amending or publishing it.

## FLAGS-01 Evidence

### Capability Semantics

- `config/feature_flags.json` is the only versioned enabled-state authority. Version 1 requires exactly the eight canonical boolean identifiers; malformed JSON, duplicate/missing/unknown keys, non-booleans, and unsupported versions abort import/startup.
- `/v1/capabilities` exposes only `identifier`, `enabled`, `implemented`, and `usable`; `usable` is always `enabled && implemented`.
- State is immutable in the backend process. Tenant entitlements and RBAC remain independent authorization layers.
- Deterministic AI Rules are enabled but `implemented: false` because no complete standalone management API/UI exists.

### Route Mapping

| Feature | API routes | Imported UI | Default result |
| --- | --- | --- | --- |
| B2B Directory | `/v1/entidades` | `/dashboard/directorio` | Mounted |
| Expenses and Payments | `/v1/bancos`, `/v1/pagos` | `/dashboard/bancos`, `/dashboard/egresos` | Mounted |
| Tax Registries | `/v1/afip-vault`, `/v1/fiscal`, `/v1/padrones` | `/dashboard/padrones` | Mounted subject to RBAC |
| Team | `/v1/equipo` | `/dashboard/equipo` | Mounted subject to RBAC |
| AI Rules | Matching/domain logic only | None | Not advertised; not usable |
| Reconciliation | `/v1/matching` | `/dashboard/conciliacion` | Unmounted; API 404 |
| AI Copilot | `/v1/ai` | None | Unmounted; API 404 |
| B2B Integrations | `/v1/b2b` | None | Unmounted; API 404 |

System health, authentication, tenant administration, billing, DLQ administration, comprobantes, accounting, and reports remain outside optional module composition.

### Schedule Mapping

- Reconciliation owns `run-auto-matching-every-15-mins`; absent by default. Matching and reconciliation accounting tasks reject normal direct invocation while disabled.
- B2B Integrations owns `run-outbox-sweeper-every-10-secs`; absent by default. Webhook dispatch rejects normal direct invocation while disabled.
- AI Copilot has no periodic schedule and its task module is not registered while disabled; the worker remains running.
- Enabled schedules are fiscal audit (Tax Registries), currency synchronization (Expenses and Payments), and the generic bank synchronization lock sweeper.

### RED, GREEN, Refactor

- RED: Python collection failed because `config.feature_flags` did not exist; the frontend proof failed because `featureFlags.ts` did not exist.
- Intermediate RED: direct matching invocation bypassed the default Celery base through `DLQTask`; the guard moved to registration-time wrapping so custom bases are covered.
- GREEN: six backend manifest/router/schedule/task tests pass in the API image; the dependency-free TypeScript route/navigation proof passes; `npm run build` passes.
- Refactor: removed the redundant default task base and removed the unimplemented AI Rules fallback advertisement.

### Runtime Proof (2026-11-03)

- `docker compose -p conciliador-financiero-dev config --quiet`: pass.
- Rebuilt and recreated only API, frontend, workers, Beat, and Flower. API/frontend are healthy; all four workers return `pong`; Beat is running.
- Capabilities returned eight safe records. Reconciliation, AI Copilot, and B2B Integration probes returned 404. Bancos, Pagos, Padrones, and Equipo returned 401, proving routes exist behind authentication.
- Beat schedule contains only `run-fiscal-auditor-daily`, `run-sincronizacion-moneda-diaria`, and `run-zombie-sweeper-every-hour`.
- Frontend `/` returned 200. Headless Edge loaded delivered assets/capabilities and rendered `Módulo no disponible` at `/dashboard/conciliacion`; disabled navigation identifiers are excluded by the automated capability proof.
- `.env` remains ignored and untracked. No secret values were added to source or capability output.

### Operations and Rollback

- Enable a ready feature by changing its boolean in `config/feature_flags.json`, reviewing that Git diff, and rebuilding/recreating API, frontend, workers, and Beat for `conciliador-financiero-dev`.
- Do not use `.env` or `VITE_*` for feature authority. A tenant entitlement or RBAC grant cannot override a globally unusable capability.
- Roll back by reverting the FLAGS-01 work unit and recreating the same affected services. No database migration, persisted tenant data, infrastructure volume, or secret rotation is involved.

### Remaining Gaps

- AI Rules still require a standalone management API and imported UI before implementation readiness can become true.
- AI Copilot and B2B Integrations have backend routes but no imported frontend modules; B2B outbox scheduling also depends on implementing the currently referenced sweeper task before enabling the feature.
