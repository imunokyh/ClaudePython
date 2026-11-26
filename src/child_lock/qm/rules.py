"""@brief 순위 6~10 QM 규칙의 쪽별 제안 (QM, SWE3-DD 3.1).

해당하는 규칙마다 제안을 내고 순위 판정은 하지 않는다. 판정과 검사는
ASIL B인 safety.arbiter가 한다(SWE2-ARC AR-08).
"""

from __future__ import annotations

from child_lock.types import (
    AUTO_LOCK_KPH,
    Action,
    DriverCommand,
    LockOutput,
    ReasonCode,
    Side,
    SideProposal,
    SnapshotValues,
)

type Pair = tuple[tuple[SideProposal, ...], tuple[SideProposal, ...]]


def _ignition_off(values: SnapshotValues) -> SideProposal | None:
    """@brief 시동 OFF 해제 (순위 6, SWR-020)."""
    if values.ignition_on is False:
        return SideProposal(6, LockOutput.RELEASE, ReasonCode.IGNITION_OFF)
    return None


def _forced_release(values: SnapshotValues) -> SideProposal | None:
    """@brief 화재 > 과온 > 성인 탑승 강제 해제 (순위 7, SWR-017)."""
    if values.fire_detected is True:
        reason = ReasonCode.FIRE
    elif values.overtemperature_detected is True:
        reason = ReasonCode.OVERTEMPERATURE
    elif values.adult_present is True:
        reason = ReasonCode.ADULT_PRESENT
    else:
        return None
    return SideProposal(7, LockOutput.RELEASE, reason)


def _isofix(values: SnapshotValues, side: Side) -> SideProposal | None:
    """@brief ISOFIX 연결 쪽 강제 잠금 (순위 8, SWR-018)."""
    connected = values.isofix_left if side is Side.LEFT else values.isofix_right
    if connected is True:
        return SideProposal(8, LockOutput.LOCK, ReasonCode.ISOFIX)
    return None


def _below_auto_lock(values: SnapshotValues) -> bool:
    """@brief 차속이 유효하고 3.0 km/h 미만인지 본다."""
    speed = values.vehicle_speed_kph
    return speed is not None and speed < AUTO_LOCK_KPH


def _auto_lock(values: SnapshotValues) -> SideProposal | None:
    """@brief 주행 시작 자동 잠금 (순위 9, SWR-003)."""
    speed = values.vehicle_speed_kph
    if speed is not None and speed >= AUTO_LOCK_KPH:
        return SideProposal(9, LockOutput.LOCK, ReasonCode.AUTO_LOCK)
    return None


def _driver(
    values: SnapshotValues, commands: tuple[DriverCommand, ...], side: Side
) -> SideProposal | None:
    """@brief 그 쪽 마지막 운전자 명령 (순위 10, SWR-001, 002, 004).

    해제(`unlock`)는 차속이 3.0 km/h 미만일 때만 제안한다.
    """
    mine = [c for c in commands if c.side is side]
    if not mine:
        return None
    if mine[-1].action is Action.LOCK:
        return SideProposal(10, LockOutput.LOCK, ReasonCode.DRIVER_COMMAND)
    if _below_auto_lock(values):
        return SideProposal(10, LockOutput.RELEASE, ReasonCode.DRIVER_COMMAND)
    return None


def _side(
    values: SnapshotValues, commands: tuple[DriverCommand, ...], side: Side
) -> tuple[SideProposal, ...]:
    """@brief 한 쪽에 해당하는 제안을 규칙 순서대로 모은다."""
    found = (
        _ignition_off(values),
        _forced_release(values),
        _isofix(values, side),
        _auto_lock(values),
        _driver(values, commands, side),
    )
    return tuple(p for p in found if p is not None)


def proposals(
    values: SnapshotValues | None, commands: tuple[DriverCommand, ...]
) -> Pair:
    """@brief 좌·우 QM 제안을 계산한다.

    @param values 쓰는 신호 값 (없으면 제안 없음)
    @param commands 이번 평가의 운전자 명령
    @return (좌 제안, 우 제안)
    """
    if values is None:
        return (), ()
    return _side(values, commands, Side.LEFT), _side(
        values, commands, Side.RIGHT
    )
