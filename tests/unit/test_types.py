"""@brief child_lock.types 단위 테스트."""

import dataclasses
import math

import pytest

from child_lock import types as t


def test_freeze_raw_converts_dict_to_sorted_frozen_map():
    frozen = t.freeze_raw({"b": 1, "a": [True, None, "x"]})
    assert isinstance(frozen, t.FrozenMap)
    assert frozen.items == (("a", (True, None, "x")), ("b", 1))


def test_frozen_map_get_returns_missing_for_absent_key():
    frozen = t.freeze_raw({"a": 1})
    assert frozen.get("a") == 1
    assert frozen.get("zz") is t.Missing.MISSING


def test_freeze_raw_copies_so_later_changes_do_not_leak():
    raw = {"speed": 1.0, "nested": {"k": [1]}}
    frozen = t.freeze_raw(raw)
    raw["speed"] = 99.0
    raw["nested"]["k"].append(2)
    assert frozen.get("speed") == 1.0
    assert frozen.get("nested").get("k") == (1,)


def test_freeze_raw_marks_non_json_values_unsupported():
    assert t.freeze_raw(object()) == t.Unsupported("object")
    assert t.freeze_raw({1: "x"}) == t.Unsupported("dict")


def test_freeze_raw_limits_nesting_depth():
    value: object = 1
    for _ in range(40):
        value = [value]
    frozen = t.freeze_raw(value)
    for _ in range(32):
        frozen = frozen[0]
    assert frozen == t.Unsupported("depth")


def test_freeze_raw_keeps_float_specials_for_validation_to_reject():
    assert math.isnan(t.freeze_raw(float("nan")))


@pytest.mark.parametrize(
    ("code", "name"),
    [
        (t.ReasonCode.FIRE, "fire_detected"),
        (t.ReasonCode.OVERTEMPERATURE, "overtemperature_detected"),
        (t.ReasonCode.ADULT_PRESENT, "adult_present"),
        (t.ReasonCode.CRASH_CONFIRMED, "crash_confirmed"),
        (t.ReasonCode.NO_CHANGE, "no_change"),
    ],
)
def test_priority_reason_of_maps_codes_to_snake_case_names(code, name):
    assert t.priority_reason_of(code) == name


def test_enum_values_match_interface_strings():
    assert t.LockOutput.LOCK.value == "LOCK"
    assert t.Side.LEFT.value == "left"
    assert t.Action.UNLOCK.value == "unlock"
    assert t.Source.MOBILE_APP.value == "mobile_app"


def test_initial_decision_is_release_and_stale():
    d = t.initial_decision()
    assert (d.lock_left, d.lock_right) == (
        t.LockOutput.RELEASE,
        t.LockOutput.RELEASE,
    )
    assert d.state is t.State.DEGRADED
    assert d.input_validity is t.InputValidity.STALE
    assert d.reason_code is t.ReasonCode.INPUT_STALE


def test_decision_as_dict_has_nine_interface_fields():
    keys = set(t.initial_decision().as_dict())
    assert keys == {
        "lock_left",
        "lock_right",
        "state",
        "priority_reason",
        "reason_code",
        "input_validity",
        "reason_left",
        "reason_right",
        "warning_code",
    }


def test_event_record_as_dict_has_eleven_fields():
    rec = t.EventRecord(
        event_id=3, timestamp_s=1.5, decision=t.initial_decision()
    )
    d = rec.as_dict()
    assert d["event_id"] == 3
    assert d["timestamp_s"] == 1.5
    assert d["lock_left"] == "RELEASE"
    assert len(d) == 11


def test_transfer_types_are_frozen():
    with pytest.raises(dataclasses.FrozenInstanceError):
        t.initial_decision().state = t.State.NORMAL
