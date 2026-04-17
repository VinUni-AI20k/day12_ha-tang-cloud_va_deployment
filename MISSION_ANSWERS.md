# Day 12 Lab - Mission Answers

**Student Name:** Ho Tran Dinh Nguyen  
**Student ID:** 2A202600080  
**Date:** 17/04/2026

---

## Part 1: Localhost vs Production

### Exercise 1.1: Anti-patterns found

1. Hardcoded secret trong source code rất nguy hiểm vì có thể bị lộ ngay khi push repo lên public.
2. Hardcoded host, port, debug mode, và các giới hạn khiến ứng dụng khó di chuyển giữa local, Docker, và môi trường cloud.
3. Dùng `print()` thay vì structured logging làm việc debug và monitoring trên production khó hơn.
4. Thiếu endpoint health và readiness khiến platform không thể phát hiện an toàn việc startup lỗi hoặc container không khỏe.
5. Lưu state hoàn toàn trong memory sẽ làm ứng dụng kém tin cậy khi scale ra nhiều container.

### Exercise 1.2: Result of running the basic version

Bản local cơ bản có thể trả lời các request đơn giản, nhưng chưa production-ready. Nó chưa có cách quản lý secret an toàn, chưa có health check, readiness check, structured logging, và chưa có shared storage theo kiểu stateless.

### Exercise 1.3: Comparison table

| Feature | Develop | Production | Why Important? |
|---------|---------|------------|----------------|
| Config | Hardcoded giá trị trong source | Đọc từ environment variables trong `Settings` | Giúp deploy an toàn hơn và dễ đổi cấu hình theo từng môi trường |
| Host/Port | Dùng giá trị local cố định | Dùng `0.0.0.0` và `PORT` | Bắt buộc khi chạy Docker và Railway/Render |
| Logging | In console cơ bản | Structured JSON logging | Dễ monitoring và debug hơn |
| Health checks | Thường không có | `/health` và `/ready` | Cần cho orchestrator và load balancer |
| Security | Ít hoặc không có | API key authentication với `X-API-Key` | Ngăn truy cập trái phép |
| State | In-memory | Shared state bằng Redis | Hoạt động đúng khi có nhiều instance |
| Shutdown | Tắt đột ngột | Lifespan shutdown + xử lý SIGTERM | Deploy an toàn hơn và ít làm gián đoạn traffic |

---

## Part 2: Docker

### Exercise 2.1: Dockerfile questions

1. Base image: `python:3.11-slim`
2. Working directory: `/build` ở builder stage và `/app` ở runtime stage
3. `COPY requirements.txt` được đặt trước source code để Docker có thể tái sử dụng layer cài dependencies khi code thay đổi nhưng requirements không đổi.
4. `CMD` định nghĩa process mặc định của container và phù hợp ở đây vì ứng dụng khởi động bằng một lệnh uvicorn duy nhất.

### Exercise 2.2: Image size comparison

- Develop image: chưa đo lại trong lần audit cuối này
- Production image: `247 MB` (`docker images day12-agent-prod`)
- Difference: production image nằm dưới yêu cầu `500 MB` của bài và nhỏ hơn nhờ dùng `python:3.11-slim`, multi-stage build, và runtime image tối giản

### Exercise 2.3: Multi-stage build

- Stage 1 cài dependencies vào `/build/packages`
- Stage 2 chỉ copy packages đã cài và source code vào runtime image
- Cách này làm image nhỏ hơn và loại bỏ các build dependency không cần thiết
- Runtime container chạy bằng non-root user `appuser`

### Exercise 2.4: Docker Compose architecture

Stack cuối cùng trong repo này:

```text
Client -> Nginx -> Agent -> Redis
```

- `nginx`: reverse proxy trên port 80
- `agent`: ứng dụng FastAPI
- `redis`: shared storage cho rate limiting, cost tracking, và conversation history

---

## Part 3: Cloud Deployment

### Exercise 3.1: Railway deployment

- URL: https://day12-final-production.up.railway.app
- Platform: Railway
- Kết quả health check đã verify ngày 17/04/2026:

```json
{"status":"ok","version":"1.0.0","environment":"production","checks":{"llm":"mock","redis":"ok"}}
```

- Screenshot cần có trước khi nộp: `screenshots/dashboard.png`

### Exercise 3.2: Compare `railway.toml` vs `render.yaml`

