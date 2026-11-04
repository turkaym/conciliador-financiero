# Frontend Lint Recovery

## Objective

Restore a green frontend lint baseline without weakening rules, ignoring repository-owned source, or trading behavioral correctness for cosmetic compliance.

## Baseline

- Parent operational guide: `a21969b`.
- Branch: `fix/frontend-lint-runtime`.
- `npm run lint -- --format json`: 142 errors and 14 warnings across 42 tracked source files.
- No finding originates from generated, vendor, build or dependency output.
- Production build, feature-flag contracts and AI Rules contracts are green.

| Rule | Errors | Warnings | Files |
| --- | ---: | ---: | ---: |
| `@typescript-eslint/no-explicit-any` | 84 | 0 | 28 |
| `@typescript-eslint/no-unused-vars` | 21 | 0 | 15 |
| `react-hooks/refs` | 17 | 0 | 1 |
| `react-hooks/set-state-in-effect` | 5 | 0 | 5 |
| `prefer-const` | 5 | 0 | 1 |
| `no-useless-catch` | 4 | 0 | 1 |
| `react-hooks/immutability` | 3 | 0 | 3 |
| `react-refresh/only-export-components` | 2 | 0 | 2 |
| `react-hooks/purity` | 1 | 0 | 1 |
| `react-hooks/exhaustive-deps` | 0 | 12 | 11 |
| `react-hooks/incompatible-library` | 0 | 2 | 2 |

## Tasks

- [x] **LINT-01 — Stabilize polling and reconciliation lifecycle callbacks**
  - Route: delegated direct; three behavioral files.
  - Surface: `ImportarExtractoModal.tsx`, `ImportarPadronModal.tsx`, `Conciliacion.tsx`.
  - Acceptance: zero lint findings in these files; successful polling still closes and resets import state; reconciliation entity/flow/tab transitions reset selection without effect loops.

- [x] **LINT-02 — Separate the Sifón ref boundary from render state**
  - Route: delegated direct.
  - Surface: `useSifonFiscal.ts`, `SifonFiscalForm.tsx`.
  - Acceptance: all 17 `react-hooks/refs` errors removed while upload, preview, clear and submit behavior remain intact.

- [ ] **LINT-03 — Remove effect-driven derived state**
  - Route: delegated direct.
  - Surface: notification, account, third-party, payment-order and comprobantes UI state.
  - Acceptance: five `set-state-in-effect` errors removed without extra network requests or render loops.

- [ ] **LINT-04 — Complete hook dependencies and session purity**
  - Route: delegated direct.
  - Acceptance: remaining hook dependency/purity findings reach zero; intervals, polling and cleanup remain deterministic.

- [ ] **LINT-05 — Model shared, auth, banking and comprobantes type boundaries**
  - Route: delegated direct.
  - Acceptance: replace relevant explicit `any` uses with error, API and domain types without unsafe assertions.

- [ ] **LINT-06 — Model reconciliation, expenses and reporting type boundaries**
  - Route: delegated direct.
  - Acceptance: replace relevant explicit `any` uses while preserving tenant and financial payload semantics.

- [ ] **LINT-07 — Model registries, team and supplier type boundaries**
  - Route: delegated direct.
  - Acceptance: replace relevant explicit `any` uses while preserving forms and API behavior.

- [ ] **LINT-08 — Remove dead code and mechanical hygiene findings**
  - Route: delegated direct.
  - Acceptance: unused, `prefer-const`, useless-catch and refresh-export findings reach zero; full lint, build, contracts and CI parity pass.

## Test-First Policy

- The existing lint findings provide an observed static RED for each slice.
- No deterministic component test runner currently exercises polling completion or reconciliation reset behavior, so each behavioral slice must document this test-gap exception and combine focused lint, build/contracts, source-level lifecycle proof and non-destructive manual runtime checks where possible.
- Never invent RED/GREEN behavioral evidence or introduce a test framework only to satisfy process ceremony.

## Delivery And Review

- Each task is a separate work-unit commit with its own verification and rollback record.
- The ~400 authored-line task size is advisory; type-boundary tasks split by feature when modeling becomes larger.
- Native review assessment runs per work-unit commit. Push, PR and merge remain separate decisions.

## LINT-01 Evidence

