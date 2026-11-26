# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

ClaudePython — "AI를 이용한 파이썬 코드" (Python code written with AI). The repository currently contains only a README; no source code, dependencies, build, lint, or test tooling has been set up yet.

When adding the first code or tooling (e.g. `pyproject.toml`, a test framework, a linter), update this file with the actual commands — including how to run a single test — and a short description of the architecture once it spans multiple modules.

## Development workflow

- Before writing any implementation code (new feature, bug fix, refactor, behavior change), invoke the `test-driven-development` skill (`.claude/skills/test-driven-development/`, from github.com/obra/superpowers, MIT) and follow its red-green-refactor cycle: write a failing test, run it and watch it fail, then write the minimal code to pass.
- No test runner is configured yet. When the first Python code is added, set up pytest and record the commands (full suite and single test) in this file.

## Environment

- Windows 11, PowerShell 5.1 shell. Python 3.12 is installed (`python`); there is no `py` launcher. Set `PYTHONUTF8=1` when a script reads/writes Korean text, since the default codepage is cp949.
- The README and the user communicate in Korean; respond in Korean unless asked otherwise.
