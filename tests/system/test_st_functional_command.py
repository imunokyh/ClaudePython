"""@brief SWE.6 기능 시험: 운전자 명령·자동 잠금 (SWR-001~004).

근거: docs/swe6/system-test-cases.json
"""

import pytest
from tests.system.harness import cmd
from tests.system.st_support import Step, check, play, run


def test_ftc_101_same_side_lock_then_unlock_last_wins(bench):
    """FTC-101 (SWR-002)

    같은 평가에서 같은 쪽 명령이 lock→unlock 순이면 마지막 명령(unlock)이
    남는지 확인. '첫 명령 우선' 또는 'lock 우선' 결함 검출
    """
    # 1단계 t=10.00: 같은 쪽 명령 2개: lock 다음 unlock
    st = run(bench, 10.00, [cmd("left", "lock"), cmd("left", "unlock")])
    check(
        st,
        1,
        lock_left="RELEASE",
        lock_right="RELEASE",
        state="NORMAL",
        reason_code="DRIVER_COMMAND",
        priority_reason="driver_command",
        reason_left="DRIVER_COMMAND",
        reason_right="NO_CHANGE",
    )


def test_ftc_102_same_side_unlock_then_lock_last_wins(bench):
    """FTC-102 (SWR-002)

    명령 순서를 뒤집어(unlock→lock) 마지막 명령(lock)이 남는지 확인. 'unlock
    우선' 결함 검출(FTC-101과 반대 방향)
    """
    # 1단계 t=10.00: 같은 쪽 명령 2개: unlock 다음 lock
    st = run(bench, 10.00, [cmd("left", "unlock"), cmd("left", "lock")])
    check(
        st,
        1,
        lock_left="LOCK",
        lock_right="RELEASE",
        state="NORMAL",
        reason_code="DRIVER_COMMAND",
        priority_reason="driver_command",
        reason_left="DRIVER_COMMAND",
        reason_right="NO_CHANGE",
    )


def test_ftc_103_all_split_in_received_order(bench):
    """FTC-103 (SWR-002)

    all이 left·right 두 명령으로 분해되어 받은 순서대로 처리되는지 확인(all
    lock 뒤 left unlock이면 좌 RELEASE, 우 LOCK). all을 마지막에 일괄
    적용하거나 분해하지 않는 결함 검출
    """
    # 1단계 t=10.00: all lock 뒤에 left unlock
    st = run(bench, 10.00, [cmd("all", "lock"), cmd("left", "unlock")])
    check(
        st,
        1,
        lock_left="RELEASE",
        lock_right="LOCK",
        state="NORMAL",
        reason_code="DRIVER_COMMAND",
        priority_reason="driver_command",
        reason_left="DRIVER_COMMAND",
        reason_right="DRIVER_COMMAND",
    )


def test_ftc_104_unlock_applies_below_3kph(bench):
    """FTC-104 (SWR-004)

    3.0 km/h 미만(2.9, 2.99 km/h)에서 unlock이 적용되는지 확인. 임계 비교를 <=
    로 구현했거나 차속을 0.1 단위로 반올림(2.99→3.0)하는 결함 검출
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
    # 2단계 t=10.05
    st = run(bench, 10.05, [cmd("left", "unlock")], vehicle_speed_kph=2.9)
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
    # 3단계 t=10.10: 좌 다시 LOCK
    st = run(bench, 10.10, [cmd("left", "lock")], vehicle_speed_kph=2.99)
    check(
        st,
        3,
        lock_left="LOCK",
        lock_right="LOCK",
        reason_code="DRIVER_COMMAND",
        priority_reason="driver_command",
    )
    # 4단계 t=10.15: 임계값 직하 2.99 km/h
    st = run(bench, 10.15, [cmd("left", "unlock")], vehicle_speed_kph=2.99)
    check(
        st,
        4,
        lock_left="RELEASE",
        lock_right="LOCK",
        state="NORMAL",
        reason_code="DRIVER_COMMAND",
        priority_reason="driver_command",
        reason_left="DRIVER_COMMAND",
    )


def test_ftc_105_unlock_blocked_by_auto_lock_at_3kph(bench):
    """FTC-105 (SWR-004, SWR-003, SWR-019)

    3.0 km/h에서 unlock이 적용되지 않고 자동 잠금(순위 9)이 우선하는지 확인.
    임계 비교 연산자 오류(< vs <=) 검출
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
    # 2단계 t=10.05: 임계값 3.0 km/h에서 unlock
    st = run(
        bench, 10.05, [cmd("left", "unlock", "avn")], vehicle_speed_kph=3.0
    )
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
        warning_code="NONE",
    )


