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


class FindingTest(unittest.TestCase):
    def test_a_finding_says_what_was_checked(self) -> None:
        one = doctor.Finding("python", True, "3.14")

        self.assertEqual(one.name, "python")

    def test_a_healthy_finding_prints_with_a_mark_that_says_so(self) -> None:
        one = doctor.Finding("python", True, "3.14")

        self.assertIn("ok", one.line)

    def test_and_an_unhealthy_one_prints_differently(self) -> None:
        one = doctor.Finding("python", False, "3.9")

        self.assertNotIn("ok", one.line)

    def test_an_unhealthy_finding_says_what_to_do_about_it(self) -> None:
        one = doctor.Finding("python", False, "3.9", "upgrade")

        self.assertIn("upgrade", one.report)

    def test_a_healthy_one_keeps_its_advice_to_itself(self) -> None:
        one = doctor.Finding("python", True, "3.14", "upgrade")

        self.assertNotIn("upgrade", one.report)

    def test_and_so_does_an_unhealthy_one_with_none_to_give(self) -> None:
        one = doctor.Finding("python", False, "3.9")

        self.assertEqual(one.report, one.line)

    def test_a_finding_prints_as_itself(self) -> None:
        one = doctor.Finding("python", False, "3.9")

        self.assertEqual(repr(one), "<Finding python not ok>")

    def test_and_says_so_when_it_is_well(self) -> None:
        one = doctor.Finding("python", True, "3.14")

        self.assertEqual(repr(one), "<Finding python ok>")


class PythonTest(unittest.TestCase):
    def test_it_reports_the_python_it_is_running_on(self) -> None:
        one = doctor._python()

        self.assertTrue(one.ok, one.detail)

    def test_and_names_the_package(self) -> None:
        one = doctor._package()

        self.assertEqual(one.name, "romimage")


class SyntheticTest(unittest.TestCase):
    def test_the_image_it_builds_declares_the_coprocessor_it_says_it_does(self) -> None:
        held = doctor._synthetic()

        self.assertEqual(held[doctor.HEADER_AT + rewrite.CHIPSET], doctor.CHIPSET)

    def test_the_title_that_lands_is_cut_to_the_width_the_reader_publishes(self) -> None:
        held = doctor._synthetic()

        self.assertEqual(
            held[doctor.HEADER_AT : doctor.HEADER_AT + TITLE_BYTES],
            doctor.TITLE[:TITLE_BYTES],
        )

    def test_and_nothing_of_it_spills_past_that_width(self) -> None:
        held = doctor._synthetic()

        self.assertNotEqual(held[doctor.HEADER_AT + TITLE_BYTES], doctor.TITLE[-1])

    def test_and_the_image_is_correct_in_every_field_but_the_probed_one(self) -> None:
        held = doctor._synthetic(chipset=0x00)

        self.assertFalse(rewrite.needs_rewrite(held))


class AskingTest(unittest.TestCase):
    def test_an_image_declaring_a_chip_is_reported_as_needing_the_rewrite(self) -> None:
        one = doctor._asking()

        self.assertTrue(one.ok, one.detail)

    def test_an_image_declaring_nothing_is_reported_as_missed(self) -> None:
        one = doctor._asking(lambda: doctor._synthetic(chipset=0x00))

        self.assertFalse(one.ok, one.detail)

    def test_a_reader_that_refuses_is_reported_as_what_it_said(self) -> None:
        def refuse(*_: Any, **__: Any) -> Any:
            raise Complaint("no")

        with unittest.mock.patch.object(rewrite, "needs_rewrite", refuse):
            one = doctor._asking()

        self.assertIn("Complaint", one.detail)


