# CONCILIADOR - Financial and Accounting Reconciliation Platform

Academic proposal for the **Final Project** course in the **University Technical Degree in Programming (UTN)**. The first submission, approved without observations, provides the background for the problem, validation strategy, scope, and initial technical proposal.

**Current status:** the MVP is implemented and deployed to Render. Remote login, both CSV imports, proposal generation, proposal confirmation, and history recording have been verified. Reversal smoke verification remains pending. This documentation translation covers only the allowed files listed in the delivery request; other academic documents remain in Spanish.

### Public deployment

- Frontend: https://conciliador-frontend-8djd.onrender.com
- API: https://conciliador-api-bym3.onrender.com
- Render Blueprint: `conciliador-financiero-mvp`
- Demo credentials: `demo@conciliador.local` / `Demo1234!` (fictional credentials for demonstration only; change or remove them before using real data).

The remote smoke test verified login, both valid CSV fixtures with 3/3 valid rows, pending records, three proposals, Proposal #1 confirmation, and the `PROPUESTA_CONFIRMADA` history event. Remote reversal verification is still pending, so MVP-11 remains open.

## Team and availability

| Member | GitHub user | Planned primary role |
|---|---|---|
| Hugo Tcach | `HugoTcach` | Backend, database, and local infrastructure |
| Farid Salomón | `turkaym` | Functional analysis, frontend, documentation, and quality |

Joint availability is approximately **10 hours per week**. Both members will participate in discovery, change review, testing, and presentation. Cross-training is planned so that no area depends on a single person.

## Problem and initial hypothesis

Companies and accounting firms may receive bank transactions and records or receipts from separate sources. Reconciliation requires relating those data, detecting differences, and retaining evidence of decisions.

The initial hypothesis is that manual comparisons and disconnected tools can create repetitive work, difficulty identifying pending items, and limited traceability of why two records were matched or discarded. **This hypothesis has not yet been validated through interviews or metrics.**

### Actors and needs to validate

| Actor | Participation in the flow | Proposed need |
|---|---|---|
| Administrative or accounting staff | Gather sources, compare records, and resolve differences | Reduce repetitive comparisons without losing control over decisions |
| Process owner | Monitor status and review exceptions | Identify pending items and reconstruct decisions |
| Company or accounting firm | Define criteria and retain documentation | Maintain a consistent and traceable process |

### Assumed current flow

1. Obtain bank transactions and records or receipts from separate sources.
2. Review formats and normalize data when necessary.
3. Compare amount, date, and references to find matches.
4. Investigate differences and decide which items match.
5. Record results and leave unresolved cases pending.

This flow is an initial representation that will be validated and corrected during discovery.

### Digitization and added value

Digitization would move the comparison to a screen without changing the process. The proposal aims to add value by assisting comparison with explainable rules, highlighting exceptions, preserving human review, and recording basic traceability. This value is not assumed to be proven; it will be evaluated with actors and workflow tests.

### Formal statement

**Project question:** How can reconciliation between bank transactions and records or receipts be assisted to reduce repetitive review and make differences visible, without replacing human decisions and while preserving basic traceability?

## Validation strategy

No users, results, or measurements are available at this stage. The following activities are proposed to validate relevance:

1. Identify people who perform or supervise reconciliation in companies or accounting firms.
2. Conduct semi-structured interviews about sources, steps, exceptions, frequency, and process difficulties.
3. Observe anonymized examples or representative fictional data without requesting sensitive financial information.
4. Document the actual flow and compare it with the initial hypothesis and actors.
5. Test a workflow prototype with test data and record understanding, perceived usefulness, errors, and requested changes.
6. Revisit scope if the problem is not recurrent, relevant, or compatible with the course schedule.

Relevance will be considered supported when discovery confirms the need to relate separate sources, resolve exceptions, and preserve traceability, and when the proposed flow can be evaluated with representative cases. Metrics and quantitative criteria will be defined after discovery, not before.

## Value proposition and existing alternatives

The proposal is a tool focused on reconciliation between two sources, with visible matching rules, human review, and decision traceability.

