"""@brief 차일드락 제어 SW의 공용 데이터 타입 (ASIL B).

SWE3-DD 1장. 모든 dataclass는 불변(frozen, slots)이고 필드 타입도 불변이다
(SWE2-ARC DR-7). 이 모듈은 패키지 내부의 다른 모듈을 import하지 않는다(DR-3).
"""

from __future__ import annotations

import enum
from dataclasses import dataclass
from typing import Final

## freeze_raw가 허용하는 최대 중첩 깊이 (SWE2-SAP 1.2)
MAX_FREEZE_DEPTH: Final = 32

# --- 공통 상수 (SWE3-DD 0장 C-1, C-2) ---
## 시간 비교의 부동소수점 허용 오차 (초)
EPS: Final = 1e-9
## 평가주기 (초, SWR-022)
PERIOD_S: Final = 0.05
## 입력 지연 판정 한계 (초, SWR-013)
STALE_LIMIT_S: Final = 0.200
## 미래 타임스탬프 허용 오차 (초, SWR-013 A-22)
FUTURE_TOLERANCE_S: Final = 0.050
## 충돌 CONFIRMED를 받아들이는 최대 나이 (초, SWR-007 A-14)
CRASH_MAX_AGE_S: Final = 1.0
## PENDING 필터 최대 지속 (초, SWR-008 A-23)
PENDING_LIMIT_S: Final = 2.0
## override 재입력 허용 시간 (초, SWR-006)
OVERRIDE_WINDOW_S: Final = 10.0
## 자동 잠금·일반 해제 기준 차속 (km/h, SWR-003, SWR-004)
AUTO_LOCK_KPH: Final = 3.0
## 차속 범위 상한 (km/h, OEM-IF-001)
SPEED_MAX_KPH: Final = 300.0
## 이벤트 보관 건수 (SWR-012)
EVENT_CAPACITY: Final = 100


class LockOutput(enum.StrEnum):
    """@brief 차일드락 논리 출력 (OEM-IF-005)."""

    LOCK = "LOCK"
    RELEASE = "RELEASE"


class State(enum.StrEnum):
    """@brief 표시용 상태 (SWE1-SRS 1.3절)."""

    OFF = "OFF"
    NORMAL = "NORMAL"
    DEGRADED = "DEGRADED"
    FAULT = "FAULT"
    OVERRIDE = "OVERRIDE"


class ReasonCode(enum.StrEnum):
    """@brief 출력을 정한 규칙의 이유코드 (SWE1-SRS 1.4절)."""

    CRASH_CONFIRMED = "CRASH_CONFIRMED"
    INPUT_INVALID = "INPUT_INVALID"
    INPUT_STALE = "INPUT_STALE"
    SENSOR_FAULT = "SENSOR_FAULT"
    APPROACH_RISK = "APPROACH_RISK"
    DRIVER_OVERRIDE = "DRIVER_OVERRIDE"
    IGNITION_OFF = "IGNITION_OFF"
    FIRE = "FIRE"
    OVERTEMPERATURE = "OVERTEMPERATURE"
    ADULT_PRESENT = "ADULT_PRESENT"
    ISOFIX = "ISOFIX"
    AUTO_LOCK = "AUTO_LOCK"
    DRIVER_COMMAND = "DRIVER_COMMAND"
    CRASH_PENDING = "CRASH_PENDING"
    NO_CHANGE = "NO_CHANGE"


class InputValidity(enum.StrEnum):
    """@brief 입력 유효성 (OEM-IF-006)."""

    VALID = "VALID"
    INVALID = "INVALID"
    STALE = "STALE"


class WarningCode(enum.StrEnum):
    """@brief 경고코드 (OEM-SR-004)."""

    NONE = "NONE"
    W_SENSOR_FAULT = "W_SENSOR_FAULT"


class Side(enum.StrEnum):
    """@brief 후석 좌·우. 값은 운전자 명령의 `side` 문자열과 같다."""

    LEFT = "left"
    RIGHT = "right"


