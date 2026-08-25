from __future__ import annotations

import ast
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.append(str(ROOT / "snes-mapper-python"))

from romimage import dump, errors, identity, manifest  # noqa: E402


def reaching_back(source: str) -> list[str]:
    """Every import in that source that comes from this package rather than outside it.

    Written against text rather than against the one file it guards, so it can be
    handed something that should fail it. A reader nobody has seen report a fault
    reports a clean run whether or not there is one.

    A relative import counts however deep it goes, and an absolute one counts
    when it is the package or a module under it. The dot is required, because a
    package whose name merely begins the same way is somebody else's.
    """

    def inside(name: str) -> bool:
        return name.startswith(".") or name == "romimage" or name.startswith("romimage.")

    borrowed = []
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.Import):
            borrowed += [alias.name for alias in node.names if inside(alias.name)]
        elif isinstance(node, ast.ImportFrom):
            name = "." * node.level + (node.module or "")
            if inside(name):
                borrowed.append(name)
    return borrowed


class OneHomeTest(unittest.TestCase):
    """That every refusal this package makes is defined here and nowhere else.

    Two classes under one name both work, both get tested, and `except` catches
    half the cases it names. Keeping them in one module is what makes that
    impossible rather than unlikely.
    """

    def named(self) -> list[str]:
        return [
            name
            for name, held in vars(errors).items()
            if isinstance(held, type) and issubclass(held, Exception)
        ]

    def test_the_module_defines_every_refusal_this_package_makes(self) -> None:
        self.assertEqual(sorted(self.named()), ["Malformed", "NoAuthority", "NoParts"])

    def test_every_one_of_them_derives_from_exception(self) -> None:
        stray = [name for name in self.named() if not issubclass(getattr(errors, name), Exception)]

        self.assertEqual(stray, [])

    def test_and_every_one_says_what_it_means(self) -> None:
        """A refusal a caller meets and cannot look up is a refusal they guess at."""
        silent = [
            name for name in self.named() if not (getattr(errors, name).__doc__ or "").strip()
        ]

        self.assertEqual(silent, [])

    def test_none_of_them_is_a_subclass_of_another(self) -> None:
        """Or catching one would silently catch the other."""
        held = [getattr(errors, name) for name in self.named()]

        overlapping = [
            (one.__name__, other.__name__)
            for one in held
            for other in held
            if one is not other and issubclass(one, other)
        ]

        self.assertEqual(overlapping, [])


class OneClassPerNameTest(unittest.TestCase):
    """That every module reaching for a refusal reaches for the same object.

    Identity rather than name. Two classes under one name compare equal by name
    and are different objects, which is what makes the duplicate survive testing.
    """

    def test_the_module_that_joins_parts_raises_the_one_no_parts(self) -> None:
        self.assertIs(getattr(dump, "NoParts"), errors.NoParts)  # noqa: B009

    def test_the_module_that_identifies_a_file_raises_the_one_no_authority(self) -> None:
        self.assertIs(getattr(identity, "NoAuthority"), errors.NoAuthority)  # noqa: B009

    def test_and_the_manifest_raises_the_one_malformed(self) -> None:
        self.assertIs(getattr(manifest, "Malformed"), errors.Malformed)  # noqa: B009

    def test_catching_the_published_name_catches_what_the_manifest_raises(self) -> None:
        with self.assertRaises(errors.Malformed):
            manifest.Manifest({})


class NoCycleTest(unittest.TestCase):
    """That this module imports nothing from the package it belongs to.

    Everything here raises, so everything here imports this. An import running
    the other way closes the cycle and makes the order modules happen to load in
    decide whether the package works.
    """

    def test_it_imports_nothing_from_this_package(self) -> None:
        held = (ROOT / "romimage" / "errors.py").read_text()

        self.assertEqual(reaching_back(held), [])

    def test_the_reader_of_that_names_an_absolute_import_back(self) -> None:
        found = reaching_back("import romimage.manifest\n")

        self.assertEqual(found, ["romimage.manifest"])

    def test_and_a_relative_one(self) -> None:
        found = reaching_back("from . import manifest\n")

        self.assertEqual(found, ["."])

    def test_and_steps_over_one_from_outside(self) -> None:
        """The standard library, the member this one consumes, and a lookalike name."""
        found = reaching_back(
            "from __future__ import annotations\nimport mapper\nimport romimagetools\n"
        )

        self.assertEqual(found, [])


if __name__ == "__main__":
    unittest.main()
