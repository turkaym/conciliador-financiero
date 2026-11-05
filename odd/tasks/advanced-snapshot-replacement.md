# Advanced Snapshot Replacement

## Objective

Replace the canonical repository application tree with a sanitized snapshot of the advanced Hugo project while preserving the canonical Git history and repository identity.

## Authorized Scope

- Source: `C:\Users\marco\Downloads\Conciliador` at its current clean `main` revision.
- Destination: `C:\Users\marco\Downloads\conciliador-financiero` on `feat/mvp-foundation-v2`.
- Replace the destination application, infrastructure, frontend, backend, database migrations, scripts, and architecture documentation with the source snapshot.
- Preserve the destination `.git` directory and this ODD task record.
- Create one reversible Conventional Commit; do not push or open a pull request.
- `size:exception` explicitly authorized by the user for this one atomic replacement commit.

## Snapshot Identity

- Source commit: `f137b5bb1ffcf94d1e18bc667f8f9b39772d0df0` on clean source branch `main`.
- Destination parent: `f68298292a211eb7357fb0e863865eae32668f87` on `feat/mvp-foundation-v2`.
- Source history is not imported; only the tracked allowlisted tree is copied.

## Mandatory Exclusions

- Source `.git` metadata and history.
- Source `.env` values.
- `tenants_data` and all tenant uploads, CSV files, certificates, and private keys.
- `node_modules`, virtual environments, caches, coverage, build output, logs, local volumes, and generated artifacts.
- Any file matching secret or credential material discovered during the pre-commit scan.

## Safety Requirements

- Generate `.env.example` from variable names only, using safe placeholders; never copy or print secret values.
- Harden `.gitignore` so excluded secrets, tenant data, certificates, uploads, caches, builds, and local tooling cannot be committed accidentally.
- Scan the staged snapshot for high-confidence secrets and sensitive file types before commit.
- Preserve source code provenance in this task record without importing unsafe source Git history.
- Do not claim the copied application is working unless verification commands actually pass.

## Applied Sanitization

- Copied only tracked paths under the approved root allowlist using `git archive HEAD`.
- Excluded source `.git`, `.env` values, `tenants_data`, uploads, financial CSVs, key/certificate material, local databases, dumps, volumes, logs, dependencies, virtual environments, caches, coverage, and generated build output.
- Generated `.env.example` from source variable names only. Secret-bearing variables are intentionally empty: `CLOUDFLARE_TOKEN`, `DB_PASSWORD`, `ENCRYPTION_KEY_MASTER`, `MINIO_ACCESS_KEY`, `MINIO_ROOT_PASSWORD`, `MINIO_ROOT_USER`, `MINIO_SECRET_KEY`, `OPENAI_API_KEY`, `PROMETEO_API_KEY`, `RABBITMQ_URL`, `SECRET_KEY`, `SMTP_PASS`, and `SMTP_USER`.
- Replaced the hard-coded Flower basic-auth default with the intentionally empty `FLOWER_BASIC_AUTH` variable.
- Removed destination-local `.atl` and `.pytest_cache` directories when present.

## Task

- [x] **SNAPSHOT-01 — Replace canonical application with sanitized advanced snapshot**
  - Route: delegated direct.
  - Trigger evidence: destructive replacement across multiple non-trivial application, infrastructure, database, and documentation paths.
  - Acceptance: destination tree matches the allowed source snapshot; mandatory exclusions are absent; canonical `.git` survives; dependencies/manifests remain coherent; snapshot is committed and reversible.
  - Checks: source/destination revision evidence, sensitive-path inventory, secret scan, Compose validation, frontend manifest validation/build where feasible, Python import/compile smoke where feasible, `git diff --check`, staged path review, and clean post-commit status.

## Delivery Context

- Parent baseline: `f682982` (`docs: add MVP demonstration guide`).
- Branch: `feat/mvp-foundation-v2`.
- Delivery strategy: stacked-to-main; this slice depends on the existing `feat/final-mvp` slice.
- Remote delivery is explicitly out of scope until the user separately authorizes push/PR operations.

## Current Next Step

The sanitized snapshot is complete. The atomic commit containing this record is the rollback boundary; its exact hash is returned externally to avoid a bookkeeping-only follow-up commit.

## Verification Evidence

- Preflight: source clean on `main`; destination at the required parent on `feat/mvp-foundation-v2`; destination remote unchanged.
- Source filename scan: no prohibited file types or runtime/generated path categories in the allowlisted tracked tree.
- Source high-confidence signature scan: no private-key blocks or recognized cloud, GitHub, OpenAI, Slack, or JWT token formats found.
- Frontend lock dry run: `npm ci --ignore-scripts --dry-run` resolved successfully.
- Staged inventory: 401 changed paths; no added, copied, or modified sensitive/runtime/generated path matched the prohibited path scan. Destination financial CSV fixtures appear only as staged deletions.
- Staged secret scan: zero high-confidence private/public key, certificate, cloud access key, GitHub token, OpenAI key, Slack token, or JWT findings. Credential-URL findings were reduced to runtime templates after committed defaults were removed.
- Manifest coherence: root `npm ci` passed; frontend `npm ci` passed without changing either lockfile.
- Compose: `docker compose config --quiet` passed using `.env.example` through an in-memory `env_file` substitution; no source `.env` was copied or created.
- Frontend build: failed in `tsc -b` on imported type/model contract errors, including missing entity, movement, receipt, and payment fields, missing module/type declarations, and incompatible component signatures. Vite did not run after TypeScript failed.
- Frontend lint: failed with 179 findings (166 errors and 13 warnings), including unsafe ref access, hook purity/ordering, explicit `any`, and unused declarations. The source manifest provides no test script.
- Verification disposition: the user explicitly renewed authorization to complete the exact snapshot replacement after these source-snapshot build and lint failures were recorded. They remain imported quality risks; no application behavior was changed to mask them. All secret-safety, path-boundary, manifest-coherence, Compose, Python structural, and Git integrity gates passed.
- Dependency audit evidence: frontend install reported 32 known vulnerabilities (2 low, 15 moderate, 15 high); no automatic audit fix was run.
- Python: `python -m compileall` passed for the copied Python roots; imports of `core.utils.enums`, `core.utils.normalizer`, and `core.utils.validators` passed. This is compile/import evidence only, not runtime health.
- Git checks: `git diff --check` and `git diff --cached --check` passed after whitespace-only normalization of imported text; the final line count is reported from the created commit.
- Repository identity: destination branch and parent remain `feat/mvp-foundation-v2` at `f68298292a211eb7357fb0e863865eae32668f87`; destination origin remains `https://github.com/turkaym/conciliador-financiero.git`.
- Source immutability: source remains clean on `main` at `f137b5bb1ffcf94d1e18bc667f8f9b39772d0df0`.
- Commit evidence: this record is included in the single authorized `size:exception` replacement commit; the exact hash is returned externally.

## Rollback Boundary

- Before commit, restore the destination worktree and index to parent `f68298292a211eb7357fb0e863865eae32668f87` while preserving this recovery record as needed.
- After commit, revert the single replacement commit to restore the complete prior application tree without affecting earlier destination history.
- The replacement commit hash will be returned after creation rather than added through a bookkeeping-only follow-up commit.
