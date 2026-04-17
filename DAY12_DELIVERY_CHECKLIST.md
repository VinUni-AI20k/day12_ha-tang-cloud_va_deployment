# Delivery Checklist — Day 12 Lab Submission

> **Student Name:** Nguyễn Tri Nhân  
> **Student ID:** 2A202600224
> **Date:** 17/4/2026

---

## Submission Requirements

Submit a **GitHub repository** containing:

### 1. Mission Answers (40 points)

Create a file `MISSION_ANSWERS.md` with your answers to all exercises:

```markdown
# Day 12 Lab - Mission Answers

## Part 1: Localhost vs Production

### Exercise 1.1: Anti-patterns found

1. Hardcoded secrets: Code cứng (Hardcode) trực tiếp API Key hoặc thông tin bảo mật vào thẳng trong mã nguồn thay vì dùng biến môi trường.
2. Hardcoded configuration: Port (cổng) chạy server bị fix cứng, không linh hoạt cấu hình theo môi trường (ví dụ luôn luôn là port 5000 hoặc 8080).
3. Sử dụng Debug mode: Bật debug=True trong môi trường có thể đưa lên production, làm lộ thông tin lỗi hoặc cấu hình nội bộ.
4.Không có health check: Không cung cấp endpoint để hệ thống bên ngoài hoặc cloud kiểm tra xem app còn sống/hoạt động ổn định hay không (Vd: thiếu /health).
5. Không xử lý shutdown an toàn (No graceful shutdown): Ứng dụng đột ngột ngắt kết nối mà không dọn dẹp bộ nhớ, không chờ hoàn tất các request đang dang dở khi bị yêu cầu tắt.

### Exercise 1.2: 

curl http://localhost:8000/ask -X POST \
            -H "Content-Type: application/json" \
            -d '{"question": "Hello"}'

output: {"detail":[{"type":"missing","loc":["query","question"],"msg":"Field required","input":null}]}⏎    

Dựa theo tư tưởng của bài Lab 12, tuy câu lệnh curl chạy thành công và trả về kết quả, nhưng ứng dụng ở phiên bản cơ bản

### Exercise 1.3: Comparison table
```
| Feature      |   Basic  | Advanced | Tại sao quan trọng? |
|--------------|----------|----------|---------------------|
| Config       | Hardcode trực tiếp trong code | Dùng Environment Variables|Giúp bảo mật thông tin nhạy cảm. Quản trị viên có thể thay đổi cấu hình cho từng môi trường (Dev, Staging, Prod) mà không cần phải đi sửa source code hay deploy lại.|
| Health check |   Missing   |   Have   |Load Balancer (ví dụ Nginx, AWS ELB, hoặc Kubernetes) cần ping vào route này để biết ứng dụng đã khởi động xong hoặc còn sống hay không, từ đó mới lùi/chuyển hướng Request của User vào.|
| Logging      | print()  |   JSON   |         Log dạng string trơn rất khó đọc và phân tích tự động. Log JSON (có các trường metadata như time, level, Request ID) giúp dễ dàng đưa vào các hệ thống theo dõi phân tích như Datadog, ELK Stack, Splunk.       |
| Shutdown     | Đột ngột | Graceful |         Tránh trường hợp người dùng đang gọi API (ví dụ đợi LLM generate chữ) thì app đột ngột chết, trả về lỗi 502/503. Graceful shutdown sẽ ngừng nhận request mới, đợi request cũ xử lý xong rồi mới tắt.|
|Binding Address|127.0.0.1 (Chỉ nhận nội bộ máy)|0.0.0.0 (Nhận mọi network interfaces)|Khi chạy trong Docker Container hoặc deploy trên các nền tảng Cloud (Render, Railway), ứng dụng bắt buộc phải lắng nghe trên 0.0.0.0 thì bên ngoài mới gọi vào được.|
```
...

## Part 2: Docker

### Exercise 2.1: Dockerfile questions

1. Base image: [Your answer]
Base image (trong file develop/Dockerfile là python:3.11) chính là môi trường hệ điều hành và thư viện gốc mà bạn chọn làm nền tảng để chạy container. Ở đây, base image là một phiên bản Linux đã được cài sẵn sẵn Python phiên bản 3.11. Docker sẽ tải nó từ Docker Hub để làm lớp (layer) đầu tiên cho ứng dụng.

2. Working directory: [Your answer]
Working directory (trong file là WORKDIR /app) là thư mục làm việc mặc định bên trong container. Mọi lệnh phía sau như RUN, CMD, ENTRYPOINT hay COPY sẽ tự động lấy thư mục này làm mốc gốc để thực thi. Điều này giúp các file code của bạn được gom gọn vào /app mà không rải rác lộn xộn trong hệ điều hành của container.

3. Tại sao COPY requirements.txt trước?
- Docker build container theo từng lớp (layers) và có tính năng cache các lớp này lặp lại ở các lần build sau nếu file gốc không có sự thay đổi.
- Việc bạn COPY requirements.txt và cài đặt dependencies (pip install) TRƯỚC khi COPY mã nguồn (app.py) giúp tận dụng tối đa cache của Docker. File mã nguồn (app.py) thường được sửa đổi liên tục, nhưng file requirements thì ít đổi hơn. Nếu bạn COPY mã nguồn trước, mọi thay đổi nhỏ ở source code sẽ làm Docker xóa cache của toàn bộ các bước sau nó, bắt bạn phải tốn thời gian ngồi pip install lại từ đầu ở mỗi lần build.

4. CMD vs ENTRYPOINT khác nhau thế nào?
- CMD: Là lệnh mặc định dễ dàng bị "ghi đè" (override) từ bên ngoài khi chạy container. Ví dụ: Nếu Dockerfile có CMD ["python", "app.py"], nhưng lúc chạy bạn gõ docker run my-app bash thì lệnh bash sẽ ghi đè và thay thế hoàn toàn python app.py. Dùng CMD khi bạn muốn cho tính linh hoạt cao.
- ENTRYPOINT: Ít bị ghi đè hơn và thường được coi là lệnh gốc (executable thực thụ) không thể thay đổi dễ dàng. Bất kỳ tham số nào bạn truyền thêm ở docker run cũng sẽ tự động được cộng nối thêm (append) vào đằng sau ENTRYPOINT chứ không ghi đè nó. Dùng ENTRYPOINT khi bạn muốn chốt chắc chắn rằng container này bắt buộc phải chạy file app của bạn.

### Exercise 2.2:
Image size là bao nhiêu? -> 1.66GB

### Exercise 2.3: Image size comparison

- Develop: 1.66 GB
- Production: 1.2 GB
- Difference: 27%

1. Stage 1 (Builder) làm gì?

- Stage 1 (được định nghĩa là builder) đóng vai trò như một "phân xưởng" để chuẩn bị môi trường và biên dịch (compile) các thư viện phụ thuộc.
- Tại đây, nó sử dụng image cơ bản là python:3.11-slim, sau đó cài đặt thêm các công cụ build nặng nề như trình biên dịch C (gcc) hay thư viện phát triển (libpq-dev). Nó cũng đọc file requirements.txt và cài đặt các thư viện Python thông qua lệnh pip install --user (để các thư viện được gom chung vào một thư mục /root/.local).
- Lưu ý: Image tạo ra từ Stage 1 rất nặng và chứa nhiều công cụ dư thừa, nên nó sẽ bị "vứt bỏ" và KHÔNG được dùng để đem đi deploy (chạy thực tế).

2. Stage 2 (Runtime) làm gì?

- Stage 2 (được định nghĩa là runtime) là image môi trường thực thi cuối cùng sẽ được đem đi deploy.
- Nó bắt đầu lại từ một image python:3.11-slim mới tinh, sạch sẽ. Tại đây, nó thiết lập một user không có quyền quản trị (non-root user) vì lý do bảo mật.
- Quan trọng nhất, nó sử dụng lệnh COPY --from=builder để chỉ "nhặt" đúng thư mục chứa các thư viện Python đã được biên dịch xong (/root/.local) từ Stage 1 mang sang, rồi copy nốt mã nguồn (main.py) vào. Không có bất kỳ công cụ build nào (gcc, pip cache) đi theo sang giai đoạn này.

3. Tại sao image nhỏ hơn?
Image cuối cùng (từ Stage 2) nhỏ hơn rất nhiều so với image thông thường vì 3 lý do:

- Dùng Base Image nhẹ: Nó bắt đầu từ phiên bản python:3.11-slim được tối giản dung lượng hệ điều hành thay vì dùng python:3.11 bản đầy đủ (~1GB).
- Loại bỏ hoàn toàn build tools: Việc tách thành 2 stage giúp loại bỏ hoàn toàn các trình biên dịch (như gcc), header files, thư viện phát triển (như libpq-dev) và công cụ hệ thống không cần thiết cho quá trình chạy. Image cuối cùng chỉ chứa đúng Python runtime và mã nguồn.
- Không chứa rác từ quá trình cài đặt: Các cache sinh ra khi chạy lệnh apt-get hoặc pip install nằm hết ở Stage 1 và bị bỏ lại, không ảnh hưởng đến dung lượng của image Runtime Image.

## Part 3: Cloud Deployment

### Exercise 3.1: Railway deployment

- URL: https://day12-2a202600224-production.up.railway.app/
- Screenshot: day12-2A202600224-NguyenTriNhan/03-cloud-deployment/image.png

## Part 4: API Security

### Exercise 4.1-4.3: Test results

**Exercise 4.1: API Key Auth**
```bash
# Không có API Key -> 401 Unauthorized
$ curl http://localhost:8000/ask -X POST -d '{"question":"Hi"}'
{"detail":"Not authenticated"}

