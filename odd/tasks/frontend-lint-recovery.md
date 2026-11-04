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

- [x] **LINT-03 — Remove effect-driven derived state**
  - Route: delegated direct.
  - Surface: notification, account, third-party, payment-order and comprobantes UI state.
  - Acceptance: five `set-state-in-effect` errors removed without extra network requests or render loops.

- [x] **LINT-04 — Complete hook dependencies and session purity**
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

- Work-unit commit: `6d1ec22` (`fix(frontend): stabilize polling lifecycle callbacks`). Its incremental assessment against `a21969b` was provisional; LINT-01, LINT-02 and LINT-03 accumulated into one 481-line native-review candidate rather than three independent final candidates.
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

- Work-unit commit: `8a059ad` (`fix(frontend): separate Sifon ref boundary`). Its incremental assessment against `6d1ec22` was provisional and became part of the cumulative LINT-01→03 candidate.
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
- Residual risk: browser-level file-picker, camera capture, object-URL preview and upload integration remain unautomated. The native assessment completed at `medium / under_budget`; no further review was due.
- Rollback: revert the LINT-02 work-unit commit to restore both Sifón files and this evidence record together; no dependency, configuration, API, feature-gate, tenant-data or remote rollback is required.

## LINT-03 Evidence

- Work-unit commit: `9f32b43` (`fix(frontend): remove effect-driven state resets`). The consolidated LINT-01→03 candidate against `a21969b` was 481 authored lines and received the exact outcome `medium / slice_budget_reached / declined_this_candidate`. The user declined only that candidate; future native reviews remain enabled.
- Root causes: notification data was synchronously cleared by the polling effect; account channel changes normalized related fields in an effect; contact suggestions copied render inputs into state; payment retention suggestions were copied into editable state; and tenant changes reset the comprobantes page inside the fetch effect.
- Semantic changes: notification state is keyed by active entity, so tenant changes start with closed, empty UI state while retaining one immediate request plus the existing interval; request completion and optimistic rollback cannot update state after unmount. Account channel normalization now occurs in the channel event, close/success still restores all defaults, and active edits remain untouched. Third-party suggestions derive from the active field, current text and loaded agenda, while deliberate field/contact changes remain event-owned.
- Semantic changes: editable payment retentions use defaults until an edit is made and retain edits only while provider, selected invoices, account, exchange rate and engine suggestions share the same key. Comprobantes resets only the page through the entity-selection event; draft filters, filter visibility, delete selection, explicit apply/clear behavior and page-zero tenant fetch remain unchanged.
- Static RED: before edits, focused lint reported 13 findings across the five files: 12 errors and 1 warning. The target rule contributed exactly 5 `react-hooks/set-state-in-effect` errors, one per file; unrelated findings were 7 `@typescript-eslint/no-explicit-any` errors, 1 `@typescript-eslint/no-unused-vars` error and 1 `react-hooks/exhaustive-deps` warning.
- Static GREEN: the same focused lint reports zero `react-hooks/set-state-in-effect` findings. Remaining focused findings are exactly 7 errors and 1 warning: `NotificationBell.tsx` has 2 `no-explicit-any`; `SeccionTercero.tsx` has 3 `no-explicit-any`; `OrdenPagoForm.tsx` has 1 `no-explicit-any` and 1 `no-unused-vars`; `Comprobantes.tsx` has 1 `exhaustive-deps` warning; `NuevaCuentaModal.tsx` is clean.
- Remaining baseline: full `npm run lint -- --format json` exits 1 with 104 errors and 12 warnings across 36 files. Relative to the LINT-02 baseline of 109 errors, 12 warnings and 37 files, `react-hooks/set-state-in-effect` changed 5 to 0; every other rule count is unchanged.
- Remaining rules: `@typescript-eslint/no-explicit-any` 74 errors; `@typescript-eslint/no-unused-vars` 18 errors; `prefer-const` 5 errors; `no-useless-catch` 4 errors; `react-refresh/only-export-components` 2 errors; `react-hooks/purity` 1 error; `react-hooks/exhaustive-deps` 10 warnings; `react-hooks/incompatible-library` 2 warnings.
- Verification: feature-flag contract printed `Frontend feature route/navigation proof passed`; AI Rules contract printed `AI Rules route and conflict contract proof passed`; `npm run build` passed with 2,030 modules transformed; focused source-transition inspection and `git diff --check` passed.
- Behavioral proof: source inspection confirmed keyed notification remount/cleanup and event-owned optimistic interactions; modal close/success default restoration and channel-owned clearing normalization; render-derived contact suggestions with event-owned edits; keyed retention defaults/overrides submitted unchanged; and entity-event page reset with existing apply/clear filters. No API payload, validation, UI copy, tenant header, feature flag or request cadence changed.
- Runtime evidence: the existing Compose API and frontend remained healthy; API `/health` returned `status=online`, frontend `/` returned HTTP 200 and disabled Reconciliation `/v1/matching` returned HTTP 404. No service was rebuilt or tenant financial data mutated.
- Test-gap exception: no deterministic component runner covers these transitions. No behavioral test result is claimed; evidence is the observed lint RED/GREEN, build/contracts, source-level transition proof and non-destructive runtime health checks.
- Residual risk: browser-level open/close/reopen, contact autocomplete, optimistic notification rollback and edited-retention interaction remain unautomated. The cumulative native-review outcome is recorded above; it does not disable review for later work units.
- Rollback: revert the LINT-03 work-unit commit to restore the five state-transition implementations and this evidence record together; no dependency, configuration, API, feature-gate, tenant-data, service or remote rollback is required.

