"""@brief SWE1-SRS 부록 A 결정표 D-01~D-45, P-01~P-10 (SWR-019 수용기준).

규칙 조건을 실제 신호·명령으로 만들어 controller로 평가하고, 결정표의
해당 쪽(좌측) 출력, reason_code, state를 확인한다.
"""

from itertools import combinations

import pytest
from tests.helpers import command, snapshot

from child_lock.controller import Controller
from child_lock.types import LockOutput, RawInput, ReasonCode, State

L, R, HOLD = LockOutput.LOCK, LockOutput.RELEASE, "HOLD"
RC = ReasonCode

## (순위, 신호 덮어쓰기, 좌측 명령, 기대 출력, 기대 이유, state 플래그)
## 순위 2는 우측 접근위험 신호를 형식 오류로 만들어
## 좌측 조건과 섞이지 않게 한다.
RULES = (
    (1, {"crash_status": "CONFIRMED"}, None, R, RC.CRASH_CONFIRMED, None),
    (2, {"rear_right_approach_risk": 1}, None, HOLD, RC.INPUT_INVALID, "D"),
    (3, {"sensor_fault": True}, None, HOLD, RC.SENSOR_FAULT, "F"),
    (4, {"rear_left_approach_risk": True}, None, L, RC.APPROACH_RISK, None),
    (5, {"gear": "X"}, None, HOLD, RC.INPUT_INVALID, "D"),
    (6, {"ignition_on": False}, None, R, RC.IGNITION_OFF, "O"),
    (7, {"fire_detected": True}, None, R, RC.FIRE, None),
    (8, {"isofix_left": True}, None, L, RC.ISOFIX, None),
    (9, {"vehicle_speed_kph": 3.0}, None, L, RC.AUTO_LOCK, None),
    (10, {}, "unlock", R, RC.DRIVER_COMMAND, None),
)


def _state(flags):
    """@brief 1.3절 성립 조건 순서로 state를 정한다."""
    for flag, state in (
        ("D", State.DEGRADED),
        ("F", State.FAULT),
        ("O", State.OFF),
    ):
        if flag in flags:
            return state
    return State.NORMAL


def _evaluate(signals, left_action, previous):
    """@brief 직전 출력을 만든 뒤 조건 스냅샷을 평가한다."""
    ctl = Controller()
    if previous is L:
        # 직전 출력을 LOCK으로: 자동 잠금 후 정차
        ctl.evaluate(10.0, RawInput(snapshot(vehicle_speed_kph=3.0), ()))
    else:
        ctl.evaluate(10.0, RawInput(snapshot(), ()))
    cmds = (command("left", left_action),) if left_action else ()
    raw = RawInput(snapshot(source_timestamp_s=10.05, **signals), cmds)
    return ctl.evaluate(10.05, raw)


def _cases():
    """@brief 순위 1~10의 모든 쌍 (D-01~D-45)."""
    for n, (high, low) in enumerate(combinations(RULES, 2), start=1):
        yield pytest.param(high, low, id=f"D-{n:02d}")


@pytest.mark.parametrize(("high", "low"), list(_cases()))
def test_decision_table_pair(high, low):
    signals = {**low[1], **high[1]}
    action = high[2] or low[2]
    expected_out = high[3]
    previous = L if expected_out in (HOLD, R) else R
    d = _evaluate(signals, action, previous)
    assert d.lock_left is (previous if expected_out == HOLD else expected_out)
    assert d.reason_code is high[4]
    assert d.state is _state({r[5] for r in (high, low) if r[5]})


## (ID, 함께 해당하는 규칙의 신호, 명령, 기대 출력, 기대 이유, 기대 state)
PENDING_CASES = (
    (
        "P-02",
        {"rear_right_approach_risk": 1},
        None,
        R,
        RC.INPUT_INVALID,
        State.DEGRADED,
    ),
    ("P-03", {"sensor_fault": True}, None, R, RC.SENSOR_FAULT, State.FAULT),
    (
        "P-04",
        {"rear_left_approach_risk": True},
        None,
        L,
        RC.APPROACH_RISK,
        State.NORMAL,
    ),
    ("P-05", {"gear": "X"}, None, R, RC.INPUT_INVALID, State.DEGRADED),
    ("P-06", {"ignition_on": False}, None, R, RC.IGNITION_OFF, State.OFF),
    ("P-07", {"fire_detected": True}, None, R, RC.FIRE, State.NORMAL),
    ("P-08", {"isofix_left": True}, None, R, RC.CRASH_PENDING, State.NORMAL),
    (
        "P-09",
        {"vehicle_speed_kph": 3.0},
        None,
        R,
        RC.CRASH_PENDING,
        State.NORMAL,
    ),
    ("P-10", {}, "lock", R, RC.CRASH_PENDING, State.NORMAL),
)


@pytest.mark.parametrize(
    ("signals", "action", "out", "reason", "state"),
    [pytest.param(*case[1:], id=case[0]) for case in PENDING_CASES],
)
def test_pending_filter_table(signals, action, out, reason, state):
    d = _evaluate({"crash_status": "PENDING", **signals}, action, R)
    assert d.lock_left is out
    assert d.reason_code is reason
    assert d.state is state


def test_pending_with_existing_latch_p01():
    ctl = Controller()
    ctl.evaluate(10.0, RawInput(snapshot(crash_status="CONFIRMED"), ()))
    raw = RawInput(
        snapshot(source_timestamp_s=10.05, crash_status="PENDING"), ()
    )
    d = ctl.evaluate(10.05, raw)
    assert d.lock_left is R
    assert d.reason_code is RC.CRASH_CONFIRMED
    assert d.state is State.NORMAL


def test_pending_does_not_block_unlock():
    d = _evaluate({"crash_status": "PENDING"}, "unlock", L)
    assert d.lock_left is R
