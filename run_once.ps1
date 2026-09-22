$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

if (-not (Test-Path ".\.venv\Scripts\python.exe")) {
    Write-Host "가상환경이 없습니다. 먼저 .\setup_free.ps1 을 실행하세요." -ForegroundColor Yellow
    exit 1
}

& ".\.venv\Scripts\python.exe" ".\qt_agent_free.py"
$exitCode = $LASTEXITCODE

Write-Host ""
Write-Host "결과 파일: $PSScriptRoot\docs\data\today.json"
if (Test-Path ".\docs\data\today.json") {
    Get-Content ".\docs\data\today.json" -Raw
}
exit $exitCode
