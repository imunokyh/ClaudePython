"""@brief 통합 테스트 IT-01~IT-11 (SWE5-ITS).

web(HTTP) → runner → controller → safety/qm 전 구간을 시험용 시계로 구동한다.
"""

import gc
import threading
import time
import tracemalloc

import pytest
from fastapi.testclient import TestClient
from tests.helpers import raw_snapshot

from child_lock import controller as controller_module
from child_lock.controller import Controller
from child_lock.qm.event_log import EventLog
from child_lock.qm.replay import decision_hash
from child_lock.runtime.clock import MonotonicClock, ScriptedClock
from child_lock.runtime.runner import Runner
from child_lock.web.app import create_app


class Sim:
    """@brief HTTP로 입력하고 tick으로 평가를 진행하는 시험 하니스."""

    def __init__(self, client, runner, clock):
        self.client, self.runner, self.clock = client, runner, clock

    def post(self, commands=None, **signals):
        """@brief 현재 시각 타임스탬프의 스냅샷(과 명령)을 HTTP로 보낸다."""
        snap = raw_snapshot(source_timestamp_s=self.clock.now(), **signals)
        body = {"snapshot": snap, "commands": commands or []}
        assert self.client.post("/input", json=body).status_code == 202

    def step(self):
        """@brief 평가 1회 후 시각을 한 주기 옮기고 상태를 조회한다."""
        self.runner.tick()
        self.clock.advance(0.05)
        return self.client.get("/status").json()


@pytest.fixture
def sim():
    """@brief 시험용 시계로 구성한 전 구간 하니스."""
    clock = ScriptedClock(100.0)
    log = EventLog()
    runner = Runner(clock, Controller(log), log)
    with TestClient(create_app(runner)) as client:
        yield Sim(client, runner, clock)


def _cmd(side="left", action="unlock", source="physical_button"):
    """@brief 원시 운전자 명령."""
    return {"side": side, "action": action, "source": source}


def test_it01_driving_scenario_end_to_end(sim):
    sim.post()
    assert sim.step()["lock_left"] == "RELEASE"
    sim.post(vehicle_speed_kph=3.0, gear="D")
    st = sim.step()
    assert (st["lock_left"], st["lock_right"], st["reason_code"]) == (
        "LOCK",
        "LOCK",
        "AUTO_LOCK",
    )
    sim.post(vehicle_speed_kph=0.0)
    assert sim.step()["lock_left"] == "LOCK"
    sim.post(commands=[_cmd("all")], vehicle_speed_kph=0.0)
    st = sim.step()
    assert (st["lock_left"], st["lock_right"], st["reason_code"]) == (
        "RELEASE",
        "RELEASE",
        "DRIVER_COMMAND",
    )


def test_it02_crash_release_within_one_cycle_and_latched(sim):
    sim.post(vehicle_speed_kph=40.0)
    sim.step()
    sim.post(vehicle_speed_kph=40.0, crash_status="CONFIRMED")
    st = sim.step()
    assert (st["lock_left"], st["lock_right"]) == ("RELEASE", "RELEASE")
    assert st["reason_code"] == "CRASH_CONFIRMED"
    sim.post(vehicle_speed_kph=40.0, isofix_left=True)
    st = sim.step()
    assert (st["lock_left"], st["reason_code"]) == (
        "RELEASE",
        "CRASH_CONFIRMED",
    )


def test_it03_approach_suppression_and_override(sim):
    sim.post(commands=[_cmd()], rear_left_approach_risk=True)
    st = sim.step()
    assert (st["lock_left"], st["reason_left"]) == ("LOCK", "APPROACH_RISK")
    sim.post(commands=[_cmd(source="voice")], rear_left_approach_risk=True)
    st = sim.step()
    assert (st["lock_left"], st["state"]) == ("RELEASE", "OVERRIDE")
    assert st["reason_left"] == "DRIVER_OVERRIDE"


def test_it04_input_loss_detected_by_periodic_evaluation(sim):
    sim.post(vehicle_speed_kph=3.0)
    results = [sim.step() for _ in range(6)]
    assert [r["input_validity"] for r in results[:5]] == ["VALID"] * 5
    assert results[5]["input_validity"] == "STALE"
    assert results[5]["state"] == "DEGRADED"
    assert results[5]["lock_left"] == "LOCK"


def test_it05_format_errors_are_judged_not_rejected(sim):
    sim.post(vehicle_speed_kph=999)
    assert sim.step()["input_validity"] == "INVALID"
    before = sim.client.get("/status").json()
    assert sim.client.post("/input", content=b"{bad").status_code == 422
    assert sim.client.get("/status").json() == before


