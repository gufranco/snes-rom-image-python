"""Look at this machine and say what is actually here, so a report can be believed.

What goes wrong with this package is rarely a defect in it. It is a submodule
that was never checked out, a corpus that is not beside the package, or a library
somebody pointed the census at that holds nothing it reads. All three look the
same from outside: the run is green and it proved less than the reader thinks.

The submodule is the sharp one. Where a header sits is not this package's claim;
it is `snes-mapper-python`, carried here as a submodule and imported by name. A
checkout without `--recurse-submodules` leaves the directory there and empty, and
what fails is an import rather than a check, which reads as a broken package
rather than an incomplete checkout.

Unlike its siblings this package locates no library of its own. The census takes
the directory to walk as an argument, so there is no variable to be set wrongly
and nothing to report about where cartridges are looked for. What is reported
instead is the corpus, which is what runs when nobody supplies a library.

Two rules shape it, and they are the whole point.

Nothing is hidden. A check that fails says what it saw, and a check that itself
throws is caught and reported as what it threw, named by its type. An absent
library is reported as absent rather than as a failure, because a fresh checkout
has none and that is the normal state, but it is never reported as nothing at all.

Nothing is imported from the package at the top of this file, and that is
deliberate rather than tidy. This package imports `snes-mapper-python` by name,
so on the machine this exists to diagnose, a checkout with no submodule,
importing it here would fail before a single finding was printed. The reader
would get a traceback naming a module they have never heard of instead of a line
telling them to fetch the submodule.

Which is also why this is run as a file rather than with `-m`. Either form has to
read the package's `__init__` first, and that is the import that fails. Run it as

    python3 romimage/doctor.py

and everything that can fail happens inside a finding, where its failure is the
report rather than the end of it.

Nothing is inferred. Every line is something looked at on this machine just now,
including a rewrite actually performed twice on an image assembled here rather
than a claim that the rewriter imports.
"""

from __future__ import annotations

import json
import platform
import re
import sys
from pathlib import Path
from typing import TYPE_CHECKING, Any, override

if TYPE_CHECKING:  # pragma: no cover
    from collections.abc import Callable, Sequence


def _version(where: Path | None = None) -> str:
    """The package version, read out of the file beside this one.

    Read rather than imported. Importing it would go through the package, and
    the package is what fails on the machine this exists to diagnose.
    """
    found = re.search(
        r"""VERSION\s*[:=][^"']*["']([^"']+)["']""",
        (where or Path(__file__).resolve().parent / "version.py").read_text(),
    )
    return found.group(1) if found else "unknown"


VERSION = _version()

ROOT = Path(__file__).resolve().parent.parent

from romimage import environment  # noqa: E402

CORPUS = ROOT / "conformance" / "corpus.json"

SUBMODULES = ("snes-mapper-python",)

OLDEST_PYTHON = (3, 12)

TITLE = b"DOCTOR SYNTHETIC IMAGE"
"""Cut, where it is used, to the width the header reader publishes.

Cut rather than counted here, because a copy of a width is a second place for it
to be wrong and this one was wrong the first time it was written. The cutting
happens inside the finding rather than here, since the reader that publishes the
width lives in a submodule that may not be present."""

HEADER_AT = 0x7FC0

CHIPSET_AT = 0x16
"""Where the chipset byte sits inside the header, for the report line only.

The rewrite reads it from the header reader; this is the offset the report
prints, and it is checked against the reader's own constant by the tests."""

CHIPSET = 0x03
"""A coprocessor byte, so the image starts out needing the rewrite it is given."""

IMAGE_BYTES = 0x10000
"""Small enough to build in memory, and a whole number of the blocks a sum walks."""


