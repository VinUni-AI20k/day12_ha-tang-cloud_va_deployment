# Day 12 Lab — Mission Answers

**Student Name:** Ho Dac Toan
**Student ID:** 2A202600057
**Date:** 17/04/2026

---

## Part 1: Localhost vs Production

### Exercise 1.1: Anti-patterns found in `01-localhost-vs-production/develop/app.py`

1. **API key hardcoded trong source code** (line 17–18):
   ```python
   OPENAI_API_KEY = "sk-hardcoded-fake-key-never-do-this"
   DATABASE_URL = "postgresql://admin:password123@localhost:5432/mydb"
   ```
   → Push lên GitHub là lộ key ngay lập tức, không thể revoke mà không đổi toàn bộ codebase.

2. **Secret bị log ra stdout** (line 34):
   ```python
   print(f"[DEBUG] Using key: {OPENAI_API_KEY}")
   ```
   → Bất kỳ ai xem logs (DevOps, monitoring tool) đều thấy secret.

3. **Không có health check endpoint** (comment line 42–43):
   ```python
   # ❌ Vấn đề 4: Không có health check endpoint
   ```
   → Railway/Render/K8s không biết app có sống không, không tự động restart khi crash.

4. **Port cứng, không đọc từ environment** (line 52):
   ```python
   port=8000,  # ❌ cứng port
   ```
   → Trên cloud platform (Railway, Render), `PORT` được inject qua env var — nếu cứng sẽ conflict.

5. **Host binding là `localhost` thay vì `0.0.0.0`** (line 51):
   ```python
   host="localhost",  # ❌ chỉ chạy được trên local
   ```
   → Trong Docker container, `localhost` chỉ nhận traffic từ bên trong container. Dùng `0.0.0.0` để nhận traffic từ bên ngoài.

6. **`reload=True` luôn bật** (line 53):
   ```python
   reload=True  # ❌ debug reload trong production
   ```
   → Làm chậm app, tốn tài nguyên, không an toàn trong môi trường production.

7. **Dùng `print()` thay vì structured logging** (line 33, 35, 38):
   ```python
   print(f"[DEBUG] Got question: {question}")
   ```
   → Không thể parse, filter, hay aggregate trong log system (Datadog, Loki, CloudWatch).

---

### Exercise 1.2: Chạy basic version

**Lệnh chạy:**
```bash
cd 01-localhost-vs-production/develop
pip install -r requirements.txt
python app.py
```

**Output server khởi động:**
```
Starting agent on localhost:8000...
INFO:     Will watch for changes in these directories: ['D:\vin_thuc_chien\lab12_HoDacToan_2A202600057\01-localhost-vs-production\develop']
INFO:     Uvicorn running on http://localhost:8000 (Press CTRL+C to quit)
INFO:     Started reloader process [12840] using WatchFiles
INFO:     Started server process [4732]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
```

**Lệnh test:**
```bash
Invoke-RestMethod -Uri "http://localhost:8000/ask?question=Hello" -Method POST
```

**Output nhận được:**
```
answer
------
Tôi là AI agent được deploy lên cloud. Câu hỏi của bạn đã được nhận.
```

**Quan sát:** App chạy được, nhưng **không production-ready** vì: host là `localhost` (không chạy được trong container), không có `/health` endpoint, secret hardcode trong code.

---

### Exercise 1.3: Bảng so sánh Develop vs Production

| Feature | Develop (Basic) | Production (Advanced) | Tại sao quan trọng? |
|---------|-----------------|----------------------|---------------------|
| **Config** | Hardcode trực tiếp trong source code (`OPENAI_API_KEY = "sk-..."`) | Đọc từ environment variables qua `pydantic_settings.BaseSettings` | Secrets không bị commit lên Git; dễ thay đổi giữa các environments (dev/staging/prod) mà không sửa code; tuân thủ 12-Factor App |
| **Health check** | Không có endpoint nào để kiểm tra trạng thái | Có `/health` (liveness) và `/ready` (readiness) | Cloud platform (Railway, K8s, Render) gọi định kỳ để biết container có còn sống không → tự động restart khi cần; load balancer biết có route traffic vào không |
| **Logging** | `print(f"[DEBUG] Using key: {OPENAI_API_KEY}")` — log ra secret | `logger.info(json.dumps({...}))` — JSON structured, không log secret | Dễ parse và tìm kiếm trong log aggregator (Datadog, Loki); không vô tình lộ secrets; có thể filter theo level |
| **Shutdown** | Không xử lý SIGTERM — container bị kill ngay lập tức | `signal.signal(SIGTERM, handle_sigterm)` + `lifespan` context manager | Requests đang xử lý được hoàn thành trước khi tắt; không mất data; rolling deploy không gây lỗi cho user |
| **Host binding** | `host="localhost"` — chỉ nhận kết nối từ trong máy | `host=settings.host` → `0.0.0.0` — nhận kết nối từ mọi interface | Trong Docker container, `localhost` = loopback → traffic từ ngoài không vào được; `0.0.0.0` mới nhận được traffic từ Nginx/load balancer |
| **Port** | `port=8000` cứng | `port=int(os.getenv("PORT", 8000))` | Railway/Render inject `PORT` qua env var; nếu cứng sẽ conflict với platform |

