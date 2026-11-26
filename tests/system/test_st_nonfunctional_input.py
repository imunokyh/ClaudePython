"""@brief SWE.6 비기능 시험: 입력 유효성·지연·명령 오류 (SWR-013).

근거: docs/swe6/system-test-cases.json
"""

from tests.system.harness import cmd
from tests.system.st_support import (
    check,
    check_http,
    run,
    run_code,
    run_no_snapshot,
)


def test_ntc_201_speed_range_bounds_valid(bench):
    """NTC-201 (SWR-013, SWR-003)

    차속 범위 경계 내부(0.0, 300.0 km/h)가 유효로 처리되고 300.0 km/h에서 자동
    잠금이 되는지 확인. 범위 경계를 포함하지 않는(< 300.0) 결함 검출
    """
    # 1단계 t=10.00: vehicle_speed_kph=0.0(하한 경계)도 유효
    st = run(bench, 10.00)
    check(
        st,
        1,
        lock_left="RELEASE",
        lock_right="RELEASE",
        state="NORMAL",
        reason_code="NO_CHANGE",
        priority_reason="no_change",
        input_validity="VALID",
    )
    # 2단계 t=10.05: 상한 경계 300.0 km/h
    code2, st = run_code(bench, 10.05, vehicle_speed_kph=300.0)
    check(
        st,
        2,
        lock_left="LOCK",
        lock_right="LOCK",
        state="NORMAL",
        reason_code="AUTO_LOCK",
        priority_reason="auto_lock",
        input_validity="VALID",
        warning_code="NONE",
    )
    # HTTP 응답 코드는 출력 판정을 모두 본 뒤 확인한다
    check_http(code2, 2)


def test_ntc_202_speed_above_max_invalid_and_recovers(bench):
    """NTC-202 (SWR-013)

    300.1 km/h는 INVALID(직전 유지, DEGRADED)이고 다음 유효 스냅샷에서 디바운스
    없이 즉시 정상 복귀하는지 확인(수용기준·④). 상한 미검사와 복귀 지연 결함
    검출
    """
    # 1단계 t=10.00: 사전 설정
    st = run(bench, 10.00)
    check(
        st,
        1,
        lock_left="RELEASE",
        lock_right="RELEASE",
        reason_code="NO_CHANGE",
        priority_reason="no_change",
    )
    # 2단계 t=10.05: 상한 초과 300.1 km/h(분해능 0.1 가정 +1)
    code2, st = run_code(bench, 10.05, vehicle_speed_kph=300.1)
    check(
        st,
        2,
        lock_left="RELEASE",
        lock_right="RELEASE",
        state="DEGRADED",
        reason_code="INPUT_INVALID",
        priority_reason="input_invalid",
        reason_left="INPUT_INVALID",
        reason_right="INPUT_INVALID",
        input_validity="INVALID",
    )
    # 3단계 t=10.10: 다음 유효·최신 스냅샷: 지연 없이 정상 판정 복귀
    st = run(bench, 10.10, vehicle_speed_kph=3.0)
    check(
        st,
        3,
        lock_left="LOCK",
        lock_right="LOCK",
        state="NORMAL",
        reason_code="AUTO_LOCK",
        priority_reason="auto_lock",
        input_validity="VALID",
    )
    # HTTP 응답 코드는 출력 판정을 모두 본 뒤 확인한다
    check_http(code2, 2)


def test_ntc_203_speed_below_min_invalid(bench):
    """NTC-203 (SWR-013)

    차속 −0.1 km/h(하한 0.0 바로 아래)가 INVALID로 처리되는지 확인. 하한 미검사
    결함 검출
    """
    # 1단계 t=10.00: 사전 설정: LOCK
    st = run(bench, 10.00, vehicle_speed_kph=3.0)
    check(
        st,
        1,
        lock_left="LOCK",
        lock_right="LOCK",
        reason_code="AUTO_LOCK",
        priority_reason="auto_lock",
    )
    # 2단계 t=10.05: 하한 미만 −0.1 km/h
    code2, st = run_code(bench, 10.05, vehicle_speed_kph=-0.1)
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
    # HTTP 응답 코드는 출력 판정을 모두 본 뒤 확인한다
    check_http(code2, 2)


