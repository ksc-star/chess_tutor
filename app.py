# app.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import chess  # python-chess
from tutor import analyze_position, format_engine_summary, llm_explain

app = FastAPI(title="GPT + Stockfish Chess Tutor")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],   # 배포 안정화 후 자신의 도메인만 허용 권장
    allow_methods=["*"],
    allow_headers=["*"],
)

# 헬스체크/테스트용
@app.get("/ping")
def ping():
    return {"ok": True}

# ---------- 분석 API ----------
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

# ---------- 움직임 적용 API (서버가 합법성 체크 + FEN 갱신) ----------
class MoveRequest(BaseModel):
    fen: str
    uci: str  # 예: "e2e4", "e7e8q"

class MoveResponse(BaseModel):
    ok: bool
    fen: str | None = None
    san: str | None = None
    error: str | None = None

@app.post("/move", response_model=MoveResponse)
def apply_move(req: MoveRequest):
    try:
        board = chess.Board(req.fen)
    except Exception as e:
        return MoveResponse(ok=False, error=f"Bad FEN: {e}")

    try:
        move = chess.Move.from_uci(req.uci)
    except Exception as e:
        return MoveResponse(ok=False, error=f"Bad UCI: {e}")

    if move not in board.legal_moves:
        return MoveResponse(ok=False, error="Illegal move")

    san = board.san(move)
    board.push(move)
    return MoveResponse(ok=True, fen=board.fen(), san=san)

# ---------- 정적 파일 서비스 (index.html 루트 노출) ----------
app.mount("/", StaticFiles(directory="static", html=True), name="static")
