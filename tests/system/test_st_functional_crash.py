"""@brief SWE.6 기능 시험: 충돌 래치·PENDING 필터 (SWR-007, 008).

근거: docs/swe6/system-test-cases.json
"""

from tests.system.harness import cmd
from tests.system.st_support import check, run, run_no_snapshot


def test_ftc_127_crash_latch_within_300ms_and_held(bench):
    """FTC-127 (SWR-007)

    나이 0.200 s인 CONFIRMED로 래치가 서 0.300 s 이내(0.200 s) RELEASE가 되고,
    이후 NONE·접근위험·ISOFIX·자동 잠금·lock·sensor fault가 와도 RELEASE가
    유지되는지 확인. 래치 미유지·낮은 순위 규칙 누수 결함 검출
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
    # 2단계 t=10.25: CONFIRMED 스냅샷(ts=10.05, 나이 0.200 s). 평가 시각−ts =
    # 0.200 s ≤ 0.300 s
    st = run(bench, 10.25, ts=10.05, crash_status="CONFIRMED")
    check(
        st,
        2,
        lock_left="RELEASE",
        lock_right="RELEASE",
        state="NORMAL",
        reason_code="CRASH_CONFIRMED",
        priority_reason="crash_confirmed",
        reason_left="CRASH_CONFIRMED",
        reason_right="CRASH_CONFIRMED",
        input_validity="VALID",
    )
    # 3단계 t=10.30: NONE 수신 + 접근위험·ISOFIX·자동잠금·lock 모두
    st = run(
        bench,
        10.30,
        [cmd("all", "lock")],
        crash_status="NONE",
        vehicle_speed_kph=3.0,
        isofix_left=True,
        isofix_right=True,
        rear_left_approach_risk=True,
        rear_right_approach_risk=True,
    )
    check(
        st,
        3,
        lock_left="RELEASE",
        lock_right="RELEASE",
        state="NORMAL",
        reason_code="CRASH_CONFIRMED",
        priority_reason="crash_confirmed",
    )
    # 4단계 t=10.35: 래치 중 sensor fault
    st = run(bench, 10.35, sensor_fault=True)
    check(
        st,
        4,
        lock_left="RELEASE",
        lock_right="RELEASE",
        state="FAULT",
        reason_code="CRASH_CONFIRMED",
        priority_reason="crash_confirmed",
        reason_left="CRASH_CONFIRMED",
        reason_right="CRASH_CONFIRMED",
    )


def test_ftc_128_late_confirmed_age_1s_latches(bench):
    """FTC-128 (SWR-007, SWR-013)

    나이 1.0 s(상한 경계)의 늦게 도착한 CONFIRMED도 래치를 세우고(지연 0.200 s
    초과와 무관), 입력은 STALE/DEGRADED로 표시되는지 확인. 1.0 s 경계 연산자
    오류와 부동소수 오차(16.10-15.10=1.0000000000000018) 처리 결함 검출

    비고: input_validity=STALE은 SWR-013 ①③에서 도출(늦은 스냅샷이 기준
    스냅샷이 되며 나이 1.00 s > 0.200 s). 질의 Q-16.
    """
    # 1단계 t=15.05: 사전 설정: LOCK
    st = run(bench, 15.05, vehicle_speed_kph=3.0)
    check(
        st,
        1,
        lock_left="LOCK",
        lock_right="LOCK",
        reason_code="AUTO_LOCK",
        priority_reason="auto_lock",
    )
    # 2단계 t=16.10: CONFIRMED 스냅샷 나이 정확히 1.00 s(ts=15.10, 평가 시각
    # 16.10)
    st = run(bench, 16.10, ts=15.1, crash_status="CONFIRMED")
    check(
        st,
        2,
        lock_left="RELEASE",
        lock_right="RELEASE",
        state="DEGRADED",
        reason_code="CRASH_CONFIRMED",
        priority_reason="crash_confirmed",
        reason_left="CRASH_CONFIRMED",
        reason_right="CRASH_CONFIRMED",
        input_validity="STALE",
    )


def test_ftc_129_confirmed_age_1_05s_no_latch(bench):
    """FTC-129 (SWR-007)

    나이 1.05 s CONFIRMED로는 래치가 서지 않고(직전 LOCK 유지, 입력 STALE),
    이후 unlock이 적용되는지 확인. 나이 상한 미검사 결함 검출
    """
    # 1단계 t=15.05: 사전 설정: LOCK
    st = run(bench, 15.05, vehicle_speed_kph=3.0)
    check(
        st,
        1,
        lock_left="LOCK",
        lock_right="LOCK",
        reason_code="AUTO_LOCK",
        priority_reason="auto_lock",
    )
    # 2단계 t=16.15: CONFIRMED 나이 1.05 s: 래치 없음
    st = run(bench, 16.15, ts=15.1, crash_status="CONFIRMED")
    check(
        st,
        2,
        lock_left="LOCK",
        lock_right="LOCK",
        state="DEGRADED",
        reason_code="INPUT_STALE",
        priority_reason="input_stale",
        reason_left="INPUT_STALE",
        reason_right="INPUT_STALE",
        input_validity="STALE",
    )
    # 3단계 t=16.20: 래치가 없으므로 unlock 정상 적용
    st = run(bench, 16.20, [cmd("left", "unlock")])
    check(
        st,
        3,
        lock_left="RELEASE",
        lock_right="LOCK",
        state="NORMAL",
        reason_code="DRIVER_COMMAND",
        priority_reason="driver_command",
        input_validity="VALID",
    )


def test_ftc_130_confirmed_ts_50ms_future_latches(bench):
    """FTC-130 (SWR-007, SWR-013)

    미래 0.050 s 타임스탬프의 CONFIRMED가 유효로 처리되어 래치가 서는지 확인.
    나이 음수(−0.05 s)를 오류로 보거나 허용 오차 부동소수
    처리(10.05−10.00>0.05) 결함 검출
    """
    # 1단계 t=9.95: 사전 설정: LOCK
    st = run(bench, 9.95, vehicle_speed_kph=3.0)
    check(
        st,
        1,
        lock_left="LOCK",
        lock_right="LOCK",
        reason_code="AUTO_LOCK",
        priority_reason="auto_lock",
    )
    # 2단계 t=10.00: CONFIRMED, ts가 평가 시각보다 0.050 s 미래(허용 경계)
    st = run(bench, 10.00, ts=10.05, crash_status="CONFIRMED")
    check(
        st,
        2,
        lock_left="RELEASE",
        lock_right="RELEASE",
        state="NORMAL",
        reason_code="CRASH_CONFIRMED",
        priority_reason="crash_confirmed",
        input_validity="VALID",
    )


def test_ftc_131_confirmed_ts_51ms_future_rejected(bench):
    """FTC-131 (SWR-007, SWR-013)

    타임스탬프가 0.051 s 미래인 CONFIRMED는 형식 오류로 보아 래치를 세우지
    않는지 확인(충돌 판정은 타임스탬프가 유효할 때만). 허용 오차 초과 미검사
    결함 검출
    """
    # 1단계 t=9.95: 사전 설정: LOCK
    st = run(bench, 9.95, vehicle_speed_kph=3.0)
    check(
        st,
        1,
        lock_left="LOCK",
        lock_right="LOCK",
        reason_code="AUTO_LOCK",
        priority_reason="auto_lock",
    )
    # 2단계 t=10.00: CONFIRMED, ts가 0.051 s 미래: 형식 오류, 래치 없음
    st = run(bench, 10.00, ts=10.051, crash_status="CONFIRMED")
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
    # 3단계 t=10.05: 래치가 없으므로 unlock 적용
    st = run(bench, 10.05, [cmd("left", "unlock")])
    check(
        st,
        3,
        lock_left="RELEASE",
        lock_right="LOCK",
        state="NORMAL",
        reason_code="DRIVER_COMMAND",
        priority_reason="driver_command",
        input_validity="VALID",
    )


def test_ftc_132_crash_ignores_timestamp_regression(bench):
    """FTC-132 (SWR-007, SWR-013)

    타임스탬프 역행 스냅샷이어도 충돌 판정에는 역행 검사를 적용하지 않아 래치가
    서고, 나머지 신호는 INVALID/DEGRADED로 처리되는지 확인(v1.2 명시). 충돌
    판정에 역행 검사를 적용하는 결함 검출
    """
    # 1단계 t=10.00: 사전 설정: LOCK(기준 스냅샷 ts=10.00)
    st = run(bench, 10.00, vehicle_speed_kph=3.0)
    check(
        st,
        1,
        lock_left="LOCK",
        lock_right="LOCK",
        reason_code="AUTO_LOCK",
        priority_reason="auto_lock",
    )
    # 2단계 t=10.05: CONFIRMED이지만 ts=9.95가 기준 스냅샷(10.00)보다
    # 작음(역행)
    st = run(bench, 10.05, ts=9.95, crash_status="CONFIRMED")
    check(
        st,
        2,
        lock_left="RELEASE",
        lock_right="RELEASE",
        state="DEGRADED",
        reason_code="CRASH_CONFIRMED",
        priority_reason="crash_confirmed",
        input_validity="INVALID",
    )


def test_ftc_133_latch_released_by_ignition_off(bench):
    """FTC-133 (SWR-007)

    시동 OFF(유효)+CONFIRMED 아님 스냅샷으로 래치가 해제되고 시동 ON 이후 정상
    판정으로 돌아가는지 확인. 래치 영구 유지 결함 검출
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
    # 2단계 t=10.05: 래치 성립
    st = run(bench, 10.05, crash_status="CONFIRMED")
    check(
        st,
        2,
        lock_left="RELEASE",
        lock_right="RELEASE",
        reason_code="CRASH_CONFIRMED",
        priority_reason="crash_confirmed",
    )
    # 3단계 t=10.10: 시동 OFF + NONE: 래치 해제
    st = run(bench, 10.10, ignition_on=False)
    check(
        st,
        3,
        lock_left="RELEASE",
        lock_right="RELEASE",
        state="OFF",
        reason_code="IGNITION_OFF",
        priority_reason="ignition_off",
    )
    # 4단계 t=10.15: 시동 ON + 차속 3.0 km/h: 래치가 풀려 자동 잠금
    st = run(bench, 10.15, vehicle_speed_kph=3.0)
    check(
        st,
        4,
        lock_left="LOCK",
        lock_right="LOCK",
        state="NORMAL",
        reason_code="AUTO_LOCK",
        priority_reason="auto_lock",
        reason_left="AUTO_LOCK",
        reason_right="AUTO_LOCK",
    )