def test_ntc_204_numeric_string_invalid(bench):
    """NTC-204 (SWR-013, SWR-015)

    숫자 자리에 문자열 "3.0"이 오면 형식 오류(INVALID)이며 자동 변환으로 3.0
    km/h(LOCK)가 되지 않는지 확인. 암묵적 형변환 결함 검출
    """
    # 1단계 t=10.00: 사전 설정
    st = run(bench, 10.00)
    check(
        st,
        1,
        lock_left="RELEASE",
        lock_right="RELEASE",
        reason_code="NO_CHANGE",
        priority_reason="no_change",
    )
    # 2단계 t=10.05: 숫자처럼 보이는 문자열 "3.0"
    code2, st = run_code(bench, 10.05, vehicle_speed_kph="3.0")
    check(
        st,
        2,
        lock_left="RELEASE",
        lock_right="RELEASE",
        state="DEGRADED",
        reason_code="INPUT_INVALID",
        priority_reason="input_invalid",
        input_validity="INVALID",
    )
    # HTTP 응답 코드는 출력 판정을 모두 본 뒤 확인한다
    check_http(code2, 2)


def test_ntc_205_unknown_crash_enum_invalid(bench):
    """NTC-205 (SWR-013)

    crash_status="UNKNOWN"(미등록 enum)이 INVALID/DEGRADED로 처리되는지 확인.
    미등록 값을 NONE으로 간주하는 결함 검출
    """
    # 1단계 t=10.00: 사전 설정: LOCK
    st = run(bench, 10.00, vehicle_speed_kph=3.0)
    check(
        st,
        1,
        lock_left="LOCK",
        lock_right="LOCK",
        reason_code="AUTO_LOCK",
        priority_reason="auto_lock",
    )
    # 2단계 t=10.05: 미등록 enum "UNKNOWN"
    code2, st = run_code(bench, 10.05, crash_status="UNKNOWN")
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
    # HTTP 응답 코드는 출력 판정을 모두 본 뒤 확인한다
    check_http(code2, 2)


def test_ntc_206_bool_zero_invalid(bench):
    """NTC-206 (SWR-013, SWR-020)

    불리언 자리의 0은 형식 오류이며 false로 해석되어 시동 OFF(RELEASE)가 되지
    않는지 확인. 0/1 암묵 변환 결함 검출
    """
    # 1단계 t=10.00: 사전 설정: LOCK
    st = run(bench, 10.00, vehicle_speed_kph=3.0)
    check(
        st,
        1,
        lock_left="LOCK",
        lock_right="LOCK",
        reason_code="AUTO_LOCK",
        priority_reason="auto_lock",
    )
    # 2단계 t=10.05: ASIL B 불리언 자리에 0(시동 OFF로 오인하면 RELEASE가 됨)
    code2, st = run_code(bench, 10.05, ignition_on=0)
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
    # HTTP 응답 코드는 출력 판정을 모두 본 뒤 확인한다
    check_http(code2, 2)


def test_ntc_207_bool_one_invalid(bench):
    """NTC-207 (SWR-013, SWR-005)

    접근위험 불리언 자리의 1이 형식 오류로 처리되어 LOCK(APPROACH_RISK)이
    만들어지지 않는지 확인(수용기준 '불리언 자리의 1'). 0/1을 true/false로
    받아들이는 결함 검출
    """
    # 1단계 t=10.00: 사전 설정
    st = run(bench, 10.00)
    check(
        st,
        1,
        lock_left="RELEASE",
        lock_right="RELEASE",
        reason_code="NO_CHANGE",
        priority_reason="no_change",
    )
    # 2단계 t=10.05: 접근위험 자리에 1(true로 오인하면 LOCK이 됨)
    code2, st = run_code(bench, 10.05, rear_left_approach_risk=1)
    check(
        st,
        2,
        lock_left="RELEASE",
        lock_right="RELEASE",
        state="DEGRADED",
        reason_code="INPUT_INVALID",
        priority_reason="input_invalid",
        input_validity="INVALID",
    )
    # HTTP 응답 코드는 출력 판정을 모두 본 뒤 확인한다
    check_http(code2, 2)


def test_ntc_208_missing_asil_b_field_invalid(bench):
    """NTC-208 (SWR-013)

    ASIL B 필드(crash_status) 누락이 INVALID(직전 유지)로 처리되고 기본값(NONE)
    대체로 자동 잠금되지 않는지 확인. 누락 필드 기본값 대체 결함 검출
    """
    # 1단계 t=10.00: 사전 설정
    st = run(bench, 10.00)
    check(
        st,
        1,
        lock_left="RELEASE",
        lock_right="RELEASE",
        reason_code="NO_CHANGE",
        priority_reason="no_change",
    )
    # 2단계 t=10.05: ASIL B 필드(crash_status) 누락 + 3.0 km/h
    code2, st = run_code(
        bench, 10.05, drop=("crash_status",), vehicle_speed_kph=3.0
    )
    check(
        st,
        2,
        lock_left="RELEASE",
        lock_right="RELEASE",
        state="DEGRADED",
        reason_code="INPUT_INVALID",
        priority_reason="input_invalid",
        input_validity="INVALID",
    )
    # HTTP 응답 코드는 출력 판정을 모두 본 뒤 확인한다
    check_http(code2, 2)


