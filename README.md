# codyssey_a1_2

# 🗺️ 날짜 기반 국내 여행 리포트 생성기 (Travel Report Generator)

이 프로젝트는 사용자가 입력한 특정 날짜를 기반으로 Google Gemini(LLM)와 **Naver Local Search API**를 활용하여 맞춤형 국내 여행지를 추천하고, 해당 지역의 맛집 정보와 1일 여행 일정을 포함한 마크다운 리포트를 자동 생성하는 CLI(Command Line Interface) 파이썬 프로그램입니다.

## 1. 프로그램 개요

본 프로그램은 다음과 같은 자동화된 파이프라인을 통해 동작합니다.

1. **LLM 1차 추천**: 입력된 날짜를 바탕으로 추천 지역, 날씨 요약, 축제 정보를 JSON 형태로 응답받습니다.
2. **지역 맛집 검색**: 추천된 도시 이름을 검색어로 삼아 네이버 지역 검색 API를 호출하여 맛집 5곳의 상세 정보(좌표 포함)를 수집합니다.
3. **데이터 캐싱**: LLM 추천 결과와 맛집 검색 결과를 조합하여 `results/` 폴더에 원본 JSON 파일로 저장합니다. (동일 날짜 재실행 시 API 비용 절감을 위해 이 캐시 데이터를 우선 활용합니다.)
4. **최종 리포트 생성**: 수집된 모든 데이터를 바탕으로 LLM이 지정된 마크다운 템플릿(5개 목차)을 엄격하게 준수하여 최종 여행 리포트를 작성합니다.

## 2. 개발 및 실행 환경

- **Language**: Python 3.10 이상 권장
- **Dependencies**: `requests`, `google-genai`, `python-dotenv`



**2-1 Docker**

도커를 사용하여 환경을 구성한 후 도커 내에서 실행합니다.

 [Docker 구성](./document/0.docker.md)



**2.2 패키지 설치 명령어: (도커에서 스크립트로 존재하지만 따로 설치한다면)**

```
pip install requests google-genai python-dotenv
```

## 3. 실행 방법

터미널(CLI) 환경에서 필수 파라미터인 `--date` 옵션과 함께 날짜를 `YYYY-MM-DD` 형식으로 입력하여 실행합니다.

```
python3 main.py --date 2026-07-09
```

- **입력값 검증**: 날짜 형식이 올바르지 않거나 옵션이 누락된 경우, 프로그램은 실행을 즉시 중단하고 직관적인 한글 에러 메시지와 올바른 사용 예시를 출력합니다.

## 4. API 키 설정 및 ⚠️ 보안 주의사항

이 프로그램은 외부 API(Google Gemini, Naver)를 사용하므로 반드시 개인 API 키가 필요합니다. **API 키가 소스 코드에 하드코딩되거나 외부에 유출되지 않도록 각별히 주의해야 합니다.** 프로젝트 최상단 폴더에 `.env` 파일을 생성하고 아래 양식에 맞춰 본인의 키를 입력하세요.

`.env` **파일 작성 예시:**

```
# Google Gemini API
GEMINI_API_KEY="본인의_제미나이_API_키"
GEMINI_MODEL_NAME="gemini-3.1-flash-lite" # 또는 사용하고자 하는 모델명

# Naver Local Search API
NAVER_CLIENT_ID="본인의_네이버_클라이언트_ID"
NAVER_CLIENT_SECRET="본인의_네이버_시크릿_키"
```

🚨 **보안 주의사항 (매우 중요)**

- 환경변수(`.env`)를 사용하는 이유: 협업 및 코드 공유 시 실수로 개인 키가 공개되는 것을 원천 차단하기 위함입니다.
- 깃허브(GitHub) 등 버전 관리 시스템에 코드를 업로드할 때는 반드시 최상단 `.gitignore` 파일에 `.env`를 추가하여 **API 키가 공개 저장소에 푸시(Push)되지 않도록 해야 합니다.**
- API 키가 노출될 경우 무단 사용으로 인한 막대한 과금이나 서비스 이용 제한(Quota 초과) 사고가 발생할 수 있습니다.

## 5. 결과물 확인 방법

프로그램 실행이 완료되면 프로젝트 폴더 내에 `results/` 폴더가 자동 생성되며, 입력한 날짜를 기준으로 다음 두 개의 파일이 저장됩니다.

