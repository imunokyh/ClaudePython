"""@brief SWE.6 기능 시험: 실행 모델·평가 시각·다중 스냅샷 (SWR-022).

근거: docs/swe6/system-test-cases.json
"""

from tests.system.harness import cmd
from tests.system.st_support import check, run, run_multi, run_no_snapshot


def test_ftc_158_evaluates_without_snapshot(bench):
    """FTC-158 (SWR-022, SWR-004)

    스냅샷이 없는 주기에도 평가가 수행되고 기준 스냅샷(3.0 km/h) 값으로
    판정되는지 확인(unlock이 자동 잠금에 막힘). 무스냅샷 주기를 건너뛰거나 차속
    0 기본값을 쓰는 결함 검출
    """
    # 1단계 t=10.00: 기준 스냅샷: 3.0 km/h
    st = run(bench, 10.00, vehicle_speed_kph=3.0)
    check(
        st,
        1,
        lock_left="LOCK",
        lock_right="LOCK",
        reason_code="AUTO_LOCK",
        priority_reason="auto_lock",
    )
    # 2단계 t=10.05: 스냅샷 없는 주기에 unlock만 제출
    st = run_no_snapshot(bench, 10.05, [cmd("left", "unlock")])
    check(
        st,
        2,
        lock_left="LOCK",
        lock_right="LOCK",
        state="NORMAL",
        reason_code="AUTO_LOCK",
        priority_reason="auto_lock",
        reason_left="AUTO_LOCK",
        reason_right="AUTO_LOCK",
        input_validity="VALID",
    )


def test_ftc_159_non_increasing_eval_time_invalid(bench):
    """FTC-159 (SWR-022, SWR-007)

    직전 정상 평가 시각과 같거나 이전인 평가 시각(9.95, 10.00 s)은
    INPUT_INVALID이고 그 평가의 CONFIRMED로 래치가 서지 않으며, 10.05 s에서
    정상 복귀하는지 확인(3-값 경계). 시각 비교 연산자(>=)·래치 선갱신 결함 검출
    """
    # 1단계 t=10.00: 정상 평가(직전 정상 평가 시각 = 10.00 s)
    st = run(bench, 10.00)
    check(
        st,
        1,
        lock_left="RELEASE",
        lock_right="RELEASE",
        reason_code="NO_CHANGE",
        priority_reason="no_change",
    )
    # 2단계 t=9.95: 평가 시각 9.95 s(직전보다 작음) + CONFIRMED
    st = run(bench, 9.95, crash_status="CONFIRMED")
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
    # 3단계 t=10.00: 평가 시각 10.00 s(직전과 같음) + CONFIRMED
    st = run(bench, 10.00, ts=10.0, crash_status="CONFIRMED")
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
    # 4단계 t=10.05: 평가 시각 10.05 s(직전 정상보다 큼): 정상 복귀, 래치 없음
    st = run(bench, 10.05, vehicle_speed_kph=3.0)
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


def test_ftc_160_large_time_jump_not_error(bench):
    """FTC-160 (SWR-022, SWR-013)

    평가 시각이 앞으로 크게 건너뛰어도 오류가 아니며(새 스냅샷이 있으면 VALID),
    스냅샷이 없으면 입력 지연(STALE)으로 판정되는지 확인. 큰 시각 점프를 오류로
    처리하는 결함과 지연 판정 누락 결함 검출
    """
    # 1단계 t=1000.00: 초기 상태에서 평가 시각이 0 근처가 아닌 1000.00 s로 크게
    # 건너뜀(첫 평가)
    st = run(bench, 1000.00, vehicle_speed_kph=3.0)
    check(
        st,
        1,
        lock_left="LOCK",
        lock_right="LOCK",
        state="NORMAL",
        reason_code="AUTO_LOCK",
        priority_reason="auto_lock",
        input_validity="VALID",
    )
    # 2단계 t=2000.00: 앞으로 1000 s 건너뜀 + 새 스냅샷(ts=2000.00, 지연 없음)
    st = run(bench, 2000.00, [cmd("all", "unlock")], vehicle_speed_kph=0.0)
    check(
        st,
        2,
        lock_left="RELEASE",
        lock_right="RELEASE",
        state="NORMAL",
        reason_code="DRIVER_COMMAND",
        priority_reason="driver_command",
        input_validity="VALID",
    )
    # 3단계 t=3000.00: 1000 s 건너뜀 + 스냅샷 없음: 입력 지연(STALE)
    st = run_no_snapshot(bench, 3000.00)
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


