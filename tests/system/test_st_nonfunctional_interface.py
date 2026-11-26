"""@brief SWE.6 비기능 시험: JSON 구문 오류, 이벤트 보존, 결정론.

대상 요구사항: SWR-010, SWR-012, SWR-013, SWR-015, SWR-016.
근거: docs/swe6/system-test-cases.json
"""

import hashlib
import json
import os
import random
import tempfile
import time
from pathlib import Path

import pytest
from tests.system.harness import Bench, cmd
from tests.system.st_support import (
    STATUS_FIELDS,
    check,
    check_http,
    run,
    run_multi,
    run_no_snapshot,
)

import child_lock

## NTC-228~230: 깨진 JSON 본문
BROKEN_BODIES = [
    pytest.param(b'{"snapshot": {"vehicle_speed_kph": 3.0, ', id="NTC-228"),
    pytest.param(
        b'{"snapshot": {"vehicle_speed_kph": 3.0}, "commands": [],}',
        id="NTC-229",
    ),
    pytest.param(b"", id="NTC-230"),
]


@pytest.mark.parametrize("raw", BROKEN_BODIES)
def test_ntc_228_230_broken_json_422(bench, raw):
    """NTC-228 / NTC-229 / NTC-230 (SWR-015)

    JSON 구문 오류(잘린 JSON / 후행 쉼표 JSON / 빈 본문)가 HTTP 422로
    거절되고 시스템 상태·이벤트가 바뀌지 않는지 확인. 구문 오류를 200으로 받아
    빈 입력으로 평가하거나 500을 반환하는 결함 검출
    """
    # 1단계 t=10.00: 사전 설정 LOCK, GET /events 건수 기록(1건)
    st = run(bench, 10.00, vehicle_speed_kph=3.0)
    check(
        st,
        1,
        lock_left="LOCK",
        lock_right="LOCK",
        reason_code="AUTO_LOCK",
        priority_reason="auto_lock",
    )
    assert len(bench.events()) == 1
    # 2단계: 깨진 본문 제출, 그 뒤 GET /status와 GET /events 조회
    code = bench.send(raw_body=raw)
    check(
        bench.status(),
        2,
        lock_left="LOCK",
        lock_right="LOCK",
        reason_code="AUTO_LOCK",
        input_validity="VALID",
        state="NORMAL",
    )
    assert len(bench.events()) == 1, "2단계: 이벤트 건수 변화"
    check_http(code, 2, expected=422)


def test_ntc_231_non_object_snapshot_evaluated(bench):
    """NTC-231 (SWR-015, SWR-013)

    구문은 유효하나 snapshot이 문자열인 입력이 422가 아니라 202 +
    INVALID/DEGRADED(평가 경로)로 처리되는지 확인. 프레임워크 스키마 검증이
    422를 돌려주는 결함 검출 [제안 케이스]

    비고: 가정: 객체가 아닌 snapshot은 모든 필드 누락으로 보아 ASIL B 오류
    처리(질의 Q-09).
    """
    # 1단계 t=10.00: 사전 설정 LOCK
    st = run(bench, 10.00, vehicle_speed_kph=3.0)
    check(
        st,
        1,
        lock_left="LOCK",
        lock_right="LOCK",
        reason_code="AUTO_LOCK",
        priority_reason="auto_lock",
    )
    # 2단계 t=10.05: 유효한 JSON이지만 snapshot이 객체가 아님("abc")
    bench.at(10.05)
    code = bench.send_body({"snapshot": "abc", "commands": []})
    st = bench.evaluate()
    check(
        st,
        2,
        lock_left="LOCK",
        lock_right="LOCK",
        state="DEGRADED",
        reason_code="INPUT_INVALID",
        priority_reason="input_invalid",
        input_validity="INVALID",
    )
    assert code not in (400, 422, 500), f"2단계: HTTP {code}"
    check_http(code, 2)


