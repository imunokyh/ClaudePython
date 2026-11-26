"""@brief safety.validation 단위 테스트 (SWR-002, SWR-013, SWR-007)."""

import pytest
from tests.helpers import DROP, command, snapshot

from child_lock.safety.validation import check_commands, check_snapshot
from child_lock.types import (
    Action,
    CrashStatus,
    DriverCommand,
    FrozenMap,
    Gear,
    Side,
    Source,
    freeze_raw,
)

NOW = 10.0

## ASIL B 신호와 QM 신호 (SWE1-SRS 1.2절)
ASIL_B = {
    "source_timestamp_s",
    "vehicle_speed_kph",
    "crash_status",
    "rear_left_approach_risk",
    "rear_right_approach_risk",
    "ignition_on",
    "sensor_fault",
}
QM = {
    "gear",
    "fire_detected",
    "overtemperature_detected",
    "adult_present",
    "isofix_left",
    "isofix_right",
}


def test_valid_snapshot_has_no_errors_and_typed_values():
    check = check_snapshot(snapshot(), NOW, None)
    assert check.received
    assert check.asil_b_errors == frozenset()
    assert check.qm_errors == frozenset()
    assert check.values.gear is Gear.P
    assert check.values.crash_status is CrashStatus.NONE
    assert check.values.ignition_on is True
    assert check.crash_status is CrashStatus.NONE
    assert check.crash_timestamp_s == 10.0


def test_no_snapshot_is_not_received():
    check = check_snapshot(None, NOW, None)
    assert not check.received
    assert check.values is None
    assert check.asil_b_errors == frozenset()
    assert check.crash_status is None


def test_non_object_snapshot_marks_every_signal_in_error():
    check = check_snapshot(freeze_raw([1, 2]), NOW, None)
    assert check.received
    assert check.values is None
    assert check.asil_b_errors == ASIL_B
    assert check.qm_errors == QM
    assert check.crash_status is None


@pytest.mark.parametrize("speed", [0.0, 300.0, 3, 150.5])
def test_speed_inside_range_is_valid(speed):
    check = check_snapshot(snapshot(vehicle_speed_kph=speed), NOW, None)
    assert check.asil_b_errors == frozenset()
    assert check.values.vehicle_speed_kph == float(speed)


@pytest.mark.parametrize(
    "speed",
    [300.1, -0.1, True, "3", None, float("nan"), float("inf"), 10**400],
)
def test_speed_out_of_range_or_wrong_type_is_asil_b_error(speed):
    check = check_snapshot(snapshot(vehicle_speed_kph=speed), NOW, None)
    assert check.asil_b_errors == {"vehicle_speed_kph"}
    assert check.values.vehicle_speed_kph is None


@pytest.mark.parametrize("value", ["UNKNOWN", "none", 1, None])
def test_unknown_crash_status_is_asil_b_error(value):
    check = check_snapshot(snapshot(crash_status=value), NOW, None)
    assert check.asil_b_errors == {"crash_status"}
    assert check.crash_status is None


@pytest.mark.parametrize("value", [1, 0, "true", None])
def test_boolean_slot_accepts_only_bool(value):
    check = check_snapshot(snapshot(ignition_on=value), NOW, None)
    assert check.asil_b_errors == {"ignition_on"}
    assert check.values.ignition_on is None


def test_qm_signal_error_goes_to_qm_errors_only():
    check = check_snapshot(snapshot(isofix_left=1, gear="X"), NOW, None)
    assert check.asil_b_errors == frozenset()
    assert check.qm_errors == {"isofix_left", "gear"}
    assert check.values.isofix_left is None
    assert check.values.gear is None


def test_missing_signal_is_an_error():
    check = check_snapshot(snapshot(sensor_fault=DROP), NOW, None)
    assert check.asil_b_errors == {"sensor_fault"}


def test_unsupported_value_is_an_error():
    check = check_snapshot(freeze_raw({"adult_present": object()}), NOW, None)
    assert "adult_present" in check.qm_errors


@pytest.mark.parametrize(
    ("ts", "ref_ts"),
    [(10.05, None), (10.0, 10.0), (0.0, None), (9.0, 8.5)],
)
def test_timestamp_within_rules_is_valid(ts, ref_ts):
    check = check_snapshot(snapshot(source_timestamp_s=ts), NOW, ref_ts)
    assert check.asil_b_errors == frozenset()
    assert check.values.source_timestamp_s == ts


@pytest.mark.parametrize(
    ("ts", "ref_ts"),
    [(10.051, None), (-0.1, None), (9.9, 9.95), ("10", None), (True, None)],
)
def test_future_negative_or_regressing_timestamp_is_error(ts, ref_ts):
    check = check_snapshot(snapshot(source_timestamp_s=ts), NOW, ref_ts)
    assert check.asil_b_errors == {"source_timestamp_s"}
    assert check.values is None


def test_crash_timestamp_ignores_regression_for_late_confirmed():
    late = snapshot(source_timestamp_s=9.5, crash_status="CONFIRMED")
    check = check_snapshot(late, NOW, 9.8)
    assert "source_timestamp_s" in check.asil_b_errors
    assert check.crash_status is CrashStatus.CONFIRMED
    assert check.crash_timestamp_s == 9.5


def test_crash_timestamp_rejects_future_values():
    check = check_snapshot(snapshot(source_timestamp_s=10.2), NOW, None)
    assert check.crash_timestamp_s is None


def test_valid_commands_are_kept_in_order():
    raw = (command("left", "lock"), command("right", "unlock", "voice"))
    commands, dropped = check_commands(raw)
    assert dropped == 0
    assert commands == (
        DriverCommand(Side.LEFT, Action.LOCK, Source.PHYSICAL_BUTTON),
        DriverCommand(Side.RIGHT, Action.UNLOCK, Source.VOICE),
    )


def test_all_command_is_split_into_left_and_right():
    commands, _ = check_commands((command("all", "unlock", "mobile_app"),))
    assert commands == (
        DriverCommand(Side.LEFT, Action.UNLOCK, Source.MOBILE_APP),
        DriverCommand(Side.RIGHT, Action.UNLOCK, Source.MOBILE_APP),
    )


@pytest.mark.parametrize(
    "raw",
    [
        command(side="middle"),
        command(action="open"),
        command(source="fax"),
        freeze_raw({"side": "left", "action": "lock"}),
        freeze_raw("lock"),
        freeze_raw({"side": 1, "action": "lock", "source": "avn"}),
    ],
)
def test_invalid_command_is_dropped_and_counted(raw):
    commands, dropped = check_commands((raw, command()))
    assert dropped == 1
    assert len(commands) == 1


def test_frozen_map_type_is_used_for_commands():
    assert isinstance(command(), FrozenMap)
