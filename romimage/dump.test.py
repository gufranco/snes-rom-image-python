import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.append(str(ROOT / "snes-mapper-python"))

import random  # noqa: E402
import tempfile  # noqa: E402
import unittest  # noqa: E402
import zlib  # noqa: E402

from mapper import COPIER_BYTES, has_copier_stub  # noqa: E402

from romimage import NoParts, dump  # noqa: E402

STUB_SHAPES = (0, 0x200, 0x8000, 0x8200, 0x20000, 0x20200, 1234)


def _image(banks: int = 2, seed: int = 1) -> bytes:
    generator = random.Random(seed)
    return bytes(generator.randrange(256) for _ in range(banks * 0x10000))


def _set(folder: str, names: list[str], parts: list[bytes]) -> None:
    for name, part in zip(names, parts, strict=True):
        (Path(folder) / name).write_bytes(part)


def _stripped(length: int) -> bool:
    return len(dump.strip_copier_stub(bytes(length))) != length


def _form_of(folder: str, length: int) -> str:
    path = Path(folder) / f"{length}.sfc"
    path.write_bytes(bytes(length))
    return dump.form(path)


class CopierStubTest(unittest.TestCase):
    def test_a_whole_number_of_half_banks_carries_no_stub(self) -> None:
        # Arrange
        image = _image()

        # Act
        found = dump.strip_copier_stub(image)

        # Assert
        self.assertEqual(found, image)

    def test_the_same_image_with_five_hundred_and_twelve_more_bytes_does(self) -> None:
        # Arrange
        image = _image()

        # Act
        found = dump.strip_copier_stub(bytes(512) + image)

        # Assert
        self.assertEqual(found, image)

    def test_a_file_no_longer_than_the_stub_cannot_be_one(self) -> None:
        # Arrange
        only = bytes(512)

        # Act
        found = dump.strip_copier_stub(only)

        # Assert
        self.assertEqual(found, only)

    def test_a_length_of_no_recognised_shape_is_left_alone(self) -> None:
        # Arrange
        odd = bytes(1234)

        # Act
        found = dump.strip_copier_stub(odd)

        # Assert
        self.assertEqual(found, odd)

    def test_the_test_is_the_one_the_header_reader_already_uses(self) -> None:
        # Arrange
        lengths = (0x20000, 0x20000 + 0x200, 0x200, 1234, 0x8000 + 0x200)

        # Act
        found = [_stripped(length) for length in lengths]

        # Assert
        self.assertEqual(found, [has_copier_stub(bytes(length)) for length in lengths])

    def test_stripping_removes_exactly_the_stub(self) -> None:
        # Arrange
        image = _image()

        # Act
        found = dump.strip_copier_stub(bytes(COPIER_BYTES) + image)

        # Assert
        self.assertEqual(found, image)

    def test_stripping_an_image_that_never_had_one_changes_nothing(self) -> None:
        # Arrange
        image = _image(seed=2)

        # Act
        found = dump.strip_copier_stub(image)

        # Assert
        self.assertEqual(found, image)


class SplitSetTest(unittest.TestCase):
    def test_the_parts_join_in_name_order_with_one_stub_removed(self) -> None:
        # Arrange
        first, second = _image(banks=1, seed=2), _image(banks=1, seed=3)
        folder = tempfile.mkdtemp()
        _set(folder, ["SF6A.078", "SF6B.078"], [bytes(COPIER_BYTES) + first, second])

        # Act
        found = dump.read(folder)

        # Assert
        self.assertEqual(found, first + second)

    def test_the_order_ignores_case(self) -> None:
        # Arrange
        first, second = _image(banks=1, seed=4), _image(banks=1, seed=5)
        folder = tempfile.mkdtemp()
        _set(folder, ["sf6a.078", "SF6B.078"], [first, second])

        # Act
        found = dump.read(folder)

        # Assert
        self.assertEqual(found, first + second)

    def test_a_numbered_suffix_of_any_width_counts_as_a_part(self) -> None:
        # Arrange
        first, second = _image(banks=1, seed=6), _image(banks=1, seed=7)
        folder = tempfile.mkdtemp()
        _set(folder, ["game.1", "game.2"], [first, second])

        # Act
        found = dump.read(folder)

        # Assert
        self.assertEqual(found, first + second)

    def test_a_file_that_is_not_a_part_is_left_out(self) -> None:
        # Arrange
        only = _image(banks=1, seed=8)
        folder = tempfile.mkdtemp()
        _set(folder, ["game.078", "notes.txt"], [only, b"nothing here"])

        # Act
        found = dump.read(folder)

        # Assert
        self.assertEqual(found, only)

    def test_parts_are_found_below_the_folder_as_well_as_in_it(self) -> None:
        # Arrange
        part = _image(banks=1, seed=9)
        folder = tempfile.mkdtemp()
        nested = Path(folder) / "set"
        nested.mkdir()
        (nested / "game.078").write_bytes(part)

        # Act
        found = dump.read(folder)

        # Assert
        self.assertEqual(found, part)

    def test_a_folder_with_no_parts_is_refused_rather_than_read_as_empty(self) -> None:
        # Arrange
        folder = tempfile.mkdtemp()
        (Path(folder) / "notes.txt").write_bytes(b"nothing here")

        # Act
        with self.assertRaises(NoParts) as refused:
            dump.read(folder)

        # Assert
        self.assertIn("holds no numbered parts", str(refused.exception))

    def test_joining_nothing_gives_nothing(self) -> None:
        # Arrange
        parts: list[bytes] = []

        # Act
        found = dump.join(parts)

        # Assert
        self.assertEqual(found, b"")


