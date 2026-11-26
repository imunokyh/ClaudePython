"""@brief 테스트 공용 도우미: 원시 입력 생성."""

from child_lock.types import freeze_raw

## 정상 스냅샷의 기본값 (정차, 시동 ON, 모든 위험·강제 신호 없음)
_BASE = (
    ("source_timestamp_s", 10.0),
    ("vehicle_speed_kph", 0.0),
    ("gear", "P"),
    ("crash_status", "NONE"),
    ("rear_left_approach_risk", False),
    ("rear_right_approach_risk", False),
    ("fire_detected", False),
    ("overtemperature_detected", False),
    ("adult_present", False),
    ("isofix_left", False),
    ("isofix_right", False),
    ("ignition_on", True),
    ("sensor_fault", False),
)


def raw_snapshot(**overrides):
    """@brief 기본값에 덮어쓴 원시 스냅샷 딕셔너리를 만든다.

    값으로 `DROP`을 주면 그 키를 뺀다.
    """
    data = dict(_BASE)
    for key, value in overrides.items():
        if value is DROP:
            data.pop(key, None)
        else:
            data[key] = value
    return data


def snapshot(**overrides):
    """@brief 불변화한 원시 스냅샷을 만든다."""
    return freeze_raw(raw_snapshot(**overrides))


def command(side="left", action="unlock", source="physical_button"):
    """@brief 불변화한 운전자 명령을 만든다."""
    return freeze_raw({"side": side, "action": action, "source": source})


class _Drop:
    """@brief raw_snapshot에서 키를 빼라는 표시."""


DROP = _Drop()
