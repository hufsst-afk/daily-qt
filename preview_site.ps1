Set-Location $PSScriptRoot
Write-Host "브라우저에서 http://localhost:8000 을 여세요."
python -m http.server 8000 --directory docs
