# SW 요구사항 명세 — 전자식 차일드락 제어 SW

| 항목 | 내용 |
|---|---|
| 문서 ID | SWE1-SRS |
| 개정 | 1.3 |

| 개정 | 날짜 | 내용 |
|---|---|---|
| 1.0 | 2026-11-26 | 최초 베이스라인 (독립 검토 SWE1-REV RV-01~43 반영) |
| 1.1 | 2026-11-26 | SWE.2 아키텍처 검토(SWE2-REV)에서 드러난 결함·모호함 정정: SWR-013 기준 스냅샷 정의(AR-02), SWR-006 첫 억제 조건·입력 이상 중 명령 처리·시각 기준(AR-06, AR-07, AR-17), SWR-007 래치 해제는 새 스냅샷에서만(AR-16), SWR-008 PENDING 타이머 기준(AR-15), SWR-022 평가 시각 단조 증가·오류 시 처리·복귀, 한 주기 다중 스냅샷 규칙(AR-01, AR-24~26), 1.2절 충돌 판정 예외(AR-27), A-24·A-25 추가 |
| 1.2 | 2026-11-26 | SWE.3 상세 설계 검토(SWE3-REV DD-17): SWR-007 충돌 판정에 타임스탬프 역행 검사 미적용 명시. 1.4절 순위 7의 `priority_reason` 명시 |
| 1.3 | 2026-11-26 | SWE.6 검증에서 발견한 요구사항 결함 정정(SWE6-VR F-02): SWR-015 입력 제출 응답을 200에서 202(Accepted)로 정정. 설계(SWE3-DD 6장)·구현·통합 시험은 처음부터 202였다 |
| 베이스라인 | BL-SWR-1.3 (G1 제출 대상, 1.2 대체) |
| 상위 입력 | OEM-SWR-001 Rev 1.0 (BL-OEM-1.0) |
| A-SPICE | SWE.1 Software Requirements Analysis |

이 문서는 OEM 요구사항(OEM-SR/FR/NFR)과 외부 인터페이스(OEM-IF)를 공급자 SW 요구사항(SWR)으로 분해한다. OEM 문서에 정의되지 않아 공급자가 정한 내용은 `가정`(A-xx)으로 표시하고 `oem-queries.md`의 질의(Q-xx)와 연결한다. 의사결정(DEC-xx)은 `docs/development-plan.md`에 있다.

**범위 경계**: 출력은 PC/SIL 논리 출력(`LOCK`/`RELEASE`)까지 검증한다. 액추에이터 적용 feedback, CAN/LIN 드라이버, 전기 출력은 범위 밖이다(OEM-IF-005).

## 1. 공통 정의

### 1.1 설계 원칙 (ISO 26262-6 공존·간섭 배제)

- **P-1.** ASIL B 규칙이 정한 출력은 QM 규칙이나 QM 신호의 이상이 바꾸지 못한다. 이를 위해 ASIL B 규칙을 모두 QM 규칙보다 위에 두고(1.4절), 신호 이상도 등급별로 처리한다(1.2절).
- **P-2.** 충돌 래치 해제처럼 ASIL B 상태를 바꾸는 로직은 ASIL B로 개발한다.

### 1.2 입력 (OEM-IF)

| 신호 | 형식 / 범위 | 인터페이스 | 신호 등급 |
|---|---|---|---|
| `source_timestamp_s` | 실수, 0.0 이상 (초) | OEM-IF-001 | ASIL B |
| `vehicle_speed_kph` | 실수, 0.0~300.0 km/h (경계 포함) | OEM-IF-001 | ASIL B |
| `gear` | `P` / `N` / `D` / `R` | OEM-IF-001 | QM |
| `crash_status` | `NONE` / `PENDING` / `CONFIRMED` | OEM-IF-002 | ASIL B |
| `rear_left_approach_risk`, `rear_right_approach_risk` | 불리언 | OEM-IF-003 | ASIL B |
| `fire_detected`, `overtemperature_detected`, `adult_present` | 불리언 | OEM-IF-007 | QM |
| `isofix_left`, `isofix_right` | 불리언 | OEM-IF-008 | QM |
| `ignition_on`, `sensor_fault` | 불리언 | OEM-IF-009 | ASIL B |
| 운전자 명령 `side` / `action` / `source` | `left`/`right`/`all`; `lock`/`unlock`; `physical_button`/`avn`/`voice`/`mobile_app` | OEM-IF-004 | QM (override 판단은 ASIL B) |

- **신호 등급**: ASIL B 규칙(충돌, 입력 감시, sensor fault, 접근위험·override, 래치 해제)이 쓰는 신호는 ASIL B 신호다. 그 밖은 QM 신호다. `가정` A-21
- **불리언**: `true`/`false`만 허용한다. 0/1, 문자열은 형식 오류다. `가정` A-12
- **스냅샷**: 차량 신호는 스냅샷 하나에 `source_timestamp_s` 하나와 함께 온다. 스냅샷이 없거나 ASIL B 신호 오류가 있는 주기에는 기준 스냅샷(SWR-013)의 값을 쓴다. 예외로 충돌 판정(SWR-007, 008)은 현재 수신 스냅샷의 `crash_status`·`source_timestamp_s`를 쓴다. `가정` A-02
- **운전자 명령 시각**: 그 평가에서 쓰는 스냅샷(새 스냅샷 또는 기준 스냅샷)의 `source_timestamp_s`다(OEM-IF-004). `가정` A-02
- **`gear`**: 형식만 검사하고 판단에는 쓰지 않는다. `가정` A-11

### 1.3 출력

