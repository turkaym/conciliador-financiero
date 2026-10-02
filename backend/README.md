# Backend documentary skeleton

This directory defines the planned modular backend; it contains no application code, package manifest, dependencies, or container image.

## Boundary

- **Input:** HTTP requests and CSV bytes from the future API adapter.
- **Output:** typed responses and domain events persisted by future adapters.
- **Direction:** API/application → domain ← persistence adapters.
- **Exclusions:** framework setup, ORM models, migrations, credentials, jobs, and executable services.

See [`app/`](app/README.md) for module contracts. Modules coordinate services through explicit contracts and never write another module's tables directly.
