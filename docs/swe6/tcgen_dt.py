# -*- coding: utf-8 -*-
"""부록 A 결정표(D-01~D-45, P-01~P-10)와 PICT 모델 3종에서 케이스를 생성한다."""
import json
import re
from tcgen_lib import *

RANK_SWR = {1: "SWR-007", 2: "SWR-013", 3: "SWR-021", 4: "SWR-005", 5: "SWR-013", 6: "SWR-020",
            7: "SWR-017", 8: "SWR-018", 9: "SWR-003"}
RANK_NAME = {1: "충돌 래치", 2: "ASIL B 입력 이상", 3: "sensor fault", 4: "접근위험", 5: "QM 입력 이상",
             6: "시동 OFF", 7: "강제 해제(화재)", 8: "ISOFIX", 9: "자동 잠금", 10: "운전자 명령"}


def cond_for(rank, cmd_action="unlock"):
    """(스냅샷 변경, 명령 목록, 오라클 플래그)"""
    if rank == 1:
        return {"crash_status": "CONFIRMED"}, [], {"latch": True}
    if rank == 2:
        return {"rear_right_approach_risk": 1}, [], {"r2": True}
    if rank == 3:
        return {"sensor_fault": True}, [], {"r3": True}
    if rank == 4:
        return {"rear_left_approach_risk": True}, [], {"risk_l": True}
    if rank == 5:
        return {"gear": "X"}, [], {"r5": True}
    if rank == 6:
        return {"ignition_on": False}, [], {"ign_off": True}
    if rank == 7:
        return {"fire_detected": True}, [], {"fire": True}
    if rank == 8:
        return {"isofix_left": True}, [], {"iso_l": True}
    if rank == 9:
        return {"vehicle_speed_kph": 3.0}, [], {"speed3": True}
    if rank == 10:
        return {}, [("left", cmd_action, "physical_button")], {"cmd_l": cmd_action}
    raise ValueError(rank)


def parse_tables(md):
    d, p = [], []
    for line in md.splitlines():
        m = re.match(r"\| (D-\d\d) \| (.*?) \| (.*?) \| (.*?) \| (.*?) \| (.*?) \|$", line)
        if m:
            d.append(m.groups())
        m = re.match(r"\| (P-\d\d) \| (.*?) \| (.*?) \| (.*?) \| (.*?) \|$", line)
        if m:
            p.append(m.groups())
    assert len(d) == 45 and len(p) == 10, (len(d), len(p))
    return d, p


def rk(cell):
    return int(re.search(r"\((\d+)\)", cell).group(1))


def merged(*conds):
    chg, cmds, fl = {}, [], {}
    for c, m, f in conds:
        chg.update(c)
        cmds += m
        fl.update(f)
    return chg, cmds, fl


def full_expected(L, R, rc, st, c, snap_err_inputs):
    iv = "INVALID" if (c.get("r2") or c.get("r5")) else "VALID"
    kw = dict(ll=L[0], lr=R[0], st=st, rc=rc, rl=L[1], rr=R[1], iv=iv)
    # warning_code: 순위 3이 해당 쪽을 정하는 행(순위 1·2가 아닌 경우)에서만 판정한다.
    if c.get("r3") and not c.get("latch") and not c.get("r2"):
        kw["w"] = "W_SENSOR_FAULT"
    elif not c.get("r3"):
        kw["w"] = "NONE"
    return Xp(**kw)


def prior_for(c):
    outs = {p: eval_both(p, p, c) for p in ("RELEASE", "LOCK")}
    lo, hi = outs["RELEASE"][0][0], outs["LOCK"][0][0]
    if lo == hi:  # 출력이 직전 값과 무관하게 정해짐 -> 반대 값을 직전 값으로
        return "LOCK" if lo == "RELEASE" else "RELEASE"
    # 직전 유지: 하위 규칙이 만들었을 출력의 반대
    return None