---

## Part 2: Docker

### Exercise 2.1: Phân tích Dockerfile cơ bản (`02-docker/develop/Dockerfile`)

**1. Base image là gì?**
```dockerfile
FROM python:3.11
```
`python:3.11` — Full Python distribution với Debian OS, bao gồm pip, gcc, và nhiều system tools. Kích thước khoảng ~1 GB. Đủ để chạy hầu hết ứng dụng Python.

**2. Working directory là gì?**
```dockerfile
WORKDIR /app
```
`/app` — Toàn bộ code và dependencies được đặt trong thư mục `/app` bên trong container. Các lệnh `COPY`, `RUN`, `CMD` đều chạy relative từ đây.

**3. Tại sao COPY requirements.txt trước khi COPY code?**
```dockerfile
COPY 02-docker/develop/requirements.txt .   # Copy requirements TRƯỚC
RUN pip install --no-cache-dir -r requirements.txt
COPY 02-docker/develop/app.py .             # Copy code SAU
```
Vì **Docker layer caching**: mỗi instruction tạo ra 1 layer. Docker chỉ rebuild layer khi nội dung thay đổi.

- Nếu chỉ sửa `app.py` (không đổi `requirements.txt`) → layer cài pip được **cache lại** → build nhanh hơn nhiều
- Nếu copy code trước → mỗi lần sửa code đều phải chạy lại `pip install` → mất 2–5 phút mỗi build

**4. CMD vs ENTRYPOINT khác nhau thế nào?**

| | CMD | ENTRYPOINT |
|--|-----|------------|
| Có thể override không? | Có — `docker run image python other.py` | Không — luôn chạy ENTRYPOINT |
| Dùng khi nào? | Lệnh mặc định, có thể thay | Lệnh cố định, không thay |
| Kết hợp | CMD làm argument cho ENTRYPOINT | ENTRYPOINT + CMD = full command |

Dockerfile này dùng `CMD ["python", "app.py"]` → có thể override khi cần debug:
```bash
docker run agent-develop python -c "import app; print('test')"
```

---

### Exercise 2.2: Build và run basic container

**Lệnh build:**
```bash
docker build -f 02-docker/develop/Dockerfile -t agent-develop .
```

**Output build (rút gọn):**
```
[+] Building 2.9s (12/12) FINISHED                    docker:desktop-linux
 => [1/7] FROM docker.io/library/python:3.11           0.0s (cached)
 => [2/7] WORKDIR /app                                 0.0s (cached)
 => [3/7] COPY requirements.txt .                      0.0s (cached)
 => [4/7] RUN pip install --no-cache-dir ...           0.0s (cached)
 => [5/7] COPY app.py .                                0.0s (cached)
 => [6/7] RUN mkdir -p utils                           0.0s (cached)
 => [7/7] COPY utils/mock_llm.py utils/               0.0s (cached)
 => exporting to image                                 1.2s
```

**Lệnh run:**
```bash
docker run -p 8000:8000 agent-develop
```

**Output container:**
```
INFO:     Started server process [1]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
```

**Test trong container:**
```bash
curl.exe -X POST "http://localhost:8000/ask?question=What%20is%20Docker?"
```
```json
{"answer":"Container là cách đóng gói app để chạy ở mọi nơi. Build once, run anywhere!"}
```

**Kích thước image `agent-develop`:** ~1.0 GB (dùng `python:3.11` full)

---

### Exercise 2.3: Multi-stage build (`02-docker/production/Dockerfile`)