def test_ntc_209_missing_qm_field_invalid(bench):
    """NTC-209 (SWR-013)

    QM 필드 누락이 순위 5(INPUT_INVALID, 직전 유지)로 처리되어 자동 잠금이
    막히는지 확인. QM 누락을 false 기본값으로 처리하는 결함 검출
    """
    # 1단계 t=10.00: 사전 설정
    st = run(bench, 10.00)
    check(
        st,
        1,
        lock_left="RELEASE",
        lock_right="RELEASE",
        reason_code="NO_CHANGE",
        priority_reason="no_change",
    )
    # 2단계 t=10.05: QM 필드(fire_detected) 누락 + 3.0 km/h
    code2, st = run_code(
        bench, 10.05, drop=("fire_detected",), vehicle_speed_kph=3.0
    )
    check(
        st,
        2,
        lock_left="RELEASE",
        lock_right="RELEASE",
        state="DEGRADED",
        reason_code="INPUT_INVALID",
        priority_reason="input_invalid",
        reason_left="INPUT_INVALID",
        reason_right="INPUT_INVALID",
        input_validity="INVALID",
    )
    # HTTP 응답 코드는 출력 판정을 모두 본 뒤 확인한다
    check_http(code2, 2)


def test_ntc_210_missing_timestamp_invalid(bench):
    """NTC-210 (SWR-013)

    source_timestamp_s 누락이 INVALID로 처리되는지 확인(타임스탬프도 ASIL B
    신호). 누락 시 평가 시각으로 대체하는 결함 검출
    """
    # 1단계 t=10.00: 사전 설정
    st = run(bench, 10.00)
    check(
        st,
        1,
        lock_left="RELEASE",
        lock_right="RELEASE",
        reason_code="NO_CHANGE",
        priority_reason="no_change",
    )
    # 2단계 t=10.05: source_timestamp_s 누락 + 3.0 km/h
    code2, st = run_code(
        bench, 10.05, drop=("source_timestamp_s",), vehicle_speed_kph=3.0
    )
    check(
        st,
        2,
        lock_left="RELEASE",
        lock_right="RELEASE",
        state="DEGRADED",
        reason_code="INPUT_INVALID",
        priority_reason="input_invalid",
        input_validity="INVALID",
    )
    # HTTP 응답 코드는 출력 판정을 모두 본 뒤 확인한다
    check_http(code2, 2)


def test_ntc_211_bool_string_invalid(bench):
    """NTC-211 (SWR-013, SWR-018)

    QM 불리언 자리의 문자열 "true"가 형식 오류(INVALID, 직전 유지)이며 true로
    해석되어 ISOFIX LOCK이 되지 않는지 확인. 문자열 불리언 허용 결함 검출
    """
    # 1단계 t=10.00: 사전 설정
    st = run(bench, 10.00)
    check(
        st,
        1,
        lock_left="RELEASE",
        lock_right="RELEASE",
        reason_code="NO_CHANGE",
        priority_reason="no_change",
    )
    # 2단계 t=10.05: QM 불리언 자리에 문자열 "true"
    code2, st = run_code(bench, 10.05, isofix_left="true")
    check(
        st,
        2,
        lock_left="RELEASE",
        lock_right="RELEASE",
        state="DEGRADED",
        reason_code="INPUT_INVALID",
        priority_reason="input_invalid",
        input_validity="INVALID",
    )
    # HTTP 응답 코드는 출력 판정을 모두 본 뒤 확인한다
    check_http(code2, 2)


def test_ntc_212_empty_snapshot_invalid(bench):
    """NTC-212 (SWR-013, SWR-015)

    빈 스냅샷 {}이 HTTP 오류 없이 INVALID/DEGRADED로 처리되는지 확인. 전 필드
    누락 시 예외·500·정상 판정 결함 검출
    """
    # 1단계 t=10.00: 사전 설정 LOCK
    st = run(bench, 10.00, [cmd("all", "lock")])
    check(
        st,
        1,
        lock_left="LOCK",
        lock_right="LOCK",
        reason_code="DRIVER_COMMAND",
        priority_reason="driver_command",
    )
    # 2단계 t=10.05: 빈 스냅샷 {}(전 필드 누락) + lock all
    bench.at(10.05)
    code = bench.send({}, [cmd("all", "lock")])
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
    check_http(code, 2)


