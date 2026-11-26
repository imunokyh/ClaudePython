"""@brief SWE.6 기능 시험: 후측방 접근위험·override·좌우 독립.

대상 요구사항: SWR-005, SWR-006, SWR-009.

근거: docs/swe6/system-test-cases.json
"""

import pytest
from tests.system.harness import cmd
from tests.system.st_support import Step, check, play, run


def test_ftc_108_approach_risk_locks_and_suppresses_unlock(bench):
    """FTC-108 (SWR-005)

    접근위험 true인 쪽이 LOCK(APPROACH_RISK)이 되고 첫 unlock이 억제되는지
    확인. 위험 입력이 반대쪽에 매핑되거나 unlock이 새는 결함 검출
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
    # 2단계 t=10.05: 위험 true가 된 평가
    st = run(bench, 10.05, rear_left_approach_risk=True)
    check(
        st,
        2,
        lock_left="LOCK",
        lock_right="RELEASE",
        state="NORMAL",
        reason_code="APPROACH_RISK",
        priority_reason="approach_risk",
        reason_left="APPROACH_RISK",
        reason_right="NO_CHANGE",
    )
    # 3단계 t=10.10: 첫 unlock
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
    )


def test_ftc_109_approach_risk_beats_all_qm_rules(bench):
    """FTC-109 (SWR-005, SWR-019)

    접근위험(ASIL B)이 시동 OFF·화재·과온·성인·QM 신호 오류·운전자 unlock이
    모두 겹쳐도 좌측 LOCK을 지키는지 확인(P-1 간섭 배제). QM 규칙 누수 결함
    검출
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
    # 2단계 t=10.05: 접근위험 + 시동 OFF + 화재·과온·성인 + QM 오류(gear) +
    # unlock 동시
    st = run(
        bench,
        10.05,
        [cmd("left", "unlock")],
        rear_left_approach_risk=True,
        ignition_on=False,
        fire_detected=True,
        overtemperature_detected=True,
        adult_present=True,
        gear="X",
    )
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


def test_ftc_110_risk_cleared_keeps_lock_then_unlock(bench):
    """FTC-110 (SWR-005)

    위험이 false가 되어도 출력은 LOCK 유지(NO_CHANGE), 이후 unlock은 억제 없이
    적용되는지 확인. 위험 해소 시 자동 해제 또는 억제 상태 잔존 결함 검출
    """
    # 1단계 t=10.00
    st = run(bench, 10.00, rear_left_approach_risk=True)
    check(
        st,
        1,
        lock_left="LOCK",
        lock_right="RELEASE",
        reason_code="APPROACH_RISK",
        priority_reason="approach_risk",
    )
    # 2단계 t=10.05: 위험 해소
    st = run(bench, 10.05, rear_left_approach_risk=False)
    check(
        st,
        2,
        lock_left="LOCK",
        lock_right="RELEASE",
        state="NORMAL",
        reason_code="NO_CHANGE",
        priority_reason="no_change",
        reason_left="NO_CHANGE",
        reason_right="NO_CHANGE",
    )
    # 3단계 t=10.10: 위험 해소 뒤 unlock은 정상 적용
    st = run(bench, 10.10, [cmd("left", "unlock")])
    check(
        st,
        3,
        lock_left="RELEASE",
        lock_right="RELEASE",
        state="NORMAL",
        reason_code="DRIVER_COMMAND",
        priority_reason="driver_command",
        reason_left="DRIVER_COMMAND",
    )


def test_ftc_111_override_at_exactly_10s(bench):
    """FTC-111 (SWR-006)

    첫 억제 후 정확히 10.0 s에 재입력하면 override(RELEASE, OVERRIDE)가 되는지,
    source가 달라도 되는지, override가 다음 평가에서 유지되는지 확인. 10.0 s
    경계의 < vs <= 오류와 부동소수 오차(20.10-10.10=10.000000000000002) 미처리
    결함 검출

    비고: 시각 쌍 10.10/20.10은 배정밀도 부동소수 뺄셈이 10.0보다 약간 커지는
    값을 의도적으로 선택함. 합격은 10.0 이하(<=)로 판정(SWR-006 원문).
    """
    # 1단계 t=10.05: 사전 설정: 좌 접근위험 LOCK
    st = run(bench, 10.05, rear_left_approach_risk=True)
    check(
        st,
        1,
        lock_left="LOCK",
        lock_right="RELEASE",
        state="NORMAL",
        reason_code="APPROACH_RISK",
        priority_reason="approach_risk",
    )
    # 2단계 t=10.10: 첫 억제 시각 = 10.10 s
    st = run(
        bench, 10.10, [cmd("left", "unlock")], rear_left_approach_risk=True
    )
    check(
        st,
        2,
        lock_left="LOCK",
        lock_right="RELEASE",
        state="NORMAL",
        reason_code="APPROACH_RISK",
        priority_reason="approach_risk",
        reason_left="APPROACH_RISK",
    )
    # 3단계 t=20.10: 재입력: 첫 억제로부터 정확히 10.00 s, source는 다름
    st = run(
        bench,
        20.10,
        [cmd("left", "unlock", "mobile_app")],
        rear_left_approach_risk=True,
    )
    check(
        st,
        3,
        lock_left="RELEASE",
        lock_right="RELEASE",
        state="OVERRIDE",
        reason_code="DRIVER_OVERRIDE",
        priority_reason="driver_override",
        reason_left="DRIVER_OVERRIDE",
        reason_right="NO_CHANGE",
        input_validity="VALID",
    )
    # 4단계 t=20.15: 명령 없는 다음 평가: override 유지
    st = run(bench, 20.15, rear_left_approach_risk=True)
    check(
        st,
        4,
        lock_left="RELEASE",
        lock_right="RELEASE",
        state="OVERRIDE",
        reason_code="DRIVER_OVERRIDE",
        priority_reason="driver_override",
        reason_left="DRIVER_OVERRIDE",
    )


