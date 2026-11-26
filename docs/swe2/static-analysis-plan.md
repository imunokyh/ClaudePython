# 정적분석 계획 — 전자식 차일드락 제어 SW

| 항목 | 내용 |
|---|---|
| 문서 ID | SWE2-SAP |
| 대상 | `src/child_lock/`, `tools/` |
| 근거 | CLAUDE.md "소스코드 품질", SWE2-ARC 2.2절 의존 규칙, ISO 26262-6 Table 1 (코딩 지침) |

## 1. 검사 항목

| ID | 검사 | 도구 / 명령 | 기준 |
|---|---|---|---|
| SA-1 | 린트 (pycodestyle, pyflakes, import 정렬, bugbear, 최신 문법, 단순화) | `ruff check .` | 위반 0건 |
| SA-2 | 포맷 | `ruff format --check .` | 차이 없음 |
| SA-3 | 명명 규칙 (Google Python Style) | Ruff `N` | 위반 0건 |
| SA-4 | 순환 복잡도 | Ruff `C901`, `max-complexity = 10` | 함수마다 10 이하 |
| SA-5 | 함수 길이, 주석률 | `python -m tools src tools` | 함수 50줄 이하, 파일 주석률 20% 이상 |
| SA-6 | 타입 검사 (강한 타이핑, Table 1 1c) | `mypy --strict src` | 오류 0건 |
| SA-7 | 의존 규칙 DR-1~DR-5, DR-8, 외부 import 허용 목록, `web.*`에서 `ScriptedClock` 사용 금지 | 아키텍처 테스트 `tests/architecture/` (AST) | 위반 0건 |
| SA-8 | DR-6 (밑줄 속성 접근, `setattr`, `object.__setattr__`, `__dict__` 금지, QM·web) | 아키텍처 테스트 (AST) | 위반 0건 |
| SA-9 | DR-7 (`types`의 dataclass는 `frozen=True`, `slots=True`, 불변 필드 타입) | 아키텍처 테스트 (실행 시점 검사) | 위반 0건 |
| SA-10 | 모듈 수준 변경 가능 전역 상태 금지 | 아키텍처 테스트 (AST) | 허용 형태 외 0건 |
| SA-11 | Python 부분집합 (Table 1 1b, 1d) | Ruff `BLE`(포괄 except), `S102`(exec), `S307`(eval), `PLW0603`(global), `F403`(와일드 import) + 아키텍처 테스트(직접 재귀, `nonlocal`) | 위반 0건 |
| SA-12 | 의존성 목록 (SBOM) | `pip list --format=json` → `reports/sbom.json` | G3 제출 |

### 1.1 SA-10 허용 형태

모듈 최상위에서 허용하는 대입은 아래뿐이다. 그 밖은 위반이다.

- 숫자·문자열·불리언·`None` 리터럴
- 위 리터럴로만 된 `tuple`, `frozenset(...)`
- `Final`로 표시되고 값이 위 형태인 대입
- `Enum` 클래스, 함수, 클래스 정의
- `__all__`(문자열 tuple), 로거가 필요하면 `logging.getLogger(__name__)` (web만)

### 1.2 SA-11 예외

- `controller`의 QM 호출 감싸기와 `runtime.runner`의 평가 예외 처리(SWE3-DD 5.2, 출력 유지)에서는 포괄 예외 처리(`except Exception`)가 설계상 필요하다(SWE2-ARC 2.4절). `pyproject.toml`의 `per-file-ignores`에 두 파일의 `BLE001`만 등록한다. 그 밖의 `# noqa`는 쓰지 않는다.
- SA-11 재귀 금지의 예외: `types.freeze_raw`는 JSON 중첩 구조를 바꾸는 재귀 함수이며, 깊이 제한(32단계, 넘으면 `Unsupported`)을 둔다. 검사기(`tools/arch_rules.py`)의 예외 목록에 등록한다.
- SA-10의 web 예외: `logging.getLogger(...)` 대입만 허용한다.

### 1.4 검사 도구

SA-7, SA-8, SA-10, SA-11의 AST 검사는 `tools/arch_rules.py`가 하고, `tests/architecture/`와 `tests/tools/test_arch_rules.py`(음성 시험 포함)가 pytest로 실행한다. 따라서 pytest가 통과하면 이 항목들도 통과한 것이다.

### 1.3 음성 시험

아키텍처 테스트(SA-7~SA-11)는 규칙을 일부러 어긴 샘플 소스를 입력으로 넣어 위반을 실제로 잡는지 확인하는 테스트를 함께 둔다. 동적 import(`importlib`, `__import__`), `exec`/`eval`, 상대 import(`from ..qm import`)를 포함한다.

## 2. 적용 시점

| 항목 | 적용 |
|---|---|
| SA-1~SA-5 | 0단계부터 적용 중 |
| SA-6~SA-11 | 4단계 첫 커밋에서 도입하고, 도입 시점에 저장소 전체를 일괄 검사한다 |
| SA-12 | 6단계 (G3) |

## 3. 운영

- 모든 PR은 SA-1~SA-11을 통과해야 병합한다(CLAUDE.md, DEC-06).
- `# noqa`, `# type: ignore`는 쓰지 않는다. 꼭 필요하면 이유를 PR에 적고 사용자 승인을 받아 이 문서 1.2절에 기록한다.
- 결과는 Jenkins 연동 후 `reports/`에 보관한다. 그 전에는 PR 본문에 결과를 적는다.
