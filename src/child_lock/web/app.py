"""@brief FastAPI 앱 (QM, SWE3-DD 6장, SWR-014, SWR-015).

판단 로직, 시각, 내부 상태를 갖지 않는다. runner의 공개 메서드만 호출하고,
JSON 구문 오류만 422로 거절한다. 필드 내용 검사는 평가 경로(SWR-013)가 한다.
"""

from __future__ import annotations

import json
from collections.abc import AsyncIterator, Callable
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Protocol

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse, Response
from starlette.concurrency import run_in_threadpool

from child_lock.runtime.runner import Runner
from child_lock.types import Decision, EventRecord

## 직렬화 중 잡는 예외 (결과 객체가 기대와 다를 때)
_SERIALIZE_ERRORS = (TypeError, ValueError, AttributeError)


class RunnerApi(Protocol):
    """@brief web이 쓰는 runner의 공개 메서드."""

    def submit(
        self, snapshot: object, commands: list[object], has_snapshot: bool
    ) -> None:
        """@brief 입력 전달."""
        ...

    def status(self) -> Decision:
        """@brief 마지막 결과."""
        ...

    def events(self) -> tuple[EventRecord, ...]:
        """@brief 제어결정 기록."""
        ...

    def now(self) -> float:
        """@brief 서버 시각."""
        ...


def _split_body(data: object) -> tuple[object, list[object], bool]:
    """@brief 요청 본문을 (스냅샷, 명령 목록, 스냅샷 여부)로 나눈다 (DD-15).

    객체에 `snapshot`이나 `commands` 키가 있으면 그 값을 쓰고, 없으면 본문
    전체를 스냅샷으로 본다. `snapshot: null`도 스냅샷으로 넘겨 형식 오류가
    되게 한다. `commands`가 null이면 빈 목록, 목록이 아니면 한 개짜리 목록.
    """
    if not (
        isinstance(data, dict) and ({"snapshot", "commands"} & data.keys())
    ):
        return data, [], True
    commands = data.get("commands")
    if commands is None:
        commands = []
    elif not isinstance(commands, list):
        commands = [commands]
    return data.get("snapshot"), commands, "snapshot" in data


def _json(build: Callable[[], object]) -> Response:
    """@brief 결과를 JSON으로 직렬화한다. 실패하면 HTTP 500 (SWR-015)."""
    try:
        text = json.dumps(build(), ensure_ascii=False, allow_nan=False)
    except _SERIALIZE_ERRORS:
        return JSONResponse({"detail": "serialization failed"}, status_code=500)
    return Response(text, media_type="application/json")


def _add_routes(app: FastAPI, runner: RunnerApi) -> None:
    """@brief 엔드포인트를 등록한다."""

    @app.post("/input", status_code=202)
    async def post_input(request: Request) -> Response:
        """@brief 시뮬레이터 입력. JSON 구문 오류만 422."""
        try:
            data = json.loads(await request.body())
        except (json.JSONDecodeError, UnicodeDecodeError):
            return JSONResponse({"detail": "invalid JSON"}, status_code=422)
        snapshot, commands, has_snapshot = _split_body(data)
        await run_in_threadpool(runner.submit, snapshot, commands, has_snapshot)
        return JSONResponse({"accepted": True}, status_code=202)

    @app.get("/status")
    async def get_status() -> Response:
        """@brief 마지막 평가 결과 (SWR-014의 9개 필드)."""
        decision = await run_in_threadpool(runner.status)
        return _json(lambda: decision.as_dict())

    @app.get("/events")
    async def get_events() -> Response:
        """@brief 최근 제어결정 기록 (SWR-011의 11개 필드)."""
        records = await run_in_threadpool(runner.events)
        return _json(lambda: [r.as_dict() for r in records])

    @app.get("/clock")
    async def get_clock() -> Response:
        """@brief 서버 시각 (시뮬레이터 타임스탬프 동기화용)."""
        now = await run_in_threadpool(runner.now)
        return _json(lambda: {"now_s": now})

    @app.get("/", response_class=HTMLResponse)
    async def index() -> HTMLResponse:
        """@brief 시뮬레이터 화면."""
        page = Path(__file__).parent / "static" / "index.html"
        return HTMLResponse(page.read_text(encoding="utf-8"))


def create_app(runner: RunnerApi | None = None) -> FastAPI:
    """@brief FastAPI 앱을 만든다.

    runner를 주지 않으면 실시간 시계로 기본 runner를 만들고, 앱 수명주기
    동안 50 ms 주기 스레드를 돌린다. runner를 주면(시험) 스레드를 돌리지 않는다.

    @param runner 사용할 runner (없으면 기본 구성)
    @return FastAPI 앱
    """
    owned: Runner | None = None
    if runner is None:
        owned = Runner.create_default()
        active: RunnerApi = owned
    else:
        active = runner

    @asynccontextmanager
    async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
        """@brief 기본 runner의 주기 스레드 시작·정지."""
        if owned is not None:
            owned.start()
        yield
        if owned is not None:
            owned.stop()

    app = FastAPI(title="전자식 차일드락 시뮬레이터", lifespan=lifespan)
    _add_routes(app, active)
    return app