def test_ntc_213_ts_50ms_future_valid(bench):
    """NTC-213 (SWR-013)

    미래 0.050 s 타임스탬프가 정상으로 처리되는지 확인(허용 경계, ≤).
    10.05−10.00=0.0500000000000007로 계산되는 부동소수 오차로 정상 입력을 오류
    처리하는 결함 검출
    """
    # 1단계 t=9.95: 사전 설정
    st = run(bench, 9.95)
    check(
        st,
        1,
        lock_left="RELEASE",
        lock_right="RELEASE",
        reason_code="NO_CHANGE",
        priority_reason="no_change",
    )
    # 2단계 t=10.00: ts가 평가 시각보다 0.050 s 미래: 정상
    st = run(bench, 10.00, ts=10.05, vehicle_speed_kph=3.0)
    check(
        st,
        2,
        lock_left="LOCK",
        lock_right="LOCK",
        state="NORMAL",
        reason_code="AUTO_LOCK",
        priority_reason="auto_lock",
        input_validity="VALID",
    )


def test_ntc_214_ts_51ms_future_invalid(bench):
    """NTC-214 (SWR-013)

    미래 0.051 s 타임스탬프가 INVALID로 처리되는지 확인(허용 경계 +1 단위).
    허용 오차를 넘는 미래 값을 받아들이는 결함 검출
    """
    # 1단계 t=9.95: 사전 설정
    st = run(bench, 9.95)
    check(
        st,
        1,
        lock_left="RELEASE",
        lock_right="RELEASE",
        reason_code="NO_CHANGE",
        priority_reason="no_change",
    )
    # 2단계 t=10.00: ts가 0.051 s 미래: 형식 오류
    code2, st = run_code(bench, 10.00, ts=10.051, vehicle_speed_kph=3.0)
    check(
        st,
        2,
        lock_left="RELEASE",
        lock_right="RELEASE",
        state="DEGRADED",
        reason_code="INPUT_INVALID",
        priority_reason="input_invalid",
        input_validity="INVALID",
    )
    # HTTP 응답 코드는 출력 판정을 모두 본 뒤 확인한다
    check_http(code2, 2)


def test_ntc_215_ts_regression_boundary(bench):
    """NTC-215 (SWR-013)

    ts가 기준 스냅샷과 같으면 정상(unlock 적용), 0.001 s라도 작으면 형식
    오류(INVALID, 명령 폐기)인지 확인. 역행 검사의 <= vs < 오류 검출
    """
    # 1단계 t=10.00: 사전 설정: 기준 스냅샷 ts=10.00, LOCK
    st = run(bench, 10.00, [cmd("all", "lock")])
    check(
        st,
        1,
        lock_left="LOCK",
        lock_right="LOCK",
        reason_code="DRIVER_COMMAND",
        priority_reason="driver_command",
    )
    # 2단계 t=10.05: ts=10.00: 기준 스냅샷과 같음(역행 아님)
    st = run(bench, 10.05, [cmd("left", "unlock")], ts=10.0)
    check(
        st,
        2,
        lock_left="RELEASE",
        lock_right="LOCK",
        state="NORMAL",
        reason_code="DRIVER_COMMAND",
        priority_reason="driver_command",
        input_validity="VALID",
    )
    # 3단계 t=10.10: ts=9.999: 기준 스냅샷(10.00)보다 작음(역행) → unlock 폐기
    st = run(bench, 10.10, [cmd("right", "unlock")], ts=9.999)
    check(
        st,
        3,
        lock_left="RELEASE",
        lock_right="LOCK",
        state="DEGRADED",
        reason_code="INPUT_INVALID",
        priority_reason="input_invalid",
        input_validity="INVALID",
    )


def test_ntc_216_ts_lower_bound(bench):
    """NTC-216 (SWR-013)

    ts=0.0(하한 경계)은 유효, 음수 ts는 INVALID인지 확인. 하한 경계 처리 결함
    검출(음수 값은 역행과 겹쳐 단독 격리 불가, 질의 Q-17)
    """
    # 1단계 t=0.00: 평가 시각 0.00 s, ts=0.00(0.0 이상의 하한): 유효
    st = run(bench, 0.00)
    check(
        st,
        1,
        lock_left="RELEASE",
        lock_right="RELEASE",
        state="NORMAL",
        reason_code="NO_CHANGE",
        priority_reason="no_change",
        input_validity="VALID",
    )
    # 2단계 t=0.05: ts=−0.05(0.0 미만)
    code2, st = run_code(bench, 0.05, ts=-0.05, vehicle_speed_kph=3.0)
    check(
        st,
        2,
        lock_left="RELEASE",
        lock_right="RELEASE",
        state="DEGRADED",
        reason_code="INPUT_INVALID",
        priority_reason="input_invalid",
        input_validity="INVALID",
    )
    # HTTP 응답 코드는 출력 판정을 모두 본 뒤 확인한다
    check_http(code2, 2)


