import hashlib
import json
import os
import sys
from collections.abc import Iterator, Mapping, Sequence
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from romimage import dump, rewrite  # noqa: E402

RECORD = ROOT / "conformance" / "testroms.json"

READINGS = ROOT / "conformance" / "testcarts.json"

DIRECTORY_VARIABLE = "SNES_TEST_CARTRIDGE_DIR"

ALONGSIDE = ROOT.parent / "snes-roms" / "5 Tools & Service Test Carts"

SUFFIXES = (".sfc", ".smc")

NOT_PRESENT = 2

PLACEHOLDER = {"complement": 0x0000, "checksum": 0xFFFF}

AGREES = "agrees"
NO_HEADER = "no header"
PLACEHOLDER_PAIR = "placeholder pair"
NOT_COMPLEMENTS = "not complements"
DISAGREES = "disagrees"

ACCOUNTED = frozenset({AGREES, NO_HEADER, PLACEHOLDER_PAIR, NOT_COMPLEMENTS})


def directory(environment: Mapping[str, str] | None = None) -> Path:
    held = os.environ if environment is None else environment
    named = held.get(DIRECTORY_VARIABLE, "").strip()
    return Path(named) if named else ALONGSIDE


def wanted(record: Mapping[str, Any]) -> dict[str, str]:
    return {str(entry["sha256"]): str(entry["id"]) for entry in record["cartridges"]}


def present(where: Path, digests: Mapping[str, str]) -> Iterator[tuple[str, bytes]]:
    if not where.is_dir():
        return
    for path in sorted(where.rglob("*")):
        if path.is_file() and path.suffix.lower() in SUFFIXES:
            blob = path.read_bytes()
            name = digests.get(hashlib.sha256(blob).hexdigest())
            if name is not None:
                yield name, blob


def word(image: bytes, at: int) -> int:
    return image[at] | (image[at + 1] << 8)


def header_of(image: bytes, places: Sequence[int]) -> dict[str, int]:
    at = places[0]
    return {
        "at": at,
        "map": image[at + rewrite.MAP_MODE],
        "chipset": image[at + rewrite.CHIPSET],
        "rom_size": image[at + rewrite.ROM_SIZE],
        "sram_size": image[at + rewrite.SRAM_SIZE],
        "complement": word(image, at + rewrite.CHECKSUM_COMPLEMENT),
        "checksum": word(image, at + rewrite.CHECKSUM),
        "computed": rewrite.checksum(image, places),
        "mirrors": len(places),
    }


def account(found: Mapping[str, Any]) -> str:
    header = found["header"]
    if header is None:
        return NO_HEADER
    if header["computed"] == header["checksum"]:
        return AGREES
    pair = {"complement": header["complement"], "checksum": header["checksum"]}
    if pair == PLACEHOLDER:
        return PLACEHOLDER_PAIR
    if header["complement"] ^ header["checksum"] != 0xFFFF:
        return NOT_COMPLEMENTS
    return DISAGREES


def reading(blob: bytes) -> dict[str, Any]:
    image = dump.strip_copier_stub(blob)
    places = rewrite.mirrors(image)
    found = {"size": len(image), "header": header_of(image, places) if places else None}
    return {**found, "account": account(found)}


def measured(where: Path, record: Mapping[str, Any]) -> dict[str, dict[str, Any]]:
    return {name: reading(blob) for name, blob in present(where, wanted(record))}


def problems_with(name: str, one: Mapping[str, Any], held: Mapping[str, Any]) -> list[str]:
    moved = ["read differently from the record"] if held.get(name) != one else []
    unaccounted = (
        [f"{one['account']}, not accounted for"] if one["account"] not in ACCOUNTED else []
    )
    return [f"{name}: {why}" for why in (*moved, *unaccounted)]


def problems(found: Mapping[str, Any], held: Mapping[str, Any]) -> list[str]:
    return [line for name, one in sorted(found.items()) for line in problems_with(name, one, held)]


def report(found: Mapping[str, Any], listed: int, wrong: Sequence[str]) -> None:
    print(f"  {len(found)} of {listed} test cartridges present")
    for name, one in sorted(found.items()):
        print(f"  {name}: {one['account']}")
    for line in wrong:
        print(f"  FAILED {line}")


def load(path: Path) -> dict[str, Any]:
    held: dict[str, Any] = json.loads(path.read_text())
    return held


def understood(argv: Sequence[str]) -> bool:
    return len(argv) == 1 or (len(argv) == 3 and argv[1] == "--record")


def main(
    argv: Sequence[str],
    environment: Mapping[str, str] | None = None,
    record: Path = RECORD,
    readings: Path = READINGS,
) -> int:
    if not understood(argv):
        print("usage: testcarts.py [--record out.json]", file=sys.stderr)
        return 2
    listed = load(record)
    found = measured(directory(environment), listed)
    if not found:
        print(f"  no test cartridge present: set {DIRECTORY_VARIABLE} to a folder holding one")
        return NOT_PRESENT
    if len(argv) == 3:
        Path(argv[2]).write_text(json.dumps(found, indent=2, sort_keys=True) + "\n")
    wrong = problems(found, load(readings)) if len(argv) == 1 else []
    report(found, len(listed["cartridges"]), wrong)
    return 1 if wrong else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
