# SW 상세 설계서 — 전자식 차일드락 제어 SW

| 항목 | 내용 |
|---|---|
| 문서 ID | SWE3-DD |
| 개정 | 1.0 (독립 검토 SWE3-REV DD-01~17 반영) |
| 베이스라인 | BL-SWD-1.0 (G2 제출 대상) |
| 상위 입력 | SWE1-SRS 1.2, SWE2-ARC 1.0 |
| A-SPICE | SWE.3 Software Detailed Design and Unit Construction |

SWE2-ARC의 컴포넌트를 모듈·함수 단위로 설계한다. 함수 이름은 구현과 같다. 모든 함수는 50줄, 순환 복잡도 10 이하로 구현하며, 복잡도가 높은 판정은 아래에 적은 보조 함수로 나눈다(DD-08).

## 0. 공통

| ID | 정의 |
|---|---|
| C-1 | 시간 비교에 `EPS = 1e-9`초를 둔다. "x ≤ 한계"는 `x <= 한계 + EPS`, "x > 한계"는 `x > 한계 + EPS`로 구현한다. |
| C-2 | 상수: `PERIOD_S = 0.05`, `STALE_LIMIT_S = 0.200`, `FUTURE_TOLERANCE_S = 0.050`, `CRASH_MAX_AGE_S = 1.0`, `PENDING_LIMIT_S = 2.0`, `OVERRIDE_WINDOW_S = 10.0`, `AUTO_LOCK_KPH = 3.0`, `SPEED_MAX_KPH = 300.0`, `EVENT_CAPACITY = 100` |
| C-3 | 숫자 신호는 `int`, `float`(`bool` 제외)를 받는다. `float()` 변환에서 `OverflowError`가 나거나 결과가 NaN·무한대면 형식 오류다(DD-02). |
| C-4 | 내부 상태 타입(`CrashMemory`, `SideMemory`, `ApproachMemory`, `ControllerState`)도 `frozen=True, slots=True` dataclass이며 갱신은 새 객체로 교체한다(DD-11). |
| C-5 | 외부에서 온 값의 타입 검사는 `type(x) is T`로 한다. `isinstance`와 `StrEnum`의 문자열 동등 비교는 쓰지 않는다(DD-06). |

## 1. `types` (ASIL B)

### 1.1 열거형 (`enum.StrEnum`, 값은 아래 문자열 그대로)

| 타입 | 멤버 = 값 |
|---|---|
| `LockOutput` | `LOCK="LOCK"`, `RELEASE="RELEASE"` |
| `State` | `OFF`, `NORMAL`, `DEGRADED`, `FAULT`, `OVERRIDE` (값 = 이름) |
| `ReasonCode` | `CRASH_CONFIRMED`, `INPUT_INVALID`, `INPUT_STALE`, `SENSOR_FAULT`, `APPROACH_RISK`, `DRIVER_OVERRIDE`, `IGNITION_OFF`, `FIRE`, `OVERTEMPERATURE`, `ADULT_PRESENT`, `ISOFIX`, `AUTO_LOCK`, `DRIVER_COMMAND`, `CRASH_PENDING`, `NO_CHANGE` (값 = 이름) |
| `InputValidity` | `VALID`, `INVALID`, `STALE` (값 = 이름) |
| `WarningCode` | `NONE`, `W_SENSOR_FAULT` (값 = 이름) |
| `Side` | `LEFT="left"`, `RIGHT="right"` (입력 `"left"`/`"right"`와 같은 값) |
| `Action` | `LOCK="lock"`, `UNLOCK="unlock"` |
| `Source` | `PHYSICAL_BUTTON="physical_button"`, `AVN="avn"`, `VOICE="voice"`, `MOBILE_APP="mobile_app"` |
| `CrashStatus` | `NONE`, `PENDING`, `CONFIRMED` (값 = 이름) |
| `Gear` | `P`, `N`, `D`, `R` (값 = 이름) |

`priority_reason_of(code) -> str`: SWE1-SRS 1.4절의 `priority_reason`. `FIRE`→`fire_detected`, `OVERTEMPERATURE`→`overtemperature_detected`, `ADULT_PRESENT`→`adult_present`, 나머지는 이름의 소문자. 이유코드 사이의 비교 순위는 `types`에 두지 않는다(같은 `INPUT_INVALID`가 순위 2일 수도 5일 수도 있고, `CRASH_PENDING`은 막은 규칙의 순위를 따른다). arbiter가 쪽마다 (출력, 이유, 비교 순위)를 계산한다.

