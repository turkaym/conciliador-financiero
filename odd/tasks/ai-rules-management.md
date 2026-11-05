# Deterministic AI Rules Management

## Objective

Provide tenant-scoped administration for deterministic learned matching rules without requiring external AI models or enabling Reconciliation.

## Context

- Parent feature composition: `efc1c96`.
- Current branch: `feat/ai-rules-api`.
- `ai_rules` is enabled in the MVP manifest but remains `implemented: false` and therefore unusable.
- Existing matching code persists and consumes deterministic learned rules, but no complete management API or UI exists.

## Product Boundaries

- “AI Rules” means deterministic learned-rule records used to assist matching; it does not include chat, LLM calls, embeddings, or the AI Copilot.
- Reconciliation remains disabled globally. Rules may be administered while disabled, but automatic application remains unavailable until Reconciliation is enabled.
- Every operation is tenant-scoped, authenticated, authorized, validated, and auditable.
- API and UI must never permit cross-tenant identifiers or raw schema selection from client input.

## Tasks

- [x] **AI-RULES-01 — Add deterministic rules management API**
  - Route: delegated direct.
  - Acceptance: authorized users can list, inspect, create, update activation state, and delete eligible rules in their own tenant; invalid/cross-tenant/conflicting operations fail deterministically; existing matching consumers remain compatible; `ai_rules` remains `implemented: false` until UI completion.
  - Checks: model/schema mapping, service tests, route/auth/RBAC tests, running-tenant API smoke, existing feature-composition tests, migration state, and rollback proof.

- [x] **AI-RULES-02 — Add rules management UI and activate readiness**
  - Route: delegated direct.
  - Acceptance: enabled and entitled users can administer deterministic rules through the frontend; disabled/unimplemented states remain fail-closed; only after API/UI proof does capability readiness become true.
  - Checks: frontend contract tests, route/navigation proof, production build, API integration smoke, and feature capability response.

## Delivery Strategy

- Stacked-to-main child of MVP feature flags.
- API and UI are separate green work units. The global capability remains unusable between them.
- Target approximately 400 authored changed lines per work unit; tests and audit behavior stay with implementation.
- No push, pull request, or remote configuration without separate authorization.

## Current Next Step

AI-RULES-02 is complete. Keep Reconciliation, AI Copilot, and B2B Integrations disabled unless separately authorized and proven.

## AI-RULES-02 Evidence

### Composition And Entitlement

- `/v1/ai-rules` is mounted only when the versioned manifest enables `ai_rules` and implementation readiness is true. The final capability is enabled true, implemented true, usable true.
- The router independently requires tenant feature `ai_rules` plus global role `admin` or `dueño`; tenant/schema authority is never accepted in request payloads. Unauthenticated access reaches the mounted auth boundary with HTTP 401.
- `init_db.py` idempotently adds only `ai_rules` to the existing demo tenant feature map for fresh and existing local bootstrap runs. It does not grant Reconciliation, AI Copilot, or B2B Integrations.

### UI Contract

- `/dashboard/reglas-ia` has deterministic unavailable and unauthorized direct-route states and appears in navigation only for a globally usable, entitled `admin`/`dueño` session.
- The Spanish page exposes loading, empty, validation, conflict, and retryable failure states; filters normalized concept/CUIT data; creates only `concepto_cuit`; and uses `expected_updated_at` for state changes.
- A 409 refreshes the affected server record while preserving the create form. “Desactivar con auditoría” communicates the API's audited soft-deactivation behavior; no tenant/schema selector or external AI request exists.

### RED, GREEN, And Runtime Proof

- RED: backend readiness failed because `IMPLEMENTATION_READINESS["ai_rules"]` was false; the dependency-free frontend contract failed because its access/conflict model did not exist.
- GREEN: 14 focused backend tests passed in the API image, including enabled/ready composition, 401/403, entitlement denial, CRUD, optimistic conflict, and Reconciliation fail-closed behavior. Both Node contract proofs and `npm run build` passed.
- `docker compose -p conciliador-financiero-dev config --quiet` passed. The migration/bootstrap job completed idempotently; only API and frontend were rebuilt/recreated. Existing workers remained running and untouched.
- Runtime `/v1/capabilities` reported `ai_rules` true/true/true; unauthenticated `/v1/ai-rules` returned 401; authenticated demo list/create/toggle/deactivate passed without printing tokens; frontend and direct route returned 200; Reconciliation remained HTTP 404.
- No external AI endpoint is referenced by the client. `.env` remains ignored and unstaged.

### Remaining Risks And Rollback

- Concurrent duplicate creation still lacks a database unique constraint, inherited from AI-RULES-01. Browser-level visual automation is not installed; route/navigation/access/conflict behavior is covered by dependency-free contract proof and the production build.
- Rollback sets `ai_rules` readiness false, removes the conditional gateway mount, frontend route/navigation/page/client, router entitlement dependency, and bootstrap grant. Existing rules and audit rows remain intact; Reconciliation stays disabled.

