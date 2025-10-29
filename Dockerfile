FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DEBIAN_FRONTEND=noninteractive

# Stockfish 설치
RUN apt-get update && apt-get install -y --no-install-recommends \
      stockfish ca-certificates curl && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY app.py tutor.py ./

# Render가 $PORT 를 주입함. 기본값 10000.
ENV PORT=10000

# 0.0.0.0 로 바인딩 (헬스체크용)
CMD ["sh", "-c", "uvicorn app:app --host 0.0.0.0 --port ${PORT:-10000} --proxy-headers"]

