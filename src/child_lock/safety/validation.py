"""@brief 원시 입력 검사 (ASIL B, SWE3-DD 2.1).

신뢰할 수 없는 원시 스냅샷과 운전자 명령을 신호별로 검사해 타입이 정해진
값으로 바꾼다. 오류 신호는 등급(ASIL B / QM)별 집합에 모은다(SWR-013).
"""

from __future__ import annotations

import enum
import math
from typing import Final

from child_lock.types import (
    EPS,
    FUTURE_TOLERANCE_S,
    SPEED_MAX_KPH,
    Action,
    CrashStatus,
    DriverCommand,
    FrozenMap,
    FrozenValue,
    Gear,
    Missing,
    Side,
    SnapshotCheck,
    SnapshotValues,
    Source,
)


class _Invalid(enum.Enum):
    """@brief 신호 검사 실패 표시."""

    INVALID = "INVALID"


## 신호 검사 실패 값
INVALID: Final = _Invalid.INVALID

## (신호 이름, 검사 종류, ASIL B 여부) — SWE1-SRS 1.2절
SIGNALS: Final = (
    ("source_timestamp_s", "timestamp", True),
    ("vehicle_speed_kph", "speed", True),
    ("gear", "gear", False),
    ("crash_status", "crash", True),
    ("rear_left_approach_risk", "bool", True),
    ("rear_right_approach_risk", "bool", True),
    ("fire_detected", "bool", False),
    ("overtemperature_detected", "bool", False),
    ("adult_present", "bool", False),
    ("isofix_left", "bool", False),
    ("isofix_right", "bool", False),
    ("ignition_on", "bool", True),
    ("sensor_fault", "bool", True),
)

## ASIL B 신호 이름 집합
ASIL_B_SIGNALS: Final = frozenset(
    {
        "source_timestamp_s",
        "vehicle_speed_kph",
        "crash_status",
        "rear_left_approach_risk",
        "rear_right_approach_risk",
        "ignition_on",
        "sensor_fault",
    }
)

## QM 신호 이름 집합
QM_SIGNALS: Final = frozenset(
    {
        "gear",
        "fire_detected",
        "overtemperature_detected",
        "adult_present",
        "isofix_left",
        "isofix_right",
    }
)

type Checked = float | bool | Gear | CrashStatus | _Invalid
type RawValue = FrozenValue | Missing


def _as_number(raw: RawValue) -> float | None:
    """@brief 정수·실수(bool 제외)를 유한한 float로 바꾼다 (C-3).

    @param raw 원시 값
    @return float, 변환할 수 없으면 None
    """
    if type(raw) is not int and type(raw) is not float:
        return None
    try:
        value = float(raw)
    except OverflowError:
        return None
    return value if math.isfinite(value) else None


def _as_speed(raw: RawValue) -> float | _Invalid:
    """@brief 차속 검사: 숫자, 0.0~300.0 km/h (경계 포함)."""
    value = _as_number(raw)
    if value is None or not 0.0 <= value <= SPEED_MAX_KPH:
        return INVALID
    return value


def _as_bool(raw: RawValue) -> bool | _Invalid:
    """@brief 불리언 검사: 정확히 bool만 허용 (A-12)."""
    return raw if type(raw) is bool else INVALID


def _as_enum[E: enum.Enum](raw: RawValue, enum_type: type[E]) -> E | _Invalid:
    """@brief 열거형 검사: 등록된 값의 문자열만 허용.

    @param raw 원시 값
    @param enum_type 열거형 타입
    @return 열거형 멤버 또는 INVALID
    """
    if type(raw) is not str:
        return INVALID
    for member in enum_type:
        if member.value == raw:
            return member
    return INVALID


def _as_timestamp(
    raw: RawValue, now: float, ref_ts: float | None
) -> float | _Invalid:
    """@brief 타임스탬프 검사: 숫자, 0 이상, 미래 0.050초 이내, 역행 없음.

    @param raw 원시 값
    @param now 평가 시각
    @param ref_ts 기준 스냅샷 시각 (없으면 None)
    @return 시각 또는 INVALID
    """
    value = _crash_timestamp(raw, now)
    if value is None:
        return INVALID
    # 기준 스냅샷보다 이전 시각은 역행이다(같은 시각은 허용).
    if ref_ts is not None and value < ref_ts - EPS:
        return INVALID
    return value


def _crash_timestamp(raw: RawValue, now: float) -> float | None:
    """@brief 충돌 판정용 시각 검사: 역행 검사를 하지 않는다 (SWR-007).

    @param raw 원시 값
    @param now 평가 시각
    @return 시각, 유효하지 않으면 None
    """
    value = _as_number(raw)
    if value is None or value < 0.0:
        return None
    if value > now + FUTURE_TOLERANCE_S + EPS:
        return None
    return value


