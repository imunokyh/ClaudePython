# -*- coding: utf-8 -*-
"""수작업 설계 기능 케이스."""
from tcgen_lib import *

PB = "physical_button"
EP, BVA, WOW, ST, REQ, FI, EG = "동치 클래스", "경계값 분석", "WoW 검증", "상태 전이", "요구사항 기반 테스트", "결함 주입", "오류 추측"
F = "기능"
ALLX = lambda **k: k


def build():
    # ---------------- SWR-002 명령 순서 ----------------
    s = Seq()
    s.ev(10.00, None, [("left", "lock", PB), ("left", "unlock", PB)],
         exp=Xp(ll="RELEASE", lr="RELEASE", st="NORMAL", rc="DRIVER_COMMAND", rl="DRIVER_COMMAND", rr="NO_CHANGE"),
         note="같은 쪽 명령 2개: lock 다음 unlock")
    tc("FTC-101", F, ["SWR-002"], "같은 평가에서 같은 쪽 명령이 lock→unlock 순이면 마지막 명령(unlock)이 남는지 확인. '첫 명령 우선' 또는 'lock 우선' 결함 검출",
       s, [EP, WOW], pre="직전 출력은 좌·우 모두 RELEASE(초기 상태). 차속 0.0 km/h.")

    s = Seq()
    s.ev(10.00, None, [("left", "unlock", PB), ("left", "lock", PB)],
         exp=Xp(ll="LOCK", lr="RELEASE", st="NORMAL", rc="DRIVER_COMMAND", rl="DRIVER_COMMAND", rr="NO_CHANGE"),
         note="같은 쪽 명령 2개: unlock 다음 lock")
    tc("FTC-102", F, ["SWR-002"], "명령 순서를 뒤집어(unlock→lock) 마지막 명령(lock)이 남는지 확인. 'unlock 우선' 결함 검출(FTC-101과 반대 방향)",
       s, [EP, WOW], pre="직전 출력은 좌·우 모두 RELEASE(초기 상태). 차속 0.0 km/h.")

    s = Seq()
    s.ev(10.00, None, [("all", "lock", PB), ("left", "unlock", PB)],
         exp=Xp(ll="RELEASE", lr="LOCK", st="NORMAL", rc="DRIVER_COMMAND", rl="DRIVER_COMMAND", rr="DRIVER_COMMAND"),
         note="all lock 뒤에 left unlock")
    tc("FTC-103", F, ["SWR-002"], "all이 left·right 두 명령으로 분해되어 받은 순서대로 처리되는지 확인(all lock 뒤 left unlock이면 좌 RELEASE, 우 LOCK). all을 마지막에 일괄 적용하거나 분해하지 않는 결함 검출",
       s, [EP, WOW], pre="직전 출력은 좌·우 모두 RELEASE. 차속 0.0 km/h.")

    # ---------------- SWR-004 unlock 차속 조건 ----------------
    s = Seq()
    s.ev(10.00, None, [("all", "lock", PB)], exp=Xp(ll="LOCK", lr="LOCK", rc="DRIVER_COMMAND"), note="사전 설정: 양쪽 LOCK")
    s.ev(10.05, {"vehicle_speed_kph": 2.9}, [("left", "unlock", PB)], exp=Xp(ll="RELEASE", lr="LOCK", st="NORMAL", rc="DRIVER_COMMAND", rl="DRIVER_COMMAND", rr="NO_CHANGE"))
    s.ev(10.10, {"vehicle_speed_kph": 2.99}, [("left", "lock", PB)], exp=Xp(ll="LOCK", lr="LOCK", rc="DRIVER_COMMAND"), note="좌 다시 LOCK")
    s.ev(10.15, {"vehicle_speed_kph": 2.99}, [("left", "unlock", PB)], exp=Xp(ll="RELEASE", lr="LOCK", st="NORMAL", rc="DRIVER_COMMAND", rl="DRIVER_COMMAND"),
         note="임계값 직하 2.99 km/h")
    tc("FTC-104", F, ["SWR-004"], "3.0 km/h 미만(2.9, 2.99 km/h)에서 unlock이 적용되는지 확인. 임계 비교를 <= 로 구현했거나 차속을 0.1 단위로 반올림(2.99→3.0)하는 결함 검출",
       s, [BVA, EP], pre="직전 출력은 1단계에서 좌·우 LOCK.")

    s = Seq()
    s.ev(10.00, None, [("all", "lock", PB)], exp=Xp(ll="LOCK", lr="LOCK", rc="DRIVER_COMMAND"), note="사전 설정: 양쪽 LOCK")
    s.ev(10.05, {"vehicle_speed_kph": 3.0}, [("left", "unlock", "avn")],
         exp=Xp(ll="LOCK", lr="LOCK", st="NORMAL", rc="AUTO_LOCK", rl="AUTO_LOCK", rr="AUTO_LOCK", iv="VALID", w="NONE"), note="임계값 3.0 km/h에서 unlock")
    tc("FTC-105", F, ["SWR-004", "SWR-003", "SWR-019"], "3.0 km/h에서 unlock이 적용되지 않고 자동 잠금(순위 9)이 우선하는지 확인. 임계 비교 연산자 오류(< vs <=) 검출",
       s, [BVA, EP], pre="직전 출력은 1단계에서 좌·우 LOCK.")

    # ---------------- SWR-003 자동 잠금 ----------------
    s = Seq()
    s.ev(10.00, {"vehicle_speed_kph": 2.99}, exp=Xp(ll="RELEASE", lr="RELEASE", st="NORMAL", rc="NO_CHANGE"), note="임계 직하")
    s.ev(10.05, {"vehicle_speed_kph": 3.0}, exp=Xp(ll="LOCK", lr="LOCK", st="NORMAL", rc="AUTO_LOCK", rl="AUTO_LOCK", rr="AUTO_LOCK"), note="임계값")
    s.ev(10.10, {"vehicle_speed_kph": 2.99}, exp=Xp(ll="LOCK", lr="LOCK", st="NORMAL", rc="NO_CHANGE"), note="차속 저하 후에도 유지")
    s.ev(10.15, {"vehicle_speed_kph": 0.0}, exp=Xp(ll="LOCK", lr="LOCK", st="NORMAL", rc="NO_CHANGE"))
    tc("FTC-106", F, ["SWR-003"], "2.99 km/h는 잠금 없음, 3.0 km/h에서 첫 평가에 AUTO_LOCK, 이후 차속이 3.0 미만으로 내려가도 LOCK 유지. 임계 오류와 '차속 하강 시 해제' 결함 검출",
       s, [BVA, EP], pre="직전 출력은 좌·우 모두 RELEASE.")

    s = Seq()
    s.ev(10.00, {"vehicle_speed_kph": 3.0}, exp=Xp(ll="LOCK", lr="LOCK", rc="AUTO_LOCK"))
    s.ev(10.05, {"vehicle_speed_kph": 2.0}, exp=Xp(ll="LOCK", lr="LOCK", rc="NO_CHANGE"))
    s.ev(10.10, {"vehicle_speed_kph": 2.0}, [("left", "unlock", PB)], exp=Xp(ll="RELEASE", lr="LOCK", st="NORMAL", rc="DRIVER_COMMAND", rl="DRIVER_COMMAND", rr="NO_CHANGE"))
    s.ev(10.15, {"vehicle_speed_kph": 2.0}, exp=Xp(ll="RELEASE", lr="LOCK", st="NORMAL", rc="NO_CHANGE", rl="NO_CHANGE", rr="NO_CHANGE"), note="2.0 km/h 유지: 자동 재잠금 없음")
    s.ev(10.20, {"vehicle_speed_kph": 3.0}, exp=Xp(ll="LOCK", lr="LOCK", st="NORMAL", rc="AUTO_LOCK", rl="AUTO_LOCK", rr="AUTO_LOCK"), note="다시 3.0 km/h: 자동 잠금 재적용")
    tc("FTC-107", F, ["SWR-003", "SWR-004"], "자동 잠금이 1회성이 아니라 3.0 km/h 이상 평가마다 적용되고(재진입), 하강 구간에서 unlock이 가능하며 재잠금이 없음을 확인. 1회성 플래그·래치 결함 검출",
       s, [ST, WOW], pre="직전 출력은 좌·우 모두 RELEASE.")

    # ---------------- SWR-005 접근위험 ----------------
    s = Seq()
    s.ev(10.00, None, exp=Xp(ll="RELEASE", lr="RELEASE", rc="NO_CHANGE"))
    s.ev(10.05, {"rear_left_approach_risk": True}, exp=Xp(ll="LOCK", lr="RELEASE", st="NORMAL", rc="APPROACH_RISK", rl="APPROACH_RISK", rr="NO_CHANGE"), note="위험 true가 된 평가")
    s.ev(10.10, {"rear_left_approach_risk": True}, [("left", "unlock", PB)], exp=Xp(ll="LOCK", lr="RELEASE", st="NORMAL", rc="APPROACH_RISK", rl="APPROACH_RISK"), note="첫 unlock")
    tc("FTC-108", F, ["SWR-005"], "접근위험 true인 쪽이 LOCK(APPROACH_RISK)이 되고 첫 unlock이 억제되는지 확인. 위험 입력이 반대쪽에 매핑되거나 unlock이 새는 결함 검출",
       s, [EP], pre="직전 출력은 좌·우 모두 RELEASE.")

    s = Seq()
    s.ev(10.00, None, exp=Xp(ll="RELEASE", lr="RELEASE", rc="NO_CHANGE"))
    s.ev(10.05, {"rear_left_approach_risk": True, "ignition_on": False, "fire_detected": True, "overtemperature_detected": True, "adult_present": True, "gear": "X"},
         [("left", "unlock", PB)],
         exp=Xp(ll="LOCK", lr="RELEASE", st="DEGRADED", rc="APPROACH_RISK", rl="APPROACH_RISK", rr="INPUT_INVALID", iv="INVALID"),
         note="접근위험 + 시동 OFF + 화재·과온·성인 + QM 오류(gear) + unlock 동시")
    tc("FTC-109", F, ["SWR-005", "SWR-019"], "접근위험(ASIL B)이 시동 OFF·화재·과온·성인·QM 신호 오류·운전자 unlock이 모두 겹쳐도 좌측 LOCK을 지키는지 확인(P-1 간섭 배제). QM 규칙 누수 결함 검출",
       s, [WOW, EP], pre="직전 출력은 좌·우 모두 RELEASE. 우측은 접근위험이 없으므로 QM 오류(순위 5)로 직전 유지.")

    s = Seq()
    s.ev(10.00, {"rear_left_approach_risk": True}, exp=Xp(ll="LOCK", lr="RELEASE", rc="APPROACH_RISK"))
    s.ev(10.05, {"rear_left_approach_risk": False}, exp=Xp(ll="LOCK", lr="RELEASE", st="NORMAL", rc="NO_CHANGE", rl="NO_CHANGE", rr="NO_CHANGE"), note="위험 해소")
    s.ev(10.10, None, [("left", "unlock", PB)], exp=Xp(ll="RELEASE", lr="RELEASE", st="NORMAL", rc="DRIVER_COMMAND", rl="DRIVER_COMMAND"), note="위험 해소 뒤 unlock은 정상 적용")
    tc("FTC-110", F, ["SWR-005"], "위험이 false가 되어도 출력은 LOCK 유지(NO_CHANGE), 이후 unlock은 억제 없이 적용되는지 확인. 위험 해소 시 자동 해제 또는 억제 상태 잔존 결함 검출",
       s, [EP, ST], pre="직전 출력은 좌·우 모두 RELEASE.")

    # ---------------- SWR-006 override ----------------
    RL = {"rear_left_approach_risk": True}

    def base_override(s, t0=10.05):
        return s

    # O1 경계 10.0 s (부동소수 오차 함정: 20.10-10.10 > 10.0)
    s = Seq()
    s.ev(10.05, RL, exp=Xp(ll="LOCK", lr="RELEASE", st="NORMAL", rc="APPROACH_RISK"), note="사전 설정: 좌 접근위험 LOCK")
    s.ev(10.10, RL, [("left", "unlock", PB)], exp=Xp(ll="LOCK", lr="RELEASE", st="NORMAL", rc="APPROACH_RISK", rl="APPROACH_RISK"), note="첫 억제 시각 = 10.10 s")
    s.ev(20.10, RL, [("left", "unlock", "mobile_app")],
         exp=Xp(ll="RELEASE", lr="RELEASE", st="OVERRIDE", rc="DRIVER_OVERRIDE", rl="DRIVER_OVERRIDE", rr="NO_CHANGE", iv="VALID"),
         note="재입력: 첫 억제로부터 정확히 10.00 s, source는 다름")
    s.ev(20.15, RL, exp=Xp(ll="RELEASE", lr="RELEASE", st="OVERRIDE", rc="DRIVER_OVERRIDE", rl="DRIVER_OVERRIDE"), note="명령 없는 다음 평가: override 유지")
    tc("FTC-111", F, ["SWR-006"], "첫 억제 후 정확히 10.0 s에 재입력하면 override(RELEASE, OVERRIDE)가 되는지, source가 달라도 되는지, override가 다음 평가에서 유지되는지 확인. 10.0 s 경계의 < vs <= 오류와 부동소수 오차(20.10-10.10=10.000000000000002) 미처리 결함 검출",
       s, [BVA, EP, EG], pre="직전 출력은 좌·우 모두 RELEASE.", remarks="시각 쌍 10.10/20.10은 배정밀도 부동소수 뺄셈이 10.0보다 약간 커지는 값을 의도적으로 선택함. 합격은 10.0 이하(<=)로 판정(SWR-006 원문).")

    s = Seq()
    s.ev(10.05, RL, exp=Xp(ll="LOCK", lr="RELEASE", rc="APPROACH_RISK"), note="사전 설정")
    s.ev(10.10, RL, [("left", "unlock", PB)], exp=Xp(ll="LOCK", st="NORMAL", rc="APPROACH_RISK"), note="첫 억제 시각 10.10 s")
    s.ev(20.15, RL, [("left", "unlock", PB)], exp=Xp(ll="LOCK", lr="RELEASE", st="NORMAL", rc="APPROACH_RISK", rl="APPROACH_RISK"), note="10.05 s 경과: 재입력이지만 10.0 s 초과 → 새로운 첫 억제")
    s.ev(20.20, RL, [("left", "unlock", PB)], exp=Xp(ll="RELEASE", lr="RELEASE", st="OVERRIDE", rc="DRIVER_OVERRIDE", rl="DRIVER_OVERRIDE"), note="새 첫 억제(20.15 s)로부터 0.05 s: override")
    tc("FTC-112", F, ["SWR-006"], "10.0 s를 0.05 s 넘긴 재입력은 override가 아니라 새로운 첫 억제로 기록되고, 그 뒤 0.05 s 재입력이 override가 되는지 확인. 창 만료 후 이력 미갱신(영구 첫 억제 유지) 결함 검출",
       s, [BVA, ST], pre="직전 출력은 좌·우 모두 RELEASE.")

    s = Seq()
    s.ev(10.05, RL, exp=Xp(ll="LOCK", rc="APPROACH_RISK"), note="사전 설정")
    s.ev(10.10, RL, [("left", "unlock", PB), ("left", "unlock", "voice")], exp=Xp(ll="LOCK", lr="RELEASE", st="NORMAL", rc="APPROACH_RISK", rl="APPROACH_RISK"),
         note="한 평가에 같은 쪽 unlock 2개")
    s.ev(11.10, RL, [("left", "unlock", PB)], exp=Xp(ll="RELEASE", st="OVERRIDE", rc="DRIVER_OVERRIDE", rl="DRIVER_OVERRIDE"), note="다음 평가의 unlock 1개: 재입력")
    tc("FTC-113", F, ["SWR-006", "SWR-002"], "같은 평가 안의 중복 unlock은 재입력이 아니며(override 아님), 그 평가가 첫 억제로 기록되어 이후 평가의 unlock 1개로 override가 되는지 확인. 평가 안 중복을 재입력으로 세는 결함 검출",
       s, [WOW, EP], pre="직전 출력은 좌·우 모두 RELEASE.")

    s = Seq()
    both = {"rear_left_approach_risk": True, "rear_right_approach_risk": True}
    s.ev(10.05, both, exp=Xp(ll="LOCK", lr="LOCK", rc="APPROACH_RISK", rl="APPROACH_RISK", rr="APPROACH_RISK"), note="사전 설정: 양쪽 접근위험")
    s.ev(10.10, both, [("all", "unlock", PB)], exp=Xp(ll="LOCK", lr="LOCK", st="NORMAL", rc="APPROACH_RISK"), note="all unlock: 양쪽 첫 억제")
    s.ev(10.15, both, [("all", "unlock", "avn")], exp=Xp(ll="RELEASE", lr="RELEASE", st="OVERRIDE", rc="DRIVER_OVERRIDE", rl="DRIVER_OVERRIDE", rr="DRIVER_OVERRIDE"), note="all unlock 재입력: 양쪽 재입력으로 간주")
    tc("FTC-114", F, ["SWR-006"], "all unlock이 양쪽 재입력으로 처리되어 두 쪽이 모두 override가 되는지 확인. all을 한쪽에만 적용하거나 첫 억제를 쪽별로 기록하지 않는 결함 검출",
       s, [EP], pre="직전 출력은 좌·우 모두 RELEASE.")

    s = Seq()
    s.ev(10.05, RL, exp=Xp(ll="LOCK", rc="APPROACH_RISK"), note="사전 설정")
    s.ev(10.10, RL, [("left", "unlock", PB)], exp=Xp(ll="LOCK", st="NORMAL", rc="APPROACH_RISK"), note="차속 0.0 km/h 첫 억제")
    s.ev(10.15, dict(RL, vehicle_speed_kph=2.99), [("left", "unlock", PB)], exp=Xp(ll="RELEASE", lr="RELEASE", st="OVERRIDE", rc="DRIVER_OVERRIDE", rl="DRIVER_OVERRIDE"), note="2.99 km/h 재입력")
    tc("FTC-115", F, ["SWR-006"], "override 성립 차속 경계 직하(2.99 km/h)에서 재입력이 override가 되는지 확인. 경계를 <= 로 구현하거나 차속을 반올림하는 결함 검출(상위 경계 3.0은 FTC-116)",
       s, [BVA], pre="직전 출력은 좌·우 모두 RELEASE.")

    s = Seq()
    s.ev(10.05, RL, exp=Xp(ll="LOCK", lr="RELEASE", rc="APPROACH_RISK"), note="사전 설정")
    s.ev(10.10, dict(RL, vehicle_speed_kph=2.9), [("left", "unlock", PB)], exp=Xp(ll="LOCK", lr="RELEASE", st="NORMAL", rc="APPROACH_RISK"), note="2.9 km/h 첫 억제(기록됨)")
    s.ev(10.15, dict(RL, vehicle_speed_kph=3.0), [("left", "unlock", PB)], exp=Xp(ll="LOCK", lr="LOCK", st="NORMAL", rc="APPROACH_RISK", rl="APPROACH_RISK", rr="AUTO_LOCK"),
         note="3.0 km/h 재입력: override 아님, 기록 삭제")
    s.ev(10.20, dict(RL, vehicle_speed_kph=2.9), [("left", "unlock", PB)], exp=Xp(ll="LOCK", lr="LOCK", st="NORMAL", rc="APPROACH_RISK", rl="APPROACH_RISK", rr="NO_CHANGE"),
         note="2.9 km/h unlock: 삭제된 기록이므로 새 첫 억제(override 아님)")
    s.ev(10.25, dict(RL, vehicle_speed_kph=2.9), [("left", "unlock", PB)], exp=Xp(ll="RELEASE", lr="LOCK", st="OVERRIDE", rc="DRIVER_OVERRIDE", rl="DRIVER_OVERRIDE", rr="NO_CHANGE"),
         note="새 첫 억제 후 재입력: override")
    tc("FTC-116", F, ["SWR-006", "SWR-004"], "3.0 km/h에서의 재입력은 override가 아니며(LOCK), 이 때 첫 억제 기록이 지워져 차속이 다시 내려가도 이전 억제가 재입력으로 쓰이지 않는지 확인. 차속 경계(3.0)와 '종료 조건에서 기록 삭제' 결함 검출",
       s, [BVA, WOW, ST], pre="직전 출력은 좌·우 모두 RELEASE.")

    def override_prefix(s):
        s.ev(10.05, RL, exp=Xp(ll="LOCK", lr="RELEASE", rc="APPROACH_RISK"), note="사전 설정")
        s.ev(10.10, RL, [("left", "unlock", PB)], exp=Xp(ll="LOCK", st="NORMAL", rc="APPROACH_RISK"), note="첫 억제")
        s.ev(10.15, RL, [("left", "unlock", PB)], exp=Xp(ll="RELEASE", lr="RELEASE", st="OVERRIDE", rc="DRIVER_OVERRIDE", rl="DRIVER_OVERRIDE"), note="재입력: override 성립")

    s = Seq()
    override_prefix(s)
    s.ev(10.20, dict(RL, vehicle_speed_kph=3.0), exp=Xp(ll="LOCK", lr="LOCK", st="NORMAL", rc="APPROACH_RISK", rl="APPROACH_RISK", rr="AUTO_LOCK"), note="override 중 차속 3.0 km/h: 종료")
    s.ev(10.25, dict(RL, vehicle_speed_kph=0.0), exp=Xp(ll="LOCK", lr="LOCK", st="NORMAL", rc="APPROACH_RISK", rl="APPROACH_RISK", rr="NO_CHANGE"), note="차속 0.0 km/h 복귀: override 재개 없음")
    tc("FTC-117", F, ["SWR-006"], "override 중 차속이 3.0 km/h가 되면 그 쪽이 LOCK이 되고, 차속이 다시 0.0이 되어도 override가 되살아나지 않는지 확인. 종료 조건 미처리·종료 후 재개 결함 검출",
       s, [ST, BVA], pre="직전 출력은 좌·우 모두 RELEASE.")

    s = Seq()
    override_prefix(s)
    s.ev(10.20, None, exp=Xp(ll="RELEASE", lr="RELEASE", st="NORMAL", rc="NO_CHANGE", rl="NO_CHANGE"), note="위험 false: override 종료, 출력은 직전 유지(RELEASE)")
    s.ev(10.25, RL, exp=Xp(ll="LOCK", lr="RELEASE", st="NORMAL", rc="APPROACH_RISK", rl="APPROACH_RISK"), note="위험 true 재발생: override 없이 새로 LOCK")
    tc("FTC-118", F, ["SWR-006", "SWR-005"], "위험이 false가 되면 override가 끝나 RELEASE 유지(NO_CHANGE), 위험이 다시 true가 되면 override 없이 LOCK이 되는지 확인. override 종료 미처리(위험 재발 시 RELEASE 지속) 결함 검출",
       s, [ST], pre="직전 출력은 좌·우 모두 RELEASE.")

    s = Seq()
    override_prefix(s)
    s.ev(10.20, dict(RL, ignition_on=False), exp=Xp(ll="LOCK", lr="RELEASE", st="OFF", rc="APPROACH_RISK", rl="APPROACH_RISK", rr="IGNITION_OFF"), note="시동 OFF: override 종료, 접근위험 LOCK이 이김")
    s.ev(10.25, RL, exp=Xp(ll="LOCK", lr="RELEASE", st="NORMAL", rc="APPROACH_RISK", rl="APPROACH_RISK"), note="시동 ON 복귀 + 위험 true: override 재개 없음")
    tc("FTC-119", F, ["SWR-006", "SWR-020"], "override 중 시동 OFF가 되면 override가 끝나(좌 LOCK, state=OFF), 시동 ON 복귀 후 위험이 true여도 override가 아닌 LOCK인지 확인. 시동 OFF 종료 조건 누락 결함 검출",
       s, [ST], pre="직전 출력은 좌·우 모두 RELEASE.")

    s = Seq()
    s.ev(10.05, RL, exp=Xp(ll="LOCK", rc="APPROACH_RISK"), note="사전 설정")
    s.ev(10.10, dict(RL, sensor_fault=True), [("left", "unlock", PB)],
         exp=Xp(ll="LOCK", lr="RELEASE", st="FAULT", rc="SENSOR_FAULT", rl="SENSOR_FAULT", w="W_SENSOR_FAULT"), note="sensor fault 중 unlock: 첫 억제로 세지 않음")
    s.ev(10.15, RL, [("left", "unlock", PB)], exp=Xp(ll="LOCK", lr="RELEASE", st="NORMAL", rc="APPROACH_RISK", rl="APPROACH_RISK", w="NONE"), note="복귀 후 첫 unlock: 첫 억제(override 아님)")
    s.ev(10.20, RL, [("left", "unlock", PB)], exp=Xp(ll="RELEASE", lr="RELEASE", st="OVERRIDE", rc="DRIVER_OVERRIDE", rl="DRIVER_OVERRIDE"), note="그 다음 unlock: override")
    tc("FTC-120", F, ["SWR-006", "SWR-021"], "순위 3(sensor fault) 평가의 unlock이 첫 억제로 기록되지 않아, 복귀 후 unlock 한 번으로는 override가 되지 않는지 확인. 순위 3 평가 명령을 override 계수에 넣는 결함 검출",
       s, [WOW, ST], pre="직전 출력은 좌·우 모두 RELEASE.")

    s = Seq()
    s.ev(10.05, RL, exp=Xp(ll="LOCK", rc="APPROACH_RISK"), note="사전 설정")
    s.ev(10.10, dict(RL, rear_right_approach_risk=1), [("left", "unlock", PB)],
         exp=Xp(ll="LOCK", lr="RELEASE", st="DEGRADED", rc="INPUT_INVALID", iv="INVALID"), note="ASIL B 신호 오류(순위 2) 평가의 unlock: 첫 억제로 세지 않음")
    s.ev(10.15, RL, [("left", "unlock", PB)], exp=Xp(ll="LOCK", lr="RELEASE", st="NORMAL", rc="APPROACH_RISK", rl="APPROACH_RISK", iv="VALID"), note="유효 평가 첫 unlock: 첫 억제(override 아님)")
    s.ev(10.20, RL, [("left", "unlock", PB)], exp=Xp(ll="RELEASE", st="OVERRIDE", rc="DRIVER_OVERRIDE", rl="DRIVER_OVERRIDE"), note="다음 unlock: override")
    tc("FTC-121", F, ["SWR-006", "SWR-013"], "순위 2(ASIL B 입력 오류) 평가의 unlock이 override 계수에서 제외되는지 확인(FTC-120과 다른 순위 경로). 입력 오류 평가의 명령 누수 결함 검출",
       s, [WOW, ST, FI], pre="직전 출력은 좌·우 모두 RELEASE.")

    s = Seq()
    s.ev(10.05, RL, exp=Xp(ll="LOCK", rc="APPROACH_RISK"), note="사전 설정")
    s.ev(20.15, RL, [("left", "unlock", PB)], ts=20.00, exp=Xp(ll="LOCK", lr="RELEASE", st="NORMAL", rc="APPROACH_RISK", iv="VALID"),
         note="스냅샷 ts=20.00(지연 0.15 s, 정상): 명령 시각은 20.00 s")
    s.ev(30.10, RL, [("left", "unlock", PB)], ts=30.05, exp=Xp(ll="LOCK", lr="RELEASE", st="NORMAL", rc="APPROACH_RISK", rl="APPROACH_RISK", iv="VALID"),
         note="ts=30.05: 명령 시각 30.05 s, 첫 억제로부터 10.05 s → override 아님(평가 시각 기준이면 9.95 s로 override가 됨)")
    tc("FTC-122", F, ["SWR-006", "SWR-022"], "override 창 판정이 평가 시각이 아니라 쓰는 스냅샷의 source_timestamp_s(명령 시각)로 이루어지는지 확인. 평가 시각을 쓰면 9.95 s로 보아 잘못 override가 되는 결함 검출",
       s, [WOW, BVA], pre="직전 출력은 좌·우 모두 RELEASE.", remarks="두 스냅샷의 나이는 0.15 s, 0.05 s로 0.200 s 이내(정상 판정).")

    s = Seq()
    override_prefix(s)
    s.ev(10.20, RL, [("left", "lock", PB)], exp=Xp(ll="RELEASE", lr="RELEASE", st="OVERRIDE", rc="DRIVER_OVERRIDE", rl="DRIVER_OVERRIDE"), note="override 중 같은 쪽 lock 명령")
    tc("FTC-123", F, ["SWR-006", "SWR-019"], "override 활성 중 운전자 lock(순위 10)이 순위 4 override 결과(RELEASE)를 바꾸지 못하는지 확인. 명시 요구가 없어 1.4절 순위(4 > 10)에서 도출한 기대값",
       s, [WOW, ST], origin="제안", pre="직전 출력은 좌·우 모두 RELEASE.", remarks="가정: override 중 lock 명령은 순위 4가 이겨 무시된다(질의 Q-07).")

    # ---------------- SWR-009 ----------------
    s = Seq()
    s.ev(10.00, None, [("all", "lock", PB)], exp=Xp(ll="LOCK", lr="LOCK", rc="DRIVER_COMMAND"), note="사전 설정: 양쪽 LOCK")
    s.ev(10.05, RL, [("all", "unlock", PB)], exp=Xp(ll="LOCK", lr="RELEASE", st="NORMAL", rc="APPROACH_RISK", rl="APPROACH_RISK", rr="DRIVER_COMMAND"),
         note="좌 위험 + all unlock")
    tc("FTC-124", F, ["SWR-009", "SWR-005"], "좌측 위험이 우측 출력에 영향을 주지 않는지(우측 unlock은 정상 적용) 확인. 위험 억제를 양쪽에 걸거나 공유 플래그를 쓰는 결함 검출",
       s, [EP], pre="직전 출력은 1단계에서 좌·우 LOCK.")

    s = Seq()
    s.ev(10.05, both, exp=Xp(ll="LOCK", lr="LOCK", rc="APPROACH_RISK"), note="사전 설정: 양쪽 접근위험")
    s.ev(10.10, both, [("left", "unlock", PB)], exp=Xp(ll="LOCK", lr="LOCK", st="NORMAL", rc="APPROACH_RISK"), note="좌 첫 억제")
    s.ev(10.15, both, [("left", "unlock", PB)], exp=Xp(ll="RELEASE", lr="LOCK", st="OVERRIDE", rc="DRIVER_OVERRIDE", rl="DRIVER_OVERRIDE", rr="APPROACH_RISK"), note="좌 override")
    s.ev(10.20, both, [("right", "unlock", PB)], exp=Xp(ll="RELEASE", lr="LOCK", st="OVERRIDE", rc="DRIVER_OVERRIDE", rl="DRIVER_OVERRIDE", rr="APPROACH_RISK"),
         note="우 첫 억제: 좌 override가 우 억제를 풀지 않음(override 아님)")
    s.ev(10.25, both, [("right", "unlock", PB)], exp=Xp(ll="RELEASE", lr="RELEASE", st="OVERRIDE", rc="DRIVER_OVERRIDE", rl="DRIVER_OVERRIDE", rr="DRIVER_OVERRIDE"), note="우 override")
    tc("FTC-125", F, ["SWR-009", "SWR-006"], "첫 억제 이력과 override가 쪽별로 독립인지 확인(좌 override 중 우 unlock 1회는 override가 아님). 좌·우 이력 공유 결함 검출",
       s, [WOW, ST], pre="직전 출력은 좌·우 모두 RELEASE.")

    s = Seq()
    mix = {"rear_left_approach_risk": True, "isofix_right": True}
    s.ev(10.00, mix, exp=Xp(ll="LOCK", lr="LOCK", st="NORMAL", rc="APPROACH_RISK", rl="APPROACH_RISK", rr="ISOFIX"), note="사전 설정: 좌 접근위험, 우 ISOFIX")
    s.ev(10.05, mix, [("left", "unlock", PB)], exp=Xp(ll="LOCK", lr="LOCK", rc="APPROACH_RISK"), note="좌 첫 억제")
    s.ev(10.10, mix, [("left", "unlock", PB)], exp=Xp(ll="RELEASE", lr="LOCK", st="OVERRIDE", rc="DRIVER_OVERRIDE", rl="DRIVER_OVERRIDE", rr="ISOFIX"),
         note="좌 override + 우 ISOFIX 동시")
    tc("FTC-126", F, ["SWR-009", "SWR-006", "SWR-018"], "좌 override와 우 ISOFIX가 같은 평가에 있을 때 좌 RELEASE(DRIVER_OVERRIDE), 우 LOCK(ISOFIX), reason_code=DRIVER_OVERRIDE, state=OVERRIDE인지 확인(수용기준 직접 검증). 쪽별 혼합 처리 결함 검출",
       s, [WOW, EP], pre="직전 출력은 1단계에서 좌·우 LOCK.")

    # ---------------- SWR-007 충돌 ----------------
    CF = {"crash_status": "CONFIRMED"}
    s = Seq()
    s.ev(10.00, {"vehicle_speed_kph": 3.0}, exp=Xp(ll="LOCK", lr="LOCK", rc="AUTO_LOCK"), note="사전 설정: LOCK")
    s.ev(10.25, CF, ts=10.05, exp=Xp(ll="RELEASE", lr="RELEASE", st="NORMAL", rc="CRASH_CONFIRMED", rl="CRASH_CONFIRMED", rr="CRASH_CONFIRMED", iv="VALID"),
         note="CONFIRMED 스냅샷(ts=10.05, 나이 0.200 s). 평가 시각−ts = 0.200 s ≤ 0.300 s")
    s.ev(10.30, {"crash_status": "NONE", "vehicle_speed_kph": 3.0, "isofix_left": True, "isofix_right": True, "rear_left_approach_risk": True, "rear_right_approach_risk": True},
         [("all", "lock", PB)], exp=Xp(ll="RELEASE", lr="RELEASE", st="NORMAL", rc="CRASH_CONFIRMED"), note="NONE 수신 + 접근위험·ISOFIX·자동잠금·lock 모두")
    s.ev(10.35, {"sensor_fault": True}, exp=Xp(ll="RELEASE", lr="RELEASE", st="FAULT", rc="CRASH_CONFIRMED", rl="CRASH_CONFIRMED", rr="CRASH_CONFIRMED"), note="래치 중 sensor fault")
    tc("FTC-127", F, ["SWR-007"], "나이 0.200 s인 CONFIRMED로 래치가 서 0.300 s 이내(0.200 s) RELEASE가 되고, 이후 NONE·접근위험·ISOFIX·자동 잠금·lock·sensor fault가 와도 RELEASE가 유지되는지 확인. 래치 미유지·낮은 순위 규칙 누수 결함 검출",
       s, [EP, BVA, ST], pre="직전 출력은 1단계에서 좌·우 LOCK.")

    s = Seq()
    s.ev(15.05, {"vehicle_speed_kph": 3.0}, exp=Xp(ll="LOCK", lr="LOCK", rc="AUTO_LOCK"), note="사전 설정: LOCK")
    s.ev(16.10, CF, ts=15.10, exp=Xp(ll="RELEASE", lr="RELEASE", st="DEGRADED", rc="CRASH_CONFIRMED", rl="CRASH_CONFIRMED", rr="CRASH_CONFIRMED", iv="STALE"),
         note="CONFIRMED 스냅샷 나이 정확히 1.00 s(ts=15.10, 평가 시각 16.10)")
    tc("FTC-128", F, ["SWR-007", "SWR-013"], "나이 1.0 s(상한 경계)의 늦게 도착한 CONFIRMED도 래치를 세우고(지연 0.200 s 초과와 무관), 입력은 STALE/DEGRADED로 표시되는지 확인. 1.0 s 경계 연산자 오류와 부동소수 오차(16.10-15.10=1.0000000000000018) 처리 결함 검출",
       s, [BVA, EP, EG], pre="직전 출력은 1단계에서 좌·우 LOCK.", remarks="input_validity=STALE은 SWR-013 ①③에서 도출(늦은 스냅샷이 기준 스냅샷이 되며 나이 1.00 s > 0.200 s). 질의 Q-16.")

    s = Seq()
    s.ev(15.05, {"vehicle_speed_kph": 3.0}, exp=Xp(ll="LOCK", lr="LOCK", rc="AUTO_LOCK"), note="사전 설정: LOCK")
    s.ev(16.15, CF, ts=15.10, exp=Xp(ll="LOCK", lr="LOCK", st="DEGRADED", rc="INPUT_STALE", rl="INPUT_STALE", rr="INPUT_STALE", iv="STALE"),
         note="CONFIRMED 나이 1.05 s: 래치 없음")
    s.ev(16.20, None, [("left", "unlock", PB)], exp=Xp(ll="RELEASE", lr="LOCK", st="NORMAL", rc="DRIVER_COMMAND", iv="VALID"), note="래치가 없으므로 unlock 정상 적용")
    tc("FTC-129", F, ["SWR-007"], "나이 1.05 s CONFIRMED로는 래치가 서지 않고(직전 LOCK 유지, 입력 STALE), 이후 unlock이 적용되는지 확인. 나이 상한 미검사 결함 검출",
       s, [BVA, EP], pre="직전 출력은 1단계에서 좌·우 LOCK.")

    s = Seq()
    s.ev(9.95, {"vehicle_speed_kph": 3.0}, exp=Xp(ll="LOCK", lr="LOCK", rc="AUTO_LOCK"), note="사전 설정: LOCK")
    s.ev(10.00, CF, ts=10.05, exp=Xp(ll="RELEASE", lr="RELEASE", st="NORMAL", rc="CRASH_CONFIRMED", iv="VALID"), note="CONFIRMED, ts가 평가 시각보다 0.050 s 미래(허용 경계)")
    tc("FTC-130", F, ["SWR-007", "SWR-013"], "미래 0.050 s 타임스탬프의 CONFIRMED가 유효로 처리되어 래치가 서는지 확인. 나이 음수(−0.05 s)를 오류로 보거나 허용 오차 부동소수 처리(10.05−10.00>0.05) 결함 검출",
       s, [BVA, EG], pre="직전 출력은 1단계에서 좌·우 LOCK.")

    s = Seq()
    s.ev(9.95, {"vehicle_speed_kph": 3.0}, exp=Xp(ll="LOCK", lr="LOCK", rc="AUTO_LOCK"), note="사전 설정: LOCK")
    s.ev(10.00, CF, ts=10.051, exp=Xp(ll="LOCK", lr="LOCK", st="DEGRADED", rc="INPUT_INVALID", iv="INVALID"), note="CONFIRMED, ts가 0.051 s 미래: 형식 오류, 래치 없음")
    s.ev(10.05, None, [("left", "unlock", PB)], exp=Xp(ll="RELEASE", lr="LOCK", st="NORMAL", rc="DRIVER_COMMAND", iv="VALID"), note="래치가 없으므로 unlock 적용")
    tc("FTC-131", F, ["SWR-007", "SWR-013"], "타임스탬프가 0.051 s 미래인 CONFIRMED는 형식 오류로 보아 래치를 세우지 않는지 확인(충돌 판정은 타임스탬프가 유효할 때만). 허용 오차 초과 미검사 결함 검출",
       s, [BVA, EP, FI], pre="직전 출력은 1단계에서 좌·우 LOCK.")

    s = Seq()
    s.ev(10.00, {"vehicle_speed_kph": 3.0}, exp=Xp(ll="LOCK", lr="LOCK", rc="AUTO_LOCK"), note="사전 설정: LOCK(기준 스냅샷 ts=10.00)")
    s.ev(10.05, CF, ts=9.95, exp=Xp(ll="RELEASE", lr="RELEASE", st="DEGRADED", rc="CRASH_CONFIRMED", iv="INVALID"),
         note="CONFIRMED이지만 ts=9.95가 기준 스냅샷(10.00)보다 작음(역행)")
    tc("FTC-132", F, ["SWR-007", "SWR-013"], "타임스탬프 역행 스냅샷이어도 충돌 판정에는 역행 검사를 적용하지 않아 래치가 서고, 나머지 신호는 INVALID/DEGRADED로 처리되는지 확인(v1.2 명시). 충돌 판정에 역행 검사를 적용하는 결함 검출",
       s, [WOW, EP], pre="직전 출력은 1단계에서 좌·우 LOCK.")

    s = Seq()
    s.ev(10.00, {"vehicle_speed_kph": 3.0}, exp=Xp(ll="LOCK", lr="LOCK", rc="AUTO_LOCK"), note="사전 설정: LOCK")
    s.ev(10.05, CF, exp=Xp(ll="RELEASE", lr="RELEASE", rc="CRASH_CONFIRMED"), note="래치 성립")
    s.ev(10.10, {"ignition_on": False}, exp=Xp(ll="RELEASE", lr="RELEASE", st="OFF", rc="IGNITION_OFF"), note="시동 OFF + NONE: 래치 해제")
    s.ev(10.15, {"vehicle_speed_kph": 3.0}, exp=Xp(ll="LOCK", lr="LOCK", st="NORMAL", rc="AUTO_LOCK", rl="AUTO_LOCK", rr="AUTO_LOCK"), note="시동 ON + 차속 3.0 km/h: 래치가 풀려 자동 잠금")
    tc("FTC-133", F, ["SWR-007"], "시동 OFF(유효)+CONFIRMED 아님 스냅샷으로 래치가 해제되고 시동 ON 이후 정상 판정으로 돌아가는지 확인. 래치 영구 유지 결함 검출",
       s, [ST, EP], pre="직전 출력은 1단계에서 좌·우 LOCK.")

    s = Seq()
    s.ev(10.00, {"vehicle_speed_kph": 3.0}, exp=Xp(ll="LOCK", lr="LOCK", rc="AUTO_LOCK"), note="사전 설정: LOCK")
    s.ev(10.05, CF, exp=Xp(ll="RELEASE", lr="RELEASE", rc="CRASH_CONFIRMED"), note="래치 성립")
    s.ev(10.10, dict(CF, ignition_on=False), exp=Xp(ll="RELEASE", lr="RELEASE", st="OFF", rc="CRASH_CONFIRMED"), note="시동 OFF이지만 crash_status가 여전히 CONFIRMED: 해제 안 됨")
    s.ev(10.15, {"vehicle_speed_kph": 3.0}, exp=Xp(ll="RELEASE", lr="RELEASE", st="NORMAL", rc="CRASH_CONFIRMED"), note="시동 ON + NONE: 해제 조건(시동 OFF)이 없었으므로 래치 유지")
    tc("FTC-134", F, ["SWR-007"], "시동 OFF만으로는(crash_status가 CONFIRMED 그대로) 래치가 풀리지 않는지 확인. 해제 조건에서 crash_status 검사 누락 결함 검출(FTC-133과 쌍)",
       s, [ST, EP], pre="직전 출력은 1단계에서 좌·우 LOCK.")

    s = Seq()
    s.ev(10.00, {"vehicle_speed_kph": 3.0}, exp=Xp(ll="LOCK", lr="LOCK", rc="AUTO_LOCK"), note="사전 설정: LOCK")
    s.ev(10.05, CF, exp=Xp(ll="RELEASE", lr="RELEASE", rc="CRASH_CONFIRMED"), note="래치 성립")
    s.ev(10.10, {"ignition_on": False, "crash_status": "PENDING"}, exp=Xp(ll="RELEASE", lr="RELEASE", st="OFF", rc="IGNITION_OFF"), note="시동 OFF + PENDING(CONFIRMED 아님): 래치 해제")
    s.ev(10.15, {"vehicle_speed_kph": 3.0}, exp=Xp(ll="LOCK", lr="LOCK", st="NORMAL", rc="AUTO_LOCK"), note="시동 ON + NONE + 3.0 km/h: 자동 잠금")
    tc("FTC-135", F, ["SWR-007", "SWR-008"], "해제 조건의 'CONFIRMED가 아님'에 PENDING도 포함되어 래치가 해제되는지 확인(동치 클래스 NONE/PENDING). NONE만 해제로 보는 결함 검출",
       s, [EP, ST], pre="직전 출력은 1단계에서 좌·우 LOCK.")

    s = Seq()
    s.ev(10.00, {"vehicle_speed_kph": 3.0}, exp=Xp(ll="LOCK", lr="LOCK", rc="AUTO_LOCK"), note="사전 설정: LOCK")
    s.ev(10.05, CF, exp=Xp(ll="RELEASE", lr="RELEASE", rc="CRASH_CONFIRMED"), note="래치 성립")
    s.ev(10.10, {"ignition_on": False, "vehicle_speed_kph": 300.1}, exp=Xp(ll="RELEASE", lr="RELEASE", st="DEGRADED", rc="INPUT_INVALID", iv="INVALID"),
         note="래치 해제 스냅샷(시동 OFF, NONE)이지만 차속 300.1 km/h(ASIL B 범위 오류)")
    s.ev(10.15, {"vehicle_speed_kph": 3.0}, exp=Xp(ll="LOCK", lr="LOCK", st="NORMAL", rc="AUTO_LOCK"), note="시동 ON + 3.0 km/h: 래치가 풀렸다면 자동 잠금")
    tc("FTC-136", F, ["SWR-007", "SWR-013"], "해제 판정이 crash_status·ignition_on·source_timestamp_s의 유효성만 요구하고 다른 신호(차속) 오류와 무관한지 확인. 다른 신호 오류 시 해제가 막히는 결함 검출",
       s, [WOW, FI], origin="제안", pre="직전 출력은 1단계에서 좌·우 LOCK.", remarks="가정: 3개 신호가 유효하면 다른 신호 오류와 무관하게 해제된다(원문은 '~일 때만'이라 필요조건만 명시). 질의 Q-08.")

    s = Seq()
    s.ev(10.00, {"vehicle_speed_kph": 3.0}, exp=Xp(ll="LOCK", lr="LOCK", rc="AUTO_LOCK"), note="사전 설정: LOCK")
    s.ev(10.05, {"crash_status": "confirmed"}, exp=Xp(ll="LOCK", lr="LOCK", st="DEGRADED", rc="INPUT_INVALID", iv="INVALID"), note="소문자 \"confirmed\"(미등록 enum)")
    s.ev(10.10, None, [("left", "unlock", PB)], exp=Xp(ll="RELEASE", lr="LOCK", st="NORMAL", rc="DRIVER_COMMAND", iv="VALID"), note="래치 없음 확인")
    tc("FTC-137", F, ["SWR-007", "SWR-013"], "crash_status 문자열 비교가 대소문자 구분인지(\"confirmed\"는 미등록 enum으로 INVALID, 래치 없음) 확인. 대소문자 무시 비교 결함 검출",
       s, [EP, FI], pre="직전 출력은 1단계에서 좌·우 LOCK.")

    s = Seq()
    s.ev(10.00, {"crash_status": "CONFIRMED", "vehicle_speed_kph": 3.0}, exp=Xp(ll="RELEASE", lr="RELEASE", st="NORMAL", rc="CRASH_CONFIRMED", iv="VALID"),
         note="시작 직후 첫 평가부터 CONFIRMED + 3.0 km/h")
    tc("FTC-138", F, ["SWR-007"], "초기화 직후 첫 평가의 CONFIRMED가 래치를 세워 RELEASE(자동 잠금 없음)가 되는지 확인. 첫 평가를 STALE/초기화 처리로 건너뛰는 결함 검출",
       s, [WOW], pre="직전 출력은 좌·우 모두 RELEASE(초기 상태, 이전 스냅샷 없음).")

    s = Seq()
    s.ev(10.00, {"ignition_on": False}, exp=Xp(ll="RELEASE", lr="RELEASE", st="OFF", rc="IGNITION_OFF", iv="VALID"), note="사전 설정: 시동 OFF NONE 스냅샷이 기준 스냅샷")
    s.ev(10.05, {"crash_status": "CONFIRMED", "ignition_on": False, "rear_right_approach_risk": 1},
         exp=Xp(ll="RELEASE", lr="RELEASE", st="DEGRADED", rc="CRASH_CONFIRMED", iv="INVALID"), note="CONFIRMED + ASIL B 오류(기준 스냅샷이 되지 못함): 래치 성립")
    s.ev(10.10, nosnap=True, exp=Xp(ll="RELEASE", lr="RELEASE", st="OFF", rc="CRASH_CONFIRMED", rl="CRASH_CONFIRMED", rr="CRASH_CONFIRMED", iv="VALID"),
         note="스냅샷 없음: 기준 스냅샷은 1단계(시동 OFF, NONE)")
    s.ev(10.15, {"vehicle_speed_kph": 3.0}, exp=Xp(ll="RELEASE", lr="RELEASE", st="NORMAL", rc="CRASH_CONFIRMED"), note="시동 ON, NONE, 3.0 km/h: 래치 유지")
    tc("FTC-139", F, ["SWR-007", "SWR-022"], "스냅샷 없는 주기에 기준 스냅샷의 '시동 OFF+NONE'을 다시 써서 래치를 해제하지 않는지 확인(reason이 IGNITION_OFF로 바뀌거나 이후 자동 잠금이 되면 결함). 직전 값 재사용 해제 결함 검출",
       s, [WOW, ST], pre="직전 출력은 좌·우 모두 RELEASE(초기 상태).")

    # ---------------- SWR-008 PENDING ----------------
    PD = {"crash_status": "PENDING"}
    s = Seq()
    s.ev(10.00, None, [("left", "lock", PB)], exp=Xp(ll="LOCK", lr="RELEASE", rc="DRIVER_COMMAND"), note="사전 설정: 좌 LOCK, 우 RELEASE")
    s.ev(10.05, dict(PD, isofix_right=True), [("left", "unlock", PB)],
         exp=Xp(ll="RELEASE", lr="RELEASE", st="NORMAL", rc="CRASH_PENDING", rl="DRIVER_COMMAND", rr="CRASH_PENDING"),
         note="PENDING 중 좌 unlock(RELEASE 방향) + 우 ISOFIX(막힘)")
    tc("FTC-140", F, ["SWR-008", "SWR-019"], "PENDING이 RELEASE 방향(좌 unlock)은 막지 않고 우측 ISOFIX LOCK만 막으며, reason_code가 막은 규칙(순위 8)의 순위로 비교되어 CRASH_PENDING이 되는지 확인(좌 DRIVER_COMMAND는 순위 10). 막은 이유 순위 계산 결함 검출",
       s, [WOW, EP], pre="직전 출력은 1단계에서 좌 LOCK / 우 RELEASE.")

    s = Seq()
    s.ev(14.10, PD, exp=Xp(ll="RELEASE", lr="RELEASE", st="NORMAL", rc="NO_CHANGE"), note="PENDING 최초 평가(타이머 시작 14.10 s)")
    s.ev(16.05, dict(PD, vehicle_speed_kph=3.0), exp=Xp(ll="RELEASE", lr="RELEASE", st="NORMAL", rc="CRASH_PENDING", rl="CRASH_PENDING", rr="CRASH_PENDING"), note="경과 1.95 s: 막음")
    s.ev(16.10, dict(PD, vehicle_speed_kph=3.0), exp=Xp(ll="RELEASE", lr="RELEASE", st="NORMAL", rc="CRASH_PENDING", rl="CRASH_PENDING", rr="CRASH_PENDING"), note="경과 정확히 2.00 s(16.10−14.10): 막음")
    s.ev(16.15, dict(PD, vehicle_speed_kph=3.0), exp=Xp(ll="LOCK", lr="LOCK", st="NORMAL", rc="AUTO_LOCK", rl="AUTO_LOCK", rr="AUTO_LOCK"), note="경과 2.05 s: 막지 않음, 자동 잠금 적용")
    tc("FTC-141", F, ["SWR-008"], "PENDING 지속 1.95/2.00/2.05 s에서 2.0 s 이하는 막고 2.05 s에서 자동 잠금이 적용되는지 확인. 2.0 s 경계 연산자 오류와 부동소수 오차(16.10−14.10>2.0) 처리 결함 검출",
       s, [BVA, ST, EG], pre="직전 출력은 좌·우 모두 RELEASE.")

    s = Seq()
    s.ev(10.00, PD, exp=Xp(ll="RELEASE", lr="RELEASE", rc="NO_CHANGE"), note="PENDING 시작 10.00 s")
    s.ev(11.00, {"crash_status": "NONE"}, exp=Xp(ll="RELEASE", lr="RELEASE", rc="NO_CHANGE"), note="NONE: 타이머 삭제")
    s.ev(11.05, PD, exp=Xp(ll="RELEASE", lr="RELEASE", rc="NO_CHANGE"), note="PENDING 재시작(새 타이머 11.05 s)")
    s.ev(13.00, dict(PD, vehicle_speed_kph=3.0), exp=Xp(ll="RELEASE", lr="RELEASE", rc="CRASH_PENDING"), note="재시작 후 1.95 s(최초 시작 기준 3.00 s): 막음")
    s.ev(13.10, dict(PD, vehicle_speed_kph=3.0), exp=Xp(ll="LOCK", lr="LOCK", rc="AUTO_LOCK"), note="재시작 후 2.05 s: 막지 않음")
    tc("FTC-142", F, ["SWR-008"], "PENDING→NONE→PENDING에서 타이머가 새로 시작되는지 확인(재시작 후 1.95 s는 막힘, 2.05 s는 풀림). NONE 수신 시 타이머를 지우지 않는 결함 검출",
       s, [ST, WOW], pre="직전 출력은 좌·우 모두 RELEASE.")

    s = Seq()
    s.ev(10.00, PD, exp=Xp(ll="RELEASE", lr="RELEASE", rc="NO_CHANGE"), note="PENDING 시작 10.00 s")
    s.ev(10.50, dict(PD, gear="X"), exp=Xp(ll="RELEASE", lr="RELEASE", st="DEGRADED", rc="INPUT_INVALID", iv="INVALID"), note="QM 오류(gear) 스냅샷: 타이머에 영향 없어야 함")
    s.ev(11.00, nosnap=True, exp=Xp(ll="RELEASE", lr="RELEASE", st="DEGRADED", rc="INPUT_STALE", iv="STALE"), note="스냅샷 없음(기준 스냅샷 나이 0.50 s → STALE): 타이머에 영향 없어야 함")
    s.ev(12.05, dict(PD, vehicle_speed_kph=3.0), exp=Xp(ll="LOCK", lr="LOCK", st="NORMAL", rc="AUTO_LOCK", iv="VALID"), note="최초 PENDING으로부터 2.05 s: 막지 않음")
    tc("FTC-143", F, ["SWR-008", "SWR-013"], "신호 오류 스냅샷과 스냅샷 없는 주기가 PENDING 타이머를 재시작하지 않는지 확인(2.05 s에 자동 잠금 적용). 오류·무스냅샷 평가가 타이머를 초기화하는 결함 검출",
       s, [WOW, ST], pre="직전 출력은 좌·우 모두 RELEASE.")

    s = Seq()
    s.ev(10.00, dict(PD, vehicle_speed_kph=3.0), exp=Xp(ll="RELEASE", lr="RELEASE", rc="CRASH_PENDING"), note="PENDING 중 3.0 km/h: 막힘")
    s.ev(10.05, {"vehicle_speed_kph": 3.0}, exp=Xp(ll="LOCK", lr="LOCK", st="NORMAL", rc="AUTO_LOCK"), note="NONE 수신: 막힘 해제")
    tc("FTC-144", F, ["SWR-008"], "PENDING→NONE 전환 평가에서 즉시 막힘이 풀려 자동 잠금이 적용되는지 확인(수용기준). 막힘 해제 지연·잔존 결함 검출",
       s, [ST, EP], pre="직전 출력은 좌·우 모두 RELEASE.")

    s = Seq()
    s.ev(10.00, {"vehicle_speed_kph": 3.0}, exp=Xp(ll="LOCK", lr="LOCK", rc="AUTO_LOCK"), note="사전 설정: LOCK")
    s.ev(10.05, dict(PD, isofix_left=True), exp=Xp(ll="LOCK", lr="LOCK"), note="PENDING 중 ISOFIX true, 직전 LOCK")
    tc("FTC-145", F, ["SWR-008"], "PENDING이 이미 LOCK인 출력을 RELEASE로 되돌리지 않는지 확인(막는 대상은 RELEASE→LOCK 전환뿐). PENDING 시 잠금을 해제해 버리는 결함 검출",
       s, [EP, WOW], origin="제안", pre="직전 출력은 1단계에서 좌·우 LOCK.", remarks="reason_left는 판정하지 않음(이 경우의 이유 코드는 원문에 없음, 질의 Q-06).")

    # ---------------- SWR-021 sensor fault ----------------
    s = Seq()
    s.ev(10.00, None, exp=Xp(ll="RELEASE", lr="RELEASE", rc="NO_CHANGE"))
    s.ev(10.05, {"sensor_fault": True, "rear_left_approach_risk": True, "isofix_right": True, "vehicle_speed_kph": 3.0}, [("all", "lock", PB)],
         exp=Xp(ll="RELEASE", lr="RELEASE", st="FAULT", rc="SENSOR_FAULT", rl="SENSOR_FAULT", rr="SENSOR_FAULT", iv="VALID", w="W_SENSOR_FAULT"),
         note="sensor_fault true + 접근위험·ISOFIX·3.0 km/h·lock 동시")
    s.ev(10.10, {"rear_left_approach_risk": True, "isofix_right": True, "vehicle_speed_kph": 3.0},
         exp=Xp(ll="LOCK", lr="LOCK", st="NORMAL", rc="APPROACH_RISK", rl="APPROACH_RISK", rr="ISOFIX", w="NONE"), note="sensor_fault=false 평가부터 정상 판정(디바운스 없음)")
    tc("FTC-146", F, ["SWR-021"], "sensor fault 중 모든 새 규칙이 적용되지 않고 직전 출력이 유지되며 warning_code=W_SENSOR_FAULT, state=FAULT인지, false가 된 평가부터 즉시 정상 판정·warning_code=NONE인지 확인. 규칙 누수와 복귀 지연 결함 검출",
       s, [EP, ST], pre="직전 출력은 좌·우 모두 RELEASE.")

    s = Seq()
    s.ev(10.00, {"vehicle_speed_kph": 3.0}, exp=Xp(ll="LOCK", lr="LOCK", rc="AUTO_LOCK"), note="사전 설정: LOCK")
    s.ev(10.05, {"sensor_fault": True, "ignition_on": False, "fire_detected": True}, [("all", "unlock", PB)],
         exp=Xp(ll="LOCK", lr="LOCK", st="FAULT", rc="SENSOR_FAULT", rl="SENSOR_FAULT", rr="SENSOR_FAULT", w="W_SENSOR_FAULT"), note="sensor_fault + 시동 OFF + 화재 + unlock all")
    tc("FTC-147", F, ["SWR-021", "SWR-020", "SWR-017"], "직전 LOCK 상태에서 sensor fault 중 RELEASE를 만드는 규칙(시동 OFF, 화재, unlock)이 모두 무시되고 LOCK이 유지되는지 확인(FTC-146은 LOCK 방향, 이 케이스는 RELEASE 방향). 방향별 규칙 누수 결함 검출",
       s, [EP, WOW], pre="직전 출력은 1단계에서 좌·우 LOCK.")

    # ---------------- SWR-020 시동 OFF ----------------
    s = Seq()
    s.ev(10.00, {"vehicle_speed_kph": 3.0}, exp=Xp(ll="LOCK", lr="LOCK", rc="AUTO_LOCK"), note="사전 설정: LOCK")
    s.ev(10.05, {"ignition_on": False}, exp=Xp(ll="RELEASE", lr="RELEASE", st="OFF", rc="IGNITION_OFF", rl="IGNITION_OFF", rr="IGNITION_OFF", iv="VALID", w="NONE"), note="시동 OFF 첫 평가")
    s.ev(10.10, None, exp=Xp(ll="RELEASE", lr="RELEASE", st="NORMAL", rc="NO_CHANGE"), note="시동 ON 복귀(차속 0.0): RELEASE 유지")
    tc("FTC-148", F, ["SWR-020"], "ignition_on=false 첫 평가에 양쪽 RELEASE, reason=IGNITION_OFF, state=OFF가 되고 시동 ON 복귀 후 state=NORMAL로 돌아가는지 확인. state 미복귀 결함 검출",
       s, [EP, ST], pre="직전 출력은 1단계에서 좌·우 LOCK.")

    s = Seq()
    s.ev(10.00, {"rear_left_approach_risk": True}, [("right", "lock", PB)], exp=Xp(ll="LOCK", lr="LOCK", rc="APPROACH_RISK"), note="사전 설정: 좌 접근위험 LOCK, 우 driver lock")
    s.ev(10.05, {"rear_left_approach_risk": True, "ignition_on": False}, exp=Xp(ll="LOCK", lr="RELEASE", st="OFF", rc="APPROACH_RISK", rl="APPROACH_RISK", rr="IGNITION_OFF"),
         note="시동 OFF + 좌 접근위험")
    tc("FTC-149", F, ["SWR-020", "SWR-005"], "시동 OFF에서도 좌 접근위험 LOCK이 유지되고 우측만 RELEASE, state=OFF인지 확인(수용기준). 시동 OFF가 ASIL B 잠금을 해제하는 결함 검출",
       s, [WOW, EP], pre="직전 출력은 1단계에서 좌·우 LOCK.")

    s = Seq()
    s.ev(10.00, None, exp=Xp(ll="RELEASE", lr="RELEASE", rc="NO_CHANGE"))
    s.ev(10.05, {"ignition_on": False}, [("all", "lock", PB)], exp=Xp(ll="RELEASE", lr="RELEASE", st="OFF", rc="IGNITION_OFF"), note="시동 OFF 중 lock all")
    tc("FTC-150", F, ["SWR-020", "SWR-002"], "시동 OFF 중 운전자 lock이 RELEASE를 바꾸지 못하는지 확인(순위 6 > 10, LOCK 방향 규칙 누수). FTC-D-39(unlock)와 반대 방향 결함 검출",
       s, [EP], pre="직전 출력은 좌·우 모두 RELEASE.")

    # ---------------- SWR-017 해제 입력 후 복귀 ----------------
    s = Seq()
    s.ev(10.00, {"isofix_left": True, "fire_detected": True}, exp=Xp(ll="RELEASE", lr="RELEASE", st="NORMAL", rc="FIRE", rl="FIRE", rr="FIRE"), note="화재 true + ISOFIX 좌 true")
    s.ev(10.05, {"isofix_left": True}, exp=Xp(ll="LOCK", lr="RELEASE", st="NORMAL", rc="ISOFIX", rl="ISOFIX", rr="NO_CHANGE"), note="화재 false로 복귀한 평가: ISOFIX가 적용되어 LOCK")
    tc("FTC-151", F, ["SWR-017", "SWR-018"], "강제 해제 입력이 false로 돌아간 평가에서 ISOFIX가 즉시 LOCK을 만드는지(해제 래치 잔존 없음), 입력 중에는 ISOFIX가 무시되는지 확인(수용기준). 강제 해제 상태가 남는 결함 검출",
       s, [ST, EP], pre="직전 출력은 좌·우 모두 RELEASE.")

    # ---------------- SWR-018 ISOFIX ----------------
    s = Seq()
    s.ev(10.00, {"isofix_left": True}, exp=Xp(ll="LOCK", lr="RELEASE", st="NORMAL", rc="ISOFIX", rl="ISOFIX", rr="NO_CHANGE"), note="좌 ISOFIX true")
    s.ev(10.05, None, exp=Xp(ll="LOCK", lr="RELEASE", st="NORMAL", rc="NO_CHANGE"), note="ISOFIX false: LOCK 유지")
    s.ev(10.10, None, [("left", "unlock", PB)], exp=Xp(ll="RELEASE", lr="RELEASE", st="NORMAL", rc="DRIVER_COMMAND"), note="ISOFIX false 이후 unlock은 적용")
    tc("FTC-152", F, ["SWR-018"], "ISOFIX true 쪽만 LOCK이 되고 반대쪽은 직전 값이며, false가 되어도 LOCK이 유지되고 이후 unlock이 적용되는지 확인. false 시 자동 해제 또는 ISOFIX 억제 잔존 결함 검출",
       s, [EP, ST], pre="직전 출력은 좌·우 모두 RELEASE.")

    # ---------------- SWR-014 ----------------
    s = Seq()
    s.ev(10.00, {"rear_left_approach_risk": True, "gear": "X"}, exp=Xp(ll="LOCK", lr="RELEASE", st="DEGRADED", rc="APPROACH_RISK", rl="APPROACH_RISK", rr="INPUT_INVALID", iv="INVALID", w="NONE"),
         note="GET /status 응답에 아홉 필드(lock_left, lock_right, state, priority_reason, reason_code, input_validity, reason_left, reason_right, warning_code)가 모두 있고 값이 위와 같은지 확인")
    s.ev(10.05, {"sensor_fault": True}, exp=Xp(ll="LOCK", lr="RELEASE", st="FAULT", rc="SENSOR_FAULT", rl="SENSOR_FAULT", rr="SENSOR_FAULT", iv="VALID", w="W_SENSOR_FAULT"),
         note="아홉 필드가 모두 마지막 평가 결과로 갱신(이전 값 잔존 없음)")
    tc("FTC-153", F, ["SWR-014"], "상태 조회가 아홉 필드를 모두 제공하고 값이 마지막 평가 결과와 같은지 확인(필드 누락·이전 결과 캐시·reason_left/right 누락 결함 검출). 서로 다른 값을 가진 두 평가를 사용해 필드별 값을 구분",
       s, [EP, REQ], pre="직전 출력은 좌·우 모두 RELEASE.")

    # ---------------- SWR-015 HTTP ----------------
    s = Seq()
    s.ev(10.00, {"vehicle_speed_kph": 3.0}, exp="POST /input 응답 HTTP 200. " + Xp(ll="LOCK", lr="LOCK", rc="AUTO_LOCK"), note="정상 입력")
    s.act("GET /status 호출", exp="HTTP 200, 본문 JSON에 아홉 필드(lock_left, lock_right, state, priority_reason, reason_code, input_validity, reason_left, reason_right, warning_code) 포함, 값은 1단계 결과와 동일")
    s.ev(10.05, {"vehicle_speed_kph": 300.1}, exp="POST /input 응답 HTTP 200(422·400 아님). " + Xp(ll="LOCK", lr="LOCK", st="DEGRADED", rc="INPUT_INVALID", iv="INVALID"),
         note="범위 밖 값(300.1 km/h): 입력 계층에서 거절하지 않고 평가 경로로 전달")
    tc("FTC-154", F, ["SWR-015", "SWR-013"], "GET /status가 200과 SWR-014 JSON을 반환하고, 범위 밖 값은 HTTP 오류가 아니라 200 + DEGRADED/INVALID로 처리되는지 확인. 스키마 검증 프레임워크가 범위 오류를 422로 돌려보내는 결함 검출",
       s, [EP, BVA], pre="직전 출력은 좌·우 모두 RELEASE.", inputs="t=10.00: vehicle_speed_kph=3.0 km/h; t=10.05: vehicle_speed_kph=300.1 km/h")

    # ---------------- 이벤트 SWR-010/011 ----------------
    s = Seq()
    s.act("t=10.00, 10.05, ..., 10.45 s(0.05 s 간격 10회)에 S0(ts=t)를 제출하며 평가를 10회 실행(명령 없음). 이후 GET /events 조회",
          exp="GET /events 결과 1건: event_id=1, timestamp_s=10.00(첫 평가). 나머지 9회는 기록되지 않음",
          inp="t=10.00~10.45(10회): S0(기본값), commands=[]")
    s.ev(10.50, None, [("left", "lock", PB)], exp="GET /events: 2건, 마지막 event_id=2, timestamp_s=10.50, lock_left=LOCK(결과 변화)", note="운전자 명령 평가(결과 변화)")
    s.ev(10.55, None, [("left", "lock", PB)], exp="결과(lock_left=LOCK, reason_left=DRIVER_COMMAND 등 아홉 필드)가 직전과 같지만 운전자 명령 평가이므로 기록. GET /events: 3건, 마지막 event_id=3, timestamp_s=10.55",
         note="직전과 같은 명령 평가(결과 동일)")
    s.ev(10.60, None, exp="reason_left가 DRIVER_COMMAND→NO_CHANGE로 변해 기록. GET /events: 4건, 마지막 event_id=4, timestamp_s=10.60", note="명령 없음(결과 변화)")
    s.act("t=10.65, 10.70, ..., 11.10 s(10회)에 S0(ts=t)를 제출하며 평가 10회 실행 후 GET /events 조회",
          exp="이벤트는 여전히 4건(event_id 1,2,3,4 순서, 중간 누락·중복 없음)", inp="t=10.65~11.10(10회): S0(기본값), commands=[]")
    tc("FTC-155", F, ["SWR-010"], "동일 결과가 이어지는 평가는 1건만 기록되고(10회→1건), 운전자 명령 평가는 결과가 같아도 기록되며, event_id가 1,2,3,…으로 증가하는지 확인. 매 평가 기록·명령 평가 누락·ID 건너뜀 결함 검출",
       s, [EP, REQ], pre="이벤트 0건(초기 상태).")

    s = Seq()
    s.ev(10.00, None, exp="GET /events: 1건(event_id=1)")
    s.ev(10.05, nosnap=True, exp="결과 동일(VALID, 나이 0.05 s)이라 기록 없음. GET /events: 1건", note="스냅샷 없는 주기")
    s.ev(10.30, nosnap=True, exp="input_validity=STALE, state=DEGRADED로 변해 기록. GET /events: 2건, event_id=2, timestamp_s=10.30, input_validity=STALE", note="기준 스냅샷 나이 0.30 s")
    s.ev(10.35, nosnap=True, exp="결과 동일(STALE 지속)이라 기록 없음. GET /events: 2건", note="STALE 지속")
    s.ev(10.40, None, exp="VALID/NORMAL로 복귀하여 기록. GET /events: 3건, event_id=3, input_validity=VALID", note="정상 스냅샷 복귀")
    s.ev(10.45, {"vehicle_speed_kph": 3.0}, exp="lock_left/right=LOCK, reason_code=AUTO_LOCK로 변해 기록. GET /events: 4건, event_id=4", note="자동 잠금")
    s.ev(10.50, {"vehicle_speed_kph": 3.0, "rear_left_approach_risk": True},
         exp="lock_left/right는 LOCK 그대로지만 reason_left=APPROACH_RISK, reason_code=APPROACH_RISK로 변해 기록. GET /events: 5건, event_id=5", note="잠금 출력은 같고 이유만 변경")
    s.ev(10.55, {"vehicle_speed_kph": 3.0, "rear_left_approach_risk": True}, exp="결과 동일이라 기록 없음. GET /events: 5건(event_id 1~5)", note="동일 결과 반복")
    tc("FTC-156", F, ["SWR-010"], "잠금 출력이 같아도 공개 결과의 다른 필드(input_validity, state, reason_*)가 바뀌면 기록되고, 같은 결과는 기록되지 않는지 확인. 'lock 출력 변화만 기록' 결함 검출",
       s, [EP, WOW], pre="이벤트 0건(초기 상태).")

    s = Seq()
    s.ev(10.00, {"vehicle_speed_kph": 123.4, "gear": "Z9", "rear_left_approach_risk": True}, [("left", "lock", "voice")],
         exp="GET /events: 1건. 모든 이벤트 키 집합이 정확히 {event_id, timestamp_s, lock_left, lock_right, state, priority_reason, reason_code, reason_left, reason_right, input_validity, warning_code}(11개). "
             + Xp(ll="LOCK", lr="RELEASE", st="DEGRADED", rc="APPROACH_RISK", rl="APPROACH_RISK", rr="INPUT_INVALID", iv="INVALID") + ", timestamp_s=10.00",
         note="QM 오류값(gear=\"Z9\")과 명령(source=voice)을 포함한 첫 평가")
    s.ev(10.05, nosnap=True, exp="(이벤트 추가 없음 또는 추가되더라도) 모든 이벤트의 키 집합은 위 11개로 동일")
    s.act("GET /events 응답 본문 전체를 문자열로 검색",
          exp="문자열 \"Z9\", \"123.4\", \"voice\", \"source_timestamp_s\", \"vehicle_speed_kph\", \"gear\", \"side\", \"action\" 어느 것도 포함되지 않음(원시 입력값·명령 미저장)")
    tc("FTC-157", F, ["SWR-011"], "이벤트가 11개 키만 가지며 원시 입력값(차속, gear 오류값, 명령 source/side/action, 입력 타임스탬프)을 저장하지 않는지 확인. 디버깅용 원시 입력 필드가 이벤트에 섞이는 결함 검출",
       s, [EP, REQ], pre="이벤트 0건(초기 상태).")

    # ---------------- SWR-022 기능 부분 ----------------
    s = Seq()
    s.ev(10.00, {"vehicle_speed_kph": 3.0}, exp=Xp(ll="LOCK", lr="LOCK", rc="AUTO_LOCK"), note="기준 스냅샷: 3.0 km/h")
    s.ev(10.05, nosnap=True, cmds=[("left", "unlock", PB)], exp=Xp(ll="LOCK", lr="LOCK", st="NORMAL", rc="AUTO_LOCK", rl="AUTO_LOCK", rr="AUTO_LOCK", iv="VALID"),
         note="스냅샷 없는 주기에 unlock만 제출")
    tc("FTC-158", F, ["SWR-022", "SWR-004"], "스냅샷이 없는 주기에도 평가가 수행되고 기준 스냅샷(3.0 km/h) 값으로 판정되는지 확인(unlock이 자동 잠금에 막힘). 무스냅샷 주기를 건너뛰거나 차속 0 기본값을 쓰는 결함 검출",
       s, [EP, REQ], pre="직전 출력은 1단계에서 좌·우 LOCK.")

    s = Seq()
    s.ev(10.00, None, exp=Xp(ll="RELEASE", lr="RELEASE", rc="NO_CHANGE"), note="정상 평가(직전 정상 평가 시각 = 10.00 s)")
    s.ev(9.95, dict(CF), exp=Xp(ll="RELEASE", lr="RELEASE", st="DEGRADED", rc="INPUT_INVALID", iv="INVALID"), note="평가 시각 9.95 s(직전보다 작음) + CONFIRMED")
    s.ev(10.00, dict(CF), ts=10.00, exp=Xp(ll="RELEASE", lr="RELEASE", st="DEGRADED", rc="INPUT_INVALID", iv="INVALID"), note="평가 시각 10.00 s(직전과 같음) + CONFIRMED")
    s.ev(10.05, {"vehicle_speed_kph": 3.0}, exp=Xp(ll="LOCK", lr="LOCK", st="NORMAL", rc="AUTO_LOCK", iv="VALID"), note="평가 시각 10.05 s(직전 정상보다 큼): 정상 복귀, 래치 없음")
    tc("FTC-159", F, ["SWR-022", "SWR-007"], "직전 정상 평가 시각과 같거나 이전인 평가 시각(9.95, 10.00 s)은 INPUT_INVALID이고 그 평가의 CONFIRMED로 래치가 서지 않으며, 10.05 s에서 정상 복귀하는지 확인(3-값 경계). 시각 비교 연산자(>=)·래치 선갱신 결함 검출",
       s, [BVA, EP, WOW], pre="직전 출력은 좌·우 모두 RELEASE.")

    s = Seq()
    s.ev(1000.00, {"vehicle_speed_kph": 3.0}, exp=Xp(ll="LOCK", lr="LOCK", st="NORMAL", rc="AUTO_LOCK", iv="VALID"), note="초기 상태에서 평가 시각이 0 근처가 아닌 1000.00 s로 크게 건너뜀(첫 평가)")
    s.ev(2000.00, {"vehicle_speed_kph": 0.0}, [("all", "unlock", PB)], exp=Xp(ll="RELEASE", lr="RELEASE", st="NORMAL", rc="DRIVER_COMMAND", iv="VALID"), note="앞으로 1000 s 건너뜀 + 새 스냅샷(ts=2000.00, 지연 없음)")
    s.ev(3000.00, nosnap=True, exp=Xp(ll="RELEASE", lr="RELEASE", st="DEGRADED", rc="INPUT_STALE", iv="STALE"), note="1000 s 건너뜀 + 스냅샷 없음: 입력 지연(STALE)")
    tc("FTC-160", F, ["SWR-022", "SWR-013"], "평가 시각이 앞으로 크게 건너뛰어도 오류가 아니며(새 스냅샷이 있으면 VALID), 스냅샷이 없으면 입력 지연(STALE)으로 판정되는지 확인. 큰 시각 점프를 오류로 처리하는 결함과 지연 판정 누락 결함 검출",
       s, [EP, WOW], pre="이전 평가 이력 없음.")

    s = Seq()
    s.ev(10.00, {"vehicle_speed_kph": 3.0}, exp=Xp(ll="LOCK", lr="LOCK", rc="AUTO_LOCK"), note="사전 설정: LOCK")
    s.ev(10.05, snaps=[(dict(CF), None), ({"crash_status": "NONE", "vehicle_speed_kph": 3.0}, None)],
         exp=Xp(ll="RELEASE", lr="RELEASE", st="NORMAL", rc="CRASH_CONFIRMED", iv="VALID"), note="한 주기에 CONFIRMED 뒤 NONE")
    tc("FTC-161", F, ["SWR-022", "SWR-007"], "한 주기에 CONFIRMED 스냅샷 뒤 NONE 스냅샷이 와도 CONFIRMED를 우선해 래치가 서는지 확인(수용기준). 마지막 스냅샷만 쓰는 결함 검출",
       s, [WOW, EP], pre="직전 출력은 1단계에서 좌·우 LOCK.")

    s = Seq()
    s.ev(10.00, None, exp=Xp(ll="RELEASE", lr="RELEASE", rc="NO_CHANGE"))
    s.ev(10.05, snaps=[({"vehicle_speed_kph": 3.0}, None), ({"vehicle_speed_kph": 0.0}, None)], exp=Xp(ll="RELEASE", lr="RELEASE", st="NORMAL", rc="NO_CHANGE"),
         note="CONFIRMED 없는 주기: 마지막 스냅샷(0.0 km/h)만 사용")
    s.ev(10.10, snaps=[({"vehicle_speed_kph": 0.0}, None), ({"vehicle_speed_kph": 3.0}, None)], exp=Xp(ll="LOCK", lr="LOCK", st="NORMAL", rc="AUTO_LOCK"),
         note="순서를 바꿔: 마지막 스냅샷(3.0 km/h) 사용")
    tc("FTC-162", F, ["SWR-022"], "CONFIRMED가 없는 주기에 여러 스냅샷이 오면 마지막 것만 쓰고 나머지는 버리는지 확인(순서를 바꿔 양방향). 첫 스냅샷 사용·평균/OR 병합 결함 검출",
       s, [EP, WOW], pre="직전 출력은 좌·우 모두 RELEASE.")

    s = Seq()
    s.ev(10.00, {"vehicle_speed_kph": 3.0}, exp=Xp(ll="LOCK", lr="LOCK", rc="AUTO_LOCK"), note="사전 설정: LOCK(기준 스냅샷 ts=10.00)")
    s.ev(11.05, snaps=[(dict(CF), 10.00), (dict(CF), 11.05)], exp=Xp(ll="RELEASE", lr="RELEASE", st="NORMAL", rc="CRASH_CONFIRMED", iv="VALID"),
         note="한 주기에 CONFIRMED 2개: 첫 번째는 나이 1.05 s(래치 불가), 마지막은 나이 0 s")
    tc("FTC-163", F, ["SWR-022", "SWR-007"], "CONFIRMED가 여러 개이면 마지막 CONFIRMED를 써서(나이 0 s) 래치가 서는지 확인. 첫 CONFIRMED를 쓰는 결함(나이 1.05 s로 래치 실패) 검출",
       s, [WOW, EP], pre="직전 출력은 1단계에서 좌·우 LOCK.")

    s = Seq()
    s.ev(10.00, dict(PD), exp=Xp(ll="RELEASE", lr="RELEASE", rc="NO_CHANGE"), note="PENDING 시작 10.00 s")
    s.ev(9.00, {"crash_status": "NONE"}, exp=Xp(ll="RELEASE", lr="RELEASE", st="DEGRADED", rc="INPUT_INVALID", iv="INVALID"), note="시각 역행(9.00 s) + NONE: 타이머를 지우면 안 됨")
    s.ev(12.05, dict(PD, vehicle_speed_kph=3.0), exp=Xp(ll="LOCK", lr="LOCK", st="NORMAL", rc="AUTO_LOCK", iv="VALID"), note="최초 PENDING(10.00)으로부터 2.05 s: 막지 않음")
    tc("FTC-164", F, ["SWR-022", "SWR-008"], "시각 오류 평가가 PENDING 타이머를 갱신(NONE으로 삭제)하지 않는지 확인. 오류 평가에서도 타이머를 갱신하는 결함 검출",
       s, [WOW, ST], pre="직전 출력은 좌·우 모두 RELEASE.")

    s = Seq()
    s.ev(10.05, RL, exp=Xp(ll="LOCK", rc="APPROACH_RISK"), note="사전 설정(직전 정상 평가 시각 10.05 s)")
    s.ev(10.00, RL, [("left", "unlock", PB)], ts=10.05, exp=Xp(ll="LOCK", lr="RELEASE", st="DEGRADED", rc="INPUT_INVALID", iv="INVALID"), note="시각 역행 평가의 unlock: 첫 억제로 기록되면 안 됨")
    s.ev(10.10, RL, [("left", "unlock", PB)], exp=Xp(ll="LOCK", lr="RELEASE", st="NORMAL", rc="APPROACH_RISK", rl="APPROACH_RISK", iv="VALID"), note="정상 평가 첫 unlock: 첫 억제(override 아님)")
    s.ev(10.15, RL, [("left", "unlock", PB)], exp=Xp(ll="RELEASE", st="OVERRIDE", rc="DRIVER_OVERRIDE", rl="DRIVER_OVERRIDE"), note="다음 unlock: override")
    tc("FTC-165", F, ["SWR-022", "SWR-006"], "시각 오류 평가가 첫 억제·override 이력을 갱신하지 않는지 확인(그 평가의 unlock이 기록되었다면 3단계가 override가 됨). 오류 평가의 override 이력 갱신 결함 검출",
       s, [WOW, ST], pre="직전 출력은 좌·우 모두 RELEASE.")

    s = Seq()
    s.ev(10.00, None, [("all", "lock", PB)], exp=Xp(ll="LOCK", lr="LOCK", rc="DRIVER_COMMAND"), note="사전 설정: 기준 스냅샷 S0(차속 0.0), 양쪽 LOCK")
    s.ev(9.95, {"vehicle_speed_kph": 3.0}, ts=10.00, exp=Xp(ll="LOCK", lr="LOCK", st="DEGRADED", rc="INPUT_INVALID", iv="INVALID"), note="시각 역행 평가에 차속 3.0 km/h 스냅샷: 기준 스냅샷이 되면 안 됨")
    s.ev(10.05, nosnap=True, cmds=[("left", "unlock", PB)], exp=Xp(ll="RELEASE", lr="LOCK", st="NORMAL", rc="DRIVER_COMMAND", iv="VALID"),
         note="스냅샷 없는 주기: 기준 스냅샷은 1단계(0.0 km/h)이므로 unlock 적용")
    tc("FTC-166", F, ["SWR-022", "SWR-013"], "시각 오류 평가의 스냅샷이 기준 스냅샷을 갱신하지 않는지 확인(갱신되었다면 3.0 km/h로 unlock이 막힘). 오류 평가의 기준 스냅샷 갱신 결함 검출",
       s, [WOW, ST], pre="직전 출력은 1단계에서 좌·우 LOCK.")

    s = Seq()
    s.ev(10.00, dict(CF, vehicle_speed_kph=3.0), exp=Xp(ll="RELEASE", lr="RELEASE", st="NORMAL", rc="CRASH_CONFIRMED"), note="래치 성립")
    s.ev(10.00, {"ignition_on": False}, exp=Xp(ll="RELEASE", lr="RELEASE", st="DEGRADED", rc="CRASH_CONFIRMED", iv="INVALID"),
         note="평가 시각 10.00 s(직전과 같음): 해제 조건(시동 OFF, NONE)의 스냅샷이지만 시각 오류 평가")
    s.ev(10.05, {"vehicle_speed_kph": 3.0}, exp=Xp(ll="RELEASE", lr="RELEASE", st="NORMAL", rc="CRASH_CONFIRMED", iv="VALID"), note="정상 평가: 래치가 풀렸다면 자동 잠금이 됨")
    tc("FTC-167", F, ["SWR-022", "SWR-007"], "시각 오류 평가에서는 기존 래치를 유지하고 해제 스냅샷을 무시하는지 확인(수용기준 '기존 래치는 유지'). 시각 검사 전에 래치 해제를 처리하는 결함 검출",
       s, [WOW, ST], pre="직전 출력은 좌·우 모두 RELEASE(초기 상태).")

    s = Seq()
    s.ev(10.00, None, exp=Xp(ll="RELEASE", lr="RELEASE", rc="NO_CHANGE"), note="직전 정상 평가 시각 10.00 s")
    s.ev(10.05, None, exp=Xp(ll="RELEASE", lr="RELEASE", rc="NO_CHANGE"), note="직전 정상 평가 시각 10.05 s")
    s.ev(10.02, None, ts=10.05, exp=Xp(ll="RELEASE", lr="RELEASE", st="DEGRADED", rc="INPUT_INVALID", iv="INVALID"), note="평가 시각 10.02 s(< 10.05): 시각 오류")
    s.ev(10.03, None, ts=10.05, exp=Xp(ll="RELEASE", lr="RELEASE", st="DEGRADED", rc="INPUT_INVALID", iv="INVALID"), note="평가 시각 10.03 s: 직전 정상(10.05)보다 작으므로 여전히 오류(10.02보다는 큼)")
    s.ev(10.10, None, exp=Xp(ll="RELEASE", lr="RELEASE", st="NORMAL", rc="NO_CHANGE", iv="VALID"), note="평가 시각 10.10 s: 정상 복귀")
    tc("FTC-168", F, ["SWR-022"], "직전 정상 평가 시각이 정상 평가에서만 갱신되는지 확인(오류 평가 10.02 s 뒤 10.03 s도 오류여야 함). 오류 평가에서 기준 시각을 갱신하는 결함 검출",
       s, [BVA, WOW], pre="직전 출력은 좌·우 모두 RELEASE.", remarks="오류 평가 단계의 스냅샷 ts는 10.05(기준 스냅샷과 같음)로 두어 타임스탬프 역행 오류와 겹치지 않게 함.")
