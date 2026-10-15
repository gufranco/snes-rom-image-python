import json
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from . import dump, identity, rewrite
from .errors import Malformed

KNOWN = "known"
REWRITTEN = "rewritten"
BAD_DUMP = "bad dump"
SAME_SIZE = "same size"
UNKNOWN = "unknown"


def _checked(document: Mapping[str, Any]) -> Mapping[str, Any]:
    artifacts = document.get("artifacts")
    if not artifacts:
        raise Malformed("a manifest with no artifacts cannot accept or reject anything")
    for artifact in artifacts:
        accepted = artifact.get("accepted")
        if not accepted:
            raise Malformed(f"{artifact.get('name', 'an artifact')} lists no accepted form")
        for form in accepted:
            if identity.AUTHORITATIVE not in form:
                raise Malformed(
                    f"{artifact.get('name', 'an artifact')} has an accepted form with no "
                    f"{identity.AUTHORITATIVE}, which is the only value that decides"
                )
    return document


class Manifest:
    __slots__ = ("document",)

    def __init__(self, document: Mapping[str, Any]) -> None:
        self.document = _checked(document)

    @classmethod
    def from_path(cls, path: Path | str) -> "Manifest":
        return cls(json.loads(Path(path).read_text()))

    @property
    def artifacts(self) -> tuple[Mapping[str, Any], ...]:
        held: tuple[Mapping[str, Any], ...] = tuple(self.document["artifacts"])
        return held

    def by_digest(self, found: Mapping[str, Any]) -> Mapping[str, Any] | None:
        for artifact in self.artifacts:
            for accepted in artifact["accepted"]:
                if identity.agrees(found, accepted):
                    return {"state": KNOWN, "artifact": artifact}
            written = artifact.get("rewritten")
            if written and identity.agrees(found, written):
                return {"state": REWRITTEN, "artifact": artifact}
            for bad in artifact.get("bad", ()):
                if identity.agrees(found, bad):
                    return {"state": BAD_DUMP, "artifact": artifact, "why": bad.get("why")}
        return None

    def by_size(self, size: int) -> tuple[Mapping[str, Any], ...]:
        return tuple(
            artifact
            for artifact in self.artifacts
            for accepted in artifact["accepted"]
            if accepted.get("size") == size
        )

    def diagnose(self, data: bytes, form: str | None = None) -> Mapping[str, Any]:
        held = dump.strip_copier_stub(data)
        found = identity.measure(held)
        matched = self.by_digest(found)
        same_size = [artifact["name"] for artifact in self.by_size(len(held))]

        return {
            "form": form or (dump.COPIER if len(held) != len(data) else dump.BARE),
            "size": len(held),
            "identity": found,
            "state": matched["state"] if matched else (SAME_SIZE if same_size else UNKNOWN),
            "artifact": matched["artifact"] if matched else None,
            "why": matched.get("why") if matched else None,
            "same_size": same_size,
            "headers": rewrite.describe(held),
        }

    def explain(self, found: Mapping[str, Any]) -> str:
        lines = [
            f"  size    {found['size']:,} bytes, read as {found['form']}",
            f"  crc32   {found['identity']['crc32']}",
            f"  sha256  {found['identity']['sha256']}",
        ]
        for entry in found["headers"]:
            declared = entry["coprocessor"] or "none"
            lines.append(
                f"  header at {entry['at']:#08x}  {entry['title']!r}  map {entry['map']:02X}  "
                f"chipset {entry['chipset']:02X} ({declared})  size {entry['size']:02X}"
            )

        if found["state"] == KNOWN:
            lines.append(f"  known   {found['artifact']['name']}")
        elif found["state"] == REWRITTEN:
            lines.append(f"  already rewritten: {found['artifact']['name']}")
        elif found["state"] == BAD_DUMP:
            lines.append(f"  a known bad dump of {found['artifact']['name']}: {found['why']}")
            lines.append("  find another copy; this one cannot be repaired from itself")
        elif found["state"] == SAME_SIZE:
            lines.append(f"  size matches {', '.join(found['same_size'])}, contents do not")
            lines.append("  a different build, a different revision, or a damaged copy")
        else:
            lines.append("  not a file this manifest knows")
        return "\n".join(lines)
