"""@brief SWE.6 기능 시험: sensor fault·시동 OFF·강제 해제·ISOFIX·상태 조회
(SWR-014, 017, 018, 020, 021).

근거: docs/swe6/system-test-cases.json
"""

import pytest
from tests.system.harness import cmd
from tests.system.st_support import Step, check, play, run


def test_ftc_146_sensor_fault_holds_outputs(bench):
    """FTC-146 (SWR-021)

    sensor fault 중 모든 새 규칙이 적용되지 않고 직전 출력이 유지되며
    warning_code=W_SENSOR_FAULT, state=FAULT인지, false가 된 평가부터 즉시 정상
    판정·warning_code=NONE인지 확인. 규칙 누수와 복귀 지연 결함 검출
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
    # 2단계 t=10.05: sensor_fault true + 접근위험·ISOFIX·3.0 km/h·lock 동시
    st = run(
        bench,
        10.05,
        [cmd("all", "lock")],
        sensor_fault=True,
        rear_left_approach_risk=True,
        isofix_right=True,
        vehicle_speed_kph=3.0,
    )
    check(
        st,
        2,
        lock_left="RELEASE",
        lock_right="RELEASE",
        state="FAULT",
        reason_code="SENSOR_FAULT",
        priority_reason="sensor_fault",
        reason_left="SENSOR_FAULT",
        reason_right="SENSOR_FAULT",
        input_validity="VALID",
        warning_code="W_SENSOR_FAULT",
    )
    # 3단계 t=10.10: sensor_fault=false 평가부터 정상 판정(디바운스 없음)
    st = run(
        bench,
        10.10,
        rear_left_approach_risk=True,
        isofix_right=True,
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
        reason_right="ISOFIX",
        warning_code="NONE",
    )


def test_ftc_147_sensor_fault_blocks_release_rules(bench):
    """FTC-147 (SWR-021, SWR-020, SWR-017)

    직전 LOCK 상태에서 sensor fault 중 RELEASE를 만드는 규칙(시동 OFF, 화재,
    unlock)이 모두 무시되고 LOCK이 유지되는지 확인(FTC-146은 LOCK 방향, 이
    케이스는 RELEASE 방향). 방향별 규칙 누수 결함 검출
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
    # 2단계 t=10.05: sensor_fault + 시동 OFF + 화재 + unlock all
    st = run(
        bench,
        10.05,
        [cmd("all", "unlock")],
        sensor_fault=True,
        ignition_on=False,
        fire_detected=True,
    )
    check(
        st,
        2,
        lock_left="LOCK",
        lock_right="LOCK",
        state="FAULT",
        reason_code="SENSOR_FAULT",
        priority_reason="sensor_fault",
        reason_left="SENSOR_FAULT",
        reason_right="SENSOR_FAULT",
        warning_code="W_SENSOR_FAULT",
    )


def test_ftc_148_ignition_off_releases_both(bench):
    """FTC-148 (SWR-020)

    ignition_on=false 첫 평가에 양쪽 RELEASE, reason=IGNITION_OFF, state=OFF가
    되고 시동 ON 복귀 후 state=NORMAL로 돌아가는지 확인. state 미복귀 결함 검출
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
    # 2단계 t=10.05: 시동 OFF 첫 평가
    st = run(bench, 10.05, ignition_on=False)
    check(
        st,
        2,
        lock_left="RELEASE",
        lock_right="RELEASE",
        state="OFF",
        reason_code="IGNITION_OFF",
        priority_reason="ignition_off",
        reason_left="IGNITION_OFF",
        reason_right="IGNITION_OFF",
        input_validity="VALID",
        warning_code="NONE",
    )
    # 3단계 t=10.10: 시동 ON 복귀(차속 0.0): RELEASE 유지
    st = run(bench, 10.10)
    check(
        st,
        3,
        lock_left="RELEASE",
        lock_right="RELEASE",
        state="NORMAL",
        reason_code="NO_CHANGE",
        priority_reason="no_change",
    )


def test_ftc_149_ignition_off_keeps_approach_lock(bench):
    """FTC-149 (SWR-020, SWR-005)

    시동 OFF에서도 좌 접근위험 LOCK이 유지되고 우측만 RELEASE, state=OFF인지
    확인(수용기준). 시동 OFF가 ASIL B 잠금을 해제하는 결함 검출
    """
    # 1단계 t=10.00: 사전 설정: 좌 접근위험 LOCK, 우 driver lock
    st = run(bench, 10.00, [cmd("right", "lock")], rear_left_approach_risk=True)
    check(
        st,
        1,
        lock_left="LOCK",
        lock_right="LOCK",
        reason_code="APPROACH_RISK",
        priority_reason="approach_risk",
    )
    # 2단계 t=10.05: 시동 OFF + 좌 접근위험
    st = run(bench, 10.05, rear_left_approach_risk=True, ignition_on=False)
    check(
        st,
        2,
        lock_left="LOCK",
        lock_right="RELEASE",
        state="OFF",
        reason_code="APPROACH_RISK",
        priority_reason="approach_risk",
        reason_left="APPROACH_RISK",
        reason_right="IGNITION_OFF",
    )


def test_ftc_150_ignition_off_ignores_lock_command(bench):
    """FTC-150 (SWR-020, SWR-002)

    시동 OFF 중 운전자 lock이 RELEASE를 바꾸지 못하는지 확인(순위 6 > 10, LOCK
    방향 규칙 누수). FTC-D-39(unlock)와 반대 방향 결함 검출
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
    # 2단계 t=10.05: 시동 OFF 중 lock all
    st = run(bench, 10.05, [cmd("all", "lock")], ignition_on=False)
    check(
        st,
        2,
        lock_left="RELEASE",
        lock_right="RELEASE",
        state="OFF",
        reason_code="IGNITION_OFF",
        priority_reason="ignition_off",
    )


