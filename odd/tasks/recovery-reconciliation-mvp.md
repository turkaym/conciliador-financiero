# Recovery: Reconciliation MVP

## Objective

Restore the approved reconciliation MVP exactly as required by the professor while preserving the repository's complete history for review.

## Recovery Boundary

- Immutable source commit: `f68298292a211eb7357fb0e863865eae32668f87` (`docs: add MVP demonstration guide`).
- Replacement commit: `18bd2b00a198ca1fea6c7e9851af264b7eb9edc8` (`feat(platform): import sanitized advanced application`).
- Authorized boundary: recover the whole tracked project tree from the immutable source commit, with this recovery record as the only additional path.
- Farid owns this recovery commit.
- Hugo reviews this recovery commit and later owns the backend critical-rule work.

## Checklist

- [x] Restore the historical tree exactly.
- [x] Verify the recovered structure and tree integrity.
- [x] Execute the restored backend and frontend test suites: 35 backend tests and 13 frontend tests pass; the frontend production build also passes.
- [x] Validate the database schema and project documentation structurally; PostgreSQL runtime validation remains pending while Docker Desktop is unavailable.
- [ ] Validate the demonstration PDF.
- [ ] Validate deployment configuration and runtime behavior.
- [ ] Rebuild the final README presentation reference with a direct video file URL.

## Exclusions

- No history rewrite, rebase, squash, or branch reset.
- No access to or modification of `.env`, local credentials, or Docker data.
- No modification of Docker volumes or services.
- No salvage of advanced-platform features in this recovery commit.

## Rollback

Revert this recovery commit.

## Current Next Step

Open the recovery pull request for Hugo's review, then add the missing professor-required backend proof on Hugo's dedicated branch: competing 1:1 proposals, blank rejection reasons, duplicate file imports, and duplicate receipt rows.

## Verification Evidence

- `backend\.venv\Scripts\python.exe -m pytest backend/tests -vv`: 35 passed.
- `npm test` from `frontend`: 13 passed across three test files.
- `npm run build` from `frontend`: passed.
- `render.yaml`: valid YAML with one database and two web services.
- Recovery tree: clean and identical to `f68298292a211eb7357fb0e863865eae32668f87`, excluding this recovery record.
- Environment limitation: Docker Desktop was stopped, so PostgreSQL locks, triggers, and deployment runtime were not executed.