1. **원본 데이터 (**`results/YYYY-MM-DD_raw.json`**)**
  - LLM의 1차 추천 결과(JSON)
  - 네이버 API가 반환한 지역별 맛집 5곳의 상세 정보(이름, 주소, 카테고리, URL, KATEC ➜ WGS84 좌표 변환값)
  - 실행 중 발생한 예외 상황 리스트(`errors` 배열)
2. **최종 여행 리포트 (**`results/YYYY-MM-DD_report.md`**)**
  - 추천 지역/이유, 날씨 요약, 축제 목록, 맛집 리스트, 1일 여행 일정 제안(복수 지역일 경우 지역별 소제목 구분)이 포함된 최종 마크다운 문서입니다.

## 6. 💡 핵심 학습 포인트 (과제 목표 달성)

본 프로젝트를 수행하며 구현한 핵심 기술 및 배움 포인트입니다.

- **REST API 요청/응답 구조 및 HTTP 메서드 (GET vs POST)**
  - **GET**: 서버의 데이터를 조회할 때 사용합니다. 본 프로젝트에서는 `requests.get()`을 사용하여 네이버 지역 검색 API(`search/local.json`)에서 맛집 데이터를 쿼리 파라미터(`?query=...`)로 받아올 때 활용했습니다.
  - **POST**: 서버에 데이터를 제출하거나 복잡한 처리(생성)를 요청할 때 사용합니다. Gemini LLM에 프롬프트를 전송하여 새로운 텍스트 콘텐츠를 생성(`generate_content`)할 때 내부적으로 사용됩니다.
- **LLM 출력 결과의 구조화(JSON) 및 파이프라인 연동**
  - LLM 프롬프트에 "반드시 JSON 객체로 응답하라"는 지시어를 부여하고, 응답 텍스트 내의 마크다운 기호(`json` )를 정제하여 완벽한 `dict` 객체로 파싱하는 로직을 구현했습니다.
  - 파싱된 JSON 데이터의 `recommended_cities` 배열 값을 반복문으로 순회하며 네이버 장소 검색 API의 검색어(query)로 활용함으로써, "LLM의 출력이 다음 API의 입력으로 연결되는 자동화 흐름"을 완성했습니다.
- **외부 API 예외 처리 (오류 및 대응 원칙)**
  - **네트워크/인증 오류 (HTTP 401/403 등)**: 네이버 API 호출 시 예외를 포착하여 프로그램 중단 없이 빈 리스트(`[]`)를 반환합니다. 이를 통해 맛집 섹션을 '데이터 없음'으로 유연하게 처리하고 다음 리포트 생성 단계로 무사히 넘어갈 수 있습니다.
  - **LLM 파싱 오류 (Hallucination)**: LLM이 JSON 형식을 어겼을 경우 즉각 실패 처리하지 않고, 최대 3회까지 재시도하는 로직을 구현하여 운영 안정성을 확보했습니다.
  - 모든 에러는 내부 로깅 시스템(`logging` 모듈)을 거쳐 최종 리포트 하단 `errors` 섹션에 요약됩니다.

## 7. json 구조

