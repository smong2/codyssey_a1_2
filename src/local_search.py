import os
import sys
import json
import re
import argparse
import requests
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv

# ── 환경 변수 최상단 로드 ──────────────────────────────────
load_dotenv()

from google import genai
from google.genai import types

# ── 날짜 검증 함수 ─────────────────────────────────────────
def parse_date(value: str) -> datetime:
    try:
        return datetime.strptime(value, "%Y-%m-%d")
    except ValueError:
        raise argparse.ArgumentTypeError(
            f"날짜 형식이 올바르지 않습니다: '{value}' (예: 2025-03-15)"
        )

# ── 기본 추천값 (API 모두 실패 시) ─────────────────────────
def _default_recommendation() -> dict:
    return {
        "recommended_cities": ["부산", "경주", "전주"],
        "weather": "바다를 따라 산책하기 좋은 맑은 날씨입니다.",
        "events": ["해운대 해변 열차 투어"],
        "reason": "탁 트인 해안 절경과 함께 여유로운 시간을 보낼 수 있습니다."
    }

# ── 캐시 경로 생성 ──────────────────────────────────────────
def _cache_path(date_str: str) -> Path:
    cache_dir = Path("cache")
    cache_dir.mkdir(exist_ok=True)  # 폴더 없으면 자동 생성
    return cache_dir / f"{date_str}_raw.json"

