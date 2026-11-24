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
- [ ] Execute the restored backend and frontend test suites in a later work unit.
- [ ] Validate the database schema and project documentation.
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

Execute the restored historical test suites after the exact tree restore is committed.
