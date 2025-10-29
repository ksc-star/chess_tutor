# app.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
import chess
from tutor import analyze_position, format_engine_summary, llm_explain

app = FastAPI(title="GPT + Stockfish Chess Tutor")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- API ---
class AnalyzeRequest(BaseModel):
    fen: str
    played_san: str | None = None
    level: str = "beginner"
    depth: int = 16
    multipv: int = 3

class AnalyzeResponse(BaseModel):
    summary: str
    explanation: str

@app.post("/analyze", response_model=AnalyzeResponse)
def analyze(req: AnalyzeRequest):
    res = analyze_position(req.fen, req.played_san, req.depth, req.multipv)
    summary = format_engine_summary(res)
    explanation = llm_explain(summary, level=req.level)
    return AnalyzeResponse(summary=summary, explanation=explanation)

# --- (선택) 서버에서 UCI 적용 API를 쓰는 경우 유지 ---
class MoveRequest(BaseModel):
    fen: str
    uci: str

class MoveResponse(BaseModel):
    ok: bool
    fen: str | None = None
    san: str | None = None
    error: str | None = None

@app.post("/move", response_model=MoveResponse)
def apply_move(req: MoveRequest):
    try:
        board = chess.Board(req.fen)
        move = chess.Move.from_uci(req.uci)
    except Exception as e:
        return MoveResponse(ok=False, error=str(e))
    if move not in board.legal_moves:
        return MoveResponse(ok=False, error="Illegal move")
    san = board.san(move)
    board.push(move)
    return MoveResponse(ok=True, fen=board.fen(), san=san)

# --- 정적파일: /static 경로로 고정 ---
app.mount("/static", StaticFiles(directory="static", html=True), name="static")

# 루트는 index.html 제공
@app.get("/")
def root():
    return FileResponse("static/index.html")