def test_ftc_151_isofix_applies_after_fire_clears(bench):
    """FTC-151 (SWR-017, SWR-018)

    강제 해제 입력이 false로 돌아간 평가에서 ISOFIX가 즉시 LOCK을 만드는지(해제
    래치 잔존 없음), 입력 중에는 ISOFIX가 무시되는지 확인(수용기준). 강제 해제
    상태가 남는 결함 검출
    """
    # 1단계 t=10.00: 화재 true + ISOFIX 좌 true
    st = run(bench, 10.00, isofix_left=True, fire_detected=True)
    check(
        st,
        1,
        lock_left="RELEASE",
        lock_right="RELEASE",
        state="NORMAL",
        reason_code="FIRE",
        priority_reason="fire_detected",
        reason_left="FIRE",
        reason_right="FIRE",
    )
    # 2단계 t=10.05: 화재 false로 복귀한 평가: ISOFIX가 적용되어 LOCK
    st = run(bench, 10.05, isofix_left=True)
    check(
        st,
        2,
        lock_left="LOCK",
        lock_right="RELEASE",
        state="NORMAL",
        reason_code="ISOFIX",
        priority_reason="isofix",
        reason_left="ISOFIX",
        reason_right="NO_CHANGE",
    )


def test_ftc_152_isofix_one_side_and_hold(bench):
    """FTC-152 (SWR-018)

    ISOFIX true 쪽만 LOCK이 되고 반대쪽은 직전 값이며, false가 되어도 LOCK이
    유지되고 이후 unlock이 적용되는지 확인. false 시 자동 해제 또는 ISOFIX 억제
    잔존 결함 검출
    """
    # 1단계 t=10.00: 좌 ISOFIX true
    st = run(bench, 10.00, isofix_left=True)
    check(
        st,
        1,
        lock_left="LOCK",
        lock_right="RELEASE",
        state="NORMAL",
        reason_code="ISOFIX",
        priority_reason="isofix",
        reason_left="ISOFIX",
        reason_right="NO_CHANGE",
    )
    # 2단계 t=10.05: ISOFIX false: LOCK 유지
    st = run(bench, 10.05)
    check(
        st,
        2,
        lock_left="LOCK",
        lock_right="RELEASE",
        state="NORMAL",
        reason_code="NO_CHANGE",
        priority_reason="no_change",
    )
    # 3단계 t=10.10: ISOFIX false 이후 unlock은 적용
    st = run(bench, 10.10, [cmd("left", "unlock")])
    check(
        st,
        3,
        lock_left="RELEASE",
        lock_right="RELEASE",
        state="NORMAL",
        reason_code="DRIVER_COMMAND",
        priority_reason="driver_command",
    )


