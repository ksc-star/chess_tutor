# Dockerfile
FROM python:3.11-slim

ENV DEBIAN_FRONTEND=noninteractive \
    PIP_NO_CACHE_DIR=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Stockfish 설치
RUN apt-get update -o Acquire::Retries=3 -o Acquire::http::Timeout=30 \
 && apt-get install -y --no-install-recommends stockfish ca-certificates curl \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# 의존성
COPY requirements.txt .
RUN pip install --upgrade pip \
 && pip install --default-timeout=100 -r requirements.txt

# 앱 전체 (static 포함)
COPY . .

# Render의 PORT 사용
CMD ["sh","-c","uvicorn app:app --host 0.0.0.0 --port ${PORT:-10000}"]
