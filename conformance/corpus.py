import json
import sys
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from romimage import rewrite

CORPUS = Path(__file__).resolve().parent / "corpus.json"


def load(path: Path | str | None = None) -> dict[str, Any]:
    held: dict[str, Any] = json.loads(Path(path or CORPUS).read_text())
    return held


def check(document: Mapping[str, Any]) -> list[dict[str, Any]]:
    wrong: list[dict[str, Any]] = []
    for case in document["cases"]:
        wanted = rewrite.size_byte(case["size"])
        if case["size_byte"] != wanted:
            wrong.append({"case": case, "why": "size_byte", "wanted": wanted})
            continue

        dirty = (
            case["chipset"] != rewrite.without_coprocessor(case["chipset"])
            or case["rom_size"] != wanted
        )
        if dirty and not case["needs_rewrite"]:
            wrong.append({"case": case, "why": "needs_rewrite", "wanted": True})
    return wrong


def report(document: Mapping[str, Any], wrong: Sequence[Mapping[str, Any]]) -> None:
    cases = document["cases"]
    print(f"  {len(cases)} declarations from {CORPUS.name}")
    print(f"  measured across {document['measured_across']} cartridges")
    print(f"  {len(cases) - len(wrong)} agreed, {len(wrong)} did not")
    for entry in wrong[:10]:
        case = entry["case"]
        print(
            f"  {entry['why']}: size {case['size']} chipset {case['chipset']:#04x} "
            f"rom_size {case['rom_size']:#04x} wanted {entry['wanted']}"
        )


def main(argv: Sequence[str]) -> int:
    if len(argv) > 2:
        print("usage: corpus.py [corpus.json]", file=sys.stderr)
        return 2

    document = load(argv[1] if len(argv) == 2 else None)
    wrong = check(document)
    report(document, wrong)
    return 1 if wrong else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
