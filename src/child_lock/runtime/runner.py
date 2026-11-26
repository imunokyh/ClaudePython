"""@brief 50 ms 주기 실행기와 입력 우편함 (ASIL B, SWE3-DD 5.2).

모든 공개 메서드를 락 하나로 직렬화한다(SWE2-ARC 2.4). 원시 입력은 submit
시점에 깊은 불변 구조로 바꿔, 이후 호출자가 원본을 바꿔도 영향이 없다.
"""

from __future__ import annotations

import threading
from collections.abc import Iterable
from typing import Protocol

from child_lock.controller import Controller
from child_lock.qm.event_log import EventLog
from child_lock.runtime.clock import Clock, MonotonicClock
from child_lock.types import (
    PERIOD_S,
    Decision,
    EventRecord,
    FrozenMap,
    FrozenValue,
    RawInput,
    Unsupported,
    freeze_raw,
)


class Evaluator(Protocol):
    """@brief runner가 호출하는 평가기 (Controller)."""

    @property
    def last_decision(self) -> Decision:
        """@brief 직전 결과."""
        ...

    def evaluate(self, now: float, raw: RawInput) -> Decision:
        """@brief 평가 1회."""
        ...


def _is_confirmed(value: FrozenValue | None) -> bool:
    """@brief 원시 스냅샷의 crash_status가 "CONFIRMED"인지 본다 (SWR-022)."""
    return type(value) is FrozenMap and value.get("crash_status") == "CONFIRMED"


class Runner:
    """@brief 주기 평가 실행기."""

    def __init__(
        self,
        clock: Clock,
        controller: Evaluator,
        event_log: EventLog | None = None,
        period_s: float = PERIOD_S,
    ) -> None:
        """@brief 실행기를 만든다 (주기 스레드는 start()로 시작).

        @param clock 시각 공급원
        @param controller 평가기
        @param event_log 이벤트 조회용 기록 (controller와 같은 객체)
        @param period_s 평가주기 (초)
        """
        self._clock = clock
        self._controller = controller
        self._log = event_log
        self._period = period_s
        self._lock = threading.Lock()
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self._snapshot: FrozenValue | None = None
        self._has_snapshot = False
        self._commands: list[FrozenValue] = []
        self._dropped_in_cycle = 0
        self.dropped_snapshots = 0
        self.overruns = 0
        self.evaluation_errors = 0

    @classmethod
    def create_default(cls) -> Runner:
        """@brief 실시간 시계·controller·이벤트 기록으로 구성한 실행기."""
        log = EventLog()
        return cls(MonotonicClock(), Controller(log), log)

    def submit(
        self, snapshot: object, commands: Iterable[object], has_snapshot: bool
    ) -> None:
        """@brief 입력을 우편함에 넣는다 (SWR-022 우편함 규칙).

        @param snapshot 원시 스냅샷 (has_snapshot이 거짓이면 무시)
        @param commands 원시 명령 목록 (받은 순서대로 이어 붙임)
        @param has_snapshot 스냅샷을 보냈는지 (명령만 보낸 경우 False)
        """
        frozen_commands = [freeze_raw(c) for c in commands]
        frozen = freeze_raw(snapshot) if has_snapshot else None
        with self._lock:
            if has_snapshot:
                # JSON null 스냅샷은 "스냅샷 없음"과 구분해 형식 오류로 넘긴다.
                self._put_snapshot(
                    Unsupported("null") if frozen is None else frozen
                )
            self._commands.extend(frozen_commands)

    def _put_snapshot(self, frozen: FrozenValue) -> None:
        """@brief 한 주기 다중 스냅샷 규칙: CONFIRMED 우선, 그다음 최신.

        락 안에서 호출한다. 남기지 않은 스냅샷 수를 센다.
        """
        if not self._has_snapshot:
            self._snapshot, self._has_snapshot = frozen, True
            return
        self._dropped_in_cycle += 1
        self.dropped_snapshots += 1
        if _is_confirmed(frozen) or not _is_confirmed(self._snapshot):
            self._snapshot = frozen

    def tick(self) -> Decision:
        """@brief 우편함을 비워 평가를 한 번 수행한다.

        평가에서 예외가 나면 출력을 유지하고 오류 횟수를 센다(DD-02).

        @return 평가 결과 (예외 시 직전 결과)
        """
        with self._lock:
            raw = RawInput(
                snapshot=self._snapshot if self._has_snapshot else None,
                commands=tuple(self._commands),
                dropped_snapshots=self._dropped_in_cycle,
            )
            self._snapshot, self._has_snapshot = None, False
            self._commands, self._dropped_in_cycle = [], 0
            try:
                return self._controller.evaluate(self._clock.now(), raw)
            except Exception:
                self.evaluation_errors += 1
                return self._controller.last_decision

    def now(self) -> float:
        """@brief 시각 공급원의 현재 시각 (시뮬레이터 시각 동기화용)."""
        return self._clock.now()

    def status(self) -> Decision:
        """@brief 마지막 평가 결과."""
        with self._lock:
            return self._controller.last_decision

    def events(self) -> tuple[EventRecord, ...]:
        """@brief 보존 중인 제어결정 기록."""
        with self._lock:
            return self._log.events() if self._log is not None else ()

    def start(self) -> None:
        """@brief 주기 스레드를 시작한다 (이미 실행 중이면 무시)."""
        if self._thread is not None:
            return
        self._stop.clear()
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        """@brief 주기 스레드를 멈추고 끝날 때까지 기다린다."""
        self._stop.set()
        if self._thread is not None:
            self._thread.join()
            self._thread = None

    def _loop(self) -> None:
        """@brief 주기 루프. 밀린 주기는 따라잡지 않는다(DD-14)."""
        deadline = self._clock.now()
        while not self._stop.is_set():
            deadline += self._period
            wait = deadline - self._clock.now()
            if wait > 0 and self._stop.wait(wait):
                break
            self.tick()
            now = self._clock.now()
            if now > deadline + self._period:
                # 주기 초과: 다음 주기 하나를 바로 실행하고 기준을 다시 맞춘다.
                self.overruns += 1
                deadline = now
