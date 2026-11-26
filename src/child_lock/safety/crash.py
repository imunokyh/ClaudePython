"""@brief 충돌 래치와 PENDING 필터 타이머 (ASIL B, SWE3-DD 2.3).

충돌 판정은 이번 주기에 받은 스냅샷의 `crash_status`와 충돌 판정용 시각만
쓴다. 다른 신호의 오류나 입력 지연과 무관하다(SWR-007).
"""

from __future__ import annotations

from dataclasses import dataclass

from child_lock.types import (
    CRASH_MAX_AGE_S,
    EPS,
    PENDING_LIMIT_S,
    CrashStatus,
    CrashView,
    SnapshotCheck,
)


@dataclass(frozen=True, slots=True)
class CrashMemory:
    """@brief 평가 사이에 남는 충돌 상태."""

    latched: bool
    pending_since: float | None


def initial_memory() -> CrashMemory:
    """@brief 초기 충돌 상태: 래치 없음, PENDING 없음."""
    return CrashMemory(latched=False, pending_since=None)


def _update_latch(latched: bool, check: SnapshotCheck, now: float) -> bool:
    """@brief 충돌 래치를 설정하거나 해제한다 (SWR-007).

    @param latched 현재 래치
    @param check 이번 주기 스냅샷 검사 결과
    @param now 평가 시각
    @return 새 래치
    """
    status, ts = check.crash_status, check.crash_timestamp_s
    if not check.received or status is None or ts is None:
        return latched
    if status is CrashStatus.CONFIRMED:
        # 나이 1.0초 이하인 CONFIRMED만 래치를 세운다(A-14).
        return latched or now - ts <= CRASH_MAX_AGE_S + EPS
    # 해제는 새로 받은 스냅샷의 유효한 ignition_on=false일 때만 한다.
    values = check.values
    ignition_off = values is not None and values.ignition_on is False
    return latched and not ignition_off


def _update_pending(
    since: float | None, check: SnapshotCheck, now: float
) -> float | None:
    """@brief PENDING 시작 시각을 갱신한다 (SWR-008).

    유효한 crash_status만 요구한다(타임스탬프 유효는 요구하지 않음).

    @param since 현재 PENDING 시작 시각
    @param check 이번 주기 스냅샷 검사 결과
    @param now 평가 시각
    @return 새 PENDING 시작 시각
    """
    if not check.received or check.crash_status is None:
        return since
    if check.crash_status is CrashStatus.PENDING:
        return now if since is None else since
    return None


def update(
    memory: CrashMemory, check: SnapshotCheck, now: float
) -> CrashMemory:
    """@brief 이번 주기 스냅샷으로 충돌 상태를 갱신한다.

    @param memory 직전 충돌 상태
    @param check 이번 주기 스냅샷 검사 결과
    @param now 평가 시각
    @return 새 충돌 상태
    """
    return CrashMemory(
        latched=_update_latch(memory.latched, check, now),
        pending_since=_update_pending(memory.pending_since, check, now),
    )


def view(memory: CrashMemory, now: float) -> CrashView:
    """@brief arbiter·approach에 넘길 충돌 판정 결과를 만든다.

    @param memory 충돌 상태
    @param now 평가 시각
    @return 래치 여부와 PENDING 필터 활성 여부(시작 후 2.0초 이하)
    """
    since = memory.pending_since
    active = since is not None and now - since <= PENDING_LIMIT_S + EPS
    return CrashView(latched=memory.latched, pending_filter=active)
