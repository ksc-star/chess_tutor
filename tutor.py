import os
import shutil  # <-- 1. shutil 임포트 추가
import chess
import chess.engine
from openai import OpenAI  # <-- 2. OpenAI 임포트 추가

# ---- Stockfish 경로 자동 탐색 ----
def _find_stockfish_path() -> str:
    # 1) 환경변수 우선
    env_path = os.environ.get("STOCKFISH_PATH")
    if env_path and os.path.exists(env_path):
        return env_path

    # 2) 시스템 PATH에 있는 바이너리 (Dockerfile에서 설치 시 이 방식이 유효)
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

# 3. 함수를 호출하여 STOCKFISH_PATH 설정
STOCKFISH_PATH = _find_stockfish_path()

# ---- 엔진 분석 ----
def analyze_position(fen: str, played_san: str | None, depth: int = 16, multipv: int = 1):
    """python-chess 엔진으로 분석 후 dict 반환"""
    # [cite_start]Dockerfile에서 stockfish를 설치하므로 경로는 유효해야 함 [cite: 2]
    with chess.engine.SimpleEngine.popen_uci(STOCKFISH_PATH) as eng:
        board = chess.Board(fen)
        if played_san:
            try:
                move = board.parse_san(played_san)
                board.push(move)
            except Exception:
                pass

        limit = chess.engine.Limit(depth=depth)
        info = eng.analyse(board, limit=limit, multipv=multipv)

        out = []
        for i in info if isinstance(info, list) else [info]:
            pv = i.get("pv", [])
            best_move_uci = pv[0].uci() if pv else None
            score = i.get("score")
            out.append({
                "best_move_uci": best_move_uci,
                "score": score.white().score(mate_score=100000) if score else None,
                "mate": score.white().mate() if score and score.is_mate() else None,
            })
        return {"results": out, "fen": fen}

def format_engine_summary(result: dict) -> str:
    """간단 요약 문자열"""
    if not result or "results" not in result or not result["results"] or not result["results"][0]["best_move_uci"]:
        return "엔진 분석 결과가 없습니다."
    r0 = result["results"][0]
    bm = r0["best_move_uci"]
    if r0["mate"] is not None:
        return f"최적의 수: {bm} (메이트까지 {r0['mate']}수)"
    score_cp = r0.get('score', 0)
    score_pawns = round(score_cp / 100.0, 2)
    return f"최적의 수: {bm} (평가: {score_pawns:+.2f})"


# 4. 실제 OpenAI 호출로 llm_explain 함수 교체
def llm_explain(fen: str, best_san: str) -> str:
    """LLM을 호출하여 FEN과 최적의 수(SAN)에 대한 설명을 생성합니다."""
    key = os.environ.get("OPENAI_API_KEY", "")
    if not key:
        return "(GPT 해설 비활성화: OPENAI_API_KEY가 설정되지 않았습니다.)"
    
    if best_san == "N/A":
        return "(엔진이 추천한 수가 없어 해설을 생성할 수 없습니다.)"

    try:
        client = OpenAI(api_key=key)
        
        system_prompt = "당신은 체스 초보자를 위한 친절한 체스 튜터입니다. FEN 포지션과 엔진이 추천한 최적의 수를 받으면, 왜 그 수가 좋은지 1~2문장으로 쉽고 명확하게 설명합니다."
        user_prompt = f"현재 포지션(FEN): {fen}\n엔진 추천 수: {best_san}\n\n이 수가 왜 좋은 수인지 초보자가 이해하기 쉽게 설명해 주세요."

        response = client.chat.completions.create(
            model="gpt-4o-mini", # 또는 gpt-3.5-turbo
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.3,
            max_tokens=150,
        )
        return response.choices[0].message.content.strip()

    except Exception as e:
        print(f"OpenAI API Error: {e}")
        return f"(GPT 해설 생성 중 오류 발생: {e})"
