import chess  # <-- 1. chess 임포트 추가
from fastapi.responses import FileResponse
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles  # <-- 2. StaticFiles 임포트 추가
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from tutor import (
    analyze_position_for_next_move, # 이름 변경
    evaluate_played_move,           # 새 함수 임포트
    llm_chat_response
)

app = FastAPI(title="GPT + Stockfish Chess Tutor")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# 3. /static 경로로 static 폴더를 서빙하도록 마운트
app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/")
async def get_index():
    return FileResponse("index.html")

# ---- health check ----
@app.get("/ping")
def ping():
    return {"ok": True}

# ---- "현재 위치" 분석 API (기존 /analyze) ----
# ▼▼▼ 2. Pydantic 모델 이름 변경 ▼▼▼
class AnalyzePositionRequest(BaseModel):
    fen: str
    played_san: str | None = None # 이 파라미터는 이제 사용되지 않을 수 있음
    depth: int = 14
    multipv: int = 1
    level: str = "beginner"

# ▼▼▼ 3. 엔드포인트 경로 변경: /analyze -> /analyze_position ▼▼▼
@app.post("/analyze_position")
def analyze_position(req: AnalyzePositionRequest):
    
    # ▼▼▼ 4. 호출할 함수 변경 ▼▼▼
    summary, gpt_explanation, info = analyze_position_for_next_move(
        fen=req.fen,
        level=req.level,
        depth=req.depth,
        multipv=req.multipv
    )
    
    return {
        "engine_summary": summary,
        "gpt_explain": gpt_explanation,
        "info": info,
    }

# ▼▼▼ 5. "방금 둔 수" 분석 API (신규 추가) ▼▼▼
class AnalyzeMoveRequest(BaseModel):
    fen_before: str
    uci_move: str
    level: str = "beginner"

@app.post("/analyze_move")
def analyze_move(req: AnalyzeMoveRequest):
    
    summary, gpt_explanation = evaluate_played_move(
        fen_before=req.fen_before,
        uci_move=req.uci_move,
        level=req.level
    )
    
    return {
        "engine_summary": summary,
        "gpt_explain": gpt_explanation,
    }

class AskRequest(BaseModel):
    fen: str
    question: str
    level: str = "beginner"

@app.post("/ask")
def ask(req: AskRequest):
    answer = llm_chat_response(
        fen=req.fen,
        question=req.question,
        level=req.level
    )
    return {"answer": answer}

# 9. /explain 엔드포인트는 더 이상 필요 없으므로 삭제 (선택 사항)
# class ExplainRequest(BaseModel):
#     ...
# @app.post("/explain")
#     ...
