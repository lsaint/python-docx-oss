"""Own temporary handles, borrow caller streams, and restore seekable positions."""

from __future__ import annotations

import io
import os
from collections.abc import Generator
from contextlib import contextmanager
from tempfile import SpooledTemporaryFile
from typing import BinaryIO, TypeAlias, cast

PackageSource: TypeAlias = str | os.PathLike[str] | bytes | BinaryIO


@contextmanager
def open_source(source: PackageSource) -> Generator[BinaryIO, None, None]:
    if isinstance(source, bytes):
        with io.BytesIO(source) as stream:
            yield stream
    elif isinstance(source, (str, os.PathLike)):
        with open(source, "rb") as stream:
            yield stream
    elif hasattr(source, "read") and hasattr(source, "seekable"):
        stream = source
        if stream.seekable():
            position = stream.tell()
            try:
                stream.seek(0)
                yield stream
            finally:
                stream.seek(position)
        else:
            # ZIP requires seeking. Spill large forward-only inputs to disk.
            with SpooledTemporaryFile(max_size=1024 * 1024) as spool:
                while chunk := stream.read(64 * 1024):
                    spool.write(chunk)
                spool.seek(0)
                yield cast(BinaryIO, spool)
    else:
        raise TypeError("source must be a path, raw bytes, or a binary stream")