def gen_d(rows):
    out = []
    for (did, up, lo, outp, reason, state) in rows:
        ru, rl_ = rk(up), rk(lo)
        action = "unlock"
        cu, cl = cond_for(ru), cond_for(rl_, action)
        if ru == 2 and rl_ == 5:
            pass
        chg, cmds, fl = merged(cu, cl)
        # 직전 값 결정
        pr = prior_for(fl)
        if pr is None:
            pr = "RELEASE" if rl_ in (4, 8, 9) else "LOCK"
        L, R, rc, st = eval_both(pr, pr, fl)
        # 결정표와 대조(해당 쪽 = 좌측)
        exp_out = outp.strip()
        if exp_out in ("RELEASE", "LOCK"):
            assert L[0] == exp_out, (did, L, exp_out)
        else:
            assert L[0] == pr, (did, L, pr)
        assert L[1] == reason.split(" / ")[0].strip(), (did, L, reason)
        assert rc == reason.split(" / ")[0].strip(), (did, rc, reason)
        assert st == state.strip(), (did, st, state)
        s = Seq()
        if pr == "LOCK":
            s.ev(10.00, {"vehicle_speed_kph": 3.0}, exp=Xp(ll="LOCK", lr="LOCK", rc="AUTO_LOCK"),
                 note="사전 설정: 직전 출력을 LOCK으로 만든다")
        else:
            s.ev(10.00, None, exp=Xp(ll="RELEASE", lr="RELEASE", st="NORMAL", rc="NO_CHANGE"), note="사전 설정: 직전 출력 RELEASE")
        s.ev(10.05, chg, cmds, exp=full_expected(L, R, rc, st, fl, None),
             note=f"{did}: 상위 {RANK_NAME[ru]}(순위 {ru}) + 하위 {RANK_NAME[rl_]}(순위 {rl_}) 동시 성립")
        basis = ["SWR-019", RANK_SWR[ru], RANK_SWR.get(rl_, "SWR-004")]
        basis = list(dict.fromkeys(basis))
        obj = (f"{did}: {RANK_NAME[ru]}(순위 {ru})와 {RANK_NAME[rl_]}(순위 {rl_})가 같은 평가·같은 쪽에 성립할 때 상위 규칙이 이긴다. "
               f"규칙 순서 뒤바뀜·하위 규칙 누수 결함 검출")
        pre = f"직전 출력은 좌·우 모두 {pr}. 부록 A.1 {did}의 '기본값'(차속 0.0 km/h, 시동 ON, 모든 신호 유효·최신)에서 두 규칙의 조건만 추가한다."
        rem = f"결정표 {did} 기대값(해당 쪽 {outp}, {reason}, {state})과 일치. 우측은 해당 규칙이 없는 쪽으로 오라클 계산."
        out.append((did, tc, dict(tc_id=f"FTC-{did}", sheet="기능", basis=basis, obj=obj, seq=s,
                                  techs=["결정 테이블", "동치 클래스"], pre=pre, remarks=rem)))
    return out


def gen_p(rows):
    out = []
    for (pid, rule, outp, reason, state) in rows:
        r = rk(rule)
        c1 = {"crash_status": "CONFIRMED"} if r == 1 else {"crash_status": "PENDING"}
        s = Seq()
        if r == 1:
            s.ev(10.00, c1, exp=Xp(ll="RELEASE", lr="RELEASE", st="NORMAL", rc="CRASH_CONFIRMED"),
                 note="사전 설정: 충돌 래치 성립")
            chg, cmds, fl = {"crash_status": "PENDING"}, [], {"latch": True, "pending": True}
        else:
            s.ev(10.00, c1, exp=Xp(ll="RELEASE", lr="RELEASE", st="NORMAL", rc="NO_CHANGE"),
                 note="사전 설정: PENDING 시작(타이머 시작), 직전 출력 RELEASE")
            cc, cm, fl = cond_for(r, "lock")
            chg = dict(cc)
            chg["crash_status"] = "PENDING"
            cmds = cm
            fl = dict(fl)
            fl["pending"] = True
        L, R, rc, st = eval_both("RELEASE", "RELEASE", fl)
        exp_out = outp.strip().split(" ")[0]
        if exp_out in ("RELEASE", "LOCK"):
            assert L[0] == exp_out, (pid, L)
        else:
            assert L[0] == "RELEASE", (pid, L)
        assert rc == reason.split(" / ")[0].strip(), (pid, rc, reason)
        assert st == state.strip(), (pid, st, state)
        s.ev(10.05, chg, cmds, exp=full_expected(L, R, rc, st, fl, None),
             note=f"{pid}: crash_status=PENDING(시작 후 0.05 s) + {RANK_NAME[r]}(순위 {r}) 동시 성립")
        basis = ["SWR-019", "SWR-008"] + ([RANK_SWR[r]] if r in RANK_SWR else ["SWR-002"])
        basis = list(dict.fromkeys(basis))
        obj = (f"{pid}: PENDING 필터가 순위 8~10의 RELEASE→LOCK만 막고 순위 1~7 결과는 막지 않음. "
               f"필터 적용 범위 오류(상위 규칙까지 막거나 8~10을 못 막음) 검출")
        pre = "직전 출력은 좌·우 모두 RELEASE(P-01은 1단계에서 래치 성립)."
        rem = f"결정표 {pid} 기대값({outp}, {reason}, {state})과 일치."
        out.append((pid, tc, dict(tc_id=f"FTC-{pid}", sheet="기능", basis=basis, obj=obj, seq=s,
                                  techs=["결정 테이블", "동치 클래스"], pre=pre, remarks=rem)))
    return out