def test_ntc_217_stale_threshold_200ms(bench):
    """NTC-217 (SWR-013, SWR-022)

    스냅샷 없는 주기에서 0.150/0.200 s는 정상, 0.200 s를 처음 넘기는 평가(0.250
    s)에서 DEGRADED/STALE이며 그 시점이 마지막 갱신 후 0.300 s 이내인지 확인.
    지연 임계 연산자 오류, 부동소수 오차(10.30−10.10=0.2000000000000011), 판정
    지연 결함 검출

    비고: 합격 시점: 0.200 s 초과 첫 평가는 평가 시각−마지막 갱신 ≤ 0.300
    s(OEM: 200 ms 초과 후 100 ms 이내, 50 ms 주기이므로 0.250 s에서 판정).
    """
    # 1단계 t=10.10: 사전 설정: 기준 스냅샷 ts=10.10, LOCK
    st = run(bench, 10.10, [cmd("all", "lock")])
    check(
        st,
        1,
        lock_left="LOCK",
        lock_right="LOCK",
        reason_code="DRIVER_COMMAND",
        priority_reason="driver_command",
    )
    # 2단계 t=10.25: 마지막 갱신 후 0.150 s: 정상
    st = run_no_snapshot(bench, 10.25, [cmd("left", "unlock")])
    check(
        st,
        2,
        lock_left="RELEASE",
        lock_right="LOCK",
        state="NORMAL",
        reason_code="DRIVER_COMMAND",
        priority_reason="driver_command",
        input_validity="VALID",
    )
    # 3단계 t=10.30: 마지막 갱신 후 0.200 s(10.30−10.10): 정상(0.200 s 이하)
    st = run_no_snapshot(bench, 10.30, [cmd("right", "unlock")])
    check(
        st,
        3,
        lock_left="RELEASE",
        lock_right="RELEASE",
        state="NORMAL",
        reason_code="DRIVER_COMMAND",
        priority_reason="driver_command",
        input_validity="VALID",
    )
    # 4단계 t=10.35: 마지막 갱신 후 0.250 s: 0.200 s 초과 첫 평가 → STALE, lock
    # 명령 폐기. 0.300 s 이내(0.250 s)
    st = run_no_snapshot(bench, 10.35, [cmd("left", "lock")])
    check(
        st,
        4,
        lock_left="RELEASE",
        lock_right="RELEASE",
        state="DEGRADED",
        reason_code="INPUT_STALE",
        priority_reason="input_stale",
        reason_left="INPUT_STALE",
        reason_right="INPUT_STALE",
        input_validity="STALE",
    )


def test_ntc_218_stale_before_first_snapshot(bench):
    """NTC-218 (SWR-013, SWR-022)

    첫 기준 스냅샷 전 평가가 STALE이고 출력은 초기 RELEASE 유지(명령 폐기)이며
    첫 유효 스냅샷에서 즉시 정상이 되는지 확인(A-15). 초기화 직후 평가를 정상
    판정하는 결함 검출
    """
    # 1단계 t=10.00: 시작 직후 첫 평가, 스냅샷 없음 + lock all
    st = run_no_snapshot(bench, 10.00, [cmd("all", "lock")])
    check(
        st,
        1,
        lock_left="RELEASE",
        lock_right="RELEASE",
        state="DEGRADED",
        reason_code="INPUT_STALE",
        priority_reason="input_stale",
        reason_left="INPUT_STALE",
        reason_right="INPUT_STALE",
        input_validity="STALE",
        warning_code="NONE",
    )
    # 2단계 t=10.05: 첫 유효 스냅샷 수신: 즉시 정상
    st = run(bench, 10.05)
    check(
        st,
        2,
        lock_left="RELEASE",
        lock_right="RELEASE",
        state="NORMAL",
        reason_code="NO_CHANGE",
        priority_reason="no_change",
        input_validity="VALID",
    )