```
{
  "recommendation": {
    "recommended_cities": [
      "평창",
      "강릉",
      "제주도"
    ],
    "weather": "2월 하순의 늦겨울 날씨로, 강원도 지역은 눈이 남아있어 설경을 즐기기 좋고 제주도는 따뜻한 기운이 감돌기 시작합니다.",
    "events": [
      "평창 대관령 눈꽃축제",
      "제주 들불축제 준비 기간"
    ],
    "reason": "2월 20일은 겨울의 끝자락으로, 평창과 강릉에서는 겨울 정취를 만끽할 수 있는 설경 여행이 가능하며, 제주도는 봄꽃이 피기 전 한적하고 여유로운 여행을 즐기기에 최적의 시기입니다."
  },
  "restaurants": {
    "평창": [
      {
        "name": "평창한우마을 대관령점",
        "address": "강원특별자치도 평창군 대관령면 경강로 5195-25",
        "category": "음식점>한식>육류,고기요리>소고기구이",
        "url": "https://blog.naver.com/pchwtown",
        "x": 128.7021685,
        "y": 37.6799009
      },
      {
        "name": "평창한우마을 면온점",
        "address": "강원특별자치도 평창군 봉평면 진조길 57",
        "category": "음식점>한식>육류,고기요리>소고기구이",
        "url": "http://www.pchw.co.kr/",
        "x": 128.3464794,
        "y": 37.5602426
      },
      {
        "name": "평창한우다래",
        "address": "강원특별자치도 평창군 봉평면 태기로 120 평창한우다래",
        "category": "한식>소고기구이",
        "url": "http://www.daraetown.com/",
        "x": 128.323733,
        "y": 37.5863524
      },
      {
        "name": "메밀꽃향기",
        "address": "강원특별자치도 평창군 봉평면 이효석길 33-5",
        "category": "한식>막국수",
        "url": "http://www.봉평맛집.com",
        "x": 128.3595836,
        "y": 37.6105777
      },
      {
        "name": "메밀꽃필무렵",
        "address": "강원특별자치도 평창군 봉평면 이효석길 33-13",
        "category": "한식>막국수",
        "url": "https://youtube.com/@gasanhouse",
        "x": 128.3603365,
        "y": 37.6109425
      }
    ],
    "강릉": [
      {
        "name": "강릉짬뽕순두부 동화가든 본점",
        "address": "강원특별자치도 강릉시 초당순두부길77번길 15 동화가든",
        "category": "한식>두부요리",
        "url": "https://www.donghwagarden.com",
        "x": 128.9146711,
        "y": 37.7911711
      },
      {
        "name": "카페 이진리",
        "address": "강원특별자치도 강릉시 임영로 234 이진리",
        "category": "음식점>카페,디저트",
        "url": "https://bio.site/easily",
        "x": 128.8925757,
        "y": 37.762023
      },
      {
        "name": "테라로사 커피공장 강릉본점",
        "address": "강원특별자치도 강릉시 구정면 현천길 7",
        "category": "카페,디저트>카페",
        "url": "https://terarosa.com",
        "x": 128.8920266,
        "y": 37.6964984
      },
      {
        "name": "강릉 수제 어묵고로케",
        "address": "강원특별자치도 강릉시 금성로13번길 8 1층",
        "category": "분식>종합분식",
        "url": "http://eomukcroquette.com/",
        "x": 128.8992102,
        "y": 37.7539609
      },
      {
        "name": "배니닭강정",
        "address": "강원특별자치도 강릉시 금성로13번길 3-1 (성남동)",
        "category": "음식점>치킨,닭강정",
        "url": "http://smartstore.naver.com/gsbaenni",
        "x": 128.8991435,
        "y": 37.7542324
      }
    ],
    "제주도": [
      {
        "name": "우진해장국",
        "address": "제주특별자치도 제주시 서사로 11",
        "category": "한식>향토음식",
        "url": "",
        "x": 126.5199459,
        "y": 33.5115338
      },
      {
        "name": "이춘옥원조고등어쌈밥 제주애월본점",
        "address": "제주특별자치도 제주시 애월읍 일주서로 7213",
        "category": "한식>쌈밥",
        "url": "https://www.instagram.com/jeju_gossam",
        "x": 126.4186804,
        "y": 33.488986
      },
      {
        "name": "모루쿠다 서귀포올레시장점",
        "address": "제주특별자치도 서귀포시 태평로431번길 32 1층 모루쿠다 서귀포올레시장점",
        "category": "한식>해물,생선요리",
        "url": "https://www.instagram.com/jejusujeyori/",
        "x": 126.566138,
        "y": 33.2482301
      },
      {
        "name": "고집돌우럭 중문점",
        "address": "제주특별자치도 서귀포시 일주서로 879",
        "category": "한식>향토음식",
        "url": "http://www.instagram.com/gozip_jeju",
        "x": 126.4166927,
        "y": 33.2579999
      },
      {
        "name": "동문올레수산 동문시장 본점",
        "address": "제주특별자치도 제주시 관덕로14길 10 동문올레수산 동문시장 본점",
        "category": "한식>생선회",
        "url": "https://blog.naver.com/tlqndi2001",
        "x": 126.5261814,
        "y": 33.5122472
      }
    ]
  },
  "errors": []
}
```

## 8. md file

root@309bfd7c44a0:/app/src# python3 main.py  --date 2020-02-21

# ❄️ 2월의 끝자락, 겨울과 봄 사이의 낭만 여행 리포트

