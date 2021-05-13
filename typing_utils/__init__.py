'''
Backport Python3.8+ typing utils &amp; issubtype &amp; more

![Python 3.6](https://github.com/bojiang/typing_utils/workflows/Python%203.6/badge.svg)
![Python 3.7](https://github.com/bojiang/typing_utils/workflows/Python%203.7/badge.svg)
![Python 3.8](https://github.com/bojiang/typing_utils/workflows/Python%203.8/badge.svg)

## Install

``` bash
    pip install typing_utils
```
'''


import collections.abc
import io
import itertools
import typing

if hasattr(typing, "ForwardRef"):  # python3.8
    ForwardRef = getattr(typing, "ForwardRef")
elif hasattr(typing, "_ForwardRef"):  # python3.6
    ForwardRef = getattr(typing, "_ForwardRef")
else:
    raise NotImplementedError()

BUILTINS_MAPPING = {
    typing.List: list,
    typing.Set: set,
    typing.Dict: dict,
    typing.Tuple: tuple,
    typing.ByteString: bytes,  # https://docs.python.org/3/library/typing.html#typing.ByteString
    typing.Callable: collections.abc.Callable,
    typing.Sequence: collections.abc.Sequence,
}


STATIC_SUBTYPE_MAPPING: typing.Dict[type, typing.Type] = {
    io.TextIOWrapper: typing.TextIO,
    io.TextIOBase: typing.TextIO,
    io.StringIO: typing.TextIO,
    io.BufferedReader: typing.BinaryIO,
    io.BufferedWriter: typing.BinaryIO,
    io.BytesIO: typing.BinaryIO,
}


def _hashable(v):
    """Determine whether `v` can be hashed."""
    try:
        hash(v)
    except TypeError:
        return False
    return True


def _ensure_builtin(tp):
    assert _hashable(tp), "_ensure_builtin should only be called on element types"

    if tp in BUILTINS_MAPPING:
        return BUILTINS_MAPPING[tp]
    return tp


get_type_hints = typing.get_type_hints

GenericClass = type(typing.List)
UnionClass = type(typing.Union)


def get_origin(tp):
    """Get the unsubscripted version of a type.
    This supports generic types, Callable, Tuple, Union, Literal, Final and ClassVar.
    Return None for unsupported types.

    Examples:

    ```python
        from typing_utils import get_origin

        get_origin(Literal[42]) is Literal
        get_origin(int) is None
        get_origin(ClassVar[int]) is ClassVar
        get_origin(Generic) is Generic
        get_origin(Generic[T]) is Generic
        get_origin(Union[T, int]) is Union
        get_origin(List[Tuple[T, T]][int]) == list
    ```
    """
    if hasattr(typing, 'get_origin'):  # python 3.8+
        _getter = getattr(typing, "get_origin")
        ori = _getter(tp)
    elif hasattr(typing.List, "_special"):  # python 3.7
        if isinstance(tp, GenericClass) and not tp._special:
            ori = tp.__origin__
        elif hasattr(tp, "_special") and tp._special:
            ori = tp
        elif tp is typing.Generic:
            ori = typing.Generic
        else:
            ori = None
    else:  # python 3.6
        if isinstance(tp, GenericClass):
            ori = tp.__origin__
            if ori is None:
                ori = tp
        elif isinstance(tp, UnionClass):
            ori = tp.__origin__
        elif tp is typing.Generic:
            ori = typing.Generic
        else:
            ori = None
    return _ensure_builtin(ori)


def get_args(tp) -> typing.Tuple:
    """Get type arguments with all substitutions performed.
    For unions, basic simplifications used by Union constructor are performed.

    Examples:

    ```python
        from typing_utils import get_args

        get_args(Dict[str, int]) == (str, int)
        get_args(int) == ()
        get_args(Union[int, Union[T, int], str][int]) == (int, str)
        get_args(Union[int, Tuple[T, int]][str]) == (int, Tuple[str, int])
        get_args(Callable[[], T][int]) == ([], int)
    ```
    """
    if hasattr(typing, 'get_args'):  # python 3.8+
        _getter = getattr(typing, "get_args")
        res = _getter(tp)
    elif hasattr(typing.List, "_special"):  # python 3.7
        if isinstance(tp, GenericClass) and not tp._special:  # backport for python 3.8
            res = tp.__args__
            if get_origin(tp) is collections.abc.Callable and res[0] is not Ellipsis:
                res = (list(res[:-1]), res[-1])
        else:
            res = ()
    else:  # python 3.6
        if isinstance(tp, (GenericClass, UnionClass)):  # backport for python 3.8
            res = tp.__args__
            if get_origin(tp) is collections.abc.Callable and res[0] is not Ellipsis:
                res = (list(res[:-1]), res[-1])
        else:
            res = ()
    return () if res is None else res


def eval_forward_ref(fr, forward_refs=None):
    localns = forward_refs or {}
    if hasattr(typing, "_eval_type"):  # python3.8 & python 3.9
        return typing._eval_type(fr, globals(), localns)
    if hasattr(fr, "_eval_type"):  # python3.6
        return fr._eval_type(globals(), localns)
    raise NotImplementedError()


class NormalizedType(typing.NamedTuple):
    '''
    Normalized type, made it possible to compare, hash between types.
    '''

    origin: type
    args: typing.Union[tuple, frozenset] = tuple()

    def __eq__(self, other):
        if isinstance(other, NormalizedType):
            if self.origin != other.origin:
                return False
            if isinstance(self.args, frozenset) and isinstance(other.args, frozenset):
                return self.args <= other.args and other.args <= self.args
            return self.origin == other.origin and self.args == other.args
        if not self.args:
            return self.origin == other
        return False

    def __hash__(self) -> int:
        if not self.args:
            return hash(self.origin)
        return hash((self.origin, self.args))

    def __repr__(self):
        if not self.args:
            return f"{self.origin}"
        return f"{self.origin}[{self.args}])"


