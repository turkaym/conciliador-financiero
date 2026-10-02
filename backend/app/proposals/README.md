# Proposals

- **Purpose:** automatically generate and rank eligible movement–receipt pairs after a successful batch.
- **Input:** newly eligible records plus all opposite historical pending records.
- **Output:** versioned generated proposals with score components and explanation.
- **RF:** RF-08, RF-09; RN-01, RN-03, RN-04, RN-07.
- **Dependencies:** pending-record, active-reconciliation, and proposal repositories; both records are locked by ascending ID before generation.
- **Exclusions:** public manual generation, automatic confirmation, and rejected-proposal reopening.
