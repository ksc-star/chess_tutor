# tutor.py
import os
import shutil
from typing import Optional, List, Dict, Any

import chess
import chess.engine

# -------- Stockfish 경로 자동 결정 (환경변수 > PATH 탐색 > 리눅스 기본 경로) --------
STOCKFISH_PATH = (
    os.getenv("STOCKFISH_PATH")
    or shutil.which("stockfish")
    or "/usr/games/stockfish"
)

def _board_from_fen(fen: str) -> chess.Board:
    try:
        return chess.Board(fen)
    except Exception as e:
        raise ValueError(f"Invalid FEN: {e}")

def analyze_position(
    fen: str,
    played_san: Optional[str] = None,
    depth: int = 12,
    multipv: int = 3,
) -> Dict[str, Any]:
    """
    Stockfish로 현재 국면을 분석.
    - fen: 현재 FEN
    - played_san: 직전 착수(SAN). 없으면 None
    - depth: 탐색 깊이
    - multipv: 상위 후보수 (1~3 권장)
    반환: { 'lines': [...], 'best': {...}, 'played_san': 'e4' | None, ... }
    """
    board = _board_from_fen(fen)

    # 엔진 열기
    try:
        eng = chess.engine.SimpleEngine.popen_uci(STOCKFISH_PATH)
    except FileNotFoundError:
        raise FileNotFoundError(
            f"Stockfish not found. Tried: {STOCKFISH_PATH}. "
            "Set STOCKFISH_PATH env var or install stockfish."
        )

    try:
        # 멀티PV 분석
        limit = chess.engine.Limit(depth=max(1, int(depth)))
        analysis: List[chess.engine.InfoDict] = eng.analyse(
            board, limit=limit, multipv=max(1, int(multipv))
        )

        # 결과 정리
        lines = []
        best_entry = None
        for idx, info in enumerate(analysis, start=1):
            move_obj = info.get("pv", [None])[0]
            if move_obj is not None:
                san = board.san(move_obj)
            else:
                san = None

            score = info.get("score")
            mate = score.mate() if score else None
            cp = score.white().score(mate_score=100000) if score else None

            rec = {
                "rank": idx,
                "san": san,
                "mate": mate,
                "cp": cp,
            }
            lines.append(rec)
            if idx == 1:
                best_entry = rec

        return {
            "stockfish_path": STOCKFISH_PATH,
            "played_san": played_san,
            "lines": lines,
            "best": best_entry,
            "depth": depth,
            "multipv": multipv,
        }
    finally:
        eng.quit()

def format_engine_summary(info: Dict[str, Any]) -> str:
    """엔진 요약을 사람이 읽기 좋게 한 줄/여러 줄 문자열로 생성"""
    lines = info.get("lines", [])
    hdr = f"[Depth {info.get('depth')}, MultiPV {info.get('multipv')}]"
    if not lines:
        return hdr + " No engine lines."

    parts = [hdr]
    for rec in lines:
        rank = rec.get("rank")
        san = rec.get("san")
        mate = rec.get("mate")
        cp = rec.get("cp")
        if mate is not None:
            score_str = f"mate {mate}"
        elif cp is not None:
            score_str = f"cp {cp}"
        else:
            score_str = "n/a"
        parts.append(f"#{rank}: {san} ({score_str})")
    return "\n".join(parts)

# ------------------------- LLM (선택) 설명 -------------------------
# openai 패키지 v2 스타일. 키가 없거나 오류면 문구만 반환하여 API 전체 실패를 막음.
def llm_explain(prompt: str, level: str = "beginner") -> str:
    """
    GPT 설명(선택). OPENAI_API_KEY 없으면 엔진만 보여주고, 여기서 안내 문구 반환.
    """
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        return "(LLM disabled: set OPENAI_API_KEY to enable explanations)"

    try:
        from openai import OpenAI
        client = OpenAI(api_key=api_key)
        sys_msg = (
            "You are a concise chess tutor. Explain ideas clearly with short bullets. "
            f"Audience level: {level}."
        )
        resp = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": sys_msg},
                {"role": "user", "content": prompt},
            ],
            temperature=0.4,
        )
        return resp.choices[0].message.content
    except Exception as e:
        return f"(LLM error: {e})"
