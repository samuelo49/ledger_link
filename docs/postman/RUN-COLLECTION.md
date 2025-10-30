# Run the Postman Collection with Newman (CLI)

Newman is the command-line runner for Postman collections. It lets you run the Identity Service API tests locally and in CI with pass/fail output, reports, and exit codes.

## Local run

Prereqs:
- Node.js 18+
- Docker Desktop running (if you plan to use docker-compose services)

Install Newman:

```zsh
npm install -g newman
```

Start the stack (if not already):

```zsh
# In repo root
make up  # or: docker compose up -d identity-service
```

Run the collection against local env (direct service):

```zsh
newman run docs/postman/identity-service.postman_collection.json \
  -e docs/postman/identity-service.local.postman_environment.json \
  --reporters cli,junit \
  --reporter-junit-export newman-report.xml
Run the collection via the API Gateway:

```zsh
newman run docs/postman/identity-service.postman_collection.json \
  -e docs/postman/identity-gateway.local.postman_environment.json \
  --reporters cli,junit \
  --reporter-junit-export newman-report-gateway.xml
```
```

Notes:
- The collection will register a user (if not exists), login, and refresh.
- Tokens are stored in the Postman environment variables between requests.
- Exit code is non-zero if any test fails.

## CI usage (overview)

In CI, Newman can run as part of a workflow to validate the API. This repo includes a ready-to-use workflow that:
- Starts the Identity Service via docker-compose
- Waits for `/api/v1/healthz`
- Runs Newman against the local environment
- Uploads a JUnit report artifact

Workflow file:
- `.github/workflows/test-identity-postman.yml`

You can trigger it on push/PR or manually from the Actions tab.

## Tips
- To change the base URL, edit `docs/postman/identity-service.local.postman_environment.json` (the `baseUrl` var).
- For a clean register test, change the email in the "Register" request body.
- Add `--delay-request 200` if you want a slight delay between requests.
