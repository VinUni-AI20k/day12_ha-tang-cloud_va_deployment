# Day 12 Lab - Mission Answers

**Student Name:** Ho Tran Dinh Nguyen
**Student ID:** 2A202600080
**Date:** 17/04/2026

---

## Part 1: Localhost vs Production

### Exercise 1.1: Anti-patterns found

1. **API key hardcode trong code** (dòng 17–18) — `OPENAI_API_KEY = "sk-hardcoded-fake-key-never-do-this"` và `DATABASE_URL` chứa password. Nếu push lên GitHub thì secret bị lộ ngay lập tức.
2. **Không có config management** (dòng 21–22) — `DEBUG = True` và `MAX_TOKENS = 500` được gán cứng trong code, không thể thay đổi giữa các environments mà không sửa code.
3. **Dùng `print()` thay vì proper logging** (dòng 33–38) — không có log level, không có structured format, và còn in ra cả secret (`OPENAI_API_KEY`) vào stdout.
4. **Không có health check endpoint** (dòng 42) — platform (Railway, Render, K8s) không có cách nào biết app có còn hoạt động không để tự động restart khi crash.
5. **Port và host cố định + `reload=True`** (dòng 51–53) — `host="localhost"` chỉ chấp nhận kết nối nội bộ (không chạy được trong container), `port=8000` cứng (xung đột với PORT env var của cloud platform), `reload=True` là tính năng development không nên bật trên production.

### Exercise 1.2: Kết quả chạy basic version

App khởi động thành công trên `localhost:8000`. Gọi thử:

```
GET http://localhost:8000/ask?question=Hello
→ 200 OK: {"answer": "Tôi là AI agent được deploy lên cloud. Câu hỏi của bạn đã được nhận."}
```

App chạy được nhưng **không production-ready** vì các lý do đã liệt kê ở Exercise 1.1.

### Exercise 1.3: Bảng so sánh Develop vs Production

| Feature | Develop (Basic) | Production (Advanced) | Tại sao quan trọng? |
|---------|----------------|----------------------|---------------------|
| Config | Hardcode trực tiếp trong code (`sk-...`, `DEBUG=True`, port=8000) | Đọc từ environment variables qua `Settings` class (pydantic-settings) | Không commit secrets lên git; dễ thay đổi config giữa dev/staging/prod mà không sửa code |
| Health check | Không có endpoint nào | `/health` (liveness) + `/ready` (readiness) | Platform biết khi nào restart container; load balancer biết khi nào route traffic vào instance |
| Logging | `print()` — in ra cả secret, không có level, không có format | JSON structured logging, không log secrets, có log level theo env | Dễ parse và tìm kiếm trong log aggregator (Datadog, Loki); không rò rỉ thông tin nhạy cảm |
| Shutdown | Đột ngột khi nhận tín hiệu tắt | `lifespan()` context manager + `handle_sigterm()` — hoàn thành request hiện tại trước khi tắt | Không mất request đang xử lý khi deploy rolling update hoặc platform restart container |
| Host binding | `host="localhost"` — chỉ nhận kết nối nội bộ | `host="0.0.0.0"` — nhận kết nối từ mọi interface | Bắt buộc khi chạy trong Docker container hoặc cloud; `localhost` trong container không accessible từ bên ngoài |
| Port | Cứng `port=8000` | Đọc từ `PORT` env var | Railway/Render inject `PORT` tự động; hardcode port gây conflict và không deploy được |

---

## Part 2: Docker

### Exercise 2.1: Dockerfile questions

1. **Base image:** `python:3.11` — full Python distribution (~1GB, bao gồm compiler tools)
2. **Working directory:** `/app` — thư mục code sống bên trong container
3. **Tại sao COPY requirements.txt trước code?** — Docker cache layer: nếu requirements.txt không thay đổi thì layer `pip install` được cache lại, không cần cài lại mỗi lần build → tiết kiệm thời gian đáng kể
4. **CMD vs ENTRYPOINT:** `CMD` có thể bị override khi chạy `docker run <image> <command_khác>`, còn `ENTRYPOINT` cố định không override được (chỉ thêm argument). CMD phù hợp cho command mặc định có thể thay đổi.