| 출력 | 값 | 인터페이스 |
|---|---|---|
| `lock_left`, `lock_right` | `LOCK` / `RELEASE` | OEM-IF-005 |
| `state` | `OFF` / `NORMAL` / `DEGRADED` / `FAULT` / `OVERRIDE` | OEM-IF-006 |
| `priority_reason` | `reason_code`에 1:1 대응하는 규칙 이름 (snake_case) | OEM-IF-006 |
| `reason_code` | `reason_left`와 `reason_right` 중 순위가 높은 것. 같으면 좌측 것 | OEM-IF-006 |
| `reason_left`, `reason_right` | 각 쪽 출력을 정한 규칙의 코드 | OEM-SR-002 "원인 기록" |
| `input_validity` | `VALID` / `INVALID` / `STALE` | OEM-IF-006 |
| `warning_code` | `W_SENSOR_FAULT` 또는 `NONE` | OEM-SR-004 |

`reason_left`, `reason_right`, `warning_code`는 OEM-IF-006에 없는 추가 필드다(Q-12).

**state 성립 조건**: 아래 조건 중 처음 성립하는 값을 `state`로 한다. 출력 결정과 별개다.

| state | 성립 조건 |
|---|---|
| `DEGRADED` | 순위 2 또는 순위 5가 성립 (입력 이상) |
| `FAULT` | 유효한 `sensor_fault=true` |
| `OFF` | 유효한 `ignition_on=false` |
| `OVERRIDE` | 한 쪽 이상에서 override가 활성 |
| `NORMAL` | 위에 해당 없음 (충돌 래치 중 포함) |

### 1.4 규칙 순위

| 순위 | 규칙 | 해당 쪽 출력 | reason_code (priority_reason) | 등급 | SWR |
|---|---|---|---|---|---|
| 1 | 충돌 래치 | 둘 다 `RELEASE` | `CRASH_CONFIRMED` (`crash_confirmed`) | ASIL B | SWR-007 |
| 2 | ASIL B 신호 오류 / 입력 지연 | 둘 다 직전 유지 | `INPUT_INVALID` / `INPUT_STALE` (`input_invalid` / `input_stale`) | ASIL B | SWR-013 |
| 3 | sensor fault | 둘 다 직전 유지 | `SENSOR_FAULT` (`sensor_fault`) | ASIL B | SWR-021 |
| 4 | 접근위험 / override (쪽별) | `LOCK` / override면 `RELEASE` | `APPROACH_RISK` / `DRIVER_OVERRIDE` (`approach_risk` / `driver_override`) | ASIL B | SWR-005, 006, 009 |
| 5 | QM 신호 오류 | 순위 1~4가 정하지 않은 쪽 직전 유지 | `INPUT_INVALID` (`input_invalid`) | QM | SWR-013 |
| 6 | 시동 OFF | `RELEASE` | `IGNITION_OFF` (`ignition_off`) | QM | SWR-020 |
| 7 | 화재 / 과온 / 성인 탑승 | `RELEASE` | `FIRE` / `OVERTEMPERATURE` / `ADULT_PRESENT` (`fire_detected` / `overtemperature_detected` / `adult_present`) | QM | SWR-017 |
| 8 | ISOFIX (쪽별) | `LOCK` | `ISOFIX` (`isofix`) | QM | SWR-018 |
| 9 | 자동 잠금 | `LOCK` | `AUTO_LOCK` (`auto_lock`) | QM | SWR-003 |
| 10 | 운전자 명령 (쪽별) | 명령대로 | `DRIVER_COMMAND` (`driver_command`) | QM | SWR-001, 002, 004 |
| 11 | 해당 없음 | 직전 유지 | `NO_CHANGE` (`no_change`) | — | SWR-019 |
| 필터 | 충돌 `PENDING` | 순위 8~10의 `RELEASE`→`LOCK` 전환을 막고 직전 유지 | `CRASH_PENDING` (`crash_pending`) — 이유 비교에서는 막은 규칙의 순위로 본다 | ASIL B | SWR-008 |

## 2. SW 요구사항

`ASIL` 열은 상위 OEM 요구사항에서 물려받는다. ASIL B와 QM 상위를 함께 가지면 ASIL B다. `검증` 열: UT = 단위 테스트(SWE.4), IT = 통합 테스트(SWE.5), ST = SW 검증(SWE.6, PC/SIL·Web).

### 2.1 실행 모델

| ID | ASIL | 요구사항 | 수용기준 | 검증 |
|---|---|---|---|---|
| SWR-022 | B | SW는 50 ms 주기마다 평가를 한 번 수행해야 한다. 새 스냅샷이 없는 주기에도 평가한다. 평가 시각은 외부에서 주입하며 직전 정상 평가 시각보다 커야 한다. 그렇지 않으면 그 평가는 ASIL B 입력 오류(순위 2, `INPUT_INVALID`)로 처리하고, 그 평가에서는 충돌 래치·PENDING 타이머·첫 억제·override·기준 스냅샷을 갱신하지 않는다(기존 래치는 유지). 직전 정상 평가 시각은 정상 평가에서만 갱신하므로, 시각이 다시 그 값보다 커지면 정상으로 돌아간다. 앞으로 크게 건너뛴 시각은 오류가 아니다(입력 지연은 SWR-013이 판정). 한 평가의 입력은 그 주기에 받은 스냅샷 0~1개와 운전자 명령 0개 이상이다. 한 주기에 스냅샷이 여러 개 오면 `crash_status`가 `"CONFIRMED"`인 것 중 마지막 것을, 없으면 마지막 것을 쓰고 나머지는 버린다. 명령은 받은 순서대로 모두 쓴다. `가정` A-01, A-25 | 스냅샷 없이 평가해도 결과가 나오고, 기준 스냅샷(SWR-013) 값으로 판정한다. 직전과 같거나 이전인 평가 시각은 `INPUT_INVALID`이고 그 평가에 `CONFIRMED`가 와도 래치가 서지 않는다. 이후 시각이 직전 정상 시각보다 커지면 정상 판정한다. 한 주기에 `CONFIRMED` 스냅샷 뒤 `NONE` 스냅샷이 와도 래치가 선다. 주입한 시각이 시간 판정(SWR-006, 007, 008, 013)에 그대로 쓰인다. | UT, IT |

### 2.2 운전자 명령 (OEM-FR-001)

