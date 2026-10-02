# Pending

- **Purpose:** list valid records without an active reconciliation.
- **Input/output:** type/lote/state filters → paginated pending records and causes.
- **RF:** RF-07; RNF-06.
- **Dependency:** `GET /api/v1/pending`.
- **Exclusions:** record mutation and matching controls.
