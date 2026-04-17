# Day 12 Lab - Mission Answers

> **Student Name:** Trần Anh Tú
> **Student ID:** 2A202600291
> **Date:** 17/4/2026

## Part 1: Localhost vs Production

### Exercise 1.1: Anti-patterns found
Trong file `01-localhost-vs-production/develop/app.py`, tôi đã tìm thấy các vấn đề sau:
1. **Hardcoded Secrets**: API Key (`OPENAI_API_KEY`) và database URL bị viết trực tiếp vào mã nguồn.
2. **Thiếu Config Management**: Các tham số như `DEBUG`, `MAX_TOKENS` là biến toàn cục, không linh hoạt.
3. **Logging không chuyên nghiệp**: Sử dụng `print()` thay vì thư viện logging chuyên dụng.
4. **Lộ Secret trong Log**: Chương trình in cả API Key ra console.
5. **Thiếu Health Check**: Không có endpoint để hệ thống giám sát biết tình trạng ứng dụng.
6. **Hardcoded Host/Port**: Host là `localhost` (không chạy được trong container) và port cố định `8000`.
7. **Debug mode trong Production**: Tham số `reload=True` được bật mặc định.

### Exercise 1.2: Test results
- **Lệnh chạy**: `python app.py` (trong thư mục `01-localhost-vs-production/develop`)
- **Kết quả Test**:
    - Khi dùng `curl` theo yêu cầu lab, gặp lỗi **422 Unprocessable Content** vì code basic mong đợi `question` là query parameter thay vì JSON body.
    - Khi dùng query parameter `?question=Hello`, gặp lỗi **500 Internal Server Error** (do `UnicodeEncodeError` trên Windows khi `print()` kết quả có dấu tiếng Việt từ mock LLM).
    - **Kết luận**: Phiên bản basic rất dễ lỗi và không ổn định khi chuyển từ localhost sang môi trường khác hoặc xử lý dữ liệu thực tế.

### Exercise 1.3: Comparison table
| Feature | Develop (Basic) | Production (Advanced) | Tại sao quan trọng? |
|---------|---------|------------|---------------------|
| **Config** | Hardcode trong code | Environment variables (.env/config.py) | Tránh lộ secret, linh hoạt cấu hình theo môi trường. |
| **Health check** | Không có | Có endpoint `/health`, `/ready` | Platform tự động phát hiện app chết để restart. |
| **Logging** | Dùng `print()` | Structured JSON logging | Quản lý log tập trung, dễ phân tích, bảo mật hơn. |
| **Shutdown** | Tắt đột ngột | Graceful shutdown (SIGTERM) | Hoàn thành các request dở dang, tránh mất data. |
| **Biến Host/Port** | Cố định `localhost:8000` | `0.0.0.0` và lấy từ ENV var | Cần thiết để chạy trong Docker và trên Cloud (Railway). |

---
*Tự đánh giá: Đã hoàn thành Checkpoint 1.*

---

## Part 2: Docker

### Exercise 2.1: Dockerfile questions
1. **Base image**: `python:3.11` (Bản full, nặng khoảng ~1.6GB).
2. **Working directory**: `/app`.
3. **Tại sao COPY requirements.txt trước?**: Để tận dụng cơ chế Docker layer cache. Nếu file requirements không thay đổi, Docker sẽ bỏ qua bước cài đặt (pip install) ở các lần build sau, giúp tăng tốc độ build đáng kể.
4. **CMD vs ENTRYPOINT khác nhau thế nào?**: 
    - `CMD`: Cung cấp lệnh mặc định cho container, có thể dễ dàng bị ghi đè bởi tham số truyền vào khi chạy `docker run`.
    - `ENTRYPOINT`: Thiết lập tiến trình chính không thay đổi của container. Các tham số truyền vào khi chạy sẽ được ghép nối tiếp vào sau lệnh này.