# Có API Key hợp lệ -> 200 OK
$ curl http://localhost:8000/ask -X POST -H "X-API-Key: my-secret-key" -d '{"question":"Hi"}'
{"answer":"Mocked response to: Hi","tokens_used":15,"cost":0.0003}
```

**Exercise 4.2: JWT Auth**
```bash
# Token hết hạn hoặc sai -> 401
$ curl http://localhost:8000/ask -X POST -H "Authorization: Bearer invalid_token"
{"detail":"Invalid authentication credentials"}
```

**Exercise 4.3: Rate Limiting**
```bash
# Gửi liên tục 15 requests, từ request 11 trở đi bị chặn
$ for i in {1..15}; do curl -s -o /dev/null -w "%{http_code}\n" http://localhost:8000/ask...; done
200
200
...
429
429
{"detail":"Rate limit exceeded"}
```

### Exercise 4.4: Cost guard implementation

**Cách tiếp cận (Approach):**
- Sử dụng Redis làm nơi lưu trữ trạng thái tiêu thụ chi phí (Cost storage) phi tập trung để đếm tổng chi phí mà mỗi `user_id` đã sử dụng trong tháng.
- Viết một middleware hoặc dependency function (`cost_guard.py`) chạy trước khi gọi LLM.
- Mỗi khi có request, hàm này sẽ lấy số chi phí hiện tại của user từ Redis. Nếu lớn hơn giới hạn (VD: $10), trả về mã lỗi `402 Payment Required` hoặc `403 Forbidden` chặn request ngay lập tức.
- Nếu request hợp lệ, tiến hành gọi LLM, tính toán số token thực tế sử dụng quy ra tiền, sau đó lấy số tiền đó cộng dồn lại vào giá trị đã lưu trong Redis của user đó.

## Part 5: Scaling & Reliability

### Exercise 5.1-5.5: Implementation notes

**Exercise 5.1: Health & Readiness Checks**
- Thực hiện thêm 2 endpoints: `/health` (liveness check) để biết container còn sống hay không, và `/ready` (readiness check) kiểm tra thử kết nối đến DB/Redis xem ứng dụng đã sẵn sàng nhận traffic chưa. Kết quả test đều trả về `HTTP 200 OK - {"status": "ok"}`.

**Exercise 5.2: Graceful Shutdown**
- Áp dụng cấu trúc `asynccontextmanager` cho `@asynccontextmanager async def lifespan(app: FastAPI):`. Khi container bị kill (nhận tín hiệu SIGTERM từ Docker/Cloud), hệ thống sẽ in log "Shutting down gracefully", ngừng nhận request mới, đợi kết nối và request hiện tại xử lý xong xuôi (kết hợp time.sleep nếu cần) trước khi thực sự thoát.

**Exercise 5.3: Stateless Design**
- Xóa bỏ mọi bộ nhớ lưu trữ state trong biến môi trường Python (như `dict` hoặc `list` lưu nội dung chat history trong RAM container). 
- Chuyển lịch sử chat và rate limit sang lưu trữ tại Redis Database. Trạng thái không còn phụ thuộc vào container nào. 

**Exercise 5.4: Load Balancing**
- Dùng `docker-compose.yml` để khởi chạy 2 instances (hoặc nhiều hơn) của app đằng sau Nginx Reverse Proxy. Mọi request người dùng gọi vào cổng 80 sẽ được Nginx Round-Robin chia đều cho cả 2 backend 1 và 2. 

**Exercise 5.5: Test Stateless**
- Output test: Gọi liên tiếp 4 API lưu dữ liệu. Các request lần lượt lọt vào instance_1 và instance_2. Sau đó thử tắt bắt buộc (stop) app số 1.
- Gửi tiếp các request để đọc dữ liệu chat history. Traffic dồn về app 2 nhưng mọi dữ liệu lịch sử chat cũ vẫn còn nguyên vẹn. Việc scale down hoặc rớt 1 server không hề gây mất mát dữ liệu khách hàng. Hệ thống đã hoàn toàn đạt chuẩn Stateless.
```

