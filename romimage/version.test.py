import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.append(str(ROOT / "snes-mapper-python"))

import re  # noqa: E402
import unittest  # noqa: E402

import romimage  # noqa: E402

VERSION_FILE = ROOT / "romimage" / "version.py"


def written_version() -> str:
    found = re.fullmatch(r'VERSION = "([^"]+)"\n', VERSION_FILE.read_text())
    return found.group(1) if found else ""


class VersionTest(unittest.TestCase):
    def test_the_version_is_three_numbers(self) -> None:
        # Arrange
        published = romimage.__version__

        # Act
        parts = published.split(".")

        # Assert
        self.assertEqual([part.isdigit() for part in parts], [True, True, True])

    def test_the_package_reports_the_version_the_release_job_writes(self) -> None:
        # Arrange
        written = written_version()

        # Act
        published = romimage.__version__

        # Assert
        self.assertEqual(published, written)


class SurfaceTest(unittest.TestCase):
    def test_everything_it_declares_is_reachable(self) -> None:
        # Arrange
        declared = romimage.__all__

        # Act
        missing = [name for name in declared if not hasattr(romimage, name)]

        # Assert
        self.assertEqual(missing, [])

    def test_the_release_job_rewrites_the_file_the_package_reads(self) -> None:
        # Arrange
        config = ROOT / ".releaserc.json"

        # Act
        assets = config.read_text()

        # Assert
        self.assertIn("romimage/version.py", assets)

    def test_the_script_that_rewrites_it_points_at_the_same_file(self) -> None:
        # Arrange
        path = ROOT / "scripts" / "set-version.sh"

        # Act
        script = path.read_text()

        # Assert
        self.assertIn("romimage/version.py", script)


if __name__ == "__main__":
    unittest.main()
