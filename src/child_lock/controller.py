"""@brief 평가 1회 조정 (ASIL B, SWE3-DD 4장).

SWE2-ARC 3장의 고정 순서로 검사 → 충돌 → 기준 스냅샷 → 접근위험 → QM 제안
→ 순위 판정 → 상태 교체 → 기록을 수행한다. QM 호출과 기록은 예외를 격리해
ASIL B 판정이 계속되게 한다(SWE2-ARC 2.4).
"""

from __future__ import annotations

import math
from dataclasses import dataclass, replace

from child_lock.qm import rules
from child_lock.qm.event_log import EventLog
from child_lock.safety import approach, crash, monitor
from child_lock.safety.arbiter import arbitrate
from child_lock.safety.validation import check_commands, check_snapshot
from child_lock.types import (
    CrashView,
    Decision,
    DriverCommand,
    InputValidity,
    RawInput,
    ReasonCode,
    SnapshotCheck,
    SnapshotValues,
    UsedSnapshot,
    initial_decision,
)

type QmPair = tuple[tuple[object, ...], tuple[object, ...]]


@dataclass(frozen=True, slots=True)
class ControllerState:
    """@brief 평가 사이에 남는 내부 상태 (SWE2-ARC 4장)."""

    decision: Decision
    last_time: float | None
    eval_index: int
    reference: SnapshotCheck | None
    crash: crash.CrashMemory
    approach: approach.ApproachMemory


def _initial_state() -> ControllerState:
    """@brief 첫 평가 전 상태: 출력 RELEASE, 래치·기준 스냅샷 없음."""
    return ControllerState(
        decision=initial_decision(),
        last_time=None,
        eval_index=0,
        reference=None,
        crash=crash.initial_memory(),
        approach=approach.initial_memory(),
    )


def _call_rules(
    values: SnapshotValues | None, commands: tuple[DriverCommand, ...]
) -> QmPair:
    """@brief QM 규칙을 호출하고 결과를 (좌, 우) 튜플로 정규화한다.

    예외가 나거나 모양이 맞지 않으면 제안 없음으로 처리한다(DD-06).
    내용 검사는 arbiter가 한다.

    @param values 쓰는 신호 값
    @param commands 이번 평가의 명령
    @return (좌 제안, 우 제안)
    """
    try:
        left, right = rules.proposals(values, commands)
        return tuple(left), tuple(right)
    except Exception:
        return (), ()


def _frozen(used: UsedSnapshot, view: CrashView) -> bool:
    """@brief 순위 1~3이 해당하는 평가인지 본다 (접근위험 명령 계수 제외용)."""
    values = used.values
    fault = values is not None and values.sensor_fault is True
    return bool(view.latched or used.rank2_reason is not None or fault)


def _reference_ts(state: ControllerState) -> float | None:
    """@brief 기준 스냅샷 시각 (역행 검사용)."""
    ref = state.reference
    if ref is None or ref.values is None:
        return None
    return ref.values.source_timestamp_s


class Controller:
    """@brief 평가 1회를 조정하고 내부 상태를 비공개로 보관한다."""

    def __init__(self, event_log: EventLog | None = None) -> None:
        """@brief 초기 상태의 controller를 만든다.

        @param event_log 제어결정 기록 (없으면 기록하지 않음)
        """
        self._log = event_log
        self._state = _initial_state()

    @property
    def last_decision(self) -> Decision:
        """@brief 직전 평가 결과 (평가 전에는 초기 결과)."""
        return self._state.decision

    def evaluate(self, now: float, raw: RawInput) -> Decision:
        """@brief 평가를 한 번 수행한다 (SWR-022).

        @param now 평가 시각 (runtime.clock이 공급)
        @param raw 이번 주기의 원시 입력
        @return 평가 결과
        """
        state = self._state
        last = state.last_time
        if not math.isfinite(now) or (last is not None and now <= last):
            decision = self._time_error(state)
            self._state = replace(state, decision=decision)
        else:
            decision, self._state = self._normal(now, raw, state)
        self._record(now, decision, bool(raw.commands))
        return decision

    def _time_error(self, state: ControllerState) -> Decision:
        """@brief 평가 시각 오류: 상태를 갱신하지 않고 출력을 유지한다.

        기존 충돌 래치만 순위 1로 반영한다(SWR-022, A-25).
        """
        used = UsedSnapshot(
            None, frozenset(), InputValidity.INVALID, ReasonCode.INPUT_INVALID
        )
        view = CrashView(latched=state.crash.latched, pending_filter=False)
        return arbitrate(
            used, view, (None, None), ((), ()), state.decision, False, True
        )

    def _normal(
        self, now: float, raw: RawInput, state: ControllerState
    ) -> tuple[Decision, ControllerState]:
        """@brief 정상 평가 (SWE2-ARC 3장 순서).

        @param now 평가 시각
        @param raw 원시 입력
        @param state 직전 상태
        @return (결과, 새 상태)
        """
        check = check_snapshot(raw.snapshot, now, _reference_ts(state))
        commands, _ = check_commands(raw.commands)
        crash_memory = crash.update(state.crash, check, now)
        view = crash.view(crash_memory, now)
        used, reference = monitor.select(check, now, state.reference)
        index = state.eval_index + 1
        approach_memory, left, right = approach.evaluate(
            state.approach, used, commands, view, _frozen(used, view), index
        )
        override = (
            approach_memory.left.override or approach_memory.right.override
        )
        decision = arbitrate(
            used,
            view,
            (left, right),
            _call_rules(used.values, commands),
            state.decision,
            override,
            False,
        )
        new_state = ControllerState(
            decision, now, index, reference, crash_memory, approach_memory
        )
        return decision, new_state

    def _record(
        self, now: float, decision: Decision, had_commands: bool
    ) -> None:
        """@brief 제어결정을 기록한다. 기록 실패는 판정에 영향을 주지 않는다."""
        if self._log is None:
            return
        try:
            self._log.record(now, decision, had_commands)
        except Exception:
            # 기록(QM) 실패는 무시한다. 판정 결과는 이미 확정되었다.
            return
