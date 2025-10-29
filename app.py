from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List
import tutor

app = FastAPI(title="GPT + Stockfish Chess Tutor")

# CORS (필요시)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------- Health check ----------
@app.get("/ping")
def ping():
    return {"ok": True}

# ---------- 요청/응답 스키마 ----------
class AnalyzeRequest(BaseModel):
    fen: str
    played_san: Optional[str] = None
    depth: int = 16
    multipv: int = 1

class Line(BaseModel):
    san: str
    uci: str
    score_cp: Optional[int] = None
    score_mate: Optional[int] = None

class AnalyzeResponse(BaseModel):
    best_san: str
    best_uci: str
    lines: List[Line]
    engine: str

# ---------- 분석 API ----------
@app.post("/analyze", response_model=AnalyzeResponse)
def analyze(req: AnalyzeRequest):
    try:
        info = tutor.analyze_position(
            fen=req.fen,
            played_san=req.played_san,
            depth=req.depth,
            multipv=req.multipv,
        )
        return AnalyzeResponse(**info)
    except tutor.EngineNotFound as e:
        # 사용성 위해 명확한 500 메시지
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"analyze failed: {e}")
