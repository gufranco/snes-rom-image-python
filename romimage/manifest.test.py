import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.append(str(ROOT / "snes-mapper-python"))

import json  # noqa: E402
import random  # noqa: E402
import tempfile  # noqa: E402
import unittest  # noqa: E402
from pathlib import Path  # noqa: E402
from typing import Any, override  # noqa: E402

from romimage import Malformed, identity, manifest, rewrite  # noqa: E402

NAME = "A Cartridge, Japanese"


def _blank(banks: int = 2, seed: int = 1) -> bytearray:
    generator = random.Random(seed)
    return bytearray(generator.randrange(256) for _ in range(banks * 0x10000))


def _cartridge(banks: int = 2, seed: int = 1, at: int = 0x007FC0, chipset: int = 0x43) -> bytes:
    image = _blank(banks, seed)
    image[at : at + 21] = b"A CARTRIDGE          "
    image[at + rewrite.MAP_MODE] = 0x20
    image[at + rewrite.CHIPSET] = chipset
    image[at + rewrite.ROM_SIZE] = 0x09
    image[at + rewrite.SRAM_SIZE] = 0x00
    image[at + rewrite.CHECKSUM_COMPLEMENT : at + rewrite.CHECKSUM_COMPLEMENT + 4] = bytes(4)
    return bytes(image)


GOOD = _cartridge()
DONE = rewrite.declare_rom_only(GOOD)
OTHER = _cartridge(seed=2)
CORRUPT = _cartridge(seed=3)


def _document() -> dict[str, Any]:
    return {
        "canonical": {"form": "one file, no copier stub"},
        "artifacts": [
            {
                "name": NAME,
                "filename": "a-cartridge-jp.sfc",
                "accepted": [identity.measure(GOOD)],
                "rewritten": identity.measure(DONE),
                "bad": [dict(identity.measure(CORRUPT), why="overdump")],
            }
        ],
    }


def _without(field: str) -> dict[str, Any]:
    document = _document()
    artifact = {key: value for key, value in document["artifacts"][0].items() if key != field}
    return dict(document, artifacts=[artifact])


class LoadTest(unittest.TestCase):
    def test_a_document_is_taken_as_given(self) -> None:
        # Arrange
        document = _document()

        # Act
        held = manifest.Manifest(document)

        # Assert
        self.assertEqual(len(held.artifacts), 1)

    def test_a_path_is_read_from_disk(self) -> None:
        # Arrange
        path = Path(tempfile.mkdtemp()) / "artifacts.manifest.json"
        path.write_text(json.dumps(_document()))

        # Act
        held = manifest.Manifest.from_path(path)

        # Assert
        self.assertEqual(len(held.artifacts), 1)

    def test_a_document_with_no_artifacts_is_refused(self) -> None:
        # Arrange
        document: dict[str, Any] = {"canonical": {}}

        # Act
        with self.assertRaises(Malformed) as refused:
            manifest.Manifest(document)

        # Assert
        self.assertIn("no artifacts", str(refused.exception))

    def test_an_artifact_with_no_accepted_form_is_refused(self) -> None:
        # Arrange
        document = {"artifacts": [{"name": "x", "accepted": []}]}

        # Act
        with self.assertRaises(Malformed) as refused:
            manifest.Manifest(document)

        # Assert
        self.assertIn("x lists no accepted form", str(refused.exception))

    def test_an_accepted_form_with_no_deciding_value_is_refused(self) -> None:
        # Arrange
        document = {"artifacts": [{"name": "x", "accepted": [{"crc32": "0"}]}]}

        # Act
        with self.assertRaises(Malformed) as refused:
            manifest.Manifest(document)

        # Assert
        self.assertIn("x has an accepted form with no sha256", str(refused.exception))


