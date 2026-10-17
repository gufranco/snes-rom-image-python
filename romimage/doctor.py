from __future__ import annotations

import json
import platform
import re
import sys
from pathlib import Path
from typing import TYPE_CHECKING, Any, override

if TYPE_CHECKING:  # pragma: no cover
    from collections.abc import Callable, Sequence


def installed_version(where: Path | None = None) -> str:
    found = re.search(
        r"""VERSION\s*[:=][^"']*["']([^"']+)["']""",
        (where or Path(__file__).resolve().parent / "version.py").read_text(),
    )
    return found.group(1) if found else "unknown"


VERSION = installed_version()

ROOT = Path(__file__).resolve().parent.parent


def reachable(root: Path = ROOT, path: list[str] | None = None) -> bool:
    where = sys.path if path is None else path
    if str(root) in where:
        return False
    where.insert(0, str(root))
    return True


reachable()

from romimage import environment  # noqa: E402

CORPUS = ROOT / "conformance" / "corpus.json"

SUBMODULES = ("snes-mapper-python",)

OLDEST_PYTHON = (3, 12)

TITLE = b"DOCTOR SYNTHETIC IMAGE"

HEADER_AT = 0x7FC0

CHIPSET_AT = 0x16

CHIPSET = 0x03

IMAGE_BYTES = 0x10000


class Finding:
    __slots__ = ("advice", "detail", "name", "ok")

    def __init__(self, name: str, ok: bool, detail: str, advice: str | None = None) -> None:
        self.name = name
        self.ok = ok
        self.detail = detail
        self.advice = advice

    @property
    def line(self) -> str:
        return f"  {'ok  ' if self.ok else '   !'}  {self.name}: {self.detail}"

    @property
    def report(self) -> str:
        if self.ok or not self.advice:
            return self.line
        return f"{self.line}\n         {self.advice}"

    @override
    def __repr__(self) -> str:
        return f"<Finding {self.name} {'ok' if self.ok else 'not ok'}>"


def check_python() -> Finding:
    return Finding(
        "python",
        sys.version_info[:2] >= OLDEST_PYTHON,
        f"{platform.python_version()} on {platform.system()} {platform.machine()}",
        f"this package needs {OLDEST_PYTHON[0]}.{OLDEST_PYTHON[1]} or newer",
    )


def check_package() -> Finding:
    return Finding("romimage", True, f"version {VERSION}")


def load_package() -> Any:
    reachable()
    from romimage import identity, rewrite

    return identity, rewrite


def synthetic_image(chipset: int = CHIPSET) -> bytes:
    _, rewrite = load_package()
    title = TITLE[: rewrite.TITLE_BYTES]
    rom = bytearray(b"\x00" * IMAGE_BYTES)
    rom[HEADER_AT : HEADER_AT + len(title)] = title
    rom[HEADER_AT + rewrite.MAP_MODE] = 0x20
    rom[HEADER_AT + rewrite.CHIPSET] = chipset
    rom[HEADER_AT + rewrite.ROM_SIZE] = rewrite.size_byte(IMAGE_BYTES)
    total = rewrite.mirrored_sum(bytes(rom))
    rom[HEADER_AT + rewrite.CHECKSUM_COMPLEMENT] = (~total) & 0xFF
    rom[HEADER_AT + rewrite.CHECKSUM_COMPLEMENT + 1] = ((~total) >> 8) & 0xFF
    rom[HEADER_AT + rewrite.CHECKSUM] = total & 0xFF
    rom[HEADER_AT + rewrite.CHECKSUM + 1] = (total >> 8) & 0xFF
    return bytes(rom)


def check_asking(build: Callable[[], bytes] = synthetic_image) -> Finding:
    try:
        _, rewrite = load_package()
        held = rewrite.needs_rewrite(build())
    except Exception as trouble:
        return Finding(
            "recognising a declaration",
            False,
            f"{type(trouble).__name__}: {trouble}",
            "the reader failed on an image built here, so nothing about a real"
            " cartridge can be trusted from this machine",
        )
    return Finding(
        "recognising a declaration",
        held,
        f"an image declaring coprocessor {CHIPSET:#04x} is"
        + ("" if held else " not")
        + " reported as needing the rewrite",
        "an image that declares a chip it does not carry is exactly what this"
        " package exists to find, and this one was missed",
    )


