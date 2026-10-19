import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.append(str(ROOT / "snes-mapper-python"))

import contextlib  # noqa: E402
import hashlib  # noqa: E402
import io  # noqa: E402
import json  # noqa: E402
import os  # noqa: E402
import tempfile  # noqa: E402
import unittest  # noqa: E402
from typing import Any  # noqa: E402

from conformance import testcarts  # noqa: E402
from romimage import rewrite  # noqa: E402

READINGS: dict[str, Any] = testcarts.load(testcarts.READINGS)

HEADER = 0x7FC0


def a_cartridge() -> bytes:
    image = bytearray(0x80000)
    image[HEADER : HEADER + 21] = b"WORKED EXAMPLE       "
    image[HEADER + rewrite.MAP_MODE] = 0x20
    return rewrite.declare_rom_only(image)


def with_pair(image: bytes, complement: int, checksum: int) -> bytes:
    changed = bytearray(image)
    at = HEADER + rewrite.CHECKSUM_COMPLEMENT
    changed[at : at + 4] = bytes(
        (complement & 0xFF, complement >> 8, checksum & 0xFF, checksum >> 8)
    )
    return bytes(changed)


def a_folder_holding(files: dict[str, bytes]) -> Path:
    where = Path(tempfile.mkdtemp())
    for name, blob in files.items():
        (where / name).write_bytes(blob)
    return where


def a_record_naming(blob: bytes, name: str = "worked") -> Path:
    where = Path(tempfile.mkdtemp()) / "testroms.json"
    entry = {"id": name, "sha256": hashlib.sha256(blob).hexdigest()}
    where.write_text(json.dumps({"cartridges": [entry]}))
    return where


def readings_holding(found: dict[str, Any]) -> Path:
    where = Path(tempfile.mkdtemp()) / "testcarts.json"
    where.write_text(json.dumps(found))
    return where


def quietly(*arguments: Any, **options: Any) -> tuple[int, str]:
    said = io.StringIO()
    with contextlib.redirect_stdout(said), contextlib.redirect_stderr(said):
        status = testcarts.main(*arguments, **options)
    return status, said.getvalue()


class EachTestCartridgeReadsAsRecordedTest(unittest.TestCase):
    def test_240p_test_suite_ntsc(self) -> None:
        # Arrange
        recorded = READINGS["240p-test-suite-ntsc"]

        # Act
        account = testcarts.account(recorded)

        # Assert
        self.assertEqual((account, recorded["header"]["computed"]), ("agrees", 0x9266))

    def test_240p_test_suite_pal(self) -> None:
        # Arrange
        recorded = READINGS["240p-test-suite-pal"]

        # Act
        account = testcarts.account(recorded)

        # Assert
        self.assertEqual((account, recorded["header"]["computed"]), ("agrees", 0x9267))

    def test_burn_in_rev_d(self) -> None:
        # Arrange
        recorded = READINGS["burn-in-rev-d"]

        # Act
        account = testcarts.account(recorded)

        # Assert
        self.assertEqual((account, recorded["header"]), ("no header", None))

    def test_campus_challenge_92_menu(self) -> None:
        # Arrange
        recorded = READINGS["campus-challenge-92-menu"]

        # Act
        account = testcarts.account(recorded)

        # Assert
        self.assertEqual((account, recorded["header"]), ("no header", None))

    def test_controller_test_cassette(self) -> None:
        # Arrange
        recorded = READINGS["controller-test-cassette"]

        # Act
        account = testcarts.account(recorded)

        # Assert
        self.assertEqual((account, recorded["header"]), ("no header", None))

    def test_dsp1_tech_demo(self) -> None:
        # Arrange
        recorded = READINGS["dsp1-tech-demo"]

        # Act
        account = testcarts.account(recorded)

        # Assert
        self.assertEqual((account, recorded["header"]), ("no header", None))

    def test_emudetect_v21(self) -> None:
        # Arrange
        recorded = READINGS["emudetect-v21"]

        # Act
        account = testcarts.account(recorded)

        # Assert
        header = recorded["header"]
        self.assertEqual(
            (account, header["complement"], header["checksum"]), ("placeholder pair", 0, 0xFFFF)
        )

    def test_evoke_2010_logo_zoomer(self) -> None:
        # Arrange
        recorded = READINGS["evoke-2010-logo-zoomer"]

        # Act
        account = testcarts.account(recorded)

        # Assert
        self.assertEqual((account, recorded["header"]["computed"]), ("agrees", 0x5A21))

    def test_hd_retrovision_1_4(self) -> None:
        # Arrange
        recorded = READINGS["hd-retrovision-1-4"]

        # Act
        account = testcarts.account(recorded)

        # Assert
        self.assertEqual((account, recorded["header"]["computed"]), ("agrees", 0x054C))

    def test_ntf_2_5_rev_a(self) -> None:
        # Arrange
        recorded = READINGS["ntf-2-5-rev-a"]

        # Act
        account = testcarts.account(recorded)

        # Assert
        self.assertEqual((account, recorded["header"]), ("no header", None))

    def test_sa1_3d_demo(self) -> None:
        # Arrange
        recorded = READINGS["sa1-3d-demo"]

        # Act
        account = testcarts.account(recorded)

        # Assert
        header = recorded["header"]
        self.assertEqual(
            (account, header["complement"], header["checksum"]), ("placeholder pair", 0, 0xFFFF)
        )

    def test_sa1_speed_test_5_1(self) -> None:
        # Arrange
        recorded = READINGS["sa1-speed-test-5-1"]

        # Act
        account = testcarts.account(recorded)

        # Assert
        header = recorded["header"]
        self.assertEqual(
            (account, header["complement"], header["checksum"]), ("placeholder pair", 0, 0xFFFF)
        )

    def test_sa1_demonstration(self) -> None:
        # Arrange
        recorded = READINGS["sa1-demonstration"]

        # Act
        account = testcarts.account(recorded)

        # Assert
        self.assertEqual((account, recorded["header"]), ("no header", None))

    def test_sa1_demonstration_header_fix(self) -> None:
        # Arrange
        recorded = READINGS["sa1-demonstration-header-fix"]

        # Act
        account = testcarts.account(recorded)

        # Assert
        header = recorded["header"]
        self.assertEqual(
            (account, header["complement"], header["checksum"]),
            ("not complements", 0x00A0, 0x0501),
        )

    def test_test_program(self) -> None:
        # Arrange
        recorded = READINGS["test-program"]

        # Act
        account = testcarts.account(recorded)

        # Assert
        self.assertEqual((account, recorded["header"]), ("no header", None))

    def test_snsp_aging_1_02(self) -> None:
        # Arrange
        recorded = READINGS["snsp-aging-1-02"]

        # Act
        account = testcarts.account(recorded)

        # Assert
        self.assertEqual((account, recorded["header"]), ("no header", None))

    def test_aging_1_00(self) -> None:
        # Arrange
        recorded = READINGS["aging-1-00"]

        # Act
        account = testcarts.account(recorded)

        # Assert
        self.assertEqual((account, recorded["header"]), ("no header", None))

    def test_control_deck_tester_rev_1(self) -> None:
        # Arrange
        recorded = READINGS["control-deck-tester-rev-1"]

        # Act
        account = testcarts.account(recorded)

        # Assert
        self.assertEqual((account, recorded["header"]), ("no header", None))