def test_ntc_219_qm_error_persists_on_reference(bench):
    """NTC-219 (SWR-013)

    QM 오류 스냅샷이 기준 스냅샷이 되어 스냅샷 없는 주기에도 순위 5(INVALID,
    직전 유지)가 이어지고 다음 정상 스냅샷에서 해소되는지 확인(③). 무스냅샷
    주기에 오류를 지우는 결함 검출
    """
    # 1단계 t=10.00: 사전 설정: LOCK
    st = run(bench, 10.00, [cmd("all", "lock")])
    check(
        st,
        1,
        lock_left="LOCK",
        lock_right="LOCK",
        reason_code="DRIVER_COMMAND",
        priority_reason="driver_command",
    )
    # 2단계 t=10.05: QM 오류(gear) 스냅샷 수신
    st = run(bench, 10.05, gear="X")
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
    # 3단계 t=10.10: 스냅샷 없음: QM 오류는 다음 기준 스냅샷까지 순위 5로
    # 유지(unlock 폐기)
    st = run_no_snapshot(bench, 10.10, [cmd("left", "unlock")])
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
    # 4단계 t=10.15: 정상 스냅샷: 오류 해소, unlock 적용
    st = run(bench, 10.15, [cmd("left", "unlock")])
    check(
        st,
        4,
        lock_left="RELEASE",
        lock_right="LOCK",
        state="NORMAL",
        reason_code="DRIVER_COMMAND",
        priority_reason="driver_command",
        input_validity="VALID",
    )


def test_ntc_220_asil_b_error_not_reference(bench):
    """NTC-220 (SWR-013)

    ASIL B 오류 스냅샷이 기준 스냅샷을 갱신하지 않아 지연이 마지막 유효 스냅샷
    기준으로 판정(STALE)되는지 확인(③). 오류 스냅샷으로 지연 타이머를 리셋하는
    결함 검출
    """
    # 1단계 t=10.00: 사전 설정: 기준 스냅샷 ts=10.00, LOCK
    st = run(bench, 10.00, [cmd("all", "lock")])
    check(
        st,
        1,
        lock_left="LOCK",
        lock_right="LOCK",
        reason_code="DRIVER_COMMAND",
        priority_reason="driver_command",
    )
    # 2단계 t=10.10: ASIL B 오류 스냅샷(기준 스냅샷이 되면 안 됨)
    st = run(bench, 10.10, rear_right_approach_risk=1)
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
    # 3단계 t=10.25: 기준 스냅샷(10.00)으로부터 0.250 s: STALE(오류 스냅샷이
    # 기준이면 0.150 s로 VALID가 되어 unlock이 적용됨)
    st = run_no_snapshot(bench, 10.25, [cmd("left", "unlock")])
    check(
        st,
        3,
        lock_left="LOCK",
        lock_right="LOCK",
        state="DEGRADED",
        reason_code="INPUT_STALE",
        priority_reason="input_stale",
        input_validity="STALE",
    )


def test_ntc_221_qm_error_not_stale(bench):
    """NTC-221 (SWR-013, SWR-005)

    gear(QM) 오류만 있는 스냅샷이 0.5 s 이어져도 STALE이 되지 않고
    접근위험(ASIL B) LOCK이 적용되는지 확인(수용기준, P-1). QM 오류를 ASIL B
    입력 이상으로 취급하는 결함 검출

    비고: 수용기준의 '0.5초 동안'은 스냅샷이 계속 도착하는 상황으로 해석하여
    0.25 s 간격 스냅샷 3회로 구성.
    """
    # 1단계 t=10.00: 사전 설정
    st = run(bench, 10.00)
    check(
        st,
        1,
        lock_left="RELEASE",
        lock_right="RELEASE",
        reason_code="NO_CHANGE",
        priority_reason="no_change",
    )
    # 2단계 t=10.05: gear 오류 지속 0.05 s
    st = run(bench, 10.05, gear="X")
    check(
        st,
        2,
        lock_left="RELEASE",
        lock_right="RELEASE",
        state="DEGRADED",
        reason_code="INPUT_INVALID",
        priority_reason="input_invalid",
        input_validity="INVALID",
    )
    # 3단계 t=10.30: gear 오류 지속 0.30 s(STALE 아님)
    st = run(bench, 10.30, gear="X")
    check(
        st,
        3,
        lock_left="RELEASE",
        lock_right="RELEASE",
        state="DEGRADED",
        reason_code="INPUT_INVALID",
        priority_reason="input_invalid",
        input_validity="INVALID",
    )
    # 4단계 t=10.55: gear 오류 0.50 s 지속 중 좌 접근위험 true
    st = run(bench, 10.55, gear="X", rear_left_approach_risk=True)
    check(
        st,
        4,
        lock_left="LOCK",
        lock_right="RELEASE",
        state="DEGRADED",
        reason_code="APPROACH_RISK",
        priority_reason="approach_risk",
        reason_left="APPROACH_RISK",
        reason_right="INPUT_INVALID",
        input_validity="INVALID",
    )


