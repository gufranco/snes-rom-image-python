import sys
from collections.abc import Sequence
from pathlib import Path
from typing import Any

sys.path.append(str(Path(__file__).resolve().parent.parent / "snes-mapper-python"))

import mapper
from mapper.header import HEADER_BYTES, TITLE_BYTES, NoHeader

MAP_MODE = 0x15
CHIPSET = 0x16
ROM_SIZE = 0x17
SRAM_SIZE = 0x18
CHECKSUM_COMPLEMENT = 0x1C
CHECKSUM = 0x1E

CHIPSET_ROM_ONLY = 0x00
CHECKSUM_FIELD_SUM = 0x01FE
CHECKSUM_FIELD_BYTES = 4
CHECKSUM_FIELD_NEUTRAL = b"\xff\xff\x00\x00"

KILOBYTE = 1024

PADDING = frozenset({0x20, 0x00, 0xFF})

COPROCESSORS = {
    0x03: "DSP",
    0x05: "DSP",
    0x13: "SuperFX",
    0x14: "SuperFX",
    0x15: "SuperFX",
    0x1A: "SuperFX",
    0x25: "OBC1",
    0x32: "SA-1",
    0x34: "SA-1",
    0x35: "SA-1",
    0x43: "S-DD1",
    0x45: "S-DD1",
    0x55: "S-RTC",
    0xE3: "Super Game Boy",
    0xF3: "CX4",
    0xF5: "SPC7110",
    0xF6: "ST010",
    0xF9: "SPC7110",
}


def size_byte(length: int) -> int:
    kilobytes = max(1, (length + KILOBYTE - 1) // KILOBYTE)
    exponent = 0
    while (1 << exponent) < kilobytes:
        exponent += 1
    return exponent


def identifies(block: bytes | bytearray) -> bool:
    return bool(set(block) - PADDING)


def anchor_of(image: bytes | bytearray) -> int | None:
    try:
        at: int = mapper.read(image).at
        return at
    except NoHeader:
        return None


def mirrors(image: bytes | bytearray) -> list[int]:
    anchor = anchor_of(image)
    if anchor is None:
        return []

    block = bytes(image[anchor : anchor + HEADER_BYTES])
    if not identifies(block):
        return [anchor]

    found = []
    at = image.find(block)
    while at != -1:
        found.append(at)
        at = image.find(block, at + HEADER_BYTES)
    return found


def describe(image: bytes | bytearray) -> list[dict[str, Any]]:
    return [
        {
            "at": at,
            "title": bytes(image[at : at + TITLE_BYTES]).decode("ascii", "replace").strip(),
            "map": image[at + MAP_MODE],
            "chipset": image[at + CHIPSET],
            "coprocessor": COPROCESSORS.get(image[at + CHIPSET]),
            "size": image[at + ROM_SIZE],
            "sram": image[at + SRAM_SIZE],
            "checksum": image[at + CHECKSUM] | (image[at + CHECKSUM + 1] << 8),
        }
        for at in mirrors(image)
    ]


def mirrored_sum(data: bytes | bytearray) -> int:
    length = len(data)
    if length == 0:
        return 0
    if length & (length - 1) == 0:
        return sum(data)
    head = 1
    while head * 2 <= length:
        head *= 2
    rest = data[head:]
    filled = 1
    while filled < len(rest):
        filled *= 2
    return sum(data[:head]) + mirrored_sum(rest) * (head // filled)


def checksum(image: bytes | bytearray, places: Sequence[int] | None = None) -> int:
    places = mirrors(image) if places is None else places
    neutral = bytearray(image)
    for at in places:
        start = at + CHECKSUM_COMPLEMENT
        neutral[start : start + CHECKSUM_FIELD_BYTES] = CHECKSUM_FIELD_NEUTRAL
    return mirrored_sum(neutral) & 0xFFFF


def declare_rom_only(image: bytes | bytearray) -> bytes:
    places = mirrors(image)
    if not places:
        raise NoHeader("no cartridge header at any documented position")

    declared = bytearray(image)
    for at in places:
        declared[at + CHIPSET] = CHIPSET_ROM_ONLY
        declared[at + ROM_SIZE] = size_byte(len(image))

    value = checksum(declared, places)
    complement = value ^ 0xFFFF
    for at in places:
        declared[at + CHECKSUM_COMPLEMENT] = complement & 0xFF
        declared[at + CHECKSUM_COMPLEMENT + 1] = complement >> 8
        declared[at + CHECKSUM] = value & 0xFF
        declared[at + CHECKSUM + 1] = value >> 8

    return bytes(declared)


def needs_rewrite(image: bytes | bytearray) -> bool:
    places = mirrors(image)
    if not places:
        raise NoHeader("no cartridge header at any documented position")

    wanted = size_byte(len(image))
    return any(
        image[at + CHIPSET] != CHIPSET_ROM_ONLY or image[at + ROM_SIZE] != wanted for at in places
    )


BLOCK_BYTES = 0x1000


def changes(
    before: bytes | bytearray, after: bytes | bytearray, block: int = BLOCK_BYTES
) -> list[int]:
    found: list[int] = []
    for start in range(0, len(before), block):
        stop = start + block
        if before[start:stop] == after[start:stop]:
            continue
        found.extend(at for at in range(start, min(stop, len(before))) if before[at] != after[at])
    return found