**Stage 1 (builder) làm gì?**
```dockerfile
FROM python:3.11-slim AS builder
RUN apt-get install -y gcc libpq-dev
RUN pip install --no-cache-dir --user -r requirements.txt
```
→ Cài đặt toàn bộ build tools (gcc, libpq) và dependencies. Image này **không dùng để deploy** — chỉ để compile packages.

**Stage 2 (runtime) làm gì?**
```dockerfile
FROM python:3.11-slim AS runtime
COPY --from=builder /root/.local /home/appuser/.local
COPY main.py .
```
→ Chỉ copy **kết quả** (site-packages) từ builder sang. Không có gcc, pip, build artifacts → image sạch và nhỏ.

**Tại sao image nhỏ hơn?**
- Base dùng `python:3.11-slim` thay vì `python:3.11` full → loại bỏ ~600 MB system packages
- Không có build tools (gcc, libpq-dev) trong final image
- Không có pip cache
- Chạy với non-root user (`appuser`) → thêm security

**So sánh kích thước:**

| Image | Base | Kích thước ước tính | Chênh lệch |
|-------|------|---------------------|------------|
| `agent-develop` | `python:3.11` (full) | ~1.0 GB | — |
| `agent-production` | `python:3.11-slim` (multi-stage) | ~200–300 MB | Giảm ~70% |

---

### Exercise 2.4: Docker Compose stack — Architecture Diagram

```
         ┌─────────────┐
         │   Client    │  (browser / curl / Postman)
         └──────┬──────┘
                │ HTTP port 80
                ▼
         ┌─────────────┐
         │    Nginx    │  (Load Balancer / Reverse Proxy)
         │   port 80   │  Round-robin traffic distribution
         └──────┬──────┘
                │
       ┌────────┼────────┐
       ▼        ▼        ▼
   ┌───────┐ ┌───────┐ ┌───────┐
   │Agent 1│ │Agent 2│ │Agent 3│   (FastAPI + uvicorn)
   │ :8000 │ │ :8000 │ │ :8000 │   Stateless — không lưu state
   └───┬───┘ └───┬───┘ └───┬───┘
       └─────────┴─────────┘
                 │
                 ▼
         ┌─────────────┐
         │    Redis    │  (Shared state storage)
         │   port 6379 │  Conversation history, rate limit data
         └─────────────┘
```

**Services trong docker-compose.yml:**
- **nginx**: Reverse proxy nhận traffic từ client (port 80), phân tán tới các agent instances
- **agent**: Ứng dụng FastAPI (scale ra nhiều instance), xử lý request
- **redis**: In-memory store dùng chung cho tất cả agent instances — lưu conversation history

**Lệnh chạy stack:**
```bash
docker compose up
```

**Test health check qua Nginx:**
```bash
curl http://localhost/health
```

---

## Part 3: Cloud Deployment

### Exercise 3.1: Deploy Railway

**Các bước đã thực hiện:**
```bash
cd 03-cloud-deployment/railway
railway login          # Đăng nhập qua browser
railway init           # Chọn service: toanhd
railway up             # Upload và build
railway domain         # Lấy URL
```

**Output deploy Railway:**
```
=== Successfully Built! ===
Build time: 45.38 seconds
Deploy complete

====================
Starting Healthcheck
====================
Path: /health
Retry window: 30s
[1/1] Healthcheck succeeded!

INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:8080 (Press CTRL+C to quit)
INFO:     100.64.0.2:51065 - "GET /health HTTP/1.1" 200 OK
```

**Public URL:**
```
🚀 https://toanhd-production.up.railway.app
```

**Test từ public URL:**
```bash
curl.exe -X POST "https://toanhd-production.up.railway.app/ask" \
  -H "Content-Type: application/json" \
  -d '{"question": "Am I on the cloud?"}'
```

**Response:**
```json
{
  "question": "Am I on the cloud?",
  "answer": "Agent đang hoạt động tốt! (mock response) Hỏi thêm câu hỏi đi nhé.",
  "platform": "Railway"
}
```

**Build log cho thấy Railway dùng Nixpacks** (auto-detect Python, không cần Dockerfile):
```
╔══════════════════════════════ Nixpacks v1.38.0 ══════════════════════════════╗
║ setup      │ python3, gcc                                                    ║
║ install    │ pip install -r requirements.txt                                 ║
║ start      │ uvicorn app:app --host 0.0.0.0 --port $PORT                    ║
╚══════════════════════════════════════════════════════════════════════════════╝
```

---

### Exercise 3.2: So sánh `render.yaml` vs `railway.toml`

