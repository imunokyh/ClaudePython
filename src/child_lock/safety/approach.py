"""@brief 후측방 접근위험 잠금과 운전자 override (ASIL B, SWE3-DD 2.4).

쪽마다 독립으로 판정한다(SWR-009). override 판단은 상위에 ASIL B
요구사항(OEM-SR-002)이 있으므로 ASIL B로 개발한다(DEC-07).
"""

from __future__ import annotations

from dataclasses import dataclass

from child_lock.types import (
    AUTO_LOCK_KPH,
    EPS,
    OVERRIDE_WINDOW_S,
    Action,
    CrashView,
    DriverCommand,
    LockOutput,
    ReasonCode,
    Side,
    SideProposal,
    SnapshotValues,
    UsedSnapshot,
)


@dataclass(frozen=True, slots=True)
class SideMemory:
    """@brief 한 쪽의 첫 억제 기록과 override 여부."""

    first_suppress_ts: float | None
    first_suppress_eval: int
    override: bool


@dataclass(frozen=True, slots=True)
class ApproachMemory:
    """@brief 좌·우 접근위험 상태."""

    left: SideMemory
    right: SideMemory


def clear_side() -> SideMemory:
    """@brief 첫 억제도 override도 없는 한 쪽 상태."""
    return SideMemory(
        first_suppress_ts=None, first_suppress_eval=-1, override=False
    )


def initial_memory() -> ApproachMemory:
    """@brief 초기 접근위험 상태 (좌·우 모두 비어 있음)."""
    return ApproachMemory(left=clear_side(), right=clear_side())


def _risk(values: SnapshotValues, side: Side) -> bool | None:
    """@brief 그 쪽 접근위험 신호 값."""
    if side is Side.LEFT:
        return values.rear_left_approach_risk
    return values.rear_right_approach_risk


def _moving(values: SnapshotValues) -> bool:
    """@brief 차속이 3.0 km/h 이상인지 본다.

    차속을 모르면(오류) 정지로 보지 않는다(보수적으로 주행 중으로 본다).
    """
    speed = values.vehicle_speed_kph
    return speed is None or speed >= AUTO_LOCK_KPH


def _terminated(values: SnapshotValues, side: Side, crash: CrashView) -> bool:
    """@brief override·첫 억제를 지우는 종료 조건 (SWR-006).

    위험 해소, 3.0 km/h 이상, 시동 OFF, 충돌 래치 중 하나면 종료한다.
    """
    return (
        _risk(values, side) is not True
        or _moving(values)
        or values.ignition_on is False
        or crash.latched
    )


def _has_unlock(commands: tuple[DriverCommand, ...], side: Side) -> bool:
    """@brief 이번 평가에 그 쪽 해제 명령이 있는지 본다 (중복은 1회로 셈)."""
    return any(c.side is side and c.action is Action.UNLOCK for c in commands)


def _count_unlock(memory: SideMemory, t: float, eval_index: int) -> SideMemory:
    """@brief 해제 명령 하나를 첫 억제 또는 재입력으로 센다.

    @param memory 그 쪽 상태
    @param t 명령 시각 (쓰는 스냅샷의 source_timestamp_s)
    @param eval_index 이번 정상 평가 번호
    @return 새 상태
    """
    if memory.override:
        return memory
    first = memory.first_suppress_ts
    # 재입력은 첫 억제 이후의 평가이고 10.0초 이하여야 한다(DD-01).
    later = eval_index > memory.first_suppress_eval
    if first is not None and later and t - first <= OVERRIDE_WINDOW_S + EPS:
        return SideMemory(None, -1, True)
    return SideMemory(t, eval_index, False)


def _evaluate_side(
    memory: SideMemory,
    side: Side,
    values: SnapshotValues,
    commands: tuple[DriverCommand, ...],
    context: tuple[CrashView, bool, int],
) -> tuple[SideMemory, SideProposal | None]:
    """@brief 한 쪽의 접근위험 판정.

    @param memory 그 쪽 상태
    @param side 좌 또는 우
    @param values 쓰는 신호 값
    @param commands 이번 평가의 명령
    @param context (충돌 판정, 순위 1~3 해당 여부, 정상 평가 번호)
    @return (새 상태, 순위 4 제안 또는 None)
    """
    crash, frozen, eval_index = context
    terminated = _terminated(values, side, crash)
    if terminated:
        memory = clear_side()
    if _risk(values, side) is not True:
        return memory, None
    # 순위 1~3이 적용된 평가의 명령과, 종료 조건(3.0 km/h 이상 등)에서
    # 받은 명령은 첫 억제·재입력으로 세지 않는다(SWR-006, A-24).
    if not frozen and not terminated and _has_unlock(commands, side):
        memory = _count_unlock(memory, values.source_timestamp_s, eval_index)
    if memory.override:
        return memory, SideProposal(
            4, LockOutput.RELEASE, ReasonCode.DRIVER_OVERRIDE
        )
    return memory, SideProposal(4, LockOutput.LOCK, ReasonCode.APPROACH_RISK)


def evaluate(
    memory: ApproachMemory,
    used: UsedSnapshot,
    commands: tuple[DriverCommand, ...],
    crash: CrashView,
    frozen: bool,
    eval_index: int,
) -> tuple[ApproachMemory, SideProposal | None, SideProposal | None]:
    """@brief 좌·우 접근위험을 판정한다 (SWR-005, 006, 009).

    @param memory 직전 접근위험 상태
    @param used 쓰는 스냅샷
    @param commands 이번 평가의 명령
    @param crash 충돌 판정
    @param frozen 순위 1~3 해당 여부
    @param eval_index 이번 정상 평가 번호
    @return (새 상태, 좌 제안, 우 제안)
    """
    values = used.values
    if values is None:
        return memory, None, None
    context = (crash, frozen, eval_index)
    left, left_prop = _evaluate_side(
        memory.left, Side.LEFT, values, commands, context
    )
    right, right_prop = _evaluate_side(
        memory.right, Side.RIGHT, values, commands, context
    )
    return ApproachMemory(left, right), left_prop, right_prop
