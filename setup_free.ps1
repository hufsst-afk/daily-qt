$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

Write-Host "=== 오늘의 QT 무료버전 초기 설정 ===" -ForegroundColor Cyan

function Require-Command($name, $message) {
    if (-not (Get-Command $name -ErrorAction SilentlyContinue)) {
        Write-Host ""
        Write-Host "[필요] $message" -ForegroundColor Yellow
        exit 1
    }
}

Require-Command python "Python 3.11 이상을 먼저 설치하세요."
Require-Command ollama "Ollama를 먼저 설치하세요: https://ollama.com/download/windows"

Write-Host "[1/4] Python 가상환경 생성"
if (-not (Test-Path ".venv")) {
    python -m venv .venv
}

Write-Host "[2/4] Python 패키지 설치"
& ".\.venv\Scripts\python.exe" -m pip install --upgrade pip
& ".\.venv\Scripts\python.exe" -m pip install -r requirements.txt

Write-Host "[3/4] Playwright Chromium 설치"
& ".\.venv\Scripts\python.exe" -m playwright install chromium

$model = (Get-Content ".\config.json" -Raw | ConvertFrom-Json).model
Write-Host "[4/4] Ollama 모델 다운로드: $model"
ollama pull $model

Write-Host ""
Write-Host "초기 설정 완료." -ForegroundColor Green
Write-Host "다음 실행: .\run_once.ps1"