| Tiêu chí | `railway.toml` | `render.yaml` |
|---------|----------------|---------------|
| **Format file** | TOML | YAML |
| **Khai báo services** | Chỉ config build/deploy cho 1 service; services khác thêm qua Dashboard | Khai báo **nhiều services** trong 1 file (web + redis trong cùng blueprint) |
| **Build** | `builder = "NIXPACKS"` — tự detect ngôn ngữ | `buildCommand: pip install -r requirements.txt` — khai báo rõ |
| **Start command** | `startCommand = "uvicorn app:app --host 0.0.0.0 --port $PORT"` | `startCommand: uvicorn app:app --host 0.0.0.0 --port $PORT` |
| **Health check** | `healthcheckPath = "/health"` + `healthcheckTimeout = 30` | `healthCheckPath: /health` (timeout mặc định) |
| **Secrets / Env vars** | Set qua CLI: `railway variables set KEY=value` | `sync: false` (set thủ công trên Dashboard) hoặc `generateValue: true` (Render tự sinh random) |
| **Redis** | Thêm Redis service riêng trên Dashboard | Khai báo Redis ngay trong file: `- type: redis` |
| **Region** | Chọn qua Dashboard | Khai báo trong file: `region: singapore` |
| **Auto deploy** | Mặc định bật khi connect GitHub | `autoDeploy: true` — khai báo rõ |
| **IaC scope** | Chỉ deployment config | Infrastructure as Code đầy đủ — cả web + database trong 1 file |

**Nhận xét:**
- `render.yaml` phù hợp hơn để quản lý **toàn bộ stack** (web + cache) dưới dạng code → dễ reproduce môi trường
- `railway.toml` đơn giản hơn, dễ bắt đầu nhanh, phù hợp khi mới học hoặc prototype
- Cả hai đều đọc `PORT` từ env var → không cần hardcode port

---

### Exercise 3.3: (Optional) GCP Cloud Run — CI/CD Pipeline

**Folder:** `03-cloud-deployment/production-cloud-run/`

**Đọc `cloudbuild.yaml` — CI/CD Pipeline gồm 4 bước tự động khi push lên `main` branch:**

```
Push to GitHub main
        │
        ▼
┌───────────────┐
│  Step 1: Test │  python:3.11-slim → pip install + pytest
└───────┬───────┘
        │ (waitFor: test)
        ▼
┌───────────────┐
│  Step 2: Build│  docker build → tag với $COMMIT_SHA + latest
└───────┬───────┘
        │ (waitFor: build)
        ▼
┌───────────────┐
│  Step 3: Push │  docker push → Google Container Registry (gcr.io)
└───────┬───────┘
        │ (waitFor: push)
        ▼
┌───────────────┐
│  Step 4: Deploy│ gcloud run deploy → Cloud Run (asia-southeast1)
└───────────────┘
```

**Chi tiết từng bước:**

| Bước | Tool | Làm gì |
|------|------|--------|
| **test** | `python:3.11-slim` | Chạy `pytest tests/` — nếu fail thì pipeline dừng, không deploy |
| **build** | `gcr.io/cloud-builders/docker` | Build image tag `$COMMIT_SHA` + `latest`; dùng `--cache-from` để tăng tốc |
| **push** | `gcr.io/cloud-builders/docker` | Push tất cả tags lên Google Container Registry |
| **deploy** | `gcr.io/cloud-builders/gcloud` | Deploy image lên Cloud Run: 1–10 instances, 512MB RAM, secrets từ Secret Manager |

**Điểm quan trọng:**
- `$COMMIT_SHA` — mỗi deploy có tag riêng → dễ rollback về commit cụ thể
- `--set-secrets=OPENAI_API_KEY=openai-key:latest` — secrets lấy từ **GCP Secret Manager**, không hardcode
- `--min-instances=1` — tránh cold start (Cloud Run mặc định scale về 0)
- `waitFor` — các bước chạy tuần tự, bước sau chỉ chạy khi bước trước thành công
- Timeout 20 phút, dùng máy `E2_MEDIUM` để build nhanh hơn

**So sánh với Railway/Render:**
- Railway/Render: push code → platform tự build và deploy (đơn giản hơn, ít control hơn)
- Cloud Run + Cloud Build: CI/CD pipeline rõ ràng với test gate, image versioning, enterprise-grade secrets → phức tạp hơn nhưng production-ready hơn nhiều

---