def test_ftc_161_confirmed_preferred_in_multi_snapshot(bench):
    """FTC-161 (SWR-022, SWR-007)

    한 주기에 CONFIRMED 스냅샷 뒤 NONE 스냅샷이 와도 CONFIRMED를 우선해 래치가
    서는지 확인(수용기준). 마지막 스냅샷만 쓰는 결함 검출
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
    # 2단계 t=10.05: 한 주기에 CONFIRMED 뒤 NONE
    st = run_multi(
        bench,
        10.05,
        {"crash_status": "CONFIRMED"},
        {"crash_status": "NONE", "vehicle_speed_kph": 3.0},
    )
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


def test_ftc_162_last_snapshot_used(bench):
    """FTC-162 (SWR-022)

    CONFIRMED가 없는 주기에 여러 스냅샷이 오면 마지막 것만 쓰고 나머지는
    버리는지 확인(순서를 바꿔 양방향). 첫 스냅샷 사용·평균/OR 병합 결함 검출
    """
    # 1단계 t=10.00
    st = run(bench, 10.00)
    check(
        st,
        1,
        lock_left="RELEASE",
        lock_right="RELEASE",
        reason_code="NO_CHANGE",
        priority_reason="no_change",
    )
    # 2단계 t=10.05: CONFIRMED 없는 주기: 마지막 스냅샷(0.0 km/h)만 사용
    st = run_multi(
        bench, 10.05, {"vehicle_speed_kph": 3.0}, {"vehicle_speed_kph": 0.0}
    )
    check(
        st,
        2,
        lock_left="RELEASE",
        lock_right="RELEASE",
        state="NORMAL",
        reason_code="NO_CHANGE",
        priority_reason="no_change",
    )
    # 3단계 t=10.10: 순서를 바꿔: 마지막 스냅샷(3.0 km/h) 사용
    st = run_multi(
        bench, 10.10, {"vehicle_speed_kph": 0.0}, {"vehicle_speed_kph": 3.0}
    )
    check(
        st,
        3,
        lock_left="LOCK",
        lock_right="LOCK",
        state="NORMAL",
        reason_code="AUTO_LOCK",
        priority_reason="auto_lock",
    )


def test_ftc_163_last_confirmed_used(bench):
    """FTC-163 (SWR-022, SWR-007)

    CONFIRMED가 여러 개이면 마지막 CONFIRMED를 써서(나이 0 s) 래치가 서는지
    확인. 첫 CONFIRMED를 쓰는 결함(나이 1.05 s로 래치 실패) 검출
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
    # 2단계 t=11.05: 한 주기에 CONFIRMED 2개: 첫 번째는 나이 1.05 s(래치 불가),
    # 마지막은 나이 0 s
    st = run_multi(
        bench,
        11.05,
        {"ts": 10.0, "crash_status": "CONFIRMED"},
        {"ts": 11.05, "crash_status": "CONFIRMED"},
    )
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


