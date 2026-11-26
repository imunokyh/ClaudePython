"""@brief controller 단위 테스트 (SWR-016, SWR-022, 간섭 배제)."""

import math

import pytest
from tests.helpers import command, snapshot

from child_lock import controller as controller_module
from child_lock.controller import Controller
from child_lock.qm.event_log import EventLog
from child_lock.types import (
    InputValidity,
    LockOutput,
    RawInput,
    ReasonCode,
    State,
    initial_decision,
)

L, R = LockOutput.LOCK, LockOutput.RELEASE


def _raw(snap=None, cmds=()):
    """@brief 원시 입력 하나."""
    return RawInput(snapshot=snap, commands=tuple(cmds))


def _at(ts, **signals):
    """@brief 시각 ts의 스냅샷 원시 입력."""
    return _raw(snapshot(source_timestamp_s=ts, **signals))


def test_last_decision_is_initial_before_any_evaluation():
    assert Controller().last_decision == initial_decision()


def test_normal_evaluation_with_auto_lock():
    ctl = Controller()
    d = ctl.evaluate(10.0, _at(10.0, vehicle_speed_kph=3.0))
    assert (d.lock_left, d.lock_right) == (L, L)
    assert d.reason_code is ReasonCode.AUTO_LOCK
    assert ctl.last_decision == d


def test_evaluation_without_snapshot_uses_reference():
    ctl = Controller()
    ctl.evaluate(10.0, _at(10.0, vehicle_speed_kph=3.0))
    d = ctl.evaluate(10.05, _raw())
    assert d.reason_code is ReasonCode.AUTO_LOCK
    assert d.input_validity is InputValidity.VALID


@pytest.mark.parametrize("bad_now", [10.0, 9.0, math.nan, math.inf])
def test_non_increasing_or_non_finite_time_is_time_error(bad_now):
    ctl = Controller()
    ctl.evaluate(10.0, _at(10.0, vehicle_speed_kph=3.0))
    d = ctl.evaluate(bad_now, _at(10.0, crash_status="CONFIRMED"))
    assert (d.lock_left, d.lock_right) == (L, L)
    assert d.reason_code is ReasonCode.INPUT_INVALID
    assert d.state is State.DEGRADED
    assert d.input_validity is InputValidity.INVALID


def test_time_error_keeps_existing_latch_and_recovers():
    ctl = Controller()
    ctl.evaluate(10.0, _at(10.0, crash_status="CONFIRMED"))
    d = ctl.evaluate(9.0, _at(9.0))
    assert d.reason_code is ReasonCode.CRASH_CONFIRMED
    d = ctl.evaluate(10.05, _at(10.05))
    assert d.reason_code is ReasonCode.CRASH_CONFIRMED
    assert d.state is State.NORMAL


def test_time_error_does_not_update_reference():
    ctl = Controller()
    ctl.evaluate(10.0, _at(10.0))
    ctl.evaluate(9.0, _at(11.0, vehicle_speed_kph=3.0))
    d = ctl.evaluate(10.05, _raw())
    assert d.reason_code is ReasonCode.NO_CHANGE


def test_time_error_evaluation_is_recorded():
    log = EventLog()
    ctl = Controller(log)
    ctl.evaluate(10.0, _at(10.0))
    ctl.evaluate(9.0, _raw(cmds=[command()]))
    assert log.events()[-1].decision.reason_code is ReasonCode.INPUT_INVALID


def test_override_through_full_flow_sets_state_override():
    ctl = Controller()
    risk = {"rear_left_approach_risk": True}
    ctl.evaluate(10.0, _raw(snapshot(**risk), [command()]))
    d = ctl.evaluate(10.05, _raw(cmds=[command(source="voice")]))
    assert d.lock_left is R
    assert d.reason_left is ReasonCode.DRIVER_OVERRIDE
    assert d.state is State.OVERRIDE


def test_rules_exception_is_isolated(monkeypatch):
    def boom(values, commands):
        raise RuntimeError("qm failure")

    monkeypatch.setattr(controller_module.rules, "proposals", boom)
    ctl = Controller()
    d = ctl.evaluate(10.0, _at(10.0, vehicle_speed_kph=3.0))
    assert (d.lock_left, d.lock_right) == (R, R)
    assert d.reason_code is ReasonCode.NO_CHANGE


@pytest.mark.parametrize(
    "bad_result",
    [None, (1,), ((), (), ()), "ab", (x for x in ())],
)
def test_malformed_rules_result_is_ignored(monkeypatch, bad_result):
    monkeypatch.setattr(
        controller_module.rules, "proposals", lambda v, c: bad_result
    )
    d = Controller().evaluate(10.0, _at(10.0, vehicle_speed_kph=3.0))
    assert d.reason_code is ReasonCode.NO_CHANGE


def test_rules_returning_lists_are_normalized(monkeypatch):
    real = controller_module.rules.proposals

    def as_lists(values, commands):
        left, right = real(values, commands)
        return [list(left), list(right)]

    monkeypatch.setattr(controller_module.rules, "proposals", as_lists)
    d = Controller().evaluate(10.0, _at(10.0, vehicle_speed_kph=3.0))
    assert d.reason_code is ReasonCode.AUTO_LOCK


def test_event_log_failure_does_not_affect_decision():
    class Broken:
        def record(self, now, decision, had_commands):
            raise OSError("disk")

    d = Controller(Broken()).evaluate(10.0, _at(10.0, vehicle_speed_kph=3.0))
    assert d.reason_code is ReasonCode.AUTO_LOCK


def test_events_are_recorded_with_command_flag():
    log = EventLog()
    ctl = Controller(log)
    ctl.evaluate(10.0, _at(10.0))
    ctl.evaluate(10.05, _raw(cmds=[command(side="bad")]))
    assert len(log.events()) == 2
