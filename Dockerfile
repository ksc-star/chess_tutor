FROM python:3.11-slim

ENV DEBIAN_FRONTEND=noninteractive \
    PIP_NO_CACHE_DIR=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Stockfish 설치 (재시도/타임아웃으로 멈춤 방지)
RUN apt-get update -o Acquire::Retries=3 -o Acquire::http::Timeout=30 \
 && apt-get install -y --no-install-recommends stockfish ca-certificates curl \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# 캐시 활용을 위해 먼저 의존성
COPY requirements.txt .
RUN pip install --upgrade pip \
 && pip install --default-timeout=100 -r requirements.txt

# 앱 소스
COPY . .

# Render가 제공하는 PORT 사용
CMD ["sh","-c","uvicorn app:app --host 0.0.0.0 --port ${PORT:-10000}"]