2월 20일, 겨울의 마지막 페이지를 장식할 특별한 여행을 계획하고 계신가요? 설원의 순수함과 다가오는 봄의 싱그러움을 모두 만끽할 수 있는 여행지를 소개합니다.

---

## 1. 추천 지역 및 추천 이유

이번 여행지로 **평창, 강릉, 제주도**를 추천합니다. 2월 하순은 겨울의 끝자락으로, 강원도의 평창과 강릉은 여전히 눈 덮인 아름다운 설경을 즐기기에 최적이며, 제주도는 봄꽃이 피기 전 가장 한적하고 여유로운 풍경을 선사합니다. 겨울의 정취와 봄의 설렘을 동시에 느끼고 싶은 여행자에게 최고의 선택지가 될 것입니다.

## 2. 날씨 요약

- **평창 & 강릉:** 늦겨울의 차가운 공기가 남아있지만, 따스한 햇살이 비치기 시작합니다. 눈 덮인 산간 지역을 여행할 때는 따뜻한 외투가 필수입니다.
- **제주도:** 육지보다 한결 포근한 기운이 감돕니다. 가벼운 외투를 겹쳐 입는 레이어드 룩으로 여행하기 좋으며, 봄이 오는 길목에서 산책을 즐기기 딱 좋은 날씨입니다.

## 3. 행사 / 축제 목록

- **평창:** 평창 대관령 눈꽃축제
- **제주도:** 제주 들불축제 준비 기간

## 4. 맛집 리스트

### 🏔️ 평창

- **평창한우마을 (대관령점/면온점):** [한식/소고기구이] 강원도 평창군 대관령면 경강로 5195-25 / 입안에서 살살 녹는 최고급 평창 한우의 참맛.
- **평창한우다래:** [한식/소고기구이] 강원도 평창군 봉평면 태기로 120 / 현지인이 사랑하는 정갈한 소고기 구이 전문점.
- **메밀꽃향기 / 메밀꽃필무렵:** [한식/막국수] 강원도 평창군 봉평면 이효석길 / 봉평의 정취가 담긴 담백한 메밀 막국수 한 그릇.

### 🌊 강릉

- **동화가든 본점:** [한식/두부요리] 강원도 강릉시 초당순두부길77번길 15 / 줄 서서 먹는 칼칼하고 고소한 짬뽕순두부의 원조.
- **카페 이진리 / 테라로사 커피공장:** [카페] 강릉시 임영로 234 / 강릉의 커피 향기를 온몸으로 느낄 수 있는 감성적인 공간.
- **수제 어묵고로케 / 배니닭강정:** [분식] 강원도 강릉시 금성로13번길 / 강릉 중앙시장에서 꼭 맛봐야 할 길거리 간식의 끝판왕.

### 🌴 제주도

- **우진해장국:** [한식/향토음식] 제주시 서사로 11 / 부드럽게 풀린 고사리가 일품인 제주의 대표 해장국.
- **이춘옥원조고등어쌈밥:** [한식/쌈밥] 제주시 애월읍 일주서로 7213 / 바다를 보며 즐기는 든든한 고등어 쌈밥 한 상.
- **모루쿠다 / 고집돌우럭:** [한식/해물] 서귀포시 일대 / 제주 바다의 신선함을 가득 담은 정성스러운 해물 요리.
- **동문올레수산:** [한식/생선회] 제주시 관덕로14길 10 / 동문시장에서 만나는 싱싱하고 가성비 좋은 활어회.

---

## 5. 1일 여행 일정 제안

### ### 평창

- **오전:** 대관령 눈꽃축제장에서 화려한 눈 조각과 설경 감상
- **오후:** 평창한우마을에서 든든한 점심 식사 후, 이효석 문학관 산책
- **저녁:** 메밀꽃필무렵에서 따뜻한 막국수로 여행 마무리

### ### 강릉

- **오전:** 동화가든에서 짬뽕순두부로 활기차게 시작
- **오후:** 강릉 중앙시장에서 수제 어묵고로케와 배니닭강정 맛보기
- **저녁:** 테라로사 커피공장에서 향긋한 커피와 함께 여유로운 밤 산책

### ### 제주도

- **오전:** 우진해장국에서 아침 식사 후, 들불축제 준비가 한창인 들판 산책
- **오후:** 애월 해안도로 드라이브 및 이춘옥 고등어쌈밥에서 점심 식사
- **저녁:** 동문시장에서 신선한 회를 포장해 숙소에서 제주 밤바다를 보며 힐링 타임

