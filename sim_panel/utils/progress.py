from __future__ import annotations

from typing import Iterable, Iterator, Optional, TypeVar

T = TypeVar("T")


def tqdm_wrap(it: Iterable[T], *, total: Optional[int] = None, desc: str = "", enabled: bool = True) -> Iterator[T]:
    """
    Wrap an iterable with tqdm if enabled, else yield items unchanged.
    """
    if not enabled:
        for x in it:
            yield x
        return

    try:
        from tqdm import tqdm  # type: ignore
    except Exception:
        # Fallback: no tqdm installed
        for x in it:
            yield x
        return

    for x in tqdm(it, total=total, desc=desc):
        yield x