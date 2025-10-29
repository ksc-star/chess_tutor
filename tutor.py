import os
import shutil
import chess
import chess.engine

# ----- 커스텀 예외 -----
class EngineNotFound(RuntimeError):
    pass

def _find_stockfish_path() -> str:
    """
    우선순위:
      1) env STOCKFISH_PATH
      2) /usr/games/stockfish
      3) PATH 내 'stockfish'
    """
    cand = os.environ.get("STOCKFISH_PATH")
    if cand and os.path.exists(cand):
        return cand

    if os.path.exists("/usr/games/stockfish"):
        return "/usr/games/stockfish"

    which = shutil.which("stockfish")
    if which:
        return which

    raise EngineNotFound(
        "Stockfish 바이너리를 찾지 못했습니다. (env STOCKFISH_PATH, "
        "/usr/games/stockfish, PATH 모두 확인 실패)"
    )

def _score_to_dict(score: chess.engine.PovScore) -> dict:
    # CP 또는 mate 둘 중 하나만 채움
    if score.is_mate():
        return {"score_cp": None, "score_mate": score.mate()}
    else:
        # None 가능성 대비
        try:
            cp = score.white().score(mate_score=100000)
        except Exception:
            cp = None
        return {"score_cp": cp, "score_mate": None}

def analyze_position(
    fen: str,
    played_san: str | None,
    depth: int = 16,
    multipv: int = 1,
) -> dict:
    """
    반환 형식:
    {
      "best_san": "e4",
      "best_uci": "e2e4",
      "lines": [
         {"san":"e4","uci":"e2e4","score_cp":34,"score_mate":null}, ...
      ],
      "engine": "Stockfish 17.1"
    }
    """
    engine_path = _find_stockfish_path()

    board = chess.Board(fen=fen)

    # 사용자가 직전에 둔 수가 있으면 적용(옵션)
    if played_san:
        try:
            move = board.parse_san(played_san)
            board.push(move)
        except Exception:
            # 무시하고 그대로 진행
            pass

    # 분석
    with chess.engine.SimpleEngine.popen_uci(engine_path) as eng:
        # 엔진 이름 가져오기
        eng_name = eng.id.get("name", "Stockfish")
        # multipv는 최소 1
        mpv = max(1, int(multipv))
        limit = chess.engine.Limit(depth=max(1, int(depth)))

        info_list = eng.analyse(board, limit, multipv=mpv)

    # python-chess가 multipv=1일 땐 dict, 그 이상은 list를 줄 수 있으므로 통일
    if isinstance(info_list, dict):
        info_list = [info_list]

    # PV들을 san/uci로 정리
    lines = []
    for i in info_list:
        pv = i.get("pv", [])
        if not pv:
            continue
        first_move = pv[0]
        san = board.san(first_move)
        uci = first_move.uci()
        sc = i.get("score")
        lines.append({
            "san": san,
            "uci": uci,
            **(_score_to_dict(sc) if sc else {"score_cp": None, "score_mate": None})
        })

    if not lines:
        raise RuntimeError("엔진이 합법 수를 반환하지 않았습니다.")

    best = lines[0]
    return {
        "best_san": best["san"],
        "best_uci": best["uci"],
        "lines": lines,
        "engine": eng_name,
    }
