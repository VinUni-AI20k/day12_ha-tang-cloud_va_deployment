# Day 12 Lab — Mission Answers

**Student Name:** Nguyễn Tri Nhân  
**Student ID:** 2A202600224  
**Date:** 17/04/2026

---

## Part 1: Localhost vs Production

### Exercise 1.1: Anti-patterns found (01-localhost-vs-production/develop/app.py)

1. **Hardcoded secrets**: Hardcode API key / DB URL trực tiếp trong code (rủi ro lộ secret khi push Git).
2. **Hardcoded configuration**: Port bị cố định, không đọc từ env (cloud platforms inject `PORT`).
3. **Debug mode / auto reload**: `reload=True` (dev-only) không phù hợp production.
4. **No health check**: thiếu endpoint `/health` để platform kiểm tra liveness.
5. **Binding sai interface**: bind `host="localhost"` → container/cloud không truy cập được từ bên ngoài.
6. **Logging sai cách**: dùng `print()` và còn log cả secret → dễ lộ dữ liệu nhạy cảm.

### Exercise 1.2: Run basic version — “Nó chạy nhưng production-ready không?”

Command test (theo lab):

```bash
curl http://localhost:8000/ask -X POST \
  -H "Content-Type: application/json" \
  -d '{"question": "Hello"}'
```

Quan sát thực tế với basic version: endpoint `/ask` trong basic app nhận `question` qua **query parameter**, không phải JSON body. Vì vậy request ở trên sẽ trả lỗi kiểu “missing query field”. Ví dụ:

```json
{"detail":[{"type":"missing","loc":["query","question"],"msg":"Field required","input":null}]}
```

Kết luận: “Nó chạy” không đồng nghĩa “production-ready”, vì basic version:

- API contract không rõ ràng/không validate input tốt (client gửi JSON thì fail).
- Hardcode secrets + log secrets.
- Bind localhost + port hardcode.
- Không có health check và không có graceful shutdown.

### Exercise 1.3: Comparison table (basic vs advanced)

| Feature | Basic | Advanced | Tại sao quan trọng? |
|---|---|---|---|
| Config | Hardcode trực tiếp trong code | Dùng Environment Variables | Tránh lộ secrets; dễ cấu hình theo môi trường (dev/staging/prod) mà không sửa code. |
| Health check | Missing | Có `/health` | Load balancer/platform cần ping để restart container khi chết và chỉ route traffic khi app sống. |
| Logging | `print()` | JSON structured logging | Dễ đưa vào ELK/Loki/Datadog, dễ filter/search theo field. |
| Shutdown | Đột ngột | Graceful (lifespan/signal) | Không cắt ngang request đang xử lý; giảm lỗi 502/503 khi deploy/scale down. |
| Binding Address | `localhost/127.0.0.1` | `0.0.0.0` | Bắt buộc khi chạy trong Docker/cloud để nhận traffic từ bên ngoài. |

---

## Part 2: Docker Containerization

### Exercise 2.1: Dockerfile questions (02-docker/develop/Dockerfile)

1. **Base image là gì?**
   - Là image nền để xây container. Ở đây là `python:3.11` (đầy đủ, khá nặng).

2. **Working directory là gì?**
   - `WORKDIR /app` đặt thư mục làm việc mặc định trong container; các lệnh sau đó (COPY/RUN/CMD) lấy `/app` làm mốc.

3. **Tại sao COPY requirements.txt trước?**
   - Để tận dụng Docker layer cache: khi chỉ code thay đổi mà requirements không đổi, Docker không cần cài dependencies lại.

4. **CMD vs ENTRYPOINT khác nhau thế nào?**
   - `CMD`: lệnh mặc định, có thể bị override khi `docker run ... <cmd khác>`.
   - `ENTRYPOINT`: “executable chính”; tham số truyền vào sẽ được append, khó bị thay thế hoàn toàn hơn.

### Exercise 2.2: Build & run (image size)

- Develop image dùng `python:3.11` nên size lớn (đã quan sát ~ **1.66GB**).

### Exercise 2.3: Multi-stage build (02-docker/production/Dockerfile)

1. **Stage 1 (builder) làm gì?**
   - Cài build tools (gcc, libpq-dev) và cài Python dependencies vào `/root/.local`.

2. **Stage 2 (runtime) làm gì?**
   - Tạo runtime image sạch hơn, non-root user; chỉ copy site-packages từ stage 1 + copy source code.

3. **Tại sao image nhỏ hơn?**
   - Runtime bỏ build tools + cache; base image `python:3.11-slim` nhỏ hơn; chỉ giữ phần cần để chạy.

### Exercise 2.4: Docker Compose stack (architecture)

Với final project ở `06-lab-complete/docker-compose.yml`, các services chính:

- `agent` (FastAPI + Uvicorn)
- `redis` (state externalization: rate limit/cost/…)

Architecture (local):

```
Client
  |
  v
Agent (FastAPI)  <---->  Redis
```

Với scaling demo ở `05-scaling-reliability/production/docker-compose.yml`, có thêm Nginx load balancer và scale nhiều instance:

```
Client
  |
  v
Nginx (LB)
  |
  +--> Agent instance 1
  +--> Agent instance 2
  +--> Agent instance 3
          |
          v
        Redis
```

---

