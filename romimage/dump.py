import re
import sys
import zlib
from collections.abc import Sequence
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent.parent / "snes-mapper-python"))

from mapper import COPIER_BYTES, has_copier_stub, stub_by_length

from .errors import NoParts

PART_SUFFIX = re.compile(r"^\.\d{1,3}$")

BARE = "bare"
COPIER = "copier header"

BLOCK_BYTES = 0x10000
DEFLATE_LEVEL = 6

CHUNK_BYTES = 1024
CHUNK_STRIDE = 512


def strip_copier_stub(data: bytes) -> bytes:
    return data[COPIER_BYTES:] if has_copier_stub(data) else data


def parts_in(folder: Path | str) -> list[Path]:
    found = [
        path
        for path in Path(folder).rglob("*")
        if path.is_file() and PART_SUFFIX.match(path.suffix)
    ]
    return sorted(found, key=lambda path: path.name.upper())


def join(parts: Sequence[bytes]) -> bytes:
    if not parts:
        return b""
    return b"".join([strip_copier_stub(parts[0]), *parts[1:]])


def form(path: Path | str) -> str:
    path = Path(path)
    if path.is_dir():
        return f"{len(parts_in(path))} part set"
    return COPIER if stub_by_length(path.stat().st_size) else BARE


def read(path: Path | str) -> bytes:
    path = Path(path)
    if not path.is_dir():
        return strip_copier_stub(path.read_bytes())

    parts = parts_in(path)
    if not parts:
        raise NoParts(f"{path} holds no numbered parts to join")
    return join([part.read_bytes() for part in parts])


def deflate_ratio(block: bytes) -> float:
    if not block:
        return 0.0
    return len(zlib.compress(block, DEFLATE_LEVEL)) / len(block)


def block_ratios(data: bytes, block: int = BLOCK_BYTES) -> list[float]:
    return [deflate_ratio(data[i : i + block]) for i in range(0, len(data) - block + 1, block)]


def chunk_index(
    data: bytes, chunk: int = CHUNK_BYTES, stride: int = CHUNK_STRIDE
) -> dict[bytes, int]:
    index: dict[bytes, int] = {}
    for i in range(0, len(data) - chunk + 1, stride):
        index.setdefault(data[i : i + chunk], i)
    return index


def measure_reuse(
    source: bytes, target: bytes, chunk: int = CHUNK_BYTES, stride: int = CHUNK_STRIDE
) -> tuple[int, int]:
    index = chunk_index(target, chunk=chunk, stride=stride)
    found = total = 0
    for i in range(0, len(source) - chunk + 1, chunk):
        total += 1
        if source[i : i + chunk] in index:
            found += 1
    return found, total
