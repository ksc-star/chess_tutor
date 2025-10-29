from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional

from tutor import analyze_position

app = FastAPI(title="GPT + Stockfish Chess Tutor")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

class AnalyzeRequest(BaseModel):
    fen: str
    played_san: Optional[str] = None
    depth: int = 16
    multipv: int = 1

@app.get("/ping")
def ping():
    return {"ok": True}

@app.get("/healthz")
def healthz():
    return {"status": "ok"}

@app.post("/analyze")
def analyze(req: AnalyzeRequest):
    try:
        res = analyze_position(
            fen=req.fen,
            played_san=req.played_san,
            depth=req.depth,
            multipv=req.multipv,
        )
        return res
    except Exception as e:
        # 로그에만 자세한 에러가 남고, 클라이언트에는 요약 전달
        raise HTTPException(status_code=500, detail=str(e))
