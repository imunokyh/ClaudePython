# 추적표 OEM ↔ SWR

| 항목 | 내용 |
|---|---|
| 문서 ID | SWE1-TRC |
| 범위 | OEM-SWR-001 요구사항·인터페이스 ↔ SWE1-SRS SW 요구사항 (양방향) |

## 1. 정방향: OEM → SWR

SWR-019(우선순위)는 순위 표에 규칙이 있는 모든 OEM 요구사항에서 파생된다.

| OEM 요구사항 | ASIL | SWR | OEM 추적표(9장)와 비교 |
|---|---|---|---|
| OEM-SR-001 | B | SWR-007, SWR-008, SWR-019 | 일치 + SWR-019 |
| OEM-SR-002 | B | SWR-005, SWR-006, SWR-009, SWR-019 | 일치 + SWR-019 |
| OEM-SR-003 | B | SWR-013, SWR-019, SWR-022 | 일치 + SWR-019, 022 |
| OEM-SR-004 | B | SWR-021, SWR-019 | 일치 + SWR-019 |
| OEM-FR-001 | QM | SWR-001, SWR-002, SWR-004, SWR-019 | 일치 + SWR-019 |
| OEM-FR-002 | QM | SWR-003, SWR-019 | 일치 + SWR-019 |
| OEM-FR-003 | QM | SWR-006, SWR-019 | 일치 + SWR-019 |
| OEM-FR-004 | QM | SWR-014, SWR-015 | 일치 |
| OEM-FR-005 | QM | SWR-017, SWR-019 | 일치 + SWR-019 |
| OEM-FR-006 | QM | SWR-018, SWR-019 | 일치 + SWR-019 |
| OEM-FR-007 | QM | SWR-020, SWR-019 | 일치 + SWR-019 |
| OEM-NFR-001 | QM | SWR-016, SWR-022 | 일치 + SWR-022 |
| OEM-NFR-002 | QM | SWR-010, SWR-011, SWR-012 | 일치 |

OEM 요구사항 13건이 모두 1건 이상의 SWR로 추적된다 (13/13).

| OEM 인터페이스 | SWR |
|---|---|
| OEM-IF-001 (차속, 기어, 타임스탬프) | SWR-003, 004, 006, 013, 022 |
| OEM-IF-002 (충돌 상태) | SWR-007, 008, 013 |
| OEM-IF-003 (접근위험) | SWR-005, 006, 009, 013 |
| OEM-IF-004 (운전자 명령) | SWR-001, 002, 004, 006, 013 |
| OEM-IF-005 (잠금 출력) | SWR-002, 003, 005, 006, 007, 008, 017, 018, 019, 020, 021 |
| OEM-IF-006 (표시) | SWR-013, 014, 015, 019, 021 |
| OEM-IF-007 (화재, 과온, 성인) | SWR-013, 017 |
| OEM-IF-008 (ISOFIX) | SWR-013, 018 |
| OEM-IF-009 (시동, sensor fault) | SWR-007, 013, 020, 021 |

OEM 인터페이스 9건이 모두 SWR로 추적된다 (9/9).

## 2. 역방향: SWR → OEM

| SWR | ASIL | 상위 OEM | 가정 |
|---|---|---|---|
| SWR-001 | QM | OEM-FR-001 | — |
| SWR-002 | QM | OEM-FR-001 | A-13 |
| SWR-003 | QM | OEM-FR-002 | A-05 |
| SWR-004 | QM | OEM-FR-001 | A-05 |
| SWR-005 | B | OEM-SR-002 | — |
| SWR-006 | B | OEM-SR-002, OEM-FR-003 | A-02, A-06, A-13, A-20, A-24 |
| SWR-007 | B | OEM-SR-001 | A-03, A-14 |
| SWR-008 | B | OEM-SR-001 | A-04, A-23 |
| SWR-009 | B | OEM-SR-002 | — |
| SWR-010 | QM | OEM-NFR-002 | A-10 |
| SWR-011 | QM | OEM-NFR-002 | A-10 |
| SWR-012 | QM | OEM-NFR-002 | — |
| SWR-013 | B | OEM-SR-003 | A-02, A-07, A-11, A-12, A-15, A-21, A-22 |
| SWR-014 | QM | OEM-FR-004 | — |
| SWR-015 | QM | OEM-FR-004 | A-19 |
| SWR-016 | QM | OEM-NFR-001 | A-09 |
| SWR-017 | QM | OEM-FR-005 | A-08, A-17 |
| SWR-018 | QM | OEM-FR-006 | A-18 |
| SWR-019 | B | OEM-SR-001~004, OEM-FR-001~003, OEM-FR-005~007 | A-08 |
| SWR-020 | QM | OEM-FR-007 | A-08 |
| SWR-021 | B | OEM-SR-004 | A-16 |
| SWR-022 | B | OEM-SR-003, OEM-NFR-001 | A-01, A-02, A-25 |

SWR 22건이 모두 상위 OEM 요구사항을 가진다 (22/22).

ASIL 상속: ASIL B와 QM 상위를 함께 가진 SWR(SWR-006, 019, 022)은 ASIL B로 개발한다.
