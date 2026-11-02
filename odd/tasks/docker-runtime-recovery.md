# Docker Runtime Recovery

## Objective

Produce and verify a safe, reproducible local Docker Compose runtime for the sanitized advanced application without exposing secrets or disrupting unrelated local containers.

## Context

- Parent frontend recovery: `ac86ca4` on `fix/frontend-build-recovery`.
- Branch: `fix/docker-runtime`.
- The imported Compose configuration is structurally valid only when an untracked `.env` exists.
- Frontend production build is green; backend and full infrastructure have not been proven together.

## Authorized Scope

- Inspect and repair Compose service wiring, Dockerfiles, healthchecks, startup order, migration/bootstrap commands, development port configuration, and safe environment templates.
- Create an ignored local `.env` containing generated development-only secrets; never commit or print its values.
- Pull/build public container images and start this repository's Compose project.
- Do not stop, remove, or reconfigure unrelated containers, networks, volumes, or processes.
- Leave the project stack running only if its required services become healthy; otherwise stop only containers created by this project after collecting bounded diagnostics.

## Task

- [x] **DOCKER-01 — Restore reproducible local stack startup**
  - Route: delegated direct.
  - Trigger evidence: runtime verification spans Compose, API image, frontend service, PostgreSQL, Redis, RabbitMQ, MinIO, migrations, workers, and health boundaries.
  - Acceptance: clean configuration validation succeeds; required images build; database initialization/migrations complete; API and frontend respond; required dependencies are healthy; no real secrets are committed; unrelated Docker resources remain untouched.
  - Checks: environment inventory, Compose config/build/up, service health and bounded logs, database migration state, API health request, frontend HTTP request, source control cleanliness, and explicit teardown/recovery instructions.

## Delivery Strategy

- Stacked-to-main child of frontend build recovery.
- Infrastructure fixes and their verification/docs belong in one cohesive work unit.
- No push, pull request, or remote deployment without separate authorization.

## Current Next Step

DOCKER-01 is complete. Keep the isolated development stack running for local use, or stop it with the command below.

## RED Evidence

- Initial command: `docker compose -p conciliador-financiero-dev config --quiet`.
- Initial result: exit 1 because the referenced project `.env` did not exist; Compose also warned that required values would otherwise become empty strings.
- Initial Docker engine check: Docker Desktop was stopped. It was started without changing any container, network, or volume.
- First startup after configuration repair: `minio/minio:latest` could no longer be pulled from Docker Hub.
- First migration attempt: tenant provisioning tried to grant access to an absent `ai_readonly_role`; PostgreSQL aborted the transaction that had created `tenant_001`, and tenant Alembic then failed with `InvalidSchemaName`.
- First frontend proxy check after API recreation: nginx retained the previous Docker DNS address and returned HTTP 502 for `/api/health` while the direct API health endpoint remained HTTP 200.

## Startup Contracts

- Use the explicit project name `conciliador-financiero-dev` for every Compose command.
- Create `.env` locally from the documented names in `.env.example`; `.env` remains ignored and must not be staged.
- Required application, database, RabbitMQ, MinIO, bootstrap admin, and Flower credentials are environment-driven. The local `.env` uses generated development-only values.
- Local published ports bind to `127.0.0.1` and are configurable. PostgreSQL itself is not published; PgBouncer is the host database boundary.
- Cloudflare and Traefik are in the opt-in `edge` profile and are not part of reproducible local startup.
- `migrate` applies master migrations, creates the required PostgreSQL read-only role, provisions the development tenant synchronously, applies tenant migrations, and exits successfully before API/workers start.
- psycopg client-side prepared statements are disabled because PgBouncer uses transaction pooling and connection cleanup issues `DISCARD ALL`.
- The frontend is built once and served by nginx. `/api/*` uses Docker DNS with periodic re-resolution so API container recreation does not leave a stale upstream address.
- MinIO uses the pinned public legacy image `bitnamilegacy/minio:2025.4.22-debian-12-r1`; the removed Docker Hub `minio/minio:latest` reference is no longer used.

