# app.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
import chess  # python-chess
from tutor import analyze_position, format_engine_summary, llm_explain

app = FastAPI(title="GPT + Stockfish Chess Tutor")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],   # 배포 안정화 후 도메인 제한 권장
    allow_methods=["*"],
    allow_headers=["*"],
)

# ----- 헬스체크 -----
@app.get("/ping")
def ping():
    return {"ok": True}

# ----- 분석 API -----
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

# ----- 움직임 적용 API -----
class MoveRequest(BaseModel):
    fen: str
    uci: str  # e.g., "e2e4", "e7e8q"

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

# ----- 정적 파일 -----
# /static 경로로 정적 자원 노출
app.mount("/static", StaticFiles(directory="static"), name="static")

# 루트는 index.html 반환 (정적 마운트가 라우트를 덮지 않게)
@app.get("/")
def root():
    return FileResponse("static/index.html")
