# Frontend documentary skeleton

This directory documents the planned UI feature boundaries. It contains no React code, package manifest, dependencies, build output, or container image.

## Boundary

- **Input:** user actions and `/api/v1` responses.
- **Output:** accessible views and explicit commands to the API.
- **Dependency:** modules depend on the API contract, never on database structures.
- **Exclusions:** application bootstrap, state library, styling system, and executable tests.

See [`src/modules/`](src/modules/) and the [wireframes](../docs/segunda-entrega/wireframes/README.md).