def check_signal(
    raw: RawValue, kind: str, now: float, ref_ts: float | None
) -> Checked:
    """@brief 신호 하나를 종류에 맞게 검사한다.

    @param raw 원시 값 (키가 없으면 Missing)
    @param kind 검사 종류 (SIGNALS 표)
    @param now 평가 시각
    @param ref_ts 기준 스냅샷 시각
    @return 검사한 값 또는 INVALID
    """
    if kind == "bool":
        return _as_bool(raw)
    if kind == "speed":
        return _as_speed(raw)
    if kind == "timestamp":
        return _as_timestamp(raw, now, ref_ts)
    if kind == "crash":
        return _as_enum(raw, CrashStatus)
    return _as_enum(raw, Gear)


def _opt_bool(results: dict[str, Checked], name: str) -> bool | None:
    """@brief 검사 결과에서 불리언 값을 꺼낸다 (오류는 None)."""
    value = results[name]
    return value if type(value) is bool else None


def _build_values(results: dict[str, Checked]) -> SnapshotValues | None:
    """@brief 검사 결과로 SnapshotValues를 만든다. 타임스탬프 오류면 None."""
    ts = results["source_timestamp_s"]
    if type(ts) is not float:
        return None
    speed = results["vehicle_speed_kph"]
    gear = results["gear"]
    crash = results["crash_status"]
    return SnapshotValues(
        source_timestamp_s=ts,
        vehicle_speed_kph=speed if type(speed) is float else None,
        gear=gear if type(gear) is Gear else None,
        crash_status=crash if type(crash) is CrashStatus else None,
        rear_left_approach_risk=_opt_bool(results, "rear_left_approach_risk"),
        rear_right_approach_risk=_opt_bool(results, "rear_right_approach_risk"),
        fire_detected=_opt_bool(results, "fire_detected"),
        overtemperature_detected=_opt_bool(results, "overtemperature_detected"),
        adult_present=_opt_bool(results, "adult_present"),
        isofix_left=_opt_bool(results, "isofix_left"),
        isofix_right=_opt_bool(results, "isofix_right"),
        ignition_on=_opt_bool(results, "ignition_on"),
        sensor_fault=_opt_bool(results, "sensor_fault"),
    )


def check_snapshot(
    raw: FrozenValue | None, now: float, ref_ts: float | None
) -> SnapshotCheck:
    """@brief 원시 스냅샷을 신호별로 검사한다 (SWR-013).

    @param raw 불변화한 원시 스냅샷 (None이면 그 주기에 스냅샷 없음)
    @param now 평가 시각
    @param ref_ts 기준 스냅샷 시각 (역행 검사용)
    @return 검사 결과
    """
    if raw is None:
        return SnapshotCheck(False, None, frozenset(), frozenset(), None, None)
    if type(raw) is not FrozenMap:
        return SnapshotCheck(True, None, ASIL_B_SIGNALS, QM_SIGNALS, None, None)
    results = {
        name: check_signal(raw.get(name), kind, now, ref_ts)
        for name, kind, _ in SIGNALS
    }
    errors = {name for name, value in results.items() if value is INVALID}
    crash = results["crash_status"]
    return SnapshotCheck(
        received=True,
        values=_build_values(results),
        asil_b_errors=frozenset(errors & ASIL_B_SIGNALS),
        qm_errors=frozenset(errors & QM_SIGNALS),
        crash_status=crash if type(crash) is CrashStatus else None,
        crash_timestamp_s=_crash_timestamp(raw.get("source_timestamp_s"), now),
    )


def _parse_command(raw: FrozenValue) -> tuple[DriverCommand, ...] | None:
    """@brief 명령 하나를 검사한다. `all`은 좌·우 두 명령으로 나눈다.

    @param raw 불변화한 원시 명령
    @return 명령 튜플, 오류면 None
    """
    if type(raw) is not FrozenMap:
        return None
    action = _as_enum(raw.get("action"), Action)
    source = _as_enum(raw.get("source"), Source)
    if action is INVALID or source is INVALID:
        return None
    side_raw = raw.get("side")
    if type(side_raw) is str and side_raw == "all":
        sides: tuple[Side, ...] = (Side.LEFT, Side.RIGHT)
    else:
        side = _as_enum(side_raw, Side)
        if side is INVALID:
            return None
        sides = (side,)
    return tuple(DriverCommand(s, action, source) for s in sides)


def check_commands(
    raw_commands: tuple[FrozenValue, ...],
) -> tuple[tuple[DriverCommand, ...], int]:
    """@brief 운전자 명령 목록을 검사한다 (SWR-002, SWR-013 ⑤).

    @param raw_commands 받은 순서의 원시 명령
    @return (유효 명령 튜플, 버린 명령 수)
    """
    commands: list[DriverCommand] = []
    dropped = 0
    for raw in raw_commands:
        parsed = _parse_command(raw)
        if parsed is None:
            dropped += 1
        else:
            commands.extend(parsed)
    return tuple(commands), dropped
