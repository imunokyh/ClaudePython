"""@brief safety.monitor 단위 테스트 (SWR-013 기준 스냅샷·지연, SWR-022)."""

from tests.helpers import snapshot

from child_lock.safety.monitor import select
from child_lock.safety.validation import check_snapshot
from child_lock.types import InputValidity, ReasonCode


def _check(now, ref=None, **signals):
    """@brief 원시 스냅샷을 검사한다."""
    ref_ts = ref.values.source_timestamp_s if ref else None
    return check_snapshot(snapshot(**signals), now, ref_ts)


NONE = check_snapshot(None, 0.0, None)


def test_valid_new_snapshot_becomes_reference():
    check = _check(10.0, source_timestamp_s=10.0)
    used, ref = select(check, 10.0, None)
    assert ref is check
    assert used.values is check.values
    assert used.input_validity is InputValidity.VALID
    assert used.rank2_reason is None


def test_asil_b_error_keeps_reference_and_is_invalid():
    ref = _check(10.0, source_timestamp_s=10.0)
    bad = _check(10.05, ref, source_timestamp_s=10.05, ignition_on=1)
    used, new_ref = select(bad, 10.05, ref)
    assert new_ref is ref
    assert used.values is ref.values
    assert used.input_validity is InputValidity.INVALID
    assert used.rank2_reason is ReasonCode.INPUT_INVALID


def test_reference_age_at_limit_is_not_stale():
    ref = _check(10.0, source_timestamp_s=10.0)
    used, _ = select(NONE, 10.2, ref)
    assert used.input_validity is InputValidity.VALID


def test_reference_older_than_limit_is_stale():
    ref = _check(10.0, source_timestamp_s=10.0)
    used, _ = select(NONE, 10.25, ref)
    assert used.input_validity is InputValidity.STALE
    assert used.rank2_reason is ReasonCode.INPUT_STALE
    assert used.values is ref.values


def test_no_reference_yet_is_stale_without_values():
    used, ref = select(NONE, 0.0, None)
    assert ref is None
    assert used.values is None
    assert used.rank2_reason is ReasonCode.INPUT_STALE


def test_qm_error_only_snapshot_becomes_reference_with_invalid():
    check = _check(10.0, source_timestamp_s=10.0, gear="X")
    used, ref = select(check, 10.0, None)
    assert ref is check
    assert used.rank2_reason is None
    assert used.qm_errors == {"gear"}
    assert used.input_validity is InputValidity.INVALID


def test_qm_errors_of_reference_persist_without_new_snapshot():
    ref = _check(10.0, source_timestamp_s=10.0, isofix_left=1)
    used, _ = select(NONE, 10.05, ref)
    assert used.qm_errors == {"isofix_left"}
    assert used.input_validity is InputValidity.INVALID


def test_continuous_qm_error_does_not_become_stale():
    ref = None
    for i in range(11):
        now = 10.0 + i * 0.05
        check = _check(now, ref, source_timestamp_s=now, gear="X")
        used, ref = select(check, now, ref)
    assert used.rank2_reason is None
    assert used.input_validity is InputValidity.INVALID