def test_ftc_134_latch_kept_when_still_confirmed(bench):
    """FTC-134 (SWR-007)

    시동 OFF만으로는(crash_status가 CONFIRMED 그대로) 래치가 풀리지 않는지
    확인. 해제 조건에서 crash_status 검사 누락 결함 검출(FTC-133과 쌍)
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
    # 2단계 t=10.05: 래치 성립
    st = run(bench, 10.05, crash_status="CONFIRMED")
    check(
        st,
        2,
        lock_left="RELEASE",
        lock_right="RELEASE",
        reason_code="CRASH_CONFIRMED",
        priority_reason="crash_confirmed",
    )
    # 3단계 t=10.10: 시동 OFF이지만 crash_status가 여전히 CONFIRMED: 해제 안 됨
    st = run(bench, 10.10, crash_status="CONFIRMED", ignition_on=False)
    check(
        st,
        3,
        lock_left="RELEASE",
        lock_right="RELEASE",
        state="OFF",
        reason_code="CRASH_CONFIRMED",
        priority_reason="crash_confirmed",
    )
    # 4단계 t=10.15: 시동 ON + NONE: 해제 조건(시동 OFF)이 없었으므로 래치 유지
    st = run(bench, 10.15, vehicle_speed_kph=3.0)
    check(
        st,
        4,
        lock_left="RELEASE",
        lock_right="RELEASE",
        state="NORMAL",
        reason_code="CRASH_CONFIRMED",
        priority_reason="crash_confirmed",
    )


def test_ftc_135_latch_released_with_pending(bench):
    """FTC-135 (SWR-007, SWR-008)

    해제 조건의 'CONFIRMED가 아님'에 PENDING도 포함되어 래치가 해제되는지
    확인(동치 클래스 NONE/PENDING). NONE만 해제로 보는 결함 검출
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
    # 2단계 t=10.05: 래치 성립
    st = run(bench, 10.05, crash_status="CONFIRMED")
    check(
        st,
        2,
        lock_left="RELEASE",
        lock_right="RELEASE",
        reason_code="CRASH_CONFIRMED",
        priority_reason="crash_confirmed",
    )
    # 3단계 t=10.10: 시동 OFF + PENDING(CONFIRMED 아님): 래치 해제
    st = run(bench, 10.10, ignition_on=False, crash_status="PENDING")
    check(
        st,
        3,
        lock_left="RELEASE",
        lock_right="RELEASE",
        state="OFF",
        reason_code="IGNITION_OFF",
        priority_reason="ignition_off",
    )
    # 4단계 t=10.15: 시동 ON + NONE + 3.0 km/h: 자동 잠금
    st = run(bench, 10.15, vehicle_speed_kph=3.0)
    check(
        st,
        4,
        lock_left="LOCK",
        lock_right="LOCK",
        state="NORMAL",
        reason_code="AUTO_LOCK",
        priority_reason="auto_lock",
    )