| ID | ASIL | 요구사항 | 수용기준 | 검증 |
|---|---|---|---|---|
| SWR-001 | QM | SW는 네 가지 source(`physical_button`, `avn`, `voice`, `mobile_app`)의 운전자 명령을 같은 규칙으로 처리해야 한다. | 정지(0.0 km/h), 정상 입력에서 4 source × `lock`/`unlock` × `left`/`right`/`all` 24개 조합 각각이 SWR-002에 따른 출력을 만든다. | UT, ST |
| SWR-002 | QM | SW는 명령을 `side`가 가리키는 출력에만 적용해야 한다. `all`은 `left`와 `right` 명령 두 개로 나눈다. 한 평가에 같은 쪽 명령이 여러 개면 받은 순서대로 처리하고 마지막 명령이 남는다. `가정` A-13 | `left`는 `lock_left`만, `right`는 `lock_right`만, `all`은 둘 다 바뀌고 선택되지 않은 출력은 직전 값이다. 같은 평가에 `left lock`, `left unlock` 순이면 `RELEASE`다. | UT, ST |
| SWR-004 | QM | SW는 운전자 `unlock`을 `vehicle_speed_kph < 3.0`일 때만 적용해야 한다. `lock`은 차속과 관계없이 적용한다. 3.0 km/h 이상에서는 자동 잠금(SWR-003, 순위 9)이 먼저 적용되므로 이 조건은 SWR-019로 보장된다. `가정` A-05 | 2.9 km/h에서 `unlock`은 `RELEASE`를 만든다. 3.0 km/h 이상에서 `unlock`을 보내도 출력은 `LOCK`(`AUTO_LOCK`)이다. | UT, ST |

### 2.3 자동 잠금 (OEM-FR-002)

| ID | ASIL | 요구사항 | 수용기준 | 검증 |
|---|---|---|---|---|
| SWR-003 | QM | SW는 유효한 `vehicle_speed_kph`가 3.0 km/h 이상인 평가에서 좌·우 출력을 `LOCK`으로 해야 한다. 차속이 3.0 km/h 미만으로 내려가도 출력은 바꾸지 않는다. `가정` A-05 | 2.9 km/h에서는 자동 잠금이 없다. 3.0 km/h인 첫 평가에서 두 출력이 `LOCK`, `reason_code=AUTO_LOCK`이다. 이후 2.0 km/h가 되어도 `LOCK`이다. | UT, ST |

### 2.4 후측방 접근위험 (OEM-SR-002, OEM-FR-003)

| ID | ASIL | 요구사항 | 수용기준 | 검증 |
|---|---|---|---|---|
| SWR-005 | B | SW는 `rear_<side>_approach_risk`가 `true`인 쪽 출력을 `LOCK`으로 해야 한다. 그 쪽 `unlock`은 억제하고 `APPROACH_RISK`로 기록한다. 재입력 override는 SWR-006이 다룬다. | 위험 `true`가 된 평가에 해당 출력 `LOCK`, `reason_<side>=APPROACH_RISK`. 첫 `unlock`에도 `LOCK`이 유지된다. 시동 OFF, 화재·과온·성인, QM 신호 오류, 운전자 `unlock`이 같이 있어도 그 쪽은 `LOCK`이다. | UT, ST |
| SWR-006 | B | SW는 접근위험으로 `unlock`을 처음 억제한 평가 이후의 평가에서, 첫 억제 시각부터 10.0초 이하에 같은 쪽 `unlock`이 다시 오면 override로 그 쪽을 `RELEASE`해야 한다. `all`은 양쪽 재입력으로 본다. source는 달라도 된다. 같은 평가 안의 중복 `unlock`은 재입력으로 보지 않는다. 10.0초를 넘긴 재입력은 새로운 첫 억제다. override는 `vehicle_speed_kph < 3.0`일 때만 성립한다. override는 다음 중 하나가 일어나면 끝난다: 그 쪽 위험이 `false`가 됨, 차속 3.0 km/h 이상, 시동 OFF, 충돌 래치. 첫 억제는 차속 3.0 km/h 미만에서 억제한 `unlock`만 기록하고, 위 종료 조건이 일어나면 지운다. 순위 1~3이 적용된 평가의 `unlock`은 첫 억제나 재입력으로 세지 않는다. 시각은 명령 시각(1.2절, 쓰는 스냅샷의 `source_timestamp_s`)으로 잰다. `가정` A-06, A-13, A-24 | 첫 억제 후 10.0초에 재입력하면 `RELEASE`, `state=OVERRIDE`, `reason_<side>=DRIVER_OVERRIDE`. 10.05초에 재입력하면 다시 억제된다. 한 평가에 `unlock`이 두 번 와도 override가 아니다. 3.0 km/h에서 10초 안에 재입력해도 override가 아니고 `LOCK`이다. override 중 차속이 3.0 km/h가 되면 그 쪽이 `LOCK`이다. sensor fault 중 받은 `unlock` 뒤, 복귀 후 `unlock` 한 번으로는 override가 되지 않는다. | UT, ST |
| SWR-009 | B | SW는 SWR-005, SWR-006을 좌·우 독립으로 수행해야 한다. | 좌측만 위험 `true`이면 `lock_right`는 영향받지 않는다. 좌측 override가 우측 억제를 풀지 않는다. 좌 override와 우 ISOFIX가 같은 평가에 있으면 좌 `RELEASE`(`DRIVER_OVERRIDE`), 우 `LOCK`(`ISOFIX`), `reason_code=DRIVER_OVERRIDE`다. | UT, ST |

### 2.5 충돌 (OEM-SR-001)