def test_ftc_153_status_has_nine_fields(bench):
    """FTC-153 (SWR-014)

    상태 조회가 아홉 필드를 모두 제공하고 값이 마지막 평가 결과와 같은지
    확인(필드 누락·이전 결과 캐시·reason_left/right 누락 결함 검출). 서로 다른
    값을 가진 두 평가를 사용해 필드별 값을 구분
    """
    # 1단계 t=10.00: GET /status 응답에 아홉 필드(lock_left, lock_right, state,
    # priority_reason, reason_code, input_validity, reason_left, reason_right,
    # warning_code)가 모두 있고 값이 위와 같은지 확인
    st = run(bench, 10.00, rear_left_approach_risk=True, gear="X")
    check(
        st,
        1,
        lock_left="LOCK",
        lock_right="RELEASE",
        state="DEGRADED",
        reason_code="APPROACH_RISK",
        priority_reason="approach_risk",
        reason_left="APPROACH_RISK",
        reason_right="INPUT_INVALID",
        input_validity="INVALID",
        warning_code="NONE",
    )
    # 2단계 t=10.05: 아홉 필드가 모두 마지막 평가 결과로 갱신(이전 값 잔존
    # 없음)
    st = run(bench, 10.05, sensor_fault=True)
    check(
        st,
        2,
        lock_left="LOCK",
        lock_right="RELEASE",
        state="FAULT",
        reason_code="SENSOR_FAULT",
        priority_reason="sensor_fault",
        reason_left="SENSOR_FAULT",
        reason_right="SENSOR_FAULT",
        input_validity="VALID",
        warning_code="W_SENSOR_FAULT",
    )


