# 개발 계획서 — 전자식 차일드락 제어 SW

| 항목 | 내용 |
|---|---|
| 입력 문서 | OEM-SWR-001 OEM SW 요구사항 사양서 Rev 1.0 (BL-OEM-1.0) |
| 대상 | 후석 좌·우 전자식 차일드락 잠금/해제 판단 로직 (Python 3.12 PC/SIL, Web 시뮬레이터) |
| 범위 밖 | HIL, 실차, 타깃 ECU, 시스템/HW 개발, HARA, 공식 심사·인증 |
| 개발 절차 | CLAUDE.md "개발 절차" (A-SPICE SWE.1~SWE.6, TDD) |

OEM 입력 문서는 교육용 저작물(과정 밖 배포 금지)이므로 저장소에 커밋하지 않는다(`.gitignore`의 `OEM/`). 산출물에는 요구사항 ID와 필요한 요지만 인용한다.

## 1. 단계와 인도 게이트

| 단계 | 브랜치 | 주요 산출물 (`docs/`) | OEM 게이트 |
|---|---|---|---|
| 0. 프로젝트 준비 | `chore/project-setup` | `pyproject.toml`, 품질 측정 도구, `Jenkinsfile`, 이 계획서 | — |
| 1. 요구사항 분석 (SWE.1) | `docs/swe1-requirements` | SW 요구사항 명세(SWR), Use Case, 우선순위 결정표, OEM 질의 목록, OEM→SWR 추적표 | G1 (BL-SWR-1.0) |
| 2. 아키텍처 설계 (SWE.2) | `docs/swe2-architecture` | 아키텍처 설계서, 인터페이스 정의, ASIL/QM 분리 근거, 정적분석 계획 | G2 (BL-SWA-1.0) |
| 3. 상세 설계 (SWE.3) | `docs/swe3-detailed-design` | 상세 설계서(상태 전이, 결정표, 타이밍) | G2 (BL-SWD-1.0) |
| 4·5. 구현·단위 테스트 (SWE.3/4) | 모듈별 `feature/...` | 소스, 단위 테스트, 커버리지 보고서, SBOM | G3 (BL-CODE-UT-1.0) |
| 6. 통합 테스트 (SWE.5) | `test/integration` | 통합 테스트 명세·결과 | G3 (BL-INT-1.0) |
| 7. SW 검증 (SWE.6) | `test/swe6-verification` | 테스트 명세(엑셀), PC/SIL·Web 결과, 미검증 범위, 잔여 문제 | G4 (BL-VER-1.0) |

단계가 끝날 때마다 사용자에게 결과를 보고한다.

## 2. 의사결정 기록

| ID | 결정 | 근거 |
|---|---|---|
| DEC-01 | OEM 미정의 사항(규칙 간 우선순위, 평가주기 등)은 공급자 가정으로 정의하고 진행한다. 가정은 SWR 명세에 `가정`으로 표시하고 OEM 질의 목록에 올린다. | 사용자 결정 (2026-11-26) |
| DEC-02 | Web 인터페이스는 FastAPI로 구현한다. | API 문서 자동 생성, TestClient로 통합 테스트 용이 |
| DEC-03 | OEM 입력 문서는 저장소에 커밋하지 않는다. | 문서의 배포 제한 문구, 공개 저장소 |
| DEC-04 | 판단 로직은 입력·상태·시각만으로 결과가 정해지는 순수 함수로 만들고, 시각은 주입 가능한 시계로 받는다. | OEM-NFR-001 결정론, 테스트 용이성 |
| DEC-05 | ASIL B 모듈과 QM 모듈을 패키지 단위로 분리하고, QM 모듈은 정해진 인터페이스로만 ASIL B 모듈에 요청한다. | ISO 26262-6 간섭 없음(FFI) 근거 |
| DEC-06 | Jenkins 연동 전까지는 로컬에서 CI와 같은 검사를 모두 통과하고 결과를 PR에 첨부하는 것으로 "Jenkins CI 통과" 병합 조건을 대신한다. `master` 보호는 PR 필수·force push 금지로 설정하고, CI 필수 조건은 연동 후 추가한다. | 사용자 결정 (2026-11-26) |
| DEC-08 | Jenkins Multibranch Job `ClaudePython-CI`(5분 주기 브랜치 스캔, Windows Built-In 노드)를 CI로 쓴다. DEC-06을 대체하며, 병합 조건은 PR 브랜치의 Jenkins 빌드 `SUCCESS`(빌드 커밋 = PR 마지막 커밋)다. Jenkins가 GitHub에 상태를 보고하려면 GitHub 토큰을 Jenkins에 등록해야 하므로, 사용자 결정 전까지는 병합 전 API 확인으로 대신한다. | 사용자 결정 (2026-11-26) |
| DEC-07 | override 판단(SWR-006)은 상위에 ASIL B 요구사항(OEM-SR-002)이 있으므로 ASIL B로 개발한다. | 높은 등급 상속, Q-03 |

## 3. 아키텍처 방향 (SWE.2에서 확정)

| 모듈 | 역할 | 등급 |
|---|---|---|
| `inputs` | 입력 데이터 구조, 형식·범위 검증, 정규화 | ASIL B |
| `freshness` | 입력 갱신 감시, DEGRADED 전이 판단 | ASIL B |
| `arbitration` | 우선순위 판정, 좌·우 출력 결정 | ASIL B |
| `state` | OFF / NORMAL / DEGRADED / FAULT 상태 전이 | ASIL B |
| `driver` | 운전자 명령 처리, override 타이머 | QM |
| `event_log` | 최근 결정 100건 보관 (메모리만) | QM |
| `clock` | 시간 공급원 (테스트에서 고정 시계로 교체) | 공통 |
| `web` | 상태 조회 API, 시뮬레이터 | QM |

## 4. 위험과 대응

| 위험 | 대응 |
|---|---|
| OEM 미정의 사항에 대한 가정이 OEM 답변과 다를 수 있음 | 가정을 결정표 한 곳에 모아 변경 영향을 줄이고, 가정마다 테스트를 연결한다 |
| QM override(OEM-FR-003)가 ASIL B 억제(OEM-SR-002)를 해제함 | override는 ASIL B 모듈이 조건을 검증한 뒤에만 적용되도록 설계하고 SWE.2에 근거를 남긴다 |
| Jenkins 결과가 GitHub 상태로 표시되지 않아 병합 조건을 GitHub가 강제하지 못함 | 병합 전에 Jenkins API로 브랜치 빌드 결과와 빌드 커밋을 확인한다 (DEC-08) |