| ID | ASIL | 요구사항 | 수용기준 | 검증 |
|---|---|---|---|---|
| SWR-007 | B | SW는 형식이 유효하고 나이(평가 시각 − `source_timestamp_s`)가 1.0초 이하인 스냅샷에서 `crash_status=CONFIRMED`를 받으면 충돌 래치를 세워야 한다. 래치가 서 있는 동안에는 다른 모든 규칙보다 우선해 좌·우 출력을 `RELEASE`한다. 이 판정은 `crash_status`와 `source_timestamp_s`만 유효하면 수행하고, 다른 신호의 오류나 0.200초 초과 지연과는 무관하다. 충돌 판정의 타임스탬프 유효성에는 역행 검사(SWR-013)를 적용하지 않는다. 늦게 도착한 `CONFIRMED`도 나이가 1.0초 이하이면 처리한다. 래치는 그 주기에 새로 받은 스냅샷에서 `crash_status`, `ignition_on`, `source_timestamp_s`가 유효하고 `ignition_on=false`, `crash_status`가 `CONFIRMED`가 아닐 때만 해제한다. 스냅샷 없는 주기에 직전 값을 다시 써서 해제하지 않는다. `가정` A-03, A-14 | 나이 0.200초 이하인 `CONFIRMED` 스냅샷에 대해: 출력 `RELEASE` 평가 시각 − 그 스냅샷의 `source_timestamp_s` ≤ 0.300초. 이후 `NONE`이 와도, 접근위험·ISOFIX·자동잠금·운전자 `lock`·sensor fault·다른 신호 오류가 있어도 `RELEASE`가 유지된다. 나이 1.05초인 `CONFIRMED`로는 래치가 서지 않는다. 시동 OFF 스냅샷 뒤 다시 시동 ON이 되면 래치가 풀려 있다. | UT, ST |
| SWR-008 | B | SW는 `crash_status=PENDING`인 동안 순위 8~10(ISOFIX, 자동 잠금, 운전자 `lock`)에 의한 `RELEASE`→`LOCK` 전환을 막아야 한다. 막은 쪽의 이유는 `CRASH_PENDING`이다. 순위 1~7의 결과와 `RELEASE` 방향 결과는 막지 않는다. `PENDING`이 2.0초를 넘게 이어지면 그 뒤로는 막지 않는다. 2.0초는 평가 시각으로, 유효한 `crash_status=PENDING`을 처음 받은 평가부터 잰다. 유효한 `NONE`/`CONFIRMED`를 받으면 타이머를 지운다. 스냅샷 없는 주기와 다른 신호 오류는 타이머에 영향을 주지 않는다. `가정` A-04, A-23 | `PENDING` 중 3.0 km/h, ISOFIX `true`, 운전자 `lock`이 와도 `RELEASE`가 유지되고 `reason_<side>=CRASH_PENDING`. `PENDING` 중 접근위험 `true`이면 그 쪽은 `LOCK`. `PENDING` 중 화재 `true`이면 `RELEASE`. `PENDING`이 시작된 지 2.0초 이하에서는 막고, 2.05초에서는 자동 잠금이 적용된다. `PENDING`→`NONE`이면 막힘이 풀린다. | UT, ST |

### 2.6 입력 유효성과 고장 (OEM-SR-003, OEM-SR-004)

| ID | ASIL | 요구사항 | 수용기준 | 검증 |
|---|---|---|---|---|
| SWR-013 | B | SW는 평가 전에 스냅샷의 신호마다 누락, 형식, 범위, 미등록 enum을 검사해야 한다. `source_timestamp_s`가 평가 시각보다 0.050초 넘게 미래이거나 기준 스냅샷보다 작으면 형식 오류다. 처리는 오류 난 신호의 등급(1.2절)에 따른다. **기준 스냅샷**은 ASIL B 신호(타임스탬프 포함)가 모두 유효한 마지막 스냅샷이다. ① ASIL B 신호 오류이거나, 평가 시각 − 기준 스냅샷의 `source_timestamp_s` > 0.200초이면 순위 2다. 둘 다 직전 유지, `input_validity=INVALID`/`STALE`. 시작 후 첫 기준 스냅샷 전에도 `STALE`이다. ② 쓰는 스냅샷에 QM 신호 오류만 있으면 순위 5다. 순위 1~4는 그대로 적용하고, 나머지 쪽은 직전 유지, `input_validity=INVALID`. ③ ASIL B 신호 오류가 있는 스냅샷은 기준 스냅샷이 되지 않는다. QM 신호 오류만 있는 스냅샷은 기준 스냅샷이 되며, 그 QM 오류는 다음 기준 스냅샷까지 순위 5로 처리한다(SWE2 검토 AR-02). ④ 다음 유효·최신 스냅샷에서 지연 없이 정상 판정으로 돌아간다. ⑤ 운전자 명령에 오류가 있으면 그 명령만 버린다. ⑥ 순위 1이 적용되는 쪽의 이유는 `CRASH_CONFIRMED`다(SWR-019). `가정` A-07, A-15, A-21, A-22 | 마지막 갱신 후 0.200초 이하에는 정상이다. 0.200초를 넘긴 첫 평가에서 `DEGRADED`이고, 이 평가는 마지막 갱신 후 0.300초 이내다(OEM: 200 ms 초과 후 100 ms 이내). 다음은 각각 `INVALID`다: 300.1 km/h, `crash_status="UNKNOWN"`, 불리언 자리의 `1`, 필드 누락, 0.051초 미래 타임스탬프, 역행 타임스탬프. 0.050초 미래는 정상이다. `isofix_left=1`이면서 좌측 접근위험 `true`이면 좌측 `LOCK`(`APPROACH_RISK`), 우측 직전 유지(`INPUT_INVALID`), `state=DEGRADED`다. `gear` 오류만 있는 스냅샷이 0.5초 동안 이어져도 `STALE`이 되지 않고, 그 사이 접근위험 `true`가 오면 그 쪽은 `LOCK`이다. | UT, ST |
| SWR-021 | B | SW는 유효한 스냅샷의 `sensor_fault`가 `true`이면 새 규칙을 적용하지 않고 직전 출력을 유지해야 한다. 이때 `warning_code=W_SENSOR_FAULT`로 하고, `state`는 1.3절 성립 조건에 따른다(다른 입력 이상이 없으면 `FAULT`). 충돌 래치(순위 1)와 ASIL B 입력 이상(순위 2)만 예외로 우선한다. `sensor_fault`가 `false`가 된 평가부터 정상 판정한다. `가정` A-16 | `sensor_fault=true`인 첫 평가에서 좌·우 출력이 유지되고 `state=FAULT`, `warning_code=W_SENSOR_FAULT`. 같은 평가에 접근위험, 시동 OFF, 운전자 명령, 자동 잠금 조건이 있어도 출력이 바뀌지 않는다. | UT, ST |

