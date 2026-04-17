# Day 12 Lab - Mission Answers

## Part 1: Localhost vs Production

### Exercise 1.1: Anti-patterns found
1. **Hardcoded API Key:** Secret key được viết trực tiếp trong code, dễ bị lộ khi push lên GitHub.
2. **Fixed Port (8000):** Không linh hoạt khi deploy lên các nền tảng Cloud (thường yêu cầu đọc PORT từ biến môi trường).
3. **Debug Mode Enabled:** Chạy server ở chế độ reload/debug trong production gây tốn tài nguyên và lộ thông tin lỗi.
4. **No Health Check:** Thiếu endpoint để hệ thống giám sát biết app còn sống hay đã treo.
5. **Standard Print Logging:** Dùng lệnh `print()` thay vì logging có cấu trúc, khó theo dõi và quản lý log ở quy mô lớn.

### Exercise 1.3: Comparison table
| Feature | Basic | Advanced | Tại sao quan trọng? |
|---------|-------|----------|---------------------|
| Config | Hardcode | Env vars (.env) | Bảo mật thông tin nhạy cảm và linh hoạt môi trường. |
| Health check | Không có | Có (/health) | Giúp Cloud Platform tự động restart khi app lỗi. |
| Logging | print() | JSON Logging | Dễ dàng lọc và phân tích log trên các hệ thống quản lý. |
| Shutdown | Đột ngột | Graceful | Đảm bảo không làm ngắt quãng các request đang xử lý của khách hàng. |

## Part 2: Docker

### Exercise 2.1: Dockerfile questions
1. **Base image:** `python:3.11-slim`. Dùng bản `-slim` để giảm dung lượng image, tăng tốc độ deploy.
2. **Working directory:** `/app`. Tạo không gian biệt lập cho mã nguồn bên trong container.
3. **COPY requirements.txt trước:** Để tận dụng Docker Layer Cache. Nếu code đổi nhưng thư viện không đổi, Docker sẽ không phải cài lại thư viện.

### Exercise 2.3: Image size comparison
- **Develop Image:** 1600MB (do chứa nhiều công cụ build và cache).
- **Production Image (Multi-stage):** ~236MB (chỉ chứa runtime cần thiết).
- **Difference:** Giảm khoảng 85% dung lượng.

## Part 4: API Security
- **Authentication:** Sử dụng `X-API-Key` trong Header. Đã tách logic ra file `auth.py` để dễ quản lý và tái sử dụng.
- **Rate Limiting:** Sử dụng thuật toán Fixed Window (10 req/phút). Dữ liệu được quản lý tập trung để bảo vệ tài nguyên hệ thống.
- **Cost Guard implementation:** Đã xây dựng class `CostGuard` để theo dõi chi phí theo thời gian thực. Logic bao gồm việc kiểm tra hạn mức $10/tháng và tự động từ chối (trả về lỗi 402) khi người dùng vượt quá ngân sách, giúp bảo vệ tài chính của chủ sở hữu Agent.

## Part 5: Scaling & Reliability
- **Implementation notes:** 
    - Đã cài đặt **Health check (/health)** để kiểm tra trạng thái sống còn của ứng dụng.
    - Đã cài đặt **Readiness probe (/ready)** để đảm bảo app chỉ nhận traffic khi đã khởi động xong.
    - Đặc biệt, đã thực hiện **Graceful Shutdown**: Khi nhận tín hiệu SIGTERM từ Railway, app sẽ chuyển trạng thái `ready` thành `False` để Load Balancer ngừng gửi khách mới, sau đó mới đóng server một cách êm ái. Điều này giúp không có request nào của khách hàng bị ngắt quãng giữa chừng.

## Part 3: Cloud Deployment
- **Exercise 3.2: Comparison (Railway vs Render)**
    - **Railway:** Rất mạnh ở khả năng tự động hóa, tự phát hiện Dockerfile và hỗ trợ deploy nhanh từ CLI. Tích hợp sẵn DB/Redis rất tiện lợi.
    - **Render:** Có giao diện trực quan và file cấu hình `render.yaml` giúp quản lý cơ sở hạ tầng dưới dạng mã (Infrastructure as Code) một cách chuyên nghiệp.

## Part 5: Stateless Design & Scaling
- **Stateless Design:** Đã sử dụng **Redis** để lưu trữ lịch sử hội thoại. Việc này đảm bảo khi hệ thống mở rộng lên nhiều máy chủ (Scaling), bất kỳ máy chủ nào cũng có thể xử lý yêu cầu của người dùng mà không bị mất dữ liệu session.
- **Load Balancing:** Sử dụng **Nginx** để phân phối tải đều cho các instance Agent, đảm bảo hệ thống luôn sẵn sàng và có tính chịu lỗi (High Availability).
