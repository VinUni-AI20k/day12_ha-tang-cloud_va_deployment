# Code Lab: Deploy Your AI Agent to Production (Windows Version)

> **AICB-P1 · VinUniversity 2026**  
> Thời gian: 3-4 giờ | Độ khó: Intermediate

## Part 4: API Security (40 phút)

### Exercise 4.1: API Key authentication

```powershell
# 1. Quay lại thư mục gốc dự án
cd d:\VinAction\day12_ha-tang-cloud_va_deployment

# 2. Dọn dẹp các tiến trình cũ (Rất quan trọng)
Stop-Process -Name "python" -Force -ErrorAction SilentlyContinue
docker stop $(docker ps -q) -ErrorAction SilentlyContinue

# 3. Vào thư mục và chạy Server
cd 04-api-gateway/develop
python app.py
```

**Mở Terminal mới để chạy lệnh Test:**

```powershell
# Tạo Body và Key
$body = @{question="Hello"} | ConvertTo-Json
$headers = @{"X-API-Key"="demo-key-change-in-production"}

# Test có Key đúng
Invoke-RestMethod -Uri "http://localhost:8000/ask" -Method Post -Headers $headers -Body $body -ContentType "application/json"
```

### Exercise 4.2: JWT authentication (Advanced)

```powershell
# 1. Quay lại thư mục gốc và dọn dẹp Server cũ
cd d:\VinAction\day12_ha-tang-cloud_va_deployment
Stop-Process -Name "python" -Force -ErrorAction SilentlyContinue

# 2. Chạy Server Production
cd 04-api-gateway/production
python app.py
```

**Mở Terminal mới để chạy lệnh Test:**

```powershell
# Lấy JWT Token
$authBody = @{username="student"; password="demo123"} | ConvertTo-Json
$authResponse = Invoke-RestMethod -Uri "http://localhost:8000/auth/token" -Method Post -Body $authBody -ContentType "application/json"
$token = $authResponse.access_token

# Dùng Token để gọi Agent
$body = @{question="Explain JWT"} | ConvertTo-Json
Invoke-RestMethod -Uri "http://localhost:8000/ask" -Method Post -Headers @{Authorization="Bearer $token"} -Body $body -ContentType "application/json"
```

### Exercise 4.3: Rate limiting

```powershell
# Chạy vòng lặp test 20 lần (Đã sửa lỗi cú pháp Windows)
1..20 | ForEach-Object {
    try {
        $loopBody = @{question="Test $($_)"} | ConvertTo-Json
        $res = Invoke-RestMethod -Uri "http://localhost:8000/ask" -Method Post -Headers @{Authorization="Bearer $token"} -Body $loopBody -ContentType "application/json"
        Write-Host "Request $($_): Success"
    } catch {
        Write-Host "Request $($_): Failed (Rate Limited)"
    }
}
```

---

## Part 5: Scaling & Reliability (40 phút)

### Exercise 5.4: Load balancing

```powershell
# 1. Quay lại gốc và dọn dẹp
cd d:\VinAction\day12_ha-tang-cloud_va_deployment
docker compose -f 05-scaling-reliability/production/docker-compose.yml down
Stop-Process -Name "python" -Force -ErrorAction SilentlyContinue

# 2. Chạy Scale 3 Agent
cd 05-scaling-reliability/production
docker compose up --scale agent=3 -d
```

Test Load Balancer:
```powershell
1..10 | ForEach-Object {
    $lbBody = @{question="Request $($_)"} | ConvertTo-Json
    Invoke-RestMethod -Uri "http://localhost/ask" -Method Post -Body $lbBody -ContentType "application/json"
}
```

**Happy Deploying!**
