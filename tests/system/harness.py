"""@brief SW 검증(SWE.6) PC/SIL 시험 하니스.

시험 대상 전체(web → runner → controller → safety/qm)를 HTTP API로 구동하고,
평가 시각은 시험용 시계(ScriptedClock)로 지정한다. 시험 케이스는 이 하니스의
공개 메서드만 쓴다.
"""

from fastapi.testclient import TestClient

from child_lock.controller import Controller
from child_lock.qm.event_log import EventLog
from child_lock.runtime.clock import ScriptedClock
from child_lock.runtime.runner import Runner
from child_lock.web.app import create_app

## 정상 스냅샷 기본값 (정차, 시동 ON, 위험·강제 신호 없음)
BASE_SIGNALS = (
    ("vehicle_speed_kph", 0.0),
    ("gear", "P"),
    ("crash_status", "NONE"),
    ("rear_left_approach_risk", False),
    ("rear_right_approach_risk", False),
    ("fire_detected", False),
    ("overtemperature_detected", False),
    ("adult_present", False),
    ("isofix_left", False),
    ("isofix_right", False),
    ("ignition_on", True),
    ("sensor_fault", False),
)


class Bench:
    """@brief PC/SIL 시험대: HTTP 입력, 평가 시각 지정, 평가 1회 실행."""

    def __init__(self, start_s=0.0):
        """@brief 새 시험 대상과 시험용 시계를 만든다 (초기 상태)."""
        self.clock = ScriptedClock(start_s)
        self.log = EventLog()
        self.runner = Runner(self.clock, Controller(self.log), self.log)
        self._client = TestClient(create_app(self.runner))

    def close(self):
        """@brief HTTP 클라이언트를 닫는다."""
        self._client.close()

    def signals(self, ts=None, **overrides):
        """@brief 기본값에 덮어쓴 스냅샷. ts가 없으면 현재 평가 시각."""
        data = dict(BASE_SIGNALS)
        data["source_timestamp_s"] = self.clock.now() if ts is None else ts
        data.update(overrides)
        return data

    def send(self, snapshot=None, commands=None, raw_body=None):
        """@brief POST /input. raw_body를 주면 그 바이트를 그대로 보낸다.

        @return HTTP 상태 코드
        """
        if raw_body is not None:
            return self._client.post("/input", content=raw_body).status_code
        body = {"commands": commands or []}
        if snapshot is not None:
            body["snapshot"] = snapshot
        return self._client.post("/input", json=body).status_code

    def send_body(self, body):
        """@brief 임의의 JSON 본문으로 POST /input."""
        return self._client.post("/input", json=body).status_code

    def at(self, t):
        """@brief 평가 시각을 t초로 지정한다."""
        self.clock.set(t)

    def evaluate(self):
        """@brief 평가 1회를 실행하고 GET /status 결과를 돌려준다."""
        self.runner.tick()
        return self.status()

    def step(self, t, commands=None, send_snapshot=True, **signals):
        """@brief 시각 t에 (스냅샷과) 명령을 보내고 평가 1회."""
        self.at(t)
        snap = self.signals(**signals) if send_snapshot else None
        self.send(snap, commands)
        return self.evaluate()

    def status(self):
        """@brief GET /status (SWR-014 9개 필드)."""
        return self._client.get("/status").json()

    def status_code(self, path):
        """@brief GET 요청의 HTTP 상태 코드."""
        return self._client.get(path).status_code

    def events(self):
        """@brief GET /events (SWR-011 11개 필드)."""
        return self._client.get("/events").json()

    def server_clock(self):
        """@brief GET /clock."""
        return self._client.get("/clock").json()


def cmd(side="left", action="unlock", source="physical_button"):
    """@brief 운전자 명령 하나."""
    return {"side": side, "action": action, "source": source}
