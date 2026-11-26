"""@brief SWE.6 기능 시험: HTTP 인터페이스·상태 조회·이벤트 기록.

대상 요구사항: SWR-010, SWR-011, SWR-013, SWR-014, SWR-015.
근거: docs/swe6/system-test-cases.json
"""

import json

import pytest
from tests.system.harness import cmd
from tests.system.st_support import (
    EVENT_KEYS,
    STATUS_FIELDS,
    check,
    check_http,
    run,
    run_code,
    run_no_snapshot,
)


def _times(start, count):
    """@brief start부터 0.05초 간격 평가 시각 count개 (소수 둘째 자리)."""
    return [round(start + 0.05 * i, 2) for i in range(count)]


def _check_last_event(events, step, count, **expected):
    """@brief 이벤트 건수와 마지막 이벤트의 필드를 확인한다."""
    assert len(events) == count, f"{step}단계: 이벤트 {len(events)}건"
    last = events[-1]
    ts = expected.pop("timestamp_s", None)
    if ts is not None:
        assert last["timestamp_s"] == pytest.approx(ts), f"{step}단계"
    check(last, step, **expected)


def test_ftc_154_http_status_and_out_of_range(bench):
    """FTC-154 (SWR-015, SWR-013)

    GET /status가 200과 SWR-014 JSON을 반환하고, 범위 밖 값은 HTTP 오류가
    아니라 202 + DEGRADED/INVALID로 처리되는지 확인. 스키마 검증 프레임워크가
    범위 오류를 422로 돌려보내는 결함 검출
    """
    # 1단계 t=10.00: 정상 입력
    code1, st1 = run_code(bench, 10.00, vehicle_speed_kph=3.0)
    check(
        st1,
        1,
        lock_left="LOCK",
        lock_right="LOCK",
        reason_code="AUTO_LOCK",
        priority_reason="auto_lock",
    )
    # 2단계: GET /status 호출 → 200, 아홉 필드 포함, 값은 1단계 결과와 동일
    assert bench.status_code("/status") == 200
    body = bench.status()
    missing = [k for k in STATUS_FIELDS if k not in body]
    assert not missing, f"2단계: 누락 필드 {missing}"
    assert {k: body[k] for k in STATUS_FIELDS} == {
        k: st1[k] for k in STATUS_FIELDS
    }
    # 3단계 t=10.05: 범위 밖 값(300.1 km/h)은 입력 계층에서 거절하지 않고
    # 평가 경로로 전달
    code3, st = run_code(bench, 10.05, vehicle_speed_kph=300.1)
    check(
        st,
        3,
        lock_left="LOCK",
        lock_right="LOCK",
        state="DEGRADED",
        reason_code="INPUT_INVALID",
        priority_reason="input_invalid",
        input_validity="INVALID",
    )
    # HTTP 응답 코드는 출력 판정을 모두 본 뒤 확인한다
    check_http(code1, 1)
    check_http(code3, 3)


def test_ftc_155_event_recording_rules(bench):
    """FTC-155 (SWR-010)

    동일 결과가 이어지는 평가는 1건만 기록되고(10회→1건), 운전자 명령 평가는
    결과가 같아도 기록되며, event_id가 1,2,3,…으로 증가하는지 확인. 매 평가
    기록·명령 평가 누락·ID 건너뜀 결함 검출
    """
    # 1단계: t=10.00~10.45 (10회) S0, 명령 없음 → 첫 평가 1건만 기록
    for t in _times(10.00, 10):
        run(bench, t)
    events = bench.events()
    _check_last_event(events, 1, 1, event_id=1, timestamp_s=10.00)
    # 2단계 t=10.50: 운전자 명령 평가(결과 변화)
    run(bench, 10.50, [cmd("left", "lock")])
    _check_last_event(
        bench.events(), 2, 2, event_id=2, timestamp_s=10.50, lock_left="LOCK"
    )
    # 3단계 t=10.55: 직전과 같은 명령(결과 동일)이지만 명령 평가이므로 기록
    run(bench, 10.55, [cmd("left", "lock")])
    _check_last_event(
        bench.events(),
        3,
        3,
        event_id=3,
        timestamp_s=10.55,
        lock_left="LOCK",
        reason_left="DRIVER_COMMAND",
    )
    # 4단계 t=10.60: 명령 없음, reason_left가 DRIVER_COMMAND→NO_CHANGE
    run(bench, 10.60)
    _check_last_event(
        bench.events(),
        4,
        4,
        event_id=4,
        timestamp_s=10.60,
        reason_left="NO_CHANGE",
    )
    # 5단계: t=10.65~11.10 (10회) 결과 동일 → 기록 없음
    for t in _times(10.65, 10):
        run(bench, t)
    ids = [e["event_id"] for e in bench.events()]
    assert ids == [1, 2, 3, 4], f"5단계: event_id {ids}"