## LINT-04 Evidence

- Work-unit: `fix(frontend): stabilize hook synchronization`, parent `9f32b43`; native review remains pending for this new slice alone.
- Root causes: loaders used render-local function identities without declaring them; bank and registry progress throttles wrapped opaque callbacks; bank retry timers were not owned by lifecycle cleanup; account selection followed completed requests through state-setting effects; tenant-sensitive lot/account hydration omitted the entity transition; and session activity called `Date.now()` during render.
- Synchronization contracts: entity, supplier, report and AI Rules loaders now have stable identities with complete dependencies. AI Rules still loads once per search/state change; report loading remains gated by role, tenant and active entity; comprobantes uses an Effect Event so tenant changes read current applied filter state without making draft filter edits refetch.
- Synchronization contracts: bank tenant transitions reset page/view selection from the auth-store event, clear movement data, fetch accounts once, and select the saved or first account only when that request completes. Account/page changes still fetch one 50-row page and page zero still replaces while later pages append. Lote pagination and account hydration now also react to entity changes.
- Synchronization contracts: bank and registry SSE progress remains leading-edge throttled at 250 ms. Bank reconnect cadence remains 1/2/4/8 seconds, the 15-second status refresh remains unchanged, and both queued retry/status timers plus the EventSource are cleared on unmount or entity change. Existing registry EventSource teardown remains intact.
- Session semantics: activity time is initialized inside the authenticated effect, reset only after a real logged-out state, updated by the same five browser events, checked every 60 seconds against the same 30-minute timeout, and refreshed every 14 minutes only while active. Token rotation therefore preserves accumulated inactivity while a later login starts a fresh idle window; interval and storage listeners retain deterministic cleanup.
- Static RED: focused JSON lint across the ten resolved files reported 37 errors and 10 warnings in all 10 files. Targets were exactly 10 `react-hooks/exhaustive-deps` warnings and 1 `react-hooks/purity` error; unrelated findings were 29 `no-explicit-any` errors and 7 `no-unused-vars` errors.
- Static GREEN: the same focused lint reports 36 errors, 0 warnings across 7 files, with both target rules at zero. The remaining focused findings are unchanged unrelated type/dead-code work: 29 `no-explicit-any` and 7 `no-unused-vars` errors.
- Full baseline: `npm run lint -- --format json` exits 1 with 103 errors and 2 warnings across 33 files. Relative to LINT-03, `react-hooks/purity` changed 1 to 0 and `react-hooks/exhaustive-deps` changed 10 to 0; every other rule count is unchanged. Remaining rules are 74 `no-explicit-any`, 18 `no-unused-vars`, 5 `prefer-const`, 4 `no-useless-catch`, 2 `react-refresh/only-export-components`, and 2 visible `react-hooks/incompatible-library` TanStack Virtual warnings.
- Verification: feature-flag contract printed `Frontend feature route/navigation proof passed`; AI Rules contract printed `AI Rules route and conflict contract proof passed`; `npm run build` passed with 2,030 modules transformed; `git diff --check` passed.
- Runtime evidence: the existing Compose API and frontend remained healthy without rebuild or mutation; API `/health` returned `status=online`, frontend `/` returned HTTP 200, capabilities returned eight records with `ai_rules=true/true/true` and `reconciliation=false/true/false`, and disabled Reconciliation `/v1/matching` returned HTTP 404.
- Behavioral proof: source inspection confirms request triggers remain tenant/entity, page, filter or explicit-event owned; pagination replacement/append semantics and filter apply/clear behavior are unchanged; SSE terminal paths still close streams and refresh data; report and AI Rules endpoints, payloads and copy are unchanged; and all intervals, storage listeners and queued bank retries have cleanup. No tenant financial API or data was mutated.
- Test-gap exception: no deterministic component runner covers these hook transitions, SSE retries or idle timeout. No browser behavioral result is claimed; evidence is static RED→GREEN, build/contracts, source-level cadence/transition/cleanup proof and non-destructive runtime health/capability checks.
- Rollback: revert this LINT-04 work-unit commit to restore the ten source synchronization implementations and this evidence record together; no dependency, configuration, endpoint, feature-gate, tenant-data, service or remote rollback is required.

## Current Next Step

Implement LINT-05 by modeling shared, auth, banking and comprobantes type boundaries without unsafe assertions.