| Alternative category | Typical contribution | Differentiation to evaluate |
|---|---|---|
| Spreadsheets | Flexibility and immediate access | Guide the flow, show pending items, and record decisions consistently |
| Isolated banking portals | Transaction lookup for one institution | Relate transactions to external records in one flow |
| General accounting systems or ERPs | Broad administrative-process coverage | Focus on a minimal, explainable, reviewable reconciliation experience |

The differentiation is a proposal to validate and does not imply demonstrated superiority over these categories.

## Prioritized scope

### Essential MVP

- Manual upload of two test-data sets: bank transactions and records or receipts.
- Validation of structure and required fields.
- Matching proposals based on amount, date, and reference.
- Manual review to confirm or reject proposals.
- Display of pending items.
- Basic traceability of data origin and decisions.

### Nice to have

- Approximate reference search with `pg_trgm`.
- Asynchronous import for large files.
- Basic dashboard.
- Result export.
- Deployment on a PaaS platform.

### Out of scope

- Artificial intelligence and predictive models.
- OCR.
- Production integration with AFIP.
- Real banking integrations.
- Kubernetes and self-managed servers.
- Multi-tenancy.
- Monetization or SaaS model.
- Advanced analytics.

## Initial technical proposal

### Planned MVP stack

| Area | Technologies | Selection criterion |
|---|---|---|
| Frontend | TypeScript, React, and Vite | Typing, mature ecosystem, extensive documentation, and transferable learning |
| Backend | Python, FastAPI, and Pydantic | Focused API, explicit validation, and broad community |
| Persistence | SQLAlchemy and Alembic | Structured access and controlled schema evolution |
| Database | PostgreSQL | Relational integrity, transactions, and traceability |
| Collaboration | Git and GitHub | Version control and joint review |
| Local environment | Docker Compose | Reproducible environment without making infrastructure the project goal |

The choice considers the problem, the academic scale of the MVP, tool maturity, the development environment, and learning cost. A small, stable stack supported by active documentation and communities is preferred. Keeping these technologies throughout the project focuses effort on the problem and avoids unnecessary training, integration, and testing costs caused by a stack change.

### Relational database versus NoSQL

Reconciliation relates transactions, records, proposals, decisions, and pending states. PostgreSQL suits this case through consistency, referential integrity, and transactional support. A NoSQL database could suit highly variable data or different scaling patterns, but those needs are not justified for the MVP. The decision will be revisited if discovery finds requirements incompatible with the relational model.

### Deployment alternatives

- **Initial development:** reproducible local execution through Docker Compose.
- **Later alternative:** PaaS, if a demonstration needs to be published with less operational overhead.
- **Initially out of scope:** self-managed servers and Kubernetes, because they add complexity without validating the core problem.

## Work plan

The sequence will be adjusted to the final course schedule and discovery findings.

| Sequence | Stage | Owners | Factual status | Planned deliverable |
|---:|---|---|---|---|
| 1 | Discovery and validation | Hugo and Farid | **Not started** | Interviews, reviewed flow, and prioritized needs |
| 2 | Formats and design | Hugo and Farid | **Documented** | Fictional formats, relational model, rules, and wireframes |
| 3 | Workflow prototype | Hugo and Farid | **Not started** | Executable MVP flow with agreed test data |
| 4 | Product verification | Hugo and Farid | **Not started** | Functional cases, technical tests, and limitations |
| 5 | Presentation | Hugo and Farid | **Not started** | Demonstration and final documentation |

Each stage reserves time for learning, integration, and joint review. No nice-to-have item will be added while an essential MVP completion criterion is missing.

## Feasibility

| Dimension | Initial assessment | Planned measure |
|---|---|---|
| Technical | The flow can be solved with explicit rules and mature technologies suitable for MVP scale | Build in stages, use test data, and validate the minimum flow first |
| Schedule | Joint availability is approximately 10 hours per week | Prioritize the MVP, limit parallel work, and adjust estimates to the final course schedule |
| Operational | The system requires clear formats and human participation to resolve exceptions | Validate the flow with actors and keep rules and states understandable |
| Knowledge | The team's academic background provides a common foundation, and the selected stack has broad documentation and communities | Organize cross-training, joint reviews, and decision documentation |