class RewritingTest(unittest.TestCase):
    def test_the_rewrite_settles_after_one_pass(self) -> None:
        one = doctor._rewriting()

        self.assertTrue(one.ok, one.detail)

    def test_a_rewrite_that_refuses_is_reported_as_what_it_said(self) -> None:
        def refuse(*_: Any, **__: Any) -> Any:
            raise Complaint("no")

        with unittest.mock.patch.object(rewrite, "declare_rom_only", refuse):
            one = doctor._rewriting()

        self.assertIn("Complaint", one.detail)

    def test_a_rewrite_that_changes_the_image_twice_is_not_well(self) -> None:
        clean = doctor._synthetic(chipset=0x00)
        held = iter((clean, bytes(len(clean))))

        with (
            unittest.mock.patch.object(rewrite, "declare_rom_only", lambda *_: next(held)),
            unittest.mock.patch.object(rewrite, "needs_rewrite", lambda *_: False),
        ):
            one = doctor._rewriting()

        self.assertIn("changed it again", one.detail)

    def test_and_one_that_leaves_the_image_still_needing_it_is_not_well(self) -> None:
        with (
            unittest.mock.patch.object(rewrite, "declare_rom_only", lambda held: held),
            unittest.mock.patch.object(rewrite, "needs_rewrite", lambda *_: True),
        ):
            one = doctor._rewriting()

        self.assertFalse(one.ok, one.detail)


class IdentifyingTest(unittest.TestCase):
    def test_every_digest_a_report_publishes_is_computed(self) -> None:
        one = doctor._identifying()

        self.assertTrue(one.ok, one.detail)

    def test_and_all_four_of_them_appear_in_the_line(self) -> None:
        one = doctor._identifying()

        self.assertTrue(
            all(name in one.detail for name in (identity.AUTHORITATIVE, *identity.INTEROPERABLE)),
            one.detail,
        )

    def test_a_digest_that_comes_back_empty_is_named(self) -> None:
        held = dict(identity.measure(doctor._synthetic()), crc32="")

        with unittest.mock.patch.object(identity, "measure", lambda *_: held):
            one = doctor._identifying()

        self.assertIn("crc32", one.advice or "")

    def test_and_the_finding_is_not_well(self) -> None:
        held = dict(identity.measure(doctor._synthetic()), crc32="")

        with unittest.mock.patch.object(identity, "measure", lambda *_: held):
            one = doctor._identifying()

        self.assertFalse(one.ok)

    def test_a_measure_that_refuses_is_reported_as_what_it_said(self) -> None:
        def refuse(*_: Any, **__: Any) -> Any:
            raise Complaint("no")

        with unittest.mock.patch.object(identity, "measure", refuse):
            one = doctor._identifying()

        self.assertIn("Complaint", one.detail)


class SubmoduleTest(unittest.TestCase):
    def test_every_submodule_this_repository_carries_is_checked_out(self) -> None:
        absent = [name for name in doctor.SUBMODULES if not doctor._submodule(name).ok]

        self.assertEqual(absent, [])

    def test_a_submodule_that_is_not_there_is_reported(self) -> None:
        one = doctor._submodule("absent", Path(tempfile.mkdtemp()))

        self.assertIn("is not there", one.detail)

    def test_a_directory_git_left_empty_is_reported_as_empty(self) -> None:
        where = Path(tempfile.mkdtemp())
        (where / "hollow").mkdir()

        one = doctor._submodule("hollow", where)

        self.assertIn("is empty", one.detail)

    def test_and_neither_is_well_because_the_checks_will_skip(self) -> None:
        one = doctor._submodule("absent", Path(tempfile.mkdtemp()))

        self.assertFalse(one.ok)


class CorpusTest(unittest.TestCase):
    def test_the_corpus_beside_the_package_holds_cases(self) -> None:
        one = doctor._corpus()

        self.assertTrue(one.ok, one.detail)

    def test_a_corpus_that_is_not_there_is_reported(self) -> None:
        one = doctor._corpus(Path(tempfile.mkdtemp()) / "absent.json")

        self.assertFalse(one.ok)

    def test_a_corpus_that_is_not_json_is_reported_differently(self) -> None:
        one = doctor._corpus(a_file("{"))

        self.assertIn("not readable as JSON", one.detail)

    def test_a_corpus_with_no_cases_is_not_well(self) -> None:
        one = doctor._corpus(a_file('{"cases": []}'))

        self.assertFalse(one.ok)


