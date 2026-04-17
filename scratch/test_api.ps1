$apiKey = "my-secret-key-2024"; $baseUrl = "https://day12-production-08c4.up.railway.app"

Write-Host "--- Health Check ---"; Invoke-RestMethod -Uri "$baseUrl/health" | ConvertTo-Json

Write-Host "--- Readiness Check ---"; Invoke-RestMethod -Uri "$baseUrl/ready" | ConvertTo-Json

Write-Host "--- No API Key ---"; try { Invoke-RestMethod -Uri "$baseUrl/ask" -Method Post -ContentType "application/json" -Body '{"question": "Hello", "user_id": "test"}' } catch { Write-Host "Result: $($_.Exception.Response.StatusCode.Value__) Unauthorized" -ForegroundColor Green }

Write-Host "--- With API Key ---"; Invoke-RestMethod -Uri "$baseUrl/ask" -Method Post -Headers @{"X-API-Key"=$apiKey} -ContentType "application/json" -Body '{"question": "Hello", "user_id": "test"}' | ConvertTo-Json

Write-Host "--- Rate Limiting (15 reqs) ---"; 1..15 | ForEach-Object { $idx = $_; $c = try { (Invoke-WebRequest -Uri "$baseUrl/ask" -Method Post -Headers @{"X-API-Key"=$apiKey} -ContentType "application/json" -Body '{"question":"test","user_id":"test"}' -UseBasicParsing).StatusCode } catch { if($_.Exception.Response) { [int]$_.Exception.Response.StatusCode } else { "Err" } }; Write-Host "Req ${idx}: $c" }

