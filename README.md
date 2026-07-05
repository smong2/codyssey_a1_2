# codyssey_a1_2

# 🗺️ 인터넷 정보를 받아와서 여행지 추천해주는 파이썬 프로그램 만들기

## 1. 프로그램 개요

이 프로그램은 사용자가 여행 날짜를 입력하면, AI(Gemini)를 통해 여행지를 추천받고, 해당 지역의 행사 및 맛집 정보를 수집하여 최종 여행 리포트를 한국어 Markdown 형식으로 자동 생성해 주는 도구입니다.

- **주요 기능**:
  - 여행지 추천 및 날씨/행사 정보 분석
  - 네이버 지역 검색 API를 통한 도시별 맛집 정보 수집
  - 최종 여행 일정 및 맛집 정보가 포함된 리포트 파일(`.md`) 생성
  - 발생 가능한 에러 상황(인증 실패, 데이터 없음 등)에 대한 자동 로그 기록

## 2. API 키 설정 방법

이 프로그램은 Google Gemini AI와 Naver Local Search API를 사용합니다. 루트 디렉토리에 `.env` 파일을 생성하고 아래 형식으로 본인의 키를 입력하세요.

1. 프로젝트 루트에 `.env` 파일 생성
2. 아래 내용을 복사하여 키 값 수정 후 저장

```env
GEMINI_API_KEY=your_gemini_api_key_here
NAVER_CLIENT_ID=your_naver_client_id_here
NAVER_CLIENT_SECRET=your_naver_client_secret_here
```

## 3. 실행방법

```
# 기본 실행

python local_search.py --date YYYY-MM-DD
```

- --date 파라미터는 필수이며, 2026-07-05와 같은 형식으로 입력해야 합니다.

## 4. 결과물 확인 방법

프로그램이 성공적으로 완료되면 results/ 디렉토리에 다음과 같은 파일들이 생성됩니다.

```
- YYYY-MM-DD_report.md: AI가 작성한 최종 여행 리포트

- YYYY-MM-DD_raw.json: 수집된 원본 데이터 및 에러 요약(errors) 기록
```

## 5.⚠️ 보안 주의 사항 (필독)

API 키 유출 금지: .env 파일에 포함된 GEMINI_API_KEY, NAVER_CLIENT_ID, NAVER_CLIENT_SECRET은 매우 중요한 개인정보라서 GitHub 업로드하지 않음

->

.gitignore 설정

```
# 보안 및 불필요 파일 제외
.env
.DS_Store
```

## 프로젝트 특징

안정적인 데이터 파이프라인: API 호출 실패 시에도 프로그램을 종료하지 않고, "데이터 없음" 처리 및 오류 기록을 통해 끝까지 리포트를 완성합니다. (최대 2회까지 재시도 수행)

효율적인 캐싱: 동일한 날짜로 재실행할 경우 API 호출을 건너뛰어 비용과 시간을 절약합니다.
