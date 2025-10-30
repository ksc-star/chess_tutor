import os
import shutil
import chess
import chess.engine
from openai import OpenAI

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

STOCKFISH_PATH = _find_stockfish_path()

# --- 도우미 함수 ---

def get_system_prompt(level: str, context: str) -> str:
    level = level.lower()
    if level == "intermediate":
        prompt_base = "당신은 체스 중급자를 위한 전문 튜터입니다."
    elif level == "advanced":
        prompt_base = "당신은 체스 고급자를 위한 마스터 레벨 분석가입니다."
    else: # beginner
        prompt_base = "당신은 체스 초보자를 위한 친절한 체스 튜터입니다. 쉽고 명확하게 설명합니다."

    if context == "explain_next":
        return f"{prompt_base} FEN 포지션과 엔진이 추천한 최적의 수를 받으면, 왜 그 수가 좋은지 해당 레벨에 맞게 설명합니다."
    if context == "evaluate_move":
        return f"{prompt_base} 사용자가 방금 둔 수에 대해 평가합니다. 최적의 수와 사용자의 수를 비교하여, 왜 잘했는지 또는 실수했는지 그 이유를 해당 레벨에 맞게 설명합니다."
    if context == "chat":
        return f"{prompt_base} FEN과 사용자의 질문을 받고, 해당 레벨에 맞게 답변합니다."
    return prompt_base

def classify_move(score_diff: int) -> str:
    if score_diff >= -10: return "최고의 수"
    if score_diff >= -50: return "좋은 수"
    if score_diff >= -100: return "부정확한 수"
    if score_diff >= -200: return "실수"
    return "블런더"

# --- API 1: 현재 위치 분석 ---

def analyze_position_for_next_move(fen: str, level: str, depth: int, multipv: int):
    """현재 FEN에서 "다음 최적의 수"를 분석합니다."""
    
    with chess.engine.SimpleEngine.popen_uci(STOCKFISH_PATH) as eng:
        board = chess.Board(fen)
        limit = chess.engine.Limit(depth=depth)
        info = eng.analyse(board, limit=limit, multipv=multipv)

        if not info:
            return "분석 실패.", "(GPT 해설 불가)", {}

        r0 = info[0]
        best_move_uci = r0["pv"][0].uci() if r0.get("pv") else "N/A"
        score_obj = r0.get("score")
        
        # ▼▼▼ [수정] score_obj가 None인지 아닌지 확인 ▼▼▼
        if score_obj and score_obj.is_mate():
            engine_summary = f"최적의 수: {best_move_uci} (메이트까지 {score_obj.white().mate()}수)"
        elif score_obj: # None이 아니고 메이트도 아닐 때
            score_cp = score_obj.white().score(mate_score=100000)
            score_pawns = round(score_cp / 100.0, 2)
            engine_summary = f"최적의 수: {best_move_uci} (평가: {score_pawns:+.2f})"
        else: # score_obj가 None일 때
            engine_summary = f"최적의 수: {best_move_uci} (평가: N/A)"
            
        try:
            best_move_san = board.san(chess.Move.from_uci(best_move_uci))
        except:
            best_move_san = best_move_uci

        gpt_explanation = llm_explain_next_move(fen, best_move_san, level)
        
        return engine_summary, gpt_explanation, info

def llm_explain_next_move(fen: str, best_san: str, level: str) -> str:
    key = os.environ.get("OPENAI_API_KEY", "")
    if not key: return "(GPT 해설 비활성화)"
    if best_san == "N/A": return "(해설 생성 불가)"

    try:
        client = OpenAI(api_key=key)
        system_prompt = get_system_prompt(level, "explain_next")
        user_prompt = f"현재 포지션(FEN): {fen}\n엔진 추천 수: {best_san}\n\n이 수가 왜 좋은 수인지 {level} 수준으로 설명해 주세요."
        
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.3, max_tokens=150
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        return f"(GPT 해설 생성 중 오류: {e})"

# --- API 2: 방금 둔 수 평가 ---

def evaluate_played_move(fen_before: str, uci_move: str, level: str):
    """사용자가 방금 둔 수를 평가합니다."""
    
    try:
        board = chess.Board(fen_before)
        played_move = chess.Move.from_uci(uci_move)
        played_move_san = board.san(played_move)
    except Exception as e:
        return f"잘못된 수입니다: {uci_move}", f"(오류: {e})"

    with chess.engine.SimpleEngine.popen_uci(STOCKFISH_PATH) as eng:
        # 1. 최적의 수는 무엇이었나?
        limit = chess.engine.Limit(depth=14)
        info_best = eng.analyse(board, limit=limit, multipv=1)
        
        if not info_best:
            return "분석 실패.", "(GPT 해설 불가)"

        best_move = info_best[0]["pv"][0]
        best_move_san = board.san(best_move)
        
        # ▼▼▼ [수정] .get("score")로 안전하게 접근하고, None일 경우 0으로 처리 ▼▼▼
        best_score_obj = info_best[0].get("score")
        best_score_cp = 0
        if best_score_obj:
            best_score_cp = best_score_obj.white().score(mate_score=100000)
        
        # 2. 내가 둔 수의 점수는?
        board.push(played_move)
        info_played = eng.analyse(board, limit=chess.engine.Limit(depth=12))
        
        # ▼▼▼ [수정] info_played가 비어있을 수 있음 ▼▼▼
        if not info_played:
            return "둔 수 분석 실패.", "(GPT 해설 불가)"

        # ▼▼▼ [수정] .get("score")로 안전하게 접근하고, None일 경우 0으로 처리 ▼▼▼
        played_score_obj = info_played[0].get("score")
        played_score_cp = 0
        if played_score_obj:
            played_score_cp = played_score_obj.white().score(mate_score=100000)

        # 3. 비교 및 요약
        score_diff = played_score_cp - best_score_cp
        move_quality = classify_move(score_diff)
        
        best_pawns = round(best_score_cp / 100.0, 2)
        played_pawns = round(played_score_cp / 100.0, 2)

        engine_summary = (
            f"평가: {move_quality}\n"
            f"내가 둔 수: {
