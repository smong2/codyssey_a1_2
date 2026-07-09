import os
import json
import logging
from typing import List, Dict
from google import genai
from google.genai import types
from api_service import Restaurant

logger = logging.getLogger(__name__)

# ── 1. 데이터 파싱 전용 유틸리티 ──
def _parse_llm_json(response_text: str) -> dict:
    try:
        # 텍스트 잘림 문제를 방지하기 위해 replace로 안전하게 마크다운 기호 제거
        json_str = response_text.replace("```json", "").replace("```", "").strip()
            
        data = json.loads(json_str)
        if not isinstance(data, dict):
            raise ValueError("응답 형식이 JSON 객체가 아닙니다.")
        return data
    except Exception as e:
        raise ValueError(f"파싱 실패: {e}")

# ── 2. LLM 실패 시 수동 리포트 생성기 (Fallback) ──
def _default_report(date_str: str, rec: dict, restaurants: dict, errors: list) -> str:
    """LLM이 리포트 생성을 완전히 실패했을 때 수동으로 마크다운을 조립합니다."""
    lines = [
        f"# 🗺️ 여행 리포트 ({date_str})\n",
        "## 1. 추천 지역 및 추천 이유",
        f"추천 도시: {', '.join(rec.get('recommended_cities', []))}",
        f"이유: {rec.get('reason', '정보 없음')}\n",
        "## 2. 날씨 요약",
        f"{rec.get('weather', '정보 없음')}\n",
        "## 3. 행사 / 축제 목록"
    ]
    
    events = rec.get("events", [])
    if events:
        lines.extend([f"- {e}" for e in events])
    else:
        lines.append("- 데이터 없음")

    lines.extend(["\n## 4. 맛집 리스트"])
    if restaurants:
        for city, items in restaurants.items():
            lines.append(f"\n### {city}")
            if items:
                for r in items:
                    lines.append(f"- {r.name} ({r.category}) / {r.address}")
            else:
                lines.append("- 데이터 없음 (장소 검색 결과 0건)")
    else:
        lines.append("- 데이터 없음")

    lines.extend([
        "\n## 5. 1일 여행 일정 제안", 
        "- (LLM 생성 실패로 인해 세부 일정은 제공되지 않습니다.)\n", 
        "## 오류 요약(errors)"
    ])
    
    if errors:
        for err in errors:
            lines.append(f"- **[{err.get('step', 'unknown')}]**: {err.get('type', 'ERROR')} - {err.get('message', '')}")
    else:
        lines.append("- 발생한 오류 없음")

    return "\n".join(lines)

# ── 3. 메인 AI 서비스 (1차 추천) ──
def get_travel_recommendations(date_kor: str, errors: list) -> dict:
    client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
    prompt = f"여행 날짜: {date_kor}. 실존하는 국내 여행지를 추천해 주세요."
    system_instr = "당신은 여행 전문가입니다. 반드시 JSON 객체로 응답하세요. 형식: {\"recommended_cities\": [\"도시1\", \"도시2\"], \"weather\": \"설명\", \"events\": [\"행사1\"], \"reason\": \"이유\"}"

    # 최대 2회 시도 (초기 1회 + 재시도 1회)
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
            if all(k in result for k in ["recommended_cities", "weather"]):
                return result
            else:
                raise ValueError("필수 키 누락")
        except Exception as e:
            if attempt == 1:
                # 1차 실패 시 프롬프트 보강 후 재시도
                system_instr += " (주의: 반드시 필수 키만 포함된 순수 JSON으로 출력하세요!)"
            else:
                # 2회 모두 실패 시 상세 에러 로깅
                errors.append({
                    "step": "llm_recommendation", 
                    "type": "API_ERROR", 
                    "message": f"Gemini 호출 실패 (2회 시도): {str(e)}"
                })
            
    # 최종 실패 시 기본값 반환
    return {"recommended_cities": ["부산", "경주", "전주"], "weather": "맑음", "events": [], "reason": "데이터 없음"}

