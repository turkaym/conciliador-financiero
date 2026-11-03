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

- [ ] **AI-RULES-02 — Add rules management UI and activate readiness**
  - Route: delegated direct.
  - Acceptance: enabled and entitled users can administer deterministic rules through the frontend; disabled/unimplemented states remain fail-closed; only after API/UI proof does capability readiness become true.
  - Checks: frontend contract tests, route/navigation proof, production build, API integration smoke, and feature capability response.

## Delivery Strategy

- Stacked-to-main child of MVP feature flags.
- API and UI are separate green work units. The global capability remains unusable between them.
- Target approximately 400 authored changed lines per work unit; tests and audit behavior stay with implementation.
- No push, pull request, or remote configuration without separate authorization.

## Current Next Step

Implement AI-RULES-02 without changing the API contract below, then mount the router and flip readiness only after UI and composition proof are green.

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