### Exercise 2.3: Image size comparison
- **Develop (Single-stage)**: ~1.66 GB (Disk Usage) / 424 MB (Content Size).
- **Production (Multi-stage)**: ~236 MB (Disk Usage) / 56.6 MB (Content Size).
- **Difference**: Kích thước bản Production nhỏ hơn khoảng **85%** so với bản Develop.
- **Tại sao image nhỏ hơn?**: Bản multi-stage tách biệt quá trình build (builder) và chạy (runtime). Stage runtime chỉ copy những gì cần thiết để chạy ứng dụng từ builder, loại bỏ hoàn toàn các trình biên dịch (gcc), dependencies headers, và cache dư thừa, giúp image gọn nhẹ và bảo mật hơn.

### Exercise 2.4: Architecture Diagram (Dự đoán từ docker-compose.yml)
Hệ thống gồm 4 dịch vụ chính:
1. **Nginx (Reverse Proxy/LB)**: Lắng nghe ở cổng 80, điều phối traffic vào Agent.
2. **Agent (FastAPI)**: Xử lý logic AI, kết nối với Redis và Qdrant qua mạng nội bộ `internal`.
3. **Redis**: Cache cho session và giới hạn tốc độ (rate limiting).
4. **Qdrant**: Vector database lưu trữ dữ liệu cho RAG (Retrieval-Augmented Generation).

---
*Tự đánh giá: Đã hoàn thành Checkpoint 2.*

---

## Part 3: Cloud Deployment

### Exercise 3.1: Railway deployment
Platform: Railway
URL: https://day12-production-08c4.up.railway.app

### Exercise 3.2: So sánh Railway và Render
| Tiêu chí | Railway (railway.toml) | Render (render.yaml) |
| :--- | :--- | :--- |
| **Độ phức tạp** | Rất thấp, cấu hình tối giản. | Trung bình, đòi hỏi hiểu biết về Blueprint spec. |
| **Phạm vi cấu hình** | Chủ yếu cấu hình cho service hiện tại. | Cấu hình toàn bộ hạ tầng (Web, Redis, DB, Background Workers). |
| **Tính linh hoạt** | Tự động hóa cao (Nixpacks), dễ setup nhanh. | Khả năng IaC (Infrastructure as Code) mạnh mẽ, dễ quản lý fleet dịch vụ. |
| **Vùng (Region)** | Thường mặc định theo tài khoản. | Cho phép chỉ định vùng (ví dụ: `singapore`) trong file cấu hình. |

### Exercise 3.3: Phân tích Cloud Run CI/CD
Dựa trên `cloudbuild.yaml`, quy trình CI/CD bao gồm:
1. **Kiểm thử (Test)**: Chạy `pytest` để đảm bảo code không lỗi trước khi build.
2. **Đóng gói (Build)**: Tạo Docker image và gắn tag theo commit SHA và `latest`.
3. **Lưu trữ (Push)**: Đẩy image lên Google Container Registry (GCR).
4. **Triển khai (Deploy)**: Cloud Run cập nhật service `ai-agent` với image mới nhất, thiết lập giới hạn RAM/CPU và kết nối với Secret Manager để lấy API Key.
*   **Tại sao tốt?**: Quy trình này đảm bảo tính nhất quán (Code đúng mới được build) và bảo mật tuyệt đối (không lộ secret trong config build).

---
*Tự đánh giá: Đã hoàn thành Checkpoint 3.*

---

## Part 4: API Security

### Exercise 4.1: API Key Authentication
- **API key check ở đâu?**: Trong dependency `verify_api_key()`, được inject vào endpoint `/ask` qua `Depends(verify_api_key)`.
- **Nếu sai key?**: Trả về HTTP 401 (thiếu key) hoặc HTTP 403 (sai key).
- **Kết quả test**:
  - `curl /ask` không có key → `401 Missing API key`
  - `curl /ask` với đúng key → `200 OK` + response từ mock LLM

