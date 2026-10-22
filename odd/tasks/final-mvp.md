# Final MVP Delivery

## Objective

Deliver a deployable end-to-end financial reconciliation MVP by Sunday, including demo data, operational documentation, and video guidance.

## Problem and Why

The repository contains an approved design and database model but no executable application. The final delivery must prove the complete reconciliation journey rather than add more design artifacts.

## Authorized Scope

- Pre-registered user login.
- CSV upload and validation using the approved templates.
- Pending transaction views.
- Automatic 1:1 reconciliation proposals.
- Proposal confirmation and rejection.
- Atomic reconciliation reversal.
- Reconciliation history.
- PostgreSQL 16 with deterministic demo data.
- Online deployment and public URL in the README.
- Installation, execution, testing, exclusions, and demo documentation.
- English video script or guidance.

## Explicit Non-goals

- User registration, password recovery, and role management.
- Multiple currencies or many-to-many reconciliation.
- Asynchronous jobs and queue infrastructure.
- Dashboards, exports, and advanced reporting.
- Performance optimization for 10,000-row files beyond a documented smoke check.
- Fuzzy database extensions such as `pg_trgm`.

## Constraints

- Deadline: Sunday.
- Preserve the approved API, SQL model, CSV formats, and business rules.
- PostgreSQL 16 is the required database.
- New code, identifiers, and comments use English; the existing Spanish UI and public documentation remain Spanish.
- `.atl/` is local generated tooling and must not be committed.
- Hugo and Farid must create their own genuine contributions; authorship must not be fabricated.

## Architecture Direction

- Modular FastAPI monolith using SQLAlchemy and PostgreSQL.
- React, Vite, and TypeScript frontend with one shared API client.
- Bearer JWT for the pre-registered demo user, following the approved API contract.
- Synchronous import and matching for the MVP.
- Reuse `database/schema.sql`; add migration tooling only if schema evolution requires it.

## Delivery Strategy

- Feature branch: `feat/final-mvp`.
- Base and initial reviewed boundary: `19cd66a`.
- Strategy: `ask-on-risk`; the maintainer selected `stacked-to-main` because the forecast exceeds 400 authored changed lines.
- Forecast: 3,000–4,500 authored changed lines across 35–50 files.
- Each task closes with focused checks and at least one Conventional Commit work unit.
- Pull request strategy: stacked PRs that merge to `main` in dependency order.
- Pull request slice boundaries will be recorded as work units close.

## Tasks

- [x] **MVP-01 — Backend bootstrap, database, authentication, and demo seed**
  - Route: delegated direct.
  - Trigger evidence: coordinated implementation across multiple non-trivial backend, database, test, and configuration files.
  - Acceptance: `/health` is healthy; demo credentials receive a valid token; invalid credentials are rejected; PostgreSQL schema and seed initialize deterministically.
  - Checks: Compose configuration; focused backend auth tests; startup smoke test.

- [x] **MVP-02 — Frontend shell and login flow**
  - Route: delegated direct.
  - Trigger evidence: multiple React, routing, API-client, and test files.
  - Acceptance: the demo user can log in, session state is handled, and protected navigation rejects unauthenticated access.
  - Checks: frontend unit tests and production build passed.

- [x] **MVP-03 — Catalogs and batch intake**
  - Route: delegated direct.
  - Trigger evidence: API, persistence, and tests span multiple non-trivial files.
  - Acceptance: approved sources/templates are listed and a CSV batch can be submitted and inspected.
  - Checks: focused API integration tests.

- [x] **MVP-04 — CSV parsing, validation, and error reporting**
  - Route: delegated direct.
  - Trigger evidence: parser, validation rules, storage, fixtures, and tests.
  - Acceptance: valid rows persist; invalid rows produce deterministic row-level errors without corrupting the batch.
  - Checks: approved CSV fixtures plus malformed-file cases.

- [x] **MVP-05 — Pending transaction queries**
  - Route: delegated direct.
  - Trigger evidence: query service, API route, serialization, and tests.
  - Acceptance: unreconciled bank and collection transactions can be filtered and listed.
  - Checks: focused query tests.

- [ ] **MVP-06 — Matching engine and proposal generation**
  - Route: delegated direct.
  - Trigger evidence: business algorithm, persistence, API, and deterministic tests.
  - Acceptance: only ARS, exact amount, and ±3-day candidates qualify; NFKD/Jaccard reference similarity ranks candidates but never changes eligibility.
  - Checks: unit tests for eligibility, ranking, duplicates, and no-match cases.