def test_ftc_136_latch_release_ignores_other_errors(bench):
    """FTC-136 (SWR-007, SWR-013)

    해제 판정이 crash_status·ignition_on·source_timestamp_s의 유효성만 요구하고
    다른 신호(차속) 오류와 무관한지 확인. 다른 신호 오류 시 해제가 막히는 결함
    검출 [제안 케이스]

    비고: 가정: 3개 신호가 유효하면 다른 신호 오류와 무관하게 해제된다(원문은
    '~일 때만'이라 필요조건만 명시). 질의 Q-08.
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
    # 2단계 t=10.05: 래치 성립
    st = run(bench, 10.05, crash_status="CONFIRMED")
    check(
        st,
        2,
        lock_left="RELEASE",
        lock_right="RELEASE",
        reason_code="CRASH_CONFIRMED",
        priority_reason="crash_confirmed",
    )
    # 3단계 t=10.10: 래치 해제 스냅샷(시동 OFF, NONE)이지만 차속 300.1
    # km/h(ASIL B 범위 오류)
    st = run(bench, 10.10, ignition_on=False, vehicle_speed_kph=300.1)
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
    # 4단계 t=10.15: 시동 ON + 3.0 km/h: 래치가 풀렸다면 자동 잠금
    st = run(bench, 10.15, vehicle_speed_kph=3.0)
    check(
        st,
        4,
        lock_left="LOCK",
        lock_right="LOCK",
        state="NORMAL",
        reason_code="AUTO_LOCK",
        priority_reason="auto_lock",
    )


def test_ftc_137_crash_status_case_sensitive(bench):
    """FTC-137 (SWR-007, SWR-013)

    crash_status 문자열 비교가 대소문자 구분인지("confirmed"는 미등록 enum으로
    INVALID, 래치 없음) 확인. 대소문자 무시 비교 결함 검출
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
    # 2단계 t=10.05: 소문자 "confirmed"(미등록 enum)
    st = run(bench, 10.05, crash_status="confirmed")
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
    # 3단계 t=10.10: 래치 없음 확인
    st = run(bench, 10.10, [cmd("left", "unlock")])
    check(
        st,
        3,
        lock_left="RELEASE",
        lock_right="LOCK",
        state="NORMAL",
        reason_code="DRIVER_COMMAND",
        priority_reason="driver_command",
        input_validity="VALID",
    )


