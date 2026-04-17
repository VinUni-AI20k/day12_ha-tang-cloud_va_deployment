# Lab 12 - Complete Production Agent

Project tổng hợp các yêu cầu production cho Day 12: auth, rate limit, cost guard, Docker, Redis, readiness check, và deploy.

## Checklist Deliverable

- [x] Dockerfile multi-stage
- [x] `docker-compose.yml` cho agent + Redis + nginx
- [x] `.dockerignore`
- [x] `GET /health`
- [x] `GET /ready`
- [x] API key authentication
- [x] Rate limiting `10 req/min`
- [x] Cost guard `$10/month`
- [x] Config từ environment variables
- [x] Structured logging
- [x] Graceful shutdown
- [x] Railway / Render config

## Structure

```text
my-production-agent/
|-- app/
|   |-- main.py
|   |-- config.py
|   |-- auth.py
|   |-- rate_limiter.py
|   `-- cost_guard.py
|-- utils/
|   `-- mock_llm.py
|-- Dockerfile
|-- docker-compose.yml
|-- railway.toml
|-- render.yaml
|-- .env.example
|-- .dockerignore
|-- requirements.txt
`-- check_production_ready.py
```

## Run Local

```bash
cp .env.example .env.local
docker compose up --build
curl http://localhost/health
```

Authenticated request:

```bash
curl -X POST http://localhost/ask \
  -H "X-API-Key: YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"user_id":"demo","question":"What is deployment?"}'
```

## Deploy

Railway:

```bash
railway login
railway init
railway variables set AGENT_API_KEY=your-secret-key
railway variables set JWT_SECRET=your-jwt-secret
railway variables set MONTHLY_BUDGET_USD=10
railway up
```

Render:

1. Push repo lên GitHub.
2. Create service from `render.yaml`.
3. Set secrets `AGENT_API_KEY`, `JWT_SECRET`, `MONTHLY_BUDGET_USD`.
4. Deploy and test `GET /health`, `GET /ready`, `POST /ask`.

## Production Check

```bash
python check_production_ready.py
```
