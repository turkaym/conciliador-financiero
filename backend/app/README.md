# Application modules

These README-only folders partition the planned monolith by responsibility. They do not assert implementation.

| Module | Purpose | Main RF |
|---|---|---|
| [`access`](access/README.md) | Authentication and actor identity | RF-01 |
| [`import_catalogs`](import_catalogs/README.md) | Sources and templates | RF-02 |
| [`imports`](imports/README.md) | Batch intake and deduplication | RF-02, RF-06 |
| [`validation`](validation/README.md) | Row validation and normalization | RF-03–RF-05 |
| [`proposals`](proposals/README.md) | Automatic candidate generation and ranking | RF-08, RF-09 |
| [`reconciliation`](reconciliation/README.md) | Human decisions and reversal | RF-10–RF-12 |
| [`queries`](queries/README.md) | Pending and history reads | RF-07, RF-13 |
| [`audit`](audit/README.md) | Append-only event attribution | RF-13 |