def test_ftc_138_confirmed_on_first_evaluation(bench):
    """FTC-138 (SWR-007)

    초기화 직후 첫 평가의 CONFIRMED가 래치를 세워 RELEASE(자동 잠금 없음)가
    되는지 확인. 첫 평가를 STALE/초기화 처리로 건너뛰는 결함 검출
    """
    # 1단계 t=10.00: 시작 직후 첫 평가부터 CONFIRMED + 3.0 km/h
    st = run(bench, 10.00, crash_status="CONFIRMED", vehicle_speed_kph=3.0)
    check(
        st,
        1,
        lock_left="RELEASE",
        lock_right="RELEASE",
        state="NORMAL",
        reason_code="CRASH_CONFIRMED",
        priority_reason="crash_confirmed",
        input_validity="VALID",
    )


def test_ftc_139_no_release_on_missing_snapshot(bench):
    """FTC-139 (SWR-007, SWR-022)

    스냅샷 없는 주기에 기준 스냅샷의 '시동 OFF+NONE'을 다시 써서 래치를
    해제하지 않는지 확인(reason이 IGNITION_OFF로 바뀌거나 이후 자동 잠금이 되면
    결함). 직전 값 재사용 해제 결함 검출
    """
    # 1단계 t=10.00: 사전 설정: 시동 OFF NONE 스냅샷이 기준 스냅샷
    st = run(bench, 10.00, ignition_on=False)
    check(
        st,
        1,
        lock_left="RELEASE",
        lock_right="RELEASE",
        state="OFF",
        reason_code="IGNITION_OFF",
        priority_reason="ignition_off",
        input_validity="VALID",
    )
    # 2단계 t=10.05: CONFIRMED + ASIL B 오류(기준 스냅샷이 되지 못함): 래치
    # 성립
    st = run(
        bench,
        10.05,
        crash_status="CONFIRMED",
        ignition_on=False,
        rear_right_approach_risk=1,
    )
    check(
        st,
        2,
        lock_left="RELEASE",
        lock_right="RELEASE",
        state="DEGRADED",
        reason_code="CRASH_CONFIRMED",
        priority_reason="crash_confirmed",
        input_validity="INVALID",
    )
    # 3단계 t=10.10: 스냅샷 없음: 기준 스냅샷은 1단계(시동 OFF, NONE)
    st = run_no_snapshot(bench, 10.10)
    check(
        st,
        3,
        lock_left="RELEASE",
        lock_right="RELEASE",
        state="OFF",
        reason_code="CRASH_CONFIRMED",
        priority_reason="crash_confirmed",
        reason_left="CRASH_CONFIRMED",
        reason_right="CRASH_CONFIRMED",
        input_validity="VALID",
    )
    # 4단계 t=10.15: 시동 ON, NONE, 3.0 km/h: 래치 유지
    st = run(bench, 10.15, vehicle_speed_kph=3.0)
    check(
        st,
        4,
        lock_left="RELEASE",
        lock_right="RELEASE",
        state="NORMAL",
        reason_code="CRASH_CONFIRMED",
        priority_reason="crash_confirmed",
    )


