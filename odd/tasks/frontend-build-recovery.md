# Frontend Build Recovery

## Objective

Restore a reproducible production build for the imported advanced frontend without changing product scope or hiding type failures.

## Context

- Parent snapshot: `18bd2b00a198ca1fea6c7e9851af264b7eb9edc8`.
- Branch: `fix/frontend-build-recovery`.
- Initial evidence: `npm run build` exits with code 2 and reports 61 TypeScript errors before Vite starts.
- The imported snapshot contains 32 known dependency vulnerabilities; dependency upgrades are a separate work unit.

## Authorized Scope

- Correct shared frontend model contracts, component props, API response types, missing imports/modules, nullability, JSX component signatures, and unused declarations that block `tsc -b`.
- Preserve current runtime behavior unless a type mismatch proves the implementation cannot work as written.
- Add focused regression tests only where an existing runner supports meaningful behavior proof.
- Do not modify backend, infrastructure, feature scope, dependencies, or lockfiles unless the build is impossible without a narrowly justified manifest correction.

## Task

- [x] **FRONTEND-01 — Restore production TypeScript build**
  - Route: delegated direct.
  - Trigger evidence: deterministic failures span multiple non-trivial React, hook, model, and API files.
  - Acceptance: clean install succeeds; `npm run build` exits 0; no `@ts-ignore`, broad error suppression, `any` proliferation, or disabled compiler checks are introduced; runtime-facing contracts remain coherent.
  - Checks: initial RED inventory, focused tests if available, production build, lint report, dependency audit report without fixes, `git diff --check`, and clean post-commit status.

## Delivery Strategy

- Stacked-to-main child of the sanitized snapshot slice.
- Target approximately 400 authored changed lines; split only if a cohesive independent boundary exists.
- Commit tests and contract documentation with the behavior they validate.
- No push or pull request without separate authorization.

## Current Next Step

Address inherited lint debt and dependency vulnerabilities as separate work units; do not push or open a pull request without explicit authorization.

## Evidence

### RED

- `npm ci` completed successfully: 428 packages installed and 429 packages audited.
- Initial `npm run build` exited 2 before Vite started with 61 TypeScript errors.
- Error inventory: 20 missing or incompatible model properties; 17 unused imports or declarations; 13 assignability, signature, operand, or JSX errors; 7 missing module, global, or type-import errors; 2 nullability errors; 2 implicit-`any` errors.
- Root-cause clusters: stale frontend DTOs versus backend response schemas; mismatched component and hook signatures; browser code using Node globals and timer types; an obsolete type-module import; nullable asynchronous response values; and a lot-assembler component with no JSX return.

### GREEN And Refactor

- Shared entity, bank, invoice, and payment contracts were aligned before leaf components.
- Bank approval now preserves the `MOVIMIENTO` versus `SOLICITUD` discriminator through the callback boundary.
- Cash-account currency is retained when preparing a cash invoice payload.
- Reconciliation pending and undo contracts now match their API and component consumers.
- Multipart upload retries now forward Axios request configuration and return a deterministic boolean result.
- The Interbanking lot assembler again renders its existing selection, account, assembly, export, and refresh workflow.
- Final `npm run build` exited 0: Vite 7.3.3 transformed 2,020 modules and completed in 5.28 seconds.
- No test script exists in `frontend/app/package.json`; no ceremonial test runner was added.

### Remaining Debt

- `npm run lint` reports inherited debt: 142 errors and 13 warnings. The remaining findings are primarily existing explicit `any`, React hook/compiler rules, unused catches, and hook dependency warnings; dependency-unrelated lint cleanup remains out of scope.
- `npm audit --json` reports 32 vulnerabilities: 2 low, 15 moderate, 15 high, and 0 critical. No audit fix or dependency change was applied.
- The production build reports a stale `caniuse-lite` dataset warning; updating browser data is dependency maintenance and remains out of scope.

### Commit And Review Assessment

- Work-unit commit: `0bb286df410c9088d377afee4a3bb79916cf9729` (`fix(frontend): restore production build`).
- Authored size: 365 lines across 27 authorized paths.
- Parent verification reran `npm run build`: exit 0, 2,020 modules transformed.
- Native risk assessment: `medium` because executable frontend behavior changed.
- Review outcome: `under_budget`; no candidate review was due for the 365-line range.

## Rollback Boundary

Revert the FRONTEND-01 commit to remove the frontend contract corrections, browser-safe typing, loading and callback boundary fixes, restored Interbanking lot assembler render, and this evidence update. No dependency manifests, lockfiles, backend files, compiler strictness, or generated output are part of the boundary.