def test_ftc_106_auto_lock_threshold_and_hold(bench):
    """FTC-106 (SWR-003)

    2.99 km/h는 잠금 없음, 3.0 km/h에서 첫 평가에 AUTO_LOCK, 이후 차속이 3.0
    미만으로 내려가도 LOCK 유지. 임계 오류와 '차속 하강 시 해제' 결함 검출
    """
    # 1단계 t=10.00: 임계 직하
    st = run(bench, 10.00, vehicle_speed_kph=2.99)
    check(
        st,
        1,
        lock_left="RELEASE",
        lock_right="RELEASE",
        state="NORMAL",
        reason_code="NO_CHANGE",
        priority_reason="no_change",
    )
    # 2단계 t=10.05: 임계값
    st = run(bench, 10.05, vehicle_speed_kph=3.0)
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
    )
    # 3단계 t=10.10: 차속 저하 후에도 유지
    st = run(bench, 10.10, vehicle_speed_kph=2.99)
    check(
        st,
        3,
        lock_left="LOCK",
        lock_right="LOCK",
        state="NORMAL",
        reason_code="NO_CHANGE",
        priority_reason="no_change",
    )
    # 4단계 t=10.15
    st = run(bench, 10.15, vehicle_speed_kph=0.0)
    check(
        st,
        4,
        lock_left="LOCK",
        lock_right="LOCK",
        state="NORMAL",
        reason_code="NO_CHANGE",
        priority_reason="no_change",
    )


def test_ftc_107_auto_lock_reapplies_on_reentry(bench):
    """FTC-107 (SWR-003, SWR-004)

    자동 잠금이 1회성이 아니라 3.0 km/h 이상 평가마다 적용되고(재진입), 하강
    구간에서 unlock이 가능하며 재잠금이 없음을 확인. 1회성 플래그·래치 결함
    검출
    """
    # 1단계 t=10.00
    st = run(bench, 10.00, vehicle_speed_kph=3.0)
    check(
        st,
        1,
        lock_left="LOCK",
        lock_right="LOCK",
        reason_code="AUTO_LOCK",
        priority_reason="auto_lock",
    )
    # 2단계 t=10.05
    st = run(bench, 10.05, vehicle_speed_kph=2.0)
    check(
        st,
        2,
        lock_left="LOCK",
        lock_right="LOCK",
        reason_code="NO_CHANGE",
        priority_reason="no_change",
    )
    # 3단계 t=10.10
    st = run(bench, 10.10, [cmd("left", "unlock")], vehicle_speed_kph=2.0)
    check(
        st,
        3,
        lock_left="RELEASE",
        lock_right="LOCK",
        state="NORMAL",
        reason_code="DRIVER_COMMAND",
        priority_reason="driver_command",
        reason_left="DRIVER_COMMAND",
        reason_right="NO_CHANGE",
    )
    # 4단계 t=10.15: 2.0 km/h 유지: 자동 재잠금 없음
    st = run(bench, 10.15, vehicle_speed_kph=2.0)
    check(
        st,
        4,
        lock_left="RELEASE",
        lock_right="LOCK",
        state="NORMAL",
        reason_code="NO_CHANGE",
        priority_reason="no_change",
        reason_left="NO_CHANGE",
        reason_right="NO_CHANGE",
    )
    # 5단계 t=10.20: 다시 3.0 km/h: 자동 잠금 재적용
    st = run(bench, 10.20, vehicle_speed_kph=3.0)
    check(
        st,
        5,
        lock_left="LOCK",
        lock_right="LOCK",
        state="NORMAL",
        reason_code="AUTO_LOCK",
        priority_reason="auto_lock",
        reason_left="AUTO_LOCK",
        reason_right="AUTO_LOCK",
    )