# ── 캐시 저장 ───────────────────────────────────────────────
def _save_cache(date_str: str, data: dict):
    try:
        _cache_path(date_str).write_text(
            json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        print(f"  💾 캐시 저장 완료: {date_str}_raw.json")
    except Exception as e:
        print(f"  ⚠️  캐시 저장 실패: {e}")

# ── 캐시 로드 ───────────────────────────────────────────────
def _load_cache(date_str: str) -> dict | None:
    path = _cache_path(date_str)
    if path.exists():
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            print(f"  📂 캐시 로드 완료: {date_str}_raw.json")
            return data
        except Exception as e:
            print(f"  ⚠️  캐시 로드 실패 (무시하고 API 호출): {e}")
    return None

def _save_report(date_str: str, report: str):
    result_dir = Path("results")
    result_dir.mkdir(exist_ok=True)  # 폴더 없으면 자동 생성
    path = result_dir / f"{date_str}_report.md"
    try:
        path.write_text(report, encoding="utf-8")
        print(f"  💾 리포트 저장 완료: results/{date_str}_report.md")
    except Exception as e:
        print(f"  ⚠️  리포트 저장 실패: {e}")

def _load_report(date_str: str) -> str | None:
    path = Path("results") / f"{date_str}_report.md"
    if path.exists():
        try:
            report = path.read_text(encoding="utf-8")
            print(f"  📂 리포트 캐시 로드 완료: results/{date_str}_report.md")
            return report
        except Exception as e:
            print(f"  ⚠️  리포트 로드 실패 (무시하고 재생성): {e}")
    return None

# ── LLM 1차 추천 함수 ────────────────────────────────────────
def get_recommendation(date_kor: str, errors: list) -> dict:
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        errors.append({"step": "llm", "type": "KEY_MISSING", "message": "GEMINI_API_KEY 없음"})
        print("  ❌ 오류: GEMINI_API_KEY가 설정되지 않았습니다.")
        sys.exit(1)

    client = genai.Client(api_key=api_key)

    try:
        print("  🤖 Gemini 호출 중...")
        response = client.models.generate_content(
            model="gemini-3.1-flash-lite",
            contents=f"여행 날짜: {date_kor}. 국내 여행지를 추천해 주세요.",
            config=types.GenerateContentConfig(
                system_instruction=(
                    "당신은 국내 여행 전문가입니다. 반드시 JSON으로 응답하세요. "
                    "형식: {\"recommended_cities\": [\"도시1\", \"도시2\", \"도시3\"], "
                    "\"weather\": \"날씨 설명\", \"events\": [\"행사1\", \"행사2\"], "
                    "\"reason\": \"추천 이유\"}"
                ),
                response_mime_type="application/json",
                temperature=0.7,
            ),
        )

        result = json.loads(response.text)

        # 필수 키 검증
        required = ["recommended_cities", "weather", "events", "reason"]
        if not all(k in result for k in required):
            raise ValueError("필수 키 누락")

        # recommended_cities 리스트 검증
        if not isinstance(result["recommended_cities"], list) or len(result["recommended_cities"]) == 0:
            raise ValueError("recommended_cities가 비어있거나 리스트가 아님")

        print(f"  ✅ 추천 도시: {', '.join(result['recommended_cities'])}")
        return result

    except Exception as e:
        errors.append({"step": "llm", "type": "API_ERROR", "message": str(e)})
        print(f"  ❌ Gemini 호출 실패: {e}")
        return _default_recommendation()

# ── 지역 맛집 추천 함수 ──────────────────────────────────────
def search_restaurants(city: str, errors: list, limit: int = 5) -> list:
    client_id = os.getenv("NAVER_CLIENT_ID")
    client_secret = os.getenv("NAVER_CLIENT_SECRET")

    if not client_id or not client_secret:
        errors.append({"step": "place", "type": "KEY_MISSING", "message": "네이버 API 키 없음"})
        print("  ❌ 오류: 네이버 API 키가 설정되지 않았습니다.")
        return []

    url = "https://openapi.naver.com/v1/search/local.json"
    headers = {"X-Naver-Client-Id": client_id, "X-Naver-Client-Secret": client_secret}
    params = {"query": f"{city} 맛집", "display": limit, "sort": "comment"}

    try:
        response = requests.get(url, headers=headers, params=params, timeout=10)

        if response.status_code != 200:
            errors.append({"step": "place", "type": "HTTP_ERROR", "message": f"HTTP {response.status_code}"})
            print(f"  ❌ 오류: HTTP {response.status_code} (인증 또는 요청 오류)")
            return []

        items = response.json().get("items", [])
        if not items:
            print(f"  ⚠️  검색 결과 0건 (도시: {city})")
            return []

        restaurants = []
        for item in items:
            name = re.sub(r"<[^>]+>", "", item.get("title", ""))

            # 좌표 변환 (KATEC 좌표계 처리)
            try:
                x = int(item.get("mapx", 0)) / 1e7
                y = int(item.get("mapy", 0)) / 1e7
            except (ValueError, TypeError):
                x, y = None, None

            restaurants.append({
                "name": name,
                "address": item.get("roadAddress") or item.get("address", ""),
                "category": item.get("category", ""),
                "url": item.get("link", ""),
                "x": x,
                "y": y
            })

        print(f"  ✅ {city} 맛집 {len(restaurants)}곳 검색 완료")
        return restaurants

    except requests.exceptions.RequestException as e:
        errors.append({"step": "place", "type": "NETWORK_ERROR", "message": str(e)})
        print(f"  ❌ 오류: 네트워크 문제 - {e}")
        return []

# ── 리포트 생성 함수 ─────────────────────────────────────────
def generate_report(date_str: str, recommendation: dict, all_restaurants: dict, errors: list) -> str:
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        errors.append({"step": "report", "type": "KEY_MISSING", "message": "GEMINI_API_KEY 없음"})
        return _default_report(date_str, recommendation, all_restaurants)

    client = genai.Client(api_key=api_key)

    # ── 맛집 텍스트 변환 ──
    restaurants_text = ""
    for city, items in all_restaurants.items():
        restaurants_text += f"\n[{city}]\n"
        if items:
            for r in items:
                restaurants_text += f"  - {r['name']} ({r['category']}) / {r['address']}\n"
        else:
            restaurants_text += "  - 데이터 없음\n"

    # ── 행사/축제 텍스트 변환 ──
    events = recommendation.get("events", [])
    if isinstance(events, list) and events:
        events_text = "\n".join(f"  - {e}" for e in events)
    elif isinstance(events, dict):
        # dict 형태일 경우 (city: [events]) 펼치기
        event_lines = []
        for city, ev_list in events.items():
            for e in ev_list:
                event_lines.append(f"  - [{city}] {e}")
        events_text = "\n".join(event_lines) if event_lines else "  - 데이터 없음"
    else:
        events_text = "  - 데이터 없음"

    # ── 프롬프트 ──
    prompt = f"""여행 날짜: {date_str}
추천 도시: {', '.join(recommendation.get('recommended_cities', []))}
날씨: {recommendation.get('weather', '정보 없음')}
추천 이유: {recommendation.get('reason', '정보 없음')}

행사/축제 목록:
{events_text}

도시별 맛집 정보:
{restaurants_text}

위 정보를 바탕으로 아래 형식에 맞춰 여행 리포트를 작성해 주세요.
반드시 5개 섹션을 모두 포함해야 합니다.

## 1. 추천 지역 및 추천 이유
(추천 도시와 선정 이유를 자연스럽게 서술)

## 2. 날씨 요약
(날씨 정보를 여행자 관점에서 서술)

## 3. 행사 / 축제 목록
(제공된 행사/축제를 목록으로 정리. 없으면 "데이터 없음" 표기)

## 4. 맛집 리스트
(도시별로 맛집을 정리. 각 맛집마다 카테고리와 주소를 포함하고,
 음식 종류와 지역 특색을 반영한 한줄 소개 코멘트를 추가.
 맛집 정보가 없으면 "데이터 없음" 표기)

## 5. 1일 여행 일정 제안
(추천 도시가 여러 곳이면 도시마다 ### 도시명 소제목으로 구분하여
 각각 오전 / 오후 / 저녁 일정을 구체적으로 제안)
"""

    # ── 섹션 검증용 ──
    required_sections = ["## 1.", "## 2.", "## 3.", "## 4.", "## 5."]

    for attempt in range(1, 4):  # 최대 3회 재시도
        try:
            print(f"  🤖 Gemini 호출 중... (시도 {attempt}/3)")
            response = client.models.generate_content(
                model="gemini-3.1-flash-lite",
                contents=prompt,
                config=types.GenerateContentConfig(
                    system_instruction=(
                        "당신은 여행 리포트 작성 전문가입니다. "
                        "주어진 정보를 바탕으로 읽기 좋은 여행 리포트를 한국어 Markdown 형식으로 작성하세요. "
                        "반드시 요청된 5개 섹션(## 1. ~ ## 5.)을 모두 포함해야 합니다. "
                        "이모지를 적절히 활용하고, 각 도시의 특징과 맛집을 자연스럽게 소개해 주세요."
                    ),
                    temperature=0.7,
                ),
            )

            report = response.text

            # ── 섹션 검증 ──
            missing = [s for s in required_sections if s not in report]
            if missing:
                print(f"  ⚠️  누락 섹션 감지 {missing} → 재시도")
                continue

            print("  ✅ 리포트 생성 완료")
            return report

        except Exception as e:
            errors.append({"step": "report", "type": "API_ERROR", "message": f"시도 {attempt}: {str(e)}"})
            print(f"  ❌ 리포트 생성 실패 (시도 {attempt}/3): {e}")

    # 3회 모두 실패
    print("  ⚠️  3회 실패 → 기본 리포트 반환")

# ── 기본 리포트 (LLM 실패 시) ────────────────────────────────
def _default_report(date_str: str, recommendation: dict, all_restaurants: dict) -> str:
    """LLM 실패 시 데이터를 그대로 나열한 기본 리포트"""
    lines = [
        f"# 🗺️ 여행 리포트 ({date_str})",
        "",
        "## 1. 추천 지역 및 추천 이유",
        f"- 추천 도시: {', '.join(recommendation.get('recommended_cities', []))}",
        f"- 추천 이유: {recommendation.get('reason', '정보 없음')}",
        "",
        "## 2. 날씨 요약",
        f"- {recommendation.get('weather', '정보 없음')}",
        "",
        "## 3. 행사 / 축제 목록",
    ]

    events = recommendation.get("events", [])
    if events:
        for e in events:
            lines.append(f"- {e}")
    else:
        lines.append("- 데이터 없음")

    lines += ["", "## 4. 맛집 리스트"]
    if all_restaurants:
        for city, items in all_restaurants.items():
            lines.append(f"\n### {city}")
            if items:
                for r in items:
                    lines.append(f"- {r['name']} ({r['category']}) / {r['address']}")
            else:
                lines.append("- 데이터 없음")
    else:
        lines.append("- 데이터 없음")

    lines += [
        "",
        "## 5. 1일 여행 일정 제안",
        "- (리포트 생성 실패로 일정 제안 불가)",
    ]

    return "\n".join(lines)

# ── 메인 함수 ───────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(description="날짜 기반 국내 여행지 추천")
    parser.add_argument("--date", type=parse_date, required=True, metavar="YYYY-MM-DD")
    args = parser.parse_args()

    date_str = args.date.strftime("%Y-%m-%d")
    date_kor = args.date.strftime("%Y년 %m월 %d일")
    errors = []

    print(f"📅 여행 날짜: {date_kor}")

    # ── 캐시 확인 ──────────────────────────────────────────
    cached = _load_cache(date_str)
    if cached:
        recommendation = cached.get("recommendation", _default_recommendation())
        all_restaurants = cached.get("restaurants", {})
        print("  ✅ 캐시 데이터 사용 (LLM 추천 + 맛집 검색 생략)")

        cached_report = _load_report(date_str)
        if cached_report:
            print("  ✅ 저장된 리포트 사용 (모든 API 호출 생략)")
            print("\n" + "=" * 50)
            print("📋 여행 리포트 - 캐시된 데이터")
            print("=" * 50)
            print(cached_report)
            return  # 리포트까지 있으면 종료

        # ✅ raw 캐시는 있지만 리포트가 없는 경우 → 리포트만 생성
        print("\n[3/3] 리포트 생성 중 (LLM)...")
        report = generate_report(date_str, recommendation, all_restaurants, errors)
        _save_report(date_str, report)

        print("\n" + "=" * 50)
        print("📋 여행 리포트")
        print("=" * 50)
        print(report)
        return  # ✅ 여기서 반드시 종료

    # ── 캐시 없음: 전체 API 호출 ───────────────────────────
    # [1/3] LLM - 1차 추천
    print("\n[1/3] 여행지 추천 중 (LLM)...")
    recommendation = get_recommendation(date_kor, errors)

    # [2/3] 맛집 검색 (도시별 루프)
    print("\n[2/3] 맛집 검색 중 (네이버 지역검색 API)...")
    all_restaurants = {}
    for city in recommendation.get("recommended_cities", []):
        print(f"  🔍 {city} 검색 중...")
        all_restaurants[city] = search_restaurants(city, errors)

    # raw 캐시 저장
    _save_cache(date_str, {
        "recommendation": recommendation,
        "restaurants": all_restaurants
    })

    # [3/3] 리포트 생성
    print("\n[3/3] 리포트 생성 중 (LLM)...")
    report = generate_report(date_str, recommendation, all_restaurants, errors)
    _save_report(date_str, report)

    # 최종 리포트 출력
    print("\n" + "=" * 50)
    print("📋 여행 리포트")
    print("=" * 50)
    print(report)

    # 에러 로그 출력
    if errors:
        print(f"\n⚠️  내부 오류 발생 기록 ({len(errors)}건):")
        for err in errors:
            print(f"  - [{err['step']}] {err['type']}: {err['message']}")

if __name__ == "__main__":
    main()