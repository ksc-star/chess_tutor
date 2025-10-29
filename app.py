# app.py
import os
from typing import Optional, Any, Dict

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel

import tutor

app = FastAPI(title="GPT + Stockfish Chess Tutor")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------- 정적 파일 (프론트) ----------
# 리포에 static/index.html이 있다고 가정
if os.path.isdir("static"):
    app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/")
def root() -> Any:
    index_path = os.path.join("static", "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return {"ok": True, "msg": "static/index.html not found"}

# ---------- 핑/헬스 ----------
@app.get("/ping")
def ping() -> Dict[str, Any]:
    return {"ok": True}

@app.get("/healthz")
def healthz() -> Dict[str, Any]:
    return {"status": "ok"}

# ---------- 분석 API ----------
class AnalyzeRequest(BaseModel):
    fen: str
    played_san: Optional[str] = None
    level: str = "beginner"
    depth: int = 12
    multipv: int = 2

@app.post("/analyze")
def analyze(req: AnalyzeRequest) -> Dict[str, Any]:
    """
    본문: {fen, played_san?, level?, depth?, multipv?}
    반환: {engine: {...}, summary: "...", gpt: "..."}
    """
    try:
        engine_info = tutor.analyze_position(
            fen=req.fen,
            played_san=req.played_san,
            depth=req.depth,
            multipv=req.multipv,
        )
        summary = tutor.format_engine_summary(engine_info)
    except Exception as e:
        # 프론트에서 에러 메시지 표시 가능하게 반환
        raise HTTPException(status_code=400, detail=f"engine_error: {e}")

    # LLM 실패해도 전체 실패시키지 않음
    prompt = (
        "Summarize the position and the suggested line(s) below for a learner.\n\n"
        + summary
    )
    explain = tutor.llm_explain(prompt, level=req.level)

    return {
        "engine": engine_info,
        "summary": summary,
        "gpt": explain,
    }
