import json
import os
import re
import sys
import time
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import requests
from bs4 import BeautifulSoup

BASE = Path(__file__).resolve().parent
CONFIG_PATH = BASE / "config.json"
MANUAL_PATH = BASE / "manual_input.json"
OUTPUT_PATH = BASE / "docs" / "data" / "today.json"
LOG_DIR = BASE / "logs"

KST = ZoneInfo("Asia/Seoul")
TODAY = datetime.now(KST).date().isoformat()


def log(message: str):
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(KST).strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] {message}"
    print(line)
    with (LOG_DIR / f"{TODAY}.log").open("a", encoding="utf-8") as f:
        f.write(line + "\n")


def load_json(path: Path, default=None):
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def save_json(path: Path, data: dict):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def unavailable(reason: str, source_url: str) -> dict:
    return {
        "date": TODAY,
        "status": "unavailable",
        "source": "두란노 생명의 삶",
        "source_url": source_url,
        "title": "",
        "bible_reference": "",
        "summary": "",
        "meditation": [],
        "application": [],
        "prayer": "",
        "notice": "공식 정보를 자동 확인하지 못해 내용을 임의 생성하지 않았습니다.",
        "error": reason,
        "generated_at": datetime.now(KST).isoformat(timespec="seconds")
    }


def clean_html_text(html: str, max_chars: int) -> str:
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style", "noscript", "svg"]):
        tag.decompose()
    text = soup.get_text("\n")
    lines = []
    for line in text.splitlines():
        s = re.sub(r"\s+", " ", line).strip()
        if s:
            lines.append(s)
    cleaned = "\n".join(lines)
    return cleaned[:max_chars]


def looks_blocked(text: str) -> bool:
    lower = text.lower()
    blocked_terms = [
        "access denied", "forbidden", "precondition failed",
        "captcha", "robot check", "cloudflare"
    ]
    return any(x in lower for x in blocked_terms)


def fetch_with_requests(url: str, timeout: int, max_chars: int):
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/153.0 Safari/537.36"
        ),
        "Accept-Language": "ko-KR,ko;q=0.9,en;q=0.7"
    }
    try:
        r = requests.get(url, headers=headers, timeout=timeout)
        log(f"HTTP 요청 결과: {r.status_code}")
        if r.status_code != 200:
            return None
        text = clean_html_text(r.text, max_chars)
        if len(text) < 500 or looks_blocked(text):
            return None
        return text
    except Exception as e:
        log(f"일반 HTTP 요청 실패: {type(e).__name__}: {e}")
        return None


def fetch_with_browser(url: str, timeout_ms: int, max_chars: int, headless: bool):
    """
    공개 페이지를 일반 브라우저 렌더링 방식으로 확인합니다.
    CAPTCHA, 인증, 접근차단을 우회하지 않습니다.
    """
    try:
        from playwright.sync_api import sync_playwright
    except Exception as e:
        log(f"Playwright 로드 실패: {e}")
        return None

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=headless)
            page = browser.new_page(
                viewport={"width": 1400, "height": 1000},
                locale="ko-KR"
            )
            page.goto(url, wait_until="domcontentloaded", timeout=timeout_ms)
            page.wait_for_timeout(2500)

            chunks = []
            for frame in page.frames:
                try:
                    body = frame.locator("body")
                    if body.count() > 0:
                        t = body.inner_text(timeout=3000)
                        if t:
                            chunks.append(t)
                except Exception:
                    pass

            browser.close()
            text = "\n".join(chunks)
            text = "\n".join(
                re.sub(r"\s+", " ", x).strip()
                for x in text.splitlines()
                if x.strip()
            )
            if len(text) < 500 or looks_blocked(text):
                log("브라우저 렌더링 결과가 비어 있거나 접근 제한 화면으로 판단됨")
                return None
            return text[:max_chars]
    except Exception as e:
        log(f"브라우저 확인 실패: {type(e).__name__}: {e}")
        return None


