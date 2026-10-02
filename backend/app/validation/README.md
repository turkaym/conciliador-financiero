# Validation

- **Purpose:** validate structure/rows, preserve originals, and produce typed eligible records.
- **Input:** resolved template and parsed CSV rows.
- **Output:** pending records or field/lote errors with stable duplicate keys.
- **RF:** RF-03–RF-06; RN-10, RN-11.
- **Dependencies:** template definitions and record/error repositories.
- **Exclusions:** changing original values, fuzzy correction, and proposal generation.
