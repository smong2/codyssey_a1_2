import os
import json
import logging
from typing import List, Dict, Any
from google import genai
from google.genai import types
from api_service import Restaurant

# 로깅 설정
logger = logging.getLogger(__name__)

# ── 1. 데이터 파싱 전용 유틸리티 ──
def _parse_llm_json(response_text: str) -> dict:
    try:
        json_str = response_text.strip()
        if json_str.startswith("```json"):
            json_str = json_str[7:]
        if json_str.startswith("```"):
            json_str = json_str[3:]
        if json_str.endswith("```"):
            json_str = json_str[:-3]
            
        data = json.loads(json_str.strip())
        
        if not isinstance(data, dict):
            raise ValueError("응답 형식이 JSON 객체가 아닙니다.")
        return data
    except (json.JSONDecodeError, ValueError) as e:
        logger.error(f"파싱 실패: {e} | 응답: {response_text[:50]}...")
        return {}

# ── 2. 메인 AI 서비스 ──
def get_travel_recommendations(date_kor: str, errors: list) -> dict:
    client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
    prompt = f"여행 날짜: {date_kor}. 실존하는 국내 여행지를 추천해 주세요."
    
    system_instr = (
        "당신은 국내 여행 전문가입니다. 반드시 JSON 객체로 응답하세요. "
        "형식: {\"recommended_cities\": [\"도시1\", \"도시2\"], \"weather\": \"설명\", "
        "\"events\": [\"행사1\"], \"reason\": \"이유\"}"
    )

    for attempt in range(1, 3):
        try:
            response = client.models.generate_content(
                model=os.getenv("GEMINI_MODEL_NAME"),
                contents=prompt,
                config=types.GenerateContentConfig(
                    system_instruction=system_instr,
                    response_mime_type="application/json",
                    temperature=0.7
                )
            )
            
            result = _parse_llm_json(response.text)
            
            if result and all(k in result for k in ["recommended_cities", "weather"]):
                logger.info(f"추천 도시 획득: {result['recommended_cities']}")
                return result
            
        except Exception as e:
            logger.warning(f"AI 호출 시도 {attempt} 실패: {e}")
            
    errors.append({"step": "llm", "type": "API_ERROR", "message": "Gemini 추천 호출 실패"})
    return {"recommended_cities": ["부산", "경주", "전주"], "weather": "맑음", "events": [], "reason": "데이터 없음"}

# ── 3. 리포트 생성 서비스 ──
def generate_travel_report(date_str: str, rec: dict, restaurants: Dict[str, List[Restaurant]], errors: list) -> str:
    client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

    rest_data = ""
    for city, items in restaurants.items():
        rest_data += f"\n[{city}]\n"
        if items:
            for r in items:
                rest_data += f"  - {r.name} ({r.category}) / {r.address}\n"
        else:
            rest_data += "  - 데이터 없음\n"

    events = rec.get("events", [])
    events_text = "\n".join([f"  - {e}" for e in events]) if events else "  - 데이터 없음"

    # [수정됨] 5번 항목 프롬프트에 지역별 작성 지시 복구
    prompt = f"""여행 날짜: {date_str}
추천 도시: {', '.join(rec.get('recommended_cities', []))}
날씨: {rec.get('weather', '정보 없음')}
추천 이유: {rec.get('reason', '정보 없음')}
행사/축제 목록:
{events_text}
도시별 맛집 정보:
{rest_data}

위 정보를 바탕으로 아래 마크다운 템플릿의 양식을 **단 한 글자도 바꾸지 말고 구조를 그대로 유지하며** 리포트를 작성해 주세요. 
섹션 번호와 제목은 절대 변경하면 안 됩니다.

[출력 템플릿 시작]
# 🗺️ 여행 리포트 ({date_str})

## 1. 추천 지역 및 추천 이유
(추천 도시와 선정 이유를 자연스럽게 서술)

## 2. 날씨 요약
(날씨 정보를 여행자 관점에서 서술)

## 3. 행사 / 축제 목록
(제공된 행사/축제를 목록으로 정리. 없으면 "- 데이터 없음" 표기)

## 4. 맛집 리스트
(도시별로 맛집을 정리. 각 맛집마다 카테고리와 주소를 포함하고 코멘트 추가. 없으면 "- 데이터 없음" 표기)

## 5. 1일 여행 일정 제안
(추천 도시가 여러 곳이면 도시마다 '### 도시명' 소제목으로 구분하여, 추천된 모든 지역에 대해 각각 오전/오후/저녁 일정을 구체적으로 제안하세요.)
[출력 템플릿 끝]
"""

    required_sections = [
        "## 1. 추천 지역 및 추천 이유", 
        "## 2. 날씨 요약", 
        "## 3. 행사 / 축제 목록", 
        "## 4. 맛집 리스트", 
        "## 5. 1일 여행 일정 제안"
    ]
    final_report = ""

    for attempt in range(1, 3):
        try:
            response = client.models.generate_content(
                model=os.getenv("GEMINI_MODEL_NAME"),
                contents=prompt,
                config=types.GenerateContentConfig(
                    system_instruction="당신은 여행 리포트 작성 전문가입니다. 요청된 5개의 마크다운 헤더(##)를 절대 변경하지 말고 구조에 맞춰 작성하세요.",
                    temperature=0.3 
                )
            )
            
            report = response.text
            missing = [s for s in required_sections if s not in report]
            if missing:
                logger.warning(f"누락/변형된 섹션 감지 {missing} → 재시도 ({attempt}/3)")
                continue

            logger.info("리포트 생성 완료")
            final_report = report
            break
        except Exception as e:
            logger.error(f"리포트 생성 실패 (시도 {attempt}/3): {e}")

    if not final_report:
        logger.warning("3회 실패 → 기본 리포트 반환")
        errors.append({"step": "report", "type": "LLM_ERROR", "message": "리포트 생성 3회 실패"})
        return f"# 🗺️ 여행 리포트 ({date_str})\n\n(생성 실패로 인해 데이터를 표시할 수 없습니다.)\n"

    final_report += "\n\n## 오류 요약(errors)\n"
    if errors:
        for err in errors:
            final_report += f"- **[{err['step']}]**: {err['type']} - {err['message']}\n"
    else:
        final_report += "- 발생한 오류 없음\n"

    return final_report