def test_ftc_112_reentry_after_10s_is_new_suppression(bench):
    """FTC-112 (SWR-006)

    10.0 s를 0.05 s 넘긴 재입력은 override가 아니라 새로운 첫 억제로 기록되고,
    그 뒤 0.05 s 재입력이 override가 되는지 확인. 창 만료 후 이력 미갱신(영구
    첫 억제 유지) 결함 검출
    """
    # 1단계 t=10.05: 사전 설정
    st = run(bench, 10.05, rear_left_approach_risk=True)
    check(
        st,
        1,
        lock_left="LOCK",
        lock_right="RELEASE",
        reason_code="APPROACH_RISK",
        priority_reason="approach_risk",
    )
    # 2단계 t=10.10: 첫 억제 시각 10.10 s
    st = run(
        bench, 10.10, [cmd("left", "unlock")], rear_left_approach_risk=True
    )
    check(
        st,
        2,
        lock_left="LOCK",
        state="NORMAL",
        reason_code="APPROACH_RISK",
        priority_reason="approach_risk",
    )
    # 3단계 t=20.15: 10.05 s 경과: 재입력이지만 10.0 s 초과 → 새로운 첫 억제
    st = run(
        bench, 20.15, [cmd("left", "unlock")], rear_left_approach_risk=True
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
    )
    # 4단계 t=20.20: 새 첫 억제(20.15 s)로부터 0.05 s: override
    st = run(
        bench, 20.20, [cmd("left", "unlock")], rear_left_approach_risk=True
    )
    check(
        st,
        4,
        lock_left="RELEASE",
        lock_right="RELEASE",
        state="OVERRIDE",
        reason_code="DRIVER_OVERRIDE",
        priority_reason="driver_override",
        reason_left="DRIVER_OVERRIDE",
    )


def test_ftc_113_duplicate_unlock_same_eval_not_reentry(bench):
    """FTC-113 (SWR-006, SWR-002)

    같은 평가 안의 중복 unlock은 재입력이 아니며(override 아님), 그 평가가 첫
    억제로 기록되어 이후 평가의 unlock 1개로 override가 되는지 확인. 평가 안
    중복을 재입력으로 세는 결함 검출
    """
    # 1단계 t=10.05: 사전 설정
    st = run(bench, 10.05, rear_left_approach_risk=True)
    check(
        st,
        1,
        lock_left="LOCK",
        reason_code="APPROACH_RISK",
        priority_reason="approach_risk",
    )
    # 2단계 t=10.10: 한 평가에 같은 쪽 unlock 2개
    st = run(
        bench,
        10.10,
        [cmd("left", "unlock"), cmd("left", "unlock", "voice")],
        rear_left_approach_risk=True,
    )
    check(
        st,
        2,
        lock_left="LOCK",
        lock_right="RELEASE",
        state="NORMAL",
        reason_code="APPROACH_RISK",
        priority_reason="approach_risk",
        reason_left="APPROACH_RISK",
    )
    # 3단계 t=11.10: 다음 평가의 unlock 1개: 재입력
    st = run(
        bench, 11.10, [cmd("left", "unlock")], rear_left_approach_risk=True
    )
    check(
        st,
        3,
        lock_left="RELEASE",
        state="OVERRIDE",
        reason_code="DRIVER_OVERRIDE",
        priority_reason="driver_override",
        reason_left="DRIVER_OVERRIDE",
    )


def test_ftc_114_all_unlock_overrides_both_sides(bench):
    """FTC-114 (SWR-006)

    all unlock이 양쪽 재입력으로 처리되어 두 쪽이 모두 override가 되는지 확인.
    all을 한쪽에만 적용하거나 첫 억제를 쪽별로 기록하지 않는 결함 검출
    """
    # 1단계 t=10.05: 사전 설정: 양쪽 접근위험
    st = run(
        bench,
        10.05,
        rear_left_approach_risk=True,
        rear_right_approach_risk=True,
    )
    check(
        st,
        1,
        lock_left="LOCK",
        lock_right="LOCK",
        reason_code="APPROACH_RISK",
        priority_reason="approach_risk",
        reason_left="APPROACH_RISK",
        reason_right="APPROACH_RISK",
    )
    # 2단계 t=10.10: all unlock: 양쪽 첫 억제
    st = run(
        bench,
        10.10,
        [cmd("all", "unlock")],
        rear_left_approach_risk=True,
        rear_right_approach_risk=True,
    )
    check(
        st,
        2,
        lock_left="LOCK",
        lock_right="LOCK",
        state="NORMAL",
        reason_code="APPROACH_RISK",
        priority_reason="approach_risk",
    )
    # 3단계 t=10.15: all unlock 재입력: 양쪽 재입력으로 간주
    st = run(
        bench,
        10.15,
        [cmd("all", "unlock", "avn")],
        rear_left_approach_risk=True,
        rear_right_approach_risk=True,
    )
    check(
        st,
        3,
        lock_left="RELEASE",
        lock_right="RELEASE",
        state="OVERRIDE",
        reason_code="DRIVER_OVERRIDE",
        priority_reason="driver_override",
        reason_left="DRIVER_OVERRIDE",
        reason_right="DRIVER_OVERRIDE",
    )


def test_ftc_115_override_at_2_99kph(bench):
    """FTC-115 (SWR-006)

    override 성립 차속 경계 직하(2.99 km/h)에서 재입력이 override가 되는지
    확인. 경계를 <= 로 구현하거나 차속을 반올림하는 결함 검출(상위 경계 3.0은
    FTC-116)
    """
    # 1단계 t=10.05: 사전 설정
    st = run(bench, 10.05, rear_left_approach_risk=True)
    check(
        st,
        1,
        lock_left="LOCK",
        reason_code="APPROACH_RISK",
        priority_reason="approach_risk",
    )
    # 2단계 t=10.10: 차속 0.0 km/h 첫 억제
    st = run(
        bench, 10.10, [cmd("left", "unlock")], rear_left_approach_risk=True
    )
    check(
        st,
        2,
        lock_left="LOCK",
        state="NORMAL",
        reason_code="APPROACH_RISK",
        priority_reason="approach_risk",
    )
    # 3단계 t=10.15: 2.99 km/h 재입력
    st = run(
        bench,
        10.15,
        [cmd("left", "unlock")],
        rear_left_approach_risk=True,
        vehicle_speed_kph=2.99,
    )
    check(
        st,
        3,
        lock_left="RELEASE",
        lock_right="RELEASE",
        state="OVERRIDE",
        reason_code="DRIVER_OVERRIDE",
        priority_reason="driver_override",
        reason_left="DRIVER_OVERRIDE",
    )