## GREEN Evidence

- `docker compose -p conciliador-financiero-dev config --quiet`: exit 0, no output.
- `docker compose -p conciliador-financiero-dev build`: exit 0; API, migration, four workers, Celery Beat, Flower, and frontend images built.
- `docker compose -p conciliador-financiero-dev up -d`: exit 0 after evidenced runtime repairs.
- Health summary: PostgreSQL, PgBouncer, Redis, RabbitMQ, MinIO, API, and frontend healthy; migration exited 0; Flower, Celery Beat, and four workers remained running.
- Migration state: master `ddb390c7dd2c (head)`, tenant `d7b9867a3231 (head)`, one active tenant, and 40 tenant tables.
- Idempotent bootstrap rerun: migration exited 0 and reported the existing admin/system initialization without errors.
- API direct: HTTP 200 with keys `status`, `version`, `multi_empresa`, and `rbac_enabled`.
- Frontend: HTTP 200, `text/html`, 450 bytes.
- Frontend API proxy: HTTP 200 before and after forced API container recreation.
- Redis: `PONG`. RabbitMQ diagnostics: `Ping succeeded`. MinIO readiness: HTTP 200.
- Celery inspection: four nodes online (`afip`, `accounting`, `matching`, and `ai`); all returned `pong`, with restart count 0.
- Frontend production build: `npm run build` exit 0, 2,020 modules transformed.
- `git diff --check`: exit 0.
- `git check-ignore -v .env`: `.gitignore:2:.env`; `.env` remained untracked and unstaged.
- Unrelated baseline containers `ospaat-backend` and `ospaat-db` retained their original IDs and remained running; no unrelated resource was stopped or changed.

## Local Endpoints

| Service | URL or address |
| --- | --- |
| Frontend | `http://127.0.0.1:15173` |
| API health | `http://127.0.0.1:18000/health` |
| Frontend API proxy health | `http://127.0.0.1:15173/api/health` |
| PgBouncer | `127.0.0.1:16432` |
| Redis | `127.0.0.1:16379` |
| RabbitMQ AMQP | `127.0.0.1:15672` |
| RabbitMQ management | `http://127.0.0.1:15673` |
| MinIO API | `http://127.0.0.1:19000` |
| MinIO console | `http://127.0.0.1:19001` |
| Flower | `http://127.0.0.1:15555` |

## Operations

- Start or reconcile: `docker compose -p conciliador-financiero-dev up -d`.
- Inspect status: `docker compose -p conciliador-financiero-dev ps -a`.
- Stop only this stack and preserve data: `docker compose -p conciliador-financiero-dev down`.
- Re-run bootstrap: `docker compose -p conciliador-financiero-dev run --rm migrate`.
- Rebuild after Dockerfile/dependency changes: `docker compose -p conciliador-financiero-dev build`.
- Recovery preserves named volumes. Do not add `--volumes` unless project-local data destruction is explicitly authorized.

## Remaining Risks

- The pinned MinIO image is from the Bitnami legacy catalog because the imported Docker Hub image is unavailable; plan a separately reviewed supported-image migration.
- The shared Python image is approximately 2.99 GB because the imported requirements include CPU PyTorch and sentence-transformers; image optimization is outside this recovery unit.
- `npm ci` reports existing dependency vulnerabilities and stale Browserslist data; dependency upgrades are outside this runtime repair.
- Local AI startup uses a generated development-only placeholder key. External AI calls require an authorized real key and were not exercised.

## Rollback Boundary

Revert this work-unit commit to restore the prior Compose/startup behavior. The code/config boundary is `.env.example`, `docker-compose.yml`, `traefik_dynamic.yml`, `frontend/app/Dockerfile`, `frontend/app/nginx.conf`, `config/config.py`, `init_db.py`, and `core/database/session.py`. The local `.env` and project-scoped Docker volumes are not versioned; preserve or remove them only through an explicit local-data decision.