class MatchTest(unittest.TestCase):
    @override
    def setUp(self) -> None:
        self.manifest = manifest.Manifest(_document())

    def test_the_file_it_expects_is_recognised(self) -> None:
        # Arrange
        data = GOOD

        # Act
        found = self.manifest.diagnose(data)

        # Assert
        self.assertEqual(found["state"], manifest.KNOWN)

    def test_an_already_rewritten_file_is_recognised_as_that(self) -> None:
        # Arrange
        data = DONE

        # Act
        found = self.manifest.diagnose(data)

        # Assert
        self.assertEqual(found["state"], manifest.REWRITTEN)

    def test_a_dump_it_knows_to_be_damaged_is_named_as_damaged(self) -> None:
        # Arrange
        data = CORRUPT

        # Act
        found = self.manifest.diagnose(data)

        # Assert
        self.assertEqual((found["state"], found["why"]), (manifest.BAD_DUMP, "overdump"))

    def test_a_file_of_the_right_size_and_wrong_content_says_so(self) -> None:
        # Arrange
        data = OTHER

        # Act
        found = self.manifest.diagnose(data)

        # Assert
        self.assertEqual(found["state"], manifest.SAME_SIZE)

    def test_a_file_of_no_recognised_size_is_simply_unknown(self) -> None:
        # Arrange
        data = bytes(0x1000)

        # Act
        found = self.manifest.diagnose(data)

        # Assert
        self.assertEqual(found["state"], manifest.UNKNOWN)

    def test_a_copier_stub_comes_off_before_the_comparison(self) -> None:
        # Arrange
        data = bytes(0x200) + GOOD

        # Act
        found = self.manifest.diagnose(data)

        # Assert
        self.assertEqual((found["state"], found["form"]), (manifest.KNOWN, "copier header"))

    def test_the_form_is_reported_as_given_when_one_is_supplied(self) -> None:
        # Arrange
        form = "4 part set"

        # Act
        found = self.manifest.diagnose(GOOD, form=form)

        # Assert
        self.assertEqual(found["form"], "4 part set")

    def test_what_it_computed_is_reported_whether_or_not_it_matched(self) -> None:
        # Arrange
        data = OTHER

        # Act
        found = self.manifest.diagnose(data)

        # Assert
        self.assertEqual(found["identity"]["sha256"], identity.measure(OTHER)["sha256"])

    def test_a_recognised_file_names_the_artifact_it_is(self) -> None:
        # Arrange
        data = GOOD

        # Act
        found = self.manifest.diagnose(data)

        # Assert
        self.assertEqual(found["artifact"]["name"], NAME)

    def test_an_unrecognised_file_names_no_artifact(self) -> None:
        # Arrange
        data = bytes(0x1000)

        # Act
        found = self.manifest.diagnose(data)

        # Assert
        self.assertIsNone(found["artifact"])

    def test_the_headers_it_found_come_back_with_the_verdict(self) -> None:
        # Arrange
        data = GOOD

        # Act
        found = self.manifest.diagnose(data)

        # Assert
        self.assertEqual(found["headers"][0]["coprocessor"], "S-DD1")

    def test_a_manifest_that_lists_no_damaged_dumps_still_answers(self) -> None:
        # Arrange
        held = manifest.Manifest(_without("bad"))

        # Act
        found = held.diagnose(CORRUPT)

        # Assert
        self.assertEqual(found["state"], manifest.SAME_SIZE)

    def test_a_manifest_that_lists_no_rewritten_form_still_answers(self) -> None:
        # Arrange
        held = manifest.Manifest(_without("rewritten"))

        # Act
        found = held.diagnose(DONE)

        # Assert
        self.assertEqual(found["state"], manifest.SAME_SIZE)


class ExplainTest(unittest.TestCase):
    @override
    def setUp(self) -> None:
        self.manifest = manifest.Manifest(_document())

    def test_it_always_prints_what_it_computed(self) -> None:
        # Arrange
        found = self.manifest.diagnose(OTHER)

        # Act
        said = self.manifest.explain(found)

        # Assert
        self.assertIn(identity.measure(OTHER)["sha256"], said)

    def test_a_recognised_file_is_named(self) -> None:
        # Arrange
        found = self.manifest.diagnose(GOOD)

        # Act
        said = self.manifest.explain(found)

        # Assert
        self.assertIn(NAME, said)

    def test_an_already_rewritten_file_says_so_rather_than_reading_as_wrong(self) -> None:
        # Arrange
        found = self.manifest.diagnose(DONE)

        # Act
        said = self.manifest.explain(found)

        # Assert
        self.assertIn("already", said)

    def test_a_damaged_dump_says_damaged_rather_than_wrong(self) -> None:
        # Arrange
        found = self.manifest.diagnose(CORRUPT)

        # Act
        said = self.manifest.explain(found)

        # Assert
        self.assertIn("overdump", said)

    def test_a_same_size_miss_says_what_to_suspect(self) -> None:
        # Arrange
        found = self.manifest.diagnose(OTHER)

        # Act
        said = self.manifest.explain(found)

        # Assert
        self.assertIn("contents do not", said)

    def test_an_unknown_file_says_the_manifest_does_not_know_it(self) -> None:
        # Arrange
        found = self.manifest.diagnose(bytes(0x1000))

        # Act
        said = self.manifest.explain(found)

        # Assert
        self.assertIn("not a file", said)

    def test_every_header_it_found_is_printed(self) -> None:
        # Arrange
        found = self.manifest.diagnose(GOOD)

        # Act
        said = self.manifest.explain(found)

        # Assert
        self.assertIn("S-DD1", said)


if __name__ == "__main__":
    unittest.main()
