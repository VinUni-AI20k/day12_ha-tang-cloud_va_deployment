# Day 12 Lab - Mission Answers

**Student Name:** Ho Tran Dinh Nguyen  
**Student ID:** 2A202600080  
**Date:** 17/04/2026

---

## Part 1: Localhost vs Production

### Exercise 1.1: Anti-patterns found

1. Hardcoded secrets in source code can leak immediately if the repository is pushed publicly.
2. Hardcoded host, port, debug mode, and limits make the app difficult to move between local, Docker, and cloud environments.
3. Using `print()` instead of structured logging makes debugging and monitoring harder in production.
4. Missing health and readiness endpoints means the platform cannot safely detect broken startup or unhealthy containers.
5. Keeping state only in memory breaks reliability when the app is scaled to multiple containers.

### Exercise 1.2: Result of running the basic version

The basic local version can answer simple requests, but it is not production-ready. It does not have production-safe secret handling, health checks, readiness checks, structured logging, or stateless shared storage.

### Exercise 1.3: Comparison table

| Feature | Develop | Production | Why Important? |
|---------|---------|------------|----------------|
| Config | Hardcoded values in source | Read from environment variables in `Settings` | Makes deployment safer and easier to change per environment |
| Host/Port | Fixed local values | Uses `0.0.0.0` and `PORT` | Required for Docker and Railway/Render |
| Logging | Basic console output | Structured JSON logging | Easier monitoring and debugging |
| Health checks | Usually missing | `/health` and `/ready` | Needed for orchestrators and load balancers |
| Security | Minimal or none | API key authentication with `X-API-Key` | Prevents unauthorized access |
| State | In-memory | Redis-backed shared state | Works correctly across multiple instances |
| Shutdown | Abrupt process stop | Lifespan shutdown plus SIGTERM handling | Safer deploys and less interrupted traffic |

---

## Part 2: Docker

### Exercise 2.1: Dockerfile questions

1. Base image: `python:3.11-slim`
2. Working directory: `/build` in the builder stage and `/app` in the runtime stage
3. `COPY requirements.txt` is done before source code so Docker can reuse the dependency layer when code changes but requirements do not.
4. `CMD` defines the default process for the container and is appropriate here because the app starts with a single uvicorn command.

### Exercise 2.2: Image size comparison

- Develop image: not re-measured in this final audit
- Production image: `247 MB` (`docker images day12-agent-prod`)
- Difference: the production image is under the lab requirement of `500 MB` and is reduced by using `python:3.11-slim`, a multi-stage build, and a minimal runtime image

### Exercise 2.3: Multi-stage build

- Stage 1 installs dependencies into `/build/packages`
- Stage 2 copies only installed packages and app source into the runtime image
- This reduces image size and removes unnecessary build dependencies
- The runtime container runs as non-root user `appuser`

### Exercise 2.4: Docker Compose architecture

Final stack in this repo:

```text
Client -> Nginx -> Agent -> Redis
```

- `nginx`: reverse proxy on port 80
- `agent`: FastAPI application
- `redis`: shared storage for rate limiting, cost tracking, and conversation history

---

## Part 3: Cloud Deployment

### Exercise 3.1: Railway deployment

- URL: https://day12-final-production.up.railway.app
- Platform: Railway
- Current health result verified on 17/04/2026:

```json
{"status":"ok","version":"1.0.0","environment":"production","checks":{"llm":"mock","redis":"ok"}}
```

- Screenshot to include before submission: `screenshots/dashboard.png`

### Exercise 3.2: Compare `railway.toml` vs `render.yaml`

| Feature | `railway.toml` | `render.yaml` |
|---------|----------------|---------------|
| Format | TOML | YAML |
| Health check | `healthcheckPath` | `healthCheckPath` |
| Start command | Defined in `[deploy]` | Defined in the service section |
| Restart policy | Explicit fields | Managed through Render config |
| Environment variables | Usually set in dashboard or CLI | Can be declared in `envVars` |

---

## Part 4: API Security

### Exercise 4.1: API key authentication

- API key validation is implemented in `app/auth.py`
- The expected key is read from `AGENT_API_KEY`
- Requests must include `X-API-Key`
- Missing or invalid API key returns `401`

Verified behavior on the live Railway service:

```text
POST /ask without X-API-Key -> 401
POST /ask with valid X-API-Key -> 200
```

### Exercise 4.2: JWT authentication

The final submitted repo uses API key authentication only and does not implement JWT login endpoints. If JWT were added later, the normal flow would be:

1. User authenticates and receives a token
2. Client sends `Authorization: Bearer <token>`
3. Server validates the token before allowing access

For this submission, API key authentication is the mechanism actually implemented and deployed.

### Exercise 4.3: Rate limiting

- Algorithm: sliding window
- Primary storage: Redis sorted set
- Fallback: in-memory list when Redis is unavailable
- Limit: `10 req/min` per user

Verified result on the live Railway service:

```text
[200, 200, 200, 200, 200, 200, 200, 200, 200, 200, 429, 429]
```

This confirms the first 10 requests were accepted and later requests were rate-limited.

### Exercise 4.4: Cost guard implementation

The app estimates token cost and stores monthly usage in Redis with keys like:

```text
cost:{user_id}:{YYYY-MM}
```

When the monthly budget is reached, the app returns `402`. The final app uses `MONTHLY_BUDGET_USD`, with default value `$10/month`.

---

## Part 5: Scaling & Reliability

### Exercise 5.1: Health and readiness checks

- `/health`: liveness endpoint that returns status, version, environment, uptime, and Redis health
- `/ready`: readiness endpoint that returns `503` when the app is not ready and `200` when it is ready

Verified live results:

```text
GET /health -> 200
GET /ready  -> 200
```

### Exercise 5.2: Graceful shutdown

The final app includes:

1. A FastAPI lifespan handler for startup and shutdown
2. A SIGTERM signal handler for shutdown logging
3. Redis connection cleanup during shutdown

### Exercise 5.3: Stateless design

The app avoids storing important request state only in process memory. Conversation history, rate limit data, and cost data are stored in Redis so multiple instances can share the same state.

### Exercise 5.4: Load balancing with Nginx

Nginx sits in front of the FastAPI service and forwards requests to the agent container. This is the standard pattern for scaling the application behind a reverse proxy.

### Exercise 5.5: Testing stateless behavior

A stateless design can be tested by running multiple agent instances behind Nginx and verifying that the same user still receives consistent conversation history and rate limits because Redis is shared across instances.

---

## Additional Verification

I also ran the repository self-check script in `06-lab-complete`:

```text
Production readiness check: 25/25 checks passed
```

This confirms that the final repo currently satisfies the main technical checklist for the Day 12 lab.
