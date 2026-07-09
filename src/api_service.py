import os
import re
import logging
import requests
from dataclasses import dataclass, field
from typing import List, Optional

# 로깅 설정
logger = logging.getLogger(__name__)

# [수정됨] 요청하신 JSON 포맷과 100% 일치하도록 데이터 구조 변경
@dataclass
class Restaurant:
    name: str
    address: str
    category: str
    url: str
    x: Optional[float] = None
    y: Optional[float] = None

    @classmethod
    def from_naver_api(cls, item: dict):
        clean_name = re.sub(r"<[^>]+>", "", item.get("title", "이름 없음"))
        
        # 기존에 있던 KATEC 좌표계 실수 변환 로직 복구
        try:
            x = int(item.get("mapx", 0)) / 1e7
            y = int(item.get("mapy", 0)) / 1e7
        except (ValueError, TypeError):
            x, y = None, None

        return cls(
            name=clean_name,
            address=item.get("roadAddress") or item.get("address", "주소 없음"),
            category=item.get("category", "일반"),
            url=item.get("link", ""),
            x=x,
            y=y
        )

# ── 1. 네이버 이미지 검색 서비스 ──
def get_naver_images(query: str, display: int = 5) -> List[str]:
    client_id = os.getenv("NAVER_CLIENT_ID")
    client_secret = os.getenv("NAVER_CLIENT_SECRET")
    
    url = "https://openapi.naver.com/v1/search/image"
    params = {"query": query, "display": display}
    headers = {"X-Naver-Client-Id": client_id, "X-Naver-Client-Secret": client_secret}
    
    try:
        response = requests.get(url, params=params, headers=headers, timeout=5)
        response.raise_for_status()
        items = response.json().get('items', [])
        return [item['link'] for item in items] if items else []
    except requests.exceptions.RequestException as e:
        logger.error(f"네이버 이미지 검색 실패: {e}")
        return []

# ── 2. 맛집 검색 서비스 ──
def search_restaurants(query: str, errors: list, limit: int = 5) -> list:
    client_id = os.getenv("NAVER_CLIENT_ID")
    client_secret = os.getenv("NAVER_CLIENT_SECRET")
    
    # 지역명 추출 (예: "강릉 맛집" -> "강릉")
    city_name = query.split()[0]
    
    if not client_id or not client_secret:
        errors.append({"step": f"place_search_{city_name}", "type": "KEY_MISSING", "message": "네이버 API 키 없음"})
        logger.error("네이버 API 키가 설정되지 않았습니다.")
        return []

    url = "https://openapi.naver.com/v1/search/local.json"
    headers = {"X-Naver-Client-Id": client_id, "X-Naver-Client-Secret": client_secret}
    params = {"query": query, "display": limit, "sort": "random"}
    
    try:
        response = requests.get(url, headers=headers, params=params, timeout=10)
        response.raise_for_status()
        return response.json().get("items", [])
    except requests.exceptions.HTTPError as e:
        status = e.response.status_code
        if status in (401, 403):
            msg = f"HTTP {status} (인증 오류: 클라이언트 ID/Secret 키 값 또는 헤더명 오타 점검)"
        else:
            msg = f"HTTP {status} (API 요청 오류)"
            
        errors.append({"step": f"place_search_{city_name}", "type": "AUTH_ERROR" if status in (401, 403) else "HTTP_ERROR", "message": msg})
        logger.error(f"맛집 검색 API 실패: {msg}")
        return []
    except requests.exceptions.RequestException as e:
        errors.append({"step": f"place_search_{city_name}", "type": "NETWORK_ERROR", "message": "네트워크 또는 기타 요청 오류"})
        logger.error(f"맛집 검색 API 네트워크 실패: {e}")
        return []