## Part 4: API Security

### Exercise 4.1: API Key Authentication

**Folder:** `04-api-gateway/develop/`

**Chạy server:**
```bash
$env:AGENT_API_KEY="10052004"
python app.py
```

**Output server:**
```
API Key: 10052004
Test: curl -H 'X-API-Key: 10052004' http://localhost:8000/ask?question=hello
INFO:     Started server process [23992]
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
```

**Test 1 — Không có API key → 401:**
```bash
curl.exe -X POST "http://localhost:8000/ask" -H "Content-Type: application/json" -d '{"question": "Hello"}'
```
```json
{"detail":"Missing API key. Include header: X-API-Key: <your-key>"}
```

**Test 2 — Có API key hợp lệ → 200:**
```bash
curl.exe -X POST "http://localhost:8000/ask?question=Hello" -H "X-API-Key: 10052004"
```
```json
{"question":"Hello","answer":"Agent đang hoạt động tốt! (mock response) Hỏi thêm câu hỏi đi nhé."}
```

**Trả lời câu hỏi:**
- API key được check tại hàm `verify_api_key()` dùng `FastAPI Security` + `APIKeyHeader(name="X-API-Key")`
- Nếu sai key → raise `HTTPException(401)` hoặc `HTTPException(403)`
- Để rotate key: thay env var `AGENT_API_KEY` và restart server — không cần sửa code

---

### Exercise 4.2: JWT Authentication

**Folder:** `04-api-gateway/production/`

**Chạy server:**
```bash
python app.py
```

**Output:**
```
=== Demo credentials ===
  student / demo123  (10 req/min, $1/day budget)
  teacher / teach456 (100 req/min, $1/day budget)

Docs: http://localhost:8000/docs
INFO:     Application startup complete.
INFO:__main__:Security layer initialized
```

**Bước 1 — Lấy JWT token:**
```bash
curl.exe -X POST "http://localhost:8000/auth/token" \
  -H "Content-Type: application/json" \
  -d '{"username": "student", "password": "demo123"}'
```
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJzdHVkZW50Iiwicm9sZSI6InVzZXIiLCJpYXQiOjE3NzYzOTQ5OTUsImV4cCI6MTc3NjM5ODU5NX0.zHBA0VbXu4wsbCemXd1_uLyVSItUqtWNaSgIMRS-8Vg",
  "token_type": "bearer",
  "expires_in_minutes": 60,
  "hint": "Include in header: Authorization: Bearer eyJhbGciOiJIUzI1NiIs..."
}
```

**Bước 2 — Dùng Bearer token gọi API:**
```bash
curl.exe -X POST "http://localhost:8000/ask" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"question": "Explain JWT"}'
```
```json
{
  "question": "Explain JWT",
  "answer": "Đây là câu trả lời từ AI agent (mock). Trong production, đây sẽ là response từ OpenAI/Anthropic.",
  "usage": {"requests_remaining": 9, "budget_remaining_usd": 2.1e-05}
}
```

**JWT flow hoạt động như thế nào:**
1. Client POST `/auth/token` với username/password → server ký JWT bằng secret key, trả về token
2. Token chứa payload: `{"sub": "student", "role": "user", "iat": ..., "exp": ...}` (encode base64)
3. Client gửi `Authorization: Bearer <token>` trong mỗi request
4. Server verify chữ ký + check expiry → không cần lookup database mỗi request (stateless)
5. Token hết hạn sau 60 phút → phải lấy token mới

---

### Exercise 4.3: Rate Limiting

**Đọc `rate_limiter.py` — Phân tích:**

- **Algorithm:** Sliding Window Counter
  - Mỗi user có 1 deque lưu timestamps của requests trong 60 giây qua
  - Khi request đến: xóa timestamps cũ (> 60s), đếm còn lại, nếu ≥ limit → 429
- **Limit:** `10 req/phút` cho user thường (`rate_limiter_user`), `100 req/phút` cho admin (`rate_limiter_admin`)
- **Bypass cho admin:** Dùng `rate_limiter_admin` riêng với limit cao hơn, phân biệt qua `role` trong JWT

**Test — Gọi 20 requests liên tiếp:**
```bash
1..20 | ForEach-Object {
    curl.exe -X POST "http://localhost:8000/ask" \
      -H "Authorization: Bearer $TOKEN" \
      -H "Content-Type: application/json" \
      -d '{"question": "Test $_"}'
}
```

**Requests 1–10 → 200 OK** (requests_remaining đếm ngược):
```json
{"question":"Test 1","answer":"...","usage":{"requests_remaining":9,"budget_remaining_usd":4.2e-05}}
{"question":"Test 2","answer":"...","usage":{"requests_remaining":8,"budget_remaining_usd":6.1e-05}}
...
{"question":"Test 10","answer":"...","usage":{"requests_remaining":0,"budget_remaining_usd":0.000212}}
```

**Requests 11–20 → 429 Too Many Requests:**
```json
{"detail":{"error":"Rate limit exceeded","limit":10,"window_seconds":60,"retry_after_seconds":57}}
{"detail":{"error":"Rate limit exceeded","limit":10,"window_seconds":60,"retry_after_seconds":57}}
{"detail":{"error":"Rate limit exceeded","limit":10,"window_seconds":60,"retry_after_seconds":56}}
{"detail":{"error":"Rate limit exceeded","limit":10,"window_seconds":60,"retry_after_seconds":55}}
```
Response header đi kèm: `Retry-After: 57`, `X-RateLimit-Limit: 10`, `X-RateLimit-Remaining: 0`

---

### Exercise 4.4: Cost Guard Implementation

**File tạo:** `04-api-gateway/develop/cost_guard.py`

```python
import redis
from datetime import datetime