PW02_CASES = [
    # FTC-PW02-1 (SWR-017) PICT-02#1: adult_present=true. 강제 해제가 ISOFIX
    # 잠금보다 우선하고 이유 순위(화재>과온>성인)가 지켜지는지 검출
    pytest.param(
        [
            Step(
                10.00,
                sig=dict(isofix_left=True, isofix_right=True),
                expect=dict(
                    lock_left="LOCK",
                    lock_right="LOCK",
                    reason_code="ISOFIX",
                    priority_reason="isofix",
                ),
            ),
            Step(
                10.05,
                sig=dict(
                    isofix_left=True,
                    isofix_right=True,
                    fire_detected=False,
                    overtemperature_detected=False,
                    adult_present=True,
                ),
                expect=dict(
                    lock_left="RELEASE",
                    lock_right="RELEASE",
                    state="NORMAL",
                    reason_code="ADULT_PRESENT",
                    priority_reason="adult_present",
                    reason_left="ADULT_PRESENT",
                    reason_right="ADULT_PRESENT",
                    input_validity="VALID",
                    warning_code="NONE",
                ),
            ),
        ],
        id="FTC-PW02-1",
    ),
    # FTC-PW02-2 (SWR-017) PICT-02#2: fire_detected,
    # overtemperature_detected=true. 강제 해제가 ISOFIX 잠금보다 우선하고 이유
    # 순위(화재>과온>성인)가 지켜지는지 검출
    pytest.param(
        [
            Step(
                10.00,
                sig=dict(isofix_left=True, isofix_right=True),
                expect=dict(
                    lock_left="LOCK",
                    lock_right="LOCK",
                    reason_code="ISOFIX",
                    priority_reason="isofix",
                ),
            ),
            Step(
                10.05,
                sig=dict(
                    isofix_left=True,
                    isofix_right=True,
                    fire_detected=True,
                    overtemperature_detected=True,
                    adult_present=False,
                ),
                expect=dict(
                    lock_left="RELEASE",
                    lock_right="RELEASE",
                    state="NORMAL",
                    reason_code="FIRE",
                    priority_reason="fire_detected",
                    reason_left="FIRE",
                    reason_right="FIRE",
                    input_validity="VALID",
                    warning_code="NONE",
                ),
            ),
        ],
        id="FTC-PW02-2",
    ),
    # FTC-PW02-3 (SWR-017) PICT-02#3: overtemperature_detected=true. 강제
    # 해제가 ISOFIX 잠금보다 우선하고 이유 순위(화재>과온>성인)가 지켜지는지
    # 검출
    pytest.param(
        [
            Step(
                10.00,
                sig=dict(isofix_left=True, isofix_right=True),
                expect=dict(
                    lock_left="LOCK",
                    lock_right="LOCK",
                    reason_code="ISOFIX",
                    priority_reason="isofix",
                ),
            ),
            Step(
                10.05,
                sig=dict(
                    isofix_left=True,
                    isofix_right=True,
                    fire_detected=False,
                    overtemperature_detected=True,
                    adult_present=False,
                ),
                expect=dict(
                    lock_left="RELEASE",
                    lock_right="RELEASE",
                    state="NORMAL",
                    reason_code="OVERTEMPERATURE",
                    priority_reason="overtemperature_detected",
                    reason_left="OVERTEMPERATURE",
                    reason_right="OVERTEMPERATURE",
                    input_validity="VALID",
                    warning_code="NONE",
                ),
            ),
        ],
        id="FTC-PW02-3",
    ),
    # FTC-PW02-4 (SWR-017) PICT-02#4: overtemperature_detected,
    # adult_present=true. 강제 해제가 ISOFIX 잠금보다 우선하고 이유
    # 순위(화재>과온>성인)가 지켜지는지 검출
    pytest.param(
        [
            Step(
                10.00,
                sig=dict(isofix_left=True, isofix_right=True),
                expect=dict(
                    lock_left="LOCK",
                    lock_right="LOCK",
                    reason_code="ISOFIX",
                    priority_reason="isofix",
                ),
            ),
            Step(
                10.05,
                sig=dict(
                    isofix_left=True,
                    isofix_right=True,
                    fire_detected=False,
                    overtemperature_detected=True,
                    adult_present=True,
                ),
                expect=dict(
                    lock_left="RELEASE",
                    lock_right="RELEASE",
                    state="NORMAL",
                    reason_code="OVERTEMPERATURE",
                    priority_reason="overtemperature_detected",
                    reason_left="OVERTEMPERATURE",
                    reason_right="OVERTEMPERATURE",
                    input_validity="VALID",
                    warning_code="NONE",
                ),
            ),
        ],
        id="FTC-PW02-4",
    ),
    # FTC-PW02-5 (SWR-017) PICT-02#5: fire_detected=true. 강제 해제가 ISOFIX
    # 잠금보다 우선하고 이유 순위(화재>과온>성인)가 지켜지는지 검출
    pytest.param(
        [
            Step(
                10.00,
                sig=dict(isofix_left=True, isofix_right=True),
                expect=dict(
                    lock_left="LOCK",
                    lock_right="LOCK",
                    reason_code="ISOFIX",
                    priority_reason="isofix",
                ),
            ),
            Step(
                10.05,
                sig=dict(
                    isofix_left=True,
                    isofix_right=True,
                    fire_detected=True,
                    overtemperature_detected=False,
                    adult_present=False,
                ),
                expect=dict(
                    lock_left="RELEASE",
                    lock_right="RELEASE",
                    state="NORMAL",
                    reason_code="FIRE",
                    priority_reason="fire_detected",
                    reason_left="FIRE",
                    reason_right="FIRE",
                    input_validity="VALID",
                    warning_code="NONE",
                ),
            ),
        ],
        id="FTC-PW02-5",
    ),
    # FTC-PW02-6 (SWR-017) PICT-02#6: fire_detected, adult_present=true. 강제
    # 해제가 ISOFIX 잠금보다 우선하고 이유 순위(화재>과온>성인)가 지켜지는지
    # 검출
    pytest.param(
        [
            Step(
                10.00,
                sig=dict(isofix_left=True, isofix_right=True),
                expect=dict(
                    lock_left="LOCK",
                    lock_right="LOCK",
                    reason_code="ISOFIX",
                    priority_reason="isofix",
                ),
            ),
            Step(
                10.05,
                sig=dict(
                    isofix_left=True,
                    isofix_right=True,
                    fire_detected=True,
                    overtemperature_detected=False,
                    adult_present=True,
                ),
                expect=dict(
                    lock_left="RELEASE",
                    lock_right="RELEASE",
                    state="NORMAL",
                    reason_code="FIRE",
                    priority_reason="fire_detected",
                    reason_left="FIRE",
                    reason_right="FIRE",
                    input_validity="VALID",
                    warning_code="NONE",
                ),
            ),
        ],
        id="FTC-PW02-6",
    ),
    # FTC-PW02-7 (SWR-017) PICT-02#7: fire_detected, overtemperature_detected,
    # adult_present=true. 강제 해제가 ISOFIX 잠금보다 우선하고 이유
    # 순위(화재>과온>성인)가 지켜지는지 검출
    pytest.param(
        [
            Step(
                10.00,
                sig=dict(isofix_left=True, isofix_right=True),
                expect=dict(
                    lock_left="LOCK",
                    lock_right="LOCK",
                    reason_code="ISOFIX",
                    priority_reason="isofix",
                ),
            ),
            Step(
                10.05,
                sig=dict(
                    isofix_left=True,
                    isofix_right=True,
                    fire_detected=True,
                    overtemperature_detected=True,
                    adult_present=True,
                ),
                expect=dict(
                    lock_left="RELEASE",
                    lock_right="RELEASE",
                    state="NORMAL",
                    reason_code="FIRE",
                    priority_reason="fire_detected",
                    reason_left="FIRE",
                    reason_right="FIRE",
                    input_validity="VALID",
                    warning_code="NONE",
                ),
            ),
        ],
        id="FTC-PW02-7",
    ),
]


@pytest.mark.parametrize("steps", PW02_CASES)
def test_ftc_pw02_forced_release_combinations(bench, steps):
    """FTC-PW02-1~FTC-PW02-7 (SWR-017)

    PICT-02 행: 화재·과온·성인 탑승 불리언 3개의 전수 조합(7행)에서
    강제 해제와 이유 순위. 케이스별 tc_id는 각 pytest.param의 id다.
    """
    play(bench, steps)
