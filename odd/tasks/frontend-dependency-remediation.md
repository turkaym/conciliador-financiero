# Frontend Dependency Remediation

## Objective

Remove high-severity frontend dependency vulnerabilities without force-upgrading, weakening the build, or changing product behavior.

## Context

- Parent AI Rules completion: `ba77817`.
- Branch: `fix/frontend-dependencies`.
- Current clean install audits 429 packages and reports 32 vulnerabilities: 2 low, 15 moderate, 15 high, 0 critical.
- The production build is green and must remain green.

## Requirements

- Trace each high-severity advisory to its direct dependency and runtime/build exposure.
- Prefer supported direct upgrades and coherent lockfile regeneration.
- Do not run or apply `npm audit fix --force`.
- Do not suppress advisories, add package-manager overrides blindly, or remove active functionality merely to improve counts.
- Separate production-impacting vulnerabilities from development-only tooling findings.
- Preserve feature flags, AI Rules behavior, disabled Reconciliation, and the current Docker runtime.

## Task

- [x] **DEPS-01 — Remediate frontend high-severity advisories**
  - Route: delegated direct.
  - Acceptance: clean install succeeds; high and critical audit counts are zero or every unavoidable advisory has an explicit evidence-backed exception; production build and feature contract proofs pass; runtime frontend/API health remains green.
  - Checks: before/after audit inventory, dependency tree evidence, clean install, build, feature proofs, runtime smoke, lockfile consistency, `git diff --check`, and rollback boundary.

## Delivery Strategy

- Stacked-to-main child of AI Rules completion.
- Dependency manifest and generated lockfile belong in one work unit with verification evidence.
- Generated lockfile churn is reported separately from authored source changes.
- No push or pull request without separate authorization.

## Current Next Step

DEPS-01 is complete. The remaining audit findings are development-tooling-only low/moderate advisories and are outside this high/critical remediation boundary.

## DEPS-01 Evidence

### Advisory inventory

The RED clean install audited 429 packages and reported 32 vulnerabilities: 2 low, 15 moderate, 15 high, and 0 critical. `npm explain` traced every high package node as follows.

| High package | Installed -> selected | Direct/root path | Exposure and actual use |
| --- | --- | --- | --- |
| `axios` | 1.16.1 -> 1.21.0 | direct dependency | Browser runtime API client; active product path. Node-only adapter advisories are not browser-reachable, but the direct package was upgraded. |
| `follow-redirects` | 1.16.0 -> 1.16.2 | `axios` | Runtime dependency for the Axios Node adapter; installed but not used by the browser bundle. |
| `form-data` | 4.0.5 -> 4.0.6 | `axios` | Runtime dependency for Node multipart handling; installed but browser workflows use native browser APIs. |
| `react-router-dom` | 7.13.1 -> 7.18.5 | direct dependency | Active browser routing and protected feature routes. |
| `react-router` | 7.13.1 -> 7.18.5 | `react-router-dom` | Active browser route matching; server/RSC-specific advisory paths are not used by this SPA. |
| `postcss` | 8.5.14 -> 8.5.32 | direct dev dependency; also `vite`, `tailwindcss`, `autoprefixer` | Production CSS build path; no runtime server exposure. |
| `nanoid` | 3.3.11 -> 3.3.20 | `postcss` | Build-time PostCSS dependency; not shipped as an application API. |
| `source-map-js` | 1.2.1 -> 1.2.2 | `postcss` | Build-time source-map processing; active during builds, not at runtime. |
| `vite` | 7.3.3 -> 7.3.7 | direct dev dependency | Build and local development server; not part of the nginx runtime image. |
| `browserslist` | 4.28.1 -> 4.29.5 | `autoprefixer`; Babel via Vite React plugin | Active build target calculation; development/build exposure only. |
| `brace-expansion` | 1.1.12/5.0.4 -> 1.1.21/5.0.12 | `eslint`/`typescript-eslint` through `minimatch` | Lint-time glob processing only. |
| `flatted` | 3.3.4 -> 3.4.4 | `eslint` -> `file-entry-cache` -> `flat-cache` | ESLint cache tooling only; no product runtime path. |
| `js-yaml` | 4.1.1 -> 4.3.2 | `eslint` -> `@eslint/eslintrc` | Lint configuration tooling; the project uses flat JS config and does not parse user YAML. |
| `picomatch` | 2.3.1 -> 2.3.2 | `tailwindcss` through `chokidar`, `micromatch`, and `readdirp` | Active build-time content scanning; no runtime path. |
| `zod` | 4.3.6 -> 4.6.7 | `eslint-plugin-react-hooks` | Lint plugin validation only; no product runtime path. |

### Upgrade rationale

- npm registry metadata confirmed all selected versions and fix boundaries before editing. Direct lower bounds changed only for active vulnerable packages: Axios 1.21.0, React Router DOM 7.18.5, PostCSS 8.5.32, and Vite 7.3.7.
- The existing lint stack was retained at ESLint 9.39.3, TypeScript ESLint 8.56.1, React Hooks plugin 7.0.1, and Autoprefixer 10.4.27. Their vulnerable transitive packages were updated within declared compatible ranges to avoid unrelated lint-rule churn.
- The lockfile was regenerated through normal `npm install`/`npm update` resolution. No `npm audit fix --force`, override, downgrade, feature removal, audit suppression, or compiler/lint setting change was used.
- No source API adaptation was required. The React Router, Axios, Vite, and PostCSS upgrades remained within the already-declared major versions and passed build, contract, and runtime checks.

### GREEN verification

- Clean `npm ci`: added 428 packages and audited 429 packages successfully.
- `npm audit --json`: 16 total findings, comprising 2 low, 14 moderate, 0 high, and 0 critical. There are no high/critical exceptions.
- Remaining findings are confined to development/build tooling (`@babel/core`, ESLint/TypeScript ESLint internals, `esbuild`, `minimatch`, and `postcss-selector-parser`). They are not accepted as high-severity exceptions; they remain visible for a separate low/moderate tooling upgrade.
- `npm run build`: passed with Vite 7.3.7; 2,030 modules transformed.
- `node src/featureFlags.test.ts`: `Frontend feature route/navigation proof passed`.
- `node src/features/ai-rules/aiRules.test.ts`: `AI Rules route and conflict contract proof passed`.
- `npm run lint`: reports inherited debt, 156 findings (142 errors and 14 warnings). No lint cleanup or configuration weakening was included; the error count matches the documented pre-task baseline.
- Only `conciliador-financiero-dev-frontend-1` was rebuilt/recreated. API and worker container IDs remained unchanged; frontend and API gateway were healthy afterward.
- Runtime HTTP: frontend `/` 200, frontend `/dashboard/reglas-ia` 200, API `/health` 200, and Reconciliation `/v1/matching` 404.
- Runtime capabilities: `ai_rules` is enabled/implemented/usable `true/true/true`; `reconciliation` remains `false/true/false`.

### Accounting and rollback

- Authored files are `frontend/app/package.json` and this task record. `frontend/app/package-lock.json` is generated lockfile churn and is reported separately from authored additions/deletions.
- The work unit remains cohesive and below the 400-authored-line review budget; dependency constraints, generated resolution, and acceptance evidence form one rollback boundary.
- Rollback is the single `fix(deps): remediate frontend vulnerabilities` commit, restoring `frontend/app/package.json`, `frontend/app/package-lock.json`, and this task record together. No source, persisted data, service configuration, or backend/worker rollback is required.