### 2.7 시동 OFF (OEM-FR-007)

| ID | ASIL | 요구사항 | 수용기준 | 검증 |
|---|---|---|---|---|
| SWR-020 | QM | SW는 `ignition_on=false`인 평가에서 좌·우 출력을 `RELEASE`, `reason_code=IGNITION_OFF`로 해야 한다. `state`는 1.3절 성립 조건에 따른다(입력 이상·sensor fault가 없으면 `OFF`). 순위 1~5가 정한 쪽은 예외로 그 규칙을 따른다(P-1). 충돌 래치 해제는 SWR-007이 정한다. `가정` A-08 | 다른 조건이 없으면 `ignition_on=false` 첫 평가에 두 출력 `RELEASE`, `state=OFF`. 좌측 접근위험 `true`이면 `lock_left=LOCK`, `lock_right=RELEASE`, `state=OFF`. | UT, ST |

### 2.8 강제 해제·잠금 (OEM-FR-005, OEM-FR-006)

| ID | ASIL | 요구사항 | 수용기준 | 검증 |
|---|---|---|---|---|
| SWR-017 | QM | SW는 `fire_detected`, `overtemperature_detected`, `adult_present` 중 하나라도 `true`이면 좌·우 출력을 `RELEASE`해야 한다. 순위 1~6이 정한 쪽은 예외다(P-1). 여러 개가 `true`이면 화재 > 과온 > 성인 순으로 이유를 정한다. 입력이 `false`로 돌아간 뒤에는 이 규칙이 적용되지 않는다. 다른 규칙도 해당하지 않으면 출력은 `RELEASE`로 남는다(`NO_CHANGE`). `가정` A-08, A-17 | 각 입력을 단독으로 `true`로 하면 그 평가에 두 출력이 `RELEASE`, 이유는 각각 `FIRE`/`OVERTEMPERATURE`/`ADULT_PRESENT`. ISOFIX `true`여도 해제된다. 좌측 접근위험 `true`이면 좌측은 `LOCK`이다. 입력이 `false`로 돌아간 평가에서 ISOFIX `true`이면 그 쪽은 `LOCK`이 된다. | UT, ST |
| SWR-018 | QM | SW는 `isofix_<side>`가 `true`인 쪽 출력을 `LOCK`으로 해야 한다. 반대쪽은 바꾸지 않는다. ISOFIX가 `false`가 되어도 출력은 유지한다. `가정` A-18 | `isofix_left`만 `true`이면 그 평가에 `lock_left=LOCK`, `lock_right`는 직전 값. 이후 `false`가 되어도 `lock_left=LOCK`이다. | UT, ST |

### 2.9 우선순위 (여러 OEM 요구사항에서 파생)

| ID | ASIL | 요구사항 | 수용기준 | 검증 |
|---|---|---|---|---|
| SWR-019 | B | SW는 한 평가에 여러 규칙이 해당하면 1.4절의 순위에 따라 쪽별로 출력과 이유를 정해야 한다. 순위 1이 가장 높다. 한 쪽에 높은 순위 규칙이 적용되면 그 쪽에는 낮은 순위 규칙을 적용하지 않는다. `PENDING` 필터는 순위 8~10의 결과에만 적용한다. `reason_code`, `state`는 1.3절 규칙으로 정한다. `가정` A-08 | 부록 A의 결정표 D-01~D-45(순위 1~10의 모든 쌍)와 P-01~P-10(`PENDING`과 각 순위)의 출력, `reason_code`, `state`가 그대로 나온다. 쪽별 혼합은 SWR-009, SWR-013 수용기준으로 확인한다. | UT, ST |

### 2.10 표시 인터페이스 (OEM-FR-004)

| ID | ASIL | 요구사항 | 수용기준 | 검증 |
|---|---|---|---|---|
| SWR-014 | QM | SW는 상태 조회에 `lock_left`, `lock_right`, `state`, `priority_reason`, `reason_code`, `input_validity`, `reason_left`, `reason_right`, `warning_code`를 제공해야 한다. | 상태 조회 응답에 아홉 필드가 모두 있고 값이 마지막 평가 결과와 같다. | UT, IT, ST |
| SWR-015 | QM | SW는 상태 조회, 이벤트 조회, 시뮬레이터 입력을 HTTP(JSON) 인터페이스로 제공해야 한다. JSON 구문 오류만 HTTP 422로 거절하고, 필드의 누락·형식·범위 검사는 SWR-013 평가 경로로 넘긴다. 응답 직렬화에 실패하면 HTTP 500을 반환한다. `가정` A-19 | `GET /status`가 200과 SWR-014의 JSON을 반환한다. 입력 제출(`POST /input`)은 접수만 하고 평가는 다음 주기에 하므로 202(Accepted)를 반환한다. 범위를 벗어난 값을 보내면 202이고 평가 결과는 `DEGRADED`/`INVALID`다. 깨진 JSON은 422다. 직렬화 실패를 주입하면 500이다. | IT, ST |

### 2.11 결정론 (OEM-NFR-001)

| ID | ASIL | 요구사항 | 수용기준 | 검증 |
|---|---|---|---|---|
| SWR-016 | QM | SW는 같은 초기 상태와 같은 입력 순서(시각 포함)에 대해 같은 공개 결과를 만들어야 한다. 공개 결과 해시는 평가 결과 목록(SWR-014의 아홉 필드)을 키 정렬 JSON으로 직렬화해 SHA-256으로 계산한다. `가정` A-09 | 고정 시계로 같은 입력 벡터를 1,000회 재생하면 해시 1,000개가 모두 같다. | IT, ST |

