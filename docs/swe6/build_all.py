# -*- coding: utf-8 -*-
"""system-test-cases.json 생성(작업용). 실행: python -X utf8 build_all.py"""
import json
import re
import sys

sys.path.insert(0, r"D:\repo\ClaudePython\docs\swe6")
import tcgen_lib as L
from tcgen_lib import tc, TCS
import tcgen_dt as DT
import tcgen_f
import tcgen_n

BASE = r"D:\repo\ClaudePython\docs\swe6"
MD = open(r"D:\repo\ClaudePython\docs\swe1\sw-requirements.md", encoding="utf-8").read()

TITLES = {
    "SWR-001": "네 가지 source 동일 처리", "SWR-002": "명령의 쪽별 적용과 순서", "SWR-003": "차속 3.0 km/h 이상 자동 잠금",
    "SWR-004": "unlock 차속 조건", "SWR-005": "후측방 접근위험 잠금과 unlock 억제", "SWR-006": "접근위험 override(재입력)",
    "SWR-007": "충돌 래치", "SWR-008": "충돌 PENDING 필터", "SWR-009": "접근위험 좌·우 독립", "SWR-010": "제어결정 이벤트 기록",
    "SWR-011": "이벤트 필드 제한", "SWR-012": "이벤트 100건 보존", "SWR-013": "입력 유효성 검사와 지연", "SWR-014": "상태 조회 아홉 필드",
    "SWR-015": "HTTP(JSON) 인터페이스", "SWR-016": "결정론", "SWR-017": "강제 해제(화재·과온·성인)", "SWR-018": "ISOFIX 잠금",
    "SWR-019": "규칙 우선순위", "SWR-020": "시동 OFF 해제", "SWR-021": "sensor fault 직전 유지", "SWR-022": "50 ms 평가 주기와 평가 시각",
}
NONFUNC = {"SWR-012", "SWR-013", "SWR-016", "SWR-022"}
NOTES = {
    "SWR-001": "경계값 분석 미적용: 입력이 범주형(source/action/side)뿐이며 순서 있는 범위·임계값·타이머가 없다(차속은 0.0 km/h 고정). 3개 파라미터 전 조합 24건은 PICT-01(3-way=전수)로 수용기준에 맞춰 모두 수행.",
    "SWR-002": "경계값 분석 미적용: 범주형 입력과 명령 순서만 있고 순서 있는 범위·임계값이 없다. 명령 순서 조합은 동치 클래스로 설계.",
    "SWR-005": "경계값 분석 미적용: 입력이 불리언(rear_<side>_approach_risk)이라 순서 있는 경계가 없다. 불리언 true/false 두 클래스를 모두 사용.",
    "SWR-009": "경계값 분석 미적용: 불리언·범주형 조합이며 임계값이 없다(override의 시간·차속 경계는 SWR-006에서 적용). 조합은 PICT-03 페어와이즈.",
    "SWR-010": "경계값 분석 미적용: 이벤트 기록 규칙에 순서 있는 입력 범위가 없다(100건 보존 경계는 SWR-012에서 적용).",
    "SWR-011": "동치 클래스·경계값 분석 미적용 항목이 있음: 입력 파라미터가 없고 출력(이벤트 키 집합)을 검사하는 요구사항이다. 서로 다른 이벤트 종류(첫 평가·명령 평가·오류 평가)를 한 시나리오에서 확인.",
    "SWR-014": "경계값 분석 미적용: 조회 응답 필드 존재 확인이며 순서 있는 입력 도메인이 없다.",
    "SWR-015": "경계값 분석 미적용: HTTP 본문의 JSON 구문 정상/오류 클래스만 있고 순서 있는 임계값이 없다(범위 경계 값은 SWR-013 케이스에서 HTTP 응답과 함께 검증). 일부(직렬화 실패 시 500)는 시험 환경에서 결함 주입 수단이 없어 검증 불가 — 질의 Q-01.",
    "SWR-016": "동치 클래스·경계값 분석 미적용: 입력 파라미터 없이 고정 벡터를 반복 재생하는 요구사항이다.",
    "SWR-017": "경계값 분석 미적용: 입력이 불리언 3개이며 임계값이 없다. 3개 전 조합(7건)은 PICT-02로 수행.",
    "SWR-018": "경계값 분석 미적용: 불리언 입력이며 임계값이 없다.",
    "SWR-019": "경계값 분석 미적용: 규칙 쌍·PENDING 조합을 부록 A 결정표(결정 테이블)로 전수 검증하며 순서 있는 입력 도메인이 없다(각 규칙의 임계 경계는 해당 SWR에서 적용).",
    "SWR-020": "경계값 분석 미적용: 불리언 입력이며 임계값이 없다.",
    "SWR-021": "경계값 분석 미적용: 불리언 입력이며 임계값이 없다.",
}


