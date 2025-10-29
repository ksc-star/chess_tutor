# ===== Runtime image =====
FROM python:3.11-slim

# 기본 패키지 + Stockfish 설치
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
      stockfish ca-certificates curl && \
    rm -rf /var/lib/apt/lists/*

# 파이썬 패키지
WORKDIR /app
COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

# 앱 소스
COPY . /app

# Render는 $PORT를 전달한다. 없으면 10000 기본값.
ENV PYTHONUNBUFFERED=1

# uvicorn이 0.0.0.0:$PORT 로 리슨하도록 강제
CMD [ "bash", "-lc", "uvicorn app:app --host 0.0.0.0 --port ${PORT:-10000}" ]
