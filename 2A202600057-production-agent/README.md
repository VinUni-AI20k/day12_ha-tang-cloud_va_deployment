
---

## 🎓 Final Project — Ho Dac Toan (2A202600057)

Production-ready AI Agent kết hợp tất cả Day 12 concepts.

**Public URL:** `https://toanhd-production.up.railway.app`

### Setup Local

```bash
# 1. Clone repo
git clone https://github.com/dactoan12345/lab12_HoDacToan_2A202600057
cd lab12_HoDacToan_2A202600057

# 2. Tạo file env
cp .env.example .env.local
# Mở .env.local và set AGENT_API_KEY

# 3. Chạy với Docker Compose (agent + redis + nginx)
docker compose up

# Test tại http://localhost/health
```

### Setup Local (không Docker)

```bash
pip install -r requirements.txt
export AGENT_API_KEY=your-key   # Windows: $env:AGENT_API_KEY="your-key"
python -m app.main
# Server chạy tại http://localhost:8000
```

### Test API

```bash
# Health check
curl http://localhost/health

# Cần API key → 401
curl -X POST http://localhost/ask \
  -H "Content-Type: application/json" \
  -d '{"user_id":"alice","question":"Hello"}'

# Có API key → 200
curl -X POST http://localhost/ask \
  -H "X-API-Key: your-key" \
  -H "Content-Type: application/json" \
  -d '{"user_id":"alice","question":"Hello"}'
```

### Deploy Lên Railway Project Mới

> Nếu deploy sang Railway project khác (hoặc account khác), cần làm thêm bước kết nối Redis vì Railway **không đọc** `docker-compose.yml` — env vars phải set thủ công trên platform.

**Bước 1 — Deploy agent:**
```bash
cd 2A202600057-production-agent
railway login
railway init          # tạo project mới, đặt tên tuỳ ý
railway up
```

**Bước 2 — Thêm Redis service:**
```bash
railway add --database redis
# Railway tạo Redis container và tự sinh REDIS_URL, REDISPASSWORD, v.v.
```

**Bước 3 — Lấy REDIS_URL từ Redis service:**
```bash
railway service Redis       # switch sang Redis service
railway variables --json    # tìm field "REDIS_URL"
# Ví dụ: redis://default:somepassword@redis.railway.internal:6379
```

**Bước 4 — Set REDIS_URL cho agent service:**
```bash
railway service <tên-agent>   # switch về agent service
railway variables set REDIS_URL="redis://default:<password>@redis.railway.internal:6379"
```

**Bước 5 — Set các env vars còn lại:**
```bash
railway variables set AGENT_API_KEY="your-secret-key"
railway variables set ENVIRONMENT="production"
railway variables set LOG_LEVEL="INFO"
railway variables set RATE_LIMIT_PER_MINUTE="10"
railway variables set MONTHLY_BUDGET_USD="10.0"
```

**Bước 6 — Redeploy để nhận env vars mới:**
```bash
railway up
```

**Kiểm tra kết quả:**
```bash
# /health phải trả "storage":"redis" (không phải "memory")
curl https://your-new-app.railway.app/health
```

> Sau khi set xong, mọi lần `railway up` tiếp theo **không cần set lại** — Railway giữ env vars vĩnh viễn trên project đó.

---

### Architecture

```
┌─────────┐   HTTPS    ┌───────────────────┐   proxy    ┌─────────────────────────┐   TCP    ┌─────────────────────┐
│ Client  │ ─────────► │  Nginx (port 80)  │ ─────────► │  FastAPI Agent (:8000)  │ ───────► │  Redis (port 6379)  │
│ Browser │            │  Load Balancer    │            │                         │          │  conversation       │
│  curl   │            │  SSL termination  │            │  POST /ask              │          │  history per        │
└─────────┘            └───────────────────┘            │    → verify_api_key     │          │  user_id            │
                                                        │    → check_rate_limit   │          │  (rpush/lrange)     │
                                                        │    → check_budget       │          └─────────────────────┘
                                                        │    → llm_ask            │
                                                        │  GET /health → 200 ok   │
                                                        │  GET /ready  → 200/503  │
                                                        │  GET /metrics (authed)  │
                                                        └─────────────────────────┘
```

**Request flow:** `Client` → `Nginx` (rate limit, SSL) → `Agent` (auth → rate limit → budget → LLM) → `Redis` (history)
