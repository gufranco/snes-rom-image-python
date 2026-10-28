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
    def named(self) -> list[str]:
        return [
            name
            for name, held in vars(errors).items()
            if isinstance(held, type) and issubclass(held, Exception)
        ]

    def test_the_module_defines_every_refusal_this_package_makes(self) -> None:
        self.assertEqual(
            sorted(self.named()), ["Malformed", "NoAuthority", "NoParts", "Unmappable"]
        )

    def test_every_one_of_them_derives_from_exception(self) -> None:
        stray = [name for name in self.named() if not issubclass(getattr(errors, name), Exception)]

        self.assertEqual(stray, [])

    def test_none_of_them_is_a_subclass_of_another(self) -> None:
        held = [getattr(errors, name) for name in self.named()]

        overlapping = [
            (one.__name__, other.__name__)
            for one in held
            for other in held
            if one is not other and issubclass(one, other)
        ]

        self.assertEqual(overlapping, [])


class OneClassPerNameTest(unittest.TestCase):
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
        found = reaching_back(
            "from __future__ import annotations\nimport mapper\nimport romimagetools\n"
        )

        self.assertEqual(found, [])


if __name__ == "__main__":
    unittest.main()
