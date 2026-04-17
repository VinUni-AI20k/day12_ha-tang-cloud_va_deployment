# Deployment Information

## Public URL
https://day12-production-08c4.up.railway.app

## Platform
Railway

## Environment Variables đã set

- `PORT`
- `REDIS_URL`
- `AGENT_API_KEY`
- `LOG_LEVEL`

## Test Commands

### Health Check
```bash
curl https://day12-production-08c4.up.railway.app/health
# Expected: {"status": "ok", "version": "1.0.0"}
```

### Readiness Check
```bash
curl https://day12-production-08c4.up.railway.app/ready
# Expected: {"status": "ready"}
```

### Không có API key → 401
```bash
curl -X POST https://day12-production-08c4.up.railway.app/ask \
  -H "Content-Type: application/json" \
  -d '{"question": "Hello", "user_id": "test"}'
# Expected: 401 Unauthorized
```

### Có API key → 200
```bash
curl -X POST https://day12-production-08c4.up.railway.app/ask \
  -H "X-API-Key: my-secret-key-2024" \
  -H "Content-Type: application/json" \
  -d '{"question": "Hello", "user_id": "test"}'
# Expected: 200 + answer
```

### Rate limiting → 429
```bash
for i in {1..15}; do
  curl -s -o /dev/null -w "%{http_code}\n" \
    -X POST https://day12-production-08c4.up.railway.app/ask \
    -H "X-API-Key: my-secret-key-2024" \
    -H "Content-Type: application/json" \
    -d '{"question": "test", "user_id": "test"}'
done
# Request 11+ trả về 429
```

## Screenshots
- [Deployment dashboard](screenshots/dashboard.png)
- [Service running](screenshots/running.png)
- [Test results](screenshots/test.png)
