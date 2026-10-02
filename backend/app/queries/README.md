# Queries

- **Purpose:** provide paginated pending, batch, proposal, reconciliation, error, and history views.
- **Input:** authenticated filters, page, and page size.
- **Output:** stable paginated read models with origin and state.
- **RF:** RF-07, RF-13; RNF-06.
- **Dependencies:** read-only query interfaces.
- **Exclusions:** domain state changes and direct ownership of persistence tables.
