import os
import shutil
import chess
import chess.engine
from typing import Optional, Dict, Any, List

def _resolve_stockfish_path() -> str:
    """
    우선순위:
    1) 환경변수 STOCKFISH_PATH (절대경로 또는 실행파일명)
    2) which('stockfish')
    3) 리눅스 기본 설치 경로 /usr/games/stockfish
    """
    cand: List[str] = []
    env = os.getenv("STOCKFISH_PATH", "").strip()
    if env:
        cand.append(env)
    found = shutil.which("stockfish")
    if found:
        cand.append(found)
    cand.append("/usr/games/stockfish")

    for p in cand:
        if shutil.which(p) or os.path.isfile(p):
            return p
    raise FileNotFoundError(f"Tried: {cand}")

def analyze_position(
    fen: str,
    played_san: Optional[str],
    depth: int = 16,
    multipv: int = 1,
) -> Dict[str, Any]:
    """
    FEN을 받아 Stockfish 분석 결과를 dict로 반환.
    """
    engine_path = _resolve_stockfish_path()

    board = chess.Board(fen=fen)

    # 사용자가 방금 둔 수(옵션) 반영
    if played_san:
        try:
            board.push_san(played_san)
        except Exception as e:
            raise ValueError(f"Invalid SAN move '{played_san}': {e}")

    limit = chess.engine.Limit(depth=max(1, int(depth)))
    mpv = max(1, int(multipv))

    out: Dict[str, Any] = {
        "fen_after": board.fen(),
        "depth": int(depth),
        "multipv": int(multipv),
        "lines": [],
    }

    with chess.engine.SimpleEngine.popen_uci(engine_path) as eng:
        info = eng.analyse(board, limit, multipv=mpv)
        # python-chess는 multipv>1 이면 list, 아니면 dict
        infos = info if isinstance(info, list) else [info]

        for i, inf in enumerate(infos, start=1):
            move = inf.get("pv", [None])[0]
            uci = move.uci() if move else None
            san = board.san(move) if move else None

            score = inf.get("score")
            cp = score.white().score(mate_score=10_000) if score else None
            mate = score.white().mate() if score else None

            out["lines"].append(
                {
                    "multipv": i,
                    "bestmove_uci": uci,
                    "bestmove_san": san,
                    "cp": cp,     # +는 백 유리
                    "mate": mate, # mate in N (양수=백 메이트)
                    "pv_san": [board.san(m) for m in inf.get("pv", [])] if inf.get("pv") else [],
                }
            )
    return out

def format_engine_summary(res: Dict[str, Any]) -> str:
    if not res.get("lines"):
        return "No engine lines."
    top = res["lines"][0]
    if top.get("mate") is not None:
        eval_str = f"Mate in {top['mate']}"
    elif top.get("cp") is not None:
        # 100cp ≒ 1 pawn
        eval_str = f"{top['cp']/100:.2f} pawns"
    else:
        eval_str = "N/A"
    move_str = top.get("bestmove_san") or top.get("bestmove_uci") or "?"
    return f"Depth {res['depth']}, best: {move_str}, eval: {eval_str}"