def ollama_chat(config: dict, prompt: str) -> dict:
    url = config["ollama_url"].rstrip("/") + "/api/chat"
    payload = {
        "model": config["model"],
        "messages": [
            {
                "role": "system",
                "content": (
                    "You are a careful Korean-language data extraction and devotional writing assistant. "
                    "Return valid JSON only. Do not invent unverified source metadata."
                )
            },
            {"role": "user", "content": prompt}
        ],
        "stream": False,
        "format": "json",
        "options": {
            "temperature": 0.2
        }
    }
    r = requests.post(
        url,
        json=payload,
        timeout=config.get("ollama_timeout_seconds", 180)
    )
    r.raise_for_status()
    obj = r.json()
    content = obj.get("message", {}).get("content", "").strip()
    if not content:
        raise RuntimeError("Ollama 응답 본문이 비어 있습니다.")
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        # JSON 코드블록 형태를 최소한으로 복구
        m = re.search(r"\{.*\}", content, re.S)
        if not m:
            raise
        return json.loads(m.group(0))


def check_ollama(config: dict):
    url = config["ollama_url"].rstrip("/") + "/api/tags"
    r = requests.get(url, timeout=5)
    r.raise_for_status()
    names = [m.get("name", "") for m in r.json().get("models", [])]
    model = config["model"]
    if not any(n == model or n.startswith(model + ":") for n in names):
        raise RuntimeError(
            f"Ollama 모델 '{model}'이 설치되어 있지 않습니다. "
            f"PowerShell에서 'ollama pull {model}'을 실행하세요."
        )


def get_manual_input():
    manual = load_json(MANUAL_PATH, {}) or {}
    if not manual.get("enabled"):
        return None
    if manual.get("date") != TODAY:
        raise RuntimeError(
            f"manual_input.json 날짜({manual.get('date')})가 오늘({TODAY})과 다릅니다."
        )
    title = (manual.get("title") or "").strip()
    ref = (manual.get("bible_reference") or "").strip()
    if not title or not ref:
        raise RuntimeError("수동 입력 사용 시 title과 bible_reference가 필요합니다.")
    return {
        "title": title,
        "bible_reference": ref,
        "source_text": (manual.get("source_text") or "").strip(),
        "manual": True
    }


def extract_metadata(config: dict, source_text: str) -> dict:
    prompt = f"""
오늘 날짜는 {TODAY} (Asia/Seoul)이다.
아래 텍스트는 두란노 '생명의 삶' 공개 웹페이지를 브라우저로 읽은 텍스트이다.

해야 할 일:
- 오늘 날짜에 해당하는 '생명의 삶' QT의 제목과 성경 본문 범위를 찾는다.
- 정보가 실제 텍스트에 근거해 확인될 때만 verified=true.
- 날짜/제목/본문 범위 중 중요한 항목이 불명확하면 verified=false.
- 다른 날짜의 콘텐츠를 오늘 것으로 추측하지 않는다.

JSON 형식:
{{
  "verified": true 또는 false,
  "date": "YYYY-MM-DD 또는 빈 문자열",
  "title": "QT 제목 또는 빈 문자열",
  "bible_reference": "예: 요한복음 3:1-15 또는 빈 문자열",
  "reason": "짧은 검증 사유"
}}

웹페이지 텍스트:
---SOURCE START---
{source_text}
---SOURCE END---
"""
    return ollama_chat(config, prompt)


def generate_content(config: dict, title: str, bible_reference: str, source_text: str) -> dict:
    source_for_prompt = source_text if source_text else "(수동 입력이며 참고 원문 텍스트 없음)"
    prompt = f"""
오늘 날짜: {TODAY}
출처: 두란노 생명의 삶
QT 제목: {title}
성경 본문 범위: {bible_reference}

아래 공개 페이지 텍스트는 사실 확인용 참고자료다.
두란노의 해설/묵상문/기도문 문장을 복제하거나 재게시하지 말라.
그 문체도 모방하지 말고, 성경 본문의 핵심 메시지를 중심으로 독자적인 한국어 콘텐츠를 작성하라.
참고자료에서 12어절 이상 연속으로 동일한 표현을 사용하지 말라.
본문과 직접 관련 없는 내용을 추가하지 말라.

결과 JSON:
{{
  "summary": "3~4문장의 독자적 요약",
  "meditation": ["짧은 묵상 포인트 1", "2", "3"],
  "application": ["개인 적용 질문 1", "개인 적용 질문 2"],
  "prayer": "120~180자 정도의 새롭게 작성한 기도문"
}}

---REFERENCE START---
{source_for_prompt}
---REFERENCE END---
"""
    return ollama_chat(config, prompt)


