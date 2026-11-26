"""@brief tools.arch_rules 단위 테스트 (SA-7, SA-8, SA-10, SA-11 음성 시험)."""

import textwrap

import pytest
from tools.arch_rules import check_source, check_tree


def _check(module: str, text: str) -> list[str]:
    """@brief 들여쓰기를 정리한 소스로 규칙을 검사한다."""
    return check_source(module, textwrap.dedent(text).lstrip("\n"))


def _rules(violations: list[str]) -> set[str]:
    """@brief 위반 메시지에서 규칙 ID만 모은다."""
    return {v.split(":", 1)[0] for v in violations}


# --- DR-1~DR-4, DR-8: 패키지 내부 import ---


@pytest.mark.parametrize(
    ("module", "imported"),
    [
        ("child_lock.safety.crash", "child_lock.types"),
        ("child_lock.qm.rules", "child_lock.types"),
        ("child_lock.controller", "child_lock.safety.arbiter"),
        ("child_lock.controller", "child_lock.qm.event_log"),
        ("child_lock.runtime.runner", "child_lock.controller"),
        ("child_lock.runtime.runner", "child_lock.qm.event_log"),
        ("child_lock.web.app", "child_lock.runtime.runner"),
        ("child_lock.web.app", "child_lock.runtime.clock"),
    ],
)
def test_allowed_internal_imports_pass(module, imported):
    assert _check(module, f"import {imported}\n") == []


@pytest.mark.parametrize(
    ("module", "imported", "rule"),
    [
        ("child_lock.safety.crash", "child_lock.qm.rules", "DR-1"),
        ("child_lock.safety.crash", "child_lock.controller", "DR-1"),
        ("child_lock.qm.rules", "child_lock.safety.arbiter", "DR-2"),
        ("child_lock.types", "child_lock.safety.crash", "DR-3"),
        ("child_lock.web.app", "child_lock.controller", "DR-4"),
        ("child_lock.web.app", "child_lock.qm.event_log", "DR-4"),
        ("child_lock.controller", "child_lock.runtime.runner", "DR-8"),
    ],
)
def test_forbidden_internal_imports_are_reported(module, imported, rule):
    assert _rules(_check(module, f"from {imported} import x\n")) == {rule}


def test_relative_import_is_resolved_before_checking():
    found = _check("child_lock.safety.crash", "from ..qm import rules\n")
    assert _rules(found) == {"DR-1"}


def test_relative_import_of_sibling_package_module_is_resolved():
    # child_lock.safety 패키지 __init__에서 `from . import x`는 safety.x
    assert _check("child_lock.safety", "from . import crash\n") == []


# --- DR-5: 외부 import, 금지 호출 ---


@pytest.mark.parametrize(
    ("module", "imported"),
    [
        ("child_lock.safety.crash", "time"),
        ("child_lock.safety.crash", "os"),
        ("child_lock.qm.rules", "random"),
        ("child_lock.controller", "threading"),
        ("child_lock.runtime.clock", "threading"),
        ("child_lock.runtime.runner", "time"),
        ("child_lock.safety.arbiter", "fastapi"),
        ("child_lock.qm.rules", "hashlib"),
    ],
)
def test_external_imports_outside_allow_list_are_reported(module, imported):
    assert _rules(_check(module, f"import {imported}\n")) == {"DR-5"}


@pytest.mark.parametrize(
    ("module", "imported"),
    [
        ("child_lock.safety.crash", "dataclasses"),
        ("child_lock.safety.crash", "collections.abc"),
        ("child_lock.runtime.clock", "time"),
        ("child_lock.runtime.runner", "threading"),
        ("child_lock.qm.replay", "hashlib"),
        ("child_lock.web.app", "fastapi.responses"),
        ("child_lock.web.app", "pathlib"),
    ],
)
def test_external_imports_in_allow_list_pass(module, imported):
    assert _check(module, f"import {imported}\n") == []


@pytest.mark.parametrize(
    "call",
    [
        "open('f')",
        "exec('x')",
        "eval('1')",
        "compile('1', 'f', 'eval')",
        "__import__('os')",
    ],
)
def test_forbidden_calls_are_reported(call):
    found = _check("child_lock.safety.crash", f"def f():\n    {call}\n")
    assert _rules(found) == {"DR-5"}


# --- DR-6: QM·web의 비공개 속성 접근과 동적 속성 변경 ---