def test_ftc_140_pending_blocks_lock_only(bench):
    """FTC-140 (SWR-008, SWR-019)

    PENDING이 RELEASE 방향(좌 unlock)은 막지 않고 우측 ISOFIX LOCK만 막으며,
    reason_code가 막은 규칙(순위 8)의 순위로 비교되어 CRASH_PENDING이 되는지
    확인(좌 DRIVER_COMMAND는 순위 10). 막은 이유 순위 계산 결함 검출
    """
    # 1단계 t=10.00: 사전 설정: 좌 LOCK, 우 RELEASE
    st = run(bench, 10.00, [cmd("left", "lock")])
    check(
        st,
        1,
        lock_left="LOCK",
        lock_right="RELEASE",
        reason_code="DRIVER_COMMAND",
        priority_reason="driver_command",
    )
    # 2단계 t=10.05: PENDING 중 좌 unlock(RELEASE 방향) + 우 ISOFIX(막힘)
    st = run(
        bench,
        10.05,
        [cmd("left", "unlock")],
        crash_status="PENDING",
        isofix_right=True,
    )
    check(
        st,
        2,
        lock_left="RELEASE",
        lock_right="RELEASE",
        state="NORMAL",
        reason_code="CRASH_PENDING",
        priority_reason="crash_pending",
        reason_left="DRIVER_COMMAND",
        reason_right="CRASH_PENDING",
    )


