# tutor.py
import os, shutil
import chess, chess.engine

# ----- Stockfish 실행 경로 탐색 -----
def _stockfish_path():
    # 우선 PATH에 있는 'stockfish'
    if shutil.which("stockfish"):
        return "stockfish"
    # Debian/Ubuntu 패키지 기본 위치
    for p in ("/usr/games/stockfish", "/usr/bin/stockfish"):
        if os.path.exists(p):
            return p
    raise FileNotFoundError("Stockfish 실행 파일을 찾을 수 없습니다.")

# ----- 엔진 분석 -----
def analyze_position(fen: str, depth: int = 16, multipv: int = 3, played_san: str | None = None):
    board = chess.Board(fen)
    engine_path = _stockfish_path()
    engine = chess.engine.SimpleEngine.popen_uci(engine_path)
    try:
        info_list = engine.analyse(board, chess.engine.Limit(depth=depth), multipv=multipv)
    finally:
        engine.quit()

    lines = []
    for info in info_list:
        move = info.get("pv", [None])[0]
        score = info.get("score")
        cp = None
        mate = None
        if score is not None:
            if score.is_mate():
                mate = score.white().mate()
            else:
                cp = score.white().score(mate_score=100000)
        san = board.san(move) if move else "?"
        lines.append({"san": san, "cp": cp, "mate": mate})
    return {"lines": lines}

# ----- 엔진 요약 텍스트 -----
def format_engine_summary(engine_info: dict) -> str:
    if not engine_info or not engine_info.get("lines"):
        return "엔진 결과가 없습니다."
    out = []
    for i, l in enumerate(engine_info["lines"], 1):
        if l["mate"] is not None:
            sc = f"Mate {l['mate']}"
        elif l["cp"] is not None:
            sc = f"{l['cp']} cp"
        else:
            sc = "N/A"
        out.append(f"{i}. {l['san']} ({sc})")
    return "\n".join(out)

# ----- GPT 해설 (키 없으면 자동 생략) -----
def llm_explain(fen: str, engine_info: dict | None, level: str = "beginner", played_san: str | None = None) -> str:
    key = os.getenv("OPENAI_API_KEY")
    if not key:
        return "OPENAI_API_KEY가 설정되어 있지 않아 GPT 해설을 생략합니다."

    try:
        # 최신 openai SDK
        from openai import OpenAI
        client = OpenAI(api_key=key)
        # 간단 프롬프트
        engine_text = format_engine_summary(engine_info) if engine_info else "엔진 결과 없음"
        prompt = (
            f"FEN: {fen}\n엔진 제안 수: \n{engine_text}\n"
            f"난이도: {level}. 체스 초보자도 이해하도록 간단히 설명하세요."
        )
        resp = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "system", "content": "You are a chess coach."},
                      {"role": "user", "content": prompt}],
            temperature=0.3,
        )
        return resp.choices[0].message.content.strip()
    except Exception as e:
        return f"GPT 호출 실패: {e}"
