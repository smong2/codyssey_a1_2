import json
import logging
from pathlib import Path
from typing import Optional

# 로깅 설정
logger = logging.getLogger(__name__)

# 경로 상수 관리
RESULTS_DIR = Path("results")
RESULTS_DIR.mkdir(exist_ok=True)

def get_cache_path(date_str: str) -> Path:
    return RESULTS_DIR / f"{date_str}_raw.json"

def get_report_path(date_str: str) -> Path:
    return RESULTS_DIR / f"{date_str}_report.md"

def save_json_cache(date_str: str, data: dict) -> bool:
    """JSON 데이터를 캐시 파일로 저장합니다."""
    try:
        path = get_cache_path(date_str)
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        logger.info(f"데이터 저장 완료: {path.name}")
        return True
    except Exception as e:
        logger.error(f"데이터 저장 실패 ({date_str}): {e}")
        return False

def load_json_cache(date_str: str) -> Optional[dict]:
    """캐시된 JSON 데이터를 불러옵니다."""
    path = get_cache_path(date_str)
    if not path.exists():
        return None
        
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        logger.info(f"데이터 로드 완료: {path.name}")
        return data
    except (json.JSONDecodeError, IOError) as e:
        logger.error(f"데이터 로드 실패 ({date_str}): {e}")
        return None

def save_markdown_report(date_str: str, report: str) -> bool:
    """생성된 리포트를 마크다운 파일로 저장합니다."""
    try:
        path = get_report_path(date_str)
        path.write_text(report, encoding="utf-8")
        logger.info(f"리포트 저장 완료: {path.name}")
        return True
    except Exception as e:
        logger.error(f"리포트 저장 실패 ({date_str}): {e}")
        return False

def load_markdown_report(date_str: str) -> Optional[str]:
    """기존 리포트를 불러옵니다."""
    path = get_report_path(date_str)
    if path.exists():
        try:
            return path.read_text(encoding="utf-8")
        except IOError as e:
            logger.error(f"리포트 로드 실패: {e}")
    return None