def validate_content(data: dict):
    if not isinstance(data.get("summary"), str) or len(data["summary"].strip()) < 20:
        raise RuntimeError("summary 검증 실패")
    if not isinstance(data.get("meditation"), list) or len(data["meditation"]) != 3:
        raise RuntimeError("meditation은 정확히 3개여야 합니다.")
    if not isinstance(data.get("application"), list) or len(data["application"]) != 2:
        raise RuntimeError("application은 정확히 2개여야 합니다.")
    if not isinstance(data.get("prayer"), str) or len(data["prayer"].strip()) < 20:
        raise RuntimeError("prayer 검증 실패")


def main():
    config = load_json(CONFIG_PATH)
    if not config:
        raise RuntimeError("config.json을 읽을 수 없습니다.")

    source_url = config["source_url"]
    log("QT 무료 로컬 Agent 시작")
    log(f"오늘 날짜: {TODAY}")
    check_ollama(config)
    log(f"Ollama 정상 / 모델: {config['model']}")

    try:
        manual = get_manual_input()
    except Exception as e:
        data = unavailable(f"수동 입력 오류: {e}", source_url)
        save_json(OUTPUT_PATH, data)
        log(data["error"])
        sys.exit(2)

    source_text = ""
    if manual:
        title = manual["title"]
        bible_reference = manual["bible_reference"]
        source_text = manual["source_text"]
        log("manual_input.json의 수동 입력을 사용합니다.")
    else:
        source_text = fetch_with_requests(
            source_url,
            config.get("request_timeout_seconds", 25),
            config.get("max_source_chars", 30000)
        )

        if not source_text and config.get("use_browser_fallback", True):
            log("일반 HTTP 확인 실패 → 공개 페이지를 브라우저 렌더링으로 재확인")
            source_text = fetch_with_browser(
                source_url,
                config.get("browser_timeout_seconds", 30000),
                config.get("max_source_chars", 30000),
                config.get("headless_browser", True)
            )

        if not source_text:
            data = unavailable(
                "두란노 공개 페이지에서 오늘 정보를 읽지 못했습니다. "
                "접근 제한을 우회하지 않고 종료했습니다. "
                "필요하면 manual_input.json을 사용하세요.",
                source_url
            )
            save_json(OUTPUT_PATH, data)
            log(data["error"])
            return

        log(f"공개 페이지 텍스트 확보: {len(source_text):,}자")
        metadata = extract_metadata(config, source_text)
        log(f"메타데이터 검증 결과: {metadata}")

        if not metadata.get("verified"):
            data = unavailable(
                "로컬 AI가 오늘 QT 제목/성경 본문 범위를 신뢰성 있게 확인하지 못했습니다. "
                + str(metadata.get("reason", "")),
                source_url
            )
            save_json(OUTPUT_PATH, data)
            log(data["error"])
            return

        title = (metadata.get("title") or "").strip()
        bible_reference = (metadata.get("bible_reference") or "").strip()

        if not title or not bible_reference:
            data = unavailable("제목 또는 성경 본문 범위가 비어 있습니다.", source_url)
            save_json(OUTPUT_PATH, data)
            return

    content = generate_content(
        config, title, bible_reference, source_text
    )
    validate_content(content)

    result = {
        "date": TODAY,
        "status": "ok",
        "source": "두란노 생명의 삶",
        "source_url": source_url,
        "title": title,
        "bible_reference": bible_reference,
        "summary": content["summary"].strip(),
        "meditation": [str(x).strip() for x in content["meditation"]],
        "application": [str(x).strip() for x in content["application"]],
        "prayer": content["prayer"].strip(),
        "notice": (
            "두란노 원문을 재게시하지 않고, 확인된 오늘의 제목·성경 본문 범위를 바탕으로 "
            "로컬 AI가 새롭게 작성한 묵상 콘텐츠입니다."
        ),
        "error": "",
        "generated_at": datetime.now(KST).isoformat(timespec="seconds")
    }
    save_json(OUTPUT_PATH, result)
    log(f"생성 완료: {OUTPUT_PATH}")
    log(f"제목: {title} / 본문: {bible_reference}")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        log("사용자가 중단했습니다.")
        sys.exit(130)
    except Exception as e:
        config = load_json(CONFIG_PATH, {}) or {}
        source_url = config.get("source_url", "https://www.duranno.com/qt/default.asp")
        data = unavailable(f"실행 오류: {type(e).__name__}: {e}", source_url)
        save_json(OUTPUT_PATH, data)
        log(data["error"])
        sys.exit(1)