### 1.2 원시 입력 불변화

| 함수 / 타입 | 설계 |
|---|---|
| `FrozenMap` | 불변 dataclass. `items: tuple[tuple[str, FrozenValue], ...]`(키 정렬). `get(key) -> FrozenValue \| Missing` |
| `Unsupported` | 불변 dataclass. `type_name: str`. JSON 값이 아닌 객체 표시 |
| `Missing.MISSING` | 키가 없음을 나타내는 열거형 멤버 |
| `freeze_raw(value) -> FrozenValue` | `dict`(키가 모두 `str`) → `FrozenMap`, `list`/`tuple` → `tuple`, `str`/`int`/`float`/`bool`/`None` → 그대로, 그 밖 → `Unsupported`. 재귀 |
| `RawInput` | `snapshot: FrozenValue \| None`(None = 그 주기에 스냅샷 없음), `commands: tuple[FrozenValue, ...]`, `dropped_snapshots: int` |

### 1.3 전달 타입 (모두 `frozen=True, slots=True`)

| 타입 | 필드 |
|---|---|
| `SnapshotValues` | `source_timestamp_s: float`, `vehicle_speed_kph: float \| None`, `gear: Gear \| None`, `crash_status: CrashStatus \| None`, `rear_left_approach_risk`, `rear_right_approach_risk`, `fire_detected`, `overtemperature_detected`, `adult_present`, `isofix_left`, `isofix_right`, `ignition_on`, `sensor_fault`: `bool \| None`(오류 신호는 `None`) |
| `SnapshotCheck` | `received: bool`, `values: SnapshotValues \| None`(타임스탬프 오류면 None), `asil_b_errors: frozenset[str]`, `qm_errors: frozenset[str]`, `crash_status: CrashStatus \| None`, `crash_timestamp_s: float \| None`(충돌 판정용, 2.1절) |
| `DriverCommand` | `side: Side`, `action: Action`, `source: Source` |
| `UsedSnapshot` | `values: SnapshotValues \| None`, `qm_errors: frozenset[str]`, `input_validity: InputValidity`, `rank2_reason: ReasonCode \| None` |
| `CrashView` | `latched: bool`, `pending_filter: bool` |
| `SideProposal` | `rank: int`, `output: LockOutput \| None`, `reason: ReasonCode` |
| `Decision` | SWR-014의 9개 필드 |
| `EventRecord` | `event_id: int`, `timestamp_s: float`, `decision: Decision`. `as_dict()`는 SWR-011의 11개 키 |

`INITIAL_DECISION`: 출력 둘 다 `RELEASE`, `state=DEGRADED`, `priority_reason=input_stale`, 이유 셋 다 `INPUT_STALE`, `input_validity=STALE`, `warning_code=NONE`(A-15).

## 2. `safety` (ASIL B)

### 2.1 `validation`

| 함수 | 설계 |
|---|---|
| `check_snapshot(raw, now, ref_ts) -> SnapshotCheck` | `raw is None` → `received=False`, 나머지 빈 값. `raw`가 `FrozenMap`이 아니면 모든 신호를 오류로. 그 밖에는 `SIGNALS` 표의 신호마다 `check_signal`을 부르고 오류 이름을 ASIL B / QM 집합에 넣는다. 타임스탬프가 오류면 `values=None`. 충돌 판정용 `crash_status`(신호 자체가 유효하면 값)와 `crash_timestamp_s`(`_crash_timestamp`)를 따로 채운다 |
| `check_signal(raw_value, kind, now, ref_ts) -> 값 \| INVALID` | 종류별 보조 함수로 위임: `_as_bool`(정확히 `bool`), `_as_speed`(C-3, 0.0~300.0), `_as_enum(enum_type)`(`str`이고 등록 값), `_as_timestamp`(C-3, ≥ 0.0, ≤ `now + 0.050`, `ref_ts`가 있으면 ≥ `ref_ts`) |
| `_crash_timestamp(raw_value, now) -> float \| None` | 숫자(C-3), ≥ 0.0, ≤ `now + 0.050`. **역행 검사는 하지 않는다**(늦게 도착한 `CONFIRMED`, SWR-007, DD-17) |
| `check_commands(raw_commands) -> tuple[tuple[DriverCommand, ...], int]` | 명령마다 `FrozenMap`이고 `side`∈{`left`,`right`,`all`}, `action`, `source`가 등록 값인지 검사. 오류 명령은 버리고 개수를 센다. `all`은 `LEFT`, `RIGHT` 두 명령으로 나눈다(SWR-002). 받은 순서 유지 |