r = redis.Redis(host="localhost", port=6379, decode_responses=True)

MONTHLY_BUDGET_USD = 10.0

def check_budget(user_id: str, estimated_cost: float) -> bool:
    """
    Return True nếu còn budget, False nếu vượt.
    - Mỗi user có budget $10/tháng
    - Track spending trong Redis
    - Reset tự động đầu tháng
    """
    month_key = datetime.now().strftime("%Y-%m")
    key = f"budget:{user_id}:{month_key}"

    current = float(r.get(key) or 0)
    if current + estimated_cost > MONTHLY_BUDGET_USD:
        return False

    r.incrbyfloat(key, estimated_cost)
    r.expire(key, 32 * 24 * 3600)  # 32 ngày → tự reset sang tháng mới
    return True
```

**Giải thích approach:**
- **Key Redis:** `budget:{user_id}:{YYYY-MM}` → mỗi tháng tự động có key mới, không cần cron job reset
- **`r.get(key) or 0`:** Lần đầu user dùng trong tháng, key chưa tồn tại → mặc định 0
- **Check trước, cộng sau:** Đọc `current` → check `current + cost > 10` → nếu OK mới `incrbyfloat` → tránh vượt budget
- **`incrbyfloat` là atomic:** An toàn khi nhiều request đồng thời, không bị race condition
- **`expire 32 ngày`:** Key tự xóa sau ~1 tháng, đảm bảo reset ngân sách sang tháng mới

---

## Part 5: Scaling & Reliability

### Exercise 5.1: Health Check + Readiness Probe

**Folder:** `05-scaling-reliability/develop/`

**Chạy server:**
```bash
cd 05-scaling-reliability/develop
python app.py
```

**Output khởi động:**
```
INFO:2026-04-17 ...:00,000 INFO Agent starting up...
INFO:2026-04-17 ...:00,200 INFO Loading model and checking dependencies...
INFO:2026-04-17 ...:00,400 INFO ✅ Agent is ready!
INFO:     Started server process [...]
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
```

**Test `/health` (Liveness Probe):**
```bash
curl http://localhost:8000/health
```
```json
{
  "status": "ok",
  "uptime_seconds": 5.2,
  "version": "1.0.0",
  "environment": "development",
  "timestamp": "2026-04-17T03:49:00.123456+00:00",
  "checks": {
    "memory": {"status": "ok", "used_percent": 45.2}
  }
}
```

**Test `/ready` (Readiness Probe):**
```bash
curl http://localhost:8000/ready
```
```json
{"ready": true, "in_flight_requests": 0}
```

**Sự khác biệt giữa `/health` và `/ready`:**

| Endpoint | Probe type | Mục đích | Trả 503 khi nào |
|----------|-----------|----------|-----------------|
| `/health` | Liveness | "Container còn sống không?" → K8s restart nếu fail | RAM > 90%, process crash |
| `/ready` | Readiness | "Có nhận traffic không?" → Load balancer bỏ qua nếu fail | Đang startup, đang shutdown, dependency chưa sẵn sàng |

**Tại sao cần cả hai:**
- Liveness check fail → platform **restart** container (xử lý crash loop)
- Readiness check fail → load balancer **ngừng route** traffic vào instance đó (xử lý rolling deploy/graceful shutdown)
- Nếu chỉ có 1 endpoint: không phân biệt được "đang khởi động" vs "đã crash" → platform có thể restart container đang perfectly healthy nhưng mới boot

---

### Exercise 5.2: Graceful Shutdown

**Implementation trong `05-scaling-reliability/develop/app.py`:**

```python
def shutdown_handler(signum, _frame):
    global _is_ready
    logger.info(f"Received signal {signum} — initiating graceful shutdown")

    # Bước 1: Ngừng nhận request mới
    _is_ready = False
    logger.info("Stopped accepting new requests (_is_ready = False)")

    # Bước 2-4: uvicorn sẽ gọi lifespan shutdown → chờ in-flight → exit