PW01_CASES = [
    # FTC-PW01-01 (SWR-001, SWR-002) PICT-01#1: source=voice, action=unlock,
    # side=right 조합 처리. source별 분기 누락·side/action 조합 결함
    # 검출(수용기준이 24개 조합 전수를 요구하므로 3-way=전수)
    pytest.param(
        [
            Step(
                10.00,
                cmds=[cmd("all", "lock")],
                expect=dict(
                    lock_left="LOCK",
                    lock_right="LOCK",
                    reason_code="DRIVER_COMMAND",
                    priority_reason="driver_command",
                ),
            ),
            Step(
                10.05,
                cmds=[cmd("right", "unlock", "voice")],
                expect=dict(
                    lock_left="LOCK",
                    lock_right="RELEASE",
                    state="NORMAL",
                    reason_code="DRIVER_COMMAND",
                    priority_reason="driver_command",
                    reason_left="NO_CHANGE",
                    reason_right="DRIVER_COMMAND",
                    input_validity="VALID",
                    warning_code="NONE",
                ),
            ),
        ],
        id="FTC-PW01-01",
    ),
    # FTC-PW01-02 (SWR-001, SWR-002) PICT-01#2: source=mobile_app,
    # action=unlock, side=right 조합 처리. source별 분기 누락·side/action 조합
    # 결함 검출(수용기준이 24개 조합 전수를 요구하므로 3-way=전수)
    pytest.param(
        [
            Step(
                10.00,
                cmds=[cmd("all", "lock")],
                expect=dict(
                    lock_left="LOCK",
                    lock_right="LOCK",
                    reason_code="DRIVER_COMMAND",
                    priority_reason="driver_command",
                ),
            ),
            Step(
                10.05,
                cmds=[cmd("right", "unlock", "mobile_app")],
                expect=dict(
                    lock_left="LOCK",
                    lock_right="RELEASE",
                    state="NORMAL",
                    reason_code="DRIVER_COMMAND",
                    priority_reason="driver_command",
                    reason_left="NO_CHANGE",
                    reason_right="DRIVER_COMMAND",
                    input_validity="VALID",
                    warning_code="NONE",
                ),
            ),
        ],
        id="FTC-PW01-02",
    ),
    # FTC-PW01-03 (SWR-001, SWR-002) PICT-01#3: source=physical_button,
    # action=lock, side=right 조합 처리. source별 분기 누락·side/action 조합
    # 결함 검출(수용기준이 24개 조합 전수를 요구하므로 3-way=전수)
    pytest.param(
        [
            Step(
                10.00,
                expect=dict(
                    lock_left="RELEASE",
                    lock_right="RELEASE",
                    reason_code="NO_CHANGE",
                    priority_reason="no_change",
                ),
            ),
            Step(
                10.05,
                cmds=[cmd("right", "lock")],
                expect=dict(
                    lock_left="RELEASE",
                    lock_right="LOCK",
                    state="NORMAL",
                    reason_code="DRIVER_COMMAND",
                    priority_reason="driver_command",
                    reason_left="NO_CHANGE",
                    reason_right="DRIVER_COMMAND",
                    input_validity="VALID",
                    warning_code="NONE",
                ),
            ),
        ],
        id="FTC-PW01-03",
    ),
    # FTC-PW01-04 (SWR-001, SWR-002) PICT-01#4: source=avn, action=lock,
    # side=left 조합 처리. source별 분기 누락·side/action 조합 결함
    # 검출(수용기준이 24개 조합 전수를 요구하므로 3-way=전수)
    pytest.param(
        [
            Step(
                10.00,
                expect=dict(
                    lock_left="RELEASE",
                    lock_right="RELEASE",
                    reason_code="NO_CHANGE",
                    priority_reason="no_change",
                ),
            ),
            Step(
                10.05,
                cmds=[cmd("left", "lock", "avn")],
                expect=dict(
                    lock_left="LOCK",
                    lock_right="RELEASE",
                    state="NORMAL",
                    reason_code="DRIVER_COMMAND",
                    priority_reason="driver_command",
                    reason_left="DRIVER_COMMAND",
                    reason_right="NO_CHANGE",
                    input_validity="VALID",
                    warning_code="NONE",
                ),
            ),
        ],
        id="FTC-PW01-04",
    ),
    # FTC-PW01-05 (SWR-001, SWR-002) PICT-01#5: source=mobile_app, action=lock,
    # side=all 조합 처리. source별 분기 누락·side/action 조합 결함
    # 검출(수용기준이 24개 조합 전수를 요구하므로 3-way=전수)
    pytest.param(
        [
            Step(
                10.00,
                expect=dict(
                    lock_left="RELEASE",
                    lock_right="RELEASE",
                    reason_code="NO_CHANGE",
                    priority_reason="no_change",
                ),
            ),
            Step(
                10.05,
                cmds=[cmd("all", "lock", "mobile_app")],
                expect=dict(
                    lock_left="LOCK",
                    lock_right="LOCK",
                    state="NORMAL",
                    reason_code="DRIVER_COMMAND",
                    priority_reason="driver_command",
                    reason_left="DRIVER_COMMAND",
                    reason_right="DRIVER_COMMAND",
                    input_validity="VALID",
                    warning_code="NONE",
                ),
            ),
        ],
        id="FTC-PW01-05",
    ),
    # FTC-PW01-06 (SWR-001, SWR-002) PICT-01#6: source=voice, action=unlock,
    # side=all 조합 처리. source별 분기 누락·side/action 조합 결함
    # 검출(수용기준이 24개 조합 전수를 요구하므로 3-way=전수)
    pytest.param(
        [
            Step(
                10.00,
                cmds=[cmd("all", "lock")],
                expect=dict(
                    lock_left="LOCK",
                    lock_right="LOCK",
                    reason_code="DRIVER_COMMAND",
                    priority_reason="driver_command",
                ),
            ),
            Step(
                10.05,
                cmds=[cmd("all", "unlock", "voice")],
                expect=dict(
                    lock_left="RELEASE",
                    lock_right="RELEASE",
                    state="NORMAL",
                    reason_code="DRIVER_COMMAND",
                    priority_reason="driver_command",
                    reason_left="DRIVER_COMMAND",
                    reason_right="DRIVER_COMMAND",
                    input_validity="VALID",
                    warning_code="NONE",
                ),
            ),
        ],
        id="FTC-PW01-06",
    ),
    # FTC-PW01-07 (SWR-001, SWR-002) PICT-01#7: source=avn, action=lock,
    # side=all 조합 처리. source별 분기 누락·side/action 조합 결함
    # 검출(수용기준이 24개 조합 전수를 요구하므로 3-way=전수)
    pytest.param(
        [
            Step(
                10.00,
                expect=dict(
                    lock_left="RELEASE",
                    lock_right="RELEASE",
                    reason_code="NO_CHANGE",
                    priority_reason="no_change",
                ),
            ),
            Step(
                10.05,
                cmds=[cmd("all", "lock", "avn")],
                expect=dict(
                    lock_left="LOCK",
                    lock_right="LOCK",
                    state="NORMAL",
                    reason_code="DRIVER_COMMAND",
                    priority_reason="driver_command",
                    reason_left="DRIVER_COMMAND",
                    reason_right="DRIVER_COMMAND",
                    input_validity="VALID",
                    warning_code="NONE",
                ),
            ),
        ],
        id="FTC-PW01-07",
    ),
    # FTC-PW01-08 (SWR-001, SWR-002) PICT-01#8: source=mobile_app, action=lock,
    # side=left 조합 처리. source별 분기 누락·side/action 조합 결함
    # 검출(수용기준이 24개 조합 전수를 요구하므로 3-way=전수)
    pytest.param(
        [
            Step(
                10.00,
                expect=dict(
                    lock_left="RELEASE",
                    lock_right="RELEASE",
                    reason_code="NO_CHANGE",
                    priority_reason="no_change",
                ),
            ),
            Step(
                10.05,
                cmds=[cmd("left", "lock", "mobile_app")],
                expect=dict(
                    lock_left="LOCK",
                    lock_right="RELEASE",
                    state="NORMAL",
                    reason_code="DRIVER_COMMAND",
                    priority_reason="driver_command",
                    reason_left="DRIVER_COMMAND",
                    reason_right="NO_CHANGE",
                    input_validity="VALID",
                    warning_code="NONE",
                ),
            ),
        ],
        id="FTC-PW01-08",
    ),
    # FTC-PW01-09 (SWR-001, SWR-002) PICT-01#9: source=physical_button,
    # action=unlock, side=left 조합 처리. source별 분기 누락·side/action 조합
    # 결함 검출(수용기준이 24개 조합 전수를 요구하므로 3-way=전수)
    pytest.param(
        [
            Step(
                10.00,
                cmds=[cmd("all", "lock")],
                expect=dict(
                    lock_left="LOCK",
                    lock_right="LOCK",
                    reason_code="DRIVER_COMMAND",
                    priority_reason="driver_command",
                ),
            ),
            Step(
                10.05,
                cmds=[cmd("left", "unlock")],
                expect=dict(
                    lock_left="RELEASE",
                    lock_right="LOCK",
                    state="NORMAL",
                    reason_code="DRIVER_COMMAND",
                    priority_reason="driver_command",
                    reason_left="DRIVER_COMMAND",
                    reason_right="NO_CHANGE",
                    input_validity="VALID",
                    warning_code="NONE",
                ),
            ),
        ],
        id="FTC-PW01-09",
    ),
    # FTC-PW01-10 (SWR-001, SWR-002) PICT-01#10: source=physical_button,
    # action=unlock, side=all 조합 처리. source별 분기 누락·side/action 조합
    # 결함 검출(수용기준이 24개 조합 전수를 요구하므로 3-way=전수)
    pytest.param(
        [
            Step(
                10.00,
                cmds=[cmd("all", "lock")],
                expect=dict(
                    lock_left="LOCK",
                    lock_right="LOCK",
                    reason_code="DRIVER_COMMAND",
                    priority_reason="driver_command",
                ),
            ),
            Step(
                10.05,
                cmds=[cmd("all", "unlock")],
                expect=dict(
                    lock_left="RELEASE",
                    lock_right="RELEASE",
                    state="NORMAL",
                    reason_code="DRIVER_COMMAND",
                    priority_reason="driver_command",
                    reason_left="DRIVER_COMMAND",
                    reason_right="DRIVER_COMMAND",
                    input_validity="VALID",
                    warning_code="NONE",
                ),
            ),
        ],
        id="FTC-PW01-10",
    ),
    # FTC-PW01-11 (SWR-001, SWR-002) PICT-01#11: source=voice, action=lock,
    # side=left 조합 처리. source별 분기 누락·side/action 조합 결함
    # 검출(수용기준이 24개 조합 전수를 요구하므로 3-way=전수)
    pytest.param(
        [
            Step(
                10.00,
                expect=dict(
                    lock_left="RELEASE",
                    lock_right="RELEASE",
                    reason_code="NO_CHANGE",
                    priority_reason="no_change",
                ),
            ),
            Step(
                10.05,
                cmds=[cmd("left", "lock", "voice")],
                expect=dict(
                    lock_left="LOCK",
                    lock_right="RELEASE",
                    state="NORMAL",
                    reason_code="DRIVER_COMMAND",
                    priority_reason="driver_command",
                    reason_left="DRIVER_COMMAND",
                    reason_right="NO_CHANGE",
                    input_validity="VALID",
                    warning_code="NONE",
                ),
            ),
        ],
        id="FTC-PW01-11",
    ),
    # FTC-PW01-12 (SWR-001, SWR-002) PICT-01#12: source=physical_button,
    # action=unlock, side=right 조합 처리. source별 분기 누락·side/action 조합
    # 결함 검출(수용기준이 24개 조합 전수를 요구하므로 3-way=전수)
    pytest.param(
        [
            Step(
                10.00,
                cmds=[cmd("all", "lock")],
                expect=dict(
                    lock_left="LOCK",
                    lock_right="LOCK",
                    reason_code="DRIVER_COMMAND",
                    priority_reason="driver_command",
                ),
            ),
            Step(
                10.05,
                cmds=[cmd("right", "unlock")],
                expect=dict(
                    lock_left="LOCK",
                    lock_right="RELEASE",
                    state="NORMAL",
                    reason_code="DRIVER_COMMAND",
                    priority_reason="driver_command",
                    reason_left="NO_CHANGE",
                    reason_right="DRIVER_COMMAND",
                    input_validity="VALID",
                    warning_code="NONE",
                ),
            ),
        ],
        id="FTC-PW01-12",
    ),
    # FTC-PW01-13 (SWR-001, SWR-002) PICT-01#13: source=voice, action=unlock,
    # side=left 조합 처리. source별 분기 누락·side/action 조합 결함
    # 검출(수용기준이 24개 조합 전수를 요구하므로 3-way=전수)
    pytest.param(
        [
            Step(
                10.00,
                cmds=[cmd("all", "lock")],
                expect=dict(
                    lock_left="LOCK",
                    lock_right="LOCK",
                    reason_code="DRIVER_COMMAND",
                    priority_reason="driver_command",
                ),
            ),
            Step(
                10.05,
                cmds=[cmd("left", "unlock", "voice")],
                expect=dict(
                    lock_left="RELEASE",
                    lock_right="LOCK",
                    state="NORMAL",
                    reason_code="DRIVER_COMMAND",
                    priority_reason="driver_command",
                    reason_left="DRIVER_COMMAND",
                    reason_right="NO_CHANGE",
                    input_validity="VALID",
                    warning_code="NONE",
                ),
            ),
        ],
        id="FTC-PW01-13",
    ),
    # FTC-PW01-14 (SWR-001, SWR-002) PICT-01#14: source=avn, action=unlock,
    # side=right 조합 처리. source별 분기 누락·side/action 조합 결함
    # 검출(수용기준이 24개 조합 전수를 요구하므로 3-way=전수)
    pytest.param(
        [
            Step(
                10.00,
                cmds=[cmd("all", "lock")],
                expect=dict(
                    lock_left="LOCK",
                    lock_right="LOCK",
                    reason_code="DRIVER_COMMAND",
                    priority_reason="driver_command",
                ),
            ),
            Step(
                10.05,
                cmds=[cmd("right", "unlock", "avn")],
                expect=dict(
                    lock_left="LOCK",
                    lock_right="RELEASE",
                    state="NORMAL",
                    reason_code="DRIVER_COMMAND",
                    priority_reason="driver_command",
                    reason_left="NO_CHANGE",
                    reason_right="DRIVER_COMMAND",
                    input_validity="VALID",
                    warning_code="NONE",
                ),
            ),
        ],
        id="FTC-PW01-14",
    ),
    # FTC-PW01-15 (SWR-001, SWR-002) PICT-01#15: source=voice, action=lock,
    # side=all 조합 처리. source별 분기 누락·side/action 조합 결함
    # 검출(수용기준이 24개 조합 전수를 요구하므로 3-way=전수)
    pytest.param(
        [
            Step(
                10.00,
                expect=dict(
                    lock_left="RELEASE",
                    lock_right="RELEASE",
                    reason_code="NO_CHANGE",
                    priority_reason="no_change",
                ),
            ),
            Step(
                10.05,
                cmds=[cmd("all", "lock", "voice")],
                expect=dict(
                    lock_left="LOCK",
                    lock_right="LOCK",
                    state="NORMAL",
                    reason_code="DRIVER_COMMAND",
                    priority_reason="driver_command",
                    reason_left="DRIVER_COMMAND",
                    reason_right="DRIVER_COMMAND",
                    input_validity="VALID",
                    warning_code="NONE",
                ),
            ),
        ],
        id="FTC-PW01-15",
    ),
    # FTC-PW01-16 (SWR-001, SWR-002) PICT-01#16: source=physical_button,
    # action=lock, side=left 조합 처리. source별 분기 누락·side/action 조합
    # 결함 검출(수용기준이 24개 조합 전수를 요구하므로 3-way=전수)
    pytest.param(
        [
            Step(
                10.00,
                expect=dict(
                    lock_left="RELEASE",
                    lock_right="RELEASE",
                    reason_code="NO_CHANGE",
                    priority_reason="no_change",
                ),
            ),
            Step(
                10.05,
                cmds=[cmd("left", "lock")],
                expect=dict(
                    lock_left="LOCK",
                    lock_right="RELEASE",
                    state="NORMAL",
                    reason_code="DRIVER_COMMAND",
                    priority_reason="driver_command",
                    reason_left="DRIVER_COMMAND",
                    reason_right="NO_CHANGE",
                    input_validity="VALID",
                    warning_code="NONE",
                ),
            ),
        ],
        id="FTC-PW01-16",
    ),
    # FTC-PW01-17 (SWR-001, SWR-002) PICT-01#17: source=mobile_app,
    # action=unlock, side=left 조합 처리. source별 분기 누락·side/action 조합
    # 결함 검출(수용기준이 24개 조합 전수를 요구하므로 3-way=전수)
    pytest.param(
        [
            Step(
                10.00,
                cmds=[cmd("all", "lock")],
                expect=dict(
                    lock_left="LOCK",
                    lock_right="LOCK",
                    reason_code="DRIVER_COMMAND",
                    priority_reason="driver_command",
                ),
            ),
            Step(
                10.05,
                cmds=[cmd("left", "unlock", "mobile_app")],
                expect=dict(
                    lock_left="RELEASE",
                    lock_right="LOCK",
                    state="NORMAL",
                    reason_code="DRIVER_COMMAND",
                    priority_reason="driver_command",
                    reason_left="DRIVER_COMMAND",
                    reason_right="NO_CHANGE",
                    input_validity="VALID",
                    warning_code="NONE",
                ),
            ),
        ],
        id="FTC-PW01-17",
    ),
    # FTC-PW01-18 (SWR-001, SWR-002) PICT-01#18: source=avn, action=unlock,
    # side=left 조합 처리. source별 분기 누락·side/action 조합 결함
    # 검출(수용기준이 24개 조합 전수를 요구하므로 3-way=전수)
    pytest.param(
        [
            Step(
                10.00,
                cmds=[cmd("all", "lock")],
                expect=dict(
                    lock_left="LOCK",
                    lock_right="LOCK",
                    reason_code="DRIVER_COMMAND",
                    priority_reason="driver_command",
                ),
            ),
            Step(
                10.05,
                cmds=[cmd("left", "unlock", "avn")],
                expect=dict(
                    lock_left="RELEASE",
                    lock_right="LOCK",
                    state="NORMAL",
                    reason_code="DRIVER_COMMAND",
                    priority_reason="driver_command",
                    reason_left="DRIVER_COMMAND",
                    reason_right="NO_CHANGE",
                    input_validity="VALID",
                    warning_code="NONE",
                ),
            ),
        ],
        id="FTC-PW01-18",
    ),
    # FTC-PW01-19 (SWR-001, SWR-002) PICT-01#19: source=physical_button,
    # action=lock, side=all 조합 처리. source별 분기 누락·side/action 조합 결함
    # 검출(수용기준이 24개 조합 전수를 요구하므로 3-way=전수)
    pytest.param(
        [
            Step(
                10.00,
                expect=dict(
                    lock_left="RELEASE",
                    lock_right="RELEASE",
                    reason_code="NO_CHANGE",
                    priority_reason="no_change",
                ),
            ),
            Step(
                10.05,
                cmds=[cmd("all", "lock")],
                expect=dict(
                    lock_left="LOCK",
                    lock_right="LOCK",
                    state="NORMAL",
                    reason_code="DRIVER_COMMAND",
                    priority_reason="driver_command",
                    reason_left="DRIVER_COMMAND",
                    reason_right="DRIVER_COMMAND",
                    input_validity="VALID",
                    warning_code="NONE",
                ),
            ),
        ],
        id="FTC-PW01-19",
    ),
    # FTC-PW01-20 (SWR-001, SWR-002) PICT-01#20: source=avn, action=lock,
    # side=right 조합 처리. source별 분기 누락·side/action 조합 결함
    # 검출(수용기준이 24개 조합 전수를 요구하므로 3-way=전수)
    pytest.param(
        [
            Step(
                10.00,
                expect=dict(
                    lock_left="RELEASE",
                    lock_right="RELEASE",
                    reason_code="NO_CHANGE",
                    priority_reason="no_change",
                ),
            ),
            Step(
                10.05,
                cmds=[cmd("right", "lock", "avn")],
                expect=dict(
                    lock_left="RELEASE",
                    lock_right="LOCK",
                    state="NORMAL",
                    reason_code="DRIVER_COMMAND",
                    priority_reason="driver_command",
                    reason_left="NO_CHANGE",
                    reason_right="DRIVER_COMMAND",
                    input_validity="VALID",
                    warning_code="NONE",
                ),
            ),
        ],
        id="FTC-PW01-20",
    ),
    # FTC-PW01-21 (SWR-001, SWR-002) PICT-01#21: source=voice, action=lock,
    # side=right 조합 처리. source별 분기 누락·side/action 조합 결함
    # 검출(수용기준이 24개 조합 전수를 요구하므로 3-way=전수)
    pytest.param(
        [
            Step(
                10.00,
                expect=dict(
                    lock_left="RELEASE",
                    lock_right="RELEASE",
                    reason_code="NO_CHANGE",
                    priority_reason="no_change",
                ),
            ),
            Step(
                10.05,
                cmds=[cmd("right", "lock", "voice")],
                expect=dict(
                    lock_left="RELEASE",
                    lock_right="LOCK",
                    state="NORMAL",
                    reason_code="DRIVER_COMMAND",
                    priority_reason="driver_command",
                    reason_left="NO_CHANGE",
                    reason_right="DRIVER_COMMAND",
                    input_validity="VALID",
                    warning_code="NONE",
                ),
            ),
        ],
        id="FTC-PW01-21",
    ),
    # FTC-PW01-22 (SWR-001, SWR-002) PICT-01#22: source=avn, action=unlock,
    # side=all 조합 처리. source별 분기 누락·side/action 조합 결함
    # 검출(수용기준이 24개 조합 전수를 요구하므로 3-way=전수)
    pytest.param(
        [
            Step(
                10.00,
                cmds=[cmd("all", "lock")],
                expect=dict(
                    lock_left="LOCK",
                    lock_right="LOCK",
                    reason_code="DRIVER_COMMAND",
                    priority_reason="driver_command",
                ),
            ),
            Step(
                10.05,
                cmds=[cmd("all", "unlock", "avn")],
                expect=dict(
                    lock_left="RELEASE",
                    lock_right="RELEASE",
                    state="NORMAL",
                    reason_code="DRIVER_COMMAND",
                    priority_reason="driver_command",
                    reason_left="DRIVER_COMMAND",
                    reason_right="DRIVER_COMMAND",
                    input_validity="VALID",
                    warning_code="NONE",
                ),
            ),
        ],
        id="FTC-PW01-22",
    ),
    # FTC-PW01-23 (SWR-001, SWR-002) PICT-01#23: source=mobile_app,
    # action=unlock, side=all 조합 처리. source별 분기 누락·side/action 조합
    # 결함 검출(수용기준이 24개 조합 전수를 요구하므로 3-way=전수)
    pytest.param(
        [
            Step(
                10.00,
                cmds=[cmd("all", "lock")],
                expect=dict(
                    lock_left="LOCK",
                    lock_right="LOCK",
                    reason_code="DRIVER_COMMAND",
                    priority_reason="driver_command",
                ),
            ),
            Step(
                10.05,
                cmds=[cmd("all", "unlock", "mobile_app")],
                expect=dict(
                    lock_left="RELEASE",
                    lock_right="RELEASE",
                    state="NORMAL",
                    reason_code="DRIVER_COMMAND",
                    priority_reason="driver_command",
                    reason_left="DRIVER_COMMAND",
                    reason_right="DRIVER_COMMAND",
                    input_validity="VALID",
                    warning_code="NONE",
                ),
            ),
        ],
        id="FTC-PW01-23",
    ),
    # FTC-PW01-24 (SWR-001, SWR-002) PICT-01#24: source=mobile_app,
    # action=lock, side=right 조합 처리. source별 분기 누락·side/action 조합
    # 결함 검출(수용기준이 24개 조합 전수를 요구하므로 3-way=전수)
    pytest.param(
        [
            Step(
                10.00,
                expect=dict(
                    lock_left="RELEASE",
                    lock_right="RELEASE",
                    reason_code="NO_CHANGE",
                    priority_reason="no_change",
                ),
            ),
            Step(
                10.05,
                cmds=[cmd("right", "lock", "mobile_app")],
                expect=dict(
                    lock_left="RELEASE",
                    lock_right="LOCK",
                    state="NORMAL",
                    reason_code="DRIVER_COMMAND",
                    priority_reason="driver_command",
                    reason_left="NO_CHANGE",
                    reason_right="DRIVER_COMMAND",
                    input_validity="VALID",
                    warning_code="NONE",
                ),
            ),
        ],
        id="FTC-PW01-24",
    ),
]


@pytest.mark.parametrize("steps", PW01_CASES)
def test_ftc_pw01_command_combinations(bench, steps):
    """FTC-PW01-01~FTC-PW01-24 (SWR-001, SWR-002)

    PICT-01 3-way(=전수) 행: 4 source × lock/unlock × left/right/all
    24개 운전자 명령 조합. 케이스별 tc_id는 각 pytest.param의 id다.
    """
    play(bench, steps)
