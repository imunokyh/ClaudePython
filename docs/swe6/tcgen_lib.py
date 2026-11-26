# -*- coding: utf-8 -*-
"""SWE.6 테스트 케이스 생성용 작업 파일(헬퍼, 규칙 오라클). 산출물 아님."""
import json

ENV = (
    "[시험 환경] PC/SIL. 시험 대상 Python 패키지를 신규 기동한 초기 상태(lock_left=lock_right=RELEASE, 평가 이력·이벤트 없음). "
    "시험자는 시험용 시계로 평가 시각 t를 직접 지정하고, HTTP API(POST /input, GET /status, GET /events)로 입력과 조회를 한다. "
    "기본 스냅샷 S0 = {source_timestamp_s=평가 시각 t, vehicle_speed_kph=0.0, gear=\"P\", crash_status=\"NONE\", "
    "rear_left_approach_risk=false, rear_right_approach_risk=false, fire_detected=false, overtemperature_detected=false, "
    "adult_present=false, isofix_left=false, isofix_right=false, ignition_on=true, sensor_fault=false}. "
    "표기: S0[ts=값; 필드=값] 는 S0에서 대괄호 안의 필드만 바꾼 스냅샷이며 ts는 source_timestamp_s(생략하면 t와 같음). "
    "cmd(side,action,source)는 {\"side\":side,\"action\":action,\"source\":source} 운전자 명령이며 L=left, R=right. "
    "한 단계 = POST /input 제출 → 평가 1회 실행(평가 시각 t) → GET /status 조회."
)

MISSING = object()
UNITS = {"vehicle_speed_kph": " km/h", "source_timestamp_s": " s"}


def fv(x):
    if isinstance(x, bool):
        return "true" if x else "false"
    if isinstance(x, str):
        return json.dumps(x, ensure_ascii=False)
    if isinstance(x, float):
        return repr(x)
    return str(x)


def snap_txt(chg=None, ts=None):
    items = []
    if ts is not None:
        items.append(f"ts={fv(ts)}")
    for k, val in (chg or {}).items():
        items.append(f"{k} 필드 삭제" if val is MISSING else f"{k}={fv(val)}")
    return "S0[" + "; ".join(items) + "]" if items else "S0"


def cmd_txt(c):
    if isinstance(c, str):
        return c
    side, action, src = c
    return f"cmd({side},{action},{src})"


SNAKE = lambda s: s.lower()


def Xp(**kw):
    """예상 출력 문자열. ll lr st rc rl rr iv w"""
    names = [("ll", "lock_left"), ("lr", "lock_right"), ("st", "state"), ("rc", "reason_code"), ("rl", "reason_left"),
             ("rr", "reason_right"), ("iv", "input_validity"), ("w", "warning_code")]
    parts = []
    for k, n in names:
        if k in kw:
            parts.append(f"{n}={kw[k]}")
            if k == "rc" and kw.get("pr", True):
                parts.append(f"priority_reason={SNAKE(kw[k])}")
    if "extra" in kw:
        parts.append(kw["extra"])
    return ", ".join(parts)


