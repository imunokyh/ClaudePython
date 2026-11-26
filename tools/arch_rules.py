"""@brief 아키텍처 규칙 검사기.

SWE2-ARC 2.2절 의존 규칙(DR-1~DR-8)과 SWE2-SAP의 SA-10(모듈 수준 상태),
SA-11(Python 부분집합)을 소스의 AST로 검사한다.
"""

import ast
from pathlib import Path

## 패키지 루트 이름
_ROOT = "child_lock"

## 모듈 이름 접두어 → 규칙 그룹 (긴 접두어가 먼저)
_GROUPS = (
    ("child_lock.runtime.clock", "clock"),
    ("child_lock.runtime.runner", "runner"),
    ("child_lock.runtime", "runtime"),
    ("child_lock.qm.replay", "replay"),
    ("child_lock.controller", "controller"),
    ("child_lock.safety", "safety"),
    ("child_lock.types", "types"),
    ("child_lock.qm", "qm"),
    ("child_lock.web", "web"),
)
# 위 접두어에 해당하지 않는 모듈(패키지 루트 `child_lock`)은 "root" 그룹이다.

## 그룹별 (위반 규칙 ID, 허용하는 내부 모듈 접두어)
_INTERNAL = {
    "types": ("DR-3", ()),
    "safety": ("DR-1", ("child_lock.types", "child_lock.safety")),
    "qm": ("DR-2", ("child_lock.types",)),
    "replay": ("DR-2", ("child_lock.types",)),
    "controller": (
        "DR-8",
        (
            "child_lock.types",
            "child_lock.safety",
            "child_lock.qm.rules",
            "child_lock.qm.event_log",
        ),
    ),
    "runner": (
        "DR-8",
        (
            "child_lock.controller",
            "child_lock.runtime.clock",
            "child_lock.types",
            "child_lock.qm.event_log",
        ),
    ),
    "clock": ("DR-8", ()),
    "runtime": ("DR-8", ()),
    "web": (
        "DR-4",
        (
            "child_lock.runtime.runner",
            "child_lock.runtime.clock",
            "child_lock.types",
            "child_lock.web",
        ),
    ),
    "root": ("DR-8", ()),
}

## 모든 그룹에 허용하는 외부 최상위 모듈
_BASE_EXTERNAL = frozenset(
    {
        "__future__",
        "abc",
        "collections",
        "dataclasses",
        "enum",
        "functools",
        "itertools",
        "math",
        "types",
        "typing",
    }
)

## 그룹별 추가 허용 외부 모듈
_EXTRA_EXTERNAL = {
    "replay": frozenset({"hashlib", "json"}),
    "clock": frozenset({"time"}),
    "runner": frozenset({"threading"}),
    "web": frozenset(
        {
            "asyncio",
            "fastapi",
            "json",
            "logging",
            "pathlib",
            "pydantic",
            "starlette",
        }
    ),
}

## 패키지(`__init__`)인 모듈 이름
_PACKAGES = frozenset(
    {
        "child_lock",
        "child_lock.safety",
        "child_lock.qm",
        "child_lock.web",
        "child_lock.runtime",
    }
)

## 어디서든 금지하는 내장 함수 호출 (DR-5)
_FORBIDDEN_CALLS = frozenset({"open", "exec", "eval", "compile", "__import__"})

## DR-6 적용 그룹 (QM, web)
_QM_GROUPS = frozenset({"qm", "replay", "web"})

## DR-6에서 금지하는 특수 속성
_FORBIDDEN_DUNDERS = frozenset({"__dict__", "__setattr__", "__delattr__"})

## SA-11 재귀 허용 예외 (SWE2-SAP 1.2)
_RECURSION_EXCEPTIONS = frozenset({("child_lock.types", "freeze_raw")})


def _group_of(module: str) -> str:
    """@brief 모듈 이름이 속한 규칙 그룹을 찾는다.

    @param module 점으로 구분한 모듈 이름
    @return 그룹 이름
    """
    for prefix, group in _GROUPS:
        if module == prefix or module.startswith(prefix + "."):
            return group
    return "root"


def _matches(target: str, prefixes: tuple[str, ...]) -> bool:
    """@brief 대상 모듈이 허용 접두어 중 하나에 속하는지 본다."""
    return any(target == p or target.startswith(p + ".") for p in prefixes)


