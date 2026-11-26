# CLAUDE.md

이 파일은 Claude Code(claude.ai/code)가 이 저장소에서 작업할 때 참고하는 지침이다.

## 프로젝트

ClaudePython — "AI를 이용한 파이썬 코드". 현재 과제는 OEM 요구사항 사양서(OEM-SWR-001, `OEM/`에 있으며 커밋 금지)에 따른 전자식 차일드락 제어 SW의 PC/SIL 참조 구현이다. 단계별 계획과 의사결정은 `docs/development-plan.md`에 있다.

- `src/child_lock/`: 제품 코드 패키지. 구조와 의존 규칙은 `docs/swe2/architecture.md`, 함수 설계는 `docs/swe3/detailed-design.md`를 따른다.
  - ASIL B: `types`, `controller`, `runtime/`(시각·주기 실행), `safety/`(검사·충돌·접근위험·순위 판정)
  - QM: `qm/`(규칙 제안·이벤트 기록·해시), `web/`(FastAPI, 시뮬레이터)
  - QM은 출력을 직접 바꾸지 않고 제안만 한다. 순위 판정은 `safety/arbiter.py`만 한다.
- `tests/`: pytest 테스트. `tests/tools/`는 품질 측정 도구 테스트.
- `tools/code_metrics.py`: 주석률·함수 길이 측정 도구 (`python -m tools <경로>`).
- `Jenkinsfile`: CI 파이프라인 (Ruff, pytest 커버리지, 주석률·함수 길이).
- `.claude/skills/system-test-case-generator/`: 요구사항으로부터 A-SPICE(SWE.6/SYS.5)·ISO 26262-6 기준의 테스트 케이스 엑셀을 만드는 스킬. `scripts/`에 PICT 실행 래퍼와 추적성·커버리지 검증 스크립트가 있다.
- `.claude/skills/test-driven-development/`: github.com/obra/superpowers의 TDD 스킬(MIT).
- `.claude/agents/system-test-case-designer.md`: 위 테스트 케이스 스킬을 쓰는 서브 에이전트(Sonnet).

코드가 여러 모듈로 나뉘면 구조 설명을 이 파일에 짧게 추가한다.

## 명령어