class Seq:
    def __init__(self):
        self.p, self.e, self.inp = [], [], []

    def ev(self, t, chg=None, cmds=None, ts=None, nosnap=False, exp=None, snaps=None, note="", raw=None):
        cmds = cmds or []
        ctxt = "[" + ", ".join(cmd_txt(c) for c in cmds) + "]"
        if raw is not None:
            text = f"평가 시각 t={t:.2f} s: POST /input {{snapshot: {raw}, commands: {ctxt}}} 제출 후 평가 1회 실행, GET /status 조회"
            self.inp.append(f"t={t:.2f}: snapshot={raw}; commands={ctxt}")
        elif snaps is not None:
            sn = " → ".join(f"POST #{i}: snapshot={snap_txt(c, tsv)}" for i, (c, tsv) in enumerate(snaps, 1))
            text = f"평가 시각 t={t:.2f} s: POST /input을 {len(snaps)}회 연속 제출({sn}; commands={ctxt}) 후 평가 1회 실행, GET /status 조회"
            self.inp.append(f"t={t:.2f}: 스냅샷 {len(snaps)}개 " + " / ".join(self._inp(c, tsv) for c, tsv in snaps))
        elif nosnap:
            text = f"평가 시각 t={t:.2f} s: 스냅샷 없이 POST /input {{commands: {ctxt}}} 제출 후 평가 1회 실행, GET /status 조회"
            self.inp.append(f"t={t:.2f}: 스냅샷 없음; commands={ctxt}")
        else:
            text = f"평가 시각 t={t:.2f} s: POST /input {{snapshot: {snap_txt(chg, ts)}, commands: {ctxt}}} 제출 후 평가 1회 실행, GET /status 조회"
            self.inp.append(f"t={t:.2f}: {self._inp(chg, ts)}; commands={ctxt}")
        if note:
            text += f" ({note})"
        self.p.append(text)
        if exp:
            self.e.append(f"{len(self.p)}단계: {exp}")
        return self

    def _inp(self, chg, ts):
        items = []
        if ts is not None:
            items.append(f"source_timestamp_s={fv(ts)} s")
        for k, val in (chg or {}).items():
            items.append(f"{k} 삭제" if val is MISSING else f"{k}={fv(val)}{UNITS.get(k, '')}")
        return ", ".join(items) if items else "S0(기본값)"

    def act(self, text, exp=None, inp=None):
        self.p.append(text)
        if inp:
            self.inp.append(inp)
        if exp:
            self.e.append(f"{len(self.p)}단계: {exp}")
        return self

    def expected(self):
        return "\n".join(self.e)


TCS = []


def tc(tc_id, sheet, basis, obj, seq, techs, origin="기본", pre="", remarks="", pict="", inputs=None, expected=None):
    TCS.append({
        "tc_id": tc_id, "sheet": sheet, "basis_ids": basis, "objective": obj,
        "preconditions": ENV + (" " + pre if pre else ""),
        "inputs": inputs if inputs is not None else "\n".join(seq.inp),
        "procedure": seq.p,
        "expected": expected if expected is not None else seq.expected(),
        "techniques": techs, "origin": origin, "pict_ref": pict, "remarks": remarks,
    })


# ---------------- 규칙 오라클(결정표·페어와이즈 행의 예상값 계산용) ----------------
def side_eval(prior, c, side):
    """c: dict(latch,r2,r3,risk_l,risk_r,r5,ign_off,fire,over,adult,iso_l,iso_r,speed3,cmd_l,cmd_r,pending)
    반환 (출력, reason, rank)"""
    risk = c.get("risk_" + side[0].lower(), False)
    iso = c.get("iso_" + side[0].lower(), False)
    cmd = c.get("cmd_" + side[0].lower())
    pend = c.get("pending", False)

    def lockrule(reason, rank):
        if pend and prior == "RELEASE":
            return (prior, "CRASH_PENDING", rank)
        return ("LOCK", reason, rank)

    if c.get("latch"):
        return ("RELEASE", "CRASH_CONFIRMED", 1)
    if c.get("r2"):
        return (prior, "INPUT_INVALID", 2)
    if c.get("r3"):
        return (prior, "SENSOR_FAULT", 3)
    if risk:
        return ("LOCK", "APPROACH_RISK", 4)
    if c.get("r5"):
        return (prior, "INPUT_INVALID", 5)
    if c.get("ign_off"):
        return ("RELEASE", "IGNITION_OFF", 6)
    if c.get("fire"):
        return ("RELEASE", "FIRE", 7)
    if c.get("over"):
        return ("RELEASE", "OVERTEMPERATURE", 7)
    if c.get("adult"):
        return ("RELEASE", "ADULT_PRESENT", 7)
    if iso:
        return lockrule("ISOFIX", 8)
    if c.get("speed3"):
        return lockrule("AUTO_LOCK", 9)
    if cmd == "lock":
        return lockrule("DRIVER_COMMAND", 10)
    if cmd == "unlock":
        return ("RELEASE", "DRIVER_COMMAND", 10)
    return (prior, "NO_CHANGE", 11)


def eval_both(prior_l, prior_r, c):
    L = side_eval(prior_l, c, "left")
    R = side_eval(prior_r, c, "right")
    rc = L[1] if L[2] <= R[2] else R[1]
    if c.get("r2") or c.get("r5"):
        st = "DEGRADED"
    elif c.get("r3"):
        st = "FAULT"
    elif c.get("ign_off"):
        st = "OFF"
    else:
        st = "NORMAL"
    return L, R, rc, st
