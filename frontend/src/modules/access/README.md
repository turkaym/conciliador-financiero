# Access

- **Purpose:** collect credentials and establish an authenticated UI context.
- **Input/output:** email/password → session or generic error.
- **RF:** RF-01.
- **Dependency:** `POST /api/v1/auth/login`.
- **Exclusions:** registration, recovery, roles, and local credential persistence.