def test_ntc_222_qm_error_with_approach_risk(bench):
    """NTC-222 (SWR-013, SWR-009)

    QM 오류(isofix_left=1)와 ASIL B 접근위험이 같이 있을 때 좌
    LOCK(APPROACH_RISK), 우 직전 유지(INPUT_INVALID), state=DEGRADED인지
    확인(수용기준 그대로). 쪽별 혼합 판정 결함 검출
    """
    # 1단계 t=10.00: 사전 설정
    st = run(bench, 10.00)
    check(
        st,
        1,
        lock_left="RELEASE",
        lock_right="RELEASE",
        reason_code="NO_CHANGE",
        priority_reason="no_change",
    )
    # 2단계 t=10.05: isofix_left=1(QM 형식 오류) + 좌 접근위험 true
    st = run(bench, 10.05, isofix_left=1, rear_left_approach_risk=True)
    check(
        st,
        2,
        lock_left="LOCK",
        lock_right="RELEASE",
        state="DEGRADED",
        reason_code="APPROACH_RISK",
        priority_reason="approach_risk",
        reason_left="APPROACH_RISK",
        reason_right="INPUT_INVALID",
        input_validity="INVALID",
    )


def test_ntc_223_gear_values_ignored(bench):
    """NTC-223 (SWR-013)

    gear의 유효 값 4종(P/N/D/R)이 모두 VALID이고 판단에 쓰이지 않아 3.0
    km/h에서 항상 AUTO_LOCK이 되는지 확인(A-11). 특정 gear를 오류로 보거나
    gear로 자동 잠금을 억제하는 결함 검출
    """
    # 1단계 t=10.00: gear="P"
    st = run(bench, 10.00, gear="P", vehicle_speed_kph=3.0)
    check(
        st,
        1,
        lock_left="LOCK",
        lock_right="LOCK",
        state="NORMAL",
        reason_code="AUTO_LOCK",
        priority_reason="auto_lock",
        input_validity="VALID",
        warning_code="NONE",
    )
    # 2단계 t=10.05: gear="N"
    st = run(bench, 10.05, gear="N", vehicle_speed_kph=3.0)
    check(
        st,
        2,
        lock_left="LOCK",
        lock_right="LOCK",
        state="NORMAL",
        reason_code="AUTO_LOCK",
        priority_reason="auto_lock",
        input_validity="VALID",
        warning_code="NONE",
    )
    # 3단계 t=10.10: gear="D"
    st = run(bench, 10.10, gear="D", vehicle_speed_kph=3.0)
    check(
        st,
        3,
        lock_left="LOCK",
        lock_right="LOCK",
        state="NORMAL",
        reason_code="AUTO_LOCK",
        priority_reason="auto_lock",
        input_validity="VALID",
        warning_code="NONE",
    )
    # 4단계 t=10.15: gear="R"
    st = run(bench, 10.15, gear="R", vehicle_speed_kph=3.0)
    check(
        st,
        4,
        lock_left="LOCK",
        lock_right="LOCK",
        state="NORMAL",
        reason_code="AUTO_LOCK",
        priority_reason="auto_lock",
        input_validity="VALID",
        warning_code="NONE",
    )


def test_ntc_224_command_invalid_side_dropped(bench):
    """NTC-224 (SWR-013, SWR-002)

    운전자 명령 오류(side가 미등록 값("up"))는 그 명령만 버려지고 같은 평가의
    유효 명령은 적용되는지 확인(⑤). 오류 명령을 기본값으로 보정해 실행하거나
    평가 전체를 버리는 결함 검출

    비고: 오류 명령 폐기 시 input_validity/state 표시는 원문에 없어 판정에서
    제외(질의 Q-03). 합격: 오류 명령 대상 출력(우측)이 LOCK 유지.
    """
    # 1단계 t=10.00: 사전 설정: LOCK
    st = run(bench, 10.00, [cmd("all", "lock")])
    check(
        st,
        1,
        lock_left="LOCK",
        lock_right="LOCK",
        reason_code="DRIVER_COMMAND",
        priority_reason="driver_command",
    )
    # 2단계 t=10.05: 유효 명령 cmd(left,unlock,avn) + 오류 명령
    # {"side":"up","action":"unlock","source":"avn"}
    st = run(
        bench,
        10.05,
        [
            cmd("left", "unlock", "avn"),
            {"side": "up", "action": "unlock", "source": "avn"},
        ],
    )
    check(
        st,
        2,
        lock_left="RELEASE",
        lock_right="LOCK",
        state="NORMAL",
        reason_code="DRIVER_COMMAND",
        priority_reason="driver_command",
        reason_left="DRIVER_COMMAND",
        reason_right="NO_CHANGE",
    )