def test_ftc_141_pending_timer_2s_boundary(bench):
    """FTC-141 (SWR-008)

    PENDING 지속 1.95/2.00/2.05 s에서 2.0 s 이하는 막고 2.05 s에서 자동 잠금이
    적용되는지 확인. 2.0 s 경계 연산자 오류와 부동소수 오차(16.10−14.10>2.0)
    처리 결함 검출
    """
    # 1단계 t=14.10: PENDING 최초 평가(타이머 시작 14.10 s)
    st = run(bench, 14.10, crash_status="PENDING")
    check(
        st,
        1,
        lock_left="RELEASE",
        lock_right="RELEASE",
        state="NORMAL",
        reason_code="NO_CHANGE",
        priority_reason="no_change",
    )
    # 2단계 t=16.05: 경과 1.95 s: 막음
    st = run(bench, 16.05, crash_status="PENDING", vehicle_speed_kph=3.0)
    check(
        st,
        2,
        lock_left="RELEASE",
        lock_right="RELEASE",
        state="NORMAL",
        reason_code="CRASH_PENDING",
        priority_reason="crash_pending",
        reason_left="CRASH_PENDING",
        reason_right="CRASH_PENDING",
    )
    # 3단계 t=16.10: 경과 정확히 2.00 s(16.10−14.10): 막음
    st = run(bench, 16.10, crash_status="PENDING", vehicle_speed_kph=3.0)
    check(
        st,
        3,
        lock_left="RELEASE",
        lock_right="RELEASE",
        state="NORMAL",
        reason_code="CRASH_PENDING",
        priority_reason="crash_pending",
        reason_left="CRASH_PENDING",
        reason_right="CRASH_PENDING",
    )
    # 4단계 t=16.15: 경과 2.05 s: 막지 않음, 자동 잠금 적용
    st = run(bench, 16.15, crash_status="PENDING", vehicle_speed_kph=3.0)
    check(
        st,
        4,
        lock_left="LOCK",
        lock_right="LOCK",
        state="NORMAL",
        reason_code="AUTO_LOCK",
        priority_reason="auto_lock",
        reason_left="AUTO_LOCK",
        reason_right="AUTO_LOCK",
    )


def test_ftc_142_pending_timer_restarts(bench):
    """FTC-142 (SWR-008)

    PENDING→NONE→PENDING에서 타이머가 새로 시작되는지 확인(재시작 후 1.95 s는
    막힘, 2.05 s는 풀림). NONE 수신 시 타이머를 지우지 않는 결함 검출
    """
    # 1단계 t=10.00: PENDING 시작 10.00 s
    st = run(bench, 10.00, crash_status="PENDING")
    check(
        st,
        1,
        lock_left="RELEASE",
        lock_right="RELEASE",
        reason_code="NO_CHANGE",
        priority_reason="no_change",
    )
    # 2단계 t=11.00: NONE: 타이머 삭제
    st = run(bench, 11.00, crash_status="NONE")
    check(
        st,
        2,
        lock_left="RELEASE",
        lock_right="RELEASE",
        reason_code="NO_CHANGE",
        priority_reason="no_change",
    )
    # 3단계 t=11.05: PENDING 재시작(새 타이머 11.05 s)
    st = run(bench, 11.05, crash_status="PENDING")
    check(
        st,
        3,
        lock_left="RELEASE",
        lock_right="RELEASE",
        reason_code="NO_CHANGE",
        priority_reason="no_change",
    )
    # 4단계 t=13.00: 재시작 후 1.95 s(최초 시작 기준 3.00 s): 막음
    st = run(bench, 13.00, crash_status="PENDING", vehicle_speed_kph=3.0)
    check(
        st,
        4,
        lock_left="RELEASE",
        lock_right="RELEASE",
        reason_code="CRASH_PENDING",
        priority_reason="crash_pending",
    )
    # 5단계 t=13.10: 재시작 후 2.05 s: 막지 않음
    st = run(bench, 13.10, crash_status="PENDING", vehicle_speed_kph=3.0)
    check(
        st,
        5,
        lock_left="LOCK",
        lock_right="LOCK",
        reason_code="AUTO_LOCK",
        priority_reason="auto_lock",
    )


