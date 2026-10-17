import sys
import tempfile
import unittest
import unittest.mock
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.append(str(Path(__file__).resolve().parent.parent / "snes-mapper-python"))

from mapper.header import TITLE_BYTES

from romimage import doctor, identity, rewrite


class Complaint(Exception):
    pass


def a_file(body: str) -> Path:
    where = Path(tempfile.mkdtemp()) / "held.json"
    where.write_text(body)
    return where


def refuse(*_: Any, **__: Any) -> Any:
    raise Complaint("no")


def clean_image() -> bytes:
    return doctor.synthetic_image(chipset=0x00)


class PythonTest(unittest.TestCase):
    def test_it_reports_the_python_it_is_running_on(self) -> None:
        # Arrange
        check = doctor.check_python

        # Act
        one = check()

        # Assert
        self.assertTrue(one.ok, one.detail)

    def test_and_names_the_package(self) -> None:
        # Arrange
        check = doctor.check_package

        # Act
        one = check()

        # Assert
        self.assertEqual(one.name, "romimage")


class SyntheticTest(unittest.TestCase):
    def test_the_image_it_builds_declares_the_coprocessor_it_says_it_does(self) -> None:
        # Arrange
        at = doctor.HEADER_AT + doctor.CHIPSET_AT

        # Act
        held = doctor.synthetic_image()

        # Assert
        self.assertEqual(held[at], doctor.CHIPSET)

    def test_the_title_that_lands_is_cut_to_the_width_the_reader_publishes(self) -> None:
        # Arrange
        title = slice(doctor.HEADER_AT, doctor.HEADER_AT + TITLE_BYTES)

        # Act
        held = doctor.synthetic_image()

        # Assert
        self.assertEqual(held[title], doctor.TITLE[:TITLE_BYTES])

    def test_and_nothing_of_it_spills_past_that_width(self) -> None:
        # Arrange
        past = doctor.HEADER_AT + TITLE_BYTES

        # Act
        held = doctor.synthetic_image()

        # Assert
        self.assertNotEqual(held[past], doctor.TITLE[-1])

    def test_and_the_image_is_correct_in_every_field_but_the_probed_one(self) -> None:
        # Arrange
        held = doctor.synthetic_image(chipset=0x00)

        # Act
        needed = rewrite.needs_rewrite(held)

        # Assert
        self.assertFalse(needed)


class AskingTest(unittest.TestCase):
    def test_an_image_declaring_a_chip_is_reported_as_needing_the_rewrite(self) -> None:
        # Arrange
        build = doctor.synthetic_image

        # Act
        one = doctor.check_asking(build)

        # Assert
        self.assertTrue(one.ok, one.detail)

    def test_an_image_declaring_nothing_is_reported_as_missed(self) -> None:
        # Arrange
        build = clean_image

        # Act
        one = doctor.check_asking(build)

        # Assert
        self.assertFalse(one.ok, one.detail)

    def test_a_reader_that_refuses_is_reported_as_what_it_said(self) -> None:
        # Arrange
        refusing = unittest.mock.patch.object(rewrite, "needs_rewrite", refuse)

        # Act
        with refusing:
            one = doctor.check_asking()

        # Assert
        self.assertIn("Complaint", one.detail)


class RewritingTest(unittest.TestCase):
    def test_the_rewrite_settles_after_one_pass(self) -> None:
        # Arrange
        build = doctor.synthetic_image

        # Act
        one = doctor.check_rewriting(build)

        # Assert
        self.assertTrue(one.ok, one.detail)

    def test_a_rewrite_that_refuses_is_reported_as_what_it_said(self) -> None:
        # Arrange
        refusing = unittest.mock.patch.object(rewrite, "declare_rom_only", refuse)

        # Act
        with refusing:
            one = doctor.check_rewriting()

        # Assert
        self.assertIn("Complaint", one.detail)

    def test_a_rewrite_that_changes_the_image_twice_is_not_well(self) -> None:
        # Arrange
        clean = clean_image()
        held = iter((clean, bytes(len(clean))))
        restless = unittest.mock.patch.object(rewrite, "declare_rom_only", lambda *_: next(held))
        settled = unittest.mock.patch.object(rewrite, "needs_rewrite", lambda *_: False)

        # Act
        with restless, settled:
            one = doctor.check_rewriting()

        # Assert
        self.assertIn("changed it again", one.detail)

    def test_and_one_that_leaves_the_image_still_needing_it_is_not_well(self) -> None:
        # Arrange
        idle = unittest.mock.patch.object(rewrite, "declare_rom_only", lambda held: held)
        unsettled = unittest.mock.patch.object(rewrite, "needs_rewrite", lambda *_: True)

        # Act
        with idle, unsettled:
            one = doctor.check_rewriting()

        # Assert
        self.assertFalse(one.ok, one.detail)


