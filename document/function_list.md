## 프로젝트 주요 함수 정의서

- 이 프로그램은 CLI 기반의 여행지 추천 및 리포트 자동 생성 시스템입니다. 각 함수는 데이터 흐름에 따라 체계적으로 설계되었습니다.

### 1. 입력 및 검증

```
parse_date(value: str) -> datetime
parse_args()
```

- 설명: 사용자가 CLI로 입력한 날짜(YYYY-MM-DD) 문자열을 파이썬 datetime 객체로 변환하고 형식을 검증합니다. 잘못된 형식 입력 시 argparse.ArgumentTypeError를 발생시켜 프로그램 실행을 방지합니다.

### 2. 캐시 및 데이터 관리

```
_cache_path(date_str: str) -> Path
```

- 설명: 특정 날짜에 대한 원본 데이터 저장 경로를 생성합니다(results/ 폴더 하위).

```
_save_cache(date_str: str, data: dict)
```

- 설명: API 호출로 수집된 데이터를 JSON 형식으로 파일에 저장합니다.

```
_load_cache(date_str: str) -> dict | None
```

- 설명: 이미 존재하는 캐시 데이터를 불러옵니다. 데이터가 있으면 API 호출을 생략하여 비용과 시간을 절약합니다.

```
_save_report(date_str: str, report: str)
```

- 설명: 최종 생성된 Markdown 형식의 여행 리포트를 파일로 저장합니다.

```
_load_report(date_str: str) -> str | None
```

- 설명: 이미 생성된 리포트 파일이 있는지 확인하고 불러옵니다.

### 3. API 연동 및 비즈니스 로직

```
get_recommendation(date_kor: str, errors: list) -> dict
```

- 설명: Gemini API를 사용하여 날짜에 맞는 여행지를 추천받습니다. JSON 파싱 실패 시 프롬프트를 보완하여 1회 재시도하는 로직이 포함되어 있습니다.

```
search_restaurants(city: str, errors: list, limit: int = 5) -> list
```

- 설명: 네이버 지역 검색 API를 통해 특정 도시의 맛집 정보를 수집합니다. 좌표 데이터(KATEC)를 위경도로 변환하며, 에러 발생 시 빈 리스트를 반환하여 프로그램의 안정성을 유지합니다.

```
generate_report(...) -> str
```

- 설명: 수집된 여행지 정보, 맛집, 에러 요약을 바탕으로 Gemini AI를 호출하여 최종 여행 리포트를 Markdown 형식으로 작성합니다. 섹션 누락 방지를 위한 검증 로직이 포함되어 있습니다.

```
_default_report(...) -> str
```

- 설명: 모든 API가 실패하거나 리포트 생성이 불가능할 경우, 수집된 데이터를 그대로 표기하는 기본 리포트를 생성합니다.

```
 _default_recommendation() -> dict:
```

- 설명 : 추천 API 가 실패할 때 가져와서 사용할 수 있는 기본 추천지역을 담은 딕셔너리입니다.

### 4. 실행 및 흐름 제어

```
main()
```

- 설명: 프로그램의 진입점입니다. argparse로 CLI 인자를 받고, 캐시 확인 -> API 호출 -> 결과 저장 -> 리포트 출력의 전 과정을 관장합니다. 발생한 모든 에러 정보를 errors 리스트에 담아 최종적으로 처리합니다.
