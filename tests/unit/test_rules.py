"""@brief qm.rules 단위 테스트 (SWR-001~004, 017, 018, 020)."""

from tests.helpers import snapshot

from child_lock.qm.rules import proposals
from child_lock.safety.validation import check_snapshot
from child_lock.types import (
    Action,
    DriverCommand,
    LockOutput,
    ReasonCode,
    Side,
    SideProposal,
    Source,
)

L, R = LockOutput.LOCK, LockOutput.RELEASE
IGN = SideProposal(6, R, ReasonCode.IGNITION_OFF)
FIRE = SideProposal(7, R, ReasonCode.FIRE)
AUTO = SideProposal(9, L, ReasonCode.AUTO_LOCK)


def _values(**signals):
    """@brief 정상 신호 값."""
    return check_snapshot(snapshot(**signals), 10.0, None).values


def _cmd(side=Side.LEFT, action=Action.UNLOCK, source=Source.AVN):
    """@brief 검사를 마친 명령 하나."""
    return DriverCommand(side, action, source)


def test_no_values_proposes_nothing():
    assert proposals(None, (_cmd(),)) == ((), ())


def test_quiet_inputs_propose_nothing():
    assert proposals(_values(), ()) == ((), ())


def test_ignition_off_proposes_release_on_both_sides():
    left, right = proposals(_values(ignition_on=False), ())
    assert IGN in left
    assert IGN in right


def test_forced_release_uses_first_true_in_fire_overtemp_adult_order():
    left, _ = proposals(_values(fire_detected=True, adult_present=True), ())
    assert left == (FIRE,)
    left, _ = proposals(
        _values(overtemperature_detected=True, adult_present=True), ()
    )
    assert left == (SideProposal(7, R, ReasonCode.OVERTEMPERATURE),)
    left, _ = proposals(_values(adult_present=True), ())
    assert left == (SideProposal(7, R, ReasonCode.ADULT_PRESENT),)


def test_isofix_locks_only_its_side():
    left, right = proposals(_values(isofix_right=True), ())
    assert left == ()
    assert right == (SideProposal(8, L, ReasonCode.ISOFIX),)


def test_auto_lock_from_three_kph():
    assert proposals(_values(vehicle_speed_kph=3.0), ()) == ((AUTO,), (AUTO,))
    assert proposals(_values(vehicle_speed_kph=2.9), ()) == ((), ())


def test_driver_command_applies_to_selected_side_only():
    left, right = proposals(_values(), (_cmd(Side.RIGHT, Action.LOCK),))
    assert left == ()
    assert right == (SideProposal(10, L, ReasonCode.DRIVER_COMMAND),)


def test_last_command_per_side_wins():
    cmds = (_cmd(action=Action.LOCK), _cmd(action=Action.UNLOCK))
    left, _ = proposals(_values(), cmds)
    assert left == (SideProposal(10, R, ReasonCode.DRIVER_COMMAND),)


def test_unlock_allowed_only_below_three_kph():
    left, _ = proposals(_values(vehicle_speed_kph=2.9), (_cmd(),))
    assert SideProposal(10, R, ReasonCode.DRIVER_COMMAND) in left
    left, _ = proposals(_values(vehicle_speed_kph=3.0), (_cmd(),))
    assert left == (AUTO,)


def test_lock_command_allowed_at_any_speed():
    cmd = (_cmd(action=Action.LOCK),)
    left, _ = proposals(_values(vehicle_speed_kph=250.0), cmd)
    assert SideProposal(10, L, ReasonCode.DRIVER_COMMAND) in left


def test_unknown_speed_does_not_allow_unlock_or_auto_lock():
    values = check_snapshot(snapshot(vehicle_speed_kph="x"), 10.0, None).values
    assert proposals(values, (_cmd(),)) == ((), ())


def test_several_rules_produce_several_proposals():
    left, right = proposals(
        _values(ignition_on=False, fire_detected=True, isofix_left=True),
        (),
    )
    assert left == (IGN, FIRE, SideProposal(8, L, ReasonCode.ISOFIX))
    assert right == (IGN, FIRE)
