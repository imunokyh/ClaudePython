"""@brief SWE.6 기능 시험: SWR-019 결정표 D-01~D-45, P-01~P-10.

근거: docs/swe6/system-test-cases.json
"""

import pytest
from tests.system.harness import cmd
from tests.system.st_support import Step, play

D_CASES = [
    # FTC-D-01 (SWR-019, SWR-007, SWR-013) D-01: 충돌 래치(순위 1)와 ASIL B
    # 입력 이상(순위 2)가 같은 평가·같은 쪽에 성립할 때 상위 규칙이 이긴다.
    # 규칙 순서 뒤바뀜·하위 규칙 누수 결함 검출
    pytest.param(
        [
            Step(
                10.00,
                sig=dict(vehicle_speed_kph=3.0),
                expect=dict(
                    lock_left="LOCK",
                    lock_right="LOCK",
                    reason_code="AUTO_LOCK",
                    priority_reason="auto_lock",
                ),
            ),
            Step(
                10.05,
                sig=dict(crash_status="CONFIRMED", rear_right_approach_risk=1),
                expect=dict(
                    lock_left="RELEASE",
                    lock_right="RELEASE",
                    state="DEGRADED",
                    reason_code="CRASH_CONFIRMED",
                    priority_reason="crash_confirmed",
                    reason_left="CRASH_CONFIRMED",
                    reason_right="CRASH_CONFIRMED",
                    input_validity="INVALID",
                    warning_code="NONE",
                ),
            ),
        ],
        id="FTC-D-01",
    ),
    # FTC-D-02 (SWR-019, SWR-007, SWR-021) D-02: 충돌 래치(순위 1)와 sensor
    # fault(순위 3)가 같은 평가·같은 쪽에 성립할 때 상위 규칙이 이긴다. 규칙
    # 순서 뒤바뀜·하위 규칙 누수 결함 검출
    pytest.param(
        [
            Step(
                10.00,
                sig=dict(vehicle_speed_kph=3.0),
                expect=dict(
                    lock_left="LOCK",
                    lock_right="LOCK",
                    reason_code="AUTO_LOCK",
                    priority_reason="auto_lock",
                ),
            ),
            Step(
                10.05,
                sig=dict(crash_status="CONFIRMED", sensor_fault=True),
                expect=dict(
                    lock_left="RELEASE",
                    lock_right="RELEASE",
                    state="FAULT",
                    reason_code="CRASH_CONFIRMED",
                    priority_reason="crash_confirmed",
                    reason_left="CRASH_CONFIRMED",
                    reason_right="CRASH_CONFIRMED",
                    input_validity="VALID",
                ),
            ),
        ],
        id="FTC-D-02",
    ),
    # FTC-D-03 (SWR-019, SWR-007, SWR-005) D-03: 충돌 래치(순위 1)와
    # 접근위험(순위 4)가 같은 평가·같은 쪽에 성립할 때 상위 규칙이 이긴다. 규칙
    # 순서 뒤바뀜·하위 규칙 누수 결함 검출
    pytest.param(
        [
            Step(
                10.00,
                sig=dict(vehicle_speed_kph=3.0),
                expect=dict(
                    lock_left="LOCK",
                    lock_right="LOCK",
                    reason_code="AUTO_LOCK",
                    priority_reason="auto_lock",
                ),
            ),
            Step(
                10.05,
                sig=dict(
                    crash_status="CONFIRMED", rear_left_approach_risk=True
                ),
                expect=dict(
                    lock_left="RELEASE",
                    lock_right="RELEASE",
                    state="NORMAL",
                    reason_code="CRASH_CONFIRMED",
                    priority_reason="crash_confirmed",
                    reason_left="CRASH_CONFIRMED",
                    reason_right="CRASH_CONFIRMED",
                    input_validity="VALID",
                    warning_code="NONE",
                ),
            ),
        ],
        id="FTC-D-03",
    ),
    # FTC-D-04 (SWR-019, SWR-007, SWR-013) D-04: 충돌 래치(순위 1)와 QM 입력
    # 이상(순위 5)가 같은 평가·같은 쪽에 성립할 때 상위 규칙이 이긴다. 규칙
    # 순서 뒤바뀜·하위 규칙 누수 결함 검출
    pytest.param(
        [
            Step(
                10.00,
                sig=dict(vehicle_speed_kph=3.0),
                expect=dict(
                    lock_left="LOCK",
                    lock_right="LOCK",
                    reason_code="AUTO_LOCK",
                    priority_reason="auto_lock",
                ),
            ),
            Step(
                10.05,
                sig=dict(crash_status="CONFIRMED", gear="X"),
                expect=dict(
                    lock_left="RELEASE",
                    lock_right="RELEASE",
                    state="DEGRADED",
                    reason_code="CRASH_CONFIRMED",
                    priority_reason="crash_confirmed",
                    reason_left="CRASH_CONFIRMED",
                    reason_right="CRASH_CONFIRMED",
                    input_validity="INVALID",
                    warning_code="NONE",
                ),
            ),
        ],
        id="FTC-D-04",
    ),
    # FTC-D-05 (SWR-019, SWR-007, SWR-020) D-05: 충돌 래치(순위 1)와 시동
    # OFF(순위 6)가 같은 평가·같은 쪽에 성립할 때 상위 규칙이 이긴다. 규칙 순서
    # 뒤바뀜·하위 규칙 누수 결함 검출
    pytest.param(
        [
            Step(
                10.00,
                sig=dict(vehicle_speed_kph=3.0),
                expect=dict(
                    lock_left="LOCK",
                    lock_right="LOCK",
                    reason_code="AUTO_LOCK",
                    priority_reason="auto_lock",
                ),
            ),
            Step(
                10.05,
                sig=dict(crash_status="CONFIRMED", ignition_on=False),
                expect=dict(
                    lock_left="RELEASE",
                    lock_right="RELEASE",
                    state="OFF",
                    reason_code="CRASH_CONFIRMED",
                    priority_reason="crash_confirmed",
                    reason_left="CRASH_CONFIRMED",
                    reason_right="CRASH_CONFIRMED",
                    input_validity="VALID",
                    warning_code="NONE",
                ),
            ),
        ],
        id="FTC-D-05",
    ),
    # FTC-D-06 (SWR-019, SWR-007, SWR-017) D-06: 충돌 래치(순위 1)와 강제
    # 해제(화재)(순위 7)가 같은 평가·같은 쪽에 성립할 때 상위 규칙이 이긴다.
    # 규칙 순서 뒤바뀜·하위 규칙 누수 결함 검출
    pytest.param(
        [
            Step(
                10.00,
                sig=dict(vehicle_speed_kph=3.0),
                expect=dict(
                    lock_left="LOCK",
                    lock_right="LOCK",
                    reason_code="AUTO_LOCK",
                    priority_reason="auto_lock",
                ),
            ),
            Step(
                10.05,
                sig=dict(crash_status="CONFIRMED", fire_detected=True),
                expect=dict(
                    lock_left="RELEASE",
                    lock_right="RELEASE",
                    state="NORMAL",
                    reason_code="CRASH_CONFIRMED",
                    priority_reason="crash_confirmed",
                    reason_left="CRASH_CONFIRMED",
                    reason_right="CRASH_CONFIRMED",
                    input_validity="VALID",
                    warning_code="NONE",
                ),
            ),
        ],
        id="FTC-D-06",
    ),
    # FTC-D-07 (SWR-019, SWR-007, SWR-018) D-07: 충돌 래치(순위 1)와
    # ISOFIX(순위 8)가 같은 평가·같은 쪽에 성립할 때 상위 규칙이 이긴다. 규칙
    # 순서 뒤바뀜·하위 규칙 누수 결함 검출
    pytest.param(
        [
            Step(
                10.00,
                sig=dict(vehicle_speed_kph=3.0),
                expect=dict(
                    lock_left="LOCK",
                    lock_right="LOCK",
                    reason_code="AUTO_LOCK",
                    priority_reason="auto_lock",
                ),
            ),
            Step(
                10.05,
                sig=dict(crash_status="CONFIRMED", isofix_left=True),
                expect=dict(
                    lock_left="RELEASE",
                    lock_right="RELEASE",
                    state="NORMAL",
                    reason_code="CRASH_CONFIRMED",
                    priority_reason="crash_confirmed",
                    reason_left="CRASH_CONFIRMED",
                    reason_right="CRASH_CONFIRMED",
                    input_validity="VALID",
                    warning_code="NONE",
                ),
            ),
        ],
        id="FTC-D-07",
    ),
    # FTC-D-08 (SWR-019, SWR-007, SWR-003) D-08: 충돌 래치(순위 1)와 자동
    # 잠금(순위 9)가 같은 평가·같은 쪽에 성립할 때 상위 규칙이 이긴다. 규칙
    # 순서 뒤바뀜·하위 규칙 누수 결함 검출
    pytest.param(
        [
            Step(
                10.00,
                sig=dict(vehicle_speed_kph=3.0),
                expect=dict(
                    lock_left="LOCK",
                    lock_right="LOCK",
                    reason_code="AUTO_LOCK",
                    priority_reason="auto_lock",
                ),
            ),
            Step(
                10.05,
                sig=dict(crash_status="CONFIRMED", vehicle_speed_kph=3.0),
                expect=dict(
                    lock_left="RELEASE",
                    lock_right="RELEASE",
                    state="NORMAL",
                    reason_code="CRASH_CONFIRMED",
                    priority_reason="crash_confirmed",
                    reason_left="CRASH_CONFIRMED",
                    reason_right="CRASH_CONFIRMED",
                    input_validity="VALID",
                    warning_code="NONE",
                ),
            ),
        ],
        id="FTC-D-08",
    ),
    # FTC-D-09 (SWR-019, SWR-007, SWR-004) D-09: 충돌 래치(순위 1)와 운전자
    # 명령(순위 10)가 같은 평가·같은 쪽에 성립할 때 상위 규칙이 이긴다. 규칙
    # 순서 뒤바뀜·하위 규칙 누수 결함 검출
    pytest.param(
        [
            Step(
                10.00,
                sig=dict(vehicle_speed_kph=3.0),
                expect=dict(
                    lock_left="LOCK",
                    lock_right="LOCK",
                    reason_code="AUTO_LOCK",
                    priority_reason="auto_lock",
                ),
            ),
            Step(
                10.05,
                sig=dict(crash_status="CONFIRMED"),
                cmds=[cmd("left", "unlock")],
                expect=dict(
                    lock_left="RELEASE",
                    lock_right="RELEASE",
                    state="NORMAL",
                    reason_code="CRASH_CONFIRMED",
                    priority_reason="crash_confirmed",
                    reason_left="CRASH_CONFIRMED",
                    reason_right="CRASH_CONFIRMED",
                    input_validity="VALID",
                    warning_code="NONE",
                ),
            ),
        ],
        id="FTC-D-09",
    ),
    # FTC-D-10 (SWR-019, SWR-013, SWR-021) D-10: ASIL B 입력 이상(순위 2)와
    # sensor fault(순위 3)가 같은 평가·같은 쪽에 성립할 때 상위 규칙이 이긴다.
    # 규칙 순서 뒤바뀜·하위 규칙 누수 결함 검출
    pytest.param(
        [
            Step(
                10.00,
                sig=dict(vehicle_speed_kph=3.0),
                expect=dict(
                    lock_left="LOCK",
                    lock_right="LOCK",
                    reason_code="AUTO_LOCK",
                    priority_reason="auto_lock",
                ),
            ),
            Step(
                10.05,
                sig=dict(rear_right_approach_risk=1, sensor_fault=True),
                expect=dict(
                    lock_left="LOCK",
                    lock_right="LOCK",
                    state="DEGRADED",
                    reason_code="INPUT_INVALID",
                    priority_reason="input_invalid",
                    reason_left="INPUT_INVALID",
                    reason_right="INPUT_INVALID",
                    input_validity="INVALID",
                ),
            ),
        ],
        id="FTC-D-10",
    ),
    # FTC-D-11 (SWR-019, SWR-013, SWR-005) D-11: ASIL B 입력 이상(순위 2)와
    # 접근위험(순위 4)가 같은 평가·같은 쪽에 성립할 때 상위 규칙이 이긴다. 규칙
    # 순서 뒤바뀜·하위 규칙 누수 결함 검출
    pytest.param(
        [
            Step(
                10.00,
                expect=dict(
                    lock_left="RELEASE",
                    lock_right="RELEASE",
                    state="NORMAL",
                    reason_code="NO_CHANGE",
                    priority_reason="no_change",
                ),
            ),
            Step(
                10.05,
                sig=dict(
                    rear_right_approach_risk=1, rear_left_approach_risk=True
                ),
                expect=dict(
                    lock_left="RELEASE",
                    lock_right="RELEASE",
                    state="DEGRADED",
                    reason_code="INPUT_INVALID",
                    priority_reason="input_invalid",
                    reason_left="INPUT_INVALID",
                    reason_right="INPUT_INVALID",
                    input_validity="INVALID",
                    warning_code="NONE",
                ),
            ),
        ],
        id="FTC-D-11",
    ),
    # FTC-D-12 (SWR-019, SWR-013) D-12: ASIL B 입력 이상(순위 2)와 QM 입력
    # 이상(순위 5)가 같은 평가·같은 쪽에 성립할 때 상위 규칙이 이긴다. 규칙
    # 순서 뒤바뀜·하위 규칙 누수 결함 검출
    pytest.param(
        [
            Step(
                10.00,
                sig=dict(vehicle_speed_kph=3.0),
                expect=dict(
                    lock_left="LOCK",
                    lock_right="LOCK",
                    reason_code="AUTO_LOCK",
                    priority_reason="auto_lock",
                ),
            ),
            Step(
                10.05,
                sig=dict(rear_right_approach_risk=1, gear="X"),
                expect=dict(
                    lock_left="LOCK",
                    lock_right="LOCK",
                    state="DEGRADED",
                    reason_code="INPUT_INVALID",
                    priority_reason="input_invalid",
                    reason_left="INPUT_INVALID",
                    reason_right="INPUT_INVALID",
                    input_validity="INVALID",
                    warning_code="NONE",
                ),
            ),
        ],
        id="FTC-D-12",
    ),
    # FTC-D-13 (SWR-019, SWR-013, SWR-020) D-13: ASIL B 입력 이상(순위 2)와
    # 시동 OFF(순위 6)가 같은 평가·같은 쪽에 성립할 때 상위 규칙이 이긴다. 규칙
    # 순서 뒤바뀜·하위 규칙 누수 결함 검출
    pytest.param(
        [
            Step(
                10.00,
                sig=dict(vehicle_speed_kph=3.0),
                expect=dict(
                    lock_left="LOCK",
                    lock_right="LOCK",
                    reason_code="AUTO_LOCK",
                    priority_reason="auto_lock",
                ),
            ),
            Step(
                10.05,
                sig=dict(rear_right_approach_risk=1, ignition_on=False),
                expect=dict(
                    lock_left="LOCK",
                    lock_right="LOCK",
                    state="DEGRADED",
                    reason_code="INPUT_INVALID",
                    priority_reason="input_invalid",
                    reason_left="INPUT_INVALID",
                    reason_right="INPUT_INVALID",
                    input_validity="INVALID",
                    warning_code="NONE",
                ),
            ),
        ],
        id="FTC-D-13",
    ),
    # FTC-D-14 (SWR-019, SWR-013, SWR-017) D-14: ASIL B 입력 이상(순위 2)와
    # 강제 해제(화재)(순위 7)가 같은 평가·같은 쪽에 성립할 때 상위 규칙이
    # 이긴다. 규칙 순서 뒤바뀜·하위 규칙 누수 결함 검출
    pytest.param(
        [
            Step(
                10.00,
                sig=dict(vehicle_speed_kph=3.0),
                expect=dict(
                    lock_left="LOCK",
                    lock_right="LOCK",
                    reason_code="AUTO_LOCK",
                    priority_reason="auto_lock",
                ),
            ),
            Step(
                10.05,
                sig=dict(rear_right_approach_risk=1, fire_detected=True),
                expect=dict(
                    lock_left="LOCK",
                    lock_right="LOCK",
                    state="DEGRADED",
                    reason_code="INPUT_INVALID",
                    priority_reason="input_invalid",
                    reason_left="INPUT_INVALID",
                    reason_right="INPUT_INVALID",
                    input_validity="INVALID",
                    warning_code="NONE",
                ),
            ),
        ],
        id="FTC-D-14",
    ),
    # FTC-D-15 (SWR-019, SWR-013, SWR-018) D-15: ASIL B 입력 이상(순위 2)와
    # ISOFIX(순위 8)가 같은 평가·같은 쪽에 성립할 때 상위 규칙이 이긴다. 규칙
    # 순서 뒤바뀜·하위 규칙 누수 결함 검출
    pytest.param(
        [
            Step(
                10.00,
                expect=dict(
                    lock_left="RELEASE",
                    lock_right="RELEASE",
                    state="NORMAL",
                    reason_code="NO_CHANGE",
                    priority_reason="no_change",
                ),
            ),
            Step(
                10.05,
                sig=dict(rear_right_approach_risk=1, isofix_left=True),
                expect=dict(
                    lock_left="RELEASE",
                    lock_right="RELEASE",
                    state="DEGRADED",
                    reason_code="INPUT_INVALID",
                    priority_reason="input_invalid",
                    reason_left="INPUT_INVALID",
                    reason_right="INPUT_INVALID",
                    input_validity="INVALID",
                    warning_code="NONE",
                ),
            ),
        ],
        id="FTC-D-15",
    ),
    # FTC-D-16 (SWR-019, SWR-013, SWR-003) D-16: ASIL B 입력 이상(순위 2)와
    # 자동 잠금(순위 9)가 같은 평가·같은 쪽에 성립할 때 상위 규칙이 이긴다.
    # 규칙 순서 뒤바뀜·하위 규칙 누수 결함 검출
    pytest.param(
        [
            Step(
                10.00,
                expect=dict(
                    lock_left="RELEASE",
                    lock_right="RELEASE",
                    state="NORMAL",
                    reason_code="NO_CHANGE",
                    priority_reason="no_change",
                ),
            ),
            Step(
                10.05,
                sig=dict(rear_right_approach_risk=1, vehicle_speed_kph=3.0),
                expect=dict(
                    lock_left="RELEASE",
                    lock_right="RELEASE",
                    state="DEGRADED",
                    reason_code="INPUT_INVALID",
                    priority_reason="input_invalid",
                    reason_left="INPUT_INVALID",
                    reason_right="INPUT_INVALID",
                    input_validity="INVALID",
                    warning_code="NONE",
                ),
            ),
        ],
        id="FTC-D-16",
    ),
    # FTC-D-17 (SWR-019, SWR-013, SWR-004) D-17: ASIL B 입력 이상(순위 2)와
    # 운전자 명령(순위 10)가 같은 평가·같은 쪽에 성립할 때 상위 규칙이 이긴다.
    # 규칙 순서 뒤바뀜·하위 규칙 누수 결함 검출
    pytest.param(
        [
            Step(
                10.00,
                sig=dict(vehicle_speed_kph=3.0),
                expect=dict(
                    lock_left="LOCK",
                    lock_right="LOCK",
                    reason_code="AUTO_LOCK",
                    priority_reason="auto_lock",
                ),
            ),
            Step(
                10.05,
                sig=dict(rear_right_approach_risk=1),
                cmds=[cmd("left", "unlock")],
                expect=dict(
                    lock_left="LOCK",
                    lock_right="LOCK",
                    state="DEGRADED",
                    reason_code="INPUT_INVALID",
                    priority_reason="input_invalid",
                    reason_left="INPUT_INVALID",
                    reason_right="INPUT_INVALID",
                    input_validity="INVALID",
                    warning_code="NONE",
                ),
            ),
        ],
        id="FTC-D-17",
    ),
    # FTC-D-18 (SWR-019, SWR-021, SWR-005) D-18: sensor fault(순위 3)와
    # 접근위험(순위 4)가 같은 평가·같은 쪽에 성립할 때 상위 규칙이 이긴다. 규칙
    # 순서 뒤바뀜·하위 규칙 누수 결함 검출
    pytest.param(
        [
            Step(
                10.00,
                expect=dict(
                    lock_left="RELEASE",
                    lock_right="RELEASE",
                    state="NORMAL",
                    reason_code="NO_CHANGE",
                    priority_reason="no_change",
                ),
            ),
            Step(
                10.05,
                sig=dict(sensor_fault=True, rear_left_approach_risk=True),
                expect=dict(
                    lock_left="RELEASE",
                    lock_right="RELEASE",
                    state="FAULT",
                    reason_code="SENSOR_FAULT",
                    priority_reason="sensor_fault",
                    reason_left="SENSOR_FAULT",
                    reason_right="SENSOR_FAULT",
                    input_validity="VALID",
                    warning_code="W_SENSOR_FAULT",
                ),
            ),
        ],
        id="FTC-D-18",
    ),
    # FTC-D-19 (SWR-019, SWR-021, SWR-013) D-19: sensor fault(순위 3)와 QM 입력
    # 이상(순위 5)가 같은 평가·같은 쪽에 성립할 때 상위 규칙이 이긴다. 규칙
    # 순서 뒤바뀜·하위 규칙 누수 결함 검출
    pytest.param(
        [
            Step(
                10.00,
                sig=dict(vehicle_speed_kph=3.0),
                expect=dict(
                    lock_left="LOCK",
                    lock_right="LOCK",
                    reason_code="AUTO_LOCK",
                    priority_reason="auto_lock",
                ),
            ),
            Step(
                10.05,
                sig=dict(sensor_fault=True, gear="X"),
                expect=dict(
                    lock_left="LOCK",
                    lock_right="LOCK",
                    state="DEGRADED",
                    reason_code="SENSOR_FAULT",
                    priority_reason="sensor_fault",
                    reason_left="SENSOR_FAULT",
                    reason_right="SENSOR_FAULT",
                    input_validity="INVALID",
                    warning_code="W_SENSOR_FAULT",
                ),
            ),
        ],
        id="FTC-D-19",
    ),
    # FTC-D-20 (SWR-019, SWR-021, SWR-020) D-20: sensor fault(순위 3)와 시동
    # OFF(순위 6)가 같은 평가·같은 쪽에 성립할 때 상위 규칙이 이긴다. 규칙 순서
    # 뒤바뀜·하위 규칙 누수 결함 검출
    pytest.param(
        [
            Step(
                10.00,
                sig=dict(vehicle_speed_kph=3.0),
                expect=dict(
                    lock_left="LOCK",
                    lock_right="LOCK",
                    reason_code="AUTO_LOCK",
                    priority_reason="auto_lock",
                ),
            ),
            Step(
                10.05,
                sig=dict(sensor_fault=True, ignition_on=False),
                expect=dict(
                    lock_left="LOCK",
                    lock_right="LOCK",
                    state="FAULT",
                    reason_code="SENSOR_FAULT",
                    priority_reason="sensor_fault",
                    reason_left="SENSOR_FAULT",
                    reason_right="SENSOR_FAULT",
                    input_validity="VALID",
                    warning_code="W_SENSOR_FAULT",
                ),
            ),
        ],
        id="FTC-D-20",
    ),
    # FTC-D-21 (SWR-019, SWR-021, SWR-017) D-21: sensor fault(순위 3)와 강제
    # 해제(화재)(순위 7)가 같은 평가·같은 쪽에 성립할 때 상위 규칙이 이긴다.
    # 규칙 순서 뒤바뀜·하위 규칙 누수 결함 검출
    pytest.param(
        [
            Step(
                10.00,
                sig=dict(vehicle_speed_kph=3.0),
                expect=dict(
                    lock_left="LOCK",
                    lock_right="LOCK",
                    reason_code="AUTO_LOCK",
                    priority_reason="auto_lock",
                ),
            ),
            Step(
                10.05,
                sig=dict(sensor_fault=True, fire_detected=True),
                expect=dict(
                    lock_left="LOCK",
                    lock_right="LOCK",
                    state="FAULT",
                    reason_code="SENSOR_FAULT",
                    priority_reason="sensor_fault",
                    reason_left="SENSOR_FAULT",
                    reason_right="SENSOR_FAULT",
                    input_validity="VALID",
                    warning_code="W_SENSOR_FAULT",
                ),
            ),
        ],
        id="FTC-D-21",
    ),
    # FTC-D-22 (SWR-019, SWR-021, SWR-018) D-22: sensor fault(순위 3)와
    # ISOFIX(순위 8)가 같은 평가·같은 쪽에 성립할 때 상위 규칙이 이긴다. 규칙
    # 순서 뒤바뀜·하위 규칙 누수 결함 검출
    pytest.param(
        [
            Step(
                10.00,
                expect=dict(
                    lock_left="RELEASE",
                    lock_right="RELEASE",
                    state="NORMAL",
                    reason_code="NO_CHANGE",
                    priority_reason="no_change",
                ),
            ),
            Step(
                10.05,
                sig=dict(sensor_fault=True, isofix_left=True),
                expect=dict(
                    lock_left="RELEASE",
                    lock_right="RELEASE",
                    state="FAULT",
                    reason_code="SENSOR_FAULT",
                    priority_reason="sensor_fault",
                    reason_left="SENSOR_FAULT",
                    reason_right="SENSOR_FAULT",
                    input_validity="VALID",
                    warning_code="W_SENSOR_FAULT",
                ),
            ),
        ],
        id="FTC-D-22",
    ),
    # FTC-D-23 (SWR-019, SWR-021, SWR-003) D-23: sensor fault(순위 3)와 자동
    # 잠금(순위 9)가 같은 평가·같은 쪽에 성립할 때 상위 규칙이 이긴다. 규칙
    # 순서 뒤바뀜·하위 규칙 누수 결함 검출
    pytest.param(
        [
            Step(
                10.00,
                expect=dict(
                    lock_left="RELEASE",
                    lock_right="RELEASE",
                    state="NORMAL",
                    reason_code="NO_CHANGE",
                    priority_reason="no_change",
                ),
            ),
            Step(
                10.05,
                sig=dict(sensor_fault=True, vehicle_speed_kph=3.0),
                expect=dict(
                    lock_left="RELEASE",
                    lock_right="RELEASE",
                    state="FAULT",
                    reason_code="SENSOR_FAULT",
                    priority_reason="sensor_fault",
                    reason_left="SENSOR_FAULT",
                    reason_right="SENSOR_FAULT",
                    input_validity="VALID",
                    warning_code="W_SENSOR_FAULT",
                ),
            ),
        ],
        id="FTC-D-23",
    ),
    # FTC-D-24 (SWR-019, SWR-021, SWR-004) D-24: sensor fault(순위 3)와 운전자
    # 명령(순위 10)가 같은 평가·같은 쪽에 성립할 때 상위 규칙이 이긴다. 규칙
    # 순서 뒤바뀜·하위 규칙 누수 결함 검출
    pytest.param(
        [
            Step(
                10.00,
                sig=dict(vehicle_speed_kph=3.0),
                expect=dict(
                    lock_left="LOCK",
                    lock_right="LOCK",
                    reason_code="AUTO_LOCK",
                    priority_reason="auto_lock",
                ),
            ),
            Step(
                10.05,
                sig=dict(sensor_fault=True),
                cmds=[cmd("left", "unlock")],
                expect=dict(
                    lock_left="LOCK",
                    lock_right="LOCK",
                    state="FAULT",
                    reason_code="SENSOR_FAULT",
                    priority_reason="sensor_fault",
                    reason_left="SENSOR_FAULT",
                    reason_right="SENSOR_FAULT",
                    input_validity="VALID",
                    warning_code="W_SENSOR_FAULT",
                ),
            ),
        ],
        id="FTC-D-24",
    ),
    # FTC-D-25 (SWR-019, SWR-005, SWR-013) D-25: 접근위험(순위 4)와 QM 입력
    # 이상(순위 5)가 같은 평가·같은 쪽에 성립할 때 상위 규칙이 이긴다. 규칙
    # 순서 뒤바뀜·하위 규칙 누수 결함 검출
    pytest.param(
        [
            Step(
                10.00,
                expect=dict(
                    lock_left="RELEASE",
                    lock_right="RELEASE",
                    state="NORMAL",
                    reason_code="NO_CHANGE",
                    priority_reason="no_change",
                ),
            ),
            Step(
                10.05,
                sig=dict(rear_left_approach_risk=True, gear="X"),
                expect=dict(
                    lock_left="LOCK",
                    lock_right="RELEASE",
                    state="DEGRADED",
                    reason_code="APPROACH_RISK",
                    priority_reason="approach_risk",
                    reason_left="APPROACH_RISK",
                    reason_right="INPUT_INVALID",
                    input_validity="INVALID",
                    warning_code="NONE",
                ),
            ),
        ],
        id="FTC-D-25",
    ),
    # FTC-D-26 (SWR-019, SWR-005, SWR-020) D-26: 접근위험(순위 4)와 시동
    # OFF(순위 6)가 같은 평가·같은 쪽에 성립할 때 상위 규칙이 이긴다. 규칙 순서
    # 뒤바뀜·하위 규칙 누수 결함 검출
    pytest.param(
        [
            Step(
                10.00,
                expect=dict(
                    lock_left="RELEASE",
                    lock_right="RELEASE",
                    state="NORMAL",
                    reason_code="NO_CHANGE",
                    priority_reason="no_change",
                ),
            ),
            Step(
                10.05,
                sig=dict(rear_left_approach_risk=True, ignition_on=False),
                expect=dict(
                    lock_left="LOCK",
                    lock_right="RELEASE",
                    state="OFF",
                    reason_code="APPROACH_RISK",
                    priority_reason="approach_risk",
                    reason_left="APPROACH_RISK",
                    reason_right="IGNITION_OFF",
                    input_validity="VALID",
                    warning_code="NONE",
                ),
            ),
        ],
        id="FTC-D-26",
    ),
    # FTC-D-27 (SWR-019, SWR-005, SWR-017) D-27: 접근위험(순위 4)와 강제
    # 해제(화재)(순위 7)가 같은 평가·같은 쪽에 성립할 때 상위 규칙이 이긴다.
    # 규칙 순서 뒤바뀜·하위 규칙 누수 결함 검출
    pytest.param(
        [
            Step(
                10.00,
                expect=dict(
                    lock_left="RELEASE",
                    lock_right="RELEASE",
                    state="NORMAL",
                    reason_code="NO_CHANGE",
                    priority_reason="no_change",
                ),
            ),
            Step(
                10.05,
                sig=dict(rear_left_approach_risk=True, fire_detected=True),
                expect=dict(
                    lock_left="LOCK",
                    lock_right="RELEASE",
                    state="NORMAL",
                    reason_code="APPROACH_RISK",
                    priority_reason="approach_risk",
                    reason_left="APPROACH_RISK",
                    reason_right="FIRE",
                    input_validity="VALID",
                    warning_code="NONE",
                ),
            ),
        ],
        id="FTC-D-27",
    ),
    # FTC-D-28 (SWR-019, SWR-005, SWR-018) D-28: 접근위험(순위 4)와 ISOFIX(순위
    # 8)가 같은 평가·같은 쪽에 성립할 때 상위 규칙이 이긴다. 규칙 순서
    # 뒤바뀜·하위 규칙 누수 결함 검출
    pytest.param(
        [
            Step(
                10.00,
                expect=dict(
                    lock_left="RELEASE",
                    lock_right="RELEASE",
                    state="NORMAL",
                    reason_code="NO_CHANGE",
                    priority_reason="no_change",
                ),
            ),
            Step(
                10.05,
                sig=dict(rear_left_approach_risk=True, isofix_left=True),
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
        id="FTC-D-28",
    ),
    # FTC-D-29 (SWR-019, SWR-005, SWR-003) D-29: 접근위험(순위 4)와 자동
    # 잠금(순위 9)가 같은 평가·같은 쪽에 성립할 때 상위 규칙이 이긴다. 규칙
    # 순서 뒤바뀜·하위 규칙 누수 결함 검출
    pytest.param(
        [
            Step(
                10.00,
                expect=dict(
                    lock_left="RELEASE",
                    lock_right="RELEASE",
                    state="NORMAL",
                    reason_code="NO_CHANGE",
                    priority_reason="no_change",
                ),
            ),
            Step(
                10.05,
                sig=dict(rear_left_approach_risk=True, vehicle_speed_kph=3.0),
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
        id="FTC-D-29",
    ),
    # FTC-D-30 (SWR-019, SWR-005, SWR-004) D-30: 접근위험(순위 4)와 운전자
    # 명령(순위 10)가 같은 평가·같은 쪽에 성립할 때 상위 규칙이 이긴다. 규칙
    # 순서 뒤바뀜·하위 규칙 누수 결함 검출
    pytest.param(
        [
            Step(
                10.00,
                expect=dict(
                    lock_left="RELEASE",
                    lock_right="RELEASE",
                    state="NORMAL",
                    reason_code="NO_CHANGE",
                    priority_reason="no_change",
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
        id="FTC-D-30",
    ),
    # FTC-D-31 (SWR-019, SWR-013, SWR-020) D-31: QM 입력 이상(순위 5)와 시동
    # OFF(순위 6)가 같은 평가·같은 쪽에 성립할 때 상위 규칙이 이긴다. 규칙 순서
    # 뒤바뀜·하위 규칙 누수 결함 검출
    pytest.param(
        [
            Step(
                10.00,
                sig=dict(vehicle_speed_kph=3.0),
                expect=dict(
                    lock_left="LOCK",
                    lock_right="LOCK",
                    reason_code="AUTO_LOCK",
                    priority_reason="auto_lock",
                ),
            ),
            Step(
                10.05,
                sig=dict(gear="X", ignition_on=False),
                expect=dict(
                    lock_left="LOCK",
                    lock_right="LOCK",
                    state="DEGRADED",
                    reason_code="INPUT_INVALID",
                    priority_reason="input_invalid",
                    reason_left="INPUT_INVALID",
                    reason_right="INPUT_INVALID",
                    input_validity="INVALID",
                    warning_code="NONE",
                ),
            ),
        ],
        id="FTC-D-31",
    ),
    # FTC-D-32 (SWR-019, SWR-013, SWR-017) D-32: QM 입력 이상(순위 5)와 강제
    # 해제(화재)(순위 7)가 같은 평가·같은 쪽에 성립할 때 상위 규칙이 이긴다.
    # 규칙 순서 뒤바뀜·하위 규칙 누수 결함 검출
    pytest.param(
        [
            Step(
                10.00,
                sig=dict(vehicle_speed_kph=3.0),
                expect=dict(
                    lock_left="LOCK",
                    lock_right="LOCK",
                    reason_code="AUTO_LOCK",
                    priority_reason="auto_lock",
                ),
            ),
            Step(
                10.05,
                sig=dict(gear="X", fire_detected=True),
                expect=dict(
                    lock_left="LOCK",
                    lock_right="LOCK",
                    state="DEGRADED",
                    reason_code="INPUT_INVALID",
                    priority_reason="input_invalid",
                    reason_left="INPUT_INVALID",
                    reason_right="INPUT_INVALID",
                    input_validity="INVALID",
                    warning_code="NONE",
                ),
            ),
        ],
        id="FTC-D-32",
    ),
    # FTC-D-33 (SWR-019, SWR-013, SWR-018) D-33: QM 입력 이상(순위 5)와
    # ISOFIX(순위 8)가 같은 평가·같은 쪽에 성립할 때 상위 규칙이 이긴다. 규칙
    # 순서 뒤바뀜·하위 규칙 누수 결함 검출
    pytest.param(
        [
            Step(
                10.00,
                expect=dict(
                    lock_left="RELEASE",
                    lock_right="RELEASE",
                    state="NORMAL",
                    reason_code="NO_CHANGE",
                    priority_reason="no_change",
                ),
            ),
            Step(
                10.05,
                sig=dict(gear="X", isofix_left=True),
                expect=dict(
                    lock_left="RELEASE",
                    lock_right="RELEASE",
                    state="DEGRADED",
                    reason_code="INPUT_INVALID",
                    priority_reason="input_invalid",
                    reason_left="INPUT_INVALID",
                    reason_right="INPUT_INVALID",
                    input_validity="INVALID",
                    warning_code="NONE",
                ),
            ),
        ],
        id="FTC-D-33",
    ),
    # FTC-D-34 (SWR-019, SWR-013, SWR-003) D-34: QM 입력 이상(순위 5)와 자동
    # 잠금(순위 9)가 같은 평가·같은 쪽에 성립할 때 상위 규칙이 이긴다. 규칙
    # 순서 뒤바뀜·하위 규칙 누수 결함 검출
    pytest.param(
        [
            Step(
                10.00,
                expect=dict(
                    lock_left="RELEASE",
                    lock_right="RELEASE",
                    state="NORMAL",
                    reason_code="NO_CHANGE",
                    priority_reason="no_change",
                ),
            ),
            Step(
                10.05,
                sig=dict(gear="X", vehicle_speed_kph=3.0),
                expect=dict(
                    lock_left="RELEASE",
                    lock_right="RELEASE",
                    state="DEGRADED",
                    reason_code="INPUT_INVALID",
                    priority_reason="input_invalid",
                    reason_left="INPUT_INVALID",
                    reason_right="INPUT_INVALID",
                    input_validity="INVALID",
                    warning_code="NONE",
                ),
            ),
        ],
        id="FTC-D-34",
    ),
    # FTC-D-35 (SWR-019, SWR-013, SWR-004) D-35: QM 입력 이상(순위 5)와 운전자
    # 명령(순위 10)가 같은 평가·같은 쪽에 성립할 때 상위 규칙이 이긴다. 규칙
    # 순서 뒤바뀜·하위 규칙 누수 결함 검출
    pytest.param(
        [
            Step(
                10.00,
                sig=dict(vehicle_speed_kph=3.0),
                expect=dict(
                    lock_left="LOCK",
                    lock_right="LOCK",
                    reason_code="AUTO_LOCK",
                    priority_reason="auto_lock",
                ),
            ),
            Step(
                10.05,
                sig=dict(gear="X"),
                cmds=[cmd("left", "unlock")],
                expect=dict(
                    lock_left="LOCK",
                    lock_right="LOCK",
                    state="DEGRADED",
                    reason_code="INPUT_INVALID",
                    priority_reason="input_invalid",
                    reason_left="INPUT_INVALID",
                    reason_right="INPUT_INVALID",
                    input_validity="INVALID",
                    warning_code="NONE",
                ),
            ),
        ],
        id="FTC-D-35",
    ),
    # FTC-D-36 (SWR-019, SWR-020, SWR-017) D-36: 시동 OFF(순위 6)와 강제
    # 해제(화재)(순위 7)가 같은 평가·같은 쪽에 성립할 때 상위 규칙이 이긴다.
    # 규칙 순서 뒤바뀜·하위 규칙 누수 결함 검출
    pytest.param(
        [
            Step(
                10.00,
                sig=dict(vehicle_speed_kph=3.0),
                expect=dict(
                    lock_left="LOCK",
                    lock_right="LOCK",
                    reason_code="AUTO_LOCK",
                    priority_reason="auto_lock",
                ),
            ),
            Step(
                10.05,
                sig=dict(ignition_on=False, fire_detected=True),
                expect=dict(
                    lock_left="RELEASE",
                    lock_right="RELEASE",
                    state="OFF",
                    reason_code="IGNITION_OFF",
                    priority_reason="ignition_off",
                    reason_left="IGNITION_OFF",
                    reason_right="IGNITION_OFF",
                    input_validity="VALID",
                    warning_code="NONE",
                ),
            ),
        ],
        id="FTC-D-36",
    ),
    # FTC-D-37 (SWR-019, SWR-020, SWR-018) D-37: 시동 OFF(순위 6)와 ISOFIX(순위
    # 8)가 같은 평가·같은 쪽에 성립할 때 상위 규칙이 이긴다. 규칙 순서
    # 뒤바뀜·하위 규칙 누수 결함 검출
    pytest.param(
        [
            Step(
                10.00,
                sig=dict(vehicle_speed_kph=3.0),
                expect=dict(
                    lock_left="LOCK",
                    lock_right="LOCK",
                    reason_code="AUTO_LOCK",
                    priority_reason="auto_lock",
                ),
            ),
            Step(
                10.05,
                sig=dict(ignition_on=False, isofix_left=True),
                expect=dict(
                    lock_left="RELEASE",
                    lock_right="RELEASE",
                    state="OFF",
                    reason_code="IGNITION_OFF",
                    priority_reason="ignition_off",
                    reason_left="IGNITION_OFF",
                    reason_right="IGNITION_OFF",
                    input_validity="VALID",
                    warning_code="NONE",
                ),
            ),
        ],
        id="FTC-D-37",
    ),
    # FTC-D-38 (SWR-019, SWR-020, SWR-003) D-38: 시동 OFF(순위 6)와 자동
    # 잠금(순위 9)가 같은 평가·같은 쪽에 성립할 때 상위 규칙이 이긴다. 규칙
    # 순서 뒤바뀜·하위 규칙 누수 결함 검출
    pytest.param(
        [
            Step(
                10.00,
                sig=dict(vehicle_speed_kph=3.0),
                expect=dict(
                    lock_left="LOCK",
                    lock_right="LOCK",
                    reason_code="AUTO_LOCK",
                    priority_reason="auto_lock",
                ),
            ),
            Step(
                10.05,
                sig=dict(ignition_on=False, vehicle_speed_kph=3.0),
                expect=dict(
                    lock_left="RELEASE",
                    lock_right="RELEASE",
                    state="OFF",
                    reason_code="IGNITION_OFF",
                    priority_reason="ignition_off",
                    reason_left="IGNITION_OFF",
                    reason_right="IGNITION_OFF",
                    input_validity="VALID",
                    warning_code="NONE",
                ),
            ),
        ],
        id="FTC-D-38",
    ),
    # FTC-D-39 (SWR-019, SWR-020, SWR-004) D-39: 시동 OFF(순위 6)와 운전자
    # 명령(순위 10)가 같은 평가·같은 쪽에 성립할 때 상위 규칙이 이긴다. 규칙
    # 순서 뒤바뀜·하위 규칙 누수 결함 검출
    pytest.param(
        [
            Step(
                10.00,
                sig=dict(vehicle_speed_kph=3.0),
                expect=dict(
                    lock_left="LOCK",
                    lock_right="LOCK",
                    reason_code="AUTO_LOCK",
                    priority_reason="auto_lock",
                ),
            ),
            Step(
                10.05,
                sig=dict(ignition_on=False),
                cmds=[cmd("left", "unlock")],
                expect=dict(
                    lock_left="RELEASE",
                    lock_right="RELEASE",
                    state="OFF",
                    reason_code="IGNITION_OFF",
                    priority_reason="ignition_off",
                    reason_left="IGNITION_OFF",
                    reason_right="IGNITION_OFF",
                    input_validity="VALID",
                    warning_code="NONE",
                ),
            ),
        ],
        id="FTC-D-39",
    ),
    # FTC-D-40 (SWR-019, SWR-017, SWR-018) D-40: 강제 해제(화재)(순위 7)와
    # ISOFIX(순위 8)가 같은 평가·같은 쪽에 성립할 때 상위 규칙이 이긴다. 규칙
    # 순서 뒤바뀜·하위 규칙 누수 결함 검출
    pytest.param(
        [
            Step(
                10.00,
                sig=dict(vehicle_speed_kph=3.0),
                expect=dict(
                    lock_left="LOCK",
                    lock_right="LOCK",
                    reason_code="AUTO_LOCK",
                    priority_reason="auto_lock",
                ),
            ),
            Step(
                10.05,
                sig=dict(fire_detected=True, isofix_left=True),
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
        id="FTC-D-40",
    ),
    # FTC-D-41 (SWR-019, SWR-017, SWR-003) D-41: 강제 해제(화재)(순위 7)와 자동
    # 잠금(순위 9)가 같은 평가·같은 쪽에 성립할 때 상위 규칙이 이긴다. 규칙
    # 순서 뒤바뀜·하위 규칙 누수 결함 검출
    pytest.param(
        [
            Step(
                10.00,
                sig=dict(vehicle_speed_kph=3.0),
                expect=dict(
                    lock_left="LOCK",
                    lock_right="LOCK",
                    reason_code="AUTO_LOCK",
                    priority_reason="auto_lock",
                ),
            ),
            Step(
                10.05,
                sig=dict(fire_detected=True, vehicle_speed_kph=3.0),
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
        id="FTC-D-41",
    ),
    # FTC-D-42 (SWR-019, SWR-017, SWR-004) D-42: 강제 해제(화재)(순위 7)와
    # 운전자 명령(순위 10)가 같은 평가·같은 쪽에 성립할 때 상위 규칙이 이긴다.
    # 규칙 순서 뒤바뀜·하위 규칙 누수 결함 검출
    pytest.param(
        [
            Step(
                10.00,
                sig=dict(vehicle_speed_kph=3.0),
                expect=dict(
                    lock_left="LOCK",
                    lock_right="LOCK",
                    reason_code="AUTO_LOCK",
                    priority_reason="auto_lock",
                ),
            ),
            Step(
                10.05,
                sig=dict(fire_detected=True),
                cmds=[cmd("left", "unlock")],
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
        id="FTC-D-42",
    ),
    # FTC-D-43 (SWR-019, SWR-018, SWR-003) D-43: ISOFIX(순위 8)와 자동
    # 잠금(순위 9)가 같은 평가·같은 쪽에 성립할 때 상위 규칙이 이긴다. 규칙
    # 순서 뒤바뀜·하위 규칙 누수 결함 검출
    pytest.param(
        [
            Step(
                10.00,
                expect=dict(
                    lock_left="RELEASE",
                    lock_right="RELEASE",
                    state="NORMAL",
                    reason_code="NO_CHANGE",
                    priority_reason="no_change",
                ),
            ),
            Step(
                10.05,
                sig=dict(isofix_left=True, vehicle_speed_kph=3.0),
                expect=dict(
                    lock_left="LOCK",
                    lock_right="LOCK",
                    state="NORMAL",
                    reason_code="ISOFIX",
                    priority_reason="isofix",
                    reason_left="ISOFIX",
                    reason_right="AUTO_LOCK",
                    input_validity="VALID",
                    warning_code="NONE",
                ),
            ),
        ],
        id="FTC-D-43",
    ),
    # FTC-D-44 (SWR-019, SWR-018, SWR-004) D-44: ISOFIX(순위 8)와 운전자
    # 명령(순위 10)가 같은 평가·같은 쪽에 성립할 때 상위 규칙이 이긴다. 규칙
    # 순서 뒤바뀜·하위 규칙 누수 결함 검출
    pytest.param(
        [
            Step(
                10.00,
                expect=dict(
                    lock_left="RELEASE",
                    lock_right="RELEASE",
                    state="NORMAL",
                    reason_code="NO_CHANGE",
                    priority_reason="no_change",
                ),
            ),
            Step(
                10.05,
                sig=dict(isofix_left=True),
                cmds=[cmd("left", "unlock")],
                expect=dict(
                    lock_left="LOCK",
                    lock_right="RELEASE",
                    state="NORMAL",
                    reason_code="ISOFIX",
                    priority_reason="isofix",
                    reason_left="ISOFIX",
                    reason_right="NO_CHANGE",
                    input_validity="VALID",
                    warning_code="NONE",
                ),
            ),
        ],
        id="FTC-D-44",
    ),
    # FTC-D-45 (SWR-019, SWR-003, SWR-004) D-45: 자동 잠금(순위 9)와 운전자
    # 명령(순위 10)가 같은 평가·같은 쪽에 성립할 때 상위 규칙이 이긴다. 규칙
    # 순서 뒤바뀜·하위 규칙 누수 결함 검출
    pytest.param(
        [
            Step(
                10.00,
                expect=dict(
                    lock_left="RELEASE",
                    lock_right="RELEASE",
                    state="NORMAL",
                    reason_code="NO_CHANGE",
                    priority_reason="no_change",
                ),
            ),
            Step(
                10.05,
                sig=dict(vehicle_speed_kph=3.0),
                cmds=[cmd("left", "unlock")],
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
        id="FTC-D-45",
    ),
]


@pytest.mark.parametrize("steps", D_CASES)
def test_ftc_d_rule_pairs(bench, steps):
    """FTC-D-01~FTC-D-45 (SWR-019 외, 케이스별 basis는 주석)

    부록 A.1 결정표: 순위 1~10 규칙 쌍이 같은 평가·같은 쪽에 성립할 때
    상위 규칙의 출력·이유·state. 케이스별 tc_id는 각 pytest.param의
    id다.
    """
    play(bench, steps)


P_CASES = [
    # FTC-P-01 (SWR-019, SWR-008, SWR-007) P-01: PENDING 필터가 순위 8~10의
    # RELEASE→LOCK만 막고 순위 1~7 결과는 막지 않음. 필터 적용 범위 오류(상위
    # 규칙까지 막거나 8~10을 못 막음) 검출
    pytest.param(
        [
            Step(
                10.00,
                sig=dict(crash_status="CONFIRMED"),
                expect=dict(
                    lock_left="RELEASE",
                    lock_right="RELEASE",
                    state="NORMAL",
                    reason_code="CRASH_CONFIRMED",
                    priority_reason="crash_confirmed",
                ),
            ),
            Step(
                10.05,
                sig=dict(crash_status="PENDING"),
                expect=dict(
                    lock_left="RELEASE",
                    lock_right="RELEASE",
                    state="NORMAL",
                    reason_code="CRASH_CONFIRMED",
                    priority_reason="crash_confirmed",
                    reason_left="CRASH_CONFIRMED",
                    reason_right="CRASH_CONFIRMED",
                    input_validity="VALID",
                    warning_code="NONE",
                ),
            ),
        ],
        id="FTC-P-01",
    ),
    # FTC-P-02 (SWR-019, SWR-008, SWR-013) P-02: PENDING 필터가 순위 8~10의
    # RELEASE→LOCK만 막고 순위 1~7 결과는 막지 않음. 필터 적용 범위 오류(상위
    # 규칙까지 막거나 8~10을 못 막음) 검출
    pytest.param(
        [
            Step(
                10.00,
                sig=dict(crash_status="PENDING"),
                expect=dict(
                    lock_left="RELEASE",
                    lock_right="RELEASE",
                    state="NORMAL",
                    reason_code="NO_CHANGE",
                    priority_reason="no_change",
                ),
            ),
            Step(
                10.05,
                sig=dict(rear_right_approach_risk=1, crash_status="PENDING"),
                expect=dict(
                    lock_left="RELEASE",
                    lock_right="RELEASE",
                    state="DEGRADED",
                    reason_code="INPUT_INVALID",
                    priority_reason="input_invalid",
                    reason_left="INPUT_INVALID",
                    reason_right="INPUT_INVALID",
                    input_validity="INVALID",
                    warning_code="NONE",
                ),
            ),
        ],
        id="FTC-P-02",
    ),
    # FTC-P-03 (SWR-019, SWR-008, SWR-021) P-03: PENDING 필터가 순위 8~10의
    # RELEASE→LOCK만 막고 순위 1~7 결과는 막지 않음. 필터 적용 범위 오류(상위
    # 규칙까지 막거나 8~10을 못 막음) 검출
    pytest.param(
        [
            Step(
                10.00,
                sig=dict(crash_status="PENDING"),
                expect=dict(
                    lock_left="RELEASE",
                    lock_right="RELEASE",
                    state="NORMAL",
                    reason_code="NO_CHANGE",
                    priority_reason="no_change",
                ),
            ),
            Step(
                10.05,
                sig=dict(sensor_fault=True, crash_status="PENDING"),
                expect=dict(
                    lock_left="RELEASE",
                    lock_right="RELEASE",
                    state="FAULT",
                    reason_code="SENSOR_FAULT",
                    priority_reason="sensor_fault",
                    reason_left="SENSOR_FAULT",
                    reason_right="SENSOR_FAULT",
                    input_validity="VALID",
                    warning_code="W_SENSOR_FAULT",
                ),
            ),
        ],
        id="FTC-P-03",
    ),
    # FTC-P-04 (SWR-019, SWR-008, SWR-005) P-04: PENDING 필터가 순위 8~10의
    # RELEASE→LOCK만 막고 순위 1~7 결과는 막지 않음. 필터 적용 범위 오류(상위
    # 규칙까지 막거나 8~10을 못 막음) 검출
    pytest.param(
        [
            Step(
                10.00,
                sig=dict(crash_status="PENDING"),
                expect=dict(
                    lock_left="RELEASE",
                    lock_right="RELEASE",
                    state="NORMAL",
                    reason_code="NO_CHANGE",
                    priority_reason="no_change",
                ),
            ),
            Step(
                10.05,
                sig=dict(rear_left_approach_risk=True, crash_status="PENDING"),
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
        id="FTC-P-04",
    ),
    # FTC-P-05 (SWR-019, SWR-008, SWR-013) P-05: PENDING 필터가 순위 8~10의
    # RELEASE→LOCK만 막고 순위 1~7 결과는 막지 않음. 필터 적용 범위 오류(상위
    # 규칙까지 막거나 8~10을 못 막음) 검출
    pytest.param(
        [
            Step(
                10.00,
                sig=dict(crash_status="PENDING"),
                expect=dict(
                    lock_left="RELEASE",
                    lock_right="RELEASE",
                    state="NORMAL",
                    reason_code="NO_CHANGE",
                    priority_reason="no_change",
                ),
            ),
            Step(
                10.05,
                sig=dict(gear="X", crash_status="PENDING"),
                expect=dict(
                    lock_left="RELEASE",
                    lock_right="RELEASE",
                    state="DEGRADED",
                    reason_code="INPUT_INVALID",
                    priority_reason="input_invalid",
                    reason_left="INPUT_INVALID",
                    reason_right="INPUT_INVALID",
                    input_validity="INVALID",
                    warning_code="NONE",
                ),
            ),
        ],
        id="FTC-P-05",
    ),
    # FTC-P-06 (SWR-019, SWR-008, SWR-020) P-06: PENDING 필터가 순위 8~10의
    # RELEASE→LOCK만 막고 순위 1~7 결과는 막지 않음. 필터 적용 범위 오류(상위
    # 규칙까지 막거나 8~10을 못 막음) 검출
    pytest.param(
        [
            Step(
                10.00,
                sig=dict(crash_status="PENDING"),
                expect=dict(
                    lock_left="RELEASE",
                    lock_right="RELEASE",
                    state="NORMAL",
                    reason_code="NO_CHANGE",
                    priority_reason="no_change",
                ),
            ),
            Step(
                10.05,
                sig=dict(ignition_on=False, crash_status="PENDING"),
                expect=dict(
                    lock_left="RELEASE",
                    lock_right="RELEASE",
                    state="OFF",
                    reason_code="IGNITION_OFF",
                    priority_reason="ignition_off",
                    reason_left="IGNITION_OFF",
                    reason_right="IGNITION_OFF",
                    input_validity="VALID",
                    warning_code="NONE",
                ),
            ),
        ],
        id="FTC-P-06",
    ),
    # FTC-P-07 (SWR-019, SWR-008, SWR-017) P-07: PENDING 필터가 순위 8~10의
    # RELEASE→LOCK만 막고 순위 1~7 결과는 막지 않음. 필터 적용 범위 오류(상위
    # 규칙까지 막거나 8~10을 못 막음) 검출
    pytest.param(
        [
            Step(
                10.00,
                sig=dict(crash_status="PENDING"),
                expect=dict(
                    lock_left="RELEASE",
                    lock_right="RELEASE",
                    state="NORMAL",
                    reason_code="NO_CHANGE",
                    priority_reason="no_change",
                ),
            ),
            Step(
                10.05,
                sig=dict(fire_detected=True, crash_status="PENDING"),
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
        id="FTC-P-07",
    ),
    # FTC-P-08 (SWR-019, SWR-008, SWR-018) P-08: PENDING 필터가 순위 8~10의
    # RELEASE→LOCK만 막고 순위 1~7 결과는 막지 않음. 필터 적용 범위 오류(상위
    # 규칙까지 막거나 8~10을 못 막음) 검출
    pytest.param(
        [
            Step(
                10.00,
                sig=dict(crash_status="PENDING"),
                expect=dict(
                    lock_left="RELEASE",
                    lock_right="RELEASE",
                    state="NORMAL",
                    reason_code="NO_CHANGE",
                    priority_reason="no_change",
                ),
            ),
            Step(
                10.05,
                sig=dict(isofix_left=True, crash_status="PENDING"),
                expect=dict(
                    lock_left="RELEASE",
                    lock_right="RELEASE",
                    state="NORMAL",
                    reason_code="CRASH_PENDING",
                    priority_reason="crash_pending",
                    reason_left="CRASH_PENDING",
                    reason_right="NO_CHANGE",
                    input_validity="VALID",
                    warning_code="NONE",
                ),
            ),
        ],
        id="FTC-P-08",
    ),
    # FTC-P-09 (SWR-019, SWR-008, SWR-003) P-09: PENDING 필터가 순위 8~10의
    # RELEASE→LOCK만 막고 순위 1~7 결과는 막지 않음. 필터 적용 범위 오류(상위
    # 규칙까지 막거나 8~10을 못 막음) 검출
    pytest.param(
        [
            Step(
                10.00,
                sig=dict(crash_status="PENDING"),
                expect=dict(
                    lock_left="RELEASE",
                    lock_right="RELEASE",
                    state="NORMAL",
                    reason_code="NO_CHANGE",
                    priority_reason="no_change",
                ),
            ),
            Step(
                10.05,
                sig=dict(vehicle_speed_kph=3.0, crash_status="PENDING"),
                expect=dict(
                    lock_left="RELEASE",
                    lock_right="RELEASE",
                    state="NORMAL",
                    reason_code="CRASH_PENDING",
                    priority_reason="crash_pending",
                    reason_left="CRASH_PENDING",
                    reason_right="CRASH_PENDING",
                    input_validity="VALID",
                    warning_code="NONE",
                ),
            ),
        ],
        id="FTC-P-09",
    ),
    # FTC-P-10 (SWR-019, SWR-008, SWR-002) P-10: PENDING 필터가 순위 8~10의
    # RELEASE→LOCK만 막고 순위 1~7 결과는 막지 않음. 필터 적용 범위 오류(상위
    # 규칙까지 막거나 8~10을 못 막음) 검출
    pytest.param(
        [
            Step(
                10.00,
                sig=dict(crash_status="PENDING"),
                expect=dict(
                    lock_left="RELEASE",
                    lock_right="RELEASE",
                    state="NORMAL",
                    reason_code="NO_CHANGE",
                    priority_reason="no_change",
                ),
            ),
            Step(
                10.05,
                sig=dict(crash_status="PENDING"),
                cmds=[cmd("left", "lock")],
                expect=dict(
                    lock_left="RELEASE",
                    lock_right="RELEASE",
                    state="NORMAL",
                    reason_code="CRASH_PENDING",
                    priority_reason="crash_pending",
                    reason_left="CRASH_PENDING",
                    reason_right="NO_CHANGE",
                    input_validity="VALID",
                    warning_code="NONE",
                ),
            ),
        ],
        id="FTC-P-10",
    ),
]


@pytest.mark.parametrize("steps", P_CASES)
def test_ftc_p_pending_filter(bench, steps):
    """FTC-P-01~FTC-P-10 (SWR-019, SWR-008 외, 케이스별 basis는 주석)

    부록 A.2 결정표: 충돌 PENDING 필터와 각 순위 규칙의 조합.
    케이스별 tc_id는 각 pytest.param의 id다.
    """
    play(bench, steps)
