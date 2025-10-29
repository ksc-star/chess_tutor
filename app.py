# app.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel
import traceback

from tutor import analyze_position, format_engine_summary, llm_explain

app = FastAPI(title="GPT + Stockfish Chess Tutor")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# 정적 파일은 /static 에만 마운트 (API가 가려지지 않도록)
app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/")
def root():
    return FileResponse("static/index.html")

class AnalyzeRequest(BaseModel):
    fen: str
    played_san: str | None = None
    level: str = "beginner"
    depth: int = 16
    multipv: int = 3

@app.post("/analyze")
def analyze(req: AnalyzeRequest):
    payload = {"fen": req.fen, "engine_summary": "", "gpt_explain": ""}

    # 1) Stockfish 분석 (실패해도 서버는 200으로 에러 메시지 포함)
    try:
        engine_info = analyze_position(
            fen=req.fen,
            depth=req.depth,
            multipv=req.multipv,
            played_san=req.played_san
        )
        payload["engine_summary"] = format_engine_summary(engine_info)
    except Exception as e:
        payload["engine_summary"] = f"[엔진 오류] {e}\n{traceback.format_exc()}"

    # 2) GPT 해설 (키가 없거나 호출 실패해도 계속 진행)
    try:
        gpt_text = llm_explain(
            fen=req.fen,
            engine_info=locals().get("engine_info"),
            level=req.level,
            played_san=req.played_san
        )
        payload["gpt_explain"] = gpt_text
    except Exception as e:
        payload["gpt_explain"] = f"[GPT 해설 생략] {e}"

    return JSONResponse(payload)

@app.get("/healthz")
def healthz():
    return {"status": "ok"}
