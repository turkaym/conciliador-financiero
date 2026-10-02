# Audit

- **Purpose:** append attributable events in the same transaction as domain facts.
- **Input:** event type, one target, actor when human, reason when required, and JSON data.
- **Output:** immutable chronological event.
- **RF:** RF-11–RF-13; RNF-03.
- **Dependencies:** event repository and transaction context.
- **Exclusions:** replacing operational entities, event mutation, and analytics.