---

### 2. Full Source Code - Lab 06 Complete (60 points)

Your final production-ready agent with all files:

```
your-repo/
├── app/
│   ├── main.py              # Main application
│   ├── config.py            # Configuration
│   ├── auth.py              # Authentication
│   ├── rate_limiter.py      # Rate limiting
│   └── cost_guard.py        # Cost protection
├── utils/
│   └── mock_llm.py          # Mock LLM (provided)
├── Dockerfile               # Multi-stage build
├── docker-compose.yml       # Full stack
├── requirements.txt         # Dependencies
├── .env.example             # Environment template
├── .dockerignore            # Docker ignore
├── railway.toml             # Railway config (or render.yaml)
└── README.md                # Setup instructions
```

**Requirements:**

- All code runs without errors
- Multi-stage Dockerfile (image < 500 MB)
- API key authentication
- Rate limiting (10 req/min)
- Cost guard ($10/month)
- Health + readiness checks
- Graceful shutdown
- Stateless design (Redis)
- No hardcoded secrets

---

### 3. Service Domain Link

Create a file `DEPLOYMENT.md` with your deployed service information:

````markdown
# Deployment Information

## Public URL

https://day12-06-production.up.railway.app
## Platform

Railway

## Test Commands

### Health Check
curl -X 'GET' \
  'https://day12-06-production.up.railway.app/health' \
  -H 'accept: application/json'
