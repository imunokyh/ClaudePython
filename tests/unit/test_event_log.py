"""@brief qm.event_log 단위 테스트 (SWR-010, SWR-011, SWR-012)."""

from dataclasses import replace

from child_lock.qm.event_log import EventLog
from child_lock.types import LockOutput, initial_decision

D0 = initial_decision()
D1 = replace(D0, lock_left=LockOutput.LOCK)


def test_first_evaluation_is_recorded():
    log = EventLog()
    assert log.record(1.0, D0, had_commands=False)
    (rec,) = log.events()
    assert rec.event_id == 1
    assert rec.timestamp_s == 1.0
    assert rec.decision == D0


def test_unchanged_result_without_command_is_not_recorded():
    log = EventLog()
    log.record(1.0, D0, False)
    for i in range(10):
        assert not log.record(1.05 + i, D0, False)
    assert len(log.events()) == 1


def test_command_evaluation_is_recorded_even_if_unchanged():
    log = EventLog()
    log.record(1.0, D0, False)
    assert log.record(1.05, D0, True)
    assert [r.event_id for r in log.events()] == [1, 2]


def test_changed_result_is_recorded():
    log = EventLog()
    log.record(1.0, D0, False)
    assert log.record(1.05, D1, False)
    assert log.events()[-1].decision == D1


def test_keeps_only_latest_capacity_in_order():
    log = EventLog()
    for i in range(101):
        log.record(float(i), D0 if i % 2 else D1, False)
    ids = [r.event_id for r in log.events()]
    assert ids == list(range(2, 102))


def test_new_log_is_empty():
    assert EventLog().events() == ()
