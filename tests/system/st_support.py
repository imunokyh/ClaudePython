"""@brief SWE.6 시험 케이스 공용 보조 함수.

시험 케이스의 한 단계(POST /input 제출 → 평가 1회 → GET /status 조회)를
하니스 공개 메서드만으로 재현하고, 기대값을 필드별로 비교한다.
표기는 시험 명세(system-test-cases.json)를 따른다.

- S0[필드=값]: run()의 키워드 인자로 S0의 필드를 덮어쓴다.
- ts=값: source_timestamp_s (생략하면 평가 시각 t).
- 필드 삭제: drop=("필드명",).
"""

from dataclasses import dataclass, field

## GET /status가 제공해야 하는 아홉 필드 (SWR-014)
STATUS_FIELDS = (
    "lock_left",
    "lock_right",
    "state",
    "priority_reason",
    "reason_code",
    "input_validity",
    "reason_left",
    "reason_right",
    "warning_code",
)

## GET /events 이벤트가 가져야 하는 열한 키 (SWR-011)
EVENT_KEYS = frozenset(("event_id", "timestamp_s", *STATUS_FIELDS))


def snapshot(bench, ts=None, drop=(), **signals):
    """@brief S0[signals] 스냅샷. drop에 든 필드는 뺀다(필드 누락)."""
    snap = bench.signals(ts=ts, **signals)
    for name in drop:
        del snap[name]
    return snap


def run_code(bench, t, commands=None, ts=None, drop=(), **signals):
    """@brief 시각 t에 S0[signals]와 명령을 제출하고 평가 1회.

    @return (POST /input HTTP 상태 코드, GET /status 결과)
    """
    bench.at(t)
    code = bench.send(snapshot(bench, ts, drop, **signals), commands or [])
    return code, bench.evaluate()


def run(bench, t, commands=None, ts=None, drop=(), **signals):
    """@brief run_code()와 같고 GET /status 결과만 돌려준다."""
    return run_code(bench, t, commands, ts, drop, **signals)[1]


def run_no_snapshot(bench, t, commands=None):
    """@brief 시각 t에 스냅샷 없이 명령만 제출하고 평가 1회."""
    bench.at(t)
    bench.send(None, commands or [])
    return bench.evaluate()


def run_multi(bench, t, *snapshots, commands=None):
    """@brief 한 주기에 스냅샷 여러 개를 차례로 POST 한 뒤 평가 1회.

    snapshots의 각 항목은 S0 덮어쓰기 dict다(키 "ts"는 타임스탬프).
    명령은 마지막 POST에만 싣는다(명세: commands=[]).
    """
    bench.at(t)
    last = len(snapshots) - 1
    for i, over in enumerate(snapshots):
        over = dict(over)
        ts = over.pop("ts", None)
        cmds = (commands or []) if i == last else []
        bench.send(snapshot(bench, ts, **over), cmds)
    return bench.evaluate()


def check(status, step, **expected):
    """@brief status에서 expected의 필드만 골라 기대값과 비교한다."""
    actual = {k: status.get(k, "<없음>") for k in expected}
    assert actual == expected, f"{step}단계: 기대 {expected} / 실제 {actual}"


def check_http(code, step, expected=202):
    """@brief POST /input 응답 HTTP 상태 코드를 비교한다."""
    assert code == expected, f"{step}단계: HTTP 기대 {expected} / 실제 {code}"


@dataclass(frozen=True)
class Step:
    """@brief 표 형태 케이스(결정표, PICT)의 한 단계."""

    t: float
    sig: dict = field(default_factory=dict)
    cmds: list = field(default_factory=list)
    expect: dict = field(default_factory=dict)
    ts: float | None = None


def play(bench, steps):
    """@brief Step 목록을 차례로 실행하고 단계마다 기대값을 확인한다."""
    for n, s in enumerate(steps, 1):
        st = run(bench, s.t, s.cmds, ts=s.ts, **s.sig)
        check(st, n, **s.expect)
