import subprocess
import sys
import tempfile
import unittest
import unittest.mock
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.append(str(Path(__file__).resolve().parent.parent / "snes-mapper-python"))

import romimage
from romimage import doctor

ROOT = Path(__file__).resolve().parent.parent


class FindingTest(unittest.TestCase):
    def test_a_finding_says_what_was_checked(self) -> None:
        # Arrange
        name = "python"

        # Act
        one = doctor.Finding(name, True, "3.14")

        # Assert
        self.assertEqual(one.name, "python")

    def test_a_healthy_finding_prints_with_a_mark_that_says_so(self) -> None:
        # Arrange
        one = doctor.Finding("python", True, "3.14")

        # Act
        line = one.line

        # Assert
        self.assertIn("ok", line)

    def test_and_an_unhealthy_one_prints_differently(self) -> None:
        # Arrange
        one = doctor.Finding("python", False, "3.9")

        # Act
        line = one.line

        # Assert
        self.assertNotIn("ok", line)

    def test_an_unhealthy_finding_says_what_to_do_about_it(self) -> None:
        # Arrange
        one = doctor.Finding("python", False, "3.9", "upgrade")

        # Act
        said = one.report

        # Assert
        self.assertIn("upgrade", said)

    def test_a_healthy_one_keeps_its_advice_to_itself(self) -> None:
        # Arrange
        one = doctor.Finding("python", True, "3.14", "upgrade")

        # Act
        said = one.report

        # Assert
        self.assertNotIn("upgrade", said)

    def test_and_so_does_an_unhealthy_one_with_none_to_give(self) -> None:
        # Arrange
        one = doctor.Finding("python", False, "3.9")

        # Act
        said = one.report

        # Assert
        self.assertEqual(said, one.line)

    def test_a_finding_prints_as_itself(self) -> None:
        # Arrange
        one = doctor.Finding("python", False, "3.9")

        # Act
        printed = repr(one)

        # Assert
        self.assertEqual(printed, "<Finding python not ok>")

    def test_and_says_so_when_it_is_well(self) -> None:
        # Arrange
        one = doctor.Finding("python", True, "3.14")

        # Act
        printed = repr(one)

        # Assert
        self.assertEqual(printed, "<Finding python ok>")


class ExamineTest(unittest.TestCase):
    def test_the_examination_produces_findings(self) -> None:
        # Arrange
        kind = doctor.Finding

        # Act
        found = doctor.examine()

        # Assert
        self.assertEqual({type(one) for one in found}, {kind})

    def test_it_looks_at_every_submodule_this_repository_carries(self) -> None:
        # Arrange
        wanted = {f"submodule {name}" for name in doctor.SUBMODULES}

        # Act
        found = doctor.examine()

        # Assert
        self.assertLessEqual(wanted, {one.name for one in found})

    def test_and_nothing_it_looks_at_is_unwell_on_this_machine(self) -> None:
        # Arrange
        corpus = doctor.CORPUS

        # Act
        found = doctor.examine(corpus)

        # Assert
        self.assertEqual([one.name for one in found if not one.ok], [])


class VersionTest(unittest.TestCase):
    def test_the_version_is_read_out_of_the_file_rather_than_imported(self) -> None:
        # Arrange
        published = romimage.__version__

        # Act
        found = doctor.installed_version()

        # Assert
        self.assertEqual(found, published)

    def test_a_version_file_naming_nothing_reads_as_unknown(self) -> None:
        # Arrange
        where = Path(tempfile.mkdtemp()) / "version.py"
        where.write_text("NOTHING = 1\n")

        # Act
        found = doctor.installed_version(where)

        # Assert
        self.assertEqual(found, "unknown")

    def test_the_repository_is_put_on_the_path_when_it_is_not_already_there(self) -> None:
        # Arrange
        held = [one for one in sys.path if one != str(doctor.ROOT)]

        # Act
        with unittest.mock.patch.object(sys, "path", held):
            doctor.load_package()

        # Assert
        self.assertIn(str(doctor.ROOT), held)


class ReportTest(unittest.TestCase):
    def test_a_clean_examination_says_there_is_nothing_to_report(self) -> None:
        # Arrange
        found = [doctor.Finding("one", True, "fine")]

        # Act
        lines = doctor.report(found)

        # Assert
        self.assertIn("nothing to report", lines[-1])

    def test_and_a_dirty_one_counts_what_did_not_pass(self) -> None:
        # Arrange
        found = [doctor.Finding("one", True, "fine"), doctor.Finding("two", False, "not")]

        # Act
        lines = doctor.report(found)

        # Assert
        self.assertIn("1 of 2", lines[-1])


class MainTest(unittest.TestCase):
    def test_a_clean_machine_exits_zero(self) -> None:
        # Arrange
        found = [doctor.Finding("one", True, "fine")]

        # Act
        code = doctor.main((), lambda: found, lambda _: None)

        # Assert
        self.assertEqual(code, 0)

    def test_and_a_machine_with_a_finding_exits_one(self) -> None:
        # Arrange
        found = [doctor.Finding("one", False, "not")]

        # Act
        code = doctor.main((), lambda: found, lambda _: None)

        # Assert
        self.assertEqual(code, 1)

    def test_the_report_is_said_rather_than_returned(self) -> None:
        # Arrange
        said: list[str] = []

        # Act
        doctor.main((), lambda: [doctor.Finding("one", True, "fine")], said.append)

        # Assert
        self.assertIn("nothing to report", said[-1])

    def test_it_runs_end_to_end_whatever_this_machine_holds(self) -> None:
        # Arrange
        said: list[str] = []
        checks = len(doctor.examine())

        # Act
        code = doctor.main((), doctor.examine, said.append)

        # Assert
        self.assertEqual((code in (0, 1), len(said) >= checks), (True, True))


class ReachableTest(unittest.TestCase):
    def test_a_root_that_is_not_on_the_path_is_put_there(self) -> None:
        # Arrange
        path: list[str] = []

        # Act
        added = doctor.reachable(Path("/somewhere"), path)

        # Assert
        self.assertEqual((added, path), (True, ["/somewhere"]))

    def test_a_root_already_on_the_path_is_left_alone(self) -> None:
        # Arrange
        path = ["/somewhere"]

        # Act
        added = doctor.reachable(Path("/somewhere"), path)

        # Assert
        self.assertEqual((added, path), (False, ["/somewhere"]))


class AsDocumentedTest(unittest.TestCase):
    def run_it(self) -> subprocess.CompletedProcess[str]:
        with tempfile.TemporaryDirectory() as elsewhere:
            return subprocess.run(
                [sys.executable, str(ROOT / "romimage" / "doctor.py")],
                capture_output=True,
                text=True,
                cwd=elsewhere,
                check=False,
            )

    def test_running_it_as_a_file_prints_a_report(self) -> None:
        # Arrange
        wanted = "checks, nothing to report"

        # Act
        finished = self.run_it()

        # Assert
        self.assertEqual((finished.returncode, wanted in finished.stdout), (0, True))

    def test_it_prints_a_report_rather_than_a_traceback(self) -> None:
        # Arrange
        unwanted = "Traceback"

        # Act
        finished = self.run_it()

        # Assert
        self.assertNotIn(unwanted, finished.stdout + finished.stderr)


if __name__ == "__main__":
    unittest.main()
