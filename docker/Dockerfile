# 파이썬 공식 이미지 사용
FROM python:3.10-slim

# 작업 디렉토리 설정
WORKDIR /app

# 시스템 의존성 설치 (필요시)
RUN apt-get update && apt-get install -y --no-install-recommends \
    && rm -rf /var/lib/apt/lists/*

# 요구사항 파일 복사 및 설치
# 루트에 requirements.txt를 두는 것을 권장합니다
COPY docker/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 소스 코드 복사
COPY ../src /app/src

# 작업 환경 변수
ENV PYTHONPATH=/app/src
