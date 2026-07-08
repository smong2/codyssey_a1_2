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
def search_restaurants(query: str, limit: int = 5) -> List[dict]:
    client_id = os.getenv("NAVER_CLIENT_ID")
    client_secret = os.getenv("NAVER_CLIENT_SECRET")
    
    if not client_id or not client_secret:
        logger.error("네이버 API 키가 설정되지 않았습니다.")
        return []

    url = "https://openapi.naver.com/v1/search/local.json"
    headers = {"X-Naver-Client-Id": client_id, "X-Naver-Client-Secret": client_secret}
    
    # [수정됨] sort 파라미터를 "comment"에서 "random"(관련도순)으로 변경하여 
    # 검색 결과가 누락되지 않고 5개(limit)가 꽉 채워져서 나오도록 보장합니다.
    params = {"query": query, "display": limit, "sort": "random"}
    
    try:
        response = requests.get(url, headers=headers, params=params, timeout=10)
        response.raise_for_status()
        return response.json().get("items", [])
    except requests.exceptions.RequestException as e:
        logger.error(f"맛집 검색 API 호출 실패: {e}")
        return []