### Exercise 2.2: Image size comparison

- `agent-develop` (single-stage, `python:3.11` full): **1.66 GB**
- `agent-production` (multi-stage, `python:3.11-slim`): **236 MB**
- Giảm **~86%** — đủ điều kiện deploy (yêu cầu < 500MB)

### Exercise 2.3: Multi-stage build

- **Stage 1 (builder):** Dùng `python:3.11-slim` + cài gcc, libpq-dev, pip install tất cả dependencies vào `/root/.local`
- **Stage 2 (runtime):** Dùng `python:3.11-slim` sạch, chỉ COPY site-packages từ builder sang — không có gcc, pip, build tools
- Image nhỏ hơn vì loại bỏ toàn bộ build tools không cần thiết khi chạy, chỉ giữ lại những gì cần để execute
- Bonus: chạy với non-root user (`appuser`) — security best practice

### Exercise 2.4: Docker Compose architecture

Stack gồm 4 services:

```
Client → Nginx (port 80) → Agent (port 8000) → Redis (port 6379)
                                             → Qdrant (port 6333)
```

- **nginx:** Reverse proxy, nhận traffic từ bên ngoài port 80, forward vào agent
- **agent:** FastAPI app, xử lý requests, kết nối Redis và Qdrant
- **redis:** Cache session, rate limiting data
- **qdrant:** Vector database cho RAG (tìm kiếm ngữ nghĩa)

Test kết quả:
```
GET http://localhost/health
→ 200 OK: {"status":"ok","uptime_seconds":11.3,"version":"2.0.0"}
```

---

## Part 3: Cloud Deployment

### Exercise 3.1: Railway deployment

- **URL:** https://day12-agent-production.up.railway.app
- **Platform:** Railway (Nixpacks builder, auto-detect Python)

Test kết quả:
```
GET https://day12-agent-production.up.railway.app/health
→ 200 OK: {"status":"ok","uptime_seconds":107.4,"platform":"Railway"}

POST https://day12-agent-production.up.railway.app/ask
→ 200 OK: {"question":"Hello from Day12 lab!","answer":"Đây là câu trả lời từ AI agent (mock)...","platform":"Railway"}
```

### Exercise 3.2: So sánh railway.toml vs render.yaml

| Tiêu chí | railway.toml | render.yaml |
|----------|-------------|-------------|
| Format | TOML | YAML |
| Builder | Khai báo (`NIXPACKS`) | Tự detect hoặc khai báo (`runtime: python`) |
| Start command | `startCommand` trong `[deploy]` | `startCommand` trong service |
| Health check | `healthcheckPath` + `healthcheckTimeout` | `healthCheckPath` |
| Restart policy | `restartPolicyType = "ON_FAILURE"` | Tự động (không cần khai báo) |
| Env vars | Set qua CLI hoặc Dashboard | Set trong `envVars` block hoặc Dashboard |
| Điểm khác biệt | Config tập trung trong 1 file TOML | YAML chi tiết hơn, khai báo cả plan/region |

---

## Part 4: API Security

### Exercise 4.1: API Key authentication

- **API key check ở đâu:** Trong dependency `verify_api_key()` dùng `APIKeyHeader(name="X-API-Key")`, inject vào endpoint qua `Depends(verify_api_key)`
- **Điều gì xảy ra nếu sai key:** Trả về `HTTP 403 Forbidden` với message "Invalid API key."
- **Điều gì xảy ra nếu không có key:** Trả về `HTTP 401 Unauthorized` với message "Missing API key."
- **Làm sao rotate key:** Thay giá trị env var `AGENT_API_KEY` và restart service — không cần sửa code

Test kết quả:
```
POST /ask (không có key)  → 401 Missing API key
POST /ask (sai key)       → 403 Invalid API key
POST /ask (đúng key)      → 200 OK
```

### Exercise 4.2: JWT authentication

JWT flow:
1. `POST /auth/token` với `{"username":"student","password":"demo123"}` → nhận `access_token`
2. Dùng token: `Authorization: Bearer <token>` để gọi các endpoint được bảo vệ
3. Token hết hạn sau 60 phút, cần lấy token mới