def test_ftc_164_time_error_keeps_pending_timer(bench):
    """FTC-164 (SWR-022, SWR-008)

    시각 오류 평가가 PENDING 타이머를 갱신(NONE으로 삭제)하지 않는지 확인. 오류
    평가에서도 타이머를 갱신하는 결함 검출
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
    # 2단계 t=9.00: 시각 역행(9.00 s) + NONE: 타이머를 지우면 안 됨
    st = run(bench, 9.00, crash_status="NONE")
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
    # 3단계 t=12.05: 최초 PENDING(10.00)으로부터 2.05 s: 막지 않음
    st = run(bench, 12.05, crash_status="PENDING", vehicle_speed_kph=3.0)
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


def test_ftc_165_time_error_keeps_override_history(bench):
    """FTC-165 (SWR-022, SWR-006)

    시각 오류 평가가 첫 억제·override 이력을 갱신하지 않는지 확인(그 평가의
    unlock이 기록되었다면 3단계가 override가 됨). 오류 평가의 override 이력
    갱신 결함 검출
    """
    # 1단계 t=10.05: 사전 설정(직전 정상 평가 시각 10.05 s)
    st = run(bench, 10.05, rear_left_approach_risk=True)
    check(
        st,
        1,
        lock_left="LOCK",
        reason_code="APPROACH_RISK",
        priority_reason="approach_risk",
    )
    # 2단계 t=10.00: 시각 역행 평가의 unlock: 첫 억제로 기록되면 안 됨
    st = run(
        bench,
        10.00,
        [cmd("left", "unlock")],
        ts=10.05,
        rear_left_approach_risk=True,
    )
    check(
        st,
        2,
        lock_left="LOCK",
        lock_right="RELEASE",
        state="DEGRADED",
        reason_code="INPUT_INVALID",
        priority_reason="input_invalid",
        input_validity="INVALID",
    )
    # 3단계 t=10.10: 정상 평가 첫 unlock: 첫 억제(override 아님)
    st = run(
        bench, 10.10, [cmd("left", "unlock")], rear_left_approach_risk=True
    )
    check(
        st,
        3,
        lock_left="LOCK",
        lock_right="RELEASE",
        state="NORMAL",
        reason_code="APPROACH_RISK",
        priority_reason="approach_risk",
        reason_left="APPROACH_RISK",
        input_validity="VALID",
    )
    # 4단계 t=10.15: 다음 unlock: override
    st = run(
        bench, 10.15, [cmd("left", "unlock")], rear_left_approach_risk=True
    )
    check(
        st,
        4,
        lock_left="RELEASE",
        state="OVERRIDE",
        reason_code="DRIVER_OVERRIDE",
        priority_reason="driver_override",
        reason_left="DRIVER_OVERRIDE",
    )


def test_ftc_166_time_error_keeps_reference_snapshot(bench):
    """FTC-166 (SWR-022, SWR-013)

    시각 오류 평가의 스냅샷이 기준 스냅샷을 갱신하지 않는지 확인(갱신되었다면
    3.0 km/h로 unlock이 막힘). 오류 평가의 기준 스냅샷 갱신 결함 검출
    """
    # 1단계 t=10.00: 사전 설정: 기준 스냅샷 S0(차속 0.0), 양쪽 LOCK
    st = run(bench, 10.00, [cmd("all", "lock")])
    check(
        st,
        1,
        lock_left="LOCK",
        lock_right="LOCK",
        reason_code="DRIVER_COMMAND",
        priority_reason="driver_command",
    )
    # 2단계 t=9.95: 시각 역행 평가에 차속 3.0 km/h 스냅샷: 기준 스냅샷이 되면
    # 안 됨
    st = run(bench, 9.95, ts=10.0, vehicle_speed_kph=3.0)
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
    # 3단계 t=10.05: 스냅샷 없는 주기: 기준 스냅샷은 1단계(0.0 km/h)이므로
    # unlock 적용
    st = run_no_snapshot(bench, 10.05, [cmd("left", "unlock")])
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


def test_ftc_167_time_error_keeps_latch(bench):
    """FTC-167 (SWR-022, SWR-007)

    시각 오류 평가에서는 기존 래치를 유지하고 해제 스냅샷을 무시하는지
    확인(수용기준 '기존 래치는 유지'). 시각 검사 전에 래치 해제를 처리하는 결함
    검출
    """
    # 1단계 t=10.00: 래치 성립
    st = run(bench, 10.00, crash_status="CONFIRMED", vehicle_speed_kph=3.0)
    check(
        st,
        1,
        lock_left="RELEASE",
        lock_right="RELEASE",
        state="NORMAL",
        reason_code="CRASH_CONFIRMED",
        priority_reason="crash_confirmed",
    )
    # 2단계 t=10.00: 평가 시각 10.00 s(직전과 같음): 해제 조건(시동 OFF,
    # NONE)의 스냅샷이지만 시각 오류 평가
    st = run(bench, 10.00, ignition_on=False)
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
    # 3단계 t=10.05: 정상 평가: 래치가 풀렸다면 자동 잠금이 됨
    st = run(bench, 10.05, vehicle_speed_kph=3.0)
    check(
        st,
        3,
        lock_left="RELEASE",
        lock_right="RELEASE",
        state="NORMAL",
        reason_code="CRASH_CONFIRMED",
        priority_reason="crash_confirmed",
        input_validity="VALID",
    )


def test_ftc_168_last_valid_time_updated_only_on_valid(bench):
    """FTC-168 (SWR-022)

    직전 정상 평가 시각이 정상 평가에서만 갱신되는지 확인(오류 평가 10.02 s 뒤
    10.03 s도 오류여야 함). 오류 평가에서 기준 시각을 갱신하는 결함 검출

    비고: 오류 평가 단계의 스냅샷 ts는 10.05(기준 스냅샷과 같음)로 두어
    타임스탬프 역행 오류와 겹치지 않게 함.
    """
    # 1단계 t=10.00: 직전 정상 평가 시각 10.00 s
    st = run(bench, 10.00)
    check(
        st,
        1,
        lock_left="RELEASE",
        lock_right="RELEASE",
        reason_code="NO_CHANGE",
        priority_reason="no_change",
    )
    # 2단계 t=10.05: 직전 정상 평가 시각 10.05 s
    st = run(bench, 10.05)
    check(
        st,
        2,
        lock_left="RELEASE",
        lock_right="RELEASE",
        reason_code="NO_CHANGE",
        priority_reason="no_change",
    )
    # 3단계 t=10.02: 평가 시각 10.02 s(< 10.05): 시각 오류
    st = run(bench, 10.02, ts=10.05)
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
    # 4단계 t=10.03: 평가 시각 10.03 s: 직전 정상(10.05)보다 작으므로 여전히
    # 오류(10.02보다는 큼)
    st = run(bench, 10.03, ts=10.05)
    check(
        st,
        4,
        lock_left="RELEASE",
        lock_right="RELEASE",
        state="DEGRADED",
        reason_code="INPUT_INVALID",
        priority_reason="input_invalid",
        input_validity="INVALID",
    )
    # 5단계 t=10.10: 평가 시각 10.10 s: 정상 복귀
    st = run(bench, 10.10)
    check(
        st,
        5,
        lock_left="RELEASE",
        lock_right="RELEASE",
        state="NORMAL",
        reason_code="NO_CHANGE",
        priority_reason="no_change",
        input_validity="VALID",
    )
