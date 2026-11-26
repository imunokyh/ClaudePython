"""@brief qm.replay 단위 테스트 (SWR-016)."""

import hashlib
from dataclasses import replace

from child_lock.qm.replay import decision_hash
from child_lock.types import LockOutput, initial_decision

D0 = initial_decision()


def test_empty_sequence_hashes_empty_json_list():
    assert decision_hash([]) == hashlib.sha256(b"[]").hexdigest()


def test_same_sequence_gives_same_hash():
    assert decision_hash([D0, D0]) == decision_hash([D0, D0])


def test_changed_field_changes_hash():
    other = replace(D0, lock_right=LockOutput.LOCK)
    assert decision_hash([D0]) != decision_hash([other])


def test_order_matters():
    other = replace(D0, lock_right=LockOutput.LOCK)
    assert decision_hash([D0, other]) != decision_hash([other, D0])


def test_hash_is_over_sorted_key_json():
    expected = hashlib.sha256(
        b'[{"input_validity":"STALE","lock_left":"RELEASE",'
        b'"lock_right":"RELEASE","priority_reason":"input_stale",'
        b'"reason_code":"INPUT_STALE","reason_left":"INPUT_STALE",'
        b'"reason_right":"INPUT_STALE","state":"DEGRADED",'
        b'"warning_code":"NONE"}]'
    ).hexdigest()
    assert decision_hash([D0]) == expected