`SIGNALS`(신호명, 종류, ASIL B 여부): SWE1-SRS 1.2절 표와 같다.

### 2.2 `monitor`

`select(check, now, ref) -> tuple[UsedSnapshot, SnapshotCheck | None]` — `ref`는 기준 스냅샷(ASIL B 오류 없는 마지막 `SnapshotCheck`).

1. `check.received`이고 `asil_b_errors`가 비어 있으면 `ref = check`.
2. 쓰는 값 = `ref.values`(ref 없으면 `None`), QM 오류 = `ref.qm_errors`(없으면 빈 집합).
3. `check.received`이고 `asil_b_errors`가 있으면 `rank2_reason=INPUT_INVALID`, `input_validity=INVALID`.
4. 아니고 `ref`가 없거나 `now − ref 시각 > 0.200`이면 `rank2_reason=INPUT_STALE`, `input_validity=STALE`.
5. 아니면 `rank2_reason=None`, `input_validity`는 QM 오류가 있으면 `INVALID`, 없으면 `VALID`.

### 2.3 `crash`

`CrashMemory(latched: bool, pending_since: float | None)`, 초기값 `(False, None)`.

`update(memory, check, now) -> CrashMemory`: `_update_latch`와 `_update_pending`으로 나눈다.
- `_update_latch`: `check.received`, `crash_status`가 있고 `crash_timestamp_s`가 있을 때만. `CONFIRMED`이고 `now − crash_timestamp_s ≤ 1.0` → `True`. 이미 `True`이고 `crash_status ≠ CONFIRMED`이고 `check.values`가 있고 `ignition_on is False` → `False`. 그 밖에는 그대로.
- `_update_pending`: `check.received`이고 `crash_status`가 있을 때만(타임스탬프 유효는 요구하지 않음, DD-09). `PENDING`이면 `pending_since`가 없을 때 `now`, 그 밖의 값이면 `None`.

`view(memory, now) -> CrashView`: `pending_filter = pending_since is not None and now − pending_since ≤ 2.0`.

### 2.4 `approach`

`SideMemory(first_suppress_ts: float | None, first_suppress_eval: int, override: bool)`, `ApproachMemory(left, right)`, 초기값 `(None, -1, False)`.

`evaluate(memory, used, commands, crash, frozen, eval_index) -> tuple[ApproachMemory, SideProposal | None, SideProposal | None]` — `frozen`은 순위 1~3 해당 여부, `eval_index`는 정상 평가 번호(controller가 1씩 증가). 쪽마다 `_evaluate_side`:

1. `used.values is None`이면 메모리 유지, 제안 없음.
2. `_terminated(values, side, crash)`(위험이 `True`가 아님, 차속 ≥ 3.0, `ignition_on is False`, `crash.latched` 중 하나)이면 `SideMemory(None, -1, False)`.
3. 위험이 `True`가 아니면 제안 없음.
4. `frozen`이 아니고 `_has_unlock(commands, side)`이고 차속 < 3.0이면 `_count_unlock(memory, t, eval_index)` — `t = values.source_timestamp_s`(명령 시각):
   - 이미 override면 그대로.
   - 첫 억제가 있고 `eval_index > first_suppress_eval`(이후 평가, DD-01)이고 `t − first_suppress_ts ≤ 10.0`이면 override, 첫 억제 지움.
   - 아니면 첫 억제 = `(t, eval_index)`.
5. override면 `SideProposal(4, RELEASE, DRIVER_OVERRIDE)`, 아니면 `SideProposal(4, LOCK, APPROACH_RISK)`.

### 2.5 `arbiter`

`arbitrate(used, crash, approach, qm, previous, override_active, time_error) -> Decision`. `approach`는 (좌, 우) 접근위험 제안, `qm`은 (좌, 우) 제안 튜플(controller가 정규화한 `tuple[object, ...]` 두 개).

