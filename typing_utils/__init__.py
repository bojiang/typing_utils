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
}


STATIC_SUBTYPE_MAPPING = {
    io.TextIOWrapper: typing.TextIO,
    io.TextIOBase: typing.TextIO,
    io.StringIO: typing.TextIO,
    io.BufferedReader: typing.BinaryIO,
    io.BufferedWriter: typing.BinaryIO,
    io.BytesIO: typing.BinaryIO,
}


forward_context = {}


def ensure_builtin(tp):
    if tp in BUILTINS_MAPPING:
        return BUILTINS_MAPPING[tp]
    return tp


get_type_hints = typing.get_type_hints

GenericClass = type(typing.List)
UnionClass = type(typing.Union)


def get_origin(tp):
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
    return ensure_builtin(ori)


def get_args(tp):
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
    if res is None:
        return ()
    else:
        return res


def eval_forward_ref(fr, forward_dict=None):
    local = forward_dict or {}
    if hasattr(fr, "_evaluate"):  # python3.8
        return fr._evaluate(globals(), local)
    if hasattr(fr, "_eval_type"):  # python3.6
        return fr._eval_type(globals(), local)
    raise NotImplementedError()


class Ntype(typing.NamedTuple):
    origin: type
    args: tuple = tuple()

    def __eq__(self, other):
        if isinstance(other, Ntype):
            return self.origin == other.origin and self.args == other.args
        if not self.args:
            return self.origin == other
        return False

    def __repr__(self):
        if not self.args:
            return f"{self.origin}"
        return f"{self.origin}[{self.args}])"


def normalize(tp) -> Ntype:
    args = get_args(tp)
    origin = get_origin(tp)
    if not origin:
        return Ntype(ensure_builtin(tp))
    origin = ensure_builtin(origin)

    if origin is typing.Union:  # sort args when the origin is Union
        args = tuple(sorted(tuple(frozenset(normalize(a) for a in args)), key=repr))
    else:
        args = tuple(normalize(a) for a in args)
    return Ntype(origin, args)


def is_origin_subtype(left: type, right: type) -> bool:
    if right is typing.Any:
        return True

    if left in STATIC_SUBTYPE_MAPPING and right == STATIC_SUBTYPE_MAPPING[left]:
        return True

    if hasattr(left, "mro"):
        for su in left.mro():
            if su == right:
                return True

    if issubclass(left, right):
        return True

    return left == right


def is_normal_subtype(
    left: Ntype, right: Ntype, forward_dict: typing.Mapping[str, type]
):
    if isinstance(left.origin, ForwardRef):
        left = normalize(eval_forward_ref(left.origin, forward_dict=forward_dict))

    if isinstance(right.origin, ForwardRef):
        right = normalize(eval_forward_ref(right.origin, forward_dict=forward_dict))

    if not left.args and not right.args:
        return is_origin_subtype(left.origin, right.origin)

    if not right.args:
        return is_origin_subtype(left.origin, right.origin)

    if right.origin == left.origin == typing.Union:
        excluded = frozenset(left.args) - frozenset(right.args)
        if not excluded:
            return True
        return all(
            any(is_normal_subtype(e, r, forward_dict) for r in right.args)
            for e in excluded
        )

    if right.origin == typing.Union:
        return any(is_normal_subtype(left, a, forward_dict) for a in right.args)

    if is_origin_subtype(left.origin, right.origin):
        return all(
            al is not None
            and ar is not None
            and is_normal_subtype(al, ar, forward_dict)
            for al, ar in itertools.zip_longest(left.args, right.args)
        )
    return False


def issubtype(left: type, right: type, forward_dict: typing.Optional[dict] = None):
    return is_normal_subtype(normalize(left), normalize(right), forward_dict)