def test_ftc_116_no_override_at_3kph_clears_history(bench):
    """FTC-116 (SWR-006, SWR-004)

    3.0 km/h에서의 재입력은 override가 아니며(LOCK), 이 때 첫 억제 기록이
    지워져 차속이 다시 내려가도 이전 억제가 재입력으로 쓰이지 않는지 확인. 차속
    경계(3.0)와 '종료 조건에서 기록 삭제' 결함 검출
    """
    # 1단계 t=10.05: 사전 설정
    st = run(bench, 10.05, rear_left_approach_risk=True)
    check(
        st,
        1,
        lock_left="LOCK",
        lock_right="RELEASE",
        reason_code="APPROACH_RISK",
        priority_reason="approach_risk",
    )
    # 2단계 t=10.10: 2.9 km/h 첫 억제(기록됨)
    st = run(
        bench,
        10.10,
        [cmd("left", "unlock")],
        rear_left_approach_risk=True,
        vehicle_speed_kph=2.9,
    )
    check(
        st,
        2,
        lock_left="LOCK",
        lock_right="RELEASE",
        state="NORMAL",
        reason_code="APPROACH_RISK",
        priority_reason="approach_risk",
    )
    # 3단계 t=10.15: 3.0 km/h 재입력: override 아님, 기록 삭제
    st = run(
        bench,
        10.15,
        [cmd("left", "unlock")],
        rear_left_approach_risk=True,
        vehicle_speed_kph=3.0,
    )
    check(
        st,
        3,
        lock_left="LOCK",
        lock_right="LOCK",
        state="NORMAL",
        reason_code="APPROACH_RISK",
        priority_reason="approach_risk",
        reason_left="APPROACH_RISK",
        reason_right="AUTO_LOCK",
    )
    # 4단계 t=10.20: 2.9 km/h unlock: 삭제된 기록이므로 새 첫 억제(override
    # 아님)
    st = run(
        bench,
        10.20,
        [cmd("left", "unlock")],
        rear_left_approach_risk=True,
        vehicle_speed_kph=2.9,
    )
    check(
        st,
        4,
        lock_left="LOCK",
        lock_right="LOCK",
        state="NORMAL",
        reason_code="APPROACH_RISK",
        priority_reason="approach_risk",
        reason_left="APPROACH_RISK",
        reason_right="NO_CHANGE",
    )
    # 5단계 t=10.25: 새 첫 억제 후 재입력: override
    st = run(
        bench,
        10.25,
        [cmd("left", "unlock")],
        rear_left_approach_risk=True,
        vehicle_speed_kph=2.9,
    )
    check(
        st,
        5,
        lock_left="RELEASE",
        lock_right="LOCK",
        state="OVERRIDE",
        reason_code="DRIVER_OVERRIDE",
        priority_reason="driver_override",
        reason_left="DRIVER_OVERRIDE",
        reason_right="NO_CHANGE",
    )


def test_ftc_117_override_ends_at_3kph(bench):
    """FTC-117 (SWR-006)

    override 중 차속이 3.0 km/h가 되면 그 쪽이 LOCK이 되고, 차속이 다시 0.0이
    되어도 override가 되살아나지 않는지 확인. 종료 조건 미처리·종료 후 재개
    결함 검출
    """
    # 1단계 t=10.05: 사전 설정
    st = run(bench, 10.05, rear_left_approach_risk=True)
    check(
        st,
        1,
        lock_left="LOCK",
        lock_right="RELEASE",
        reason_code="APPROACH_RISK",
        priority_reason="approach_risk",
    )
    # 2단계 t=10.10: 첫 억제
    st = run(
        bench, 10.10, [cmd("left", "unlock")], rear_left_approach_risk=True
    )
    check(
        st,
        2,
        lock_left="LOCK",
        state="NORMAL",
        reason_code="APPROACH_RISK",
        priority_reason="approach_risk",
    )
    # 3단계 t=10.15: 재입력: override 성립
    st = run(
        bench, 10.15, [cmd("left", "unlock")], rear_left_approach_risk=True
    )
    check(
        st,
        3,
        lock_left="RELEASE",
        lock_right="RELEASE",
        state="OVERRIDE",
        reason_code="DRIVER_OVERRIDE",
        priority_reason="driver_override",
        reason_left="DRIVER_OVERRIDE",
    )
    # 4단계 t=10.20: override 중 차속 3.0 km/h: 종료
    st = run(bench, 10.20, rear_left_approach_risk=True, vehicle_speed_kph=3.0)
    check(
        st,
        4,
        lock_left="LOCK",
        lock_right="LOCK",
        state="NORMAL",
        reason_code="APPROACH_RISK",
        priority_reason="approach_risk",
        reason_left="APPROACH_RISK",
        reason_right="AUTO_LOCK",
    )
    # 5단계 t=10.25: 차속 0.0 km/h 복귀: override 재개 없음
    st = run(bench, 10.25, rear_left_approach_risk=True, vehicle_speed_kph=0.0)
    check(
        st,
        5,
        lock_left="LOCK",
        lock_right="LOCK",
        state="NORMAL",
        reason_code="APPROACH_RISK",
        priority_reason="approach_risk",
        reason_left="APPROACH_RISK",
        reason_right="NO_CHANGE",
    )


def test_ftc_118_override_ends_when_risk_clears(bench):
    """FTC-118 (SWR-006, SWR-005)

    위험이 false가 되면 override가 끝나 RELEASE 유지(NO_CHANGE), 위험이 다시
    true가 되면 override 없이 LOCK이 되는지 확인. override 종료 미처리(위험
    재발 시 RELEASE 지속) 결함 검출
    """
    # 1단계 t=10.05: 사전 설정
    st = run(bench, 10.05, rear_left_approach_risk=True)
    check(
        st,
        1,
        lock_left="LOCK",
        lock_right="RELEASE",
        reason_code="APPROACH_RISK",
        priority_reason="approach_risk",
    )
    # 2단계 t=10.10: 첫 억제
    st = run(
        bench, 10.10, [cmd("left", "unlock")], rear_left_approach_risk=True
    )
    check(
        st,
        2,
        lock_left="LOCK",
        state="NORMAL",
        reason_code="APPROACH_RISK",
        priority_reason="approach_risk",
    )
    # 3단계 t=10.15: 재입력: override 성립
    st = run(
        bench, 10.15, [cmd("left", "unlock")], rear_left_approach_risk=True
    )
    check(
        st,
        3,
        lock_left="RELEASE",
        lock_right="RELEASE",
        state="OVERRIDE",
        reason_code="DRIVER_OVERRIDE",
        priority_reason="driver_override",
        reason_left="DRIVER_OVERRIDE",
    )
    # 4단계 t=10.20: 위험 false: override 종료, 출력은 직전 유지(RELEASE)
    st = run(bench, 10.20)
    check(
        st,
        4,
        lock_left="RELEASE",
        lock_right="RELEASE",
        state="NORMAL",
        reason_code="NO_CHANGE",
        priority_reason="no_change",
        reason_left="NO_CHANGE",
    )
    # 5단계 t=10.25: 위험 true 재발생: override 없이 새로 LOCK
    st = run(bench, 10.25, rear_left_approach_risk=True)
    check(
        st,
        5,
        lock_left="LOCK",
        lock_right="RELEASE",
        state="NORMAL",
        reason_code="APPROACH_RISK",
        priority_reason="approach_risk",
        reason_left="APPROACH_RISK",
    )


