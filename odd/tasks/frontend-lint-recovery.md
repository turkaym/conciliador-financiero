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

- [x] **LINT-05 — Model shared, auth, banking and comprobantes type boundaries**
  - Route: delegated direct.
  - Acceptance: replace relevant explicit `any` uses with error, API and domain types without unsafe assertions.

- [x] **LINT-06 — Model reconciliation, expenses and reporting type boundaries**
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

- Work-unit commit: `6e321c8` (`fix(frontend): stabilize hook synchronization`), parent `9f32b43`. Its native assessment against `9f32b43` was `medium / under_budget`, with `review_due=false`; the current cumulative review boundary remains `9f32b43`.
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

## LINT-05 Evidence

- Work-unit commit: `3d70ba0` (`refactor(frontend): type shared data boundaries`), parent `6e321c8`. The cumulative LINT-04→05 candidate from `9f32b43` was assessed `medium / slice_budget_reached / declined_this_candidate`; the user declined only that candidate and future native reviews remain enabled.
- Owned contracts: shared Axios/FastAPI error detail parsing now accepts `unknown` and validates Pydantic detail items; Axios request headers use the library-owned `AxiosHeaders` boundary; backoff and throttle preserve generic payload/callback types. Entity, fiscal alert and AFIP vault responses use their backend fields without open index signatures.
- Owned contracts: banking models now match manual movement, clearing-provider, presigned upload, SSE progress/result and four-eyes resolution payloads. Comprobantes models now own the complete form/create payload, dynamic association filters and typed bank-account projection used for cash accounts; existing shared bank and comprobante domain types are reused.
- Static RED: before edits, focused JSON lint over `src/api`, `src/lib`, top-level `src/components/*.tsx`, `src/features/bancos` and `src/features/comprobantes` reported exactly 35 `no-explicit-any` errors across 12 files.
- Static GREEN: the same focused lint reports zero `no-explicit-any` findings. Remaining focused findings are 9 unrelated errors across 4 files: 4 `no-unused-vars` errors and 5 `prefer-const` errors; these remain owned by LINT-08.
- Full baseline: `npm run lint -- --format json` exits 1 with 68 errors and 2 warnings across 24 files. Relative to LINT-04, `no-explicit-any` changed 74 to 39 and its files changed 28 to 13; `no-unused-vars` remains 18, `prefer-const` 5, `no-useless-catch` 4, `react-refresh/only-export-components` 2, and the 2 valid TanStack Virtual `react-hooks/incompatible-library` warnings remain visible.
- Verification: `npx --no-install tsc -b` passed with no output; feature-flag contract printed `Frontend feature route/navigation proof passed`; AI Rules contract printed `AI Rules route and conflict contract proof passed`; `npm run build` passed with 2,030 modules transformed; `git diff --check` passed.
- Behavioral proof: backend string and Pydantic validation details retain their existing user-facing extraction and fallbacks. The Axios interceptor still injects bearer, active `X-Entity-ID` and mutation idempotency headers. Banking account/manual movement/import/analyze/confirm/resolution payload keys, page size 50 replacement/append behavior and SSE result messages are unchanged. Comprobante draft/apply filters, association routing by buyer/seller CUIT, complete form payload, explicit tenant header, page size 50 pagination and optimistic delete rollback are unchanged.
- Runtime evidence: read-only probes returned API `/health` HTTP 200 with `status=online`, frontend `/` HTTP 200, and eight capabilities with `ai_rules=true/true/true` and `reconciliation=false/true/false`; disabled Reconciliation `/v1/matching` returned HTTP 404. No service was started or rebuilt and no tenant financial data was mutated.
- Test-gap exception: no deterministic component/API mock suite covers every typed interaction. No behavioral RED/GREEN result is claimed; evidence is the observed lint RED→GREEN, strict type/build/contracts, source-level contract proof and non-destructive runtime health/capability checks.
- Residual risk: runtime response validation remains owned by Axios/backend contracts rather than a schema parser, and browser-level upload, autocomplete, account creation and comprobante submission remain unautomated. Cumulative native review is pending from boundary `9f32b43`.
- Rollback: revert the LINT-05 work-unit commit to restore the shared/API/auth/top-level component, banking and comprobantes type boundaries plus this evidence record; no dependency, configuration, endpoint, feature-gate, tenant-data, service or remote rollback is required.

## LINT-06 Evidence

