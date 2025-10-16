from typing import Any

from loguru import logger

_MISSING = object()


def get_nested(
    data: dict | list, *path: str | int, default: Any = _MISSING, strict: bool = False
) -> Any:
    """Dynamic, safe traversal using Python 3.10+ structural pattern matching."""
    cur = data
    for i, key in enumerate(path, 1):
        try:
            match cur, key:
                case dict() as d, str() as k:
                    if k in d:
                        cur = d[k]
                    else:
                        msg = f"Key '{k}' not found at path: {path[:i]}"
                        if strict:
                            raise KeyError(msg)
                        logger.debug(msg)
                        return None if default is _MISSING else default
                case list() as lst, int() as idx:
                    try:
                        cur = lst[idx]
                    except IndexError as e:
                        msg = f"Index {idx} out of range at path: {path[:i]}"
                        if strict:
                            raise IndexError(msg) from e
                        logger.debug(msg)
                        return None if default is _MISSING else default
                case dict(), int() | list(), str():
                    exp = "dict" if isinstance(key, str) else "list"
                    act = type(cur).__name__
                    msg = f"Type mismatch at {path[:i]} - expected {exp}, got {act}"
                    if strict:
                        raise TypeError(msg)
                    logger.debug(msg)
                    return None if default is _MISSING else default
                case _:
                    msg = f"Unsupported structure at {path[:i]} (type: {type(cur).__name__})"
                    if strict:
                        raise TypeError(msg)
                    logger.debug(msg)
                    return None if default is _MISSING else default
        except (TypeError, KeyError, IndexError):
            if strict:
                raise
            return None if default is _MISSING else default
    return cur
