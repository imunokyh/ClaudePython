"""@brief 기준 스냅샷과 입력 지연 판정 (ASIL B, SWE3-DD 2.2).

기준 스냅샷은 ASIL B 신호가 모두 유효한 마지막 스냅샷이다(SWR-013).
스냅샷이 없거나 ASIL B 오류가 있는 주기에는 기준 스냅샷 값을 쓴다.
"""

from __future__ import annotations

from child_lock.types import (
    EPS,
    STALE_LIMIT_S,
    InputValidity,
    ReasonCode,
    SnapshotCheck,
    UsedSnapshot,
)


def _is_stale(ref: SnapshotCheck | None, now: float) -> bool:
    """@brief 기준 스냅샷이 없거나 0.200초보다 오래되었는지 본다.

    @param ref 기준 스냅샷
    @param now 평가 시각
    @return 지연이면 True
    """
    if ref is None or ref.values is None:
        return True
    age = now - ref.values.source_timestamp_s
    return age > STALE_LIMIT_S + EPS


def select(
    check: SnapshotCheck, now: float, ref: SnapshotCheck | None
) -> tuple[UsedSnapshot, SnapshotCheck | None]:
    """@brief 이번 평가에 쓸 스냅샷과 입력 상태를 정한다 (SWR-013, SWR-022).

    @param check 이번 주기 스냅샷 검사 결과
    @param now 평가 시각
    @param ref 직전 기준 스냅샷
    @return (쓰는 스냅샷, 새 기준 스냅샷)
    """
    # ASIL B 신호가 모두 유효한 새 스냅샷만 기준 스냅샷이 된다(QM 오류는 허용).
    if check.received and not check.asil_b_errors:
        ref = check
    values = ref.values if ref is not None else None
    qm_errors = ref.qm_errors if ref is not None else frozenset()
    if check.received and check.asil_b_errors:
        validity, rank2 = InputValidity.INVALID, ReasonCode.INPUT_INVALID
    elif _is_stale(ref, now):
        validity, rank2 = InputValidity.STALE, ReasonCode.INPUT_STALE
    else:
        # QM 신호 오류만 있으면 순위 5로 처리하도록 INVALID만 표시한다.
        validity = InputValidity.INVALID if qm_errors else InputValidity.VALID
        rank2 = None
    return UsedSnapshot(values, qm_errors, validity, rank2), ref