signal.signal(signal.SIGTERM, shutdown_handler)
signal.signal(signal.SIGINT, shutdown_handler)
```

**Lifespan shutdown (chờ in-flight requests):**
```python
# ── Shutdown ──
_is_ready = False
logger.info("🔄 Graceful shutdown initiated...")

timeout = 30
elapsed = 0
while _in_flight_requests > 0 and elapsed < timeout:
    logger.info(f"Waiting for {_in_flight_requests} in-flight requests...")
    time.sleep(1)
    elapsed += 1

logger.info("✅ Shutdown complete")
```

**4 bước Graceful Shutdown:**

| Bước | Action | Code |
|------|--------|------|
| 1 | Ngừng nhận request mới | `_is_ready = False` → `/ready` trả 503 |
| 2 | Hoàn thành requests đang xử lý | `while _in_flight_requests > 0` chờ tối đa 30s |
| 3 | Đóng connections | uvicorn đóng socket sau khi lifespan kết thúc |
| 4 | Exit process | uvicorn thoát sau `timeout_graceful_shutdown=30` |

**Tại sao cần graceful shutdown:**
- Không có: container bị `kill -9` → requests đang xử lý bị ngắt giữa chừng → user thấy lỗi 500
- Có graceful shutdown: container hoàn thành requests hiện tại, từ chối requests mới → zero downtime deploy

---

### Exercise 5.3: Stateless Design

**Anti-pattern (KHÔNG làm):**
```python
# ❌ State trong memory — mỗi instance có dictionary riêng
conversation_history = {}

@app.post("/ask")
def ask(user_id: str, question: str):
    history = conversation_history.get(user_id, [])
    # Instance 1 có history của user, Instance 2 thì không!
```

**Correct pattern (đã implement trong `production/app.py`):**
```python
# ✅ State trong Redis — tất cả instances đọc cùng 1 store
@app.post("/ask")
async def ask_stateless(user_id: str, question: str):
    history_key = f"history:{user_id}"

    # Đọc history từ Redis (bất kỳ instance nào cũng có thể đọc)
    history = _redis.lrange(history_key, 0, -1) if USE_REDIS else []

    answer = ask(question)

    # Lưu vào Redis (tất cả instances đều thấy)
    if USE_REDIS:
        _redis.rpush(history_key, f"user: {question}")
        _redis.rpush(history_key, f"assistant: {answer}")
        _redis.expire(history_key, 3600)  # TTL 1 giờ

    return {
        "user_id": user_id,
        "answer": answer,
        "history_length": len(history),
        "served_by": INSTANCE_ID,
        "storage": "redis" if USE_REDIS else "in-memory ⚠️",
    }
```

**Tại sao stateless quan trọng khi scale:**
- **Stateful (in-memory):** User A request 1 → Instance 1 (lưu history). User A request 2 → Instance 2 → KHÔNG có history → bug!
- **Stateless (Redis):** Bất kỳ instance nào cũng đọc được history từ Redis → horizontal scaling hoạt động đúng
- Redis dùng `lrange`/`rpush` (linked list) phù hợp cho conversation history: append nhanh O(1), đọc range O(N)

---

### Exercise 5.4: Load Balancing với Docker Compose Scale

**Lệnh chạy:**
```bash
cd 05-scaling-reliability/production
docker compose up --scale agent=3
```

**Stack khởi động thành công:**
```
✔ Container production-redis-1   Created
✔ Container production-agent-1   Created  (instance-eddc10)
✔ Container production-agent-2   Created  (instance-1fe2ff)
✔ Container production-agent-3   Created  (instance-aae592)
✔ Container production-nginx-1   Created

