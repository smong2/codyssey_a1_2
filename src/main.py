import argparse
import sys
import logging
import dataclasses
from datetime import datetime
from dotenv import load_dotenv

import file_manager as fm
import llm_service as llm
import api_service as api

# [수정됨] override=True를 주어야 도커 환경에서도 수정된 .env를 실시간으로 덮어씁니다!
load_dotenv(override=True)

def parse_date(value: str) -> datetime:
    try:
        return datetime.strptime(value, "%Y-%m-%d")
    except ValueError:
        raise argparse.ArgumentTypeError(f"날짜 형식이 올바르지 않습니다: '{value}'")

class KoreanArgumentParser(argparse.ArgumentParser):
    def error(self, message):
        print("\n🚨 입력 오류가 발생했습니다.")
        if "the following arguments are required" in message:
            print("👉 필수 파라미터(--date)가 누락되었습니다.")
        else:
            print(f"👉 {message}")
        print("💡 사용 예시: python main.py --date 2026-07-09\n")
        sys.exit(2)

def parse_args():
    parser = KoreanArgumentParser(description="여행 리포트 생성기")
    parser.add_argument("--date", type=parse_date, required=True, metavar="YYYY-MM-DD")
    return parser.parse_args()

def process_full_pipeline(date_str: str, date_kor: str, errors: list):
    print(f"\n[1/3] 여행지 추천 중...")
    recommendation = llm.get_travel_recommendations(date_kor, errors)

    print("\n[2/3] 맛집 검색 중 (네이버)...")
    restaurants = {}
    for city in recommendation.get("recommended_cities", []):
        raw_items = api.search_restaurants(f"{city} 맛집", errors=errors, limit=5)
        restaurants[city] = [api.Restaurant.from_naver_api(item) for item in raw_items]

    restaurants_dict = {
        city: [dataclasses.asdict(r) for r in r_list] 
        for city, r_list in restaurants.items()
    }

    fm.save_json_cache(date_str, {
        "recommendation": recommendation,
        "restaurants": restaurants_dict,
        "errors": errors
    })

    print("\n[3/3] 리포트 생성 중...")
    report = llm.generate_travel_report(date_str, recommendation, restaurants, errors)
    fm.save_markdown_report(date_str, report)
    return report

def process_cached_pipeline(date_str: str, cached_data: dict, errors: list):
    default_rec = {"recommended_cities": ["부산", "경주", "전주"], "weather": "맑음", "events": [], "reason": "데이터 없음"}
    rec = cached_data.get("recommendation", default_rec)
    
    restaurants = {city: [api.Restaurant(**item) for item in items] 
                   for city, items in cached_data.get("restaurants", {}).items()}

    cached_report = fm.load_markdown_report(date_str)
    if cached_report:
        return cached_report

    print("\n[3/3] 리포트 생성 중 (캐시 활용)...")
    report = llm.generate_travel_report(date_str, rec, restaurants, errors)
    fm.save_markdown_report(date_str, report)
    return report

def main():
    if not os.getenv("GEMINI_API_KEY") or not os.getenv("NAVER_CLIENT_ID"):
        print("\n🚨 [오류] API 키가 설정되지 않았습니다. .env 파일을 확인하세요.")
        sys.exit(1)

    args = parse_args()
    date_str = args.date.strftime("%Y-%m-%d")
    date_kor = args.date.strftime("%Y년 %m월 %d일")
    errors = []

    print(f"📅 여행 날짜: {date_kor}")

    cached_data = fm.load_json_cache(date_str)
    
    if cached_data:
        print("  ✅ 캐시 데이터 발견")
        report = process_cached_pipeline(date_str, cached_data, errors)
    else:
        print("  ❌ 캐시 데이터 없음")
        report = process_full_pipeline(date_str, date_kor, errors)

    print("\n" + "=" * 50 + "\n📋 여행 리포트\n" + "=" * 50)
    print(report)

    if errors:
        print(f"\n⚠️  총 {len(errors)}개의 오류가 발생했습니다.")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)

if __name__ == "__main__":
    main()