output:
{
  "status": "ok",
  "version": "1.0.0",
  "environment": "production",
  "uptime_seconds": 410.9,
  "total_requests": 3,
  "checks": {
    "llm": "dashscope",
    "redis": "not_configured"
  },
  "timestamp": "2026-04-17T11:03:58.950585+00:00"
}


```bash
curl https://your-agent.railway.app/health
# Expected: {"status": "ok"}
```
### API Test (with authentication)

```bash
AGENT_API_KEY="<YOUR_AGENT_API_KEY>"
curl -X 'POST' \
  'https://day12-06-production.up.railway.app/ask' \
  -H 'accept: application/json' \
  -H 'X-API-Key: X-API-KEY' \
  -H 'Content-Type: application/json' \
  -d '{
  "question": "chào bạn",
  "user_id": "anonymous"
}'
```
```
output: 
{
  "question": "chào bạn",
  "answer": "Tôi là AI agent được deploy lên cloud. Câu hỏi của bạn đã được nhận.",
  "model": "qwen3.5-27b",
  "provider": "mock",
  "timestamp": "2026-04-17T10:57:03.242130+00:00"
}
```
## Environment Variables Set

- PORT
- REDIS_URL
- AGENT_API_KEY
- LOG_LEVEL

## Screenshots

- [Deployment dashboard](screenshots/dashboard.png)
- [Service running](screenshots/running.png)
- [Test results](screenshots/test.png)

````

##  Pre-Submission Checklist

- [x] Repository is public (or instructor has access)
- [x] `MISSION_ANSWERS.md` completed with all exercises
- [x] `DEPLOYMENT.md` has working public URL
- [x] All source code in `app/` directory
- [x] `README.md` has clear setup instructions
- [x] No `.env` file committed (only `.env.example`)
- [x] No hardcoded secrets in code
- [x] Public URL is accessible and working
- [ ] Screenshots included in `screenshots/` folder
- [ ] Repository has clear commit history

---

##  Self-Test

Before submitting, verify your deployment


---

## Submission

**Submit your GitHub repository URL:**

```
https://github.com/your-username/day12-agent-deployment
```

**Deadline:** 17/4/2026

---

## Quick Tips

1.  Test your public URL from a different device
2.  Make sure repository is public or instructor has access
3.  Include screenshots of working deployment
4.  Write clear commit messages
5.  Test all commands in DEPLOYMENT.md work
6.  No secrets in code or commit history

---

## Need Help?

- Check [TROUBLESHOOTING.md](TROUBLESHOOTING.md)
- Review [CODE_LAB.md](CODE_LAB.md)
- Ask in office hours
- Post in discussion forum

---

**Good luck! **