def _resolve_from(module: str, node: ast.ImportFrom) -> list[str]:
    """@brief `from ... import ...`의 대상 모듈 이름을 절대 이름으로 푼다.

    @param module 검사 중인 모듈 이름
    @param node ImportFrom 노드
    @return 대상 모듈 이름 목록
    """
    target = node.module or ""
    if node.level:
        # 상대 import의 기준은 모듈이 속한 패키지다. 패키지 자신(__init__)이면
        # 그 패키지가 기준이고, 일반 모듈이면 부모 패키지가 기준이다.
        package = module if module in _PACKAGES else module.rsplit(".", 1)[0]
        parts = package.split(".")
        # 점 하나(level=1)는 기준 패키지, 점 두 개는 그 위 패키지를 뜻한다.
        base = ".".join(parts[: len(parts) - (node.level - 1)])
        target = f"{base}.{target}" if target else base
    if target in _PACKAGES:
        # `from child_lock.safety import crash`처럼 패키지에서 가져오는 이름은
        # 하위 모듈일 수 있으므로 하위 모듈 이름으로 검사한다.
        return [f"{target}.{alias.name}" for alias in node.names]
    return [target]


def _imported_modules(module: str, tree: ast.AST):
    """@brief 소스의 모든 import 대상과 줄 번호를 낸다.

    @param module 검사 중인 모듈 이름
    @param tree 파싱된 AST
    @return (대상 모듈 이름, 줄 번호) 제너레이터
    """
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                yield alias.name, node.lineno
        elif isinstance(node, ast.ImportFrom):
            for target in _resolve_from(module, node):
                yield target, node.lineno


def _check_imports(module: str, group: str, tree: ast.AST) -> list[str]:
    """@brief 내부·외부 import 규칙(DR-1~5, DR-8)을 검사한다."""
    rule, allowed = _INTERNAL[group]
    external = _BASE_EXTERNAL | _EXTRA_EXTERNAL.get(group, frozenset())
    found = []
    for target, line in _imported_modules(module, tree):
        # 최상위 이름으로 내부(child_lock) import와 외부 import를 나눈다.
        # 내부는 그룹별 허용 접두어(DR-1~4, DR-8),
        # 외부는 허용 목록(DR-5)으로 본다.
        top = target.split(".")[0]
        if top == _ROOT and not _matches(target, allowed):
            found.append(f"{rule}: {module}:{line}: 내부 import {target}")
        elif top != _ROOT and top not in external:
            found.append(f"DR-5: {module}:{line}: 외부 import {target}")
    return found


def _check_calls(module: str, tree: ast.AST) -> list[str]:
    """@brief 금지 내장 함수 호출(DR-5)을 검사한다."""
    return [
        f"DR-5: {module}:{node.lineno}: 금지 호출 {node.func.id}"
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id in _FORBIDDEN_CALLS
    ]


def _is_private_access(node: ast.Attribute) -> bool:
    """@brief self/cls가 아닌 객체의 비공개·특수 속성 접근인지 본다."""
    name = node.attr
    # __dict__·__setattr__는 불변 객체를 우회해 바꿀 수 있으므로 항상 금지한다.
    if name in _FORBIDDEN_DUNDERS:
        return True
    # 그 밖의 특수 이름(__name__ 등)과 공개 속성은 허용한다.
    is_dunder = name.startswith("__") and name.endswith("__")
    if not name.startswith("_") or is_dunder:
        return False
    # 자기 객체(self/cls)의 비공개 속성은 그 클래스 내부 구현이므로 허용한다.
    owner = node.value
    return not (isinstance(owner, ast.Name) and owner.id in ("self", "cls"))


def _check_private(module: str, group: str, tree: ast.AST) -> list[str]:
    """@brief QM·web의 비공개 속성 접근과 setattr 사용(DR-6)을 검사한다."""
    if group not in _QM_GROUPS:
        return []
    found = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Attribute) and _is_private_access(node):
            found.append(f"DR-6: {module}:{node.lineno}: 속성 {node.attr}")
        elif (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Name)
            and node.func.id == "setattr"
        ):
            found.append(f"DR-6: {module}:{node.lineno}: setattr")
    return found


