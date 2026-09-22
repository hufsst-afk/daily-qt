# 오늘의 QT 무료 버전
## Ollama + Python + GitHub Pages

추가 유료 API 없이 PC에서 로컬 AI를 실행하여 오늘의 QT 웹페이지를 생성하는 PoC입니다.

## 구조

매일 05:10 (Windows 작업 스케줄러)
→ `qt_agent_free.py`
→ 두란노 공개 페이지 확인
→ 로컬 Ollama / Qwen3 4B
→ `docs/data/today.json`
→ Git commit / push
→ GitHub Pages 자동 반영

### 비용
- Python: 무료
- Ollama 로컬 실행: 무료
- Qwen3 4B 로컬 모델: 무료
- Windows 작업 스케줄러: 무료
- GitHub Free + 공개 저장소 Pages: 무료
- OpenAI API: 사용하지 않음
- Figma Sites: 사용하지 않음

> PC 전기료/인터넷 사용료는 별도입니다.

---

# 1. 준비

## Python
Python 3.11 이상 권장.

확인:
```powershell
python --version
```

## Ollama
Windows 10 이상에서 Ollama를 설치합니다.

공식 다운로드:
https://ollama.com/download/windows

확인:
```powershell
ollama --version
```

## Git
GitHub 자동 게시까지 할 경우 Git for Windows가 필요합니다.

확인:
```powershell
git --version
```

---

# 2. 최초 설정

압축을 예를 들어 다음 위치에 풉니다.

```text
C:\qt_free_local_poc
```

가장 간단한 방법:

```text
SETUP.bat
```

을 더블클릭합니다.

또는 PowerShell:

```powershell
cd C:\qt_free_local_poc
Set-ExecutionPolicy -Scope Process Bypass
.\setup_free.ps1
```

설정 스크립트가 하는 일:
1. `.venv` 생성
2. Python 라이브러리 설치
3. Playwright Chromium 설치
4. `qwen3:4b-instruct` 로컬 모델 다운로드

기본 모델은 약 2.5GB 수준입니다.

---

# 3. 1회 실행

```text
RUN_ONCE.bat
```

또는:

```powershell
.\run_once.ps1
```

성공 시 결과:

```text
docs\data\today.json
```

## 성공 예
```json
{
  "status": "ok",
  "title": "...",
  "bible_reference": "...",
  "summary": "...",
  "meditation": ["...", "...", "..."],
  "application": ["...", "..."],
  "prayer": "..."
}
```

## 자동 확인 실패
```json
{
  "status": "unavailable"
}
```

이것은 의도된 안전장치입니다.
두란노 접근 제한, 페이지 구조 변경, 날짜 검증 실패 시 임의로 QT 내용을 생성하지 않습니다.

---

# 4. 두란노 페이지 확인 방식

1. 일반 HTTP GET으로 공개 페이지 확인
2. 실패하면 Playwright Chromium으로 일반 브라우저 렌더링
3. CAPTCHA/접근차단/인증 화면을 만나면 우회하지 않고 종료
4. 로컬 Ollama가 페이지 텍스트에서 오늘 제목과 성경 본문 범위만 검증
5. 두란노 원문을 웹사이트에 저장하거나 그대로 재게시하지 않음
6. AI가 독자적인 요약/묵상/적용/기도문 생성

사이트 구조가 변경되면 자동 검증이 실패할 수 있습니다.

---

# 5. 수동 입력 Fallback

자동 확인이 실패하는 날에는 `manual_input.json`을 사용합니다.

예:
```json
{
  "enabled": true,
  "date": "2026-09-22",
  "title": "오늘의 QT 제목",
  "bible_reference": "요한복음 3:1-15",
  "source_text": ""
}
```

`enabled=true`로 바꾸고 오늘 날짜/제목/본문 범위를 입력하면 웹 수집을 건너뜁니다.

사용 후에는 다시:
```json
"enabled": false
```
로 변경하십시오.

---

# 6. 로컬 웹페이지 미리보기

```powershell
.\preview_site.ps1
```

브라우저:
```text
http://localhost:8000
```

종료: PowerShell에서 `Ctrl + C`

---

# 7. GitHub 저장소 생성

GitHub에서 Public Repository를 하나 만듭니다.

예:
```text
daily-qt
```

현재 폴더에서:

```powershell
git init
git add .
git commit -m "Initial free QT agent"
git branch -M main
git remote add origin https://github.com/YOUR_ID/daily-qt.git
git push -u origin main
```

GitHub 인증은 Git Credential Manager 등을 사용하십시오.

---

# 8. GitHub Pages 활성화

GitHub Repository:
```text
Settings
→ Pages
→ Build and deployment
→ Source: Deploy from a branch
→ Branch: main
→ Folder: /docs
→ Save
```

주소 예:
```text
https://YOUR_ID.github.io/daily-qt/
```

GitHub Free에서는 Public Repository에서 GitHub Pages를 사용할 수 있습니다.

주의:
웹사이트는 인터넷에 공개됩니다.
민감정보/개인정보를 저장하지 마십시오.

---

# 9. 매일 자동 실행

GitHub 게시 설정이 완료된 뒤:

```powershell
.\install_scheduler.ps1
```

등록 내용:
```text
작업명: DailyQTFreeAgent
시간: 매일 05:10
실행: run_daily_and_publish.ps1
```

동작:
```text
05:10
→ 로컬 AI 생성
→ today.json 갱신
→ git commit
→ git push
→ GitHub Pages 갱신
```

PC가 꺼져 있으면 실행되지 않습니다.
필요하다면 Windows 작업 스케줄러에서 "예약된 시작 시간을 놓친 경우 가능한 한 빨리 작업 시작" 옵션을 켜십시오.

---

# 10. 모델 변경

`config.json`:

```json
"model": "qwen3:4b-instruct"
```

PC 성능이 충분하면 더 큰 모델을 사용할 수 있습니다.

예:
```text
qwen3:8b
gemma3:4b
```

먼저:
```powershell
ollama pull qwen3:8b
```

이후 config.json 모델명 변경.

---

# 11. 운영 시 권고

1. 최초 1~2주는 매일 결과를 사람이 확인합니다.
2. 제목/본문 범위가 맞는지 두란노 원문과 대조합니다.
3. AI 요약이 성경 본문 취지와 맞는지 확인합니다.
4. 자동 공개가 부담되면 git push를 하지 않고 로컬 검수 후 수동 게시합니다.
5. 두란노 이용약관/콘텐츠 사용 범위는 실제 공개 서비스 전에 별도 확인하십시오.

---

# 12. 문제 해결

## Ollama 연결 오류
확인:
```powershell
ollama list
```

모델이 없으면:
```powershell
ollama pull qwen3:4b-instruct
```

Ollama API 기본 주소:
```text
http://localhost:11434
```

## Playwright Chromium 오류
```powershell
.\.venv\Scripts\python.exe -m playwright install chromium
```

## PowerShell 실행 제한
```powershell
Set-ExecutionPolicy -Scope Process Bypass
```

## GitHub에 반영되지 않음
```powershell
git status
git remote -v
git push
```

## QT 정보가 unavailable
- 두란노 페이지 접근 제한
- 페이지 구조 변경
- 로컬 모델이 날짜/메타데이터를 확정하지 못함

이 경우 임의 생성을 하지 않는 것이 정상 동작입니다.
`manual_input.json`을 사용하십시오.
