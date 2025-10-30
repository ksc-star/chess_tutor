import chess  # <-- 1. chess 임포트 추가
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles  # <-- 2. StaticFiles 임포트 추가
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from tutor import analyze_position, format_engine_summary, llm_explain

app = FastAPI(title="GPT + Stockfish Chess Tutor")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# 3. /static 경로로 static 폴더를 서빙하도록 마운트
app.mount("/static", StaticFiles(directory="static"), name="static")


# ---- health check ----
@app.get("/ping")
def ping():
    return {"ok": True}

# ---- analyze API (수정됨) ----
class AnalyzeRequest(BaseModel):
    fen: str
    played_san: str | None = None
    depth: int = 14
    multipv: int = 1

@app.post("/analyze")
def analyze(req: AnalyzeRequest):
    # 4. 엔진 분석 실행
    info = analyze_position(
        fen=req.fen,
        played_san=req.played_san,
        depth=req.depth,
        multipv=req.multipv,
    )
    
    # 5. 엔진 요약 포맷팅
    engine_summary = format_engine_summary(info)

    # 6. GPT에게 전달할 최적의 수(SAN) 찾기
    best_move_san = "N/A"
    try:
        # 엔진 결과에서 UCI(e.g., e2e4) 추출
        if info.get("results") and info["results"][0].get("best_move_uci"):
            best_move_uci = info["results"][0]["best_move_uci"]
            
            # python-chess를 사용해 FEN 기준 UCI -> SAN (e.g., e4) 변환
            board = chess.Board(req.fen)
            move = chess.Move.from_uci(best_move_uci)
            best_move_san = board.san(move)
    except Exception:
        pass # 변환 실패 시 best_move_san은 "N/A" 유지

    # 7. GPT 해설 실행
    gpt_explanation = llm_explain(req.fen, best_move_san)

    # 8. index.html이 기대하는 형식으로 응답 반환
    return {
        "engine_summary": engine_summary, # 'summary' -> 'engine_summary'
        "gpt_explain": gpt_explanation,   # GPT 결과 추가
        "info": info,                     # (디버깅용 상세 정보)
    }

# 9. /explain 엔드포인트는 더 이상 필요 없으므로 삭제 (선택 사항)
# class ExplainRequest(BaseModel):
#     ...
# @app.post("/explain")
#     ...
