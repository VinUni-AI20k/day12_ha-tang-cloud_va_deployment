# Deployment Information — Day 12

**Student Name:** Nguyễn Tri Nhân  
**Student ID:** 2A202600224  
**Date:** 17/04/2026

## Public URL

https://day12-06-production.up.railway.app

## Platform

Railway (Dockerfile-based deployment)

- Config: `06-lab-complete/railway.toml`
- Runtime: Docker container (Uvicorn + FastAPI)

## Test Commands

### Health check

```bash
curl https://day12-06-production.up.railway.app/health
```

### Root info

```bash
curl https://day12-06-production.up.railway.app/
```

### API test (requires authentication)

```bash
API_KEY="<YOUR_AGENT_API_KEY>"

curl -X POST 'https://day12-06-production.up.railway.app/ask' \
  -H "accept: application/json" \
  -H "X-API-Key: ${API_KEY}" \
  -H "Content-Type: application/json" \
  -d '{"question":"chào bạn","user_id":"anonymous"}'
```

## Environment Variables (set on Railway)

- `AGENT_API_KEY` (required)
- `ENVIRONMENT=production` (recommended)
- `DASHSCOPE_API_KEY` (optional; if missing the app may fall back to mock depending on build)
- `DASHSCOPE_ENDPOINT`
- `QWEN_MODEL`
- `JWT_SECRET`
- `RATE_LIMIT_PER_MINUTE`
- `DAILY_BUDGET_USD`
- `REDIS_URL` (optional; if unset, Redis features may be disabled)

Notes:
- `PORT` is injected automatically by Railway.

## Screenshots

Place your screenshots under `screenshots/`:

- `screenshots/railway-dashboard.png` — Railway deployment dashboard
- `screenshots/service-running.png` — Service status running
- `screenshots/curl-test.png` — terminal output showing `/health` and `/ask`