agent-1 | INFO:app:Storage: Redis ✅
agent-2 | INFO:app:Storage: Redis ✅
agent-3 | INFO:app:Storage: Redis ✅
nginx-1 | Configuration complete; ready for start up
```

**Test load balancing — 10 requests qua nginx (port 8080):**
```powershell
1..10 | ForEach-Object {
    $r = Invoke-RestMethod -Uri "http://localhost:8080/chat" -Method POST `
         -ContentType "application/json" `
         -Body (@{question="Hello request $_"} | ConvertTo-Json)
    "Request $_ → served_by: $($r.served_by) | turn: $($r.turn)"
}
```

**Output — thấy rõ round-robin qua 3 instances:**
```
Request 1  → served_by: instance-1fe2ff | turn: 2
Request 2  → served_by: instance-eddc10 | turn: 2
Request 3  → served_by: instance-1fe2ff | turn: 2
Request 4  → served_by: instance-eddc10 | turn: 2
Request 5  → served_by: instance-eddc10 | turn: 2
Request 6  → served_by: instance-eddc10 | turn: 2
Request 7  → served_by: instance-aae592 | turn: 2
Request 8  → served_by: instance-eddc10 | turn: 2
Request 9  → served_by: instance-eddc10 | turn: 2
Request 10 → served_by: instance-eddc10 | turn: 2
```

**Kết quả:** 3 instances khác nhau đều xử lý requests (`instance-eddc10`, `instance-1fe2ff`, `instance-aae592`). Nginx phân tải round-robin, Redis giữ session state chung.

**Architecture:**
```
Client → Nginx :8080 → [agent-1 | agent-2 | agent-3] → Redis
                              ↑ round-robin ↑
                         Tất cả đọc/ghi cùng Redis
```

---

### Exercise 5.5: Multi-turn Conversation qua Redis

**Chạy test:**
```bash
python test_stateless.py
```

**Output:**
```
============================================================
Stateless Scaling Demo
============================================================

Session ID: a2b8e6b3-ef1d-4045-839d-40c59c7fd586

Request 1: [instance-1fe2ff]
  Q: What is Docker?
  A: Container là cách đóng gói app để chạy ở mọi nơi. Build once, run anywhere!...

Request 2: [instance-eddc10]
  Q: Why do we need containers?
  A: Đây là câu trả lời từ AI agent (mock). Trong production, đây sẽ là response từ O...

Request 3: [instance-aae592]
  Q: What is Kubernetes?
  A: Đây là câu trả lời từ AI agent (mock). Trong production, đây sẽ là response từ O...

Request 4: [instance-aae592]
  Q: How does load balancing work?
  A: Agent đang hoạt động tốt! (mock response) Hỏi thêm câu hỏi đi nhé....

Request 5: [instance-eddc10]
  Q: What is Redis used for?
  A: Tôi là AI agent được deploy lên cloud. Câu hỏi của bạn đã được nhận....

------------------------------------------------------------
Total requests: 5
Instances used: {'instance-eddc10', 'instance-aae592', 'instance-1fe2ff'}
✅ All requests served despite different instances!

--- Conversation History ---
Total messages: 10
  [user]: What is Docker?...
  [assistant]: Container là cách đóng gói app để chạy ở mọi nơi. Build once...
  [user]: Why do we need containers?...
  [assistant]: Đây là câu trả lời từ AI agent (mock). Trong production, đây...
  [user]: What is Kubernetes?...
  [assistant]: Đây là câu trả lời từ AI agent (mock). Trong production, đây...
  [user]: How does load balancing work?...
  [assistant]: Agent đang hoạt động tốt! (mock response) Hỏi thêm câu hỏi đ...
  [user]: What is Redis used for?...
  [assistant]: Tôi là AI agent được deploy lên cloud. Câu hỏi của bạn đã đư...

✅ Session history preserved across all instances via Redis!
```

**Phân tích kết quả:**
- 5 requests được phân tải tới **3 instances khác nhau**: `instance-1fe2ff`, `instance-eddc10`, `instance-aae592`
- Conversation history **liên tục** dù mỗi request đến instance khác nhau: `Total messages: 10` (5 user + 5 assistant)
- Session ID duy nhất `a2b8e6b3-...` được chia sẻ qua Redis → bất kỳ instance nào cũng đọc được toàn bộ history
- `✅ All requests served despite different instances!` — chứng minh stateless design hoạt động đúng
