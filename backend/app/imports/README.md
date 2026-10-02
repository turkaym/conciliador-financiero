# Imports

- **Purpose:** receive one CSV, fingerprint its exact bytes, and control its batch lifecycle.
- **Input:** source ID, exact template ID from the catalog, record type, filename, and CSV bytes.
- **Output:** batch identity, status, totals, and structural errors.
- **RF:** RF-02, RF-06; RN-10, RN-11.
- **Dependencies:** catalogs, validation, audit, and batch repositories.
- **Exclusions:** matching, human decisions, external storage, and asynchronous queues.
