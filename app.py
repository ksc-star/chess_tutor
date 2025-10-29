# app.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel

# 외부 모듈
from tutor import analyze_position, format_engine_summary, llm_explain

app = FastAPI(title="GPT + Stockfish Chess Tutor")

# CORS (브라우저 호출 가능)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# -------- 정적 파일 서빙 --------
# /static 경로로 정적 자원 제공
app.mount("/static", StaticFiles(directory="static"), name="static")

# 루트는 index.html 반환
@app.get("/")
def root():
    return FileResponse("static/index.html")


# -------- 분석 API --------
class AnalyzeRequest(BaseModel):
    fen: str
    played_san: str | None = None
    level: str = "beginner"
    depth: int = 16
    multipv: int = 3

@app.post("/analyze")
def analyze(req: AnalyzeRequest):
    """
    체스 엔진 분석 + GPT 해설을 묶어서 반환.
    tutor.py의 기존 함수들을 그대로 사용합니다.
    """
    # 엔진 분석
    engine_info = analyze_position(
        fen=req.fen,
        depth=req.depth,
        multipv=req.multipv,
        played_san=req.played_san
    )

    # 요약 텍스트
    engine_summary = format_engine_summary(engine_info)

    # GPT 해설 (동기 함수라고 가정; 비동기라면 asyncio.run 등으로 래핑)
    gpt_explain = llm_explain(
        fen=req.fen,
        engine_info=engine_info,
        level=req.level,
        played_san=req.played_san
    )

    return JSONResponse({
        "fen": req.fen,
        "engine_summary": engine_summary,
        "gpt_explain": gpt_explain
    })


# -------- 헬스체크 --------
@app.get("/healthz")
def healthz():
    return {"status": "ok"}