class TheRecordTest(unittest.TestCase):
    def test_every_listed_cartridge_has_a_reading(self) -> None:
        # Arrange
        listed = testcarts.wanted(testcarts.load(testcarts.RECORD))

        # Act
        read = sorted(READINGS)

        # Assert
        self.assertEqual(read, sorted(listed.values()))

    def test_the_readings_carry_no_title(self) -> None:
        # Arrange
        text = testcarts.READINGS.read_text()

        # Act
        titled = "title" in text

        # Assert
        self.assertIs(titled, False)


class TheReaderTest(unittest.TestCase):
    def test_a_consistent_header_agrees(self) -> None:
        # Arrange
        image = a_cartridge()

        # Act
        found = testcarts.reading(image)

        # Assert
        self.assertEqual((found["account"], found["header"]["mirrors"]), ("agrees", 1))

    def test_the_placeholder_pair_is_named(self) -> None:
        # Arrange
        image = with_pair(a_cartridge(), 0x0000, 0xFFFF)

        # Act
        found = testcarts.reading(image)

        # Assert
        self.assertEqual(found["account"], "placeholder pair")

    def test_a_pair_that_is_not_complements_is_named(self) -> None:
        # Arrange
        image = with_pair(a_cartridge(), 0x1234, 0x1234)

        # Act
        found = testcarts.reading(image)

        # Assert
        self.assertEqual(found["account"], "not complements")

    def test_a_complementary_pair_that_is_not_the_sum_disagrees(self) -> None:
        # Arrange
        image = with_pair(a_cartridge(), 0xEDCB, 0x1234)

        # Act
        found = testcarts.reading(image)

        # Assert
        self.assertEqual(found["account"], "disagrees")

    def test_an_image_with_no_header_is_named(self) -> None:
        # Arrange
        image = bytes(0x20000)

        # Act
        found = testcarts.reading(image)

        # Assert
        self.assertEqual(found, {"size": 0x20000, "header": None, "account": "no header"})

    def test_a_copier_stub_is_stripped_before_reading(self) -> None:
        # Arrange
        image = bytes(0x200) + a_cartridge()

        # Act
        found = testcarts.reading(image)

        # Assert
        self.assertEqual((found["size"], found["header"]["at"]), (0x80000, HEADER))


