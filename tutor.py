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


def _pv_to_san_list(board: chess.Board, pv:
