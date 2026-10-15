import hashlib
import zlib
from collections.abc import Mapping
from typing import Any

from .errors import NoAuthority

AUTHORITATIVE = "sha256"

INTEROPERABLE = ("crc32", "md5", "sha1")


def measure(data: bytes) -> dict[str, Any]:
    return {
        "size": len(data),
        "crc32": f"{zlib.crc32(data):08X}",
        "md5": hashlib.md5(data).hexdigest(),
        "sha1": hashlib.sha1(data).hexdigest(),
        AUTHORITATIVE: hashlib.sha256(data).hexdigest(),
    }


def agrees(found: Mapping[str, Any], expected: Mapping[str, Any]) -> bool:
    if AUTHORITATIVE not in expected:
        raise NoAuthority(f"an expectation with no {AUTHORITATIVE} cannot accept or reject")
    agreed: bool = found.get(AUTHORITATIVE) == expected[AUTHORITATIVE]
    return agreed
