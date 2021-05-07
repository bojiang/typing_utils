'''
common tests
'''
import collections.abc
import io
import typing

from typing_utils import get_args, get_origin, issubtype, normalize

JSON = typing.Union[
    int, float, bool, str, None, typing.Sequence["JSON"], typing.Mapping[str, "JSON"]
]


def test_normalize():
    assert normalize(list) == normalize(typing.List) == list
    assert normalize(typing.Union) == typing.Union
    assert normalize(typing.Union[int, typing.List, list]) == normalize(
        typing.Union[typing.List, list, int]
    )

    assert normalize(typing.Union[typing.List[int], int]) == normalize(
        typing.Union[int, typing.List[int], int]
    )
    assert normalize(typing.Union[typing.List[int], int]) != normalize(
        typing.Union[typing.List, int]
    )


def test_generic_utils():
    assert get_origin(list) is None
    assert get_origin(typing.Union) is None

    assert get_args(typing.List) == tuple()
    assert get_origin(typing.List) == list

    assert get_args(typing.List[int]) == (int,)
    assert get_origin(typing.List[int]) == list
    assert get_args(typing.List[str]) != (int,)

    assert get_origin(typing.Union[int, str]) == typing.Union
    assert get_args(typing.Union[int, str]) == (int, str)

    fun = typing.Callable[[str, int], int]
    assert get_origin(fun) == collections.abc.Callable
    assert get_args(fun) == ([str, int], int)

    PayloadType = typing.TypeVar("PayloadType")

    class TypeA(typing.Generic[PayloadType]):
        def __init__(self, payload: PayloadType):
            self.payload = payload

    assert get_origin(TypeA[int]) == TypeA
    assert get_args(TypeA[int]) == (int,)


def test_is_subtype():
    # Any
    assert issubtype(typing.List, typing.Any)
    assert issubtype(typing.Any, typing.Any)

    # Self
    assert issubtype(list, list)
    assert issubtype(typing.List, typing.List)
    assert not issubtype(list, dict)
    assert not issubtype(typing.List, typing.Dict)

    # alias
    assert issubtype(list, typing.List)
    assert issubtype(typing.List, list)
    assert issubtype(bytes, typing.ByteString)

    # Subclass
    assert issubtype(list, typing.Sequence)

    # FileLike
    with open("test", "wb") as f:
        assert issubtype(type(f), typing.BinaryIO)
    with open("test", "rb") as f:
        assert issubtype(type(f), typing.BinaryIO)
    with open("test", "w") as f:
        assert issubtype(type(f), typing.TextIO)
    with open("test", "r") as f:
        assert issubtype(type(f), typing.TextIO)

    assert issubtype(type(io.BytesIO(b"0")), typing.BinaryIO)
    assert issubtype(type(io.StringIO("0")), typing.TextIO)

    # subscribed generic
    assert issubtype(typing.List[int], list)
    assert issubtype(typing.List[typing.List], list)
    assert not issubtype(list, typing.List[int])

    # Union
    assert issubtype(list, typing.Union[typing.List, typing.Tuple])
    assert not issubtype(list, typing.Union[typing.Tuple, typing.Set])
    assert not issubtype(typing.Tuple[typing.Union[int, None]], typing.Tuple[None])

    # Nested containers
    assert issubtype(typing.List[int], typing.List[int])
    assert issubtype(typing.List[typing.List], typing.List[typing.Sequence])

    assert issubtype(typing.Dict[typing.List, int], typing.Dict[typing.Sequence, int])
    assert issubtype(
        typing.Callable[[typing.List, int], int],
        typing.Callable[[typing.Sequence, int], int],
    )
    assert not issubtype(
        typing.Callable[[typing.Sequence, int], int],
        typing.Callable[[typing.List, int], int],
    )

    # ForwardRef
    assert issubtype(int, JSON, forward_refs={'JSON': JSON})
    assert issubtype(str, JSON, forward_refs={'JSON': JSON})
    assert issubtype(typing.Dict[str, str], JSON, forward_refs={'JSON': JSON})
    assert not issubtype(typing.Dict[str, bytes], JSON, forward_refs={'JSON': JSON})

    assert issubtype(
        typing.Dict[str, str], typing.Union[JSON, bytes], forward_refs={'JSON': JSON}
    )
    assert not issubtype(
        typing.Dict[str, bytes], typing.Union[JSON, bytes], forward_refs={'JSON': JSON}
    )

    # Ellipsis
    assert issubtype(typing.Tuple[list], typing.Tuple[list, ...])
    assert issubtype(typing.Tuple[typing.List], typing.Tuple[list, ...])
    assert issubtype(typing.Tuple[list, list], typing.Tuple[typing.Sequence, ...])
    assert not issubtype(typing.Tuple[list, int], typing.Tuple[typing.Sequence, ...])
    assert issubtype(typing.Tuple[list, ...], typing.Tuple[list, ...])
    assert issubtype(typing.Tuple[list, ...], typing.Tuple[typing.Sequence, ...])
    assert not issubtype(typing.Tuple[list, ...], typing.Tuple[list])
