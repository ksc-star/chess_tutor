from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from tutor import analyze_position, format_engine_summary, llm_explain  # tutor.py에 존재

app = FastAPI(title="GPT + Stockfish Chess Tutor")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---- health check ----
@app.get("/ping")
def ping():
    return {"ok": True}

# ---- analyze API ----
class AnalyzeRequest(BaseModel):
    fen: str
    played_san: str | None = None
    depth: int = 14
    multipv: int = 1

@app.post("/analyze")
def analyze(req: AnalyzeRequest):
    info = analyze_position(
        fen=req.fen,
        played_san=req.played_san,
        depth=req.depth,
        multipv=req.multipv,
    )
    return {
        "summary": format_engine_summary(info),
        "info": info,
    }

# 선택: 간단 LLM 설명 (키가 있을 때만 내부에서 사용)
class ExplainRequest(BaseModel):
    fen: str
    best_san: str

@app.post("/explain")
def explain(req: ExplainRequest):
    return {"text": llm_explain(req.fen, req.best_san)}