### 2.12 이벤트 기록 (OEM-NFR-002)

| ID | ASIL | 요구사항 | 수용기준 | 검증 |
|---|---|---|---|---|
| SWR-010 | QM | SW는 **제어결정**을 기록해야 한다. 제어결정은 다음 평가를 말한다: 첫 평가, 운전자 명령을 받은 평가, 공개 결과(SWR-014 필드)가 직전 기록과 달라진 평가. 기록마다 프로세스 안에서 1부터 1씩 증가하는 `event_id`를 붙인다. `가정` A-10 | 같은 결과가 이어지는 평가 10회는 1건만 기록된다. 운전자 명령 평가는 결과가 같아도 기록된다. `event_id`는 1, 2, 3… 순이다. | UT |
| SWR-011 | QM | 이벤트는 `event_id`, `timestamp_s`(평가 시각), `lock_left`, `lock_right`, `state`, `priority_reason`, `reason_code`, `reason_left`, `reason_right`, `input_validity`, `warning_code`만 가져야 한다. 영상, 음성, 개인 식별자, 원시 입력값을 저장하지 않는다. `가정` A-10 | 조회한 이벤트의 키 집합이 위 11개와 정확히 같다. | UT, IT |
| SWR-012 | QM | SW는 최근 이벤트 100건만 메모리에 보존하고 오래된 순으로 조회할 수 있어야 한다. 파일·DB에 저장하지 않는다. | 101건 기록 후 조회하면 `event_id` 2~101이 순서대로 나온다. 프로세스를 다시 시작하면 0건이다. | UT, IT |

## 3. 가정 목록

| ID | 가정 | 관련 SWR | 질의 |
|---|---|---|---|
| A-01 | 평가주기 50 ms, 스냅샷이 없어도 주기마다 평가 | SWR-022 | Q-02 |
| A-02 | 차량 신호는 스냅샷 하나에 타임스탬프 하나. 스냅샷 없는 주기와 ASIL B 신호 오류 주기는 기준 스냅샷 값 사용(충돌 판정은 현재 수신 스냅샷). 명령 시각은 쓰는 스냅샷의 타임스탬프 | SWR-006, 013, 022 | Q-05 |
| A-03 | 충돌 `CONFIRMED`는 시동 OFF(유효 스냅샷, `CONFIRMED` 아님)까지 래치 | SWR-007 | Q-04 |
| A-04 | 충돌 `PENDING`은 순위 8~10의 잠금 전환만 막음 | SWR-008 | Q-04 |
| A-05 | 운전자 `unlock`과 override는 3.0 km/h 미만에서만, 자동 잠금 출력은 차속이 내려가도 유지 | SWR-003, 004 | Q-07 |
| A-06 | override는 이후 평가의 같은 쪽 재입력(`all` 포함, source 무관). 위험 해소, 3.0 km/h 도달, 시동 OFF, 충돌 래치 중 하나로 종료 | SWR-006 | Q-08 |
| A-07 | 입력 이상 시 직전 출력 유지, `DEGRADED`. 복귀는 디바운스 없이 즉시 | SWR-013 | Q-05 |
| A-08 | ASIL B 규칙을 모두 QM 규칙보다 위에 두는 순위 표. 시동 OFF와 화재·과온·성인 해제도 접근위험 잠금을 이기지 못함 | SWR-017, 019, 020 | Q-01 |
| A-09 | 공개 결과 해시 정의 | SWR-016 | Q-09 |
| A-10 | 제어결정의 정의(첫 평가, 명령 평가, 결과 변화)와 이벤트 필드 11개 | SWR-010, 011 | Q-11 |
| A-11 | `gear`는 형식만 검사 | SWR-013 | Q-06 |
| A-12 | 불리언은 `true`/`false`만, 타임스탬프는 0.0 이상 | SWR-013 | Q-05 |
| A-13 | `all`은 좌·우 명령 두 개. 같은 쪽 여러 명령은 받은 순서대로, 마지막이 남음. 같은 평가 안 중복은 재입력 아님 | SWR-002, 006 | Q-08 |
| A-14 | `CONFIRMED`는 나이 1.0초 이하면 다른 신호 오류·0.200초 초과 지연과 무관하게 처리 | SWR-007 | Q-04 |
| A-15 | 시작 후 첫 유효 스냅샷 전에는 `STALE`, 출력은 초기 `RELEASE` | SWR-013 | Q-05 |
| A-16 | sensor fault 중에도 충돌 래치와 ASIL B 입력 이상이 우선. 복귀는 `sensor_fault=false` 평가부터 | SWR-021 | Q-01c, Q-01f |
| A-17 | 강제 해제 입력이 `false`로 돌아가면 규칙 미적용, 다른 규칙이 없으면 `RELEASE` 유지 | SWR-017 | Q-01e |
| A-18 | ISOFIX가 `false`가 되어도 잠금 유지 | SWR-018 | Q-13 |
| A-19 | HTTP는 JSON 구문 오류만 422, 내용 검사는 SWR-013 경로 | SWR-015 | — (공급자 설계 결정) |
| A-20 | override 판단(SWR-006)은 ASIL B로 개발 (DEC-07) | SWR-006 | Q-03 |
| A-21 | 신호 등급 분류(1.2절). QM 신호 오류는 ASIL B 규칙을 막지 않음 | SWR-013 | Q-05 |
| A-22 | 미래 타임스탬프 허용 오차 0.050초 | SWR-013 | Q-05 |
| A-23 | `PENDING` 필터 최대 지속 2.0초 | SWR-008 | Q-04 |
| A-24 | 첫 억제는 3.0 km/h 미만에서만 기록, 순위 1~3 평가의 명령은 override 계수에서 제외 | SWR-006 | Q-08 |
| A-25 | 평가 시각 역행 시 그 평가의 상태 갱신 생략·복귀 규칙, 한 주기 다중 스냅샷은 `CONFIRMED` 우선 후 최신 | SWR-022 | Q-02 |

