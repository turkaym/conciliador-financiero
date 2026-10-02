# Access

- **Purpose:** authenticate pre-registered users and provide actor identity.
- **Input:** email and password.
- **Output:** authenticated session/token context or a generic denial.
- **RF:** RF-01, RNF-04.
- **Dependencies:** user repository and password verifier interfaces.
- **Exclusions:** registration, password recovery, role administration, and user management.
