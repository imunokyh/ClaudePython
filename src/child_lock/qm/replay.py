"""@brief 공개 결과 해시 (QM, SWE3-DD 3.3, SWR-016).

같은 입력 순서를 재생했을 때 결과가 같은지 비교하는 데 쓴다.
시험 하니스와 tools가 호출한다.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Iterable

from child_lock.types import Decision


def decision_hash(decisions: Iterable[Decision]) -> str:
    """@brief 결과 목록의 SHA-256 해시를 계산한다.

    각 결과를 SWR-014의 9개 키 딕셔너리로 바꾸고, 목록 전체를 키 정렬
    JSON(공백 없음)으로 직렬화해 해시한다(A-09).

    @param decisions 평가 결과 순서열
    @return 16진수 해시 문자열
    """
    payload = [d.as_dict() for d in decisions]
    text = json.dumps(
        payload, sort_keys=True, ensure_ascii=False, separators=(",", ":")
    )
    return hashlib.sha256(text.encode("utf-8")).hexdigest()