### AI-RULES-02 Commit And Review Assessment

- Work-unit commit: `4ab218c` (`feat(ai-rules): add deterministic rules management UI`).
- Authored size: 296 lines across 14 authorized paths.
- Parent verification reran the production build, confirmed `ai_rules` is true/true/true, observed the mounted API auth boundary at HTTP 401, and confirmed Reconciliation remains HTTP 404.
- Native risk assessment: `medium` because executable feature-composition behavior changed.
- Review outcome: `under_budget`; no candidate review was due for the 296-line range.

## AI-RULES-01 Evidence

### Model Semantics

- `ReglaAprendizaje` remains mapped to `reglas_aprendizaje` with `entidad_id`, normalized concept pattern, optional CUIT and AFIP voucher type, usage frequency, activation state, and auditable timestamps. No database column or migration changed.
- Matching reads remain compatible: active rules are still filtered by entity and grouped by associated CUIT. The learned-rule writer now uses the mapped `entidad_id` attribute instead of the invalid `entity_id` keyword.
- Manual records start with `frecuencia_uso = 0`; matching may increment usage normally. Immutable provenance is the signed `REGLA_MANUAL_CREADA` audit action, and clients cannot set provenance or frequency.
- The current model has no confidence or range fields. Strict request schemas reject those unsupported fields rather than pretending to persist semantics the matching engine does not consume.
- Hard delete is not exposed because learned/audit history must remain traceable. `DELETE` performs audited deactivation.

### Endpoint And Authorization Contract

- Future mount prefix: `/v1/ai-rules`; this work unit intentionally does not mount it in the gateway.
- `GET /ai-rules` supports `limit` 1-100, non-negative `offset`, `activa`, and bounded `buscar`; `GET /ai-rules/{rule_id}` retrieves one tenant/entity-scoped record.
- `POST /ai-rules` creates only `concepto_cuit` manual rules. Patterns and CUITs are normalized; voucher types are bounded to 1-999; unknown or provenance fields are rejected.
- `PATCH /ai-rules/{rule_id}` changes only activation state and requires `expected_updated_at`; `DELETE` requires the same optimistic token and deactivates.
- Existing global roles `admin` and `dueño` are the narrow management permission. Tenant sessions come only from authenticated `get_tenant_db_session`; no schema or tenant identifier exists in paths or accepted payloads.
- Stable responses are `400 Datos de regla inválidos.`, `404 Regla no encontrada.`, and `409 La regla fue modificada por otra operación.` Database/schema/tenant details are never returned.
- Create, update, and deactivate add a signed tenant `LogAuditoria` row before the shared commit. Audit/database failure rolls back the rule mutation and returns a sanitized error.

### TDD And Verification

- RED: `python -m unittest tests.test_ai_rules` failed with `ModuleNotFoundError: core.api.v1.endpoints.ai_rules` before implementation.
- GREEN: focused isolated FastAPI/SQLite suite ran 6 tests in 0.422s, `OK`; it covers mapping/writer compatibility, CRUD/deactivation, filters, invalid type/payload, 404/409, dependency-built tenant isolation, 401/403, audit rollback, and sanitized envelopes.
- Existing feature flag/composition suites ran 6 tests in 2.990s, `OK`; only pre-existing Pydantic deprecation warnings were emitted.
- `compileall` succeeded for the four touched Python modules; import smoke reported `5 AiRulesService`.
- Existing API `/health` and frontend `/` returned HTTP 200. `/v1/capabilities` reported `ai_rules` enabled true, implemented false, usable false. Reconciliation status remained HTTP 404.
- `.env` remains ignored by `.gitignore:2`; no secret values were read or emitted. `git diff --check` passed.
- No Docker image was rebuilt and no service was recreated because no production-composed runtime file changed; all project services remained running and API/frontend health stayed healthy.

### Boundary And Rollback

- AI-RULES-02 still owns frontend management, gateway router mounting, and the atomic `ai_rules` implementation-readiness flip.
- Rollback removes the new router, schema, service, and focused test, reverts the learned-writer keyword correction, and restores this task checkbox/evidence. No migration, persisted schema, runtime composition, feature manifest, or reconciliation behavior requires rollback.
- Known model constraint: duplicate prevention follows the existing entity-plus-pattern learned-writer identity but has no database unique constraint; concurrent duplicate creates remain a migration-level follow-up risk.

### Commit And Review Assessment

- The maintainer explicitly authorized `size:exception` for the cohesive 534-line API transaction.
- Work-unit commit: `49cb895` (`feat(ai-rules): add tenant rule management API`).
- Parent verification reran all six focused tests successfully and confirmed the capability remains enabled but unusable until UI completion.
- Native risk assessment: `medium`; review was due because the 534-line slice budget was reached.
- Candidate review outcome: explicitly declined for this candidate; future reviews remain enabled.