def parse_basis():
    out = []
    for line in MD.splitlines():
        if not line.startswith("| SWR-"):
            continue
        cells = re.split(r"\s\|\s", line.strip().strip("|").strip())
        cells = [c.strip() for c in cells]
        assert len(cells) == 5, (len(cells), line[:40])
        bid, asil, req, acc, ver = cells
        out.append({
            "id": bid, "title": TITLES[bid], "type": "비기능" if bid in NONFUNC else "기능",
            "text": f"{req} [수용기준] {acc}", "asil": "ASIL B" if asil == "B" else "QM",
            "technique_notes": NOTES.get(bid, ""),
        })
    out.sort(key=lambda b: b["id"])
    assert len(out) == 22, len(out)
    return out


def main():
    basis = parse_basis()
    models = [json.load(open(f"{BASE}\\PICT-0{i}.json", encoding="utf-8")) for i in (1, 2, 3)]
    d_rows, p_rows = DT.parse_tables(MD)

    def add(d):
        tc(d["tc_id"], d["sheet"], d["basis"], d["obj"], d["seq"], d["techs"], pre=d.get("pre", ""),
           remarks=d.get("remarks", ""), pict=d.get("pict", ""))

    tcgen_f.build()
    for d in DT.gen_pict01(models[0]):
        add(d)
    for d in DT.gen_pict02(models[1]):
        add(d)
    for d in DT.gen_pict03(models[2]):
        add(d)
    for x in DT.gen_d(d_rows):
        add(x[2])
    for x in DT.gen_p(p_rows):
        add(x[2])
    tcgen_n.build()

    issues = ISSUES
    data = {
        "project": "전자식 차일드락 제어 SW",
        "test_level": "SWE.6",
        "test_basis_source": "docs/swe1/sw-requirements.md (SWE1-SRS 개정 1.2, BL-SWR-1.2)",
        "test_basis": basis,
        "test_cases": TCS,
        "pict_models": models,
        "issues": issues,
        "template": None,
    }
    with open(f"{BASE}\\system-test-cases.json", "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=1)
    print("basis", len(basis), "cases", len(TCS))


ISSUES = [
    {"id": "Q-01", "basis_id": "SWR-015", "question": "[검증 불가·보류] '응답 직렬화에 실패하면 HTTP 500을 반환한다'는 PC/SIL 시험 환경(HTTP API + 시험용 시계)에서 직렬화 실패를 주입할 수단이 없어 시험할 수 없다. 결함 주입용 시험 훅(또는 시험용 빌드)이 제공되는지, 아니면 SWE.4 단위 시험으로 이관할지 결정 필요.",
     "impact": "SWR-015의 500 응답 부분은 케이스가 없다(SWR-015의 200/422 부분만 FTC-154, NTC-204·212·228~231로 검증). 커버리지 100%는 해당 요구사항에 최소 1건의 케이스가 있다는 뜻이며 이 부분은 미검증이다."},
    {"id": "Q-02", "basis_id": "SWR-022", "question": "[검증 불가·보류] '50 ms 주기마다 평가를 한 번 수행'은 평가 시각을 외부에서 주입하는 시험용 시계로는 실시간 주기 준수를 확인할 수 없다(평가 1회를 시험자가 직접 실행). 주기 준수(지터 허용치 포함)를 어느 환경·수단으로 검증할지, 허용 지터 기준이 필요하다. GET /clock의 응답 의미도 요구사항에 없다.",
     "impact": "SWR-022의 주기 수행 부분은 케이스가 없다. 시각 단조 증가·무스냅샷 평가·다중 스냅샷 규칙은 FTC-158~168, NTC-217~218로 검증."},
    {"id": "Q-03", "basis_id": "SWR-013", "question": "⑤ 운전자 명령 오류 시 그 명령만 버린다고 하나, 이때 input_validity(INVALID?)와 state(DEGRADED?)에 영향을 주는지 정의가 없다(명령은 '신호'가 아니라 순위 2·5 정의에 해당하는지 불명).",
     "impact": "NTC-224~227은 오류 명령 대상 출력이 바뀌지 않는 것만 판정하고 input_validity/state는 판정에서 제외."},
    {"id": "Q-04", "basis_id": "SWR-013", "question": "시작 후 첫 기준 스냅샷 전(STALE)이면서 동시에 ASIL B 오류(INVALID)인 평가(예: 첫 스냅샷의 ts가 음수)에서 input_validity와 reason_code가 INVALID/INPUT_INVALID인지 STALE/INPUT_STALE인지 우선순위가 없다.",
       "impact": "첫 평가에서 ASIL B 오류 케이스를 만들지 않음(NTC-216은 ts 하한 오류를 두 번째 평가에서 확인)."},
    {"id": "Q-05", "basis_id": "SWR-021", "question": "sensor_fault=true가 충돌 래치(순위 1) 또는 ASIL B 입력 이상(순위 2)과 같은 평가에 있을 때 warning_code가 W_SENSOR_FAULT인지 NONE인지 정의가 없다(SWR-021은 '이때'를 순위 3 적용 시로 읽을 수 있음). 부록 A D-02, D-10은 state만 정함.",
       "impact": "FTC-D-02, FTC-D-10, FTC-127 4단계는 warning_code를 판정에서 제외."},
    {"id": "Q-06", "basis_id": "SWR-008", "question": "PENDING 중 직전 출력이 이미 LOCK이고 순위 8~10이 LOCK을 요구할 때(전환 없음) reason_<side>가 ISOFIX/AUTO_LOCK/DRIVER_COMMAND인지 CRASH_PENDING인지 정의가 없다.",
       "impact": "FTC-145(제안)는 출력 LOCK 유지만 판정하고 reason은 판정에서 제외."},
    {"id": "Q-07", "basis_id": "SWR-006", "question": "override 활성 중 같은 쪽 운전자 lock 명령의 처리가 명시되어 있지 않다(1.4절 순위 4 > 10으로 무시 추정).",
       "impact": "FTC-123은 '무시(RELEASE 유지)'를 가정한 제안 케이스."},
    {"id": "Q-08", "basis_id": "SWR-007", "question": "충돌 래치 해제 조건이 '~일 때만'(필요조건)으로 쓰여 있다. crash_status·ignition_on·source_timestamp_s가 유효하면 다른 신호 오류(예: 차속 범위 오류)와 무관하게 해제되는지(충분조건) 확인 필요.",
       "impact": "FTC-136은 '다른 신호 오류와 무관하게 해제'를 가정한 제안 케이스."},
    {"id": "Q-09", "basis_id": "SWR-015", "question": "JSON 구문은 유효하나 최상위가 객체가 아니거나 snapshot/commands의 타입이 틀린 본문(예: snapshot이 문자열)의 처리가 구체적이지 않다(200 + 모든 필드 누락 처리로 추정).",
       "impact": "NTC-231은 200 + INVALID/DEGRADED를 가정한 제안 케이스."},
    {"id": "Q-10", "basis_id": "SWR-013", "question": "JSON 정수(예: vehicle_speed_kph=3)가 '실수' 필드에서 유효한지, 불리언이 숫자 자리에 오는 경우(vehicle_speed_kph=true)는 어떻게 처리하는지 정의가 없다.",
       "impact": "정수·불리언-숫자 케이스를 만들지 않았다(기대값 불명). 정의 후 동치 클래스 케이스 추가 필요."},
    {"id": "Q-11", "basis_id": "SWR-014", "question": "평가가 한 번도 실행되기 전 GET /status의 응답(필드 값 또는 오류)이 정의가 없다.",
       "impact": "초기 상태 조회 케이스를 만들지 않음."},
    {"id": "Q-12", "basis_id": "SWR-016", "question": "공개 결과 해시의 직렬화 세부(JSON 구분자, 부동소수·유니코드 표기)와 '같은 초기 상태'를 만드는 방법(프로세스 재기동 vs 리셋 API)이 정의가 없다.",
       "impact": "NTC-234는 시험자 측 고정 알고리즘으로 1,000회 해시가 같은지만(자기 일관성) 검증하고 구현 내부 해시값과는 비교하지 않는다."},
    {"id": "Q-13", "basis_id": "SWR-012", "question": "'파일·DB에 저장하지 않는다'(부정 요구사항)의 PC/SIL 검증 방법이 정의가 없다. 디렉터리 파일 목록 비교로 한정해도 되는지, 프로세스 파일 핸들 감시가 필요한지 확인 필요.",
       "impact": "NTC-233은 파일 목록 비교로만 확인(가정)."},
    {"id": "Q-14", "basis_id": "SWR-006", "question": "시간·임계 비교(10.0 s, 2.0 s, 0.200 s, 1.0 s, 0.050 s 이하)의 부동소수 오차 허용 방식(십진 값 기준 정확 비교 vs 엡실론)이 정의가 없다. 예: 20.10−10.10은 배정밀도에서 10.000000000000002.",
       "impact": "FTC-111, 128, 130, 141, NTC-213, 217은 십진 값 기준 '이하(≤)' 합격을 가정하고 부동소수 오차 값을 의도적으로 선택. 구현이 엡실론 없이 비교하면 실패하며 이는 결함으로 판정."},
    {"id": "Q-15", "basis_id": "SWR-022", "question": "한 주기에 CONFIRMED 스냅샷이 여러 개이고 마지막 CONFIRMED의 나이가 1.0초를 넘는 경우(앞의 CONFIRMED는 유효) 앞의 것을 쓰는지 마지막만 쓰는지 불명하다. 마지막만 쓰면 안전측이 아니다.",
       "impact": "마지막 CONFIRMED가 유효한 경우만 FTC-163으로 검증. 마지막이 오래된 경우 케이스를 만들지 않음."},
    {"id": "Q-16", "basis_id": "SWR-007", "question": "나이 0.200 s 초과 1.0 s 이하의 늦게 도착한 CONFIRMED로 래치가 선 평가의 input_validity가 STALE이 맞는지(그 스냅샷이 기준 스냅샷이 되며 나이 > 0.200 s) 확인 필요.",
       "impact": "FTC-128의 input_validity=STALE 판정은 SWR-013 ①③에서 도출한 가정."},
    {"id": "Q-17", "basis_id": "SWR-013", "question": "source_timestamp_s의 '0.0 이상' 범위 오류는 역행 검사(기준 스냅샷보다 작음)와 겹쳐(기준이 있으면 음수는 항상 역행) 단독 시험이 불가능하다. 범위 오류와 역행 오류를 구분해야 하는 요구가 있는지 확인 필요.",
       "impact": "NTC-216은 음수 ts가 INVALID가 되는지만 판정."},
    {"id": "Q-18", "basis_id": "SWR-004", "question": "'lock은 차속과 관계없이 적용한다'는 3.0 km/h 이상에서 자동 잠금(순위 9)과 결과가 같아 출력으로 구분되지 않는다(reason은 AUTO_LOCK). 별도 시험이 필요한지 확인 필요.",
       "impact": "고속 lock 단독 케이스를 만들지 않음(결함을 구분해 드러낼 수 없음)."},
]

if __name__ == "__main__":
    main()