class LengthTest(unittest.TestCase):
    def test_the_form_it_names_agrees_with_what_reading_strips(self) -> None:
        # Arrange
        folder = tempfile.mkdtemp()

        # Act
        found = [_form_of(folder, size) == dump.COPIER for size in STUB_SHAPES]

        # Assert
        self.assertEqual(found, [_stripped(size) for size in STUB_SHAPES])


class FormTest(unittest.TestCase):
    def test_a_bare_file_says_so(self) -> None:
        # Arrange
        path = Path(tempfile.mkdtemp()) / "game.sfc"
        path.write_bytes(_image())

        # Act
        found = dump.form(path)

        # Assert
        self.assertEqual(found, dump.BARE)

    def test_a_file_with_a_stub_says_so(self) -> None:
        # Arrange
        path = Path(tempfile.mkdtemp()) / "game.smc"
        path.write_bytes(bytes(COPIER_BYTES) + _image())

        # Act
        found = dump.form(path)

        # Assert
        self.assertEqual(found, dump.COPIER)

    def test_a_folder_says_how_many_parts_it_holds(self) -> None:
        # Arrange
        folder = tempfile.mkdtemp()
        _set(folder, ["game.1", "game.2", "game.3"], [_image(banks=1)] * 3)

        # Act
        found = dump.form(folder)

        # Assert
        self.assertEqual(found, "3 part set")


class ReadTest(unittest.TestCase):
    def test_a_dump_comes_back_as_the_console_would_have_seen_it(self) -> None:
        # Arrange
        image = _image()
        path = Path(tempfile.mkdtemp()) / "game.smc"
        path.write_bytes(bytes(COPIER_BYTES) + image)

        # Act
        found = dump.read(path)

        # Assert
        self.assertEqual(found, image)


class RatioTest(unittest.TestCase):
    def test_an_empty_block_has_no_ratio_rather_than_a_division(self) -> None:
        # Arrange
        block = b""

        # Act
        found = dump.deflate_ratio(block)

        # Assert
        self.assertEqual(found, 0.0)

    def test_a_block_of_one_repeated_byte_compresses_far_below_one(self) -> None:
        # Arrange
        block = bytes(0x10000)

        # Act
        found = dump.deflate_ratio(block)

        # Assert
        self.assertLess(found, 0.1)

    def test_a_block_of_random_bytes_does_not(self) -> None:
        # Arrange
        block = _image(banks=1)

        # Act
        found = dump.deflate_ratio(block)

        # Assert
        self.assertGreater(found, 0.9)

    def test_the_ratio_is_the_compressed_size_over_the_original(self) -> None:
        # Arrange
        block = _image(banks=1, seed=10)

        # Act
        found = dump.deflate_ratio(block)

        # Assert
        self.assertEqual(found, len(zlib.compress(block, 6)) / len(block))

    def test_one_ratio_per_whole_block_and_none_for_the_remainder(self) -> None:
        # Arrange
        data = bytes(0x10000 * 3 + 5)

        # Act
        found = dump.block_ratios(data, block=0x10000)

        # Assert
        self.assertEqual(len(found), 3)

    def test_an_image_shorter_than_one_block_gives_no_ratios(self) -> None:
        # Arrange
        data = bytes(0x100)

        # Act
        found = dump.block_ratios(data, block=0x10000)

        # Assert
        self.assertEqual(found, [])


class ReuseTest(unittest.TestCase):
    def test_a_chunk_is_indexed_at_the_first_place_it_appears(self) -> None:
        # Arrange
        data = b"AB" * 8

        # Act
        index = dump.chunk_index(data, chunk=4, stride=2)

        # Assert
        self.assertEqual(index[b"ABAB"], 0)

    def test_an_image_shorter_than_the_chunk_indexes_nothing(self) -> None:
        # Arrange
        data = b"AB"

        # Act
        index = dump.chunk_index(data, chunk=4, stride=2)

        # Assert
        self.assertEqual(index, {})

    def test_an_image_compared_with_itself_reuses_everything(self) -> None:
        # Arrange
        image = _image(banks=1, seed=11)

        # Act
        found = dump.measure_reuse(image, image)

        # Assert
        self.assertEqual(found, (64, 64))

    def test_two_unrelated_images_reuse_nothing(self) -> None:
        # Arrange
        first, second = _image(banks=1, seed=12), _image(banks=1, seed=13)

        # Act
        found, _ = dump.measure_reuse(first, second)

        # Assert
        self.assertEqual(found, 0)

    def test_a_run_that_moved_by_less_than_a_chunk_is_still_found(self) -> None:
        # Arrange
        run = _image(banks=1, seed=14)[:4096]

        # Act
        found, _ = dump.measure_reuse(run + bytes(4096), bytes(512) + run)

        # Assert
        self.assertGreater(found, 0)


if __name__ == "__main__":
    unittest.main()
