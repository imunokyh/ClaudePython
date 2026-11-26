# 통합 테스트 명세 — 전자식 차일드락 제어 SW

| 항목 | 내용 |
|---|---|
| 문서 ID | SWE5-ITS |
| 베이스라인 | BL-INT-1.0 (G3 제출 대상) |
| 상위 입력 | SWE2-ARC 1.0 (컴포넌트·인터페이스·동적 구조·자원 예산), SWE1-SRS 1.2 |
| A-SPICE | SWE.5 Software Integration and Integration Test |
| 시험 환경 | PC/SIL: Python 3.12, Windows 11, Jenkins Built-In 노드 (`ClaudePython-CI`) |
| 자동화 | `tests/integration/` (pytest, CI에서 매 빌드 실행) |

## 1. 통합 전략

상향식으로 통합한다. 각 단계는 앞 단계가 단위 테스트를 통과한 뒤 수행한다.

| 단계 | 통합 대상 | 확인 대상 인터페이스 |
|---|---|---|
| I-1 | `safety.*` + `types` | `SnapshotCheck`, `UsedSnapshot`, `CrashView`, `SideProposal` (단위 테스트 `tests/unit/test_decision_table.py`에서 controller를 통해 확인) |
| I-2 | I-1 + `qm.rules` + `qm.event_log` + `controller` | `Decision`, QM 제안, 이벤트 기록 |
| I-3 | I-2 + `runtime.runner` + `runtime.clock` | 우편함, 주기 평가, 시각 공급 |
| I-4 | I-3 + `web.app` (HTTP) | `POST /input`, `GET /status`, `GET /events`, `GET /clock` |

## 2. 통합 테스트 케이스

| ID | 목적 | 통합 단계 | 절차 요약 | 합격 기준 | 근거 |
|---|---|---|---|---|---|
| IT-01 | HTTP 입력부터 출력까지 주행 시나리오가 전 구간을 통과 | I-4 | 시뮬레이터 순서(정차 → 주행 3 km/h → 정차 → 운전자 해제)로 `POST /input`과 `tick`을 반복 | `GET /status`가 단계마다 `RELEASE` → `LOCK`(`AUTO_LOCK`) → `LOCK` 유지 → `RELEASE`(`DRIVER_COMMAND`) | ARC 3장, SWR-001, 003, 004 |
| IT-02 | 충돌 긴급 해제가 HTTP 경로에서 300 ms 안에 반영 | I-4 | 주행 중 `CONFIRMED` 스냅샷 제출 → 다음 tick | 다음 평가(≤ 50 ms)에 양쪽 `RELEASE`, `CRASH_CONFIRMED`, 이후 `NONE`·ISOFIX에도 유지 | SWR-007, ARC 2.4 |
| IT-03 | 접근위험 억제와 override가 HTTP 명령 경로로 동작 | I-4 | 좌측 위험 + 해제 명령 2회(다음 평가) | 첫 명령 후 `LOCK`(`APPROACH_RISK`), 두 번째 후 `RELEASE`, `state=OVERRIDE` | SWR-005, 006 |
| IT-04 | 입력이 끊기면 주기 평가가 지연을 판정 | I-3 | 스냅샷 1회 후 제출 없이 tick 반복 | 0.200초 이하 `VALID`, 처음 넘는 tick에서 `STALE`/`DEGRADED`, 출력 유지 | SWR-013, 022, ARC AR-01 |
| IT-05 | 형식 오류 입력이 HTTP 200대로 받아져 평가에서 `INVALID` | I-4 | 범위 밖 차속, 깨진 JSON | 범위 밖은 202 후 `INVALID`, 깨진 JSON은 422이고 평가 상태 불변 | SWR-015, 013 |
| IT-06 | 결정론: 같은 입력 벡터 1,000회 재생의 공개 결과 해시가 같음 | I-3 | `ScriptedClock`으로 120주기 시나리오를 새 runner로 1,000회 재생, `decision_hash` 비교 | 해시 1,000개가 모두 같음 | SWR-016, A-09 |
| IT-07 | 이벤트 기록이 101건 이상에서 최근 100건만 HTTP로 조회 | I-4 | 결과가 바뀌는 평가 150회 | `GET /events`가 100건, `event_id` 51~150 순서, 키 11개 | SWR-010~012 |
| IT-08 | 평가 1회 실행 시간 예산 | I-3 | 다양한 입력으로 10,000회 `tick`, GC 포함 최댓값 측정 | 최댓값 ≤ 5 ms | ARC 7장 |
| IT-09 | 메모리 상한 | I-3 | 10,000회 평가 전후 `tracemalloc` 비교 | 증가량 ≤ 1 MiB, 이벤트 100건 이하 | ARC 7장 |
| IT-10 | 주기 스레드 동작 중 동시 HTTP 요청 | I-4 | 실시간 runner(10 ms 주기) 동작 중 4개 스레드에서 입력·조회 각 100회 | 모든 응답 2xx, `evaluation_errors=0`, 상태 조회 일관 | ARC 2.4 실행 순서, AR-13 |
| IT-11 | QM 규칙 예외가 HTTP 경로 전체에서 격리 | I-4 | `qm.rules.proposals`가 예외를 내도록 바꾼 뒤 접근위험·충돌 입력 | ASIL B 결과(`APPROACH_RISK`, `CRASH_CONFIRMED`)는 정상, HTTP 200 | ARC 2.4 예외 전파 |

## 3. 판정과 기록

- 결과는 Jenkins 빌드(JUnit 보고서 `reports/junit.xml`)로 남는다. 통합 테스트 결과서(`integration-test-report.md`)에 빌드 번호와 커밋을 기록한다.
- 실패는 결함으로 등록하고, 수정 커밋과 재시험 빌드를 결과서에 연결한다.