def test_ftc_119_override_ends_on_ignition_off(bench):
    """FTC-119 (SWR-006, SWR-020)

    override 중 시동 OFF가 되면 override가 끝나(좌 LOCK, state=OFF), 시동 ON
    복귀 후 위험이 true여도 override가 아닌 LOCK인지 확인. 시동 OFF 종료 조건
    누락 결함 검출
    """
    # 1단계 t=10.05: 사전 설정
    st = run(bench, 10.05, rear_left_approach_risk=True)
    check(
        st,
        1,
        lock_left="LOCK",
        lock_right="RELEASE",
        reason_code="APPROACH_RISK",
        priority_reason="approach_risk",
    )
    # 2단계 t=10.10: 첫 억제
    st = run(
        bench, 10.10, [cmd("left", "unlock")], rear_left_approach_risk=True
    )
    check(
        st,
        2,
        lock_left="LOCK",
        state="NORMAL",
        reason_code="APPROACH_RISK",
        priority_reason="approach_risk",
    )
    # 3단계 t=10.15: 재입력: override 성립
    st = run(
        bench, 10.15, [cmd("left", "unlock")], rear_left_approach_risk=True
    )
    check(
        st,
        3,
        lock_left="RELEASE",
        lock_right="RELEASE",
        state="OVERRIDE",
        reason_code="DRIVER_OVERRIDE",
        priority_reason="driver_override",
        reason_left="DRIVER_OVERRIDE",
    )
    # 4단계 t=10.20: 시동 OFF: override 종료, 접근위험 LOCK이 이김
    st = run(bench, 10.20, rear_left_approach_risk=True, ignition_on=False)
    check(
        st,
        4,
        lock_left="LOCK",
        lock_right="RELEASE",
        state="OFF",
        reason_code="APPROACH_RISK",
        priority_reason="approach_risk",
        reason_left="APPROACH_RISK",
        reason_right="IGNITION_OFF",
    )
    # 5단계 t=10.25: 시동 ON 복귀 + 위험 true: override 재개 없음
    st = run(bench, 10.25, rear_left_approach_risk=True)
    check(
        st,
        5,
        lock_left="LOCK",
        lock_right="RELEASE",
        state="NORMAL",
        reason_code="APPROACH_RISK",
        priority_reason="approach_risk",
        reason_left="APPROACH_RISK",
    )


def test_ftc_120_sensor_fault_unlock_not_counted(bench):
    """FTC-120 (SWR-006, SWR-021)

    순위 3(sensor fault) 평가의 unlock이 첫 억제로 기록되지 않아, 복귀 후
    unlock 한 번으로는 override가 되지 않는지 확인. 순위 3 평가 명령을 override
    계수에 넣는 결함 검출
    """
    # 1단계 t=10.05: 사전 설정
    st = run(bench, 10.05, rear_left_approach_risk=True)
    check(
        st,
        1,
        lock_left="LOCK",
        reason_code="APPROACH_RISK",
        priority_reason="approach_risk",
    )
    # 2단계 t=10.10: sensor fault 중 unlock: 첫 억제로 세지 않음
    st = run(
        bench,
        10.10,
        [cmd("left", "unlock")],
        rear_left_approach_risk=True,
        sensor_fault=True,
    )
    check(
        st,
        2,
        lock_left="LOCK",
        lock_right="RELEASE",
        state="FAULT",
        reason_code="SENSOR_FAULT",
        priority_reason="sensor_fault",
        reason_left="SENSOR_FAULT",
        warning_code="W_SENSOR_FAULT",
    )
    # 3단계 t=10.15: 복귀 후 첫 unlock: 첫 억제(override 아님)
    st = run(
        bench, 10.15, [cmd("left", "unlock")], rear_left_approach_risk=True
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
        warning_code="NONE",
    )
    # 4단계 t=10.20: 그 다음 unlock: override
    st = run(
        bench, 10.20, [cmd("left", "unlock")], rear_left_approach_risk=True
    )
    check(
        st,
        4,
        lock_left="RELEASE",
        lock_right="RELEASE",
        state="OVERRIDE",
        reason_code="DRIVER_OVERRIDE",
        priority_reason="driver_override",
        reason_left="DRIVER_OVERRIDE",
    )