가상환경은 저장소 루트의 `.venv`를 쓴다. 처음 한 번 설정한다.

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
```

| 작업 | 명령 |
|---|---|
| 전체 테스트 + Branch 커버리지 100% 확인 | `.\.venv\Scripts\python.exe -m pytest --cov --cov-branch --cov-fail-under=100` |
| 테스트 파일 하나 | `.\.venv\Scripts\python.exe -m pytest tests/tools/test_code_metrics.py` |
| 테스트 함수 하나 | `.\.venv\Scripts\python.exe -m pytest tests/tools/test_code_metrics.py::test_main_reports_low_comment_ratio_per_file` |
| 린트 | `.\.venv\Scripts\python.exe -m ruff check .` |
| 포맷 검사 / 적용 | `.\.venv\Scripts\python.exe -m ruff format --check .` / `... ruff format .` |
| 주석률·함수 길이 | `.\.venv\Scripts\python.exe -m tools src tools` |
| 타입 검사 (strict) | `.\.venv\Scripts\python.exe -m mypy` |
| Web 시뮬레이터 실행 | `.\.venv\Scripts\python.exe -m child_lock.web` → http://127.0.0.1:8000 |

아키텍처 규칙(의존 방향, 금지 import·호출, 전역 상태, 비공개 속성 접근)은 `tools/arch_rules.py`로 검사하며 pytest(`tests/tools/test_arch_rules.py`)에 포함된다.

PR을 올리기 전에 위 검사를 모두 통과시킨다. Ruff는 `.claude/`(스킬 스크립트)를 검사하지 않는다.

## 개발 환경

- **언어**: Python 3.12 이상. `pyproject.toml`에 `requires-python = ">=3.12"`로 고정한다. 더 높은 버전으로 올릴 때는 이 파일과 `pyproject.toml`을 함께 고친다.
- **단위 테스트**: pytest. 커버리지는 pytest-cov로 측정한다.
- **정적 분석**: Ruff. `ruff check`(린트)와 `ruff format`(포매팅)을 모두 쓴다. 설정은 `pyproject.toml`의 `[tool.ruff]`에 둔다.
- 개발 의존성(pytest, pytest-cov, ruff)은 `pyproject.toml`의 개발용 의존성 그룹에 버전과 함께 적는다.

## 개발 절차

개발은 A-SPICE 절차를 따르며, 아래 순서로 진행한다. 각 단계의 산출물은 `docs/` 아래에 한글로 작성하고, 앞 단계 산출물과의 양방향 추적성(ID로 연결)을 유지한다.

| 순서 | 단계 | A-SPICE | 산출물 |
|---|---|---|---|
| 1 | 요구사항 분석 | SWE.1 | SW 요구사항 명세 (요구사항마다 고유 ID) |
| 2 | 아키텍처 설계 | SWE.2 | SW 아키텍처 설계서 (컴포넌트, 인터페이스) |
| 3 | 상세 설계 | SWE.3 | 상세 설계서 (모듈·함수 단위) |
| 4 | 구현 | SWE.3 | 소스 코드 |
| 5 | 단위 테스트 | SWE.4 | pytest 단위 테스트, 커버리지 결과 |
| 6 | 통합 테스트 | SWE.5 | 통합 테스트 명세와 결과 |
| 7 | 시스템 테스트 | SWE.6 | 테스트 명세 엑셀과 결과 |

- 앞 단계 산출물이 없으면 다음 단계로 넘어가지 않는다. 작은 수정도 영향받는 산출물을 함께 고친다.
- 구현(4)과 단위 테스트(5)는 TDD로 함께 진행한다. 구현 코드를 쓰기 전에 `test-driven-development` 스킬을 호출하고 red-green-refactor 순서를 따른다: 실패하는 테스트 작성 → 실행해서 실패 확인 → 통과할 최소한의 코드 작성 → 리팩터링.
- 시스템 테스트 케이스(7)는 `system-test-case-designer` 서브 에이전트(`system-test-case-generator` 스킬)로 만든다.

## 소스코드 품질

아래 기준은 PR 병합 조건이다. 하나라도 만족하지 못하면 병합하지 않는다.

| 항목 | 기준 | 측정 방법 |
|---|---|---|
| 단위 테스트 성공률 | 100% (실패·에러 0건) | `pytest` |
| Branch 커버리지 | **반드시** 100% | `pytest --cov --cov-branch --cov-fail-under=100` |
| 순환 복잡도 | 함수마다 **반드시** 10 이하 | Ruff `C901`, `max-complexity = 10` |
| 함수 길이 | 순수 코드 50줄 이하 | 빈 줄, 주석, docstring을 뺀 줄 수 |
| 주석률 | 파일마다 20% 이상 | (주석 줄 + docstring 줄) ÷ (주석 줄 + docstring 줄 + 코드 줄), 빈 줄 제외 |
| 명명 규칙 | Google Python Style Guide | Ruff `N`(pep8-naming) |
| 린트·포맷 | 경고 0건, 포맷 차이 없음 | `ruff check`, `ruff format --check` |

- **커버리지 100%**: 달성할 때까지 테스트를 추가한다. 커버리지만 채우는 의미 없는 테스트(검증 없는 호출, 결과를 확인하지 않는 테스트)는 쓰지 않는다. `# pragma: no cover`로 측정에서 빼는 것은 금지한다. 꼭 필요하면 이유를 PR에 적고 사용자 승인을 받는다.
- **명명 규칙**(Google Python Style Guide): 모듈·패키지·함수·메서드·변수는 `lower_with_under`, 클래스·예외는 `CapWords`, 상수는 `CAPS_WITH_UNDER`, 내부용은 앞에 `_`를 붙인다.
- **주석**: Doxygen 스타일로 쓴다. 모듈, 클래스, 공개 함수에는 docstring을 단다. docstring 안에서 `@brief`, `@param`, `@return`, `@raises` 태그를 쓴다. 주석과 docstring은 한글로 쓴다.

  ```python
  def calc_interval_ms(level: int) -> int:
      """@brief 인터벌 단계로 와이프 간격을 계산한다.

      @param level 인터벌 단계 (1~5)
      @return 와이프 간격 (ms)
      @raises ValueError level이 1~5 범위를 벗어난 경우
      """
  ```