- [ ] **MVP-07 — Proposal decision and history**
  - Route: delegated direct.
  - Trigger evidence: transactional state changes, API routes, queries, and tests.
  - Acceptance: proposals can be confirmed or rejected exactly once and confirmed reconciliations appear in history.
  - Checks: integration tests for valid and conflicting transitions.

- [ ] **MVP-08 — Atomic reconciliation reversal**
  - Route: delegated direct.
  - Trigger evidence: transactional reversal, proposal regeneration behavior, and tests.
  - Acceptance: reversal restores both transactions to pending, records audit data, and prevents duplicate reversal.
  - Checks: transaction and concurrency-oriented integration tests.

- [ ] **MVP-09 — Import, validation, and pending UI**
  - Route: delegated direct.
  - Trigger evidence: multiple pages, components, API integration, and tests.
  - Acceptance: users can upload both approved CSV types, inspect validation results, and browse pending records.
  - Checks: component tests and production build.

- [ ] **MVP-10 — Proposal, history, and reversal UI**
  - Route: delegated direct.
  - Trigger evidence: multiple workflow pages, mutations, state handling, and tests.
  - Acceptance: users can inspect, confirm, reject, and reverse records through the complete UI journey.
  - Checks: component tests and an end-to-end happy-path smoke test.

- [ ] **MVP-11 — Deployment and demo environment**
  - Route: delegated direct.
  - Trigger evidence: production configuration across API, frontend, PostgreSQL, and hosting manifests.
  - Acceptance: the public deployment works with documented demo credentials and deterministic seed data.
  - Checks: production builds, database initialization, and remote smoke test after explicit remote authorization.

- [ ] **MVP-12 — Final documentation and video guidance**
  - Route: delegated direct.
  - Trigger evidence: README, deployment instructions, test evidence, exclusions, and video script span multiple documents.
  - Acceptance: a reviewer can install, run, test, access the deployment, understand exclusions, and record the English walkthrough.
  - Checks: link validation and clean-environment instruction review.

## Progress and Evidence

- 2026-10-21: repository mapped; approved design is implementation-ready, but no product code or manifests exist.
- 2026-10-21: feature branch `feat/final-mvp` created from `19cd66a`.
- 2026-10-21: maintainer selected the `stacked-to-main` chain strategy.
- 2026-10-22: MVP-01 implemented with FastAPI health/login, JWT validation dependency, PostgreSQL 16 compose initialization, deterministic demo seed, and focused tests.
- 2026-10-22: MVP-01 checks passed: backend pytest, Compose configuration validation, and import/startup smoke check.
- 2026-10-22: Isolated PostgreSQL 16 initialization completed successfully; schema and seed ran in order, created 12 public tables, and produced the active demo user. The standard host-port startup was unavailable because `127.0.0.1:5432` was already occupied.
- 2026-10-22: MVP-02 implemented with the React/Vite/TypeScript shell, shared auth API client, bearer session persistence with expiry handling, accessible login/error states, logout, and protected navigation redirect.
- 2026-10-22: MVP-02 checks passed: five frontend authentication tests and the Vite production build.
- 2026-10-22: MVP-03 implemented authenticated source/template catalogs and transactional CSV batch intake with exact file bytes and ownership-scoped inspection; row parsing remains deferred to MVP-04.
- 2026-10-22: MVP-03 checks passed: focused backend API tests, full backend pytest, schema/seed SQL parsing, and Compose configuration validation.
- 2026-10-22: MVP-04 implemented synchronous parsing of stored original bytes, exact template header validation, typed movement/receipt persistence, deterministic duplicate and row-level validation errors, owner-scoped error inspection, and terminal batch status/totals.
- 2026-10-22: MVP-04 checks passed: backend pytest (16 passed), Python compilation, Compose configuration validation, SQL boundary inspection, and approved CSV fixture coverage for valid, invalid, duplicate, and structurally invalid files.
- 2026-10-22: MVP-05 implemented with owner-scoped pending queries for bank and collection records, type/source/batch/state/date filters, stable creation-order pagination, original-reference serialization, and active-reconciliation exclusion.
- 2026-10-22: MVP-05 checks passed: focused query tests (3 passed), full backend pytest (19 passed), Python compilation, Docker Compose configuration validation, PostgreSQL 16 schema initialization in an isolated container, and diff-whitespace validation. Pytest reports one existing Starlette/httpx deprecation warning.

## Current Next Step

MVP-05 is complete. Continue with MVP-06 — matching engine and proposal generation.