## 부록 A. SWR-019 결정표

### A.1 규칙 쌍 (D-01~D-45)

두 규칙이 같은 평가, 같은 쪽에 해당할 때의 결과다. "ASIL B 입력 이상"(순위 2)에는 평가 시각 오류(SWR-022)도 포함되며 결과는 같다. 두 규칙의 조건 외에는 기본값이다(차속 0.0 km/h, 시동 ON, 모든 신호 유효·최신, 직전 출력은 결과와 반대 값). "직전 유지"는 그 평가 전 출력이 그대로 남는다는 뜻이다. `state`는 1.3절 성립 조건으로 정한다. 대표 조건으로 화재(순위 7)와 `unlock`(순위 10)을 쓴다.

| # | 상위 규칙 (순위) | 하위 규칙 (순위) | 해당 쪽 출력 | reason_code | state |
|---|---|---|---|---|---|
| D-01 | 충돌 래치 (1): `crash_status=CONFIRMED` (래치) | ASIL B 입력 이상 (2): ASIL B 신호 오류 또는 지연 | RELEASE | CRASH_CONFIRMED | DEGRADED |
| D-02 | 충돌 래치 (1): `crash_status=CONFIRMED` (래치) | sensor fault (3): `sensor_fault=true` | RELEASE | CRASH_CONFIRMED | FAULT |
| D-03 | 충돌 래치 (1): `crash_status=CONFIRMED` (래치) | 접근위험 (4): 해당 쪽 `approach_risk=true` (override 없음) | RELEASE | CRASH_CONFIRMED | NORMAL |
| D-04 | 충돌 래치 (1): `crash_status=CONFIRMED` (래치) | QM 입력 이상 (5): QM 신호 오류 | RELEASE | CRASH_CONFIRMED | DEGRADED |
| D-05 | 충돌 래치 (1): `crash_status=CONFIRMED` (래치) | 시동 OFF (6): `ignition_on=false` | RELEASE | CRASH_CONFIRMED | OFF |
| D-06 | 충돌 래치 (1): `crash_status=CONFIRMED` (래치) | 강제 해제 (7): `fire_detected=true` | RELEASE | CRASH_CONFIRMED | NORMAL |
| D-07 | 충돌 래치 (1): `crash_status=CONFIRMED` (래치) | ISOFIX (8): 해당 쪽 `isofix=true` | RELEASE | CRASH_CONFIRMED | NORMAL |
| D-08 | 충돌 래치 (1): `crash_status=CONFIRMED` (래치) | 자동 잠금 (9): `vehicle_speed_kph=3.0` | RELEASE | CRASH_CONFIRMED | NORMAL |
| D-09 | 충돌 래치 (1): `crash_status=CONFIRMED` (래치) | 운전자 명령 (10): 해당 쪽 `unlock` | RELEASE | CRASH_CONFIRMED | NORMAL |
| D-10 | ASIL B 입력 이상 (2): ASIL B 신호 오류 또는 지연 | sensor fault (3): `sensor_fault=true` | 직전 유지 | INPUT_INVALID / INPUT_STALE | DEGRADED |
| D-11 | ASIL B 입력 이상 (2): ASIL B 신호 오류 또는 지연 | 접근위험 (4): 해당 쪽 `approach_risk=true` (override 없음) | 직전 유지 | INPUT_INVALID / INPUT_STALE | DEGRADED |
| D-12 | ASIL B 입력 이상 (2): ASIL B 신호 오류 또는 지연 | QM 입력 이상 (5): QM 신호 오류 | 직전 유지 | INPUT_INVALID / INPUT_STALE | DEGRADED |
| D-13 | ASIL B 입력 이상 (2): ASIL B 신호 오류 또는 지연 | 시동 OFF (6): `ignition_on=false` | 직전 유지 | INPUT_INVALID / INPUT_STALE | DEGRADED |
| D-14 | ASIL B 입력 이상 (2): ASIL B 신호 오류 또는 지연 | 강제 해제 (7): `fire_detected=true` | 직전 유지 | INPUT_INVALID / INPUT_STALE | DEGRADED |
| D-15 | ASIL B 입력 이상 (2): ASIL B 신호 오류 또는 지연 | ISOFIX (8): 해당 쪽 `isofix=true` | 직전 유지 | INPUT_INVALID / INPUT_STALE | DEGRADED |
| D-16 | ASIL B 입력 이상 (2): ASIL B 신호 오류 또는 지연 | 자동 잠금 (9): `vehicle_speed_kph=3.0` | 직전 유지 | INPUT_INVALID / INPUT_STALE | DEGRADED |
| D-17 | ASIL B 입력 이상 (2): ASIL B 신호 오류 또는 지연 | 운전자 명령 (10): 해당 쪽 `unlock` | 직전 유지 | INPUT_INVALID / INPUT_STALE | DEGRADED |
| D-18 | sensor fault (3): `sensor_fault=true` | 접근위험 (4): 해당 쪽 `approach_risk=true` (override 없음) | 직전 유지 | SENSOR_FAULT | FAULT |
| D-19 | sensor fault (3): `sensor_fault=true` | QM 입력 이상 (5): QM 신호 오류 | 직전 유지 | SENSOR_FAULT | DEGRADED |
| D-20 | sensor fault (3): `sensor_fault=true` | 시동 OFF (6): `ignition_on=false` | 직전 유지 | SENSOR_FAULT | FAULT |
| D-21 | sensor fault (3): `sensor_fault=true` | 강제 해제 (7): `fire_detected=true` | 직전 유지 | SENSOR_FAULT | FAULT |
| D-22 | sensor fault (3): `sensor_fault=true` | ISOFIX (8): 해당 쪽 `isofix=true` | 직전 유지 | SENSOR_FAULT | FAULT |
| D-23 | sensor fault (3): `sensor_fault=true` | 자동 잠금 (9): `vehicle_speed_kph=3.0` | 직전 유지 | SENSOR_FAULT | FAULT |
| D-24 | sensor fault (3): `sensor_fault=true` | 운전자 명령 (10): 해당 쪽 `unlock` | 직전 유지 | SENSOR_FAULT | FAULT |
| D-25 | 접근위험 (4): 해당 쪽 `approach_risk=true` (override 없음) | QM 입력 이상 (5): QM 신호 오류 | LOCK | APPROACH_RISK | DEGRADED |
| D-26 | 접근위험 (4): 해당 쪽 `approach_risk=true` (override 없음) | 시동 OFF (6): `ignition_on=false` | LOCK | APPROACH_RISK | OFF |
| D-27 | 접근위험 (4): 해당 쪽 `approach_risk=true` (override 없음) | 강제 해제 (7): `fire_detected=true` | LOCK | APPROACH_RISK | NORMAL |
| D-28 | 접근위험 (4): 해당 쪽 `approach_risk=true` (override 없음) | ISOFIX (8): 해당 쪽 `isofix=true` | LOCK | APPROACH_RISK | NORMAL |
| D-29 | 접근위험 (4): 해당 쪽 `approach_risk=true` (override 없음) | 자동 잠금 (9): `vehicle_speed_kph=3.0` | LOCK | APPROACH_RISK | NORMAL |
| D-30 | 접근위험 (4): 해당 쪽 `approach_risk=true` (override 없음) | 운전자 명령 (10): 해당 쪽 `unlock` | LOCK | APPROACH_RISK | NORMAL |
| D-31 | QM 입력 이상 (5): QM 신호 오류 | 시동 OFF (6): `ignition_on=false` | 직전 유지 | INPUT_INVALID | DEGRADED |
| D-32 | QM 입력 이상 (5): QM 신호 오류 | 강제 해제 (7): `fire_detected=true` | 직전 유지 | INPUT_INVALID | DEGRADED |
| D-33 | QM 입력 이상 (5): QM 신호 오류 | ISOFIX (8): 해당 쪽 `isofix=true` | 직전 유지 | INPUT_INVALID | DEGRADED |
| D-34 | QM 입력 이상 (5): QM 신호 오류 | 자동 잠금 (9): `vehicle_speed_kph=3.0` | 직전 유지 | INPUT_INVALID | DEGRADED |
| D-35 | QM 입력 이상 (5): QM 신호 오류 | 운전자 명령 (10): 해당 쪽 `unlock` | 직전 유지 | INPUT_INVALID | DEGRADED |
| D-36 | 시동 OFF (6): `ignition_on=false` | 강제 해제 (7): `fire_detected=true` | RELEASE | IGNITION_OFF | OFF |
| D-37 | 시동 OFF (6): `ignition_on=false` | ISOFIX (8): 해당 쪽 `isofix=true` | RELEASE | IGNITION_OFF | OFF |
| D-38 | 시동 OFF (6): `ignition_on=false` | 자동 잠금 (9): `vehicle_speed_kph=3.0` | RELEASE | IGNITION_OFF | OFF |
| D-39 | 시동 OFF (6): `ignition_on=false` | 운전자 명령 (10): 해당 쪽 `unlock` | RELEASE | IGNITION_OFF | OFF |
| D-40 | 강제 해제 (7): `fire_detected=true` | ISOFIX (8): 해당 쪽 `isofix=true` | RELEASE | FIRE | NORMAL |
| D-41 | 강제 해제 (7): `fire_detected=true` | 자동 잠금 (9): `vehicle_speed_kph=3.0` | RELEASE | FIRE | NORMAL |
| D-42 | 강제 해제 (7): `fire_detected=true` | 운전자 명령 (10): 해당 쪽 `unlock` | RELEASE | FIRE | NORMAL |
| D-43 | ISOFIX (8): 해당 쪽 `isofix=true` | 자동 잠금 (9): `vehicle_speed_kph=3.0` | LOCK | ISOFIX | NORMAL |
| D-44 | ISOFIX (8): 해당 쪽 `isofix=true` | 운전자 명령 (10): 해당 쪽 `unlock` | LOCK | ISOFIX | NORMAL |
| D-45 | 자동 잠금 (9): `vehicle_speed_kph=3.0` | 운전자 명령 (10): 해당 쪽 `unlock` | LOCK | AUTO_LOCK | NORMAL |

