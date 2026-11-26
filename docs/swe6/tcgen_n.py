# -*- coding: utf-8 -*-
"""수작업 설계 비기능 케이스(입력 유효성·타이밍·견고성·결정론·보존 용량)."""
from tcgen_lib import *

PB = "physical_button"
EP, BVA, WOW, ST, REQ, FI, EG = "동치 클래스", "경계값 분석", "WoW 검증", "상태 전이", "요구사항 기반 테스트", "결함 주입", "오류 추측"
N = "비기능"
HTTP200 = "POST /input 응답 HTTP 200. "


def inv(s, t, chg, exp_note="", prior_lock=False, **extra):
    pass


def build():
    # ---------- SWR-013 신호 유효성: 범위 ----------
    s = Seq()
    s.ev(10.00, None, exp=Xp(ll="RELEASE", lr="RELEASE", st="NORMAL", rc="NO_CHANGE", iv="VALID"), note="vehicle_speed_kph=0.0(하한 경계)도 유효")
    s.ev(10.05, {"vehicle_speed_kph": 300.0}, exp=HTTP200 + Xp(ll="LOCK", lr="LOCK", st="NORMAL", rc="AUTO_LOCK", iv="VALID", w="NONE"), note="상한 경계 300.0 km/h")
    tc("NTC-201", N, ["SWR-013", "SWR-003"], "차속 범위 경계 내부(0.0, 300.0 km/h)가 유효로 처리되고 300.0 km/h에서 자동 잠금이 되는지 확인. 범위 경계를 포함하지 않는(< 300.0) 결함 검출",
       s, [BVA, EP], pre="직전 출력은 좌·우 모두 RELEASE.")

    s = Seq()
    s.ev(10.00, None, exp=Xp(ll="RELEASE", lr="RELEASE", rc="NO_CHANGE"), note="사전 설정")
    s.ev(10.05, {"vehicle_speed_kph": 300.1}, exp=HTTP200 + Xp(ll="RELEASE", lr="RELEASE", st="DEGRADED", rc="INPUT_INVALID", rl="INPUT_INVALID", rr="INPUT_INVALID", iv="INVALID"),
         note="상한 초과 300.1 km/h(분해능 0.1 가정 +1)")
    s.ev(10.10, {"vehicle_speed_kph": 3.0}, exp=Xp(ll="LOCK", lr="LOCK", st="NORMAL", rc="AUTO_LOCK", iv="VALID"), note="다음 유효·최신 스냅샷: 지연 없이 정상 판정 복귀")
    tc("NTC-202", N, ["SWR-013"], "300.1 km/h는 INVALID(직전 유지, DEGRADED)이고 다음 유효 스냅샷에서 디바운스 없이 즉시 정상 복귀하는지 확인(수용기준·④). 상한 미검사와 복귀 지연 결함 검출",
       s, [BVA, EP, FI], pre="직전 출력은 좌·우 모두 RELEASE.")

    s = Seq()
    s.ev(10.00, {"vehicle_speed_kph": 3.0}, exp=Xp(ll="LOCK", lr="LOCK", rc="AUTO_LOCK"), note="사전 설정: LOCK")
    s.ev(10.05, {"vehicle_speed_kph": -0.1}, exp=HTTP200 + Xp(ll="LOCK", lr="LOCK", st="DEGRADED", rc="INPUT_INVALID", iv="INVALID"), note="하한 미만 −0.1 km/h")
    tc("NTC-203", N, ["SWR-013"], "차속 −0.1 km/h(하한 0.0 바로 아래)가 INVALID로 처리되는지 확인. 하한 미검사 결함 검출",
       s, [BVA, EP, FI], pre="직전 출력은 1단계에서 좌·우 LOCK.")

    s = Seq()
    s.ev(10.00, None, exp=Xp(ll="RELEASE", lr="RELEASE", rc="NO_CHANGE"), note="사전 설정")
    s.ev(10.05, {"vehicle_speed_kph": "3.0"}, exp=HTTP200 + Xp(ll="RELEASE", lr="RELEASE", st="DEGRADED", rc="INPUT_INVALID", iv="INVALID"),
         note="숫자처럼 보이는 문자열 \"3.0\"")
    tc("NTC-204", N, ["SWR-013", "SWR-015"], "숫자 자리에 문자열 \"3.0\"이 오면 형식 오류(INVALID)이며 자동 변환으로 3.0 km/h(LOCK)가 되지 않는지 확인. 암묵적 형변환 결함 검출",
       s, [EP, FI], pre="직전 출력은 좌·우 모두 RELEASE.")

    s = Seq()
    s.ev(10.00, {"vehicle_speed_kph": 3.0}, exp=Xp(ll="LOCK", lr="LOCK", rc="AUTO_LOCK"), note="사전 설정: LOCK")
    s.ev(10.05, {"crash_status": "UNKNOWN"}, exp=HTTP200 + Xp(ll="LOCK", lr="LOCK", st="DEGRADED", rc="INPUT_INVALID", iv="INVALID"), note="미등록 enum \"UNKNOWN\"")
    tc("NTC-205", N, ["SWR-013"], "crash_status=\"UNKNOWN\"(미등록 enum)이 INVALID/DEGRADED로 처리되는지 확인. 미등록 값을 NONE으로 간주하는 결함 검출",
       s, [EP, FI], pre="직전 출력은 1단계에서 좌·우 LOCK.")

    s = Seq()
    s.ev(10.00, {"vehicle_speed_kph": 3.0}, exp=Xp(ll="LOCK", lr="LOCK", rc="AUTO_LOCK"), note="사전 설정: LOCK")
    s.ev(10.05, {"ignition_on": 0}, exp=HTTP200 + Xp(ll="LOCK", lr="LOCK", st="DEGRADED", rc="INPUT_INVALID", iv="INVALID"), note="ASIL B 불리언 자리에 0(시동 OFF로 오인하면 RELEASE가 됨)")
    tc("NTC-206", N, ["SWR-013", "SWR-020"], "불리언 자리의 0은 형식 오류이며 false로 해석되어 시동 OFF(RELEASE)가 되지 않는지 확인. 0/1 암묵 변환 결함 검출",
       s, [EP, FI], pre="직전 출력은 1단계에서 좌·우 LOCK.")

    s = Seq()
    s.ev(10.00, None, exp=Xp(ll="RELEASE", lr="RELEASE", rc="NO_CHANGE"), note="사전 설정")
    s.ev(10.05, {"rear_left_approach_risk": 1}, exp=HTTP200 + Xp(ll="RELEASE", lr="RELEASE", st="DEGRADED", rc="INPUT_INVALID", iv="INVALID"), note="접근위험 자리에 1(true로 오인하면 LOCK이 됨)")
    tc("NTC-207", N, ["SWR-013", "SWR-005"], "접근위험 불리언 자리의 1이 형식 오류로 처리되어 LOCK(APPROACH_RISK)이 만들어지지 않는지 확인(수용기준 '불리언 자리의 1'). 0/1을 true/false로 받아들이는 결함 검출",
       s, [EP, FI], pre="직전 출력은 좌·우 모두 RELEASE.")

    s = Seq()
    s.ev(10.00, None, exp=Xp(ll="RELEASE", lr="RELEASE", rc="NO_CHANGE"), note="사전 설정")
    s.ev(10.05, {"vehicle_speed_kph": 3.0, "crash_status": MISSING}, exp=HTTP200 + Xp(ll="RELEASE", lr="RELEASE", st="DEGRADED", rc="INPUT_INVALID", iv="INVALID"),
         note="ASIL B 필드(crash_status) 누락 + 3.0 km/h")
    tc("NTC-208", N, ["SWR-013"], "ASIL B 필드(crash_status) 누락이 INVALID(직전 유지)로 처리되고 기본값(NONE) 대체로 자동 잠금되지 않는지 확인. 누락 필드 기본값 대체 결함 검출",
       s, [EP, FI], pre="직전 출력은 좌·우 모두 RELEASE.")

    s = Seq()
    s.ev(10.00, None, exp=Xp(ll="RELEASE", lr="RELEASE", rc="NO_CHANGE"), note="사전 설정")
    s.ev(10.05, {"vehicle_speed_kph": 3.0, "fire_detected": MISSING}, exp=HTTP200 + Xp(ll="RELEASE", lr="RELEASE", st="DEGRADED", rc="INPUT_INVALID", rl="INPUT_INVALID", rr="INPUT_INVALID", iv="INVALID"),
         note="QM 필드(fire_detected) 누락 + 3.0 km/h")
    tc("NTC-209", N, ["SWR-013"], "QM 필드 누락이 순위 5(INPUT_INVALID, 직전 유지)로 처리되어 자동 잠금이 막히는지 확인. QM 누락을 false 기본값으로 처리하는 결함 검출",
       s, [EP, FI], pre="직전 출력은 좌·우 모두 RELEASE.")

    s = Seq()
    s.ev(10.00, None, exp=Xp(ll="RELEASE", lr="RELEASE", rc="NO_CHANGE"), note="사전 설정")
    s.ev(10.05, {"vehicle_speed_kph": 3.0, "source_timestamp_s": MISSING}, exp=HTTP200 + Xp(ll="RELEASE", lr="RELEASE", st="DEGRADED", rc="INPUT_INVALID", iv="INVALID"),
         note="source_timestamp_s 누락 + 3.0 km/h")
    tc("NTC-210", N, ["SWR-013"], "source_timestamp_s 누락이 INVALID로 처리되는지 확인(타임스탬프도 ASIL B 신호). 누락 시 평가 시각으로 대체하는 결함 검출",
       s, [EP, FI], pre="직전 출력은 좌·우 모두 RELEASE.")

    s = Seq()
    s.ev(10.00, None, exp=Xp(ll="RELEASE", lr="RELEASE", rc="NO_CHANGE"), note="사전 설정")
    s.ev(10.05, {"isofix_left": "true"}, exp=HTTP200 + Xp(ll="RELEASE", lr="RELEASE", st="DEGRADED", rc="INPUT_INVALID", iv="INVALID"), note="QM 불리언 자리에 문자열 \"true\"")
    tc("NTC-211", N, ["SWR-013", "SWR-018"], "QM 불리언 자리의 문자열 \"true\"가 형식 오류(INVALID, 직전 유지)이며 true로 해석되어 ISOFIX LOCK이 되지 않는지 확인. 문자열 불리언 허용 결함 검출",
       s, [EP, FI], pre="직전 출력은 좌·우 모두 RELEASE.")

    s = Seq()
    s.ev(10.00, None, [("all", "lock", PB)], exp=Xp(ll="LOCK", lr="LOCK", rc="DRIVER_COMMAND"), note="사전 설정: LOCK")
    s.ev(10.05, None, [("all", "lock", PB)], raw="{}", exp=HTTP200 + Xp(ll="LOCK", lr="LOCK", st="DEGRADED", rc="INPUT_INVALID", iv="INVALID"), note="빈 스냅샷 {}(전 필드 누락)")
    tc("NTC-212", N, ["SWR-013", "SWR-015"], "빈 스냅샷 {}이 HTTP 오류 없이 INVALID/DEGRADED로 처리되는지 확인. 전 필드 누락 시 예외·500·정상 판정 결함 검출",
       s, [EP, FI], pre="직전 출력은 1단계에서 좌·우 LOCK.")

    # ---------- 타임스탬프 ----------
    s = Seq()
    s.ev(9.95, None, exp=Xp(ll="RELEASE", lr="RELEASE", rc="NO_CHANGE"), note="사전 설정")
    s.ev(10.00, {"vehicle_speed_kph": 3.0}, ts=10.05, exp=Xp(ll="LOCK", lr="LOCK", st="NORMAL", rc="AUTO_LOCK", iv="VALID"), note="ts가 평가 시각보다 0.050 s 미래: 정상")
    tc("NTC-213", N, ["SWR-013"], "미래 0.050 s 타임스탬프가 정상으로 처리되는지 확인(허용 경계, ≤). 10.05−10.00=0.0500000000000007로 계산되는 부동소수 오차로 정상 입력을 오류 처리하는 결함 검출",
       s, [BVA, EG], pre="직전 출력은 좌·우 모두 RELEASE.")

    s = Seq()
    s.ev(9.95, None, exp=Xp(ll="RELEASE", lr="RELEASE", rc="NO_CHANGE"), note="사전 설정")
    s.ev(10.00, {"vehicle_speed_kph": 3.0}, ts=10.051, exp=HTTP200 + Xp(ll="RELEASE", lr="RELEASE", st="DEGRADED", rc="INPUT_INVALID", iv="INVALID"), note="ts가 0.051 s 미래: 형식 오류")
    tc("NTC-214", N, ["SWR-013"], "미래 0.051 s 타임스탬프가 INVALID로 처리되는지 확인(허용 경계 +1 단위). 허용 오차를 넘는 미래 값을 받아들이는 결함 검출",
       s, [BVA, EP, FI], pre="직전 출력은 좌·우 모두 RELEASE.")

    s = Seq()
    s.ev(10.00, None, [("all", "lock", PB)], exp=Xp(ll="LOCK", lr="LOCK", rc="DRIVER_COMMAND"), note="사전 설정: 기준 스냅샷 ts=10.00, LOCK")
    s.ev(10.05, None, [("left", "unlock", PB)], ts=10.00, exp=Xp(ll="RELEASE", lr="LOCK", st="NORMAL", rc="DRIVER_COMMAND", iv="VALID"), note="ts=10.00: 기준 스냅샷과 같음(역행 아님)")
    s.ev(10.10, None, [("right", "unlock", PB)], ts=9.999, exp=Xp(ll="RELEASE", lr="LOCK", st="DEGRADED", rc="INPUT_INVALID", iv="INVALID"), note="ts=9.999: 기준 스냅샷(10.00)보다 작음(역행) → unlock 폐기")
    tc("NTC-215", N, ["SWR-013"], "ts가 기준 스냅샷과 같으면 정상(unlock 적용), 0.001 s라도 작으면 형식 오류(INVALID, 명령 폐기)인지 확인. 역행 검사의 <= vs < 오류 검출",
       s, [BVA, EP], pre="직전 출력은 1단계에서 좌·우 LOCK.")

    s = Seq()
    s.ev(0.00, None, exp=Xp(ll="RELEASE", lr="RELEASE", st="NORMAL", rc="NO_CHANGE", iv="VALID"), note="평가 시각 0.00 s, ts=0.00(0.0 이상의 하한): 유효")
    s.ev(0.05, {"vehicle_speed_kph": 3.0}, ts=-0.05, exp=HTTP200 + Xp(ll="RELEASE", lr="RELEASE", st="DEGRADED", rc="INPUT_INVALID", iv="INVALID"), note="ts=−0.05(0.0 미만)")
    tc("NTC-216", N, ["SWR-013"], "ts=0.0(하한 경계)은 유효, 음수 ts는 INVALID인지 확인. 하한 경계 처리 결함 검출(음수 값은 역행과 겹쳐 단독 격리 불가, 질의 Q-17)",
       s, [BVA, EP], pre="직전 출력은 좌·우 모두 RELEASE. 이 케이스는 평가 시각 0.00 s에서 시작한다.")

    # ---------- 입력 지연(0.200 s) ----------
    s = Seq()
    s.ev(10.10, None, [("all", "lock", PB)], exp=Xp(ll="LOCK", lr="LOCK", rc="DRIVER_COMMAND"), note="사전 설정: 기준 스냅샷 ts=10.10, LOCK")
    s.ev(10.25, nosnap=True, cmds=[("left", "unlock", PB)], exp=Xp(ll="RELEASE", lr="LOCK", st="NORMAL", rc="DRIVER_COMMAND", iv="VALID"), note="마지막 갱신 후 0.150 s: 정상")
    s.ev(10.30, nosnap=True, cmds=[("right", "unlock", PB)], exp=Xp(ll="RELEASE", lr="RELEASE", st="NORMAL", rc="DRIVER_COMMAND", iv="VALID"),
         note="마지막 갱신 후 0.200 s(10.30−10.10): 정상(0.200 s 이하)")
    s.ev(10.35, nosnap=True, cmds=[("left", "lock", PB)], exp=Xp(ll="RELEASE", lr="RELEASE", st="DEGRADED", rc="INPUT_STALE", rl="INPUT_STALE", rr="INPUT_STALE", iv="STALE"),
         note="마지막 갱신 후 0.250 s: 0.200 s 초과 첫 평가 → STALE, lock 명령 폐기. 0.300 s 이내(0.250 s)")
    tc("NTC-217", N, ["SWR-013", "SWR-022"], "스냅샷 없는 주기에서 0.150/0.200 s는 정상, 0.200 s를 처음 넘기는 평가(0.250 s)에서 DEGRADED/STALE이며 그 시점이 마지막 갱신 후 0.300 s 이내인지 확인. 지연 임계 연산자 오류, 부동소수 오차(10.30−10.10=0.2000000000000011), 판정 지연 결함 검출",
       s, [BVA, EP, EG], pre="직전 출력은 1단계에서 좌·우 LOCK.", remarks="합격 시점: 0.200 s 초과 첫 평가는 평가 시각−마지막 갱신 ≤ 0.300 s(OEM: 200 ms 초과 후 100 ms 이내, 50 ms 주기이므로 0.250 s에서 판정).")

    s = Seq()
    s.ev(10.00, None, [("all", "lock", PB)], nosnap=True, exp=Xp(ll="RELEASE", lr="RELEASE", st="DEGRADED", rc="INPUT_STALE", rl="INPUT_STALE", rr="INPUT_STALE", iv="STALE", w="NONE"),
         note="시작 직후 첫 평가, 스냅샷 없음 + lock all")
    s.ev(10.05, None, exp=Xp(ll="RELEASE", lr="RELEASE", st="NORMAL", rc="NO_CHANGE", iv="VALID"), note="첫 유효 스냅샷 수신: 즉시 정상")
    tc("NTC-218", N, ["SWR-013", "SWR-022"], "첫 기준 스냅샷 전 평가가 STALE이고 출력은 초기 RELEASE 유지(명령 폐기)이며 첫 유효 스냅샷에서 즉시 정상이 되는지 확인(A-15). 초기화 직후 평가를 정상 판정하는 결함 검출",
       s, [WOW, EP], pre="신규 기동 직후. 이전 스냅샷 없음.")

    s = Seq()
    s.ev(10.00, None, [("all", "lock", PB)], exp=Xp(ll="LOCK", lr="LOCK", rc="DRIVER_COMMAND"), note="사전 설정: LOCK")
    s.ev(10.05, {"gear": "X"}, exp=Xp(ll="LOCK", lr="LOCK", st="DEGRADED", rc="INPUT_INVALID", iv="INVALID"), note="QM 오류(gear) 스냅샷 수신")
    s.ev(10.10, nosnap=True, cmds=[("left", "unlock", PB)], exp=Xp(ll="LOCK", lr="LOCK", st="DEGRADED", rc="INPUT_INVALID", iv="INVALID"),
         note="스냅샷 없음: QM 오류는 다음 기준 스냅샷까지 순위 5로 유지(unlock 폐기)")
    s.ev(10.15, None, [("left", "unlock", PB)], exp=Xp(ll="RELEASE", lr="LOCK", st="NORMAL", rc="DRIVER_COMMAND", iv="VALID"), note="정상 스냅샷: 오류 해소, unlock 적용")
    tc("NTC-219", N, ["SWR-013"], "QM 오류 스냅샷이 기준 스냅샷이 되어 스냅샷 없는 주기에도 순위 5(INVALID, 직전 유지)가 이어지고 다음 정상 스냅샷에서 해소되는지 확인(③). 무스냅샷 주기에 오류를 지우는 결함 검출",
       s, [ST, WOW], pre="직전 출력은 1단계에서 좌·우 LOCK.")

    s = Seq()
    s.ev(10.00, None, [("all", "lock", PB)], exp=Xp(ll="LOCK", lr="LOCK", rc="DRIVER_COMMAND"), note="사전 설정: 기준 스냅샷 ts=10.00, LOCK")
    s.ev(10.10, {"rear_right_approach_risk": 1}, exp=Xp(ll="LOCK", lr="LOCK", st="DEGRADED", rc="INPUT_INVALID", iv="INVALID"), note="ASIL B 오류 스냅샷(기준 스냅샷이 되면 안 됨)")
    s.ev(10.25, nosnap=True, cmds=[("left", "unlock", PB)], exp=Xp(ll="LOCK", lr="LOCK", st="DEGRADED", rc="INPUT_STALE", iv="STALE"),
         note="기준 스냅샷(10.00)으로부터 0.250 s: STALE(오류 스냅샷이 기준이면 0.150 s로 VALID가 되어 unlock이 적용됨)")
    tc("NTC-220", N, ["SWR-013"], "ASIL B 오류 스냅샷이 기준 스냅샷을 갱신하지 않아 지연이 마지막 유효 스냅샷 기준으로 판정(STALE)되는지 확인(③). 오류 스냅샷으로 지연 타이머를 리셋하는 결함 검출",
       s, [WOW, ST, FI], pre="직전 출력은 1단계에서 좌·우 LOCK.")

    s = Seq()
    s.ev(10.00, None, exp=Xp(ll="RELEASE", lr="RELEASE", rc="NO_CHANGE"), note="사전 설정")
    s.ev(10.05, {"gear": "X"}, exp=Xp(ll="RELEASE", lr="RELEASE", st="DEGRADED", rc="INPUT_INVALID", iv="INVALID"), note="gear 오류 지속 0.05 s")
    s.ev(10.30, {"gear": "X"}, exp=Xp(ll="RELEASE", lr="RELEASE", st="DEGRADED", rc="INPUT_INVALID", iv="INVALID"), note="gear 오류 지속 0.30 s(STALE 아님)")
    s.ev(10.55, {"gear": "X", "rear_left_approach_risk": True}, exp=Xp(ll="LOCK", lr="RELEASE", st="DEGRADED", rc="APPROACH_RISK", rl="APPROACH_RISK", rr="INPUT_INVALID", iv="INVALID"),
         note="gear 오류 0.50 s 지속 중 좌 접근위험 true")
    tc("NTC-221", N, ["SWR-013", "SWR-005"], "gear(QM) 오류만 있는 스냅샷이 0.5 s 이어져도 STALE이 되지 않고 접근위험(ASIL B) LOCK이 적용되는지 확인(수용기준, P-1). QM 오류를 ASIL B 입력 이상으로 취급하는 결함 검출",
       s, [EP, WOW, FI], pre="직전 출력은 좌·우 모두 RELEASE.", remarks="수용기준의 '0.5초 동안'은 스냅샷이 계속 도착하는 상황으로 해석하여 0.25 s 간격 스냅샷 3회로 구성.")

    s = Seq()
    s.ev(10.00, None, exp=Xp(ll="RELEASE", lr="RELEASE", rc="NO_CHANGE"), note="사전 설정")
    s.ev(10.05, {"isofix_left": 1, "rear_left_approach_risk": True},
         exp=Xp(ll="LOCK", lr="RELEASE", st="DEGRADED", rc="APPROACH_RISK", rl="APPROACH_RISK", rr="INPUT_INVALID", iv="INVALID"), note="isofix_left=1(QM 형식 오류) + 좌 접근위험 true")
    tc("NTC-222", N, ["SWR-013", "SWR-009"], "QM 오류(isofix_left=1)와 ASIL B 접근위험이 같이 있을 때 좌 LOCK(APPROACH_RISK), 우 직전 유지(INPUT_INVALID), state=DEGRADED인지 확인(수용기준 그대로). 쪽별 혼합 판정 결함 검출",
       s, [EP, WOW], pre="직전 출력은 좌·우 모두 RELEASE.")

    s = Seq()
    for i, g in enumerate(["P", "N", "D", "R"]):
        s.ev(10.00 + 0.05 * i, {"gear": g, "vehicle_speed_kph": 3.0}, exp=Xp(ll="LOCK", lr="LOCK", st="NORMAL", rc="AUTO_LOCK", iv="VALID", w="NONE"), note=f"gear=\"{g}\"")
    tc("NTC-223", N, ["SWR-013"], "gear의 유효 값 4종(P/N/D/R)이 모두 VALID이고 판단에 쓰이지 않아 3.0 km/h에서 항상 AUTO_LOCK이 되는지 확인(A-11). 특정 gear를 오류로 보거나 gear로 자동 잠금을 억제하는 결함 검출",
       s, [EP], pre="직전 출력은 좌·우 모두 RELEASE(1단계에서 gear=P로 처음 LOCK).")

    # ---------- 운전자 명령 오류 ----------
    bad = [("side가 미등록 값(\"up\")", '{"side":"up","action":"unlock","source":"avn"}', "NTC-224"),
           ("action이 미등록 값(\"toggle\")", '{"side":"right","action":"toggle","source":"avn"}', "NTC-225"),
           ("source가 미등록 값(\"keyboard\")", '{"side":"right","action":"unlock","source":"keyboard"}', "NTC-226"),
           ("source 필드 누락", '{"side":"right","action":"unlock"}', "NTC-227")]
    for desc, raw, tid in bad:
        s = Seq()
        s.ev(10.00, None, [("all", "lock", PB)], exp=Xp(ll="LOCK", lr="LOCK", rc="DRIVER_COMMAND"), note="사전 설정: LOCK")
        s.ev(10.05, None, [("left", "unlock", "avn"), raw], exp=Xp(ll="RELEASE", lr="LOCK", rl="DRIVER_COMMAND", rr="NO_CHANGE", st="NORMAL", rc="DRIVER_COMMAND"),
             note=f"유효 명령 cmd(left,unlock,avn) + 오류 명령 {raw}")
        tc(tid, N, ["SWR-013", "SWR-002"], f"운전자 명령 오류({desc})는 그 명령만 버려지고 같은 평가의 유효 명령은 적용되는지 확인(⑤). 오류 명령을 기본값으로 보정해 실행하거나 평가 전체를 버리는 결함 검출",
           s, [EP, FI], pre="직전 출력은 1단계에서 좌·우 LOCK.",
           remarks="오류 명령 폐기 시 input_validity/state 표시는 원문에 없어 판정에서 제외(질의 Q-03). 합격: 오류 명령 대상 출력(우측)이 LOCK 유지.")

    # ---------- HTTP 422 ----------
    for tid, desc, body, obj in [
        ("NTC-228", "잘린 JSON", '{"snapshot": {"vehicle_speed_kph": 3.0, ', "본문이 중간에서 끊긴 JSON"),
        ("NTC-229", "후행 쉼표 JSON", '{"snapshot": {"vehicle_speed_kph": 3.0}, "commands": [],}', "후행 쉼표가 있는 JSON"),
        ("NTC-230", "빈 본문", "", "본문 길이 0"),
    ]:
        s = Seq()
        s.ev(10.00, {"vehicle_speed_kph": 3.0}, exp=Xp(ll="LOCK", lr="LOCK", rc="AUTO_LOCK"), note="사전 설정: LOCK, GET /events 건수 기록(1건)")
        s.act(f"POST /input 본문 = {body!r} ({obj}) 제출, 그 뒤 GET /status와 GET /events 조회",
              exp="POST 응답 HTTP 422. GET /status는 1단계 결과 그대로(lock_left=lock_right=LOCK, reason_code=AUTO_LOCK, input_validity=VALID, state=NORMAL). GET /events 건수 불변(1건)",
              inp=f"POST /input 본문: {body!r}")
        tc(tid, N, ["SWR-015"], f"JSON 구문 오류({desc})가 HTTP 422로 거절되고 시스템 상태·이벤트가 바뀌지 않는지 확인. 구문 오류를 200으로 받아 빈 입력으로 평가하거나 500을 반환하는 결함 검출",
           s, [EP, FI], pre="직전 출력은 1단계에서 좌·우 LOCK.")

    s = Seq()
    s.ev(10.00, {"vehicle_speed_kph": 3.0}, exp=Xp(ll="LOCK", lr="LOCK", rc="AUTO_LOCK"), note="사전 설정: LOCK")
    s.ev(10.05, None, raw='"abc"(문자열)', exp=HTTP200 + "HTTP 422·400·500이 아님. " + Xp(ll="LOCK", lr="LOCK", st="DEGRADED", rc="INPUT_INVALID", iv="INVALID"),
         note="유효한 JSON이지만 snapshot이 객체가 아님")
    tc("NTC-231", N, ["SWR-015", "SWR-013"], "구문은 유효하나 snapshot이 문자열인 입력이 422가 아니라 200 + INVALID/DEGRADED(평가 경로)로 처리되는지 확인. 프레임워크 스키마 검증이 422를 돌려주는 결함 검출",
       s, [EP, FI], origin="제안", pre="직전 출력은 1단계에서 좌·우 LOCK.", remarks="가정: 객체가 아닌 snapshot은 모든 필드 누락으로 보아 ASIL B 오류 처리(질의 Q-09).")

    # ---------- SWR-012 ----------
    s = Seq()
    for n, exp in [(99, "GET /events: 99건, event_id 1~99 오름차순(오래된 순)"),
                   (100, "GET /events: 100건, event_id 1~100 오름차순"),
                   (101, "GET /events: 100건, 첫 항목 event_id=2, 마지막 event_id=101, 2~101 연속 오름차순(1번 이벤트 삭제됨)")]:
        pass
    s.act("t=10.00 s부터 0.05 s 간격으로 평가를 99회 실행(각 평가: S0(ts=t) + cmd(left,lock,physical_button) 제출; 운전자 명령 평가는 항상 기록됨). GET /events 조회",
          exp="99건, event_id 1~99 오름차순(오래된 순)", inp="t=10.00~13.90(99회): S0, commands=[cmd(left,lock,physical_button)]")
    s.act("t=13.95 s에 같은 입력으로 100번째 평가 실행. GET /events 조회", exp="100건, event_id 1~100 오름차순", inp="t=13.95: S0, commands=[cmd(left,lock,physical_button)]")
    s.act("t=14.00 s에 같은 입력으로 101번째 평가 실행. GET /events 조회", exp="100건, 첫 항목 event_id=2, 마지막 event_id=101, 2~101 연속 오름차순(event_id=1 삭제됨)",
          inp="t=14.00: S0, commands=[cmd(left,lock,physical_button)]")
    tc("NTC-232", N, ["SWR-012", "SWR-010"], "보존 한도 경계(99/100/101건)에서 최근 100건만 오래된 순으로 조회되는지 확인. 한도 off-by-one(99건 또는 101건 보존), 최신 우선 정렬, 가장 새 항목을 버리는 결함 검출",
       s, [BVA, EP], pre="이벤트 0건(초기 상태).")

    s = Seq()
    s.act("t=10.00 s부터 0.05 s 간격으로 평가를 3회 실행(S0(ts=t) + cmd(left,lock,physical_button)). 시험 전 작업 디렉터리·패키지 데이터 폴더·임시 폴더의 파일 목록을 기록한다",
          exp="GET /events: 3건, event_id 1,2,3", inp="t=10.00~10.10(3회): S0, commands=[cmd(left,lock,physical_button)]")
    s.act("시험 대상 프로세스를 종료하고 다시 기동한다(같은 설치, 같은 작업 디렉터리). GET /events 조회", exp="0건(이전 이벤트가 복원되지 않음)")
    s.ev(20.00, None, exp="GET /events: 1건, event_id=1(프로세스 안에서 1부터 시작), timestamp_s=20.00")
    s.act("프로세스 종료 후 파일 목록을 시험 전과 비교", exp="새로 생긴 파일(.db, .json, .log, .sqlite 등) 없음 — 파일·DB에 저장하지 않음")
    tc("NTC-233", N, ["SWR-012", "SWR-010"], "프로세스 재시작 후 이벤트가 0건이고 event_id가 1부터 다시 시작하며 파일·DB 저장이 없는지 확인. 이벤트 영속화와 event_id 이어쓰기 결함 검출",
       s, [EP, REQ], pre="이벤트 0건(초기 상태). 파일 시스템 감시 수단(디렉터리 목록 비교) 사용 가능.", remarks="파일 비저장 확인은 디렉터리 목록 비교로 한정(질의 Q-13).")

    # ---------- SWR-016 결정론 ----------
    s = Seq()
    s.act("고정 입력 벡터 V16(아래 12개 평가, 평가 시각 포함)을 정의한다: ① t=10.00 S0 ② t=10.05 S0[vehicle_speed_kph=3.0] ③ t=10.10 S0[rear_left_approach_risk=true] + cmd(left,unlock,avn) "
          "④ t=10.15 S0[rear_left_approach_risk=true] + cmd(left,unlock,voice) ⑤ t=10.20 S0[sensor_fault=true] ⑥ t=10.25 S0[vehicle_speed_kph=300.1] ⑦ 스냅샷 없이 t=10.55 "
          "⑧ t=10.60 S0[crash_status=\"PENDING\"; vehicle_speed_kph=3.0] ⑨ t=10.65 두 스냅샷 [S0[crash_status=\"CONFIRMED\"], S0] ⑩ t=10.70 S0[ignition_on=false] ⑪ t=10.75 S0 + cmd(all,lock,mobile_app) ⑫ t=10.80 S0[ignition_on=true]",
          inp="입력 벡터 V16(12개 평가), 평가 시각 10.00~10.80 s")
    s.act("시험 대상 프로세스를 신규 기동하고(초기 상태) V16을 순서대로 재생한다. 각 평가 뒤 GET /status의 아홉 필드(lock_left, lock_right, state, priority_reason, reason_code, input_validity, reason_left, reason_right, warning_code)를 수집해 "
          "12개 결과 목록을 만든 뒤, 키 정렬 JSON(sort_keys=true)으로 직렬화하여 SHA-256 해시 H_k를 계산한다. 이를 k=1..1000회 반복한다(매 회 프로세스 신규 기동)")
    s.act("반복 중 회차마다 무작위(0~200 ms)의 실제 대기(wall-clock)를 평가 사이에 삽입하고, 회차의 절반은 벡터 재생 전에 다른 입력의 선행 시험을 한 번 수행한 뒤 프로세스를 재기동한다",
          exp="H_1 ~ H_1000 1,000개가 모두 같다(서로 다른 해시 값 1개). 실제 대기 시간과 선행 시험 이력이 결과에 영향을 주지 않음")
    tc("NTC-234", N, ["SWR-016"], "같은 초기 상태·같은 입력 순서(시각 포함)를 1,000회 재생해 공개 결과 해시가 모두 같은지 확인. 실제 시계·난수·전역 상태·dict/set 순서 의존 결함 검출",
       s, [EP, WOW], pre="시험자 측 해시 계산기: 결과 목록 직렬화 방식은 시험자가 고정(구현 내부 해시와의 비교는 하지 않음).",
       remarks="해시 직렬화 세부(구분자, 부동소수 표기)가 원문에 없어 시험자 측 동일 알고리즘으로 자기 일관성만 검증(질의 Q-12). 벡터 ⑨의 두 스냅샷 제출 순서도 고정.")
