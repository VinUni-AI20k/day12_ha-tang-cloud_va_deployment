# Deployment Information

## Public URL
https://day12-final-production.up.railway.app

## Platform
Railway

## Test Commands

### Health Check
```bash
curl https://day12-final-production.up.railway.app/health
```

### Readiness Check
```bash
curl https://day12-final-production.up.railway.app/ready
```

### Authentication Required
```bash
curl -X POST https://day12-final-production.up.railway.app/ask \
  -H "Content-Type: application/json" \
  -d '{"user_id":"test","question":"Hello"}'
```

### API Test
```bash
curl -X POST https://day12-final-production.up.railway.app/ask \
  -H "X-API-Key: YOUR_DEPLOYED_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"user_id":"demo","question":"Hello from production!"}'
```

### Rate Limiting Test
```bash
for i in {1..15}; do
  curl -s -o /dev/null -w "Request $i: HTTP %{http_code}\n" \
    -X POST https://day12-final-production.up.railway.app/ask \
    -H "X-API-Key: YOUR_DEPLOYED_API_KEY" \
    -H "Content-Type: application/json" \
    -d '{"user_id":"ratetest","question":"test"}'
done
```

## Environment Variables Set
- `PORT`
- `REDIS_URL`
- `AGENT_API_KEY`
- `JWT_SECRET`
- `MONTHLY_BUDGET_USD`
- `LOG_LEVEL`

## Screenshots
- [Deployment dashboard](screenshots/dashboard.png)
- [Service running](screenshots/running.png)
- [Test results](screenshots/test.png)

## Notes
- This file intentionally uses placeholders instead of real secrets.