쪽마다 `_decide_side`는 `_asil_b_side`(순서 1~4)를 먼저 보고, 결과가 없으면 `_qm_side`(순서 5~7)를 본다. 결과는 `(출력, 이유, 비교 순위)`다.

| 순서 | 조건 | 출력 | 이유 | 비교 순위 |
|---|---|---|---|---|
| 1 | `crash.latched` | `RELEASE` | `CRASH_CONFIRMED` | 1 |
| 2 | `time_error` 또는 `used.rank2_reason` 있음 | 직전 | `INPUT_INVALID`(시각 오류) / `rank2_reason` | 2 |
| 3 | `used.values`가 있고 `sensor_fault is True` | 직전 | `SENSOR_FAULT` | 3 |
| 4 | 이 쪽 접근위험 제안 | 제안 출력 | 제안 이유 | 4 |
| 5 | `used.qm_errors`가 있음 | 직전 | `INPUT_INVALID` | 5 |
| 6 | `_valid_qm`을 통과한 제안 중 순위가 가장 높은 것. 같은 순위면 목록에서 먼저 나온 것(DD-16) | 제안 출력(None이면 직전) | 제안 이유 | 제안 순위 |
| 6a | 6의 결과가 `LOCK`, 직전이 `RELEASE`, `crash.pending_filter` | 직전 | `CRASH_PENDING` | 제안 순위 |
| 7 | 해당 없음 | 직전 | `NO_CHANGE` | 11 |

`_valid_qm(p) -> bool`(C-5): `type(p) is SideProposal`, `type(p.rank) is int`이고 6~10, `type(p.reason) is ReasonCode`이고 그 순위의 코드(6: `IGNITION_OFF`, 7: `FIRE`/`OVERTEMPERATURE`/`ADULT_PRESENT`, 8: `ISOFIX`, 9: `AUTO_LOCK`, 10: `DRIVER_COMMAND`), `type(p.output) is LockOutput`이고 방향 허용(6·7 `RELEASE`, 8·9 `LOCK`, 10 둘 다).

전체 결과(`_summarize`):
- `reason_code`: 두 쪽 중 비교 순위가 작은 쪽의 이유, 같으면 좌측. `priority_reason = priority_reason_of(reason_code)`.
- `_state_of`(DD-04, 조건 기준): `degraded = time_error or used.rank2_reason is not None or bool(used.qm_errors)`. `values = None if time_error else used.values`. `DEGRADED`(degraded) > `FAULT`(values가 있고 `sensor_fault is True`) > `OFF`(values가 있고 `ignition_on is False`) > `OVERRIDE`(`override_active`) > `NORMAL`.
- `warning_code`: values가 있고 `sensor_fault is True`면 `W_SENSOR_FAULT`, 아니면 `NONE`(DD-05).
- `input_validity`: 시각 오류면 `INVALID`, 아니면 `used.input_validity`.

## 3. `qm` (QM)

### 3.1 `rules`

`proposals(values, commands) -> tuple[tuple[SideProposal, ...], tuple[SideProposal, ...]]`(좌, 우). `values`가 `None`이면 `((), ())`. 규칙별 보조 함수가 해당하면 제안을 낸다. 순위 판정은 하지 않는다.

| 보조 함수 | 조건 | 제안 |
|---|---|---|
| `_ignition_off` | `ignition_on is False` | 양쪽 `(6, RELEASE, IGNITION_OFF)` |
| `_forced_release` | 화재 > 과온 > 성인 중 첫 `True` | 양쪽 `(7, RELEASE, FIRE/OVERTEMPERATURE/ADULT_PRESENT)` |
| `_isofix` | `isofix_<side> is True` | 그 쪽 `(8, LOCK, ISOFIX)` |
| `_auto_lock` | 차속이 있고 ≥ 3.0 | 양쪽 `(9, LOCK, AUTO_LOCK)` |
| `_driver` | 그 쪽의 마지막 명령. `UNLOCK`은 차속이 있고 < 3.0일 때만 | 그 쪽 `(10, LOCK/RELEASE, DRIVER_COMMAND)` |

### 3.2 `event_log`

