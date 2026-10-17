import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.append(str(ROOT / "snes-mapper-python"))

import hashlib  # noqa: E402
import random  # noqa: E402
import unittest  # noqa: E402
import zlib  # noqa: E402

from romimage import AUTHORITATIVE, NoAuthority, identity  # noqa: E402


def _image(banks: int = 1, seed: int = 1) -> bytes:
    generator = random.Random(seed)
    return bytes(generator.randrange(256) for _ in range(banks * 0x10000))


class MeasureTest(unittest.TestCase):
    def test_the_size_is_the_length_in_bytes(self) -> None:
        # Arrange
        image = _image(banks=2)

        # Act
        found = identity.measure(image)

        # Assert
        self.assertEqual(found["size"], 0x20000)

    def test_every_published_value_is_present(self) -> None:
        # Arrange
        image = _image()

        # Act
        found = identity.measure(image)

        # Assert
        self.assertEqual(set(found), {"size", "crc32", "md5", "sha1", "sha256"})

    def test_the_deciding_value_is_the_one_it_names(self) -> None:
        # Arrange
        image = _image(seed=9)

        # Act
        found = identity.measure(image)

        # Assert
        self.assertEqual(
            (AUTHORITATIVE, found[AUTHORITATIVE]), ("sha256", hashlib.sha256(image).hexdigest())
        )

    def test_the_digests_are_of_the_bytes_given(self) -> None:
        # Arrange
        image = _image(seed=2)

        # Act
        found = identity.measure(image)

        # Assert
        self.assertEqual(
            [found["crc32"], found["sha256"], found["sha1"], found["md5"]],
            [
                f"{zlib.crc32(image):08X}",
                hashlib.sha256(image).hexdigest(),
                hashlib.sha1(image).hexdigest(),
                hashlib.md5(image).hexdigest(),
            ],
        )

    def test_two_images_that_differ_by_one_byte_measure_differently(self) -> None:
        # Arrange
        first = _image(seed=3)
        second = bytes([first[0] ^ 0xFF]) + first[1:]

        # Act
        found = identity.measure(second)

        # Assert
        self.assertNotEqual(found["sha256"], hashlib.sha256(first).hexdigest())

    def test_an_empty_image_measures_rather_than_failing(self) -> None:
        # Arrange
        image = b""

        # Act
        found = identity.measure(image)

        # Assert
        self.assertEqual(found["size"], 0)


class AgreementTest(unittest.TestCase):
    def test_a_measurement_agrees_with_itself(self) -> None:
        # Arrange
        found = identity.measure(_image(seed=4))

        # Act
        agreed = identity.agrees(found, found)

        # Assert
        self.assertTrue(agreed)

    def test_the_deciding_value_settles_it_even_when_another_disagrees(self) -> None:
        # Arrange
        found = identity.measure(_image(seed=5))
        loose = dict(found, crc32="00000000")

        # Act
        agreed = identity.agrees(found, loose)

        # Assert
        self.assertTrue(agreed)

    def test_a_different_deciding_value_is_a_different_file(self) -> None:
        # Arrange
        first = identity.measure(_image(seed=6))
        second = identity.measure(_image(seed=7))

        # Act
        agreed = identity.agrees(first, second)

        # Assert
        self.assertFalse(agreed)

    def test_an_expectation_with_no_deciding_value_is_refused(self) -> None:
        # Arrange
        found = identity.measure(_image(seed=8))
        expected = {"crc32": found["crc32"]}

        # Act
        with self.assertRaises(NoAuthority) as refused:
            identity.agrees(found, expected)

        # Assert
        self.assertIn("cannot accept or reject", str(refused.exception))


if __name__ == "__main__":
    unittest.main()
