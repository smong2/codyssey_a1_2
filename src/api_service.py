import os
import re
import logging
import requests
from dataclasses import dataclass, field
from typing import List, Optional

logger = logging.getLogger(__name__)

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
    # (이미지 검색 로직 동일 유지)
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
    except Exception as e:
        return []

# ── 2. 맛집 검색 서비스 ──
def search_restaurants(query: str, errors: list, limit: int = 5) -> list:
    client_id = os.getenv("NAVER_CLIENT_ID")
    client_secret = os.getenv("NAVER_CLIENT_SECRET")
    city_name = query.split()[0]
    
    if not client_id or not client_secret:
        errors.append({"step": f"place_search_{city_name}", "type": "KEY_MISSING", "message": "네이버 API 키 미설정"})
        return []

    url = "https://openapi.naver.com/v1/search/local.json"
    headers = {"X-Naver-Client-Id": client_id, "X-Naver-Client-Secret": client_secret}
    params = {"query": query, "display": limit, "sort": "random"}
    
    try:
        response = requests.get(url, headers=headers, params=params, timeout=10)
        response.raise_for_status()
        return response.json().get("items", [])
        
    # [수정됨] 상세한 HTTP 에러 포착
    except requests.exceptions.HTTPError as e:
        status = e.response.status_code
        if status in (401, 403, 429):
            msg = f"HTTP {status} (인증/쿼터 오류: 키 값을 확인하세요)"
        else:
            msg = f"HTTP {status} (요청 오류)"
            
        errors.append({"step": f"place_search_{city_name}", "type": "AUTH_ERROR" if status in (401, 403) else "HTTP_ERROR", "message": msg})
        logger.error(f"네이버 API 에러: {msg}")
        return []
        
    except requests.exceptions.RequestException as e:
        errors.append({"step": f"place_search_{city_name}", "type": "NETWORK_ERROR", "message": str(e)})
        return []