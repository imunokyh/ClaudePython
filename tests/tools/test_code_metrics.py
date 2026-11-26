"""@brief tools.code_metrics 단위 테스트."""

import runpy
import textwrap

import pytest
from tools.code_metrics import comment_ratio, function_lengths, main


def _src(text: str) -> str:
    """@brief 테스트용 소스의 공통 들여쓰기를 제거한다."""
    return textwrap.dedent(text).lstrip("\n")


def test_comment_ratio_counts_comment_and_docstring_lines():
    # 코드 2줄(def, return), 주석 1줄, docstring 4줄(모듈 1 + 함수 3),
    # 빈 줄 2줄은 제외 -> 5 / 7
    source = _src('''
        """모듈 설명."""

        # 주석
        def f():
            """첫 줄.

            둘째 줄.
            """
            return 1
    ''')
    assert comment_ratio(source) == 5 / 7


def test_comment_ratio_counts_code_with_trailing_comment_as_code():
    source = "x = 1  # 끝 주석\n"
    assert comment_ratio(source) == 0.0


def test_comment_ratio_ignores_string_statements_that_are_not_docstrings():
    source = _src('''
        x = 1
        """docstring 위치가 아닌 문자열."""
    ''')
    assert comment_ratio(source) == 0.0


def test_comment_ratio_of_empty_source_is_one():
    # 측정할 줄이 없으면 기준 위반으로 보지 않는다.
    assert comment_ratio("\n\n") == 1.0


def test_function_lengths_excludes_blank_comment_and_docstring_lines():
    source = _src('''
        def f(a):
            """설명.

            상세.
            """
            # 주석
            b = a + 1

            return b
    ''')
    # def, b = ..., return -> 3줄
    assert function_lengths(source) == [("f", 1, 3)]


def test_function_lengths_reports_methods_with_class_prefix():
    source = _src("""
        class Box:
            def size(self):
                return 1
    """)
    assert function_lengths(source) == [("Box.size", 2, 2)]


def test_function_lengths_counts_multiline_statement_lines():
    source = _src("""
        async def g():
            return [
                1,
                2,
            ]
    """)
    assert function_lengths(source) == [("g", 1, 5)]


def _write(path, text):
    """@brief tmp 디렉터리에 테스트용 소스 파일을 쓴다."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(_src(text), encoding="utf-8")
    return path


def test_main_returns_zero_when_all_files_meet_criteria(tmp_path, capsys):
    _write(
        tmp_path / "ok.py",
        '''
        """모듈."""
        x = 1
    ''',
    )
    assert main([str(tmp_path)]) == 0
    assert "위반 0건" in capsys.readouterr().out


def test_main_reports_low_comment_ratio_per_file(tmp_path, capsys):
    bad = _write(
        tmp_path / "pkg" / "bad.py",
        """
        x = 1
        y = 2
    """,
    )
    assert main([str(tmp_path), "--min-comment-ratio", "0.2"]) == 1
    out = capsys.readouterr().out
    assert f"{bad}: 주석률 0.0% < 20.0%" in out


def test_main_reports_function_longer_than_limit(tmp_path, capsys):
    path = _write(
        tmp_path / "long.py",
        '''
        """모듈."""
        # 주석
        # 주석
        def f():
            v0 = 0
            v1 = 1
            v2 = 2
    ''',
    )
    # def + 3줄 = 4줄 > 3줄
    assert main([str(path), "--max-function-lines", "3"]) == 1
    assert f"{path}:4: f 함수 4줄 > 3줄" in capsys.readouterr().out


def test_main_accepts_function_exactly_at_limit(tmp_path):
    path = _write(
        tmp_path / "edge.py",
        '''
        def f():
            """설명."""
            return 1
    ''',
    )
    # def + return = 2줄 == 기준 2줄
    assert (
        main(
            [str(path), "--max-function-lines", "2", "--min-comment-ratio", "0"]
        )
        == 0
    )


def test_python_m_tools_runs_metrics_check_and_exits_with_code(
    tmp_path, monkeypatch
):
    _write(tmp_path / "bad.py", "x = 1\n")
    monkeypatch.setattr("sys.argv", ["tools", str(tmp_path)])
    with pytest.raises(SystemExit) as exc:
        runpy.run_module("tools", run_name="__main__")
    assert exc.value.code == 1
