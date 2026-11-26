# 테스트 케이스 JSON 스키마 (`build_workbook.py` 입력)

UTF-8로 저장한다.

```json
{
  "project": "Door Lock ECU SW",
  "test_level": "SWE.6",
  "test_basis_source": "DoorLock_SRS_v1.2.docx",
  "test_basis": [
    {
      "id": "SWR-010",
      "title": "차속 연동 자동 잠금",
      "type": "기능",
      "text": "차속이 15 km/h 이상이 되면 500 ms 이내에 전 도어를 잠근다.",
      "asil": "QM",
      "technique_notes": ""
    }
  ],
  "test_cases": [
    {
      "tc_id": "FTC-001",
      "sheet": "기능",
      "basis_ids": ["SWR-010"],
      "objective": "임계값 직하(14 km/h)에서 자동 잠금이 동작하지 않음을 확인",
      "preconditions": "HIL, IGN=ON, Gear=D, 전 도어 닫힘, DoorLockCmd=UNLOCK",
      "inputs": "VehSpd = 14 km/h",
      "procedure": ["VehSpd를 0에서 14 km/h로 설정", "1000 ms 대기", "DoorLockCmd 관측"],
      "expected": "DoorLockCmd = UNLOCK 유지 (1000 ms 동안 LOCK 송신 없음)",
      "techniques": ["경계값 분석", "동치 클래스"],
      "origin": "기본",
      "pict_ref": "",
      "remarks": ""
    }
  ],
  "pict_models": [],
  "issues": [
    {"id": "Q-01", "basis_id": "SWR-010", "question": "VehSpd 신호 무효 시 동작이 정의되지 않음", "impact": "FTC-012는 '잠금 상태 유지'를 가정한 제안 케이스"}
  ],
  "template": null
}
```

## 필드 규칙

| 필드 | 필수 | 설명 |
|---|---|---|
| `test_basis[].type` | O | `기능` 또는 `비기능` |
| `test_basis[].technique_notes` | 조건부 | 이 항목에 동치 클래스나 경계값 분석이 적용되지 않았으면 이유를 적는다. 없으면 오류 |
| `test_cases[].sheet` | O | `기능` 또는 `비기능`. 베이시스 type과 달라도 된다(예: 기능 요구사항의 응답 시간 케이스는 비기능) |
| `test_cases[].basis_ids` | O | 1개 이상. 모두 `test_basis`에 있어야 함 |
| `preconditions` | O | 시험 환경, 시스템 상태, 초기 신호값. 실행 가능성의 전제라 필수 |
| `procedure` | O | 문자열 배열. 엑셀에서 번호가 매겨진다 |
| `techniques` | O | 허용 값: `동치 클래스`, `경계값 분석`, `페어와이즈(PICT)`, `WoW 검증`, `요구사항 기반 테스트`, `결함 주입`, `오류 추측`, `상태 전이`, `결정 테이블` |
| `origin` | O | `기본` 또는 `제안` |
| `pict_ref` | 조건부 | techniques에 `페어와이즈(PICT)`가 있으면 필수. `<모델ID>#<행번호>` |
| `pict_models` | 조건부 | `run_pict.py` 출력 JSON 객체들을 그대로 넣는다 |

## 사용자 양식(template) 사용

사용자가 엑셀 양식을 주면 `template`을 채운다:

```json
"template": {
  "path": "C:/work/TC_Template.xlsx",
  "sheets": {"기능": "Functional", "비기능": "NonFunctional"},
  "header_row": 3,
  "column_map": {
    "TC No.": "tc_id",
    "Req. ID": "basis_ids",
    "Test Objective": "objective",
    "Precondition": "preconditions",
    "Input": "inputs",
    "Test Steps": "procedure",
    "Expected Result": "expected",
    "Test Method": "techniques",
    "Type": "origin"
  }
}
```

- `sheets`: 기능/비기능 케이스를 넣을 양식 내 시트 이름. 양식에 시트가 하나뿐이면 그 시트를 복사해 두 시트를 만든다(`"비기능": null`로 두면 스크립트가 복사).
- `column_map`: 양식 헤더 문자열 → 필드 키. 양식에 필수 항목(TC ID, 베이시스 ID, 목적, 입력값, 절차, 예상 출력값, 기법) 열이 없으면 헤더 오른쪽 끝에 열을 추가하고 경고한다. `제안` 표시가 빠지면 안 되므로 `origin` 열도 같은 방식으로 보장한다.
- 추적성 매트릭스·커버리지 요약 시트는 양식과 별도로 항상 추가된다.