- 함수 길이와 주석률은 Ruff로 측정할 수 없어 `tools/code_metrics.py`로 측정한다. 대상은 `src`와 `tools`이며, 테스트 코드(`tests/`)는 주석률·함수 길이 측정 대상에서 뺀다.

## Git 브랜치 규칙

GitHub Flow를 쓴다.

- **`master`**: 항상 배포 가능한 상태를 유지한다. `master`에 직접 커밋하거나 push하지 않는다. 모든 변경은 PR로 병합한다.
- **작업 브랜치**: 최신 `master`에서 만든다. 이름은 `<유형>/<짧은-설명>` 형식이며 소문자와 하이픈만 쓴다.

  | 유형 | 용도 | 예 |
  |---|---|---|
  | `feature/` | 새 기능 | `feature/wiper-interval` |
  | `fix/` | 버그 수정 | `fix/door-lock-timeout` |
  | `refactor/` | 동작 변경 없는 구조 개선 | `refactor/split-validator` |
  | `docs/` | 문서·산출물만 변경 | `docs/swe2-architecture` |
  | `test/` | 테스트만 추가·수정 | `test/boundary-cases` |
  | `chore/` | 설정, CI, 의존성 | `chore/ruff-config` |

- **커밋 메시지**: 한글로 쓴다. 첫 줄은 `<유형>: <요약>` 형식으로 50자 안팎(예: `feature: 와이퍼 인터벌 계산 추가`), 빈 줄 다음에 무엇을 왜 바꿨는지 적는다. 관련 요구사항 ID가 있으면 본문에 적는다.
- **PR**:
  - 대상은 `master`다. 설명은 한글로 쓰고, 변경 내용, 관련 요구사항 ID, 테스트 결과를 적는다.
  - "소스코드 품질"의 모든 기준과 Jenkins CI 통과가 병합 조건이다.
  - 병합은 squash merge로 하고, 병합한 브랜치는 삭제한다.
- `master`에 force push하지 않는다. 작업 브랜치의 rebase나 force push는 그 브랜치 작성자만 한다.

## CI

- Jenkins를 쓴다. 주소는 `http://172.16.7.117`이고, 이 개발 PC에서 Windows 서비스로 동작한다(Built-In 노드, Windows 11).
- Job은 Multibranch Pipeline `ClaudePython-CI`다. 5분마다 GitHub 저장소를 확인해 브랜치마다 빌드한다. 사내 IP라 GitHub webhook은 쓸 수 없다. 기존 FreeStyle Job `ClaudePython`은 사용자 시험용이므로 건드리지 않는다.
- 파이프라인 정의는 저장소 루트의 `Jenkinsfile`에 둔다. Windows `bat` 명령을 쓰며, Python 경로는 Jenkins 전역 환경 변수 `CHILD_LOCK_PYTHON`이 있으면 그것을, 없으면 이 PC의 Python 3.12 경로를 쓴다.
- 빌드마다 다음을 실행한다: `ruff check`, `ruff format --check`, pytest(Branch 커버리지 100% 확인), 함수 길이·주석률 측정. 하나라도 실패하면 PR을 병합하지 않는다.
- Jenkins 결과는 GitHub에 상태로 표시되지 않는다. PR을 병합하기 전에 Jenkins API로 그 브랜치의 마지막 빌드가 `SUCCESS`이고, 빌드한 커밋이 PR의 마지막 커밋과 같은지 확인한다.
- Jenkins 인증 정보(사용자, API 토큰)는 Windows 사용자 환경 변수 `JENKINS_USER`, `JENKINS_API_TOKEN`에만 둔다. 저장소, 문서, 커밋, PR에 절대 기록하지 않는다.

## 작성 언어와 응답 방식

- 이 파일(CLAUDE.md)은 반드시 한글로 작성한다. 내용을 추가하거나 고칠 때도 한글로 쓴다.
- 모든 산출물(설계 문서, 테스트 명세, 주석, docstring, 커밋 메시지, PR 설명)은 한글로 작성한다. 코드 식별자, 명령어, 파일 경로는 영어 원문 그대로 둔다.
- 사용자에게는 존댓말(합니다체·해요체)로 응답한다. 반말을 쓰지 않는다.
- 의미 없는 사과를 하지 않는다. 실수가 있으면 무엇이 잘못됐고 어떻게 고쳤는지만 말한다.
