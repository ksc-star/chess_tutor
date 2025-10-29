# 베이스: slim + 필요한 패키지
FROM python:3.11-slim

# 시스템 패키지 (stockfish 포함)
RUN apt-get update && \
    apt-get install -y --no-install-recommends stockfish curl && \
    rm -rf /var/lib/apt/lists/*

# 작업 디렉토리
WORKDIR /app

# 파이썬 의존성
COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

# 앱 소스
COPY . /app

# Render가 할당한 포트 사용
ENV PORT=10000
# 헬스체크용 기본 경로 유지
ENV STOCKFISH_PATH=/usr/games/stockfish

# 컨테이너 시작 커맨드: 반드시 $PORT 바인딩
CMD ["bash", "-lc", "python -c 'import os; print(\"PORT=\", os.environ.get(\"PORT\"))' && uvicorn app:app --host 0.0.0.0 --port $PORT"]