- Work unit: `refactor(frontend): type financial data boundaries`, parent and new native-review boundary `3d70ba0`. The complete authorized reconciliation, expenses/payments and reporting scope is included as one independently green feature-boundary commit; future native review remains enabled.
- Owned contracts: reconciliation status preserves nullable source dates, polymorphic `CBT-*`/`OP-*` IDs, numeric movement IDs and optional fiscal adjustments. Manual matching retains the exact `comprobantes_ids`, `movimientos_ids` and conditional `ajustes_fiscales` payload. History now reflects nullable `asiento_id`, pagination metadata and the backend's distinct comprobante/movement detail shapes using `monto_aplicado`; no invented `monto_applied` or currency field remains.
- Owned contracts: payment simulation represents backend Decimal amounts as `string | number` until the existing explicit UI calculations, while payment-order payloads retain nullable `cuenta_origen_id`, selected invoice IDs, exchange rate and edited retention values. Existing `Comprobante`, `CuentaBancaria`, `LotePago` and inferred lot-detail models are reused. Bank assembly retains its treasury-account and order-ID payload plus idempotency header; presigned MinIO upload results retain separate `upload_url` and `final_url` fields.
- Owned contracts: trial-balance and ledger datasets now include the backend tenant, cutoff, movement-count, account, totals and row shapes. Shared `extractApiError` narrows `unknown` and preserves FastAPI string and Pydantic detail messages for reconciliation, payment simulation/submission, lot assembly and reports.
- Static RED: focused lint over `src/features/conciliacion`, `src/features/egresos`, `src/features/reportes`, `src/pages/Conciliacion.tsx` and `src/pages/Reportes.tsx` reported exactly 15 `no-explicit-any` errors across 8 files. The full focused result was 22 errors and 2 warnings: 15 target errors, 7 unrelated `no-unused-vars` errors and 2 existing TanStack Virtual `react-hooks/incompatible-library` warnings.
- Static GREEN: the same focused lint reports zero `no-explicit-any` findings. Remaining focused findings are 6 unrelated `no-unused-vars` errors across 4 files and the same 2 TanStack Virtual warnings; the report exporter's co-located unused catch binding was removed directly with its `any` annotation.
- Full baseline: `npm run lint` exits 1 with 52 errors and 2 warnings across 19 files. Relative to LINT-05's 68 errors, 2 warnings and 24 files, `no-explicit-any` changed 39 to 24 and `no-unused-vars` changed 18 to 17; `prefer-const` remains 5, `no-useless-catch` 4, `react-refresh/only-export-components` 2 and `react-hooks/incompatible-library` 2 warnings.
- Verification: `npx --no-install tsc -b` passed with no output; the feature-flag contract printed `Frontend feature route/navigation proof passed`; the AI Rules contract printed `AI Rules route and conflict contract proof passed`; `npm run build` passed with 2,030 modules transformed; `git diff --check` passed.
- Runtime evidence: read-only probes returned API `/health` HTTP 200 with `status=online`, frontend `/` HTTP 200, and eight capabilities with `expenses_payments=true/true/true`, `ai_rules=true/true/true` and `reconciliation=false/true/false`; disabled `/v1/matching` returned HTTP 404. No service was rebuilt, no upload was attempted and no tenant or financial data was mutated.
- Behavioral proof: reconciliation selection arithmetic still converts only displayed transport amounts, rounds the difference to two decimals and posts unchanged matching IDs/adjustments while its route remains capability-disabled. Payment gross, retention, net, balance and FX calculations retain their explicit conversions and null account semantics; lot authorization/assembly/export and MinIO PUT paths retain their endpoints and payload keys. Reports retain their tenant-scoped endpoints, numeric formatting and read-only datasets.
- Test-gap exception: no deterministic component/API mock suite covers every financial interaction. No behavioral RED/GREEN, upload, payment, lot, reconciliation or tenant mutation is claimed; evidence is the observed lint RED→GREEN, strict type/build/contracts, source-level contract proof and non-destructive runtime checks.
- Residual risk: runtime response validation remains owned by Axios/backend contracts rather than a schema parser, and browser-level matching, payment, lot, presigned upload and report interactions remain unautomated.
- Rollback: revert the LINT-06 work-unit commit to restore the financial boundary types and this evidence record together; no dependency, configuration, feature-gate, endpoint, tenant-data, service or remote rollback is required.

## Current Next Step

Implement LINT-07 by modeling registries, team and supplier type boundaries without unsafe assertions.