class TheFolderTest(unittest.TestCase):
    def test_the_variable_names_the_folder(self) -> None:
        # Arrange
        environment = {"SNES_TEST_CARTRIDGE_DIR": "/somewhere"}

        # Act
        where = testcarts.directory(environment)

        # Assert
        self.assertEqual(where, Path("/somewhere"))

    def test_with_no_variable_the_library_alongside_is_read(self) -> None:
        # Arrange
        environment = {"SNES_TEST_CARTRIDGE_DIR": " "}

        # Act
        where = testcarts.directory(environment)

        # Assert
        self.assertEqual(where, ROOT.parent / "snes-roms" / "5 Tools & Service Test Carts")

    def test_the_process_environment_is_read_when_none_is_given(self) -> None:
        # Arrange
        expected = testcarts.directory(dict(os.environ))

        # Act
        where = testcarts.directory()

        # Assert
        self.assertEqual(where, expected)

    def test_only_listed_images_are_yielded(self) -> None:
        # Arrange
        image = a_cartridge()
        where = a_folder_holding({"a.sfc": image, "b.sfc": bytes(16), "c.txt": image})

        # Act
        found = list(testcarts.present(where, {hashlib.sha256(image).hexdigest(): "worked"}))

        # Assert
        self.assertEqual(found, [("worked", image)])

    def test_a_missing_folder_yields_nothing(self) -> None:
        # Arrange
        where = Path(tempfile.mkdtemp()) / "gone"

        # Act
        found = list(testcarts.present(where, {}))

        # Assert
        self.assertEqual(found, [])


class TheRunnerTest(unittest.TestCase):
    def test_with_no_image_it_says_so_and_exits_two(self) -> None:
        # Arrange
        environment = {"SNES_TEST_CARTRIDGE_DIR": str(Path(tempfile.mkdtemp()))}

        # Act
        status, said = quietly(["testcarts.py"], environment)

        # Assert
        self.assertEqual(
            (status, said),
            (
                2,
                "  no test cartridge present: set SNES_TEST_CARTRIDGE_DIR to a folder holding one\n",
            ),
        )

    def test_a_reading_that_matches_the_record_passes(self) -> None:
        # Arrange
        image = a_cartridge()
        environment = {"SNES_TEST_CARTRIDGE_DIR": str(a_folder_holding({"a.sfc": image}))}
        readings = readings_holding({"worked": testcarts.reading(image)})

        # Act
        status, said = quietly(["testcarts.py"], environment, a_record_naming(image), readings)

        # Assert
        self.assertEqual(
            (status, said), (0, "  1 of 1 test cartridges present\n  worked: agrees\n")
        )

    def test_a_reading_that_moved_fails(self) -> None:
        # Arrange
        image = a_cartridge()
        environment = {"SNES_TEST_CARTRIDGE_DIR": str(a_folder_holding({"a.sfc": image}))}

        # Act
        status, said = quietly(
            ["testcarts.py"], environment, a_record_naming(image), readings_holding({})
        )

        # Assert
        self.assertEqual(
            (status, said.splitlines()[-1]),
            (1, "  FAILED worked: read differently from the record"),
        )

    def test_a_reading_nobody_accounts_for_fails(self) -> None:
        # Arrange
        image = with_pair(a_cartridge(), 0xEDCB, 0x1234)
        environment = {"SNES_TEST_CARTRIDGE_DIR": str(a_folder_holding({"a.sfc": image}))}
        readings = readings_holding({"worked": testcarts.reading(image)})

        # Act
        status, said = quietly(["testcarts.py"], environment, a_record_naming(image), readings)

        # Assert
        self.assertEqual(
            (status, said.splitlines()[-1]), (1, "  FAILED worked: disagrees, not accounted for")
        )

    def test_record_writes_what_it_read(self) -> None:
        # Arrange
        image = a_cartridge()
        environment = {"SNES_TEST_CARTRIDGE_DIR": str(a_folder_holding({"a.sfc": image}))}
        out = Path(tempfile.mkdtemp()) / "out.json"

        # Act
        status, _ = quietly(
            ["testcarts.py", "--record", str(out)], environment, a_record_naming(image)
        )

        # Assert
        self.assertEqual(
            (status, json.loads(out.read_text())), (0, {"worked": testcarts.reading(image)})
        )

    def test_a_wrong_argument_is_refused(self) -> None:
        # Arrange
        argv = ["testcarts.py", "--keep", "out.json"]

        # Act
        status, said = quietly(argv)

        # Assert
        self.assertEqual((status, said), (2, "usage: testcarts.py [--record out.json]\n"))

    def test_a_lone_argument_is_refused(self) -> None:
        # Arrange
        argv = ["testcarts.py", "--record"]

        # Act
        status, _ = quietly(argv)

        # Assert
        self.assertEqual(status, 2)


if __name__ == "__main__":
    unittest.main()