### Exercise 4.2: JWT Authentication
- **JWT Flow**: Client dùng username/password → POST `/auth/token` → nhận JWT token → dùng token trong header `Authorization: Bearer <token>` → server verify signature và extract user info.
- **Kết quả test (production app)**:
  - `POST /auth/token` với `student/demo123` → Nhận JWT token 60 phút.
  - `POST /ask` với Bearer token → `200 OK` + response với thông tin `requests_remaining`.

### Exercise 4.3: Rate Limiting
- **Algorithm**: Sliding Window Counter — đếm số request trong 60 giây qua.
- **Limit**: 10 req/phút cho user thường, 100 req/phút cho admin role.
- **Bypass cho admin?**: Có — admin dùng `rate_limiter_admin` (100 req/min) thay vì `rate_limiter_user` (10 req/min).
- **Kết quả test (12 requests liên tục)**:
  - Request 1-10: HTTP 200
  - Request 11-12: HTTP 429 (Rate limit exceeded)

### Exercise 4.4: Cost Guard Implementation
```python
import redis
from datetime import datetime

r = redis.Redis()

def check_budget(user_id: str, estimated_cost: float) -> bool:
    month_key = datetime.now().strftime("%Y-%m")
    key = f"budget:{user_id}:{month_key}"

    current = float(r.get(key) or 0)
    if current + estimated_cost > 10:
        return False

    r.incrbyfloat(key, estimated_cost)
    r.expire(key, 32 * 24 * 3600)  # 32 days
    return True
```
- **Logic**: Mỗi user có budget $10/tháng được lưu trong Redis với key `budget:<user_id>:<year-month>`. Nếu tổng đã dùng + cost mới > $10 → return False (block). Key tự động expire sau 32 ngày.

---
## Part 5: Scaling & Reliability

### Exercise 5.1 & 5.2: Health Checks & Graceful Shutdown
- **Health Checks**: Đã phân tích endpoint `/health` (Liveness) và `/ready` (Readiness). Orchestrator (Docker/K8s) dùng `/health` để quyết định restart container, và `/ready` để route traffic tới đây hay không.
- **Graceful Shutdown**: Cấu hình Signal Handler bắt tín hiệu `SIGTERM`. App sẽ từ chối request mới và đợi các in-flight requests (đợi timeout max 30s) hoàn tất rồi mới tắt hoàn toàn, giúp người dùng không bị mất data giữa chừng.

### Exercise 5.3 & 5.4 & 5.5: Stateless Design & Load Balancing
- **Dữ liệu thực tế (test_stateless.py)**:
  - Đã chạy `docker compose up --scale agent=3`.
  - Thực hiện 5 câu hỏi liên tiếp, kết quả cho thấy Nginx đã load balance requests tới các Instances riêng biệt thông qua header `X-Served-By`.
  - Tính nguyên vẹn vẫn được đảm bảo: Lịch sử chat được lưu trữ tập trung tại Redis, giúp duy trì context hội thoại dù request được xử lý bởi các instance khác nhau.

---
*Tự đánh giá: Đã hoàn thành Checkpoint 5.*

---

## Part 6: Final Project - Production-Ready AI Agent

### 📊 Kết quả kiểm thử thực tế (Railway Deployment)
Việc kiểm thử được thực hiện bằng PowerShell gọi tới Public URL. Kết quả như sau:

- **Health Check**: `{"status":"ok","version":"1.0.0"}`
- **Readiness Check**: `{"status":"ready"}`
- **Security Check (No API Key)**: Trả về lỗi `401 Unauthorized` (đúng như kỳ vọng).
- **API Interaction (With API Key)**:
  ```json
  {
    "session_id": "sess_test_1776434872",
    "question": "Hello",
    "answer": "Đây là câu trả lời từ AI agent (mock). Trong production, đây sẽ là response từ OpenAI/Anthropic.",
    "history_length": 2
  }
  ```
- **Rate Limiting (15 requests liên tiếp)**:
  - Request 1-10: Trả về `200 OK`.
  - Request 11-15: Trả về `429 Too Many Requests`.

---
*Tự đánh giá: Đã hoàn thành toàn bộ Lab Day 12 - Deploying AI Agent to Production.*