def check_rewriting(build: Callable[[], bytes] = synthetic_image) -> Finding:
    try:
        _, rewrite = load_package()
        once = rewrite.declare_rom_only(build())
        twice = rewrite.declare_rom_only(once)
    except Exception as trouble:
        return Finding(
            "rewriting",
            False,
            f"{type(trouble).__name__}: {trouble}",
            "the rewrite failed on an image built here, which is the finding",
        )
    settled = not rewrite.needs_rewrite(once) and once == twice
    return Finding(
        "rewriting",
        settled,
        f"chipset byte {once[HEADER_AT + CHIPSET_AT]:#04x} after one pass,"
        f" and a second pass {'changed nothing' if once == twice else 'changed it again'}",
        "a rewrite that is not settled after one pass cannot safely be re-run",
    )


def check_identifying(build: Callable[[], bytes] = synthetic_image) -> Finding:
    try:
        identity, _ = load_package()
        wanted = (identity.AUTHORITATIVE, *identity.INTEROPERABLE)
        held = identity.measure(build())
    except Exception as trouble:
        return Finding(
            "identifying",
            False,
            f"{type(trouble).__name__}: {trouble}",
            "measuring an image built here failed, which is the finding",
        )
    missing = sorted(name for name in wanted if not held.get(name))
    return Finding(
        "identifying",
        not missing,
        f"{held.get('size')} bytes, "
        + ", ".join(f"{name} {str(held.get(name))[:8]}" for name in wanted),
        f"nothing was computed for {', '.join(missing)}, and a digest a report"
        " publishes without computing is decoration",
    )


def check_submodule(name: str, root: Path = ROOT) -> Finding:
    where = root / name
    if (where / "pyproject.toml").is_file():
        return Finding(f"submodule {name}", True, f"checked out at {where}")
    return Finding(
        f"submodule {name}",
        False,
        f"{where} is empty" if where.is_dir() else f"{where} is not there",
        "the checks that read a real cartridge import from this and will skip"
        " rather than run; git submodule update --init --recursive",
    )


def check_corpus(path: Path | str = CORPUS) -> Finding:
    try:
        held = json.loads(Path(path).read_text())
    except OSError as trouble:
        return Finding(
            "corpus",
            False,
            f"could not be read: {trouble}",
            "the corpus is what the checks run against on a machine with no"
            " cartridges; without it they have nothing to read",
        )
    except ValueError as trouble:
        return Finding("corpus", False, f"is not readable as JSON: {trouble}")
    cases = held.get("cases") or []
    return Finding(
        "corpus",
        bool(cases),
        f"{len(cases)} recorded cases, measured across"
        f" {held.get('measured_across', 'a number not stated')}",
        "a corpus with no cases proves nothing",
    )


def check_census() -> Finding:
    return Finding(
        "library",
        True,
        "supplied to conformance/census.py as an argument, so there is no"
        " directory to be set wrongly and none to report",
    )


def examine(
    corpus: Path | str = CORPUS,
    root: Path = ROOT,
) -> list[Finding]:
    return [
        check_python(),
        check_package(),
        check_asking(),
        check_rewriting(),
        check_identifying(),
        *(check_submodule(name, root) for name in SUBMODULES),
        check_corpus(corpus),
        check_census(),
    ]


def report(found: Sequence[Finding]) -> list[str]:
    unwell = [one for one in found if not one.ok]
    lines = [f"romimage {VERSION} on {platform.python_version()}, {platform.system()}", ""]
    lines.append("  the machine")
    lines.extend(environment.lines(ROOT))
    lines.append("")
    lines.append("  this package")
    lines.extend(one.report for one in found)
    lines.append("")
    if unwell:
        lines.append(f"  {len(unwell)} of {len(found)} checks did not pass")
    else:
        lines.append(f"  {len(found)} checks, nothing to report")
    return lines


def main(
    argv: Sequence[str] = (),
    examine: Callable[..., list[Finding]] = examine,
    say: Callable[[str], None] = print,
) -> int:
    found = examine()
    for line in report(found):
        say(line)
    return 1 if any(not one.ok for one in found) else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
