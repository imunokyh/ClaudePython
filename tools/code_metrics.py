"""@brief 소스코드 품질 지표(주석률, 함수 길이) 측정 도구.

CLAUDE.md의 "소스코드 품질" 기준 중 Ruff로 측정할 수 없는 항목을 계산한다.
"""

import argparse
import ast
import io
import tokenize
from pathlib import Path

## 코드 줄로 세지 않는 토큰 종류
_NON_CODE_TOKENS = frozenset(
    {
        tokenize.COMMENT,
        tokenize.NL,
        tokenize.NEWLINE,
        tokenize.INDENT,
        tokenize.DEDENT,
        tokenize.ENDMARKER,
        tokenize.ENCODING,
    }
)

## docstring을 가질 수 있는 AST 노드 종류
_DOC_OWNERS = (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)


def _docstring_rows(tree: ast.Module) -> set[int]:
    """@brief docstring이 차지하는 줄 번호를 모은다.

    @param tree 파싱된 모듈
    @return docstring 줄 번호 집합 (1부터 시작)
    """
    rows: set[int] = set()
    for node in ast.walk(tree):
        if not isinstance(node, _DOC_OWNERS) or not node.body:
            continue
        first = node.body[0]
        is_doc = isinstance(first, ast.Expr) and isinstance(
            first.value, ast.Constant
        )
        if is_doc and isinstance(first.value.value, str):
            rows.update(range(first.lineno, first.end_lineno + 1))
    return rows


def _token_rows(source: str) -> tuple[set[int], set[int]]:
    """@brief 토큰을 분석해 코드 줄과 주석 줄을 구분한다.

    @param source 파이썬 소스
    @return (코드 토큰이 있는 줄, 주석 토큰이 있는 줄)
    """
    code_rows: set[int] = set()
    comment_rows: set[int] = set()
    tokens = tokenize.generate_tokens(io.StringIO(source).readline)
    for tok in tokens:
        if tok.type == tokenize.COMMENT:
            comment_rows.add(tok.start[0])
        elif tok.type not in _NON_CODE_TOKENS:
            code_rows.update(range(tok.start[0], tok.end[0] + 1))
    return code_rows, comment_rows


def comment_ratio(source: str) -> float:
    """@brief 주석률을 계산한다.

    주석률 = (주석 줄 + docstring 줄) / (주석 줄 + docstring 줄 + 코드 줄).
    빈 줄은 제외하고, 코드와 끝 주석이 같이 있는 줄은 코드 줄로 센다.

    @param source 파이썬 소스
    @return 0.0~1.0 주석률. 측정할 줄이 없으면 1.0
    """
    doc_rows = _docstring_rows(ast.parse(source))
    code_rows, comment_rows = _token_rows(source)
    commented = code = 0
    for row, line in enumerate(source.splitlines(), start=1):
        if not line.strip():
            continue
        if row in doc_rows or row not in code_rows and row in comment_rows:
            commented += 1
        else:
            code += 1
    total = commented + code
    return commented / total if total else 1.0


## 함수 정의 노드 종류
_FUNC_NODES = (ast.FunctionDef, ast.AsyncFunctionDef)


def _iter_functions(node: ast.AST, prefix: str = ""):
    """@brief 함수 정의를 한정 이름(예: Class.method)과 함께 순회한다.

    @param node 탐색을 시작할 AST 노드
    @param prefix 상위 클래스·함수 이름 접두어
    @return (한정 이름, 함수 노드) 제너레이터
    """
    for child in ast.iter_child_nodes(node):
        if isinstance(child, (*_FUNC_NODES, ast.ClassDef)):
            name = f"{prefix}{child.name}"
            if isinstance(child, _FUNC_NODES):
                yield name, child
            yield from _iter_functions(child, f"{name}.")
        else:
            yield from _iter_functions(child, prefix)


def function_lengths(source: str) -> list[tuple[str, int, int]]:
    """@brief 함수마다 순수 코드 줄 수를 측정한다.

    빈 줄, 주석만 있는 줄, docstring 줄을 뺀 나머지를 센다.
    중첩 함수의 줄은 바깥 함수에도 포함된다.

    @param source 파이썬 소스
    @return (한정 이름, 시작 줄, 순수 코드 줄 수) 목록 (소스 순서)
    """
    tree = ast.parse(source)
    doc_rows = _docstring_rows(tree)
    code_rows = _token_rows(source)[0] - doc_rows
    result = []
    for name, func in _iter_functions(tree):
        span = range(func.lineno, func.end_lineno + 1)
        result.append((name, func.lineno, len(code_rows.intersection(span))))
    return result


def _iter_py_files(paths: list[str]):
    """@brief 경로 목록에서 .py 파일을 정렬된 순서로 찾는다.

    @param paths 파일 또는 디렉터리 경로 목록
    @return .py 파일 Path 제너레이터
    """
    for raw in paths:
        path = Path(raw)
        if path.is_dir():
            yield from sorted(path.rglob("*.py"))
        else:
            yield path


def _check_file(path: Path, args: argparse.Namespace) -> list[str]:
    """@brief 파일 하나의 기준 위반 내역을 만든다.

    @param path 검사할 파일
    @param args 명령행 옵션 (기준값)
    @return 위반 메시지 목록
    """
    source = path.read_text(encoding="utf-8")
    problems = []
    ratio = comment_ratio(source)
    if ratio < args.min_comment_ratio:
        problems.append(
            f"{path}: 주석률 {ratio:.1%} < {args.min_comment_ratio:.1%}"
        )
    for name, lineno, length in function_lengths(source):
        if length > args.max_function_lines:
            problems.append(
                f"{path}:{lineno}: {name} 함수 {length}줄 "
                f"> {args.max_function_lines}줄"
            )
    return problems


def main(argv: list[str] | None = None) -> int:
    """@brief 명령행 진입점. 기준 위반이 있으면 1을 반환한다.

    @param argv 명령행 인자 (None이면 sys.argv 사용)
    @return 종료 코드 (0: 통과, 1: 위반 있음)
    """
    parser = argparse.ArgumentParser(description="주석률과 함수 길이 검사")
    parser.add_argument("paths", nargs="+", help="검사할 파일 또는 디렉터리")
    parser.add_argument("--max-function-lines", type=int, default=50)
    parser.add_argument("--min-comment-ratio", type=float, default=0.2)
    args = parser.parse_args(argv)
    problems = []
    for path in _iter_py_files(args.paths):
        problems.extend(_check_file(path, args))
    for problem in problems:
        print(problem)
    print(f"위반 {len(problems)}건")
    return 1 if problems else 0
