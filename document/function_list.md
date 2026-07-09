# 🐍 프로젝트 함수 명세서 (Function Reference)

프로젝트를 구성하는 4개의 핵심 파이썬 파일(`api_service.py`, `file_manager.py`, `llm_service.py`, `main.py`)에 정의된 함수들의 역할과 기능 요약입니다.

## 1. `api_service.py` (외부 API 통신 담당)

외부 검색 API(네이버)와의 통신 및 데이터 변환을 담당하는 모듈입니다.

- `Restaurant.from_naver_api(cls, item: dict)` (클래스 메서드)
  - 네이버 지역 검색 API가 반환한 원시 딕셔너리(`dict`) 데이터를 파싱하여, 내부에서 다루기 편한 `Restaurant` 데이터 객체로 변환합니다. KATEC 좌표를 WGS84 기반의 실수형(`float`) x, y 좌표로 변환하는 과정도 포함되어 있습니다.
- `get_naver_images(query: str, display: int = 5) -> List[str]`
  - 검색어(`query`)를 기반으로 네이버 이미지 검색 API를 호출하여, 이미지 URL 리스트를 가져오는 함수입니다.
- `search_restaurants(query: str, limit: int = 5) -> List[dict]`
  - 추천된 지역명을 기반으로 네이버 지역 검색 API(`local.json`)를 호출하여 맛집 데이터를 가져옵니다. 누락되는 결과를 방지하기 위해 관련도순(`random`)으로 결과를 반환합니다.

## 2. `file_manager.py` (파일 입출력 및 캐싱 담당)

JSON 데이터 및 마크다운 리포트 파일의 로컬 입출력(I/O)을 담당하는 모듈입니다.

- `get_cache_path(date_str: str) -> Path`
  - 입력된 날짜를 기준으로 원본 JSON 데이터(캐시)가 저장될 파일 경로(`results/YYYY-MM-DD_raw.json`)를 생성하여 반환합니다.
- `get_report_path(date_str: str) -> Path`
  - 입력된 날짜를 기준으로 최종 여행 리포트가 저장될 마크다운 파일 경로(`results/YYYY-MM-DD_report.md`)를 생성하여 반환합니다.
- `save_json_cache(date_str: str, data: dict) -> bool`
  - LLM 추천 결과와 맛집 정보가 병합된 딕셔너리 데이터를 JSON 파일로 안전하게 기록(캐싱)합니다.
- `load_json_cache(date_str: str) -> Optional[dict]`
  - 저장된 JSON 캐시 파일이 있다면 읽어와 딕셔너리로 반환하고, 없거나 오류가 나면 `None`을 반환합니다.
- `save_markdown_report(date_str: str, report: str) -> bool`
  - 최종 완성된 텍스트 형태의 여행 리포트를 마크다운(`.md`) 파일 형식으로 기록합니다.
- `load_markdown_report(date_str: str) -> Optional[str]`
  - 저장된 리포트 파일이 존재할 경우 파일의 내용을 읽어와 문자열로 반환합니다.

## 3. `llm_service.py` (LLM 생성 및 데이터 파싱 담당)

Google Gemini AI를 호출하여 여행지를 추천받고 보고서를 생성하는 모듈입니다.

- `_parse_llm_json(response_text: str) -> dict` (내부 유틸리티)
  - LLM이 응답한 텍스트 데이터에 섞여 있는 마크다운 찌꺼기(예: `json` )를 깔끔하게 제거하고 순수 JSON 객체(딕셔너리)로 변환해 주는 전처리 함수입니다.
- `get_travel_recommendations(date_kor: str, errors: list) -> dict`
  - 해당 날짜에 어울리는 여행지, 날씨, 행사 정보를 담은 JSON 형태의 1차 추천 결과를 Gemini API로부터 생성받아 반환합니다. 형식이 어긋날 경우 최대 3회 재시도합니다.
- `generate_travel_report(date_str: str, rec: dict, restaurants: Dict[str, List[Restaurant]], errors: list) -> str`
  - 1차 추천 정보와 도시별 맛집 데이터를 바탕으로 Gemini API를 호출하여, 지정된 5개의 목차 양식(템플릿)을 엄격하게 지킨 최종 마크다운 여행 리포트를 작성합니다.

## 4. `main.py` (프로그램 흐름 및 CLI 제어 담당)

프로그램의 진입점(Entry Point)으로 파이프라인의 전체 흐름(Controller)을 관리합니다.

- `parse_date(value: str) -> datetime`
  - CLI로 입력받은 값이 정확한 날짜 포맷(`YYYY-MM-DD`)인지 검증하고 형 변환을 수행합니다. 실패 시 에러를 발생시킵니다.
- `KoreanArgumentParser.error(self, message)` (메서드 덮어쓰기)
  - 기본 `argparse`의 영어 에러 메시지를 차단하고, 직관적인 한글 에러 메시지와 올바른 사용 가이드를 제공하는 커스텀 에러 처리기입니다.
- `parse_args()`
  - CLI 명령어에서 `--date` 파라미터를 읽고 파싱 하는 역할을 합니다.
- `process_full_pipeline(date_str: str, date_kor: str, errors: list)`
  - 캐시된 파일이 없을 때 실행되는 **전체 자동화 파이프라인**입니다. (LLM 추천 ➜ 네이버 맛집 검색 ➜ 데이터 JSON 저장 ➜ 최종 리포트 생성 및 저장)
- `process_cached_pipeline(date_str: str, cached_data: dict, errors: list)`
  - 이미 저장된 원본 데이터(JSON 캐시)가 있을 때 실행되는 **우회 파이프라인**입니다. 불필요한 API 호출을 건너뛰고 기존 데이터를 객체화하여 리포트만 재사용 또는 재생성합니다.
- `main()`
  - 프로그램의 전체 진입 함수로, 인자 파싱 결과와 캐시 유무를 바탕으로 어떤 파이프라인을 실행할지 결정하고 최종 리포트 및 오류(Errors)를 터미널에 출력합니다.