class IdentifyingTest(unittest.TestCase):
    def test_every_digest_a_report_publishes_is_computed(self) -> None:
        # Arrange
        build = doctor.synthetic_image

        # Act
        one = doctor.check_identifying(build)

        # Assert
        self.assertTrue(one.ok, one.detail)

    def test_and_all_four_of_them_appear_in_the_line(self) -> None:
        # Arrange
        wanted = (identity.AUTHORITATIVE, *identity.INTEROPERABLE)

        # Act
        one = doctor.check_identifying()

        # Assert
        self.assertEqual([name for name in wanted if name not in one.detail], [])

    def test_a_digest_that_comes_back_empty_is_named(self) -> None:
        # Arrange
        held = dict(identity.measure(doctor.synthetic_image()), crc32="")
        hollow = unittest.mock.patch.object(identity, "measure", lambda *_: held)

        # Act
        with hollow:
            one = doctor.check_identifying()

        # Assert
        self.assertIn("crc32", one.advice or "")

    def test_and_the_finding_is_not_well(self) -> None:
        # Arrange
        held = dict(identity.measure(doctor.synthetic_image()), crc32="")
        hollow = unittest.mock.patch.object(identity, "measure", lambda *_: held)

        # Act
        with hollow:
            one = doctor.check_identifying()

        # Assert
        self.assertFalse(one.ok)

    def test_a_measure_that_refuses_is_reported_as_what_it_said(self) -> None:
        # Arrange
        refusing = unittest.mock.patch.object(identity, "measure", refuse)

        # Act
        with refusing:
            one = doctor.check_identifying()

        # Assert
        self.assertIn("Complaint", one.detail)


class SubmoduleTest(unittest.TestCase):
    def test_every_submodule_this_repository_carries_is_checked_out(self) -> None:
        # Arrange
        names = doctor.SUBMODULES

        # Act
        absent = [name for name in names if not doctor.check_submodule(name).ok]

        # Assert
        self.assertEqual(absent, [])

    def test_a_submodule_that_is_not_there_is_reported(self) -> None:
        # Arrange
        where = Path(tempfile.mkdtemp())

        # Act
        one = doctor.check_submodule("absent", where)

        # Assert
        self.assertIn("is not there", one.detail)

    def test_a_directory_git_left_empty_is_reported_as_empty(self) -> None:
        # Arrange
        where = Path(tempfile.mkdtemp())
        (where / "hollow").mkdir()

        # Act
        one = doctor.check_submodule("hollow", where)

        # Assert
        self.assertIn("is empty", one.detail)

    def test_and_neither_is_well_because_the_checks_will_skip(self) -> None:
        # Arrange
        where = Path(tempfile.mkdtemp())

        # Act
        one = doctor.check_submodule("absent", where)

        # Assert
        self.assertFalse(one.ok)


class CorpusTest(unittest.TestCase):
    def test_the_corpus_beside_the_package_holds_cases(self) -> None:
        # Arrange
        path = doctor.CORPUS

        # Act
        one = doctor.check_corpus(path)

        # Assert
        self.assertTrue(one.ok, one.detail)

    def test_a_corpus_that_is_not_there_is_reported(self) -> None:
        # Arrange
        path = Path(tempfile.mkdtemp()) / "absent.json"

        # Act
        one = doctor.check_corpus(path)

        # Assert
        self.assertFalse(one.ok)

    def test_a_corpus_that_is_not_json_is_reported_differently(self) -> None:
        # Arrange
        path = a_file("{")

        # Act
        one = doctor.check_corpus(path)

        # Assert
        self.assertIn("not readable as JSON", one.detail)

    def test_a_corpus_with_no_cases_is_not_well(self) -> None:
        # Arrange
        path = a_file('{"cases": []}')

        # Act
        one = doctor.check_corpus(path)

        # Assert
        self.assertFalse(one.ok)


class CensusTest(unittest.TestCase):
    def test_it_says_the_library_is_supplied_rather_than_located(self) -> None:
        # Arrange
        check = doctor.check_census

        # Act
        one = check()

        # Assert
        self.assertIn("as an argument", one.detail)

    def test_and_that_is_not_a_fault(self) -> None:
        # Arrange
        check = doctor.check_census

        # Act
        one = check()

        # Assert
        self.assertTrue(one.ok)


if __name__ == "__main__":
    unittest.main()
