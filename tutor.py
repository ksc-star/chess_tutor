# tutor.py
import os
import chess
import chess.engine
from typing import List, Dict, Any

# --- Stockfish 세팅 ---
STOCKFISH_PATH = os.environ.get("STOCKFISH_PATH", "stockfish")  # Dockerfile에서 apt로 설치됨

def analyze_position(fen: str, played_san: str | None, depth: int = 16, multipv: int = 3) -> List[Dict[str, Any]]:
    """python-chess로 Stockfish 분석 결과(MPV) 반환"""
    board = chess.Board(fen)
    limit = chess.engine.Limit(depth=depth)

    with chess.engine.SimpleEngine.popen_uci(STOCKFISH_PATH) as eng:
        info = eng.analyse(board, limit, multipv=multipv)
        # info는 리스트 또는 단일 dict 형태 -> 리스트 형태로 통일
        if isinstance(info, dict):
            info = [info]

        out = []
        for i in info:
            pv = i.get("pv", [])
            uci_line = [m.uci() for m in pv]
            score = i.get("score")
            cp = score.white().score(mate_score=100000) if score else None
            out.append({
                "uci_line": uci_line,
                "cp": cp,
            })
        return out

def format_engine_summary(results: List[Dict[str, Any]]) -> str:
    """엔진 다변량 변형(MPV) 요약 텍스트"""
    lines = []
    for idx, r in enumerate(results, start=1):
        cp = r["cp"]
        score_str = f"{cp/100:+.2f}" if cp is not None and abs(cp) < 5000 else ("#mate" if cp else "?")
        principal = " ".join(r["uci_line"][:6])  # 너무 길면 앞 6수만
        lines.append(f"[{idx}] eval {score_str}  |  {principal}")
    return "\n".join(lines) if lines else "(no engine lines)"

# --- LLM 설명 ---
from openai import OpenAI
_client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

def llm_explain(engine_summary: str, level: str = "beginner") -> str:
    """엔진 요약을 독자 수준에 맞춰 자연어 설명으로 변환"""
    prompt = f"""
You are a chess coach. Explain these engine lines for a {level} player.
Focus on ideas, plans, tactical motifs, and why lines are good/bad.
Engine summary:
{engine_summary}
"""
    try:
        resp = _client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7,
            max_tokens=350,
        )
        return resp.choices[0].message.content.strip()
    except Exception as e:
        return f"(LLM error) {e}"