SRC = ["physical_button", "avn", "voice", "mobile_app"]


def gen_pict01(model):
    out = []
    for i, row in enumerate(model["rows"], 1):
        src, act, side = row["Source"], row["Action"], row["Side"]
        s = Seq()
        sides = ["left", "right"] if side == "all" else [side]
        if act == "lock":
            prior = "RELEASE"
            s.ev(10.00, None, exp=Xp(ll="RELEASE", lr="RELEASE", rc="NO_CHANGE"), note="사전 설정: 직전 출력 RELEASE, 차속 0.0 km/h")
            res = "LOCK"
        else:
            prior = "LOCK"
            s.ev(10.00, None, [("all", "lock", "physical_button")], exp=Xp(ll="LOCK", lr="LOCK", rc="DRIVER_COMMAND"),
                 note="사전 설정: 직전 출력을 LOCK으로 만든다(차속 0.0 km/h)")
            res = "RELEASE"
        ll = res if "left" in sides else prior
        lr = res if "right" in sides else prior
        rl = "DRIVER_COMMAND" if "left" in sides else "NO_CHANGE"
        rr = "DRIVER_COMMAND" if "right" in sides else "NO_CHANGE"
        s.ev(10.05, None, [(side, act, src)], exp=Xp(ll=ll, lr=lr, st="NORMAL", rc="DRIVER_COMMAND", rl=rl, rr=rr, iv="VALID", w="NONE"),
             note=f"정지 상태에서 {src} {act} {side}")
        out.append(dict(tc_id=f"FTC-PW01-{i:02d}", sheet="기능", basis=["SWR-001", "SWR-002"],
                        obj=f"PICT-01#{i}: source={src}, action={act}, side={side} 조합 처리. source별 분기 누락·side/action 조합 결함 검출(수용기준이 24개 조합 전수를 요구하므로 3-way=전수)",
                        seq=s, techs=["페어와이즈(PICT)", "동치 클래스"], pict=f"PICT-01#{i}",
                        pre=f"직전 출력은 좌·우 모두 {prior}. 차속 0.0 km/h(정지), 모든 신호 정상.",
                        remarks="선택되지 않은 쪽은 직전 값 유지(reason=NO_CHANGE)"))
    return out