def _is_constant(node: ast.expr) -> bool:
    """@brief 모듈 수준에서 허용하는 불변 값 표현인지 본다 (SA-10)."""
    # 리터럴과 다른 상수·열거형 멤버 참조(이름, 속성)는 불변 값으로 본다.
    if isinstance(node, (ast.Constant, ast.Name, ast.Attribute)):
        return True
    # 음수 리터럴(-1)은 UnaryOp로 파싱된다.
    if isinstance(node, ast.UnaryOp):
        return isinstance(node.operand, ast.Constant)
    if isinstance(node, ast.Tuple):
        return all(_is_constant(e) for e in node.elts)
    if isinstance(node, ast.Call):
        return _is_frozen_call(node)
    return False


def _is_frozen_call(node: ast.Call) -> bool:
    """@brief `frozenset(...)`/`tuple(...)`에 리터럴만 넘긴 호출인지 본다."""
    if not (
        isinstance(node.func, ast.Name)
        and node.func.id in ("frozenset", "tuple")
    ):
        return False
    # 키워드 인자나 인자 여러 개는 리터럴 상수 생성이 아니다.
    if node.keywords or len(node.args) > 1:
        return False
    # 빈 frozenset()/tuple()은 불변 빈 값이다.
    if not node.args:
        return True
    # 인자는 리터럴 묶음({...}, (...), [...])이고 원소가 모두 상수여야 한다.
    arg = node.args[0]
    literal = isinstance(arg, (ast.Tuple, ast.Set, ast.List))
    return literal and all(_is_constant(e) for e in arg.elts)


def _is_web_logger(group: str, node: ast.expr) -> bool:
    """@brief web의 `logging.getLogger(...)` 대입인지 본다."""
    return (
        group == "web"
        and isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr == "getLogger"
    )


def _check_module_state(module: str, group: str, tree: ast.Module) -> list[str]:
    """@brief 모듈 최상위 대입이 허용 형태인지(SA-10) 검사한다."""
    found = []
    for node in tree.body:
        value = (
            node.value
            if isinstance(node, (ast.Assign, ast.AnnAssign))
            else None
        )
        if value is None or _is_constant(value) or _is_web_logger(group, value):
            continue
        found.append(f"SA-10: {module}:{node.lineno}: 변경 가능 전역 상태")
    return found


def _check_subset(module: str, tree: ast.AST) -> list[str]:
    """@brief nonlocal·global과 직접 재귀(SA-11)를 검사한다."""
    found = []
    for node in ast.walk(tree):
        if isinstance(node, (ast.Nonlocal, ast.Global)):
            found.append(f"SA-11: {module}:{node.lineno}: nonlocal/global")
        elif isinstance(node, ast.FunctionDef) and _is_recursive(module, node):
            found.append(f"SA-11: {module}:{node.lineno}: 재귀 {node.name}")
    return found


def _is_recursive(module: str, func: ast.FunctionDef) -> bool:
    """@brief 함수가 자기 이름을 직접 호출하는지 본다(예외 목록 제외)."""
    if (module, func.name) in _RECURSION_EXCEPTIONS:
        return False
    return any(
        isinstance(n, ast.Call)
        and isinstance(n.func, ast.Name)
        and n.func.id == func.name
        for n in ast.walk(func)
    )


def check_source(module: str, source: str) -> list[str]:
    """@brief 모듈 소스 하나의 아키텍처 규칙 위반을 찾는다.

    @param module 점으로 구분한 모듈 이름 (예: child_lock.safety.crash)
    @param source 모듈 소스
    @return "규칙ID: 모듈:줄: 내용" 형식의 위반 목록
    """
    tree = ast.parse(source)
    group = _group_of(module)
    return (
        _check_imports(module, group, tree)
        + _check_calls(module, tree)
        + _check_private(module, group, tree)
        + _check_module_state(module, group, tree)
        + _check_subset(module, tree)
    )


def check_tree(root: Path) -> list[str]:
    """@brief `root/child_lock` 아래 모든 모듈을 검사한다.

    @param root `child_lock` 패키지를 담은 디렉터리 (예: src)
    @return 위반 목록
    """
    found = []
    # 정렬해서 순회하면 결과 순서가 실행 환경과 무관하게 같다.
    for path in sorted((root / _ROOT).rglob("*.py")):
        # src/child_lock/safety/crash.py → child_lock.safety.crash
        parts = list(path.relative_to(root).with_suffix("").parts)
        # 패키지의 __init__.py는 패키지 이름 자체로 검사한다.
        if parts[-1] == "__init__":
            parts.pop()
        source = path.read_text(encoding="utf-8")
        found.extend(check_source(".".join(parts), source))
    return found
