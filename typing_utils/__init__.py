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


import collections
import contextlib
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
}


STATIC_SUBTYPE_MAPPING = {
    io.TextIOWrapper: typing.TextIO,
    io.TextIOBase: typing.TextIO,
    io.StringIO: typing.TextIO,
    io.BufferedReader: typing.BinaryIO,
    io.BufferedWriter: typing.BinaryIO,
    io.BytesIO: typing.BinaryIO,
}


def _ensure_builtin(tp):
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


def get_args(tp):
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
    local = forward_refs or {}
    if hasattr(typing, "_eval_type"):  # python3.8 & python 3.9
        return typing._eval_type(fr, globals(), local)
    if hasattr(fr, "_eval_type"):  # python3.6
        return fr._eval_type(globals(), local)
    raise NotImplementedError()


class NormalizedType(typing.NamedTuple):
    origin: type
    args: tuple = tuple()

    def __eq__(self, other):
        if isinstance(other, NormalizedType):
            return self.origin == other.origin and self.args == other.args
        if not self.args:
            return self.origin == other
        return False

    def __repr__(self):
        if not self.args:
            return f"{self.origin}"
        return f"{self.origin}[{self.args}])"


def normalize(tp: type) -> NormalizedType:
    args = get_args(tp)
    origin = get_origin(tp)
    if not origin:
        return NormalizedType(_ensure_builtin(tp))
    origin = _ensure_builtin(origin)

    if origin is typing.Union:  # sort args when the origin is Union
        args = tuple(sorted(tuple(frozenset(normalize(a) for a in args)), key=repr))
    else:
        args = tuple(normalize(a) for a in args)
    return NormalizedType(origin, args)


def _is_origin_subtype(left: type, right: type) -> bool:
    if left is right:
        return True

    if right is typing.Any:
        return True

    if left in STATIC_SUBTYPE_MAPPING and right == STATIC_SUBTYPE_MAPPING[left]:
        return True

    if hasattr(left, "mro"):
        for su in left.mro():
            if su == right:
                return True

    if isinstance(left, type):  # issubclass() arg 1 must be a class
        return issubclass(left, right)

    return left == right


def _is_normal_subtype(
    left: NormalizedType, right: NormalizedType, forward_refs: typing.Mapping[str, type]
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
        excluded = frozenset(left.args) - frozenset(right.args)
        if not excluded:
            return True
        return all(
            any(_is_normal_subtype(e, r, forward_refs) for r in right.args)
            for e in excluded
        )

    if right.origin == typing.Union:
        return any(_is_normal_subtype(left, a, forward_refs) for a in right.args)

    if _is_origin_subtype(left.origin, right.origin):
        if (
            left.args
            and left.args[-1].origin is not Ellipsis
            and right.args[-1].origin is Ellipsis
        ):
            ar = right.args[0]
            return all(_is_normal_subtype(al, ar, forward_refs) for al in left.args)
        return all(
            al is not None
            and ar is not None
            and _is_normal_subtype(al, ar, forward_refs)
            for al, ar in itertools.zip_longest(left.args, right.args)
        )
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
