from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from tutor import analyze_position, format_engine_summary, llm_explain

app = FastAPI(title="GPT + Stockfish Chess Tutor")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
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

# 분석 API (POST만 쓰므로 StaticFiles와 충돌 없음)
@app.post("/analyze", response_model=AnalyzeResponse)
def analyze(req: AnalyzeRequest):
    res = analyze_position(req.fen, req.played_san, req.depth, req.multipv)
    summary = format_engine_summary(res)
    explanation = llm_explain(summary, level=req.level)
    return AnalyzeResponse(summary=summary, explanation=explanation)

# ✅ 정적 파일을 루트에 마운트 (index.html 자동 노출)
app.mount("/", StaticFiles(directory="static", html=True), name="static")
