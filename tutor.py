import os
import json
from typing import Any, Dict, List, Optional

import chess
import chess.engine

# 환경변수 없을 때도 항상 동작하도록 확정 기본값 제공
# (Render 컨테이너에 기본 설치 위치)
STOCKFISH_PATH = os.environ.get("STOCKFISH_PATH") or "/usr/games/stockfish"


def _score_to_dict(score: chess.engine.PovScore, turn: chess.Color) -> Dict[str, Any]:
    """python-chess 점수를 직렬화 가능한 dict로 변환."""
    # 현재 수순의 관점으로 통일
    pov = score.pov(turn)
    if pov.is_mate():
        return {"type": "mate", "value": pov.mate()}
    return {"type": "cp", "value": pov.score()}


def _pv_to_san_list(board: chess.Board, pv: List[chess.Move]) -> List[str]:
    """PV를 SAN 문자열 리스트로 변환 (원본 보드 보존)."""
    b = board.copy(stack=False)
    sans: List[str] = []
    for mv in pv:
        sans.append(b.san(mv))
        b.push(mv)
    return sans


def analyze_position(
    fen: str,
    played_san: Optional[str],
    depth: int = 16,
    multipv: int = 1,
) -> Dict[str, Any]:
    """
    Stockfish로 포지션 분석.
    - fen: FEN 문자열
    - played_san: 방금 둔 수(SAN). 있으면 보드에 적용한 상태에서 분석
    - depth: 탐색 깊이
    - multipv: 상위 해변가(라인) 개수
    반환: 직렬화 가능한 dict
    """
    if not fen:
        raise ValueError("fen must be provided")

    board = chess.Board(fen)

    # 방금 둔 수가 있으면 적용 (실패해도 전체 실패로 만들지 않음)
    if played_san:
        try:
            board.push_san(played_san)
        except Exception as e:  # 잘못된 SAN이면 무시하고 진행
            pass

    # 엔진 열기
    with chess.engine.SimpleEngine.popen_uci(STOCKFISH_PATH) as eng:
        # 가볍게 기본 옵션 (필요시 조정)
        try:
            eng.configure({"Threads": 1, "Hash": 64})
        except Exception:
            pass

        # 분석 실행
        info_list = eng.analyse(
            board,
            chess.engine.Limit(depth=depth),
            multipv=max(1, int(multipv)),
        )

    # multipv=1이면 dict, 그 이상이면 list가 올 수 있으므로 통일
    if isinstance(info_list, dict):
        info_list = [info_list]

    lines: List[Dict[str, Any]] = []
    for idx, info in enumerate(info_list, start=1):
        # python-chess의 키 접근은 엔진 버전에 따라 다를 수 있어 .get 사용
        score = info.get("score")
        pv = info.get("pv", [])
        depth_out = info.get("depth")
        seldepth = info.get("seldepth")
        nps = info.get("nps")
        time_ms = info.get("time")  # 초 단위가 들어올 수 있음

        line: Dict[str, Any] = {
            "multipv": info.get("multipv", idx),
            "depth": depth_out,
            "seldepth": seldepth,
            "nps": nps,
            "time": time_ms,
        }

        if score is not None:
            line["score"] = _score_to_dict(score, board.turn)

        if pv:
            try:
                line["pv_san"] = _pv_to_san_list(board, pv)
                # 첫 수를 bestmove로 표기
                line["bestmove_san"] = line["pv_san"][0] if line["pv_san"] else None
            except Exception:
                line["pv_san"] = []
                line["bestmove_san"] = None

        lines.append(line)

    return {
        "engine": {
            "path": STOCKFISH_PATH,
            "depth": depth,
            "multipv": multipv,
        },
        "position": {
            "fen": board.fen(),
            "turn": "white" if board.turn else "black",
        },
        "lines": lines,
        "summary": format_engine_summary({"lines": lines}),
    }


def format_engine_summary(result: Dict[str, Any]) -> str:
    """
    analyze_position 결과에서 첫 라인을 짧게 요약.
    """
    lines = result.get("lines") or []
    if not lines:
        return "No engine lines."

    top = lines[0]
    parts: List[str] = []

    bm = top.get("bestmove_san")
    if bm:
        parts.append(f"Best: {bm}")

    sc = top.get("score")
    if sc:
        if sc.get("type") == "mate":
            parts.append(f"Mate in {sc.get('value')}")
        elif sc.get("type") == "cp":
            # 센티폰을 폰 값으로도 같이 표기
            cp = sc.get("value")
            parts.append(f"Eval {cp}cp (~{cp/100:.2f}p)")

    d = top.get("depth")
    if d is not None:
        parts.append(f"D{d}")

    return " | ".join(parts) if parts else "No summary."


def llm_explain(text: str) -> str:
    """
    (옵션) LLM 설명. OPENAI_API_KEY 없으면 빈 문자열 반환.
    """
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        return ""

    try:
        # SDK 없이 간단히 requests 사용(외부 의존 줄이기)
        import requests  # type: ignore

        payload = {
            "model": "gpt-4o-mini",
            "input": text,
        }
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }
        # 최신 API 스펙에 맞게 엔드포인트 조정 (필요 시 사용자 환경에 맞춰 수정)
        resp = requests.post("https://api.openai.com/v1/responses", headers=headers, json=payload, timeout=30)
        resp.raise_for_status()
        data = resp.json()
        out = (
            data.get("output_text")
            or data.get("choices", [{}])[0].get("message", {}).get("content")
            or ""
        )
        return str(out).strip()
    except Exception:
        return ""
