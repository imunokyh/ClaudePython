"""@brief safety.arbiter 단위 테스트 (SWR-008 필터, SWR-019, SWR-021)."""

from dataclasses import replace

import pytest
from tests.helpers import snapshot

from child_lock.safety.arbiter import arbitrate
from child_lock.safety.validation import check_snapshot
from child_lock.types import (
    CrashView,
    InputValidity,
    LockOutput,
    ReasonCode,
    SideProposal,
    State,
    UsedSnapshot,
    WarningCode,
    initial_decision,
)

L, R = LockOutput.LOCK, LockOutput.RELEASE
RC = ReasonCode
NO_CRASH = CrashView(latched=False, pending_filter=False)


def _used(qm_errors=frozenset(), **signals):
    """@brief 정상(순위 2 아님) 쓰는 스냅샷."""
    values = check_snapshot(snapshot(**signals), 10.0, None).values
    validity = InputValidity.INVALID if qm_errors else InputValidity.VALID
    return UsedSnapshot(values, frozenset(qm_errors), validity, None)


def _prev(left=R, right=R):
    """@brief 직전 결과 (출력만 지정)."""
    return replace(initial_decision(), lock_left=left, lock_right=right)


def _p(rank, output, reason):
    """@brief 제안 하나."""
    return SideProposal(rank, output, reason)


def _run(
    used=None,
    crash=NO_CRASH,
    approach=(None, None),
    qm=((), ()),
    prev=None,
    override=False,
    time_error=False,
):
    """@brief arbitrate를 기본값과 함께 부른다."""
    return arbitrate(
        used or _used(),
        crash,
        approach,
        qm,
        prev or _prev(),
        override,
        time_error,
    )


AUTO = _p(9, L, RC.AUTO_LOCK)
ISO = _p(8, L, RC.ISOFIX)
FIRE = _p(7, R, RC.FIRE)
RISK = _p(4, L, RC.APPROACH_RISK)


def test_crash_latch_releases_both_sides_over_everything():
    d = _run(
        crash=CrashView(True, False),
        approach=(RISK, RISK),
        qm=((AUTO,), (ISO,)),
        prev=_prev(L, L),
    )
    assert (d.lock_left, d.lock_right) == (R, R)
    assert d.reason_code is RC.CRASH_CONFIRMED
    assert d.priority_reason == "crash_confirmed"


def test_time_error_holds_outputs_and_is_degraded_invalid():
    d = _run(qm=((AUTO,), (AUTO,)), prev=_prev(L, R), time_error=True)
    assert (d.lock_left, d.lock_right) == (L, R)
    assert d.reason_code is RC.INPUT_INVALID
    assert d.state is State.DEGRADED
    assert d.input_validity is InputValidity.INVALID


def test_time_error_with_latch_still_releases():
    d = _run(crash=CrashView(True, False), prev=_prev(L, L), time_error=True)
    assert (d.lock_left, d.lock_right) == (R, R)
    assert d.state is State.DEGRADED


def test_stale_input_holds_outputs():
    stale = UsedSnapshot(None, frozenset(), InputValidity.STALE, RC.INPUT_STALE)
    d = _run(used=stale, qm=((AUTO,), (AUTO,)), prev=_prev(L, R))
    assert (d.lock_left, d.lock_right) == (L, R)
    assert d.reason_code is RC.INPUT_STALE
    assert d.state is State.DEGRADED
    assert d.warning_code is WarningCode.NONE


def test_sensor_fault_holds_outputs_even_with_approach_risk():
    d = _run(used=_used(sensor_fault=True), approach=(RISK, None))
    assert (d.lock_left, d.lock_right) == (R, R)
    assert d.reason_code is RC.SENSOR_FAULT
    assert d.state is State.FAULT
    assert d.warning_code is WarningCode.W_SENSOR_FAULT


def test_approach_side_ignores_qm_while_other_side_uses_qm():
    d = _run(approach=(RISK, None), qm=((FIRE,), (ISO,)))
    assert (d.lock_left, d.lock_right) == (L, L)
    assert (d.reason_left, d.reason_right) == (RC.APPROACH_RISK, RC.ISOFIX)
    assert d.reason_code is RC.APPROACH_RISK