def test_ntc_225_command_invalid_action_dropped(bench):
    """NTC-225 (SWR-013, SWR-002)

    운전자 명령 오류(action이 미등록 값("toggle"))는 그 명령만 버려지고 같은
    평가의 유효 명령은 적용되는지 확인(⑤). 오류 명령을 기본값으로 보정해
    실행하거나 평가 전체를 버리는 결함 검출

    비고: 오류 명령 폐기 시 input_validity/state 표시는 원문에 없어 판정에서
    제외(질의 Q-03). 합격: 오류 명령 대상 출력(우측)이 LOCK 유지.
    """
    # 1단계 t=10.00: 사전 설정: LOCK
    st = run(bench, 10.00, [cmd("all", "lock")])
    check(
        st,
        1,
        lock_left="LOCK",
        lock_right="LOCK",
        reason_code="DRIVER_COMMAND",
        priority_reason="driver_command",
    )
    # 2단계 t=10.05: 유효 명령 cmd(left,unlock,avn) + 오류 명령
    # {"side":"right","action":"toggle","source":"avn"}
    st = run(
        bench,
        10.05,
        [
            cmd("left", "unlock", "avn"),
            {"side": "right", "action": "toggle", "source": "avn"},
        ],
    )
    check(
        st,
        2,
        lock_left="RELEASE",
        lock_right="LOCK",
        state="NORMAL",
        reason_code="DRIVER_COMMAND",
        priority_reason="driver_command",
        reason_left="DRIVER_COMMAND",
        reason_right="NO_CHANGE",
    )


def test_ntc_226_command_invalid_source_dropped(bench):
    """NTC-226 (SWR-013, SWR-002)

    운전자 명령 오류(source가 미등록 값("keyboard"))는 그 명령만 버려지고 같은
    평가의 유효 명령은 적용되는지 확인(⑤). 오류 명령을 기본값으로 보정해
    실행하거나 평가 전체를 버리는 결함 검출

    비고: 오류 명령 폐기 시 input_validity/state 표시는 원문에 없어 판정에서
    제외(질의 Q-03). 합격: 오류 명령 대상 출력(우측)이 LOCK 유지.
    """
    # 1단계 t=10.00: 사전 설정: LOCK
    st = run(bench, 10.00, [cmd("all", "lock")])
    check(
        st,
        1,
        lock_left="LOCK",
        lock_right="LOCK",
        reason_code="DRIVER_COMMAND",
        priority_reason="driver_command",
    )
    # 2단계 t=10.05: 유효 명령 cmd(left,unlock,avn) + 오류 명령
    # {"side":"right","action":"unlock","source":"keyboard"}
    st = run(
        bench,
        10.05,
        [
            cmd("left", "unlock", "avn"),
            {"side": "right", "action": "unlock", "source": "keyboard"},
        ],
    )
    check(
        st,
        2,
        lock_left="RELEASE",
        lock_right="LOCK",
        state="NORMAL",
        reason_code="DRIVER_COMMAND",
        priority_reason="driver_command",
        reason_left="DRIVER_COMMAND",
        reason_right="NO_CHANGE",
    )


def test_ntc_227_command_missing_source_dropped(bench):
    """NTC-227 (SWR-013, SWR-002)

    운전자 명령 오류(source 필드 누락)는 그 명령만 버려지고 같은 평가의 유효
    명령은 적용되는지 확인(⑤). 오류 명령을 기본값으로 보정해 실행하거나 평가
    전체를 버리는 결함 검출

    비고: 오류 명령 폐기 시 input_validity/state 표시는 원문에 없어 판정에서
    제외(질의 Q-03). 합격: 오류 명령 대상 출력(우측)이 LOCK 유지.
    """
    # 1단계 t=10.00: 사전 설정: LOCK
    st = run(bench, 10.00, [cmd("all", "lock")])
    check(
        st,
        1,
        lock_left="LOCK",
        lock_right="LOCK",
        reason_code="DRIVER_COMMAND",
        priority_reason="driver_command",
    )
    # 2단계 t=10.05: 유효 명령 cmd(left,unlock,avn) + 오류 명령
    # {"side":"right","action":"unlock"}
    st = run(
        bench,
        10.05,
        [cmd("left", "unlock", "avn"), {"side": "right", "action": "unlock"}],
    )
    check(
        st,
        2,
        lock_left="RELEASE",
        lock_right="LOCK",
        state="NORMAL",
        reason_code="DRIVER_COMMAND",
        priority_reason="driver_command",
        reason_left="DRIVER_COMMAND",
        reason_right="NO_CHANGE",
    )
