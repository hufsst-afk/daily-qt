$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

$python = ".\.venv\Scripts\python.exe"
if (-not (Test-Path $python)) {
    throw "가상환경이 없습니다. setup_free.ps1을 먼저 실행하세요."
}

& $python ".\qt_agent_free.py"
$agentExit = $LASTEXITCODE

if (-not (Get-Command git -ErrorAction SilentlyContinue)) {
    Write-Host "Git이 설치되어 있지 않아 로컬 JSON까지만 갱신했습니다." -ForegroundColor Yellow
    exit $agentExit
}

$insideRepo = git rev-parse --is-inside-work-tree 2>$null
if ($LASTEXITCODE -ne 0 -or $insideRepo -ne "true") {
    Write-Host "현재 폴더가 Git 저장소가 아니므로 GitHub 게시를 생략합니다." -ForegroundColor Yellow
    exit $agentExit
}

$remote = git remote get-url origin 2>$null
if ($LASTEXITCODE -ne 0 -or -not $remote) {
    Write-Host "origin 원격 저장소가 없어 GitHub 게시를 생략합니다." -ForegroundColor Yellow
    exit $agentExit
}

git add docs/data/today.json
$changed = git diff --cached --name-only

if (-not $changed) {
    Write-Host "게시할 변경사항이 없습니다."
    exit $agentExit
}

$today = Get-Date -Format "yyyy-MM-dd"
git commit -m "Update daily QT $today"
if ($LASTEXITCODE -ne 0) {
    throw "git commit 실패"
}

git push
if ($LASTEXITCODE -ne 0) {
    throw "git push 실패"
}

Write-Host "GitHub에 게시 완료." -ForegroundColor Green
exit $agentExit