## 오류 요약(errors)

- 발생한 오류 없음

---

## 캐시된 데이터는 저장된 리포트를 로딩함

root@309bfd7c44a0:/app/src# python3 [main.py](http://main.py) --date 2026-07-09

📅 여행 날짜: 2026년 07월 09일

2026-07-08 17:35:28 [INFO] file_manager: 데이터 로드 완료: 2026-07-09_raw.json

  ✅ 캐시 데이터 발견

---

# 🗺️ 여행 리포트 (2026-01-22)

## 1. 추천 지역 및 추천 이유
추천 도시: 부산, 경주, 전주
이유: 데이터 없음

## 2. 날씨 요약
맑음

## 3. 행사 / 축제 목록
- 데이터 없음

## 4. 맛집 리스트

### 부산
- 데이터 없음 (장소 검색 결과 0건)

### 경주
- 데이터 없음 (장소 검색 결과 0건)

### 전주
- 데이터 없음 (장소 검색 결과 0건)

## 5. 1일 여행 일정 제안
- (LLM 생성 실패로 인해 세부 일정은 제공되지 않습니다.)

## 오류 요약(errors)
- **[llm_recommendation]**: API_ERROR - Gemini 호출 실패 (2회 시도): 401 UNAUTHENTICATED. {'error': {'code': 401, 'message': 'Request had invalid authentication credentials. Expected OAuth 2 access token, login cookie or other valid authentication credential. See https://developers.google.com/identity/sign-in/web/devconsole-project.', 'status': 'UNAUTHENTICATED', 'details': [{'@type': 'type.googleapis.com/google.rpc.ErrorInfo', 'reason': 'ACCESS_TOKEN_TYPE_UNSUPPORTED', 'metadata': {'method': 'google.ai.generativelanguage.v1beta.GenerativeService.GenerateContent', 'service': 'generativelanguage.googleapis.com'}}]}}
- **[place_search_부산]**: AUTH_ERROR - HTTP 401 (인증/쿼터 오류: 키 값을 확인하세요)
- **[place_search_경주]**: AUTH_ERROR - HTTP 401 (인증/쿼터 오류: 키 값을 확인하세요)
- **[place_search_전주]**: AUTH_ERROR - HTTP 401 (인증/쿼터 오류: 키 값을 확인하세요)
- **[report_generation_attempt_1]**: API_ERROR - 401 UNAUTHENTICATED. {'error': {'code': 401, 'message': 'Request had invalid authentication credentials. Expected OAuth 2 access token, login cookie or other valid authentication credential. See https://developers.google.com/identity/sign-in/web/devconsole-project.', 'status': 'UNAUTHENTICATED', 'details': [{'@type': 'type.googleapis.com/google.rpc.ErrorInfo', 'reason': 'ACCESS_TOKEN_TYPE_UNSUPPORTED', 'metadata': {'method': 'google.ai.generativelanguage.v1beta.GenerativeService.GenerateContent', 'service': 'generativelanguage.googleapis.com'}}]}}
- **[report_generation_attempt_2]**: API_ERROR - 401 UNAUTHENTICATED. {'error': {'code': 401, 'message': 'Request had invalid authentication credentials. Expected OAuth 2 access token, login cookie or other valid authentication credential. See https://developers.google.com/identity/sign-in/web/devconsole-project.', 'status': 'UNAUTHENTICATED', 'details': [{'@type': 'type.googleapis.com/google.rpc.ErrorInfo', 'reason': 'ACCESS_TOKEN_TYPE_UNSUPPORTED', 'metadata': {'service': 'generativelanguage.googleapis.com', 'method': 'google.ai.generativelanguage.v1beta.GenerativeService.GenerateContent'}}]}}
- **[report_generation_final]**: LLM_ERROR - 리포트 생성 최종 실패 (수동 리포트로 대체됨)

---

## 프로젝트 특징

안정적인 데이터 파이프라인: API 호출 실패 시에도 프로그램을 종료하지 않고, "데이터 없음" 처리 및 오류 기록을 통해 끝까지 리포트를 완성합니다. (최대 2회까지 재시도 수행)

효율적인 캐싱: 동일한 날짜로 재실행할 경우 API 호출을 건너뛰어 비용과 시간을 절약합니다.