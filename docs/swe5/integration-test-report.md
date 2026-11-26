# 통합 테스트 결과서 — 전자식 차일드락 제어 SW

| 항목 | 내용 |
|---|---|
| 문서 ID | SWE5-ITR |
| 대상 명세 | SWE5-ITS (IT-01~IT-11) |
| 시험 대상 | `master` 기준 `test/integration` 브랜치 (커밋은 이 문서를 포함한 PR의 병합 커밋) |
| 시험 환경 | Windows 11, Python 3.12.10, 로컬 + Jenkins `ClaudePython-CI` |
| 시험일 | 2026-11-26 |

## 1. 결과 요약

| ID | 결과 | 비고 |
|---|---|---|
| IT-01 | 합격 | 정차 → 자동 잠금 → 유지 → 전체 해제 |
| IT-02 | 합격 | `CONFIRMED` 다음 평가(≤ 50 ms)에 양쪽 해제, 이후 ISOFIX에도 유지 |
| IT-03 | 합격 | 첫 해제 억제, 다음 평가 재입력으로 override |
| IT-04 | 합격 | 마지막 갱신 후 0.20초까지 `VALID`, 0.25초 `STALE` |
| IT-05 | 합격 | 범위 밖 값 202 후 `INVALID`, 깨진 JSON 422·상태 불변 |
| IT-06 | 합격 | 120주기 벡터 1,000회 재생, 해시 1종 |
| IT-07 | 합격 | 150건 중 `event_id` 51~150 조회 |
| IT-08 | 합격 | 측정값 아래 |
| IT-09 | 합격 | 측정값 아래 |
| IT-10 | 합격 | 응답 800건 모두 2xx, 평가 예외 0 |
| IT-11 | 합격 | QM 예외 중에도 `APPROACH_RISK`, `CRASH_CONFIRMED` 정상 |

11건 중 11건 합격. 통합 중 발견한 결함은 없다.

## 2. 자원·타이밍 측정 (SWE2-ARC 7장)

10,000회 평가, 로컬 PC, GC 포함.

| 항목 | 측정 | 예산 | 판정 |
|---|---|---|---|
| 평가 1회 평균 | 36.8 µs | — | — |
| 평가 1회 99번째 백분위 | 57.0 µs | — | — |
| 평가 1회 최댓값 | 522.4 µs | 5 ms | 합격 (예산의 약 10%) |
| 10,000회 평가 메모리 증가 | 25.8 KiB | 1 MiB | 합격 |
| 이벤트 보관 건수 | 100 | 100 | 합격 |

## 3. 산출물

- 자동 테스트: `tests/integration/test_integration.py`
- CI 보고서: Jenkins `ClaudePython-CI` 빌드의 `reports/junit.xml`, `reports/coverage.xml`, `reports/sbom.json`(이 PR부터 생성)