class Action(enum.StrEnum):
    """@brief 운전자 명령 동작 (OEM-IF-004)."""

    LOCK = "lock"
    UNLOCK = "unlock"


class Source(enum.StrEnum):
    """@brief 운전자 명령 경로 (OEM-IF-004)."""

    PHYSICAL_BUTTON = "physical_button"
    AVN = "avn"
    VOICE = "voice"
    MOBILE_APP = "mobile_app"


class CrashStatus(enum.StrEnum):
    """@brief 충돌 상태 (OEM-IF-002)."""

    NONE = "NONE"
    PENDING = "PENDING"
    CONFIRMED = "CONFIRMED"


class Gear(enum.StrEnum):
    """@brief 기어 위치 (OEM-IF-001)."""

    P = "P"
    N = "N"
    D = "D"
    R = "R"


class Missing(enum.Enum):
    """@brief FrozenMap에 키가 없음을 나타내는 표시."""

    MISSING = "MISSING"


# --- 원시 입력 불변화 (SWE3-DD 1.2) ---


@dataclass(frozen=True, slots=True)
class Unsupported:
    """@brief JSON 값으로 바꿀 수 없는 원시 값의 표시."""

    type_name: str


@dataclass(frozen=True, slots=True)
class FrozenMap:
    """@brief 원시 JSON 객체의 불변 사본 (키 정렬)."""

    items: tuple[tuple[str, FrozenValue], ...]

    def get(self, key: str) -> FrozenValue | Missing:
        """@brief 키의 값을 찾는다.

        @param key 키 문자열
        @return 값, 키가 없으면 Missing.MISSING
        """
        for name, value in self.items:
            if name == key:
                return value
        return Missing.MISSING


type FrozenValue = (
    str
    | int
    | float
    | bool
    | None
    | FrozenMap
    | Unsupported
    | tuple[FrozenValue, ...]
)


def freeze_raw(value: object, depth: int = 0) -> FrozenValue:
    """@brief 원시 JSON 값을 깊은 불변 구조로 바꾼다.

    dict(키가 모두 문자열)는 FrozenMap, list·tuple은 tuple, 스칼라는 그대로
    두고, 그 밖의 값과 깊이 제한을 넘는 중첩은 Unsupported로 표시한다.
    값의 내용 검사는 safety.validation이 한다.

    @param value 원시 값
    @param depth 현재 중첩 깊이 (재귀용)
    @return 불변 값
    """
    if depth >= MAX_FREEZE_DEPTH:
        return Unsupported("depth")
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, dict):
        if not all(isinstance(k, str) for k in value):
            return Unsupported("dict")
        pairs = sorted(value.items())
        return FrozenMap(tuple((k, freeze_raw(v, depth + 1)) for k, v in pairs))
    if isinstance(value, (list, tuple)):
        return tuple(freeze_raw(v, depth + 1) for v in value)
    return Unsupported(type(value).__name__)


@dataclass(frozen=True, slots=True)
class RawInput:
    """@brief 한 평가의 원시 입력 (불변화됨, 내용 검증 전)."""

    snapshot: FrozenValue | None
    commands: tuple[FrozenValue, ...]
    dropped_snapshots: int = 0


# --- 전달 타입 (SWE3-DD 1.3) ---


@dataclass(frozen=True, slots=True)
class SnapshotValues:
    """@brief 검사를 마친 차량 신호 값. 오류 신호는 None이다."""

    source_timestamp_s: float
    vehicle_speed_kph: float | None
    gear: Gear | None
    crash_status: CrashStatus | None
    rear_left_approach_risk: bool | None
    rear_right_approach_risk: bool | None
    fire_detected: bool | None
    overtemperature_detected: bool | None
    adult_present: bool | None
    isofix_left: bool | None
    isofix_right: bool | None
    ignition_on: bool | None
    sensor_fault: bool | None