Feasibility will be reassessed after discovery and each stage. If the required time or learning exceeds expectations, scope will be reduced before adding infrastructure or secondary features.

## Repository

Project code and documentation: [github.com/turkaym/conciliador-financiero](https://github.com/turkaym/conciliador-financiero)

## Documentation

- [Second delivery: index and review path](docs/segunda-entrega/README.md)
- [API contract `/api/v1`](docs/segunda-entrega/09-contrato-api.md)
- [CSV templates and fixtures](docs/segunda-entrega/csv/README.md)
- [MVP wireframes](docs/segunda-entrega/wireframes/README.md)
- [Backend skeleton](backend/README.md), [frontend skeleton](frontend/README.md), and [PostgreSQL schema](database/README.md)

## Local execution

1. Copy `.env.example` to `.env` and define a local `JWT_SECRET_KEY`.
2. Run `docker compose up --wait` from the root. On a new volume, Compose runs `database/schema.sql` and `database/seed.sql` once.
3. Install the backend with `backend\\.venv\\Scripts\\python.exe -m pip install -e backend[test]`.
4. Start the API with `backend\\.venv\\Scripts\\python.exe -m uvicorn app.main:app --app-dir backend --reload`.
5. Start the frontend with `npm install && npm run dev` from `frontend/`.

The local application uses `http://localhost:8000` as the API and `http://localhost:5173` as the default allowed origin. The demo user is `demo@conciliador.local` / `Demo1234!`; these are fictional development credentials and must not be reused in a public environment.

## Render deployment

`render.yaml` defines a Blueprint with a managed PostgreSQL database, a FastAPI web service, and a Vite static site. The Blueprint generates `JWT_SECRET_KEY` and references the PostgreSQL connection; it contains no secrets. The deployed Blueprint is `conciliador-financiero-mvp`.

1. In Render, connect the repository and select the `render.yaml` Blueprint.
2. In `conciliador-api`, set `CORS_ORIGINS` to the final static-site URL, such as `https://<frontend>.onrender.com`.
3. In `conciliador-frontend`, set `VITE_API_BASE_URL` to the final web-service URL, such as `https://<api>.onrender.com`.
4. Save the changes and redeploy the frontend after configuring `VITE_API_BASE_URL`, because Vite embeds this variable during the build.

The backend start command runs `app.initialize_database`: it acquires a transactional lock, creates the schema only when `public.usuario` is missing, and runs the deterministic idempotent seed on every start. It does not perform a destructive reset. Render injects `PORT`, Uvicorn listens on `0.0.0.0`, and `/health` is the health check.

### Credentials and required variables

- `DATABASE_URL`: the Blueprint reference to the managed database.
- `JWT_SECRET_KEY`: generated by Render; never add it to the repository.
- `CORS_ORIGINS`: exact public frontend URL, without a trailing slash.
- `VITE_API_BASE_URL`: exact public API URL, without a trailing slash.
- `DATABASE_SCHEMA_PATH` and `DATABASE_SEED_PATH`: versioned paths used by the initializer.

The seed creates or reactivates the demo user and catalogs. For a public demonstration, change the documented credentials or remove the demo user through a secure procedure before using real data.

### Post-deployment smoke test

Verify from an authorized machine:

1. `curl -fsS https://<api>.onrender.com/health` returns `{"status":"healthy"}`.
2. The public frontend loads without asset or console errors.
3. Login with the configured demo credentials receives a token.
4. Upload both CSVs from `docs/segunda-entrega/csv/fixtures/`, inspect errors and pending records, and verify a proposal.
5. Confirm a proposal, inspect history, reverse the reconciliation, and verify that both records return to pending.
6. Restart or redeploy the backend and confirm that the seed does not duplicate catalogs or reset data.

MVP-11 is deployed, but it is not complete until the reversal step in this remote smoke test is verified explicitly.
