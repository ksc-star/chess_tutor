from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, Any, Dict

from tutor import analyze_position, format_engine_summary

app = FastAPI(title="Chess Tutor")

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
def ping() -> Dict[str, Any]:
    return {"ok": True}

@app.post("/analyze")
def analyze(req: AnalyzeRequest) -> Dict[str, Any]:
    try:
        info = analyze_position(
            fen=req.fen,
            played_san=req.played_san,
            depth=req.depth,
            multipv=req.multipv,
        )
        return {
            "summary": format_engine_summary(info),
            "engine": info,
        }
    except FileNotFoundError as e:
        # Stockfish 경로 문제를 500으로 명확히 노출
        raise HTTPException(status_code=500, detail=f"Stockfish not found: {e}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

