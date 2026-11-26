"""@brief web.app 단위 테스트 (SWR-014, SWR-015)."""

import runpy

import pytest
from fastapi.testclient import TestClient
from tests.helpers import raw_snapshot

from child_lock.controller import Controller
from child_lock.qm.event_log import EventLog
from child_lock.runtime.clock import ScriptedClock
from child_lock.runtime.runner import Runner
from child_lock.web.app import create_app

STATUS_KEYS = {
    "lock_left",
    "lock_right",
    "state",
    "priority_reason",
    "reason_code",
    "input_validity",
    "reason_left",
    "reason_right",
    "warning_code",
}


@pytest.fixture
def env():
    """@brief 시험용 시계·runner·클라이언트 (tick은 직접 호출)."""
    clock = ScriptedClock(10.0)
    log = EventLog()
    runner = Runner(clock, Controller(log), log)
    with TestClient(create_app(runner)) as client:
        yield clock, runner, client


def test_status_returns_nine_fields_of_last_decision(env):
    _, runner, client = env
    runner.submit(raw_snapshot(vehicle_speed_kph=3.0), [], True)
    runner.tick()
    res = client.get("/status")
    assert res.status_code == 200
    body = res.json()
    assert set(body) == STATUS_KEYS
    assert body["reason_code"] == "AUTO_LOCK"
    assert body["lock_left"] == "LOCK"


def test_input_with_snapshot_and_commands_is_submitted(env):
    _, runner, client = env
    res = client.post(
        "/input",
        json={
            "snapshot": raw_snapshot(),
            "commands": [{"side": "left", "action": "lock", "source": "avn"}],
        },
    )
    assert res.status_code == 202
    d = runner.tick()
    assert d.lock_left.value == "LOCK"


def test_out_of_range_value_is_accepted_and_judged_invalid(env):
    _, runner, client = env
    res = client.post(
        "/input", json={"snapshot": raw_snapshot(vehicle_speed_kph=999)}
    )
    assert res.status_code == 202
    assert runner.tick().input_validity.value == "INVALID"


def test_null_snapshot_is_judged_invalid_not_missing(env):
    _, runner, client = env
    client.post("/input", json={"snapshot": None})
    assert runner.tick().input_validity.value == "INVALID"


def test_bare_snapshot_body_is_used_as_snapshot(env):
    _, runner, client = env
    client.post("/input", json=raw_snapshot(vehicle_speed_kph=3.0))
    assert runner.tick().reason_code.value == "AUTO_LOCK"


def test_commands_only_body_keeps_no_snapshot(env):
    clock, runner, client = env
    client.post("/input", json={"snapshot": raw_snapshot()})
    runner.tick()
    clock.advance(0.05)
    client.post("/input", json={"commands": None})
    assert runner.tick().input_validity.value == "VALID"


def test_single_command_object_is_wrapped(env):
    _, runner, client = env
    client.post(
        "/input",
        json={
            "snapshot": raw_snapshot(),
            "commands": {"side": "all", "action": "lock", "source": "voice"},
        },
    )
    d = runner.tick()
    assert (d.lock_left.value, d.lock_right.value) == ("LOCK", "LOCK")


@pytest.mark.parametrize("body", [b"{broken", b"\xff\xfe", b""])
def test_json_syntax_error_returns_422(env, body):
    _, runner, client = env
    res = client.post("/input", content=body)
    assert res.status_code == 422
    runner.tick()
    assert runner.events()[-1].decision.input_validity.value == "STALE"


def test_events_returns_eleven_field_records(env):
    _, runner, client = env
    runner.submit(raw_snapshot(), [], True)
    runner.tick()
    res = client.get("/events")
    assert res.status_code == 200
    (event,) = res.json()
    assert len(event) == 11
    assert event["event_id"] == 1


def test_clock_returns_server_time(env):
    clock, _, client = env
    assert client.get("/clock").json() == {"now_s": 10.0}


def test_serialization_failure_returns_500():
    class BadRunner:
        def status(self):
            return object()

        def events(self):
            return (object(),)

        def now(self):
            return float("nan")

    with TestClient(create_app(BadRunner())) as client:
        assert client.get("/status").status_code == 500
        assert client.get("/events").status_code == 500
        assert client.get("/clock").status_code == 500


def test_index_serves_simulator_page(env):
    _, _, client = env
    res = client.get("/")
    assert res.status_code == 200
    assert "차일드락" in res.text


def test_default_app_runs_periodic_loop():
    with TestClient(create_app()) as client:
        client.post("/input", json={"snapshot": None})
        assert client.get("/status").status_code == 200


def test_main_module_starts_uvicorn(monkeypatch):
    calls = []
    monkeypatch.setattr("uvicorn.run", lambda app, **kw: calls.append(kw))
    runpy.run_module("child_lock.web", run_name="__main__")
    assert calls == [{"host": "127.0.0.1", "port": 8000}]
