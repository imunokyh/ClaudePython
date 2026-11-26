"""@brief safety.approach 단위 테스트 (SWR-005, SWR-006, SWR-009)."""

from dataclasses import replace

from tests.helpers import snapshot

from child_lock.safety.approach import evaluate, initial_memory
from child_lock.safety.validation import check_snapshot
from child_lock.types import (
    Action,
    CrashView,
    DriverCommand,
    InputValidity,
    LockOutput,
    ReasonCode,
    Side,
    SideProposal,
    Source,
    UsedSnapshot,
)

NO_CRASH = CrashView(latched=False, pending_filter=False)
LOCK = SideProposal(4, LockOutput.LOCK, ReasonCode.APPROACH_RISK)
OVERRIDE = SideProposal(4, LockOutput.RELEASE, ReasonCode.DRIVER_OVERRIDE)


def _used(ts=10.0, **signals):
    """@brief 접근위험 판정에 쓰는 스냅샷."""
    values = check_snapshot(
        snapshot(source_timestamp_s=ts, **signals), ts, None
    ).values
    return UsedSnapshot(values, frozenset(), InputValidity.VALID, None)


def _unlock(side=Side.LEFT, source=Source.PHYSICAL_BUTTON):
    """@brief 해제 명령 하나."""
    return DriverCommand(side, Action.UNLOCK, source)


RISK_L = {"rear_left_approach_risk": True}


class Run:
    """@brief 평가를 이어서 실행하는 도우미 (메모리·평가 번호 보관)."""

    def __init__(self):
        self.memory = initial_memory()
        self.index = 0

    def step(self, used, commands=(), crash=NO_CRASH, frozen=False):
        """@brief 평가 1회를 실행하고 (좌, 우) 제안을 돌려준다."""
        self.index += 1
        self.memory, left, right = evaluate(
            self.memory, used, tuple(commands), crash, frozen, self.index
        )
        return left, right


def test_no_values_keeps_memory_and_proposes_nothing():
    run = Run()
    empty = UsedSnapshot(None, frozenset(), InputValidity.STALE, None)
    assert run.step(empty) == (None, None)
    assert run.memory == initial_memory()


def test_risk_locks_that_side_only():
    assert Run().step(_used(**RISK_L)) == (LOCK, None)


def test_first_unlock_is_suppressed():
    run = Run()
    assert run.step(_used(**RISK_L), [_unlock()])[0] == LOCK
    assert run.memory.left.first_suppress_ts == 10.0


def test_second_unlock_within_window_overrides():
    run = Run()
    run.step(_used(10.0, **RISK_L), [_unlock()])
    left, _ = run.step(_used(20.0, **RISK_L), [_unlock(source=Source.VOICE)])
    assert left == OVERRIDE
    assert run.memory.left.override


def test_second_unlock_after_window_is_new_first_suppression():
    run = Run()
    run.step(_used(10.0, **RISK_L), [_unlock()])
    left, _ = run.step(_used(20.05, **RISK_L), [_unlock()])
    assert left == LOCK
    assert run.memory.left.first_suppress_ts == 20.05


def test_duplicate_unlock_in_same_evaluation_is_not_reentry():
    run = Run()
    left, _ = run.step(_used(**RISK_L), [_unlock(), _unlock()])
    assert left == LOCK


def test_reentry_in_next_evaluation_without_new_snapshot_overrides():
    run = Run()
    same = _used(10.0, **RISK_L)
    run.step(same, [_unlock()])
    assert run.step(same, [_unlock()])[0] == OVERRIDE


def test_unlock_at_auto_lock_speed_is_not_counted():
    run = Run()
    fast = _used(10.0, vehicle_speed_kph=3.0, **RISK_L)
    run.step(fast, [_unlock()])
    assert (
        run.step(_used(10.05, vehicle_speed_kph=3.0, **RISK_L), [_unlock()])[0]
        == LOCK
    )
    assert run.memory.left.first_suppress_ts is None


def test_frozen_evaluation_does_not_count_unlock():
    run = Run()
    run.step(_used(**RISK_L), [_unlock()], frozen=True)
    assert run.memory.left.first_suppress_ts is None
    assert run.step(_used(10.05, **RISK_L), [_unlock()])[0] == LOCK


def test_override_persists_while_risk_and_ends_when_risk_clears():
    run = Run()
    run.step(_used(10.0, **RISK_L), [_unlock()])
    run.step(_used(10.05, **RISK_L), [_unlock()])
    assert run.step(_used(10.1, **RISK_L))[0] == OVERRIDE
    assert run.step(_used(10.15)) == (None, None)
    assert run.step(_used(10.2, **RISK_L))[0] == LOCK


def test_override_ends_at_auto_lock_speed():
    run = Run()
    run.step(_used(10.0, **RISK_L), [_unlock()])
    run.step(_used(10.05, **RISK_L), [_unlock()])
    assert run.step(_used(10.1, vehicle_speed_kph=3.0, **RISK_L))[0] == LOCK


def test_override_ends_on_ignition_off_and_latch():
    for change in ({"ignition_on": False}, {}):
        run = Run()
        run.step(_used(10.0, **RISK_L), [_unlock()])
        run.step(_used(10.05, **RISK_L), [_unlock()])
        crash = replace(NO_CRASH, latched=not change)
        run.step(_used(10.1, **RISK_L, **change), crash=crash)
        assert not run.memory.left.override


def test_sides_are_independent():
    run = Run()
    both = {"rear_left_approach_risk": True, "rear_right_approach_risk": True}
    run.step(_used(10.0, **both), [_unlock(Side.LEFT)])
    left, right = run.step(_used(10.05, **both), [_unlock(Side.LEFT)])
    assert left == OVERRIDE
    assert right == LOCK
    assert run.memory.right.first_suppress_ts is None


def test_all_command_counts_for_both_sides():
    run = Run()
    both = {"rear_left_approach_risk": True, "rear_right_approach_risk": True}
    all_cmd = [_unlock(Side.LEFT), _unlock(Side.RIGHT)]
    run.step(_used(10.0, **both), all_cmd)
    assert run.step(_used(10.05, **both), all_cmd) == (OVERRIDE, OVERRIDE)


def test_further_unlock_during_override_keeps_override():
    run = Run()
    run.step(_used(10.0, **RISK_L), [_unlock()])
    run.step(_used(10.05, **RISK_L), [_unlock()])
    assert run.step(_used(10.1, **RISK_L), [_unlock()])[0] == OVERRIDE
    assert run.memory.left.override


def test_lock_command_does_not_count_as_unlock():
    run = Run()
    lock_cmd = DriverCommand(Side.LEFT, Action.LOCK, Source.AVN)
    run.step(_used(**RISK_L), [lock_cmd])
    assert run.memory.left.first_suppress_ts is None
