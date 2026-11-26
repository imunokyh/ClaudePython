"""@brief 시각 공급원 (ASIL B, SWE3-DD 5.1).

패키지에서 시스템 시계를 읽는 유일한 모듈이다(SWE2-ARC G-3, DR-5).
Web 앱은 MonotonicClock만 쓰고, ScriptedClock은 시험 하니스만 쓴다.
"""

from __future__ import annotations

import time
from typing import Protocol


class Clock(Protocol):
    """@brief 평가 시각을 주는 객체."""

    def now(self) -> float:
        """@brief 현재 시각 (초)."""
        ...


class MonotonicClock:
    """@brief 실시간 단조 시계 (time.monotonic)."""

    def now(self) -> float:
        """@brief 단조 증가하는 현재 시각 (초)."""
        return time.monotonic()


class ScriptedClock:
    """@brief 시험 벡터 시각을 넣는 시계 (시험 하니스 전용)."""

    def __init__(self, start: float = 0.0) -> None:
        """@brief 시작 시각을 정한다.

        @param start 시작 시각 (초)
        """
        self._now = start

    def now(self) -> float:
        """@brief 저장된 시각."""
        return self._now

    def set(self, value: float) -> None:
        """@brief 시각을 지정한다."""
        self._now = value

    def advance(self, delta: float) -> None:
        """@brief 시각을 delta초 앞으로 옮긴다."""
        self._now += delta
