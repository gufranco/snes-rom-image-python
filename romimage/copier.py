import sys
from collections.abc import Callable
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent.parent / "snes-mapper-python"))

import mapper
from mapper import image as placement
from mapper.header import LOROM, WHOLEBANK, WHOLEBANK_BYTES, board

from . import rewrite
from .errors import Unmappable

COPIER_BYTES = 0x200

GAME_DOCTOR_MAGIC = b"GAME DOCTOR SF 3"
GAME_DOCTOR_SAVE_BYTE = 0x10
GAME_DOCTOR_MAP_BYTE = 0x11
GAME_DOCTOR_CHUNK = 0x80000
GAME_DOCTOR_CHUNK_CODE = 0x20
GAME_DOCTOR_CHUNKS = 0x20
GAME_DOCTOR_SAVE_RAM = 0x40
GAME_DOCTOR_SAVE_SLOTS = (0x24, 0x28)
GAME_DOCTOR_SAVE_CODES = {0: 0x80, 0x800: 0x82, 0x2000: 0x81, 0x8000: 0x80}
GAME_DOCTOR_SLOT_BANKS = 16

HALF = 0x8000
UPPER = 0x8000
LOWER = 0x0000
WORK_RAM_BANKS = frozenset({0x7E, 0x7F})

GAME_DOCTOR_SLOTS = (
    tuple((first, UPPER) for first in range(0x00, 0x80, GAME_DOCTOR_SLOT_BANKS))
    + tuple((first, UPPER) for first in range(0x80, 0x100, GAME_DOCTOR_SLOT_BANKS))
    + tuple((first, LOWER) for first in range(0x40, 0x80, GAME_DOCTOR_SLOT_BANKS))
    + tuple((first, LOWER) for first in range(0xC0, 0x100, GAME_DOCTOR_SLOT_BANKS))
)

SD2SNES_CHIPSETS = frozenset({0x43, 0x45})

Place = Callable[[int, int], int]


def lorom_place(size: int) -> Place:
    def place(bank: int, page: int) -> int:
        return ((bank & 0x7F) * HALF + (page & (HALF - 1))) % size

    return place


def wholebank_place(size: int) -> Place:
    banks = placement.bank_count(size)

    def place(bank: int, page: int) -> int:
        found: int = placement.address_to_file(bank, page, banks)
        return found

    return place


def _check_slot(place: Place, first: int, page: int, start: int) -> None:
    for bank in range(first, first + GAME_DOCTOR_SLOT_BANKS):
        if bank in WORK_RAM_BANKS:
            continue
        expected = start + (bank - first) * HALF
        for address in (page, page | (HALF - 1)):
            if place(bank, address) != expected + (address & (HALF - 1)):
                raise Unmappable(
                    f"${bank:02X}:{address:04X} does not follow the chunk its slot starts,"
                    " so no Game Doctor map byte can place it"
                )


def _slot_code(place: Place, first: int, page: int) -> int:
    start = place(first, page)
    chunk, within = divmod(start, GAME_DOCTOR_CHUNK)
    if within or chunk >= GAME_DOCTOR_CHUNKS:
        raise Unmappable(
            f"banks ${first:02X}-${first + GAME_DOCTOR_SLOT_BANKS - 1:02X} at ${page:04X}"
            f" begin at file offset {start:#x}, which is not the start of a 4 Mbit chunk"
        )
    _check_slot(place, first, page, start)
    return GAME_DOCTOR_CHUNK_CODE + chunk


def game_doctor_map(place: Place) -> bytes:
    return bytes(_slot_code(place, first, page) for first, page in GAME_DOCTOR_SLOTS)


def game_doctor_header(place: Place, save_ram_bytes: int = 0) -> bytes:
    if save_ram_bytes not in GAME_DOCTOR_SAVE_CODES:
        raise Unmappable(f"the Game Doctor has no code for {save_ram_bytes} bytes of save RAM")
    header = bytearray(COPIER_BYTES)
    header[: len(GAME_DOCTOR_MAGIC)] = GAME_DOCTOR_MAGIC
    header[GAME_DOCTOR_SAVE_BYTE] = GAME_DOCTOR_SAVE_CODES[save_ram_bytes]
    layout = game_doctor_map(place)
    header[GAME_DOCTOR_MAP_BYTE : GAME_DOCTOR_MAP_BYTE + len(layout)] = layout
    if save_ram_bytes:
        for slot in GAME_DOCTOR_SAVE_SLOTS:
            header[slot] = GAME_DOCTOR_SAVE_RAM
    return bytes(header)


def place_of(image: bytes | bytearray) -> Place:
    layout = board(mapper.read(bytes(image)), len(image))
    if layout == WHOLEBANK:
        return wholebank_place(len(image))
    if layout == LOROM:
        return lorom_place(len(image))
    raise Unmappable(
        f"a Game Doctor map is derived here for lorom and wholebank images, not {layout}"
    )


def for_game_doctor(image: bytes | bytearray) -> bytes:
    save_ram_bytes: int = mapper.read(bytes(image)).ram_bytes
    if save_ram_bytes and len(image) == WHOLEBANK_BYTES:
        raise Unmappable(
            "a whole-bank image keeps graphics where a Game Doctor maps save RAM,"
            " and where its save RAM belongs instead has not been measured"
        )
    return game_doctor_header(place_of(image), save_ram_bytes) + bytes(image)


def for_sd2snes(image: bytes | bytearray, chipset: int) -> bytes:
    if len(image) != WHOLEBANK_BYTES:
        raise Unmappable(
            f"the sd2snes form is the {WHOLEBANK_BYTES:#x} byte whole-bank image;"
            f" this one is {len(image):#x} bytes and runs on the firmware as it is"
        )
    if chipset not in SD2SNES_CHIPSETS:
        raise Unmappable(
            f"the sd2snes firmware picks this map only for chipset $43 or $45, not ${chipset:02X}"
        )
    return bytes(COPIER_BYTES) + rewrite.declare_chipset(image, chipset)