### A.2 `PENDING` 필터 (P-01~P-10)

`crash_status=PENDING`(시작 후 2.0초 이하)과 각 순위 규칙이 같은 평가, 같은 쪽에 해당할 때의 결과다. 직전 출력은 `RELEASE`다(P-01은 이미 래치된 경우).

| # | 함께 해당하는 규칙 (순위) | 해당 쪽 출력 | reason_code | state |
|---|---|---|---|---|
| P-01 | 충돌 래치 (1) | RELEASE | CRASH_CONFIRMED | NORMAL |
| P-02 | ASIL B 입력 이상 (2) | 직전 유지 | INPUT_INVALID / INPUT_STALE | DEGRADED |
| P-03 | sensor fault (3) | 직전 유지 | SENSOR_FAULT | FAULT |
| P-04 | 접근위험 (4) | LOCK | APPROACH_RISK | NORMAL |
| P-05 | QM 입력 이상 (5) | 직전 유지 | INPUT_INVALID | DEGRADED |
| P-06 | 시동 OFF (6) | RELEASE | IGNITION_OFF | OFF |
| P-07 | 화재 (7) | RELEASE | FIRE | NORMAL |
| P-08 | ISOFIX (8) | 직전 유지 (RELEASE) | CRASH_PENDING | NORMAL |
| P-09 | 자동 잠금 (9) | 직전 유지 (RELEASE) | CRASH_PENDING | NORMAL |
| P-10 | 운전자 `lock` (10) | 직전 유지 (RELEASE) | CRASH_PENDING | NORMAL |

`PENDING` 중 운전자 `unlock`은 `RELEASE` 방향이므로 막지 않는다.