def _vector():
    """@brief 결정론 시험용 120주기 입력 벡터 (주행·위험·충돌 포함)."""
    steps = []
    for i in range(120):
        signals = {"vehicle_speed_kph": float(i % 40)}
        if 30 <= i < 50:
            signals["rear_left_approach_risk"] = True
        if i == 80:
            signals["crash_status"] = "PENDING"
        if i == 90:
            signals["crash_status"] = "CONFIRMED"
        cmds = (
            [_cmd("all", "lock" if i % 7 else "unlock")] if i % 5 == 0 else []
        )
        steps.append((signals, cmds, i % 11 != 0))
    return steps


def _replay(vector):
    """@brief 새 runner로 벡터를 재생하고 결과 목록을 돌려준다."""
    clock = ScriptedClock(0.0)
    runner = Runner(clock, Controller())
    decisions = []
    for signals, cmds, send in vector:
        snap = raw_snapshot(source_timestamp_s=clock.now(), **signals)
        runner.submit(snap, cmds, has_snapshot=send)
        decisions.append(runner.tick())
        clock.advance(0.05)
    return decisions


def test_it06_replay_of_same_vector_is_deterministic():
    vector = _vector()
    hashes = {decision_hash(_replay(vector)) for _ in range(1000)}
    assert len(hashes) == 1


def test_it07_only_latest_hundred_events_over_http(sim):
    for i in range(150):
        action = "lock" if i % 2 else "unlock"
        sim.post(commands=[_cmd("left", action)])
        sim.step()
    events = sim.client.get("/events").json()
    assert [e["event_id"] for e in events] == list(range(51, 151))
    assert all(len(e) == 11 for e in events)


def test_it08_evaluation_time_budget():
    clock = ScriptedClock(0.0)
    runner = Runner(clock, Controller(EventLog()))
    worst = 0.0
    vector = _vector()
    for i in range(10_000):
        signals, cmds, send = vector[i % len(vector)]
        snap = raw_snapshot(source_timestamp_s=clock.now(), **signals)
        runner.submit(snap, cmds, has_snapshot=send)
        start = time.perf_counter()
        runner.tick()
        worst = max(worst, time.perf_counter() - start)
        clock.advance(0.05)
    assert worst <= 0.005


def test_it09_memory_is_bounded():
    clock = ScriptedClock(0.0)
    log = EventLog()
    runner = Runner(clock, Controller(log), log)

    def run(n):
        for i in range(n):
            snap = raw_snapshot(source_timestamp_s=clock.now())
            runner.submit(
                snap, [_cmd("left", "lock" if i % 2 else "unlock")], True
            )
            runner.tick()
            clock.advance(0.05)

    run(1_000)
    gc.collect()
    tracemalloc.start()
    before = tracemalloc.take_snapshot()
    run(10_000)
    gc.collect()
    after = tracemalloc.take_snapshot()
    tracemalloc.stop()
    growth = sum(s.size_diff for s in after.compare_to(before, "filename"))
    assert growth <= 1024 * 1024
    assert len(runner.events()) == 100


def test_it10_concurrent_http_while_periodic_thread_runs():
    log = EventLog()
    runner = Runner(MonotonicClock(), Controller(log), log, period_s=0.01)
    app = create_app(runner)
    codes = []
    lock = threading.Lock()

    def worker():
        with TestClient(app) as client:
            for _ in range(100):
                snap = raw_snapshot(source_timestamp_s=runner.now())
                r1 = client.post("/input", json={"snapshot": snap})
                r2 = client.get("/status")
                with lock:
                    codes.extend([r1.status_code, r2.status_code])

    runner.start()
    try:
        threads = [threading.Thread(target=worker) for _ in range(4)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
    finally:
        runner.stop()
    assert len(codes) == 800
    assert set(codes) <= {200, 202}
    assert runner.evaluation_errors == 0


def test_it11_qm_failure_is_isolated_over_http(sim, monkeypatch):
    def boom(values, commands):
        raise RuntimeError("qm failure")

    monkeypatch.setattr(controller_module.rules, "proposals", boom)
    sim.post(rear_left_approach_risk=True, vehicle_speed_kph=3.0)
    st = sim.step()
    assert (st["lock_left"], st["reason_left"]) == ("LOCK", "APPROACH_RISK")
    assert st["reason_right"] == "NO_CHANGE"
    sim.post(crash_status="CONFIRMED")
    assert sim.step()["reason_code"] == "CRASH_CONFIRMED"