# ── 4. 리포트 생성 서비스 ──
def generate_travel_report(date_str: str, rec: dict, restaurants: Dict[str, List[Restaurant]], errors: list) -> str:
    client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
    
    # 맛집 데이터를 문자열로 변환
    rest_data = ""
    for city, items in restaurants.items():
        rest_data += f"\n[{city}]\n"
        if items:
            for r in items: 
                rest_data += f"  - {r.name} ({r.category}) / {r.address}\n"
        else:
            rest_data += "  - 데이터 없음\n"

    # 축제 데이터를 문자열로 변환
    events = rec.get("events", [])
    events_text = "\n".join([f"  - {e}" for e in events]) if events else "  - 데이터 없음"

    # 프롬프트 문자열 구성 (파싱 에러 방지를 위해 일반 문자열 결합 방식 사용)
    prompt = (
        f"여행 날짜: {date_str}\n"
        f"추천 도시: {', '.join(rec.get('recommended_cities', []))}\n"
        f"날씨: {rec.get('weather', '정보 없음')}\n"
        f"행사/축제: {events_text}\n"
        f"맛집: {rest_data}\n\n"
        "[출력 템플릿 시작]\n"
        "# 🗺️ 여행 리포트 ({date_str})\n\n"
        "## 1. 추천 지역 및 추천 이유\n(추천 도시와 선정 이유를 자연스럽게 서술)\n\n"
        "## 2. 날씨 요약\n(날씨 정보를 여행자 관점에서 서술)\n\n"
        "## 3. 행사 / 축제 목록\n(제공된 행사/축제를 목록으로 정리. 없으면 '- 데이터 없음' 표기)\n\n"
        "## 4. 맛집 리스트\n(전달된 도시별 맛집 데이터를 하나도 빠짐없이 모두 나열하세요. 카테고리와 주소를 포함하고 코멘트를 추가하세요. 없으면 '- 데이터 없음' 표기)\n\n"
        "## 5. 1일 여행 일정 제안\n(추천 도시마다 '### 도시명' 소제목으로 구분하여 오전/오후/저녁 일정을 구체적으로 제안하세요.)\n"
        "[출력 템플릿 끝]"
    )

    required_sections = [
        "## 1. 추천 지역 및 추천 이유", 
        "## 2. 날씨 요약", 
        "## 3. 행사 / 축제 목록", 
        "## 4. 맛집 리스트", 
        "## 5. 1일 여행 일정 제안"
    ]
    final_report = ""

    # 최대 2회 시도 (초기 1회 + 재시도 1회)
    for attempt in range(1, 3):
        try:
            response = client.models.generate_content(
                model=os.getenv("GEMINI_MODEL_NAME"),
                contents=prompt,
                config=types.GenerateContentConfig(
                    system_instruction="지정된 5개 마크다운 헤더를 반드시 한 글자도 바꾸지 말고 유지하세요.", 
                    temperature=0.3
                )
            )
            report = response.text
            missing = [s for s in required_sections if s not in report]
            if missing:
                continue

            final_report = report
            break
        except Exception as e:
            # 리포트 생성 중 발생한 에러 기록
            errors.append({
                "step": f"report_generation_attempt_{attempt}", 
                "type": "API_ERROR", 
                "message": str(e)
            })

    # LLM이 2회 모두 리포트 생성을 실패하면 수동 리포트(default_report)로 데이터를 조립하여 반환!
    if not final_report:
        errors.append({
            "step": "report_generation_final", 
            "type": "LLM_ERROR", 
            "message": "리포트 생성 최종 실패 (수동 리포트로 대체됨)"
        })
        return _default_report(date_str, rec, restaurants, errors)

    # 성공적으로 만들어진 리포트 하단에 오류 내역 첨부
    final_report += "\n\n## 오류 요약(errors)\n"
    if errors:
        for err in errors:
            final_report += f"- **[{err.get('step')}]**: {err.get('type')} - {err.get('message')}\n"
    else:
        final_report += "- 발생한 오류 없음\n"

    return final_report