def test_ntc_232_event_retention_100(bench):
    """NTC-232 (SWR-012, SWR-010)

    보존 한도 경계(99/100/101건)에서 최근 100건만 오래된 순으로 조회되는지
    확인. 한도 off-by-one(99건 또는 101건 보존), 최신 우선 정렬, 가장 새 항목을
    버리는 결함 검출

    0.05 s 간격 99회(10.00~14.90) 뒤 100번째는 14.95, 101번째는 15.00에
    실행한다 (명세의 시각 표기 오류는 SWE6 결과서 F-03으로 정정됨).
    """
    times = [round(10.00 + 0.05 * i, 2) for i in range(101)]
    # 1단계: 99회 평가(각 평가 S0 + 좌 lock 명령 → 항상 기록)
    for t in times[:99]:
        run(bench, t, [cmd("left", "lock")])
    ids = [e["event_id"] for e in bench.events()]
    assert ids == list(range(1, 100)), f"1단계: {len(ids)}건"
    # 2단계: 100번째 평가
    run(bench, times[99], [cmd("left", "lock")])
    ids = [e["event_id"] for e in bench.events()]
    assert ids == list(range(1, 101)), f"2단계: {len(ids)}건"
    # 3단계: 101번째 평가 → event_id=1 삭제, 2~101
    run(bench, times[100], [cmd("left", "lock")])
    ids = [e["event_id"] for e in bench.events()]
    assert ids == list(range(2, 102)), f"3단계: {ids[:2]}…{ids[-2:]}"


## NTC-233 파일 목록 비교에서 제외할 디렉터리(도구·캐시)
_SKIP_DIRS = {
    ".git",
    ".venv",
    "__pycache__",
    ".pytest_cache",
    ".ruff_cache",
    ".mypy_cache",
}
## 임시 폴더에서 영속 저장으로 볼 확장자
_STORE_SUFFIXES = {".db", ".json", ".log", ".sqlite", ".sqlite3"}


def _tree_files(root):
    """@brief root 아래 파일 경로 집합 (도구·캐시 디렉터리 제외)."""
    found = set()
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in _SKIP_DIRS]
        found.update(os.path.join(dirpath, f) for f in filenames)
    return found


def _file_listing():
    """@brief 작업 디렉터리·패키지 폴더·임시 폴더의 파일 목록."""
    pkg = Path(child_lock.__file__).parent
    tmp = Path(tempfile.gettempdir())
    tmp_store = {
        str(p)
        for p in tmp.iterdir()
        if p.is_file() and p.suffix.lower() in _STORE_SUFFIXES
    }
    return _tree_files(Path.cwd()) | _tree_files(pkg) | tmp_store


def test_ntc_233_events_not_persisted():
    """NTC-233 (SWR-012, SWR-010)

    프로세스 재시작 후 이벤트가 0건이고 event_id가 1부터 다시 시작하며
    파일·DB 저장이 없는지 확인. 이벤트 영속화와 event_id 이어쓰기 결함 검출

    프로세스 재기동은 새 Bench(새 시험 대상, 초기 상태)로 대신한다. 파일 비저장
    확인은 디렉터리 목록 비교로 한정한다(질의 Q-13).
    """
    before = _file_listing()
    first = Bench()
    try:
        # 1단계: t=10.00부터 0.05 s 간격 3회(S0 + 좌 lock)
        for t in (10.00, 10.05, 10.10):
            run(first, t, [cmd("left", "lock")])
        ids = [e["event_id"] for e in first.events()]
        assert ids == [1, 2, 3], f"1단계: {ids}"
    finally:
        first.close()
    # 2단계: 재기동 후 GET /events → 0건
    second = Bench()
    try:
        assert second.events() == [], "2단계: 이전 이벤트 복원됨"
        # 3단계 t=20.00: S0 제출 후 평가 1회
        run(second, 20.00)
        events = second.events()
        assert len(events) == 1, "3단계"
        assert events[0]["event_id"] == 1, "3단계"
        assert events[0]["timestamp_s"] == pytest.approx(20.00), "3단계"
    finally:
        second.close()
    # 4단계: 종료 후 파일 목록을 시험 전과 비교
    created = sorted(_file_listing() - before)
    assert not created, f"4단계: 새 파일 {created}"


