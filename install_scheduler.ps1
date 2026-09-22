$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

$taskName = "DailyQTFreeAgent"

schtasks /Query /TN $taskName *> $null
if ($LASTEXITCODE -eq 0) {
    Write-Host "이미 '$taskName' 작업이 존재합니다." -ForegroundColor Yellow
    Write-Host "기존 작업을 변경하려면 먼저 작업 스케줄러에서 확인/삭제한 후 다시 실행하세요."
    exit 1
}

$script = Join-Path $PSScriptRoot "run_daily_and_publish.ps1"
$action = "powershell.exe -NoProfile -ExecutionPolicy Bypass -File `"$script`""

Write-Host "다음 작업을 등록합니다:"
Write-Host "이름: $taskName"
Write-Host "시간: 매일 05:10"
Write-Host "스크립트: $script"

schtasks /Create /SC DAILY /TN $taskName /TR $action /ST 05:10
if ($LASTEXITCODE -ne 0) {
    throw "작업 스케줄러 등록 실패"
}

Write-Host "등록 완료." -ForegroundColor Green
Write-Host "Windows 작업 스케줄러에서 '$taskName'을 확인하세요."
