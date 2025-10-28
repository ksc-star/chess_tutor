# tutor.py
import chess, chess.engine
from dataclasses import dataclass
from typing import List, Optional
from openai import OpenAI
import os

STOCKFISH_PATH = "/usr/games/stockfish"  # Render 컨테이너에서 apt로 설치됨

@dataclass
class Line:
    san: str
    uci: str
    pv_san: List[str]
    score_cp: Optional[int]
    mate: Optional[int]

@dataclass
class AnalysisResult:
    fen: str
    side_to_move: str
    best: Optional[Line]
    alternatives: List[Line]
    eval_before_cp: Optional[int]
    eval_after_cp: Optional[int]
    is_blunder: bool
    cp_loss: Optional[int]

def _score_to_cp_mate(score):
    if score.is_mate(): return None, score.mate()
    return score.white().score(), None  # 백 기준 cp

def analyze_position(fen: str, played_san: Optional[str]=None, depth: int=16, multipv: int=3) -> AnalysisResult:
    board = chess.Board(fen)
    engine = chess.engine.SimpleEngine.popen_uci(STOCKFISH_PATH)
    engine.configure({"Threads": 2, "Hash": 256})

    info0 = engine.analyse(board, chess.engine.Limit(depth=depth), multipv=1)[0]
    eval_before_cp, _ = _score_to_cp_mate(info0["score"])

    infos = engine.analyse(board, chess.engine.Limit(depth=depth), multipv=multipv)
    lines: List[Line] = []
    for info in infos:
        pv = info.get("pv", [])
        if not pv: continue
        tmp = board.copy()
        pv_san = []
        for mv in pv:
            pv_san.append(tmp.san(mv)); tmp.push(mv)
        sc_cp, sc_mate = _score_to_cp_mate(info["score"])
        lines.append(Line(tmp.root().san(pv[0]), pv[0].uci(), pv_san, sc_cp, sc_mate))
    best, alts = (lines[0] if lines else None), (lines[1:] if len(lines)>1 else [])

    eval_after_cp, cp_loss, is_blunder = None, None, False
    if played_san:
        try:
            mv = board.parse_san(played_san); board.push(mv)
            info1 = engine.analyse(board, chess.engine.Limit(depth=depth), multipv=1)[0]
            eval_after_cp, _ = _score_to_cp_mate(info1["score"])
            if eval_before_cp is not None and eval_after_cp is not None:
                cp_loss = eval_before_cp - eval_after_cp
                is_blunder = cp_loss >= 150
        except Exception:
            pass

    engine.quit()
    side = "White" if board.turn == chess.WHITE else "Black"
    return AnalysisResult(fen, side, best, alts, eval_before_cp, eval_after_cp, is_blunder, cp_loss)

def format_engine_summary(a: AnalysisResult) -> str:
    def lt(tag, line: Optional[Line]):
        if not line: return f"{tag}: (none)"
        ev = f"mate in {abs(line.mate)}" if line.mate is not None else f"{line.score_cp} cp"
        return f"{tag}: {line.san} | {ev} | PV: {', '.join(line.pv_san[:6])}"
    parts = [
        f"Eval(before): {a.eval_before_cp} cp",
        f"Eval(after): {a.eval_after_cp} cp" if a.eval_after_cp is not None else "",
        f"Δeval: {a.cp_loss} cp" if a.cp_loss is not None else "",
        lt("Best", a.best)
    ] + [lt(f"Alt{i+1}", alt) for i, alt in enumerate(a.alternatives)]
    if a.is_blunder: parts.append("⚠️ Possible blunder (≥150cp loss)")
    return "\n".join(p for p in parts if p)

def build_prompt(summary: str, level: str="beginner") -> str:
    style = {
        "beginner": "초보자에게 말하듯 쉬운 한국어로 bullet 4~6줄.",
        "intermediate": "근거(약점, 활동성, 킹안전)를 구체적으로.",
        "advanced": "라인 비교·구조·장기 계획 중심."
    }.get(level, "초보자에게 말하듯 쉽게.")
    return f"""당신은 정확한 체스 코치입니다.
아래 엔진 요약을 바탕으로
- 왜 최선수가 좋은지
- (있다면) 사용자가 둔 수의 문제점
- 다음에 기억할 원칙/패턴
을 한국어로 설명하세요. {style}

[엔진 요약]
{summary}"""

def llm_explain(summary: str, level: str="beginner", model: str="gpt-5-thinking") -> str:
    key = os.getenv("OPENAI_API_KEY", "")
    if not key: return "⚠️ OPENAI_API_KEY 미설정"
    client = OpenAI(api_key=key)
    resp = client.chat.completions.create(
        model=model,
        messages=[{"role":"system","content":"You are a concise, accurate chess coach."},
                  {"role":"user","content":build_prompt(summary, level)}],
        temperature=0.2
    )
    return resp.choices[0].message.content.strip()