# app.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from tutor import analyze_position, format_engine_summary, llm_explain

app = FastAPI(title="GPT + Stockfish Chess Tutor")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 배포 시 필요 도메인만 허용 권장
    allow_methods=["*"],
    allow_headers=["*"],
)

class AnalyzeRequest(BaseModel):
    fen: str
    played_san: str | None = None
    level: str = "beginner"
    depth: int = 16
    multipv: int = 3

class AnalyzeResponse(BaseModel):
    summary: str
    explanation: str

@app.get("/")
def root():
    return {"ok": True, "tip": "Open /docs for API UI"}

@app.post("/analyze", response_model=AnalyzeResponse)
def analyze(req: AnalyzeRequest):
    res = analyze_position(req.fen, req.played_san, req.depth, req.multipv)
    summary = format_engine_summary(res)
    explanation = llm_explain(summary, level=req.level)
    return AnalyzeResponse(summary=summary, explanation=explanation)

from fastapi.staticfiles import StaticFiles
app.mount("/", StaticFiles(directory="static", html=True), name="static")