def test_ftc_156_event_on_non_lock_field_change(bench):
    """FTC-156 (SWR-010)

    잠금 출력이 같아도 공개 결과의 다른 필드(input_validity, state, reason_*)가
    바뀌면 기록되고, 같은 결과는 기록되지 않는지 확인. 'lock 출력 변화만 기록'
    결함 검출
    """
    # 1단계 t=10.00
    run(bench, 10.00)
    _check_last_event(bench.events(), 1, 1, event_id=1)
    # 2단계 t=10.05: 스냅샷 없는 주기, 결과 동일(VALID, 나이 0.05 s)
    run_no_snapshot(bench, 10.05)
    assert len(bench.events()) == 1, "2단계"
    # 3단계 t=10.30: 기준 스냅샷 나이 0.30 s → STALE/DEGRADED로 변해 기록
    run_no_snapshot(bench, 10.30)
    _check_last_event(
        bench.events(),
        3,
        2,
        event_id=2,
        timestamp_s=10.30,
        input_validity="STALE",
        state="DEGRADED",
    )
    # 4단계 t=10.35: STALE 지속, 결과 동일 → 기록 없음
    run_no_snapshot(bench, 10.35)
    assert len(bench.events()) == 2, "4단계"
    # 5단계 t=10.40: 정상 스냅샷 복귀 → VALID/NORMAL로 기록
    run(bench, 10.40)
    _check_last_event(
        bench.events(),
        5,
        3,
        event_id=3,
        input_validity="VALID",
        state="NORMAL",
    )
    # 6단계 t=10.45: 자동 잠금
    run(bench, 10.45, vehicle_speed_kph=3.0)
    _check_last_event(
        bench.events(),
        6,
        4,
        event_id=4,
        lock_left="LOCK",
        lock_right="LOCK",
        reason_code="AUTO_LOCK",
    )
    # 7단계 t=10.50: 잠금 출력은 같고 이유만 변경
    run(bench, 10.50, vehicle_speed_kph=3.0, rear_left_approach_risk=True)
    _check_last_event(
        bench.events(),
        7,
        5,
        event_id=5,
        lock_left="LOCK",
        lock_right="LOCK",
        reason_left="APPROACH_RISK",
        reason_code="APPROACH_RISK",
    )
    # 8단계 t=10.55: 동일 결과 반복 → 기록 없음
    run(bench, 10.55, vehicle_speed_kph=3.0, rear_left_approach_risk=True)
    ids = [e["event_id"] for e in bench.events()]
    assert ids == [1, 2, 3, 4, 5], f"8단계: event_id {ids}"


def test_ftc_157_event_has_only_eleven_keys(bench):
    """FTC-157 (SWR-011)

    이벤트가 11개 키만 가지며 원시 입력값(차속, gear 오류값, 명령
    source/side/action, 입력 타임스탬프)을 저장하지 않는지 확인. 디버깅용 원시
    입력 필드가 이벤트에 섞이는 결함 검출
    """
    # 1단계 t=10.00: QM 오류값(gear="Z9")과 명령(source=voice)을 포함한 첫 평가
    run(
        bench,
        10.00,
        [cmd("left", "lock", "voice")],
        vehicle_speed_kph=123.4,
        gear="Z9",
        rear_left_approach_risk=True,
    )
    events = bench.events()
    assert len(events) == 1, "1단계"
    assert set(events[0]) == EVENT_KEYS, f"1단계: 키 {sorted(events[0])}"
    _check_last_event(
        events,
        1,
        1,
        lock_left="LOCK",
        lock_right="RELEASE",
        state="DEGRADED",
        reason_code="APPROACH_RISK",
        priority_reason="approach_risk",
        reason_left="APPROACH_RISK",
        reason_right="INPUT_INVALID",
        input_validity="INVALID",
        timestamp_s=10.00,
    )
    # 2단계 t=10.05: 스냅샷 없음. 모든 이벤트의 키 집합은 11개로 동일
    run_no_snapshot(bench, 10.05)
    events = bench.events()
    for e in events:
        assert set(e) == EVENT_KEYS, f"2단계: 키 {sorted(e)}"
    # 3단계: GET /events 응답 본문 전체를 문자열로 검색
    text = json.dumps(events, ensure_ascii=False)
    for word in (
        "Z9",
        "123.4",
        "voice",
        "source_timestamp_s",
        "vehicle_speed_kph",
        "gear",
        "side",
        "action",
    ):
        assert word not in text, f"3단계: 이벤트에 '{word}' 포함"