@pytest.mark.parametrize(
    "stmt",
    [
        "runner._controller = None",
        "x = runner._state",
        "setattr(runner, 'a', 1)",
        "object.__setattr__(runner, 'a', 1)",
        "d = runner.__dict__",
    ],
)
def test_private_access_from_qm_or_web_is_reported(stmt):
    found = _check("child_lock.web.app", f"def f(runner):\n    {stmt}\n")
    assert _rules(found) == {"DR-6"}


def test_self_private_access_in_qm_is_allowed():
    source = """
        class Log:
            def __init__(self):
                self._items = ()

            def items(self):
                return self._items
    """
    assert _check("child_lock.qm.event_log", source) == []


def test_private_access_in_safety_is_not_dr6():
    assert (
        _check("child_lock.safety.crash", "def f(m):\n    return m._x\n") == []
    )


# --- SA-10: 모듈 수준 변경 가능 상태 ---


@pytest.mark.parametrize(
    "stmt",
    [
        "ITEMS = []",
        "TABLE = {}",
        "CACHE = dict()",
        "S = {1, 2}",
        "x = f()",
        "PAIR = tuple(a, b)",
        "KINDS = frozenset((1,), key=1)",
        "KINDS = frozenset(make())",
    ],
)
def test_mutable_module_level_assignments_are_reported(stmt):
    assert _rules(_check("child_lock.safety.crash", f"{stmt}\n")) == {"SA-10"}


@pytest.mark.parametrize(
    "stmt",
    [
        "EPS = 1e-9",
        "LIMIT = -1",
        "NAME = 'a'",
        "PAIR = (1, ('a', None))",
        "KINDS = frozenset({'a', 'b'})",
        "EMPTY = frozenset()",
        "ORDER = (State.A, State.B)",
        "LIMIT: Final = 2.0",
        "__all__ = ('a', 'b')",
        "type Alias = int | str",
    ],
)
def test_constant_module_level_assignments_pass(stmt):
    assert _check("child_lock.safety.crash", f"{stmt}\n") == []


def test_logger_is_allowed_only_in_web():
    stmt = "LOG = logging.getLogger(__name__)\n"
    assert _check("child_lock.web.app", "import logging\n" + stmt) == []
    assert "SA-10" in _rules(_check("child_lock.qm.rules", stmt))


# --- SA-11: Python 부분집합 ---


def test_nonlocal_is_reported():
    source = """
        def outer():
            x = 1

            def inner():
                nonlocal x
                x = 2

            return inner
    """
    assert _rules(_check("child_lock.safety.crash", source)) == {"SA-11"}


def test_direct_recursion_is_reported():
    source = "def walk(n):\n    return walk(n - 1)\n"
    assert _rules(_check("child_lock.safety.crash", source)) == {"SA-11"}


def test_registered_recursion_exception_passes():
    # SWE2-SAP 1.2: types.freeze_raw는 깊이 제한이 있는 재귀를 허용한다.
    source = (
        "def freeze_raw(v, depth=0):\n    return freeze_raw(v, depth + 1)\n"
    )
    assert _check("child_lock.types", source) == []


# --- 패키지 전체 검사 ---


def test_check_tree_maps_paths_to_module_names(tmp_path):
    pkg = tmp_path / "child_lock"
    (pkg / "safety").mkdir(parents=True)
    (pkg / "__init__.py").write_text('"""p."""\n', encoding="utf-8")
    (pkg / "safety" / "__init__.py").write_text('"""s."""\n', encoding="utf-8")
    bad = pkg / "safety" / "crash.py"
    bad.write_text("import child_lock.qm.rules\n", encoding="utf-8")
    found = check_tree(tmp_path)
    assert len(found) == 1
    assert found[0].startswith("DR-1:")
    assert "child_lock.safety.crash" in found[0]


def test_real_source_tree_has_no_violations():
    assert check_tree(__import__("pathlib").Path("src")) == []


def test_scripted_clock_is_forbidden_in_web():
    source = """
        from child_lock.runtime.clock import ScriptedClock

        def make():
            return ScriptedClock(0.0)
    """
    assert "DR-4" in _rules(_check("child_lock.web.app", source))


def test_scripted_clock_is_allowed_outside_web():
    source = "from child_lock.runtime.clock import ScriptedClock\n"
    assert _check("child_lock.runtime.runner", source) == []


def test_uvicorn_is_allowed_only_in_web():
    assert _check("child_lock.web.__main__", "import uvicorn\n") == []
    assert "DR-5" in _rules(_check("child_lock.controller", "import uvicorn\n"))