def gen_pict02(model):
    out = []
    for i, row in enumerate(model["rows"], 1):
        f, o, a = (row[k] == "true" for k in ("Fire", "Overtemp", "Adult"))
        reason = "FIRE" if f else ("OVERTEMPERATURE" if o else "ADULT_PRESENT")
        chg = {"isofix_left": True, "isofix_right": True, "fire_detected": f, "overtemperature_detected": o, "adult_present": a}
        s = Seq()
        s.ev(10.00, {"isofix_left": True, "isofix_right": True}, exp=Xp(ll="LOCK", lr="LOCK", rc="ISOFIX"),
             note="사전 설정: ISOFIX true로 양쪽 LOCK")
        s.ev(10.05, chg, exp=Xp(ll="RELEASE", lr="RELEASE", st="NORMAL", rc=reason, rl=reason, rr=reason, iv="VALID", w="NONE"),
             note="강제 해제 입력 적용(ISOFIX는 true 유지)")
        desc = ", ".join(n for n, v in (("fire_detected", f), ("overtemperature_detected", o), ("adult_present", a)) if v)
        out.append(dict(tc_id=f"FTC-PW02-{i}", sheet="기능", basis=["SWR-017"],
                        obj=f"PICT-02#{i}: {desc}=true. 강제 해제가 ISOFIX 잠금보다 우선하고 이유 순위(화재>과온>성인)가 지켜지는지 검출",
                        seq=s, techs=["페어와이즈(PICT)", "동치 클래스"], pict=f"PICT-02#{i}",
                        pre="직전 출력은 1단계에서 LOCK(ISOFIX).", remarks="3개 불리언 전수(7행): 단독 입력 3건 + 이유 순위 조합 4건"))
    return out


def gen_pict03(model):
    out = []
    for i, row in enumerate(model["rows"], 1):
        rl_, rr_, il, ir = (row[k] == "true" for k in ("RiskL", "RiskR", "IsoL", "IsoR"))
        cm, sp = row["Cmd"], float(row["Speed"])
        src = SRC[i % 4]
        cmds = {"NONE": [], "L_UNLOCK": [("left", "unlock", src)], "R_UNLOCK": [("right", "unlock", src)],
                "ALL_UNLOCK": [("all", "unlock", src)], "L_LOCK": [("left", "lock", src)],
                "R_LOCK": [("right", "lock", src)], "ALL_LOCK": [("all", "lock", src)]}[cm]
        cl = cr = None
        if cm != "NONE":
            side, act = cm.split("_")
            act = act.lower()
            if side in ("L", "ALL"):
                cl = act
            if side in ("R", "ALL"):
                cr = act
        fl = {"risk_l": rl_, "risk_r": rr_, "iso_l": il, "iso_r": ir, "speed3": sp >= 3.0, "cmd_l": cl, "cmd_r": cr}
        L, R, rc, st = eval_both("LOCK", "RELEASE", fl)
        chg = {}
        if rl_:
            chg["rear_left_approach_risk"] = True
        if rr_:
            chg["rear_right_approach_risk"] = True
        if il:
            chg["isofix_left"] = True
        if ir:
            chg["isofix_right"] = True
        if sp:
            chg["vehicle_speed_kph"] = sp
        s = Seq()
        s.ev(10.00, None, [("left", "lock", "physical_button")], exp=Xp(ll="LOCK", lr="RELEASE", rl="DRIVER_COMMAND", rr="NO_CHANGE"),
             note="사전 설정: 좌 LOCK / 우 RELEASE로 비대칭 직전 상태 만들기")
        s.ev(10.05, chg, cmds, exp=Xp(ll=L[0], lr=R[0], st=st, rc=rc, rl=L[1], rr=R[1], iv="VALID", w="NONE"))
        out.append(dict(tc_id=f"FTC-PW03-{i:02d}", sheet="기능", basis=["SWR-009", "SWR-005", "SWR-018", "SWR-003", "SWR-004"],
                        obj=f"PICT-03#{i}: 좌/우 접근위험·ISOFIX·명령·차속 조합에서 쪽별 독립 판정과 reason_code 선택(순위 높은 쪽, 동순위는 좌측) 검증. 좌우 혼동·공유 상태 결함 검출",
                        seq=s, techs=["페어와이즈(PICT)", "동치 클래스"], pict=f"PICT-03#{i}",
                        pre="직전 출력은 1단계 결과인 좌 LOCK / 우 RELEASE. 첫 억제 이력 없음(1단계 명령은 lock).",
                        remarks="예상값은 SWR-005/009/018/003/004와 1.4절 순위로 계산. 첫 평가 이후 override는 성립할 수 없으므로 state=NORMAL."))
    return out
