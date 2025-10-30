# Postman — Identity Service

This folder contains a ready-to-import Postman collection and environment for the Identity Service.

- identity-service.postman_collection.json — requests for Health, Register, Token, Refresh
- identity-service.local.postman_environment.json — environment for direct service (http://localhost:8001/api/v1)
- identity-gateway.local.postman_environment.json — environment for gateway-hosted tests (http://localhost:8080/api/v1)
- identity-service-extended.postman_collection.json — adds Me, Verification, Password Reset, Lockout demo
- identity-service-extended.local.postman_environment.json — adds email/password variables used by extended flows

For CLI/CI usage, see: `RUN-COLLECTION.md`

## How to use

1) Open Postman → Import → Select the two JSON files.
2) Choose an environment:
   - "Identity Service (Local)" to hit the service directly
   - "Identity via Gateway (Local)" to go through the API Gateway
3) Run the requests in order:
   - Health
   - Auth / Register (once per email)
   - Auth / Token (captures access/refresh into environment variables)
   - Auth / Refresh (uses refresh_token from environment)
   - Optional: Auth / Me (requires Authorization: Bearer)
   - Optional flows: Verification, Password Reset, and Lockout Demo (using the extended collection)

Tip: The collection auto-sets `access_token` and `refresh_token` into the environment after successful login/refresh.

Base URL defaults to `http://localhost:8001/api/v1` (see docker-compose port mapping).
