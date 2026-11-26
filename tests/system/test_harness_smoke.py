"""@brief 시험 하니스 자체 확인 (시험 케이스 아님)."""

from tests.system.harness import cmd


def test_bench_drives_full_stack(bench):
    st = bench.step(10.0, vehicle_speed_kph=3.0)
    assert st["reason_code"] == "AUTO_LOCK"
    st = bench.step(10.05, commands=[cmd("all", "unlock")], send_snapshot=False)
    assert st["lock_left"] == "LOCK"
    assert bench.server_clock() == {"now_s": 10.05}
    assert len(bench.events()) == 2


def test_bench_raw_body_and_status_codes(bench):
    assert bench.send(raw_body=b"{bad") == 422
    assert bench.send_body({"snapshot": None}) == 202
    assert bench.status_code("/status") == 200