| Feature | `railway.toml` | `render.yaml` |
|---------|----------------|---------------|
| Format | TOML | YAML |
| Health check | `healthcheckPath` | `healthCheckPath` |
| Start command | Định nghĩa trong `[deploy]` | Định nghĩa trong service section |
| Restart policy | Có field tường minh | Được quản lý qua Render config |
| Environment variables | Thường set qua dashboard hoặc CLI | Có thể khai báo trong `envVars` |

### Exercise 3.3: GCP Cloud Run CI/CD

Đây là phần bonus nên em tìm hiểu ở mức khái niệm và cấu hình cơ bản. Trong repo hiện có sẵn 2 file liên quan là:

- `03-cloud-deployment/production-cloud-run/cloudbuild.yaml`
- `03-cloud-deployment/production-cloud-run/service.yaml`

Theo em hiểu thì luồng CI/CD với Cloud Run sẽ là: khi push code, Cloud Build đọc `cloudbuild.yaml` để build image, sau đó đẩy image lên registry rồi deploy lên Cloud Run bằng `service.yaml`. Mỗi lần deploy sẽ tạo revision mới để cập nhật service.

Trong bài này em triển khai production thật trên Railway, còn phần Cloud Run em dừng ở mức đọc cấu hình và hiểu cách hoạt động của pipeline.

---

## Part 4: API Security

### Exercise 4.1: API key authentication

- Việc validate API key được triển khai trong `app/auth.py`
- Key hợp lệ được đọc từ `AGENT_API_KEY`
- Request phải gửi `X-API-Key`
- Thiếu hoặc sai API key sẽ trả về `401`

Hành vi đã verify trên Railway service:

```text
POST /ask không có X-API-Key -> 401
POST /ask có X-API-Key hợp lệ -> 200
```

### Exercise 4.2: JWT authentication

Repo final nộp bài chỉ dùng API key authentication và không triển khai JWT login endpoint. Nếu bổ sung JWT sau này thì flow thông thường sẽ là:

1. User đăng nhập và nhận token
2. Client gửi `Authorization: Bearer <token>`
3. Server validate token trước khi cho phép truy cập

Trong bài nộp này, cơ chế auth thực tế đang được triển khai và deploy là API key authentication.

### Exercise 4.3: Rate limiting

- Algorithm: sliding window
- Primary storage: Redis sorted set
- Fallback: in-memory list khi Redis không khả dụng
- Limit: `10 req/min` cho mỗi user

Kết quả đã verify trên Railway service:

```text
[200, 200, 200, 200, 200, 200, 200, 200, 200, 200, 429, 429]
```

Kết quả này xác nhận 10 request đầu được chấp nhận và các request sau bị rate limit.

### Exercise 4.4: Cost guard implementation

Ứng dụng ước tính token cost và lưu usage theo tháng trong Redis với key dạng:

```text
cost:{user_id}:{YYYY-MM}
```

Khi user chạm ngưỡng budget theo tháng, app sẽ trả về `402`. Ứng dụng final dùng `MONTHLY_BUDGET_USD`, với giá trị mặc định là `$10/month`.

---

## Part 5: Scaling & Reliability

### Exercise 5.1: Health and readiness checks

- `/health`: liveness endpoint trả về status, version, environment, uptime, và Redis health
- `/ready`: readiness endpoint trả về `503` khi app chưa sẵn sàng và `200` khi app đã ready

Kết quả live đã verify:

```text
GET /health -> 200
GET /ready  -> 200
```

### Exercise 5.2: Graceful shutdown

Ứng dụng final có:

1. FastAPI lifespan handler cho startup và shutdown
2. SIGTERM signal handler để log sự kiện shutdown
3. Cleanup kết nối Redis khi shutdown

### Exercise 5.3: Stateless design

Ứng dụng tránh lưu request state quan trọng chỉ trong process memory. Conversation history, rate limit data, và cost data được lưu trong Redis để nhiều instance có thể dùng chung state.

### Exercise 5.4: Load balancing with Nginx

Nginx đứng trước FastAPI service và forward request vào agent container. Đây là pattern tiêu chuẩn để scale ứng dụng phía sau reverse proxy.

### Exercise 5.5: Testing stateless behavior

Một thiết kế stateless có thể được kiểm tra bằng cách chạy nhiều agent instance sau Nginx và xác minh rằng cùng một user vẫn nhận được conversation history và rate limits nhất quán vì Redis là shared giữa các instance.

---

## Additional Verification

Em cũng đã chạy script self-check của repo trong `my-production-agent`:

```text
Production readiness check: 25/25 checks passed
```

Điều này xác nhận repo final hiện tại đáp ứng các yêu cầu kỹ thuật chính của Day 12 lab.