TypeArgs = typing.Union[type, typing.AbstractSet[type], typing.Sequence[type]]


def _normalize_args(tps: TypeArgs):
    if isinstance(tps, collections.abc.Sequence):
        return tuple(_normalize_args(tp) for tp in tps)
    if isinstance(tps, collections.abc.Set):
        return frozenset(_normalize_args(tp) for tp in tps)
    return normalize(tps)


def normalize(type_: type) -> NormalizedType:
    '''
    convert types to NormalizedType instances.
    '''
    args = get_args(type_)
    origin = get_origin(type_)
    if not origin:
        return NormalizedType(_ensure_builtin(type_))
    origin = _ensure_builtin(origin)

    if origin is typing.Union:  # sort args when the origin is Union
        args = _normalize_args(frozenset(args))
    else:
        args = _normalize_args(args)
    return NormalizedType(origin, args)


def _is_origin_subtype(left: type, right: type) -> bool:
    if left is right:
        return True

    if right is typing.Any:
        return True

    if left in STATIC_SUBTYPE_MAPPING and right == STATIC_SUBTYPE_MAPPING[left]:
        return True

    if hasattr(left, "mro"):
        for parent in left.mro():
            if parent == right:
                return True

    if isinstance(left, type):  # issubclass() arg 1 must be a class
        return issubclass(left, right)

    return left == right


NormalizedTypeArgs = typing.Union[
    typing.Tuple["NormalizedTypeArgs", ...],
    typing.FrozenSet[NormalizedType],
    NormalizedType,
]


def _is_origin_subtype_args(
    left: NormalizedTypeArgs,
    right: NormalizedTypeArgs,
    forward_refs: typing.Optional[typing.Mapping[str, type]],
) -> bool:
    if isinstance(left, frozenset):
        if not isinstance(right, frozenset):
            return False

        excluded = left - right
        if not excluded:
            # Union[str, int] <> Union[int, str]
            return True

        # Union[list, int] <> Union[typing.Sequence, int]
        return all(
            any(_is_normal_subtype(e, r, forward_refs) for r in right) for e in excluded
        )

    if isinstance(left, collections.abc.Sequence) and not isinstance(
        left, NormalizedType
    ):
        if not isinstance(right, collections.abc.Sequence) or isinstance(
            right, NormalizedType
        ):
            return False

        if (
            left
            and left[-1].origin is not Ellipsis
            and right
            and right[-1].origin is Ellipsis
        ):
            # Tuple[type, type] <> Tuple[type, ...]
            return all(_is_origin_subtype_args(l, right[0], forward_refs) for l in left)

        if len(left) != len(right):
            return False

        return all(
            l is not None
            and r is not None
            and _is_origin_subtype_args(l, r, forward_refs)
            for l, r in itertools.zip_longest(left, right)
        )

    assert isinstance(left, NormalizedType)
    assert isinstance(right, NormalizedType)

    return _is_normal_subtype(left, right, forward_refs)


def _is_normal_subtype(
    left: NormalizedType,
    right: NormalizedType,
    forward_refs: typing.Optional[typing.Mapping[str, type]],
):
    if isinstance(left.origin, ForwardRef):
        left = normalize(eval_forward_ref(left.origin, forward_refs=forward_refs))

    if isinstance(right.origin, ForwardRef):
        right = normalize(eval_forward_ref(right.origin, forward_refs=forward_refs))

    if not left.args and not right.args:
        return _is_origin_subtype(left.origin, right.origin)

    if not right.args:
        return _is_origin_subtype(left.origin, right.origin)

    if right.origin == left.origin == typing.Union:
        return _is_origin_subtype_args(left.args, right.args, forward_refs)
    if right.origin == typing.Union:
        return any(_is_normal_subtype(left, a, forward_refs) for a in right.args)

    if _is_origin_subtype(left.origin, right.origin):
        return _is_origin_subtype_args(left.args, right.args, forward_refs)

    return False


def issubtype(left: type, right: type, forward_refs: typing.Optional[dict] = None):
    """Check that the left argument is a subtype of the right.
    For unions, check if the type arguments of the left is a subset of the right.
    Also works for nested types including ForwardRefs.

    Examples:

    ```python
        from typing_utils import issubtype

        issubtype(typing.List, typing.Any) == True
        issubtype(list, list) == True
        issubtype(list, typing.List) == True
        issubtype(list, typing.Sequence) == True
        issubtype(typing.List[int], list) == True
        issubtype(typing.List[typing.List], list) == True
        issubtype(list, typing.List[int]) == False
        issubtype(list, typing.Union[typing.Tuple, typing.Set]) == False
        issubtype(typing.List[typing.List], typing.List[typing.Sequence]) == True
        JSON = typing.Union[
            int, float, bool, str, None, typing.Sequence["JSON"],
            typing.Mapping[str, "JSON"]
        ]
        issubtype(str, JSON, forward_refs={'JSON': JSON}) == True
        issubtype(typing.Dict[str, str], JSON, forward_refs={'JSON': JSON}) == True
        issubtype(typing.Dict[str, bytes], JSON, forward_refs={'JSON': JSON}) == False
    ```
    """
    return _is_normal_subtype(normalize(left), normalize(right), forward_refs)


__all__ = [
    "issubtype",
    "get_origin",
    "get_args",
    "get_type_hints",
]
