# Deployment Information

**Student:** Ho Dac Toan — 2A202600057  
**Date:** 17/04/2026

---

## Public URL

```
https://toanhd-production.up.railway.app
```

## Platform

**Railway** — Dockerfile builder, region: us-west1

---

## Test Commands

### Health Check (Liveness Probe)
```bash
curl https://toanhd-production.up.railway.app/health
```
Expected:
```json
{"status":"ok","version":"1.0.0","environment":"development","uptime_seconds":16.3,"storage":"redis"}
```

### 401 — No API Key
```bash
curl -X POST https://toanhd-production.up.railway.app/ask \
  -H "Content-Type: application/json" \
  -d '{"user_id":"test","question":"Hello"}'
```
Expected: `{"detail":"Missing or invalid API key..."}`

### 200 — With API Key
```bash
curl -X POST https://toanhd-production.up.railway.app/ask \
  -H "X-API-Key: 10052004" \
  -H "Content-Type: application/json" \
  -d '{"user_id":"alice","question":"Hello from cloud!"}'
```
Expected:
```json
{
  "user_id": "alice",
  "question": "Hello from cloud!",
  "answer": "...",
  "history_count": 1,
  "model": "mock",
  "timestamp": "2026-04-17T04:27:25.071673+00:00"
}
```

### 429 — Rate Limit (call 11+ times)
```bash
for i in {1..12}; do
  curl -s -X POST https://toanhd-production.up.railway.app/ask \
    -H "X-API-Key: 10052004" \
    -H "Content-Type: application/json" \
    -d '{"user_id":"ratelimit-test","question":"test"}' | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('answer','RATE LIMITED: '+str(d)))"
done
```
Expected: requests 1–10 return answers, request 11+ returns `{"detail":{"error":"Rate limit exceeded",...}}`

---

## Environment Variables Set on Railway

| Variable | Value |
|----------|-------|
| `AGENT_API_KEY` | `10052004` |
| `REDIS_URL` | `redis://default:***@redis.railway.internal:6379` |
| `PORT` | injected by Railway |
| `ENVIRONMENT` | `development` |
| `LOG_LEVEL` | `INFO` |
| `RATE_LIMIT_PER_MINUTE` | `10` |
| `MONTHLY_BUDGET_USD` | `10.0` |

---

## Architecture

```
Internet
    │
    ▼
Railway Platform (us-west1)
    │
    ▼ HTTPS
┌─────────────────────────────────┐      ┌──────────────────────────────┐
│  AI Agent — FastAPI + uvicorn   │      │  Redis (railway.internal)    │
│  Port: $PORT (Railway injected) │ ───► │  Conversation history        │
│                                 │      │  Cost guard budget           │
│  POST /ask   → auth → rate →   │      │  (private network)           │
│               budget → LLM     │      └──────────────────────────────┘
│  GET  /health → liveness        │
│  GET  /ready  → readiness       │
└─────────────────────────────────┘
```