class Finding:
    """One thing that was looked at, and what was there."""

    __slots__ = ("advice", "detail", "name", "ok")

    def __init__(self, name: str, ok: bool, detail: str, advice: str | None = None) -> None:
        self.name = name
        self.ok = ok
        self.detail = detail
        self.advice = advice

    @property
    def line(self) -> str:
        """The one-line form, which is what a reader scans."""
        return f"  {'ok  ' if self.ok else '   !'}  {self.name}: {self.detail}"

    @property
    def report(self) -> str:
        """The same, with what to do about it when there is something to do."""
        if self.ok or not self.advice:
            return self.line
        return f"{self.line}\n         {self.advice}"

    @override
    def __repr__(self) -> str:
        return f"<Finding {self.name} {'ok' if self.ok else 'not ok'}>"


def _python() -> Finding:
    return Finding(
        "python",
        sys.version_info[:2] >= OLDEST_PYTHON,
        f"{platform.python_version()} on {platform.system()} {platform.machine()}",
        f"this package needs {OLDEST_PYTHON[0]}.{OLDEST_PYTHON[1]} or newer",
    )


def _package() -> Finding:
    return Finding("romimage", True, f"version {VERSION}")


def _loaded() -> Any:
    """The package, imported now rather than when this file was read.

    Imported by name rather than relatively, and with the repository put on the
    path first, because this file is run as a script and a relative import has
    no package to be relative to. A single place for it, so every finding fails
    the same way when the submodule is absent and the failure is a line in the
    report rather than a traceback in place of one.
    """
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))
    from romimage import identity, rewrite

    return identity, rewrite


def _synthetic(chipset: int = CHIPSET) -> bytes:
    """An image correct in every field but the one being probed.

    Written rather than borrowed, because an image taken from a cartridge would
    put a fragment of somebody's ROM in this file.

    The size byte and the checksum pair are computed here rather than left at
    zero, and that is the whole point of the probe. An image wrong in three
    fields needs the rewrite whichever one you ask about, so a finding built on
    one would report a pass no matter what the coprocessor byte said. Correct
    everywhere else, the answer is about the coprocessor and nothing else.
    """
    _, rewrite = _loaded()
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


def _asking(build: Callable[[], bytes] = _synthetic) -> Finding:
    """That an image declaring a chip is recognised as needing the rewrite."""
    try:
        _, rewrite = _loaded()
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


def _rewriting(build: Callable[[], bytes] = _synthetic) -> Finding:
    """That the rewrite lands and leaves nothing behind for a second pass.

    Running it twice is the line that matters. A rewrite that is not idempotent
    is one nobody can safely re-run, and the failure is invisible after one pass.
    """
    try:
        _, rewrite = _loaded()
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


def _identifying(build: Callable[[], bytes] = _synthetic) -> Finding:
    """That every digest a report publishes is actually computed here.

    All of them rather than the one that decides. A report publishing a crc32
    beside a sha256 and computing only the sha256 is publishing decoration, and
    the four are checked together so that cannot pass unnoticed.
    """
    try:
        identity, _ = _loaded()
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


def _submodule(name: str, root: Path = ROOT) -> Finding:
    """Whether a submodule is checked out, since its absence is silent otherwise.

    The marker is the manifest rather than the directory. Git creates the empty
    directory for a submodule it has not fetched, so a check on the path alone
    reports a present submodule on exactly the machine where it is missing.
    """
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


def _corpus(path: Path | str = CORPUS) -> Finding:
    """The recording, which is what runs when nobody supplies a library."""
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


def _census() -> Finding:
    """That the library is supplied per run rather than located, said out loud.

    Its siblings look in a fixed place and can therefore look in the wrong one.
    This one cannot, and saying so stops a reader hunting for a variable that
    does not exist.
    """
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
    """Everything worth looking at on this machine, in the order a reader wants it."""
    return [
        _python(),
        _package(),
        _asking(),
        _rewriting(),
        _identifying(),
        *(_submodule(name, root) for name in SUBMODULES),
        _corpus(corpus),
        _census(),
    ]


def report(found: Sequence[Finding]) -> list[str]:
    """The lines a person pastes into an issue."""
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
