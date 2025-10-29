FROM python:3.11-slim

# 시스템 패키지 (stockfish 포함)
RUN apt-get update && \
    apt-get install -y --no-install-recommends stockfish curl && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

# 파이썬 의존성
COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

# 앱 소스
COPY . /app

# Render가 주는 동적 $PORT로 반드시 바인딩
# (시작 로그를 찍어 헬스체크 트러블슈팅에 도움)
CMD ["bash","-lc","echo Starting on PORT=$PORT; uvicorn app:app --host 0.0.0.0 --port $PORT"]

