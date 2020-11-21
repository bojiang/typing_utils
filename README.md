# typing-utils

Backport Python3.8+ typing utils &amp; issubtype &amp; more

- [Install](#install)
- [API](#api)
    - [issubtype](#issubtype)
    - [get_origin](#get_origin)
    - [get_args](#get_args)
    - [get_type_hints](#get_type_hints)

![Python 3.6](https://github.com/bojiang/typing_utils/workflows/Python%203.6/badge.svg)
![Python 3.7](https://github.com/bojiang/typing_utils/workflows/Python%203.7/badge.svg)
![Python 3.8](https://github.com/bojiang/typing_utils/workflows/Python%203.8/badge.svg)

## Install

``` bash
    pip install typing_utils
```


## API

- [issubtype](#issubtype)
- [get_origin](#get_origin)
- [get_args](#get_args)
- [get_type_hints](#get_type_hints)


### issubtype

Check that the left argument is a subtype of the right.

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


### get_origin

Get the unsubscripted version of a type.

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


### get_args

Get type arguments with all substitutions performed.

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


### get_type_hints

Return type hints for an object.


This is often the same as obj.__annotations__, but it handles
forward references encoded as string literals, and if necessary
adds Optional[t] if a default value equal to None is set.

The argument may be a module, class, method, or function. The annotations
are returned as a dictionary. For classes, annotations include also
inherited members.

TypeError is raised if the argument is not of a type that can contain
annotations, and an empty dictionary is returned if no annotations are
present.

BEWARE -- the behavior of globalns and localns is counterintuitive
(unless you are familiar with how eval() and exec() work).  The
search order is locals first, then globals.

- If no dict arguments are passed, an attempt is made to use the
  globals from obj (or the respective module's globals for classes),
  and these are also used as the locals.  If the object does not appear
  to have globals, an empty dictionary is used.

- If one dict argument is passed, it is used for both globals and
  locals.

- If two dict arguments are passed, they specify globals and
  locals, respectively.
