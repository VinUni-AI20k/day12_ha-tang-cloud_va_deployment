# Deployment Information

## Public URL
https://day12-final-production.up.railway.app

## Platform
Railway (Nixpacks builder, auto-detect Python)

## Test Commands

### Health Check
```bash
curl https://day12-final-production.up.railway.app/health
# Expected: {"status":"ok","version":"1.0.0","environment":"development",...}
```

### Readiness Check
```bash
curl https://day12-final-production.up.railway.app/ready
# Expected: {"ready":true}
```

### Authentication Required
```bash
curl -X POST https://day12-final-production.up.railway.app/ask \
  -H "Content-Type: application/json" \
  -d '{"question": "Hello"}'
# Expected: 401 {"detail":"Invalid or missing API key..."}
```

### API Test (with authentication)
```bash
curl -X POST https://day12-final-production.up.railway.app/ask \
  -H "X-API-Key: day12-secret-key-2026" \
  -H "Content-Type: application/json" \
  -d '{"question": "Hello from production!"}'
# Expected: 200 {"question":"...","answer":"...","model":"gpt-4o-mini","timestamp":"..."}
```

### Rate Limiting Test
```bash
for i in {1..15}; do
  curl -s -o /dev/null -w "Request $i: HTTP %{http_code}\n" \
    -X POST https://day12-final-production.up.railway.app/ask \
    -H "X-API-Key: day12-secret-key-2026" \
    -H "Content-Type: application/json" \
    -d '{"question": "test"}'
done
# Expected: 200 for first 10, then 429 Too Many Requests
```

## Environment Variables Set on Railway
- `AGENT_API_KEY` — API key để xác thực
- `PORT` — Inject tự động bởi Railway

## Features Implemented
- API Key authentication (X-API-Key header)
- Rate limiting (10 req/min per key)
- Cost guard (daily budget tracking)
- Health check endpoint (/health)
- Readiness check endpoint (/ready)
- Graceful shutdown (SIGTERM handler)
- Structured JSON logging
- No hardcoded secrets

## Railway Project
- Project ID: 8d621142-5838-4aab-b005-99c6b9c32f8d
- Dashboard: https://railway.com/project/8d621142-5838-4aab-b005-99c6b9c32f8d
