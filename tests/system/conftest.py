"""@brief SWE.6 시험 공용 fixture."""

import pytest
from tests.system.harness import Bench


@pytest.fixture
def bench():
    """@brief 초기 상태의 시험대 (시각 0.0초)."""
    b = Bench()
    yield b
    b.close()
