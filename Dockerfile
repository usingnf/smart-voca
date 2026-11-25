# 2026-11-25 - 클로드 스마트 보카 - 학교 서버 배포용 이미지 (웹 API + 화면, 단일 워커)
# 파일 위치: Dockerfile
# 빌드: 리포 루트에서 docker build -t smart-voca .
# 실행 예: docker run -p 8080:8080 -v voca-data:/data -e ALLOWED_HOSTS=<접속 호스트> smart-voca

FROM python:3.13-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# 1) 의존성 파일만 먼저 복사해 설치한다. 소스만 바뀌면 이 층은 캐시를 재사용한다.
COPY requirements-server.txt ./
RUN pip install --no-cache-dir -r requirements-server.txt

# 2) 소스와 단어 파일을 복사한다. 단어 파일은 이미지 안에서 읽기 전용으로 둔다.
COPY src/ ./src/
COPY web/ ./web/
COPY data/voca.csv ./data/voca.csv

# 3) 실행 전용 사용자(UID 10001)를 만들고, 쓰기 가능한 데이터 폴더 /data를 이 사용자 소유로 만든다.
RUN groupadd --system --gid 10001 app \
    && useradd --system --uid 10001 --gid 10001 --no-create-home --home-dir /nonexistent --shell /usr/sbin/nologin app \
    && mkdir -p /data \
    && chown 10001:10001 /data

# ALLOWED_HOSTS=*: 앞단 프록시가 보내는 Host 이름(학교 주소, 점검 환경의 front 등)을 모두 받는다.
# 앱에는 로그인이 없으므로 접근 제한은 앞단(학교 서버)에서 한다.
ENV SMARTVOCA_DATA_DIR=/data \
    VOCA_PATH=/app/data/voca.csv \
    DB_PATH=/data/voca.db \
    ALLOWED_HOSTS=*

USER 10001:10001

EXPOSE 8080

# 워커는 1개로 둔다. 시험 진행 정보(QuizRegistry)가 프로세스 메모리에 있어서 워커를 나누면 채점 요청이 다른 프로세스로 가 실패한다.
CMD ["uvicorn", "--app-dir", "web", "app:create_app", "--factory", "--host", "0.0.0.0", "--port", "8080", "--workers", "1", "--no-server-header"]
