# Recovery: Reconciliation MVP

## Objective

Restore the approved reconciliation MVP exactly as required by the professor while preserving the repository's complete history for review.

## Recovery Boundary

- Immutable source commit: `f68298292a211eb7357fb0e863865eae32668f87` (`docs: add MVP demonstration guide`).
- Replacement commit: `18bd2b00a198ca1fea6c7e9851af264b7eb9edc8` (`feat(platform): import sanitized advanced application`).
- Authorized boundary: recover the whole tracked project tree from the immutable source commit, with this recovery record as the only additional path.
- Explicitly authorized CI exception: preserve `.github/workflows/quality-gates.yml` as an MVP-compatible workflow so the protected `main` branch receives its required checks. This is the only exception to exact recovered-tree identity and does not restore any advanced-platform behavior.
- Farid owns this recovery commit.
- Hugo reviews this recovery commit and later owns the backend critical-rule work.

## Checklist

- [x] Restore the historical tree exactly.
- [x] Verify the recovered structure and tree integrity.
- [x] Execute the restored backend and frontend test suites: 35 backend tests and 13 frontend tests pass; the frontend production build also passes.
- [x] Preserve compatible quality gates for the restored `backend/` and `frontend/` layout with the exact required check names.
- [x] Validate the database schema and project documentation structurally; PostgreSQL runtime validation remains pending while Docker Desktop is unavailable.
- [ ] Validate the demonstration PDF.
- [ ] Validate deployment configuration and runtime behavior.
- [ ] Rebuild the final README presentation reference with a direct video file URL.

## Exclusions

- No history rewrite, rebase, squash, or branch reset.
- No access to or modification of `.env`, local credentials, or Docker data.
- No modification of Docker volumes or services.
- No salvage of advanced-platform features in this recovery commit.
- No use of obsolete advanced-platform paths or commands in the preserved quality gates.

## Rollback

Revert this recovery commit.

## Current Next Step

Open the recovery pull request for Hugo's review, then add the missing professor-required backend proof on Hugo's dedicated branch: competing 1:1 proposals, blank rejection reasons, duplicate file imports, and duplicate receipt rows.

## Verification Evidence

- `python -c "import pathlib, yaml; ..."`: `.github/workflows/quality-gates.yml` parsed successfully.
- `backend\.venv\Scripts\python.exe -m pytest backend/tests`: 35 passed with one upstream Starlette `httpx` deprecation warning.
- `npm test` from `frontend`: 13 passed across three test files in non-watch mode.
- `npm run build` from `frontend`: production build passed.
- `.github/workflows/quality-gates.yml`: triggers for every pull request and pushes to `main`; routes frontend validation through `frontend/` and backend validation through `backend/pyproject.toml` from the repository root.
- Required check routes: `Frontend quality` runs `npm ci`, `npm test`, and `npm run build`; `Backend and governance` installs `backend[test]` and runs `python -m pytest backend/tests`.
- `render.yaml`: valid YAML with one database and two web services.
- Recovery tree: identical to `f68298292a211eb7357fb0e863865eae32668f87`, excluding this recovery record and the explicitly authorized MVP-compatible quality-gates workflow.
- Environment limitation: Docker Desktop was stopped, so PostgreSQL locks, triggers, and deployment runtime were not executed.