`EventLog(capacity=100)`: 내부에 `collections.deque(maxlen=capacity)`, 다음 `event_id`, 직전 기록 `Decision`.
- `record(now, decision, had_commands) -> bool`: 첫 기록이거나, `had_commands`이거나, `decision != 직전 기록`이면 `EventRecord`를 추가하고 `True`.
- `events() -> tuple[EventRecord, ...]`: 오래된 순.

### 3.3 `replay`

`decision_hash(decisions) -> str`: `Decision`마다 9개 키 딕셔너리로 바꿔 목록을 `json.dumps(sort_keys=True, ensure_ascii=False, separators=(",", ":"))`로 직렬화하고 SHA-256 16진수 문자열을 낸다.

## 4. `controller` (ASIL B)

`Controller(event_log: EventLog | None = None)`. 비공개 상태 `_state: ControllerState`(직전 `Decision`, 직전 정상 평가 시각, 정상 평가 번호, 기준 스냅샷, `CrashMemory`, `ApproachMemory`).

`evaluate(now, raw) -> Decision`:
1. `now`가 유한하지 않거나(DD-10), 직전 정상 평가 시각이 있고 `now ≤` 그 값이면 `_evaluate_time_error`:
   - `used = UsedSnapshot(None, ∅, INVALID, INPUT_INVALID)`.
   - crash 뷰는 `CrashView(현재 래치, False)`, 접근위험·QM 제안은 없음, `override_active=False`.
   - `arbitrate(..., time_error=True)`로 결정한다. `Decision`만 교체하고 기록한다(DD-05, DD-07).
2. `check = check_snapshot(raw.snapshot, now, ref_ts)`, `commands, _ = check_commands(raw.commands)`.
3. `crash_memory = crash.update(...)`, `view = crash.view(...)`.
4. `used, ref = monitor.select(check, now, ref)`.
5. `frozen = bool(view.latched or used.rank2_reason is not None or (used.values is not None and used.values.sensor_fault is True))`(DD-13).
6. `eval_index += 1`, `approach.evaluate(...)`. `override_active = 새 메모리 좌.override or 우.override`.
7. `_call_rules(used.values, commands)`: `try` 안에서 `rules.proposals`를 부르고 결과를 `(tuple(좌), tuple(우))`로 정규화한다. 모양이 맞지 않거나 예외가 나면 `((), ())`(DD-06).
8. `arbitrate(...)`, 상태 교체.
9. `_record(now, decision, had_commands=len(raw.commands) > 0)`: 예외는 무시.

`last_decision` 속성: 직전 `Decision`(평가 전에는 `INITIAL_DECISION`).

## 5. `runtime` (ASIL B)

### 5.1 `clock`

| 타입 | 설계 |
|---|---|
| `Clock`(Protocol) | `now() -> float` |
| `MonotonicClock` | `time.monotonic()` |
| `ScriptedClock(start=0.0)` | `now()`는 저장된 값. `set(t)`, `advance(dt)`. 시험 하니스 전용 |

### 5.2 `runner`

`Runner(clock, controller, event_log=None, period_s=0.05)`. 락 하나로 모든 공개 메서드를 직렬화한다.

| 메서드 | 설계 |
|---|---|
| `submit(snapshot, commands, has_snapshot)` | `has_snapshot`이 거짓이면 우편함 스냅샷을 건드리지 않는다(DD-03). 참이면 `freeze_raw(snapshot)`을 SWR-022 규칙으로 넣는다: 우편함이 비었거나, 새 것이 `CONFIRMED`이거나, 기존 것이 `CONFIRMED`가 아니면 교체(기존 것이 있었으면 버린 수 +1), 그 밖에는 새 것을 버린다(+1). 명령은 `freeze_raw`해서 이어 붙인다 |
| `tick() -> Decision` | 우편함을 비워 `RawInput`을 만들고 `controller.evaluate(clock.now(), raw)`. 평가에서 예외가 나면 `evaluation_errors`를 올리고 직전 `Decision`을 그대로 둔다(출력 유지, DD-02) |
| `status() -> Decision` | `controller.last_decision` |
| `events() -> tuple[EventRecord, ...]` | `event_log.events()`(없으면 빈 튜플) |
| `start()` / `stop()` | 주기 스레드. `deadline += period`, `Event.wait(max(0, deadline − now))` 후 `tick`. `tick` 뒤 `now > deadline + period`이면 `overruns += 1`, `deadline = now`(밀린 주기는 따라잡지 않고 다음 주기 하나를 바로 실행, DD-14) |
| `overruns`, `evaluation_errors`, `dropped_snapshots` | 운영 카운터 |

