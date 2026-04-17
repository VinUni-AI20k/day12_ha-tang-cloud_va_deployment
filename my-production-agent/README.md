# My Production Agent

Production-ready AI agent với đầy đủ: authentication, rate limiting, cost guard, stateless design, health checks, graceful shutdown.

## Kiến trúc

```
Client → Nginx (port 80) → Agent x3 (FastAPI) → Redis
```

## Yêu cầu

- Docker & Docker Compose

## Chạy local

```bash
# 1. Tạo file .env
cp .env.example .env
# Chỉnh AGENT_API_KEY thành giá trị bí mật của bạn

# 2. Khởi động toàn bộ stack (3 agent instances)
docker compose up --scale agent=3

# 3. Kiểm tra
curl http://localhost/health
curl http://localhost/ready
```

## Test API

```bash
# Health check
curl http://localhost/health

# Readiness check
curl http://localhost/ready

# Gọi agent (cần API key)
curl -X POST http://localhost/ask \
  -H "X-API-Key: your-secret-api-key-here" \
  -H "Content-Type: application/json" \
  -d '{"question": "Hello", "user_id": "user1"}'

# Không có key → 401
curl -X POST http://localhost/ask \
  -H "Content-Type: application/json" \
  -d '{"question": "Hello", "user_id": "user1"}'
```

## Environment Variables

| Biến | Mặc định | Mô tả |
|------|----------|-------|
| `PORT` | `8000` | Port ứng dụng |
| `REDIS_URL` | `redis://localhost:6379/0` | Kết nối Redis |
| `AGENT_API_KEY` | `secret` | API key xác thực |
| `LOG_LEVEL` | `INFO` | Mức log |
| `RATE_LIMIT_PER_MINUTE` | `10` | Giới hạn request/phút/user |
| `MONTHLY_BUDGET_USD` | `10.0` | Budget tháng/user (USD) |

## Tính năng

- **API Key Auth** — Từ chối request không có key hợp lệ (401)
- **Rate Limiting** — Sliding window, 10 req/phút/user (429 khi vượt)
- **Cost Guard** — $10/tháng/user, dùng Redis tracking (402 khi vượt)
- **Health Check** — `GET /health` — liveness probe
- **Readiness Check** — `GET /ready` — kiểm tra Redis trước khi nhận traffic
- **Graceful Shutdown** — Chờ in-flight requests xong (tối đa 30s) rồi mới tắt
- **Stateless** — Toàn bộ state (history, rate limit, budget) lưu trong Redis
- **Multi-stage Dockerfile** — Image nhỏ gọn, chạy non-root user
