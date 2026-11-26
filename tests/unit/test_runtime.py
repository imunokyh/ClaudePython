"""@brief runtime.clock, runtime.runner 단위 테스트 (SWR-022)."""

import threading
import time

from tests.helpers import command, raw_snapshot

from child_lock.controller import Controller
from child_lock.qm.event_log import EventLog
from child_lock.runtime.clock import MonotonicClock, ScriptedClock
from child_lock.runtime.runner import Runner
from child_lock.types import LockOutput, ReasonCode, initial_decision


class Recorder:
    """@brief 받은 입력을 기록하는 controller 시험 대역."""

    def __init__(self):
        self.calls = []
        self.last_decision = initial_decision()

    def evaluate(self, now, raw):
        self.calls.append((now, raw))
        return self.last_decision


def _runner(controller=None, log=None):
    """@brief 시험용 시계와 runner."""
    clock = ScriptedClock(10.0)
    return clock, Runner(clock, controller or Recorder(), log)


def test_scripted_clock_set_and_advance():
    clock = ScriptedClock(1.0)
    clock.advance(0.05)
    assert clock.now() == 1.05
    clock.set(3.0)
    assert clock.now() == 3.0


def test_monotonic_clock_does_not_go_backwards():
    clock = MonotonicClock()
    first = clock.now()
    assert clock.now() >= first


def test_tick_passes_clock_time_and_mailbox():
    clock, runner = _runner()
    runner.submit(raw_snapshot(), [{"side": "left"}], has_snapshot=True)
    runner.tick()
    now, raw = runner._controller.calls[0]
    assert now == 10.0
    assert raw.snapshot.get("gear") == "P"
    assert len(raw.commands) == 1


def test_mailbox_is_emptied_after_tick():
    clock, runner = _runner()
    runner.submit(raw_snapshot(), [], has_snapshot=True)
    runner.tick()
    clock.advance(0.05)
    runner.tick()
    _, raw = runner._controller.calls[1]
    assert raw.snapshot is None
    assert raw.commands == ()


def test_latest_snapshot_wins_and_dropped_is_counted():
    _, runner = _runner()
    runner.submit(raw_snapshot(gear="P"), [], True)
    runner.submit(raw_snapshot(gear="D"), [], True)
    runner.tick()
    _, raw = runner._controller.calls[0]
    assert raw.snapshot.get("gear") == "D"
    assert raw.dropped_snapshots == 1
    assert runner.dropped_snapshots == 1


def test_confirmed_snapshot_is_kept_over_later_snapshot():
    _, runner = _runner()
    runner.submit(raw_snapshot(crash_status="CONFIRMED"), [], True)
    runner.submit(raw_snapshot(crash_status="NONE"), [], True)
    runner.tick()
    _, raw = runner._controller.calls[0]
    assert raw.snapshot.get("crash_status") == "CONFIRMED"


def test_later_confirmed_replaces_earlier_snapshot():
    _, runner = _runner()
    runner.submit(raw_snapshot(), [], True)
    runner.submit(raw_snapshot(crash_status="CONFIRMED"), [], True)
    runner.tick()
    _, raw = runner._controller.calls[0]
    assert raw.snapshot.get("crash_status") == "CONFIRMED"


def test_commands_only_submission_keeps_snapshot_and_appends():
    _, runner = _runner()
    runner.submit(raw_snapshot(), [command()], True)
    runner.submit(None, [{"side": "right"}], has_snapshot=False)
    runner.tick()
    _, raw = runner._controller.calls[0]
    assert raw.snapshot is not None
    assert len(raw.commands) == 2


def test_submitted_input_is_frozen_against_later_changes():
    _, runner = _runner()
    snap = raw_snapshot()
    runner.submit(snap, [], True)
    snap["gear"] = "R"
    runner.tick()
    _, raw = runner._controller.calls[0]
    assert raw.snapshot.get("gear") == "P"


def test_evaluation_exception_keeps_previous_decision():
    class Failing(Recorder):
        def evaluate(self, now, raw):
            raise RuntimeError("bug")

    _, runner = _runner(Failing())
    assert runner.tick() == initial_decision()
    assert runner.evaluation_errors == 1


def test_status_and_events_with_real_controller():
    log = EventLog()
    clock = ScriptedClock(10.0)
    runner = Runner(clock, Controller(log), log)
    runner.submit(raw_snapshot(vehicle_speed_kph=3.0), [], True)
    runner.tick()
    assert runner.status().reason_code is ReasonCode.AUTO_LOCK
    assert runner.status().lock_left is LockOutput.LOCK
    assert len(runner.events()) == 1


def test_events_without_log_is_empty():
    _, runner = _runner()
    assert runner.events() == ()


def test_create_default_builds_working_runner():
    runner = Runner.create_default()
    runner.submit(raw_snapshot(), [], True)
    runner.tick()
    assert len(runner.events()) == 1


def test_periodic_thread_ticks_and_stops():
    recorder = Recorder()
    runner = Runner(MonotonicClock(), recorder, None, period_s=0.01)
    runner.start()
    time.sleep(0.1)
    runner.stop()
    count = len(recorder.calls)
    assert count >= 3
    time.sleep(0.05)
    assert len(recorder.calls) == count


def test_overrun_is_counted_and_missed_cycles_are_not_caught_up():
    class Slow(Recorder):
        def evaluate(self, now, raw):
            super().evaluate(now, raw)
            time.sleep(0.05)
            return self.last_decision

    slow = Slow()
    runner = Runner(MonotonicClock(), slow, None, period_s=0.01)
    runner.start()
    time.sleep(0.3)
    runner.stop()
    assert runner.overruns >= 1
    assert len(slow.calls) <= 8


def test_stop_is_safe_without_start_and_start_twice_is_ignored():
    _, runner = _runner()
    runner.stop()
    runner.start()
    thread = runner._thread
    runner.start()
    assert runner._thread is thread
    runner.stop()


def test_submit_is_serialized_with_tick():
    _, runner = _runner()
    barrier = threading.Barrier(4)

    def worker():
        barrier.wait()
        for _ in range(50):
            runner.submit(None, [command()], has_snapshot=False)

    threads = [threading.Thread(target=worker) for _ in range(4)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    runner.tick()
    _, raw = runner._controller.calls[0]
    assert len(raw.commands) == 200


def test_runner_now_reports_clock_time():
    clock, runner = _runner()
    clock.set(42.5)
    assert runner.now() == 42.5
