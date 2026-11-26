"""@brief DR-7: types의 dataclass는 frozen·slots, 필드 타입은 불변 (SA-9)."""

import dataclasses
import inspect
import types as pytypes
import typing

from child_lock import types as t

## 불변으로 인정하는 필드 타입의 원자 타입
_IMMUTABLE_ATOMS = (int, float, str, bool, type(None), frozenset, tuple)


def _dataclasses():
    """@brief child_lock.types의 모든 dataclass를 모은다."""
    return [
        obj
        for _, obj in inspect.getmembers(t, inspect.isclass)
        if dataclasses.is_dataclass(obj) and obj.__module__ == t.__name__
    ]


def _is_immutable_type(tp, seen=frozenset()) -> bool:
    """@brief 타입 힌트가 불변 타입으로만 이뤄졌는지 본다."""
    origin = typing.get_origin(tp)
    if origin in (typing.Union, pytypes.UnionType, tuple, frozenset):
        return all(_is_immutable_type(a, seen) for a in typing.get_args(tp))
    if isinstance(tp, typing.TypeAliasType):
        # 재귀 타입 별칭(FrozenValue)은 한 번만 펼친다.
        if tp in seen:
            return True
        return _is_immutable_type(tp.__value__, seen | {tp})
    if tp is Ellipsis:
        return True
    if inspect.isclass(tp):
        if issubclass(tp, _IMMUTABLE_ATOMS) or issubclass(tp, t.enum.Enum):
            return True
        params = getattr(tp, "__dataclass_params__", None)
        return params is not None and params.frozen
    return False


def test_types_module_defines_dataclasses():
    assert len(_dataclasses()) >= 8


def test_all_types_dataclasses_are_frozen_with_slots():
    for cls in _dataclasses():
        assert cls.__dataclass_params__.frozen, cls.__name__
        assert "__slots__" in cls.__dict__, cls.__name__


def test_all_types_dataclass_fields_are_immutable():
    for cls in _dataclasses():
        hints = typing.get_type_hints(cls)
        for field in dataclasses.fields(cls):
            assert _is_immutable_type(hints[field.name]), (
                f"{cls.__name__}.{field.name}"
            )


def test_real_source_tree_has_no_architecture_violations():
    from pathlib import Path

    from tools.arch_rules import check_tree

    assert check_tree(Path("src")) == []