## NTC-234 실제 대기를 넣는 회차 수. 기본은 1,000회 중 10회(전수 대기는
## 평균 약 18분이 걸린다). 환경 변수 ST_FULL_WALL_WAIT=1이면 1,000회 모두.
_WAIT_ROUNDS = 1000 if os.environ.get("ST_FULL_WALL_WAIT") == "1" else 10


def _replay_v16(bench, rng, wait):
    """@brief 입력 벡터 V16(12개 평가)을 재생하고 결과 목록을 돌려준다."""
    risk = {"rear_left_approach_risk": True}
    plays = [
        lambda: run(bench, 10.00),
        lambda: run(bench, 10.05, vehicle_speed_kph=3.0),
        lambda: run(bench, 10.10, [cmd("left", "unlock", "avn")], **risk),
        lambda: run(bench, 10.15, [cmd("left", "unlock", "voice")], **risk),
        lambda: run(bench, 10.20, sensor_fault=True),
        lambda: run(bench, 10.25, vehicle_speed_kph=300.1),
        lambda: run_no_snapshot(bench, 10.55),
        lambda: run(
            bench, 10.60, crash_status="PENDING", vehicle_speed_kph=3.0
        ),
        lambda: run_multi(bench, 10.65, {"crash_status": "CONFIRMED"}, {}),
        lambda: run(bench, 10.70, ignition_on=False),
        lambda: run(bench, 10.75, [cmd("all", "lock", "mobile_app")]),
        lambda: run(bench, 10.80, ignition_on=True),
    ]
    results = []
    for i, play in enumerate(plays):
        if wait and i:
            time.sleep(rng.uniform(0.0, 0.2))
        st = play()
        results.append({k: st[k] for k in STATUS_FIELDS})
    return results


def _public_hash(results):
    """@brief 결과 목록을 키 정렬 JSON으로 직렬화한 SHA-256."""
    text = json.dumps(results, sort_keys=True)
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _warm_up(rng):
    """@brief 다른 입력의 선행 시험 1회 (그 뒤 시험 대상은 폐기)."""
    other = Bench()
    try:
        run(other, rng.uniform(1.0, 5.0), [cmd("all", "lock", "voice")])
        run(other, 6.0, vehicle_speed_kph=3.0, rear_left_approach_risk=True)
    finally:
        other.close()


def test_ntc_234_deterministic_hash():
    """NTC-234 (SWR-016)

    같은 초기 상태·같은 입력 순서(시각 포함)를 1,000회 재생해 공개 결과 해시가
    모두 같은지 확인. 실제 시계·난수·전역 상태·dict/set 순서 의존 결함 검출

    매 회차 새 Bench(프로세스 신규 기동과 같은 초기 상태)로 재생하고, 회차의
    절반은 선행 시험을 먼저 수행한다. 평가 사이 무작위 실제 대기(0~200 ms)는
    실행 시간 때문에 기본 10회차에만 넣는다(_WAIT_ROUNDS 참고).
    해시 직렬화는 시험자 측 고정 알고리즘이다(질의 Q-12).
    """
    rng = random.Random()
    wait_every = 1000 // _WAIT_ROUNDS
    hashes = set()
    for k in range(1000):
        if k % 2:
            _warm_up(rng)
        bench = Bench()
        try:
            results = _replay_v16(bench, rng, wait=k % wait_every == 0)
        finally:
            bench.close()
        hashes.add(_public_hash(results))
    assert len(hashes) == 1, f"서로 다른 해시 {len(hashes)}개"