@dataclass(frozen=True, slots=True)
class SnapshotCheck:
    """@brief 스냅샷 검사 결과 (safety.validation)."""

    received: bool
    values: SnapshotValues | None
    asil_b_errors: frozenset[str]
    qm_errors: frozenset[str]
    crash_status: CrashStatus | None
    crash_timestamp_s: float | None


@dataclass(frozen=True, slots=True)
class DriverCommand:
    """@brief 검사를 마친 운전자 명령. `all`은 좌·우 두 명령으로 나뉜다."""

    side: Side
    action: Action
    source: Source


@dataclass(frozen=True, slots=True)
class UsedSnapshot:
    """@brief 이번 평가의 판정에 쓰는 신호와 입력 상태 (safety.monitor)."""

    values: SnapshotValues | None
    qm_errors: frozenset[str]
    input_validity: InputValidity
    rank2_reason: ReasonCode | None


@dataclass(frozen=True, slots=True)
class CrashView:
    """@brief 충돌 판정 결과 (safety.crash)."""

    latched: bool
    pending_filter: bool


@dataclass(frozen=True, slots=True)
class SideProposal:
    """@brief 한 쪽 출력에 대한 규칙의 제안. output이 None이면 유지."""

    rank: int
    output: LockOutput | None
    reason: ReasonCode


@dataclass(frozen=True, slots=True)
class Decision:
    """@brief 한 평가의 공개 결과 (SWR-014의 9개 필드)."""

    lock_left: LockOutput
    lock_right: LockOutput
    state: State
    priority_reason: str
    reason_code: ReasonCode
    input_validity: InputValidity
    reason_left: ReasonCode
    reason_right: ReasonCode
    warning_code: WarningCode

    def as_dict(self) -> dict[str, str]:
        """@brief 표시 인터페이스(JSON)용 딕셔너리로 바꾼다."""
        return {
            "lock_left": self.lock_left.value,
            "lock_right": self.lock_right.value,
            "state": self.state.value,
            "priority_reason": self.priority_reason,
            "reason_code": self.reason_code.value,
            "input_validity": self.input_validity.value,
            "reason_left": self.reason_left.value,
            "reason_right": self.reason_right.value,
            "warning_code": self.warning_code.value,
        }


@dataclass(frozen=True, slots=True)
class EventRecord:
    """@brief 제어결정 기록 1건 (SWR-010, SWR-011)."""

    event_id: int
    timestamp_s: float
    decision: Decision

    def as_dict(self) -> dict[str, object]:
        """@brief SWR-011의 11개 키 딕셔너리로 바꾼다."""
        record: dict[str, object] = {
            "event_id": self.event_id,
            "timestamp_s": self.timestamp_s,
        }
        record.update(self.decision.as_dict())
        return record


def priority_reason_of(code: ReasonCode) -> str:
    """@brief 이유코드에 대응하는 priority_reason 이름 (SWE1-SRS 1.4절).

    @param code 이유코드
    @return snake_case 규칙 이름
    """
    if code is ReasonCode.FIRE:
        return "fire_detected"
    if code is ReasonCode.OVERTEMPERATURE:
        return "overtemperature_detected"
    return code.value.lower()


def initial_decision() -> Decision:
    """@brief 첫 평가 전의 직전 결과 (SWE1-SRS A-15).

    출력은 둘 다 초기 해제 상태이고, 아직 입력이 없으므로 STALE이다.

    @return 초기 Decision
    """
    return Decision(
        lock_left=LockOutput.RELEASE,
        lock_right=LockOutput.RELEASE,
        state=State.DEGRADED,
        priority_reason="input_stale",
        reason_code=ReasonCode.INPUT_STALE,
        input_validity=InputValidity.STALE,
        reason_left=ReasonCode.INPUT_STALE,
        reason_right=ReasonCode.INPUT_STALE,
        warning_code=WarningCode.NONE,
    )
