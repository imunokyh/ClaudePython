"""@brief 제어결정 기록 (QM, SWE3-DD 3.2).

최근 100건만 메모리에 보존한다(SWR-012). 영상·음성·개인 식별자·원시
입력값은 저장하지 않고, SWR-011의 11개 필드만 기록한다.
"""

from __future__ import annotations

from collections import deque

from child_lock.types import EVENT_CAPACITY, Decision, EventRecord


class EventLog:
    """@brief 제어결정 기록 저장소 (프로세스 메모리 전용)."""

    def __init__(self, capacity: int = EVENT_CAPACITY) -> None:
        """@brief 빈 기록을 만든다.

        @param capacity 보존할 최대 건수
        """
        self._records: deque[EventRecord] = deque(maxlen=capacity)
        self._next_id = 1
        self._last: Decision | None = None

    def record(
        self, now: float, decision: Decision, had_commands: bool
    ) -> bool:
        """@brief 제어결정이면 기록한다 (SWR-010).

        제어결정: 첫 평가, 운전자 명령을 받은 평가,
        결과가 직전 기록과 다른 평가.

        @param now 평가 시각
        @param decision 평가 결과
        @param had_commands 운전자 명령(버린 명령 포함)을 받았는지
        @return 기록했으면 True
        """
        changed = self._last is None or decision != self._last
        if not (changed or had_commands):
            return False
        self._records.append(EventRecord(self._next_id, now, decision))
        self._next_id += 1
        self._last = decision
        return True

    def events(self) -> tuple[EventRecord, ...]:
        """@brief 보존 중인 기록을 오래된 순으로 돌려준다."""
        return tuple(self._records)