def test_ftc_121_asil_b_error_unlock_not_counted(bench):
    """FTC-121 (SWR-006, SWR-013)

    순위 2(ASIL B 입력 오류) 평가의 unlock이 override 계수에서 제외되는지
    확인(FTC-120과 다른 순위 경로). 입력 오류 평가의 명령 누수 결함 검출
    """
    # 1단계 t=10.05: 사전 설정
    st = run(bench, 10.05, rear_left_approach_risk=True)
    check(
        st,
        1,
        lock_left="LOCK",
        reason_code="APPROACH_RISK",
        priority_reason="approach_risk",
    )
    # 2단계 t=10.10: ASIL B 신호 오류(순위 2) 평가의 unlock: 첫 억제로 세지
    # 않음
    st = run(
        bench,
        10.10,
        [cmd("left", "unlock")],
        rear_left_approach_risk=True,
        rear_right_approach_risk=1,
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
    # 3단계 t=10.15: 유효 평가 첫 unlock: 첫 억제(override 아님)
    st = run(
        bench, 10.15, [cmd("left", "unlock")], rear_left_approach_risk=True
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
    # 4단계 t=10.20: 다음 unlock: override
    st = run(
        bench, 10.20, [cmd("left", "unlock")], rear_left_approach_risk=True
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


def test_ftc_122_override_window_uses_source_timestamp(bench):
    """FTC-122 (SWR-006, SWR-022)

    override 창 판정이 평가 시각이 아니라 쓰는 스냅샷의 source_timestamp_s(명령
    시각)로 이루어지는지 확인. 평가 시각을 쓰면 9.95 s로 보아 잘못 override가
    되는 결함 검출

    비고: 두 스냅샷의 나이는 0.15 s, 0.05 s로 0.200 s 이내(정상 판정).
    """
    # 1단계 t=10.05: 사전 설정
    st = run(bench, 10.05, rear_left_approach_risk=True)
    check(
        st,
        1,
        lock_left="LOCK",
        reason_code="APPROACH_RISK",
        priority_reason="approach_risk",
    )
    # 2단계 t=20.15: 스냅샷 ts=20.00(지연 0.15 s, 정상): 명령 시각은 20.00 s
    st = run(
        bench,
        20.15,
        [cmd("left", "unlock")],
        ts=20.0,
        rear_left_approach_risk=True,
    )
    check(
        st,
        2,
        lock_left="LOCK",
        lock_right="RELEASE",
        state="NORMAL",
        reason_code="APPROACH_RISK",
        priority_reason="approach_risk",
        input_validity="VALID",
    )
    # 3단계 t=30.10: ts=30.05: 명령 시각 30.05 s, 첫 억제로부터 10.05 s →
    # override 아님(평가 시각 기준이면 9.95 s로 override가 됨)
    st = run(
        bench,
        30.10,
        [cmd("left", "unlock")],
        ts=30.05,
        rear_left_approach_risk=True,
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


def test_ftc_123_lock_ignored_during_override(bench):
    """FTC-123 (SWR-006, SWR-019)

    override 활성 중 운전자 lock(순위 10)이 순위 4 override 결과(RELEASE)를
    바꾸지 못하는지 확인. 명시 요구가 없어 1.4절 순위(4 > 10)에서 도출한 기대값
    [제안 케이스]

    비고: 가정: override 중 lock 명령은 순위 4가 이겨 무시된다(질의 Q-07).
    """
    # 1단계 t=10.05: 사전 설정
    st = run(bench, 10.05, rear_left_approach_risk=True)
    check(
        st,
        1,
        lock_left="LOCK",
        lock_right="RELEASE",
        reason_code="APPROACH_RISK",
        priority_reason="approach_risk",
    )
    # 2단계 t=10.10: 첫 억제
    st = run(
        bench, 10.10, [cmd("left", "unlock")], rear_left_approach_risk=True
    )
    check(
        st,
        2,
        lock_left="LOCK",
        state="NORMAL",
        reason_code="APPROACH_RISK",
        priority_reason="approach_risk",
    )
    # 3단계 t=10.15: 재입력: override 성립
    st = run(
        bench, 10.15, [cmd("left", "unlock")], rear_left_approach_risk=True
    )
    check(
        st,
        3,
        lock_left="RELEASE",
        lock_right="RELEASE",
        state="OVERRIDE",
        reason_code="DRIVER_OVERRIDE",
        priority_reason="driver_override",
        reason_left="DRIVER_OVERRIDE",
    )
    # 4단계 t=10.20: override 중 같은 쪽 lock 명령
    st = run(bench, 10.20, [cmd("left", "lock")], rear_left_approach_risk=True)
    check(
        st,
        4,
        lock_left="RELEASE",
        lock_right="RELEASE",
        state="OVERRIDE",
        reason_code="DRIVER_OVERRIDE",
        priority_reason="driver_override",
        reason_left="DRIVER_OVERRIDE",
    )


def test_ftc_124_left_risk_does_not_affect_right(bench):
    """FTC-124 (SWR-009, SWR-005)

    좌측 위험이 우측 출력에 영향을 주지 않는지(우측 unlock은 정상 적용) 확인.
    위험 억제를 양쪽에 걸거나 공유 플래그를 쓰는 결함 검출
    """
    # 1단계 t=10.00: 사전 설정: 양쪽 LOCK
    st = run(bench, 10.00, [cmd("all", "lock")])
    check(
        st,
        1,
        lock_left="LOCK",
        lock_right="LOCK",
        reason_code="DRIVER_COMMAND",
        priority_reason="driver_command",
    )
    # 2단계 t=10.05: 좌 위험 + all unlock
    st = run(bench, 10.05, [cmd("all", "unlock")], rear_left_approach_risk=True)
    check(
        st,
        2,
        lock_left="LOCK",
        lock_right="RELEASE",
        state="NORMAL",
        reason_code="APPROACH_RISK",
        priority_reason="approach_risk",
        reason_left="APPROACH_RISK",
        reason_right="DRIVER_COMMAND",
    )


def test_ftc_125_override_history_per_side(bench):
    """FTC-125 (SWR-009, SWR-006)

    첫 억제 이력과 override가 쪽별로 독립인지 확인(좌 override 중 우 unlock
    1회는 override가 아님). 좌·우 이력 공유 결함 검출
    """
    # 1단계 t=10.05: 사전 설정: 양쪽 접근위험
    st = run(
        bench,
        10.05,
        rear_left_approach_risk=True,
        rear_right_approach_risk=True,
    )
    check(
        st,
        1,
        lock_left="LOCK",
        lock_right="LOCK",
        reason_code="APPROACH_RISK",
        priority_reason="approach_risk",
    )
    # 2단계 t=10.10: 좌 첫 억제
    st = run(
        bench,
        10.10,
        [cmd("left", "unlock")],
        rear_left_approach_risk=True,
        rear_right_approach_risk=True,
    )
    check(
        st,
        2,
        lock_left="LOCK",
        lock_right="LOCK",
        state="NORMAL",
        reason_code="APPROACH_RISK",
        priority_reason="approach_risk",
    )
    # 3단계 t=10.15: 좌 override
    st = run(
        bench,
        10.15,
        [cmd("left", "unlock")],
        rear_left_approach_risk=True,
        rear_right_approach_risk=True,
    )
    check(
        st,
        3,
        lock_left="RELEASE",
        lock_right="LOCK",
        state="OVERRIDE",
        reason_code="DRIVER_OVERRIDE",
        priority_reason="driver_override",
        reason_left="DRIVER_OVERRIDE",
        reason_right="APPROACH_RISK",
    )
    # 4단계 t=10.20: 우 첫 억제: 좌 override가 우 억제를 풀지 않음(override
    # 아님)
    st = run(
        bench,
        10.20,
        [cmd("right", "unlock")],
        rear_left_approach_risk=True,
        rear_right_approach_risk=True,
    )
    check(
        st,
        4,
        lock_left="RELEASE",
        lock_right="LOCK",
        state="OVERRIDE",
        reason_code="DRIVER_OVERRIDE",
        priority_reason="driver_override",
        reason_left="DRIVER_OVERRIDE",
        reason_right="APPROACH_RISK",
    )
    # 5단계 t=10.25: 우 override
    st = run(
        bench,
        10.25,
        [cmd("right", "unlock")],
        rear_left_approach_risk=True,
        rear_right_approach_risk=True,
    )
    check(
        st,
        5,
        lock_left="RELEASE",
        lock_right="RELEASE",
        state="OVERRIDE",
        reason_code="DRIVER_OVERRIDE",
        priority_reason="driver_override",
        reason_left="DRIVER_OVERRIDE",
        reason_right="DRIVER_OVERRIDE",
    )


def test_ftc_126_left_override_with_right_isofix(bench):
    """FTC-126 (SWR-009, SWR-006, SWR-018)

    좌 override와 우 ISOFIX가 같은 평가에 있을 때 좌 RELEASE(DRIVER_OVERRIDE),
    우 LOCK(ISOFIX), reason_code=DRIVER_OVERRIDE, state=OVERRIDE인지
    확인(수용기준 직접 검증). 쪽별 혼합 처리 결함 검출
    """
    # 1단계 t=10.00: 사전 설정: 좌 접근위험, 우 ISOFIX
    st = run(bench, 10.00, rear_left_approach_risk=True, isofix_right=True)
    check(
        st,
        1,
        lock_left="LOCK",
        lock_right="LOCK",
        state="NORMAL",
        reason_code="APPROACH_RISK",
        priority_reason="approach_risk",
        reason_left="APPROACH_RISK",
        reason_right="ISOFIX",
    )
    # 2단계 t=10.05: 좌 첫 억제
    st = run(
        bench,
        10.05,
        [cmd("left", "unlock")],
        rear_left_approach_risk=True,
        isofix_right=True,
    )
    check(
        st,
        2,
        lock_left="LOCK",
        lock_right="LOCK",
        reason_code="APPROACH_RISK",
        priority_reason="approach_risk",
    )
    # 3단계 t=10.10: 좌 override + 우 ISOFIX 동시
    st = run(
        bench,
        10.10,
        [cmd("left", "unlock")],
        rear_left_approach_risk=True,
        isofix_right=True,
    )
    check(
        st,
        3,
        lock_left="RELEASE",
        lock_right="LOCK",
        state="OVERRIDE",
        reason_code="DRIVER_OVERRIDE",
        priority_reason="driver_override",
        reason_left="DRIVER_OVERRIDE",
        reason_right="ISOFIX",
    )


PW03_CASES = [
    # FTC-PW03-01 (SWR-009, SWR-005, SWR-018, SWR-003, SWR-004) PICT-03#1:
    # 좌/우 접근위험·ISOFIX·명령·차속 조합에서 쪽별 독립 판정과 reason_code
    # 선택(순위 높은 쪽, 동순위는 좌측) 검증. 좌우 혼동·공유 상태 결함 검출
    pytest.param(
        [
            Step(
                10.00,
                cmds=[cmd("left", "lock")],
                expect=dict(
                    lock_left="LOCK",
                    lock_right="RELEASE",
                    reason_left="DRIVER_COMMAND",
                    reason_right="NO_CHANGE",
                ),
            ),
            Step(
                10.05,
                sig=dict(rear_right_approach_risk=True, isofix_right=True),
                cmds=[cmd("all", "unlock", "avn")],
                expect=dict(
                    lock_left="RELEASE",
                    lock_right="LOCK",
                    state="NORMAL",
                    reason_code="APPROACH_RISK",
                    priority_reason="approach_risk",
                    reason_left="DRIVER_COMMAND",
                    reason_right="APPROACH_RISK",
                    input_validity="VALID",
                    warning_code="NONE",
                ),
            ),
        ],
        id="FTC-PW03-01",
    ),
    # FTC-PW03-02 (SWR-009, SWR-005, SWR-018, SWR-003, SWR-004) PICT-03#2:
    # 좌/우 접근위험·ISOFIX·명령·차속 조합에서 쪽별 독립 판정과 reason_code
    # 선택(순위 높은 쪽, 동순위는 좌측) 검증. 좌우 혼동·공유 상태 결함 검출
    pytest.param(
        [
            Step(
                10.00,
                cmds=[cmd("left", "lock")],
                expect=dict(
                    lock_left="LOCK",
                    lock_right="RELEASE",
                    reason_left="DRIVER_COMMAND",
                    reason_right="NO_CHANGE",
                ),
            ),
            Step(
                10.05,
                sig=dict(
                    rear_left_approach_risk=True,
                    isofix_left=True,
                    vehicle_speed_kph=3.0,
                ),
                cmds=[cmd("left", "lock", "voice")],
                expect=dict(
                    lock_left="LOCK",
                    lock_right="LOCK",
                    state="NORMAL",
                    reason_code="APPROACH_RISK",
                    priority_reason="approach_risk",
                    reason_left="APPROACH_RISK",
                    reason_right="AUTO_LOCK",
                    input_validity="VALID",
                    warning_code="NONE",
                ),
            ),
        ],
        id="FTC-PW03-02",
    ),
    # FTC-PW03-03 (SWR-009, SWR-005, SWR-018, SWR-003, SWR-004) PICT-03#3:
    # 좌/우 접근위험·ISOFIX·명령·차속 조합에서 쪽별 독립 판정과 reason_code
    # 선택(순위 높은 쪽, 동순위는 좌측) 검증. 좌우 혼동·공유 상태 결함 검출
    pytest.param(
        [
            Step(
                10.00,
                cmds=[cmd("left", "lock")],
                expect=dict(
                    lock_left="LOCK",
                    lock_right="RELEASE",
                    reason_left="DRIVER_COMMAND",
                    reason_right="NO_CHANGE",
                ),
            ),
            Step(
                10.05,
                sig=dict(rear_left_approach_risk=True),
                cmds=[cmd("right", "lock", "mobile_app")],
                expect=dict(
                    lock_left="LOCK",
                    lock_right="LOCK",
                    state="NORMAL",
                    reason_code="APPROACH_RISK",
                    priority_reason="approach_risk",
                    reason_left="APPROACH_RISK",
                    reason_right="DRIVER_COMMAND",
                    input_validity="VALID",
                    warning_code="NONE",
                ),
            ),
        ],
        id="FTC-PW03-03",
    ),
    # FTC-PW03-04 (SWR-009, SWR-005, SWR-018, SWR-003, SWR-004) PICT-03#4:
    # 좌/우 접근위험·ISOFIX·명령·차속 조합에서 쪽별 독립 판정과 reason_code
    # 선택(순위 높은 쪽, 동순위는 좌측) 검증. 좌우 혼동·공유 상태 결함 검출
    pytest.param(
        [
            Step(
                10.00,
                cmds=[cmd("left", "lock")],
                expect=dict(
                    lock_left="LOCK",
                    lock_right="RELEASE",
                    reason_left="DRIVER_COMMAND",
                    reason_right="NO_CHANGE",
                ),
            ),
            Step(
                10.05,
                sig=dict(
                    rear_right_approach_risk=True,
                    isofix_left=True,
                    isofix_right=True,
                    vehicle_speed_kph=3.0,
                ),
                cmds=[cmd("left", "unlock")],
                expect=dict(
                    lock_left="LOCK",
                    lock_right="LOCK",
                    state="NORMAL",
                    reason_code="APPROACH_RISK",
                    priority_reason="approach_risk",
                    reason_left="ISOFIX",
                    reason_right="APPROACH_RISK",
                    input_validity="VALID",
                    warning_code="NONE",
                ),
            ),
        ],
        id="FTC-PW03-04",
    ),
    # FTC-PW03-05 (SWR-009, SWR-005, SWR-018, SWR-003, SWR-004) PICT-03#5:
    # 좌/우 접근위험·ISOFIX·명령·차속 조합에서 쪽별 독립 판정과 reason_code
    # 선택(순위 높은 쪽, 동순위는 좌측) 검증. 좌우 혼동·공유 상태 결함 검출
    pytest.param(
        [
            Step(
                10.00,
                cmds=[cmd("left", "lock")],
                expect=dict(
                    lock_left="LOCK",
                    lock_right="RELEASE",
                    reason_left="DRIVER_COMMAND",
                    reason_right="NO_CHANGE",
                ),
            ),
            Step(
                10.05,
                sig=dict(
                    rear_left_approach_risk=True,
                    rear_right_approach_risk=True,
                    isofix_left=True,
                    isofix_right=True,
                ),
                expect=dict(
                    lock_left="LOCK",
                    lock_right="LOCK",
                    state="NORMAL",
                    reason_code="APPROACH_RISK",
                    priority_reason="approach_risk",
                    reason_left="APPROACH_RISK",
                    reason_right="APPROACH_RISK",
                    input_validity="VALID",
                    warning_code="NONE",
                ),
            ),
        ],
        id="FTC-PW03-05",
    ),
    # FTC-PW03-06 (SWR-009, SWR-005, SWR-018, SWR-003, SWR-004) PICT-03#6:
    # 좌/우 접근위험·ISOFIX·명령·차속 조합에서 쪽별 독립 판정과 reason_code
    # 선택(순위 높은 쪽, 동순위는 좌측) 검증. 좌우 혼동·공유 상태 결함 검출
    pytest.param(
        [
            Step(
                10.00,
                cmds=[cmd("left", "lock")],
                expect=dict(
                    lock_left="LOCK",
                    lock_right="RELEASE",
                    reason_left="DRIVER_COMMAND",
                    reason_right="NO_CHANGE",
                ),
            ),
            Step(
                10.05,
                sig=dict(rear_right_approach_risk=True, isofix_left=True),
                cmds=[cmd("all", "lock", "voice")],
                expect=dict(
                    lock_left="LOCK",
                    lock_right="LOCK",
                    state="NORMAL",
                    reason_code="APPROACH_RISK",
                    priority_reason="approach_risk",
                    reason_left="ISOFIX",
                    reason_right="APPROACH_RISK",
                    input_validity="VALID",
                    warning_code="NONE",
                ),
            ),
        ],
        id="FTC-PW03-06",
    ),
    # FTC-PW03-07 (SWR-009, SWR-005, SWR-018, SWR-003, SWR-004) PICT-03#7:
    # 좌/우 접근위험·ISOFIX·명령·차속 조합에서 쪽별 독립 판정과 reason_code
    # 선택(순위 높은 쪽, 동순위는 좌측) 검증. 좌우 혼동·공유 상태 결함 검출
    pytest.param(
        [
            Step(
                10.00,
                cmds=[cmd("left", "lock")],
                expect=dict(
                    lock_left="LOCK",
                    lock_right="RELEASE",
                    reason_left="DRIVER_COMMAND",
                    reason_right="NO_CHANGE",
                ),
            ),
            Step(
                10.05,
                sig=dict(vehicle_speed_kph=3.0),
                expect=dict(
                    lock_left="LOCK",
                    lock_right="LOCK",
                    state="NORMAL",
                    reason_code="AUTO_LOCK",
                    priority_reason="auto_lock",
                    reason_left="AUTO_LOCK",
                    reason_right="AUTO_LOCK",
                    input_validity="VALID",
                    warning_code="NONE",
                ),
            ),
        ],
        id="FTC-PW03-07",
    ),
    # FTC-PW03-08 (SWR-009, SWR-005, SWR-018, SWR-003, SWR-004) PICT-03#8:
    # 좌/우 접근위험·ISOFIX·명령·차속 조합에서 쪽별 독립 판정과 reason_code
    # 선택(순위 높은 쪽, 동순위는 좌측) 검증. 좌우 혼동·공유 상태 결함 검출
    pytest.param(
        [
            Step(
                10.00,
                cmds=[cmd("left", "lock")],
                expect=dict(
                    lock_left="LOCK",
                    lock_right="RELEASE",
                    reason_left="DRIVER_COMMAND",
                    reason_right="NO_CHANGE",
                ),
            ),
            Step(
                10.05,
                sig=dict(rear_left_approach_risk=True),
                cmds=[cmd("left", "unlock")],
                expect=dict(
                    lock_left="LOCK",
                    lock_right="RELEASE",
                    state="NORMAL",
                    reason_code="APPROACH_RISK",
                    priority_reason="approach_risk",
                    reason_left="APPROACH_RISK",
                    reason_right="NO_CHANGE",
                    input_validity="VALID",
                    warning_code="NONE",
                ),
            ),
        ],
        id="FTC-PW03-08",
    ),
    # FTC-PW03-09 (SWR-009, SWR-005, SWR-018, SWR-003, SWR-004) PICT-03#9:
    # 좌/우 접근위험·ISOFIX·명령·차속 조합에서 쪽별 독립 판정과 reason_code
    # 선택(순위 높은 쪽, 동순위는 좌측) 검증. 좌우 혼동·공유 상태 결함 검출
    pytest.param(
        [
            Step(
                10.00,
                cmds=[cmd("left", "lock")],
                expect=dict(
                    lock_left="LOCK",
                    lock_right="RELEASE",
                    reason_left="DRIVER_COMMAND",
                    reason_right="NO_CHANGE",
                ),
            ),
            Step(
                10.05,
                sig=dict(rear_right_approach_risk=True, vehicle_speed_kph=3.0),
                cmds=[cmd("right", "unlock", "avn")],
                expect=dict(
                    lock_left="LOCK",
                    lock_right="LOCK",
                    state="NORMAL",
                    reason_code="APPROACH_RISK",
                    priority_reason="approach_risk",
                    reason_left="AUTO_LOCK",
                    reason_right="APPROACH_RISK",
                    input_validity="VALID",
                    warning_code="NONE",
                ),
            ),
        ],
        id="FTC-PW03-09",
    ),
    # FTC-PW03-10 (SWR-009, SWR-005, SWR-018, SWR-003, SWR-004) PICT-03#10:
    # 좌/우 접근위험·ISOFIX·명령·차속 조합에서 쪽별 독립 판정과 reason_code
    # 선택(순위 높은 쪽, 동순위는 좌측) 검증. 좌우 혼동·공유 상태 결함 검출
    pytest.param(
        [
            Step(
                10.00,
                cmds=[cmd("left", "lock")],
                expect=dict(
                    lock_left="LOCK",
                    lock_right="RELEASE",
                    reason_left="DRIVER_COMMAND",
                    reason_right="NO_CHANGE",
                ),
            ),
            Step(
                10.05,
                sig=dict(
                    rear_left_approach_risk=True,
                    isofix_left=True,
                    vehicle_speed_kph=3.0,
                ),
                cmds=[cmd("all", "unlock", "voice")],
                expect=dict(
                    lock_left="LOCK",
                    lock_right="LOCK",
                    state="NORMAL",
                    reason_code="APPROACH_RISK",
                    priority_reason="approach_risk",
                    reason_left="APPROACH_RISK",
                    reason_right="AUTO_LOCK",
                    input_validity="VALID",
                    warning_code="NONE",
                ),
            ),
        ],
        id="FTC-PW03-10",
    ),
    # FTC-PW03-11 (SWR-009, SWR-005, SWR-018, SWR-003, SWR-004) PICT-03#11:
    # 좌/우 접근위험·ISOFIX·명령·차속 조합에서 쪽별 독립 판정과 reason_code
    # 선택(순위 높은 쪽, 동순위는 좌측) 검증. 좌우 혼동·공유 상태 결함 검출
    pytest.param(
        [
            Step(
                10.00,
                cmds=[cmd("left", "lock")],
                expect=dict(
                    lock_left="LOCK",
                    lock_right="RELEASE",
                    reason_left="DRIVER_COMMAND",
                    reason_right="NO_CHANGE",
                ),
            ),
            Step(
                10.05,
                sig=dict(
                    rear_left_approach_risk=True,
                    isofix_right=True,
                    vehicle_speed_kph=3.0,
                ),
                cmds=[cmd("all", "lock", "mobile_app")],
                expect=dict(
                    lock_left="LOCK",
                    lock_right="LOCK",
                    state="NORMAL",
                    reason_code="APPROACH_RISK",
                    priority_reason="approach_risk",
                    reason_left="APPROACH_RISK",
                    reason_right="ISOFIX",
                    input_validity="VALID",
                    warning_code="NONE",
                ),
            ),
        ],
        id="FTC-PW03-11",
    ),
    # FTC-PW03-12 (SWR-009, SWR-005, SWR-018, SWR-003, SWR-004) PICT-03#12:
    # 좌/우 접근위험·ISOFIX·명령·차속 조합에서 쪽별 독립 판정과 reason_code
    # 선택(순위 높은 쪽, 동순위는 좌측) 검증. 좌우 혼동·공유 상태 결함 검출
    pytest.param(
        [
            Step(
                10.00,
                cmds=[cmd("left", "lock")],
                expect=dict(
                    lock_left="LOCK",
                    lock_right="RELEASE",
                    reason_left="DRIVER_COMMAND",
                    reason_right="NO_CHANGE",
                ),
            ),
            Step(
                10.05,
                sig=dict(
                    rear_right_approach_risk=True,
                    isofix_left=True,
                    isofix_right=True,
                    vehicle_speed_kph=3.0,
                ),
                cmds=[cmd("right", "lock")],
                expect=dict(
                    lock_left="LOCK",
                    lock_right="LOCK",
                    state="NORMAL",
                    reason_code="APPROACH_RISK",
                    priority_reason="approach_risk",
                    reason_left="ISOFIX",
                    reason_right="APPROACH_RISK",
                    input_validity="VALID",
                    warning_code="NONE",
                ),
            ),
        ],
        id="FTC-PW03-12",
    ),
    # FTC-PW03-13 (SWR-009, SWR-005, SWR-018, SWR-003, SWR-004) PICT-03#13:
    # 좌/우 접근위험·ISOFIX·명령·차속 조합에서 쪽별 독립 판정과 reason_code
    # 선택(순위 높은 쪽, 동순위는 좌측) 검증. 좌우 혼동·공유 상태 결함 검출
    pytest.param(
        [
            Step(
                10.00,
                cmds=[cmd("left", "lock")],
                expect=dict(
                    lock_left="LOCK",
                    lock_right="RELEASE",
                    reason_left="DRIVER_COMMAND",
                    reason_right="NO_CHANGE",
                ),
            ),
            Step(
                10.05,
                sig=dict(rear_right_approach_risk=True, isofix_right=True),
                cmds=[cmd("left", "lock", "avn")],
                expect=dict(
                    lock_left="LOCK",
                    lock_right="LOCK",
                    state="NORMAL",
                    reason_code="APPROACH_RISK",
                    priority_reason="approach_risk",
                    reason_left="DRIVER_COMMAND",
                    reason_right="APPROACH_RISK",
                    input_validity="VALID",
                    warning_code="NONE",
                ),
            ),
        ],
        id="FTC-PW03-13",
    ),
    # FTC-PW03-14 (SWR-009, SWR-005, SWR-018, SWR-003, SWR-004) PICT-03#14:
    # 좌/우 접근위험·ISOFIX·명령·차속 조합에서 쪽별 독립 판정과 reason_code
    # 선택(순위 높은 쪽, 동순위는 좌측) 검증. 좌우 혼동·공유 상태 결함 검출
    pytest.param(
        [
            Step(
                10.00,
                cmds=[cmd("left", "lock")],
                expect=dict(
                    lock_left="LOCK",
                    lock_right="RELEASE",
                    reason_left="DRIVER_COMMAND",
                    reason_right="NO_CHANGE",
                ),
            ),
            Step(
                10.05,
                sig=dict(
                    rear_left_approach_risk=True,
                    isofix_left=True,
                    isofix_right=True,
                ),
                cmds=[cmd("right", "unlock", "voice")],
                expect=dict(
                    lock_left="LOCK",
                    lock_right="LOCK",
                    state="NORMAL",
                    reason_code="APPROACH_RISK",
                    priority_reason="approach_risk",
                    reason_left="APPROACH_RISK",
                    reason_right="ISOFIX",
                    input_validity="VALID",
                    warning_code="NONE",
                ),
            ),
        ],
        id="FTC-PW03-14",
    ),
]


@pytest.mark.parametrize("steps", PW03_CASES)
def test_ftc_pw03_side_mix_combinations(bench, steps):
    """FTC-PW03-01~FTC-PW03-14 (SWR-009, SWR-005, SWR-018, SWR-003, SWR-004)

    PICT-03 2-way 행: 좌·우 접근위험, 좌·우 ISOFIX, 명령, 차속 조합의
    쪽별 출력·이유. 케이스별 tc_id는 각 pytest.param의 id다.
    """
    play(bench, steps)