Test kết quả:
```
POST /auth/token → 200 OK: {"access_token": "eyJhbGci..."}
POST /ask (không có token) → 401 Authentication required
POST /ask (có token) → 200 OK: {"answer": "...", "usage": {"requests_remaining": 9}}
```

### Exercise 4.3: Rate limiting

- **Algorithm:** Sliding window (dùng Redis sorted set với timestamp)
- **Limit:** 10 requests/phút mỗi user (trong demo dùng in-memory dict)
- **Bypass cho admin:** Role `admin` có `daily_limit: 1000` thay vì `50`

Test kết quả:
```
Request 1-9:  HTTP 200 OK
Request 10:   HTTP 429 Too Many Requests (rate limit hit)
Request 11+:  HTTP 429 Too Many Requests
```

### Exercise 4.4: Cost guard implementation

Logic `check_budget()` dùng Redis để track spending mỗi user theo tháng:

```python
import redis
from datetime import datetime

r = redis.Redis()

def check_budget(user_id: str, estimated_cost: float) -> bool:
    month_key = datetime.now().strftime("%Y-%m")
    key = f"budget:{user_id}:{month_key}"
    
    current = float(r.get(key) or 0)
    if current + estimated_cost > 10:
        return False  # Vượt $10/tháng
    
    r.incrbyfloat(key, estimated_cost)
    r.expire(key, 32 * 24 * 3600)  # Reset sau 32 ngày
    return True
```

Key thiết kế: dùng format `budget:{user_id}:{YYYY-MM}` để tự động reset theo tháng mà không cần cron job.

---

## Part 5: Scaling & Reliability

### Exercise 5.1: Health và Readiness checks

**`/health` (Liveness probe):** Kiểm tra process còn sống không — trả về uptime, version, memory usage. Platform dùng để quyết định restart container.

**`/ready` (Readiness probe):** Kiểm tra app sẵn sàng nhận traffic chưa — trả 503 khi đang startup hoặc shutdown. Load balancer dùng để quyết định có route request vào không.

Test kết quả:
```
GET /health → 200: {"status":"ok","uptime_seconds":2.6,"checks":{"memory":{"status":"ok","used_percent":79.8}}}
GET /ready  → 200: {"ready":true,"in_flight_requests":1}
```

### Exercise 5.2: Graceful shutdown

Implement qua 2 cơ chế:
1. **`lifespan()` context manager:** Khi shutdown, set `_is_ready=False` rồi chờ `_in_flight_requests == 0` (tối đa 30 giây)
2. **`handle_sigterm()`:** Bắt signal SIGTERM/SIGINT, log thông tin trước khi uvicorn xử lý shutdown

Middleware `track_requests` đếm số request đang xử lý — đảm bảo không tắt khi còn request đang chạy.

### Exercise 5.3: Stateless design

**Anti-pattern (stateful):**
```python
conversation_history = {}  # ❌ mỗi instance có memory riêng

@app.post("/ask")
def ask(user_id: str, question: str):
    history = conversation_history.get(user_id, [])  # ❌ chỉ đúng với 1 instance
```

**Đúng (stateless):**
```python
@app.post("/ask")
def ask(user_id: str, question: str):
    history = r.lrange(f"history:{user_id}", 0, -1)  # ✅ shared Redis
    # Khi scale 3 instances, tất cả đọc cùng 1 Redis
```

Lý do: khi scale `--scale agent=3`, mỗi container có memory riêng biệt. Request thứ 2 của user có thể vào container khác → mất history nếu lưu in-memory.

### Exercise 5.4: Load balancing với Nginx

```
docker compose up --scale agent=3
```

Nginx phân tán traffic theo round-robin sang 3 agent instances. Nếu 1 instance down, Nginx tự động bỏ qua và route sang instance còn lại.

### Exercise 5.5: Test stateless design

Script `test_stateless.py` xác nhận: sau khi kill 1 instance ngẫu nhiên, conversation history vẫn còn vì state được lưu trong Redis (shared giữa tất cả instances), không phải in-memory.
