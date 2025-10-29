import os
import chess
import chess.engine

# ---- Stockfish 경로 자동 탐색 ----
def _find_stockfish_path() -> str:
    # 1) 환경변수 우선
    env_path = os.environ.get("STOCKFISH_PATH")
    if env_path and os.path.exists(env_path):
        return env_path

    # 2) 시스템 PATH에 있는 바이너리
    which = shutil.which("stockfish")
    if which:
        return which

    # 3) 리눅스 배포판에서 일반적인 설치 경로 후보
    candidates = [
        "/usr/games/stockfish",
        "/usr/bin/stockfish",
        "/usr/local/bin/stockfish",
    ]
    for p in candidates:
        if os.path.exists(p):
            return p

    # 4) 못 찾으면 명확한 에러 메시지
    raise FileNotFoundError(
        "Stockfish binary not found. "
        "Set env STOCKFISH_PATH or install stockfish (e.g., apt-get install stockfish)."
    )

STOCKFISH_PATH = os.getenv("STOCKFISH_PATH") or "/usr/games/stockfish"

# ---- 엔진 분석 ----
def analyze_position(fen: str, played_san: str | None, depth: int = 16, multipv: int = 1):
    """python-chess 엔진으로 분석 후 dict 반환"""
    with chess.engine.SimpleEngine.popen_uci(STOCKFISH_PATH) as eng:
        board = chess.Board(fen)
        if played_san:
            try:
                move = board.parse_san(played_san)
                board.push(move)
            except Exception:
                # played_san이 잘못 들어와도 계속 진행
                pass

        limit = chess.engine.Limit(depth=depth)
        info = eng.analyse(board, limit=limit, multipv=multipv)

        # 정리된 결과 만들기
        out = []
        for i in info if isinstance(info, list) else [info]:
            pv = i.get("pv", [])
            best_move = pv[0].uci() if pv else None
            score = i.get("score")
            out.append({
                "best_move_uci": best_move,
                "score": score.white().score(mate_score=100000) if score else None,
                "mate": score.white().mate() if score and score.is_mate() else None,
            })
        return {"results": out, "fen": fen}

def format_engine_summary(result: dict) -> str:
    """간단 요약 문자열"""
    if not result or "results" not in result or not result["results"]:
        return "No analysis."
    r0 = result["results"][0]
    bm = r0["best_move_uci"]
    if r0["mate"] is not None:
        return f"Best: {bm}, mate in {r0['mate']}"
    return f"Best: {bm}, eval ≈ {r0['score']} centipawns"

# 선택: LLM 설명 (OPENAI_API_KEY 없으면 빈 설명)
def llm_explain(fen: str, best_san: str) -> str:
    import os
    key = os.environ.get("OPENAI_API_KEY", "")
    if not key:
        return "(Explanation disabled: OPENAI_API_KEY not set.)"
    try:
        # 여기서는 키 존재만 체크하고, 외부 호출 없이 더미 설명을 반환
        return f"Why {best_san}?: Improves king safety and activity from position {fen[:30]}..."
    except Exception:
        return "(Explanation error.)"