## Part 3: Cloud Deployment

### Exercise 3.1: Deploy Railway

- Platform: **Railway**
- Public URL (production): https://day12-06-production.up.railway.app

Test (health):

```bash
curl https://day12-06-production.up.railway.app/health
```

Test (ask — cần API key):

```bash
curl -X POST 'https://day12-06-production.up.railway.app/ask' \
  -H 'X-API-Key: <YOUR_AGENT_API_KEY>' \
  -H 'Content-Type: application/json' \
  -d '{"question":"chào bạn","user_id":"anonymous"}'
```

### Exercise 3.2: Compare render.yaml vs railway.toml

- **Format**
  - Render: YAML blueprint (IaC) — `render.yaml`
  - Railway: TOML config-as-code — `railway.toml`

- **Runtime/build**
  - Render có thể dùng `runtime: python` + `buildCommand`/`startCommand` hoặc `runtime: docker`.
  - Railway có thể dùng Nixpacks hoặc Dockerfile (`builder = "DOCKERFILE"`).

- **Secrets & env vars**
  - Render: `sync: false` cho secrets, hoặc `generateValue: true`.
  - Railway: set qua Dashboard/CLI (`railway variables set ...`).

- **Health checks**
  - Cả hai đều có `healthCheckPath`/`healthcheckPath`.

- **Redis**
  - Render blueprint có thể khai báo luôn service Redis.
  - Railway thường dùng Redis add-on hoặc service riêng (khai báo/attach trong Railway).

### Exercise 3.3: (Optional) GCP Cloud Run

- Chưa triển khai (optional). Đã đọc khái niệm CI/CD qua `cloudbuild.yaml` và `service.yaml`.

---

## Part 4: API Security

### Exercise 4.1: API Key authentication (04-api-gateway/develop/app.py)

- **API key được check ở đâu?**
  - Ở dependency `verify_api_key()` sử dụng `APIKeyHeader(name="X-API-Key")`.

- **Điều gì xảy ra nếu sai key?**
  - Missing key → HTTP 401
  - Invalid key → HTTP 403

- **Rotate key thế nào?**
  - Đổi `AGENT_API_KEY` trong environment (local `.env` hoặc cloud variables) rồi restart/redeploy.

### Exercise 4.2: JWT authentication (04-api-gateway/production)

- Flow:
  1. `POST /auth/token` với username/password → nhận JWT
  2. Gọi API protected với header `Authorization: Bearer <token>`
  3. Server verify signature (HS256) + expiry (60 phút)

Commands:

```bash
# Lấy token
curl -X POST http://localhost:8000/auth/token \
  -H "Content-Type: application/json" \
  -d '{"username":"student","password":"demo123"}'

# Dùng token
TOKEN="<token>"
curl -X POST http://localhost:8000/ask \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"question":"Explain JWT"}'
```

### Exercise 4.3: Rate limiting (04-api-gateway/production/rate_limiter.py)

- **Algorithm**: Sliding Window Counter (deque timestamps per user)
- **Limit**:
  - user: 10 req/min
  - admin: 100 req/min
- **Bypass/admin tier**:
  - Dựa vào role trong JWT (`user` vs `admin`) để chọn limiter khác nhau.

### Exercise 4.4: Cost guard (04-api-gateway/production/cost_guard.py)

- Mục tiêu: chặn khi vượt budget, cảnh báo khi gần hết budget.
- Cơ chế demo: in-memory `UsageRecord` theo ngày.
- Nếu vượt budget user → HTTP 402; nếu vượt global budget → HTTP 503.
- Trong production thực tế: nên lưu usage trong Redis/DB để stateless.

---

## Part 5: Scaling & Reliability

### Exercise 5.1: Health & readiness checks

- `/health`: liveness probe (process sống)
- `/ready`: readiness probe (đã init xong, sẵn sàng nhận traffic)

Final project có ở `06-lab-complete/app/main.py`.

### Exercise 5.2: Graceful shutdown

- Dùng FastAPI lifespan để đánh dấu ready/unready và log startup/shutdown.
- Xử lý SIGTERM để tắt “êm”, không cắt ngang request.

### Exercise 5.3: Stateless design

- Không lưu state trong RAM theo instance.
- Đưa state ra Redis (`REDIS_URL`) để khi scale nhiều instance, session/rate-limit/budget vẫn nhất quán.

### Exercise 5.4: Load balancing (05-scaling-reliability/production/nginx.conf)

- Nginx reverse proxy tới upstream `agent:8000`.
- Docker DNS tự round-robin các replica agent.
- Thêm header `X-Served-By` để quan sát instance nào xử lý request.

### Exercise 5.5: Test stateless (05-scaling-reliability/production/test_stateless.py)

- Script gửi nhiều request qua Nginx và quan sát `served_by` đổi giữa các instance.
- Sau đó lấy history để chứng minh state được lưu ở Redis, không phụ thuộc instance.

---

## Part 6: Final Project (summary)

Final code nằm trong thư mục `06-lab-complete/` và đáp ứng các tiêu chí chính:

- REST API `/ask` + `/health` + `/ready`
- Config từ environment variables
- API key authentication
- Rate limiting + cost guard
- Dockerfile multi-stage + docker-compose (agent + redis)
- Deploy Railway bằng `railway.toml`
