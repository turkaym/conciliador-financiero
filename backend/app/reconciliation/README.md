# Reconciliation

- **Purpose:** confirm/reject proposals and reverse active reconciliations atomically.
- **Input:** proposal or reconciliation ID, authenticated actor, and required reason.
- **Output:** terminal proposal decision or active/reverted reconciliation with audit data.
- **RF:** RF-10–RF-12; RN-02, RN-05–RN-09, RN-12.
- **Dependencies:** proposal, reconciliation, record, and audit repositories; it uses the same ascending record-lock order as proposal generation.
- **Exclusions:** automatic confirmation, deletion of history, and manual reopening.