class CensusTest(unittest.TestCase):
    def test_it_says_the_library_is_supplied_rather_than_located(self) -> None:
        one = doctor._census()

        self.assertIn("as an argument", one.detail)

    def test_and_that_is_not_a_fault(self) -> None:
        one = doctor._census()

        self.assertTrue(one.ok)


class ExamineTest(unittest.TestCase):
    def test_the_examination_produces_findings(self) -> None:
        found = doctor.examine()

        self.assertTrue(all(isinstance(one, doctor.Finding) for one in found))

    def test_it_looks_at_every_submodule_this_repository_carries(self) -> None:
        named = {one.name for one in doctor.examine()}

        self.assertTrue({f"submodule {name}" for name in doctor.SUBMODULES} <= named, named)

    def test_and_nothing_it_looks_at_is_unwell_on_this_machine(self) -> None:
        unwell = [one.name for one in doctor.examine() if not one.ok]

        self.assertEqual(unwell, [])


class VersionTest(unittest.TestCase):
    def test_the_version_is_read_out_of_the_file_rather_than_imported(self) -> None:
        from romimage.version import VERSION

        self.assertEqual(doctor.VERSION, VERSION)

    def test_a_version_file_naming_nothing_reads_as_unknown(self) -> None:
        where = Path(tempfile.mkdtemp()) / "version.py"
        where.write_text("NOTHING = 1\n")

        self.assertEqual(doctor._version(where), "unknown")

    def test_the_repository_is_put_on_the_path_when_it_is_not_already_there(self) -> None:
        held = [one for one in sys.path if one != str(doctor.ROOT)]

        with unittest.mock.patch.object(sys, "path", held):
            doctor._loaded()

            self.assertIn(str(doctor.ROOT), held)


class ReportTest(unittest.TestCase):
    def test_a_clean_examination_says_there_is_nothing_to_report(self) -> None:
        lines = doctor.report([doctor.Finding("one", True, "fine")])

        self.assertIn("nothing to report", lines[-1])

    def test_and_a_dirty_one_counts_what_did_not_pass(self) -> None:
        lines = doctor.report(
            [doctor.Finding("one", True, "fine"), doctor.Finding("two", False, "not")]
        )

        self.assertIn("1 of 2", lines[-1])


class MainTest(unittest.TestCase):
    def test_a_clean_machine_exits_zero(self) -> None:
        code = doctor.main((), lambda: [doctor.Finding("one", True, "fine")], lambda _: None)

        self.assertEqual(code, 0)

    def test_and_a_machine_with_a_finding_exits_one(self) -> None:
        code = doctor.main((), lambda: [doctor.Finding("one", False, "not")], lambda _: None)

        self.assertEqual(code, 1)

    def test_the_report_is_said_rather_than_returned(self) -> None:
        said: list[str] = []

        doctor.main((), lambda: [doctor.Finding("one", True, "fine")], said.append)

        self.assertTrue(any("nothing to report" in one for one in said))

    def test_it_runs_end_to_end_whatever_this_machine_holds(self) -> None:
        """A report, not a verdict that the machine is well.

        Asserting a clean exit here would make the suite require exactly the
        machine the doctor exists to report on. CI has no cartridges, and a
        doctor that says so is working. What has to hold on every machine is
        that it examines everything and prints a line for each finding.
        """
        said: list[str] = []

        code = doctor.main((), doctor.examine, said.append)

        self.assertIn(code, (0, 1))
        self.assertGreaterEqual(len(said), len(doctor.examine()))


if __name__ == "__main__":
    unittest.main()
