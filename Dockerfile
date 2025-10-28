FROM python:3.11-slim

# Stockfish 설치
RUN apt-get update && apt-get install -y --no-install-recommends \
    stockfish ca-certificates curl && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Render에서 환경변수로 OPENAI_API_KEY를 주입하세요.
EXPOSE 8000
CMD ["uvicorn", "app:app", "--host=0.0.0.0", "--port=8000"]

# static 파일 서빙
CMD ["uvicorn", "app:app", "--host=0.0.0.0", "--port=8000", "--reload", "--root-path", "/"]