def test_ftc_143_pending_timer_unaffected_by_errors(bench):
    """FTC-143 (SWR-008, SWR-013)

    신호 오류 스냅샷과 스냅샷 없는 주기가 PENDING 타이머를 재시작하지 않는지
    확인(2.05 s에 자동 잠금 적용). 오류·무스냅샷 평가가 타이머를 초기화하는
    결함 검출
    """
    # 1단계 t=10.00: PENDING 시작 10.00 s
    st = run(bench, 10.00, crash_status="PENDING")
    check(
        st,
        1,
        lock_left="RELEASE",
        lock_right="RELEASE",
        reason_code="NO_CHANGE",
        priority_reason="no_change",
    )
    # 2단계 t=10.50: QM 오류(gear) 스냅샷: 타이머에 영향 없어야 함
    st = run(bench, 10.50, crash_status="PENDING", gear="X")
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
    # 3단계 t=11.00: 스냅샷 없음(기준 스냅샷 나이 0.50 s → STALE): 타이머에
    # 영향 없어야 함
    st = run_no_snapshot(bench, 11.00)
    check(
        st,
        3,
        lock_left="RELEASE",
        lock_right="RELEASE",
        state="DEGRADED",
        reason_code="INPUT_STALE",
        priority_reason="input_stale",
        input_validity="STALE",
    )
    # 4단계 t=12.05: 최초 PENDING으로부터 2.05 s: 막지 않음
    st = run(bench, 12.05, crash_status="PENDING", vehicle_speed_kph=3.0)
    check(
        st,
        4,
        lock_left="LOCK",
        lock_right="LOCK",
        state="NORMAL",
        reason_code="AUTO_LOCK",
        priority_reason="auto_lock",
        input_validity="VALID",
    )


def test_ftc_144_pending_to_none_unblocks(bench):
    """FTC-144 (SWR-008)

    PENDING→NONE 전환 평가에서 즉시 막힘이 풀려 자동 잠금이 적용되는지
    확인(수용기준). 막힘 해제 지연·잔존 결함 검출
    """
    # 1단계 t=10.00: PENDING 중 3.0 km/h: 막힘
    st = run(bench, 10.00, crash_status="PENDING", vehicle_speed_kph=3.0)
    check(
        st,
        1,
        lock_left="RELEASE",
        lock_right="RELEASE",
        reason_code="CRASH_PENDING",
        priority_reason="crash_pending",
    )
    # 2단계 t=10.05: NONE 수신: 막힘 해제
    st = run(bench, 10.05, vehicle_speed_kph=3.0)
    check(
        st,
        2,
        lock_left="LOCK",
        lock_right="LOCK",
        state="NORMAL",
        reason_code="AUTO_LOCK",
        priority_reason="auto_lock",
    )


def test_ftc_145_pending_keeps_existing_lock(bench):
    """FTC-145 (SWR-008)

    PENDING이 이미 LOCK인 출력을 RELEASE로 되돌리지 않는지 확인(막는 대상은
    RELEASE→LOCK 전환뿐). PENDING 시 잠금을 해제해 버리는 결함 검출 [제안
    케이스]

    비고: reason_left는 판정하지 않음(이 경우의 이유 코드는 원문에 없음, 질의
    Q-06).
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
    # 2단계 t=10.05: PENDING 중 ISOFIX true, 직전 LOCK
    st = run(bench, 10.05, crash_status="PENDING", isofix_left=True)
    check(st, 2, lock_left="LOCK", lock_right="LOCK")