- Work-unit commit: `6d1ec22` (`fix(frontend): stabilize polling lifecycle callbacks`). Native assessment against `a21969b`: `medium`, `review_due=false`, `review_due_reason=under_budget`.
- Changed behavior: extract and registry polling synchronization now cancels queued state work during dependency cleanup; successful completion still closes once by resetting `isSubmitted`, modal visibility, form state and errors through the existing close semantics. Manual close uses the same reset path.
- Changed behavior: reconciliation entity changes clear selections after starting the existing status/history refreshes, while actual flow and tab transitions clear movement/document selections, restore the first mobile step and close the adjustment modal before changing views. Same-tab clicks remain no-ops and no feature gate or API payload changed.
- Static RED: focused lint reported 8 findings across the three files: 6 errors and 2 warnings (`react-hooks/immutability` 3, `react-hooks/exhaustive-deps` 2, `@typescript-eslint/no-explicit-any` 2 and `@typescript-eslint/no-unused-vars` 1).
- Static GREEN: `npx --no-install eslint src/features/bancos/components/ImportarExtractoModal.tsx src/features/padrones/components/ImportarPadronModal.tsx src/pages/Conciliacion.tsx` exited 0 with no output.
- Remaining baseline: full `npm run lint -- --format json` reports 136 errors and 12 warnings across 39 files. Relative to the 142-error/14-warning/42-file baseline, the rule delta is `react-hooks/immutability` 3 to 0, `react-hooks/exhaustive-deps` 12 to 10, `@typescript-eslint/no-explicit-any` 84 to 82 and `@typescript-eslint/no-unused-vars` 21 to 20; all other rule counts are unchanged.
- Remaining rules: `@typescript-eslint/no-explicit-any` 82 errors; `@typescript-eslint/no-unused-vars` 20 errors; `react-hooks/refs` 17 errors; `react-hooks/set-state-in-effect` 5 errors; `prefer-const` 5 errors; `no-useless-catch` 4 errors; `react-refresh/only-export-components` 2 errors; `react-hooks/purity` 1 error; `react-hooks/exhaustive-deps` 10 warnings; `react-hooks/incompatible-library` 2 warnings.
- Focused verification: feature-flag and AI Rules dependency-free contracts passed; `npm run build` passed with 2,030 modules transformed; `git diff --check` passed.
- Behavioral proof: a read-only source contract confirmed both modal completion/reset paths, cancellation guards and reconciliation transition resets. `src/featureFlags.test.ts` passed and confirmed reconciliation remains unusable/hidden; `App.tsx` continues to register its route only through `isFeatureUsable(capabilities, "reconciliation")`. No tenant API or data was mutated.
- Test-gap exception: no deterministic component runner exists for these polling/reset transitions. No behavioral test result is claimed; verification is focused lint, build/contracts, source-level lifecycle proof and non-destructive feature-route execution.
- Residual risk: pre-existing notification and bank SSE retry timeouts are owned by the parent hooks and remain outside this exact task surface. Existing EventSource teardown remains unchanged. Native review is pending for this work-unit commit against parent `a21969b`.
- Rollback: revert the LINT-01 work-unit commit to restore the three source files and this evidence record together; no dependency, configuration, feature-gate or remote rollback is required.

## LINT-02 Evidence

- Root cause: `useSifonFiscal` returned `fileInputRef` in the same object as render state and callbacks. The React hooks analyzer therefore treated ordinary `h.*` render reads as ref-derived and reported 17 `react-hooks/refs` errors in `SifonFiscalForm.tsx`.
- Contract change: the hidden file input ref is now component-owned and used only by its input binding and upload-area click handler. The hook remains the owner of selected-file, preview, compression, clear/reset and submit state; no effect, duplicate state, callback memoization, payload, endpoint, calculation, copy or feature-gate changed. Local response shapes and caught errors were typed only as required to clear every focused finding.
- Static RED: before edits, `npx --no-install eslint src/features/egresos/hooks/useSifonFiscal.ts src/features/egresos/components/SifonFiscalForm.tsx` reported 27 errors: `react-hooks/refs` 17, `@typescript-eslint/no-explicit-any` 8 and `@typescript-eslint/no-unused-vars` 2.
- Static GREEN: the same focused lint command exited 0 with no output.
- Remaining baseline: full `npm run lint -- --format json` reports 109 errors and 12 warnings across 37 files. Relative to the LINT-01 baseline of 136 errors, 12 warnings and 39 files, `react-hooks/refs` changed 17 to 0, `@typescript-eslint/no-explicit-any` 82 to 74 and `@typescript-eslint/no-unused-vars` 20 to 18; all other rule counts are unchanged.
- Remaining rules: `@typescript-eslint/no-explicit-any` 74 errors; `@typescript-eslint/no-unused-vars` 18 errors; `react-hooks/set-state-in-effect` 5 errors; `prefer-const` 5 errors; `no-useless-catch` 4 errors; `react-refresh/only-export-components` 2 errors; `react-hooks/purity` 1 error; `react-hooks/exhaustive-deps` 10 warnings; `react-hooks/incompatible-library` 2 warnings.
- Verification: feature-flag contract printed `Frontend feature route/navigation proof passed`; AI Rules contract printed `AI Rules route and conflict contract proof passed`; `npm run build` passed with 2,030 modules transformed; focused lint and `git diff --check` passed.
- Behavioral proof: file selection still flows from the hidden input `onChange` into image validation, WebP compression, `selectedFile` and object-URL preview state; the selected filename and preview still render from that state. Clear sets both values to null, remounting a fresh hidden input. Submit still validates required fields, optionally obtains the same presigned URL and uploads the same file, posts the unchanged order payload, refreshes orders and resets the form including file state. Disabled and loading states still derive from `isCompressing` and `isSubmitting`.
- Capability evidence: `expenses_payments` remains enabled in `config/feature_flags.json`, implementation-ready in `config/feature_flags.py`, usable in the dependency-free feature contract and routed to `egresos` through the existing capability guard. No credentials or tenant data were accessed.
- Test-gap exception: no deterministic component runner covers this form. No behavioral test or financial upload is claimed; evidence is focused lint, build/contracts, source-level path proof and read-only capability inspection. No tenant record was mutated.
- Residual risk: browser-level file-picker, camera capture, object-URL preview and upload integration remain unautomated. Native review is pending for the LINT-02 work-unit commit against parent `6d1ec22`.
- Rollback: revert the LINT-02 work-unit commit to restore both Sifón files and this evidence record together; no dependency, configuration, API, feature-gate, tenant-data or remote rollback is required.

## Current Next Step

Implement LINT-03 by removing effect-driven derived state without extra network requests or render loops.
