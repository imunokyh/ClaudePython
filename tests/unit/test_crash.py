"""@brief safety.crash 단위 테스트 (SWR-007 래치, SWR-008 PENDING)."""

import pytest
from tests.helpers import snapshot

from child_lock.safety.crash import initial_memory, update, view
from child_lock.safety.validation import check_snapshot


def _rx(now, ref_ts=None, **signals):
    """@brief 이번 주기에 받은 스냅샷 검사 결과."""
    return check_snapshot(snapshot(**signals), now, ref_ts)


NONE_RX = check_snapshot(None, 0.0, None)


@pytest.mark.parametrize(
    ("age", "latched"), [(0.0, True), (1.0, True), (1.05, False)]
)
def test_confirmed_latches_only_within_max_age(age, latched):
    rx = _rx(10.0 + age, source_timestamp_s=10.0, crash_status="CONFIRMED")
    assert update(initial_memory(), rx, 10.0 + age).latched is latched


def test_latch_survives_none_while_ignition_on():
    mem = update(initial_memory(), _rx(10.0, crash_status="CONFIRMED"), 10.0)
    mem = update(mem, _rx(10.05, source_timestamp_s=10.05), 10.05)
    assert mem.latched


def test_latch_released_by_new_ignition_off_snapshot():
    mem = update(initial_memory(), _rx(10.0, crash_status="CONFIRMED"), 10.0)
    off = _rx(10.05, source_timestamp_s=10.05, ignition_on=False)
    assert not update(mem, off, 10.05).latched


def test_latch_not_released_when_still_confirmed():
    mem = update(initial_memory(), _rx(10.0, crash_status="CONFIRMED"), 10.0)
    off = _rx(
        10.05,
        source_timestamp_s=10.05,
        ignition_on=False,
        crash_status="CONFIRMED",
    )
    assert update(mem, off, 10.05).latched


def test_latch_not_released_without_new_snapshot():
    mem = update(initial_memory(), _rx(10.0, crash_status="CONFIRMED"), 10.0)
    assert update(mem, NONE_RX, 10.05).latched


def test_latch_not_released_when_ignition_invalid():
    mem = update(initial_memory(), _rx(10.0, crash_status="CONFIRMED"), 10.0)
    bad = _rx(10.05, source_timestamp_s=10.05, ignition_on=0)
    assert update(mem, bad, 10.05).latched


def test_other_signal_errors_do_not_block_latch():
    rx = _rx(10.0, crash_status="CONFIRMED", gear="X", sensor_fault=1)
    assert update(initial_memory(), rx, 10.0).latched


def test_late_confirmed_with_regressing_timestamp_still_latches():
    rx = _rx(10.0, 9.9, source_timestamp_s=9.5, crash_status="CONFIRMED")
    assert update(initial_memory(), rx, 10.0).latched


def test_invalid_crash_status_changes_nothing():
    mem = update(initial_memory(), _rx(10.0, crash_status="PENDING"), 10.0)
    assert update(mem, _rx(10.05, crash_status="BAD"), 10.05) == mem


def test_pending_filter_lasts_two_seconds_from_first_pending():
    mem = update(initial_memory(), _rx(10.0, crash_status="PENDING"), 10.0)
    mem = update(
        mem, _rx(11.0, source_timestamp_s=11.0, crash_status="PENDING"), 11.0
    )
    assert mem.pending_since == 10.0
    assert view(mem, 12.0).pending_filter
    assert not view(mem, 12.05).pending_filter


def test_pending_cleared_by_valid_none():
    mem = update(initial_memory(), _rx(10.0, crash_status="PENDING"), 10.0)
    mem = update(mem, _rx(10.05, source_timestamp_s=10.05), 10.05)
    assert mem.pending_since is None
    assert not view(mem, 10.05).pending_filter


def test_pending_kept_without_new_snapshot():
    mem = update(initial_memory(), _rx(10.0, crash_status="PENDING"), 10.0)
    assert update(mem, NONE_RX, 10.05).pending_since == 10.0


def test_pending_starts_even_when_timestamp_invalid():
    rx = _rx(10.0, source_timestamp_s=10.3, crash_status="PENDING")
    assert update(initial_memory(), rx, 10.0).pending_since == 10.0


def test_view_reports_latch():
    mem = update(initial_memory(), _rx(10.0, crash_status="CONFIRMED"), 10.0)
    assert view(mem, 10.0).latched
    assert not view(initial_memory(), 10.0).latched