## 6. `web` (QM)

`create_app(runner: Runner | None = None) -> FastAPI`. `runner`가 없으면 `Runner(MonotonicClock(), Controller(log), log)`를 만들고 앱 수명주기(lifespan)에서 `start()`/`stop()`. 엔드포인트는 `async def`이며 runner 호출은 `starlette.concurrency.run_in_threadpool`로 보낸다(이벤트 루프가 락에 막히지 않게, DD-14).

| 엔드포인트 | 설계 |
|---|---|
| `POST /input` | 본문을 직접 JSON 파싱한다. 구문 오류면 422. 본문이 객체이고 `snapshot` 또는 `commands` 키가 있으면 그 값을 쓴다: `snapshot` 키가 있으면 값이 `null`이어도 스냅샷으로 넘긴다(→ 형식 오류 `INVALID`, DD-15). `commands`가 `null`이거나 없으면 빈 목록, 목록이 아니면 원소 하나짜리 목록. 두 키가 모두 없으면 본문 전체를 스냅샷으로 넘긴다. 202 |
| `GET /status` | `runner.status()`를 SWR-014의 9개 키 JSON으로. 직렬화 실패 시 500 |
| `GET /events` | 이벤트 목록(SWR-011의 11개 키). 직렬화 실패 시 500 |
| `GET /` | 시뮬레이터 HTML(정적 파일) |

## 7. 추적 (SWR → 함수)

| SWR | 함수 |
|---|---|
| SWR-001, 002 | `validation.check_commands`, `rules._driver`, `arbiter._qm_side` |
| SWR-003 | `rules._auto_lock` |
| SWR-004 | `rules._driver`(운전자 `UNLOCK` 차속 조건) |
| SWR-005, 006, 009 | `approach.evaluate`, `_evaluate_side`, `_terminated`, `_count_unlock` |
| SWR-007 | `validation._crash_timestamp`, `crash._update_latch`, `arbiter._asil_b_side`(1) |
| SWR-008 | `crash._update_pending`, `crash.view`, `arbiter._qm_side`(6a) |
| SWR-010, 011, 012 | `EventLog.record`, `EventLog.events`, `EventRecord.as_dict` |
| SWR-013 | `validation.check_snapshot`, `check_signal`, `monitor.select`, `arbiter._asil_b_side`(2), `_qm_side`(5) |
| SWR-014, 015 | `web` 엔드포인트, `Decision` |
| SWR-016 | `replay.decision_hash`, `Controller.evaluate`(결정론) |
| SWR-017, 018, 020 | `rules._forced_release`, `_isofix`, `_ignition_off` |
| SWR-019 | `arbiter.arbitrate`, `_decide_side`, `_valid_qm`, `_summarize` |
| SWR-021 | `arbiter._asil_b_side`(3), `_state_of`, `_summarize` |
| SWR-022 | `Runner.tick`, `submit`, `start`, `Controller.evaluate`(시각 검사), `monitor.select` |

## 8. 아키텍처(SWE2-ARC 1.0)와의 차이

상세화하면서 바뀐 인터페이스다. 아키텍처의 컴포넌트, 등급, 의존 규칙은 바뀌지 않는다.

| ARC 2.3 | 이 설계 | 이유 |
|---|---|---|
| `SnapshotCheck.crash_status_valid`, `timestamp_valid` | `crash_status`, `crash_timestamp_s`(값 또는 None) | 충돌 판정에 값이 필요하고, 역행 검사를 뺀 별도 시각이 필요함(DD-17) |
| `UsedSnapshot.rank2: bool` | `rank2_reason: ReasonCode \| None` | `INVALID`/`STALE` 구분 |
| `rules.proposals(UsedSnapshot, 명령, 직전 Decision)` | `proposals(values, 명령)` | 규칙이 직전 출력을 쓰지 않음. 직전 출력은 arbiter만 씀 |
| `Runner.submit(snapshot, commands)` | `submit(snapshot, commands, has_snapshot)` | 명령만 보낸 경우 우편함 스냅샷 보존(DD-03) |
| `Runner(clock, controller)` | `Runner(clock, controller, event_log)` | `events()` 조회를 runner로 통일(ARC AR-30) |
