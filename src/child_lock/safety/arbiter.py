"""@brief 규칙 순위 판정 (ASIL B, SWE3-DD 2.5).

쪽마다 ASIL B 규칙(순위 1~4)을 먼저 판정하고, 정해지지 않은 쪽에만 QM 제안
(순위 6~10)을 반영한다(SWE1-SRS P-1, SWR-019). QM 제안은 타입·순위·이유·
출력 방향을 검사해 어긋나면 버린다(SWE2-ARC 2.4 간섭 배제).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Final, TypeGuard

from child_lock.types import (
    CrashView,
    Decision,
    InputValidity,
    LockOutput,
    ReasonCode,
    SideProposal,
    SnapshotValues,
    State,
    UsedSnapshot,
    WarningCode,
    priority_reason_of,
)

## QM 규칙 순위별 (순위, 허용 이유코드, 허용 출력) — SWE1-SRS 1.4절
_QM_RULES: Final = (
    (6, (ReasonCode.IGNITION_OFF,), (LockOutput.RELEASE,)),
    (
        7,
        (
            ReasonCode.FIRE,
            ReasonCode.OVERTEMPERATURE,
            ReasonCode.ADULT_PRESENT,
        ),
        (LockOutput.RELEASE,),
    ),
    (8, (ReasonCode.ISOFIX,), (LockOutput.LOCK,)),
    (9, (ReasonCode.AUTO_LOCK,), (LockOutput.LOCK,)),
    (
        10,
        (ReasonCode.DRIVER_COMMAND,),
        (LockOutput.LOCK, LockOutput.RELEASE),
    ),
)

## "해당 없음"의 비교 순위 (가장 낮음)
_NO_RULE_RANK: Final = 11

## 한 쪽 결과: (출력, 이유코드, 비교 순위)
type SideResult = tuple[LockOutput, ReasonCode, int]


@dataclass(frozen=True, slots=True)
class _Context:
    """@brief 두 쪽 판정에 공통인 입력."""

    used: UsedSnapshot
    crash: CrashView
    time_error: bool

    @property
    def values(self) -> SnapshotValues | None:
        """@brief 판정에 쓰는 신호 값. 시각 오류면 신뢰하지 않는다."""
        return None if self.time_error else self.used.values


def _valid_qm(proposal: object) -> TypeGuard[SideProposal]:
    """@brief QM 제안이 순위·이유·출력 방향 규칙에 맞는지 본다 (C-5).

    @param proposal QM 모듈이 돌려준 값 (신뢰하지 않음)
    @return 올바른 SideProposal이면 True
    """
    if type(proposal) is not SideProposal:
        return False
    rank, output, reason = proposal.rank, proposal.output, proposal.reason
    if type(rank) is not int or type(reason) is not ReasonCode:
        return False
    if type(output) is not LockOutput:
        return False
    for rule_rank, reasons, outputs in _QM_RULES:
        if rank == rule_rank:
            return reason in reasons and output in outputs
    return False


def _asil_b_side(
    ctx: _Context, approach: SideProposal | None, previous: LockOutput
) -> SideResult | None:
    """@brief 순위 1~4(ASIL B) 판정. 해당 없으면 None.

    @param ctx 공통 입력
    @param approach 이 쪽 접근위험 제안 (순위 4)
    @param previous 이 쪽 직전 출력
    @return 결과 또는 None
    """
    if ctx.crash.latched:
        return LockOutput.RELEASE, ReasonCode.CRASH_CONFIRMED, 1
    if ctx.time_error:
        return previous, ReasonCode.INPUT_INVALID, 2
    if ctx.used.rank2_reason is not None:
        return previous, ctx.used.rank2_reason, 2
    values = ctx.values
    if values is not None and values.sensor_fault is True:
        return previous, ReasonCode.SENSOR_FAULT, 3
    if approach is not None and approach.output is not None:
        return approach.output, approach.reason, 4
    return None


def _qm_side(
    ctx: _Context, proposals: tuple[object, ...], previous: LockOutput
) -> SideResult:
    """@brief 순위 5~11 판정과 PENDING 필터 (SWR-008, SWR-013, SWR-019).

    @param ctx 공통 입력
    @param proposals 이 쪽 QM 제안 (신뢰하지 않음)
    @param previous 이 쪽 직전 출력
    @return 결과
    """
    if ctx.used.qm_errors:
        return previous, ReasonCode.INPUT_INVALID, 5
    valid = [p for p in proposals if _valid_qm(p)]
    if not valid:
        return previous, ReasonCode.NO_CHANGE, _NO_RULE_RANK
    # 순위가 가장 높은(숫자가 작은) 제안. 같으면 목록에서 먼저 나온 것.
    best = min(valid, key=lambda p: p.rank)
    output = best.output if best.output is not None else previous
    locking = output is LockOutput.LOCK and previous is LockOutput.RELEASE
    if locking and ctx.crash.pending_filter:
        return previous, ReasonCode.CRASH_PENDING, best.rank
    return output, best.reason, best.rank


def _decide_side(
    ctx: _Context,
    approach: SideProposal | None,
    proposals: tuple[object, ...],
    previous: LockOutput,
) -> SideResult:
    """@brief 한 쪽의 출력과 이유를 정한다."""
    asil_b = _asil_b_side(ctx, approach, previous)
    if asil_b is not None:
        return asil_b
    return _qm_side(ctx, proposals, previous)


def _state_of(ctx: _Context, override_active: bool) -> State:
    """@brief 상태를 성립 조건 순서로 정한다 (SWE1-SRS 1.3절, DD-04).

    @param ctx 공통 입력
    @param override_active 한 쪽 이상 override 활성
    @return 상태
    """
    used = ctx.used
    degraded = ctx.time_error or used.rank2_reason is not None
    if degraded or used.qm_errors:
        return State.DEGRADED
    values = ctx.values
    if values is not None and values.sensor_fault is True:
        return State.FAULT
    if values is not None and values.ignition_on is False:
        return State.OFF
    return State.OVERRIDE if override_active else State.NORMAL


def _warning_of(ctx: _Context) -> WarningCode:
    """@brief sensor fault 경고코드 (SWR-021)."""
    values = ctx.values
    if values is not None and values.sensor_fault is True:
        return WarningCode.W_SENSOR_FAULT
    return WarningCode.NONE


def arbitrate(
    used: UsedSnapshot,
    crash: CrashView,
    approach: tuple[SideProposal | None, SideProposal | None],
    qm: tuple[tuple[object, ...], tuple[object, ...]],
    previous: Decision,
    override_active: bool,
    time_error: bool,
) -> Decision:
    """@brief 한 평가의 최종 결과를 정한다 (SWR-019).

    @param used 쓰는 스냅샷
    @param crash 충돌 판정
    @param approach (좌, 우) 접근위험 제안
    @param qm (좌, 우) QM 제안 (controller가 튜플로 정규화한 값)
    @param previous 직전 결과
    @param override_active 한 쪽 이상 override 활성
    @param time_error 평가 시각 오류 여부 (SWR-022)
    @return 결과
    """
    ctx = _Context(used, crash, time_error)
    left = _decide_side(ctx, approach[0], qm[0], previous.lock_left)
    right = _decide_side(ctx, approach[1], qm[1], previous.lock_right)
    # 비교 순위가 높은(숫자가 작은) 쪽의 이유. 같으면 좌측(SWR-019).
    code = left[1] if left[2] <= right[2] else right[1]
    validity = InputValidity.INVALID if time_error else used.input_validity
    return Decision(
        lock_left=left[0],
        lock_right=right[0],
        state=_state_of(ctx, override_active),
        priority_reason=priority_reason_of(code),
        reason_code=code,
        input_validity=validity,
        reason_left=left[1],
        reason_right=right[1],
        warning_code=_warning_of(ctx),
    )