def test_qm_signal_error_holds_sides_without_asil_b_decision():
    used = _used(qm_errors={"isofix_left"})
    d = _run(used=used, approach=(RISK, None), qm=((), (AUTO,)))
    assert (d.lock_left, d.lock_right) == (L, R)
    assert (d.reason_left, d.reason_right) == (
        RC.APPROACH_RISK,
        RC.INPUT_INVALID,
    )
    assert d.reason_code is RC.APPROACH_RISK
    assert d.state is State.DEGRADED


def test_qm_error_with_sensor_fault_is_degraded():
    used = _used(qm_errors={"gear"}, sensor_fault=True)
    assert _run(used=used).state is State.DEGRADED


def test_highest_ranked_valid_qm_proposal_wins():
    d = _run(qm=((AUTO, FIRE, ISO), (_p(10, L, RC.DRIVER_COMMAND),)))
    assert (d.lock_left, d.lock_right) == (R, L)
    assert (d.reason_left, d.reason_right) == (RC.FIRE, RC.DRIVER_COMMAND)
    assert d.reason_code is RC.FIRE
    assert d.priority_reason == "fire_detected"


def test_same_rank_proposals_take_the_first():
    first = _p(10, L, RC.DRIVER_COMMAND)
    second = _p(10, R, RC.DRIVER_COMMAND)
    assert _run(qm=((first, second), ())).lock_left is L


@pytest.mark.parametrize(
    "bad",
    [
        SideProposal(8, "LOCK", RC.ISOFIX),
        SideProposal(8.0, L, RC.ISOFIX),
        SideProposal(6, L, RC.ISOFIX),
        SideProposal(6, L, RC.IGNITION_OFF),
        SideProposal(9, R, RC.AUTO_LOCK),
        SideProposal(11, L, RC.NO_CHANGE),
        SideProposal(10, None, RC.DRIVER_COMMAND),
        SideProposal(10, L, "DRIVER_COMMAND"),
        (9, L, RC.AUTO_LOCK),
        None,
    ],
)
def test_malformed_qm_proposal_is_discarded(bad):
    d = _run(qm=((bad,), ()), prev=_prev(R, R))
    assert d.lock_left is R
    assert d.reason_left is RC.NO_CHANGE


def test_no_rule_keeps_previous_output():
    d = _run(prev=_prev(L, R))
    assert (d.lock_left, d.lock_right) == (L, R)
    assert d.reason_code is RC.NO_CHANGE
    assert d.state is State.NORMAL


def test_pending_filter_blocks_qm_lock_transition():
    d = _run(crash=CrashView(False, True), qm=((AUTO,), (AUTO,)))
    assert (d.lock_left, d.lock_right) == (R, R)
    assert d.reason_code is RC.CRASH_PENDING


def test_pending_filter_does_not_block_when_already_locked():
    d = _run(crash=CrashView(False, True), qm=((AUTO,), ()), prev=_prev(L, R))
    assert d.lock_left is L
    assert d.reason_left is RC.AUTO_LOCK


def test_pending_filter_does_not_block_release_or_approach_lock():
    d = _run(
        crash=CrashView(False, True), approach=(RISK, None), qm=((), (FIRE,))
    )
    assert (d.lock_left, d.lock_right) == (L, R)


def test_pending_reason_compares_with_rank_of_blocked_rule():
    driver = _p(10, R, RC.DRIVER_COMMAND)
    d = _run(
        crash=CrashView(False, True), qm=((AUTO,), (driver,)), prev=_prev(R, L)
    )
    assert d.reason_left is RC.CRASH_PENDING
    assert d.reason_code is RC.CRASH_PENDING


def test_equal_rank_reason_prefers_left():
    d = _run(qm=((_p(8, L, RC.ISOFIX),), (_p(8, L, RC.ISOFIX),)))
    assert d.reason_code is RC.ISOFIX


def test_right_side_reason_wins_when_higher_rank():
    d = _run(qm=((AUTO,), (FIRE,)))
    assert d.reason_code is RC.FIRE


def test_state_off_when_ignition_false():
    assert _run(used=_used(ignition_on=False)).state is State.OFF


def test_state_override_when_override_active():
    assert _run(override=True).state is State.OVERRIDE


def test_state_fault_precedes_off():
    used = _used(sensor_fault=True, ignition_on=False)
    assert _run(used=used).state is State.FAULT


def test_input_validity_is_copied_from_used_snapshot():
    used = _used(qm_errors={"gear"})
    assert _run(used=used).input_validity is InputValidity.INVALID
