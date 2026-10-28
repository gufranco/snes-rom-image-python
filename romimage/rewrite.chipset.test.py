import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.append(str(ROOT / "snes-mapper-python"))

import random  # noqa: E402
import unittest  # noqa: E402

from mapper.header import HEADER_BYTES, NoHeader  # noqa: E402

from romimage import rewrite  # noqa: E402


def _blank(banks: int = 2, seed: int = 1) -> bytearray:
    generator = random.Random(seed)
    return bytearray(generator.randrange(256) for _ in range(banks * 0x10000))


def _stamp(
    image: bytearray,
    at: int,
    title: bytes = b"A CARTRIDGE          ",
    chipset: int = 0x43,
    mapping: int = 0x20,
) -> None:
    block = bytearray(HEADER_BYTES)
    block[: len(title)] = title
    block[rewrite.MAP_MODE] = mapping
    block[rewrite.CHIPSET] = chipset
    block[rewrite.ROM_SIZE] = 0x09
    block[rewrite.SRAM_SIZE] = 0x00
    block[0x19] = 0x01
    block[0x1A] = 0x02
    block[0x1B] = 0x03
    image[at : at + HEADER_BYTES] = block


def _cartridge(
    banks: int = 2,
    seed: int = 1,
    at: tuple[int, ...] = (0x007FC0,),
    chipset: int = 0x43,
) -> bytes:
    image = _blank(banks, seed)
    for place in at:
        _stamp(image, place, chipset=chipset)
    return bytes(image)


class SaveMemoryTest(unittest.TestCase):
    def test_a_coprocessor_with_battery_backed_ram_keeps_the_battery(self) -> None:
        # Arrange
        image = _cartridge(chipset=0x45)

        # Act
        declared = rewrite.declare_rom_only(image)

        # Assert
        self.assertEqual(declared[0x007FC0 + rewrite.CHIPSET], 0x02)

    def test_a_dsp_with_battery_backed_ram_keeps_the_battery(self) -> None:
        # Arrange
        image = _cartridge(chipset=0x05)

        # Act
        declared = rewrite.declare_rom_only(image)

        # Assert
        self.assertEqual(declared[0x007FC0 + rewrite.CHIPSET], 0x02)

    def test_a_coprocessor_with_plain_ram_keeps_the_ram(self) -> None:
        # Arrange
        image = _cartridge(chipset=0x04)

        # Act
        declared = rewrite.declare_rom_only(image)

        # Assert
        self.assertEqual(declared[0x007FC0 + rewrite.CHIPSET], 0x01)

    def test_a_coprocessor_with_a_battery_and_no_ram_keeps_the_battery(self) -> None:
        # Arrange
        chipset = 0x06

        # Act
        found = rewrite.without_coprocessor(chipset)

        # Assert
        self.assertEqual(found, 0x02)

    def test_a_cartridge_with_save_ram_and_no_coprocessor_needs_nothing(self) -> None:
        # Arrange
        image = rewrite.declare_rom_only(_cartridge(chipset=0x02))

        # Act
        found = rewrite.needs_rewrite(image)

        # Assert
        self.assertFalse(found)

    def test_one_declaring_battery_ram_is_left_declaring_it(self) -> None:
        # Arrange
        image = _cartridge(chipset=0x02)

        # Act
        declared = rewrite.declare_rom_only(image)

        # Assert
        self.assertEqual(declared[0x007FC0 + rewrite.CHIPSET], 0x02)

    def test_keeping_the_battery_settles_on_a_second_pass(self) -> None:
        # Arrange
        once = rewrite.declare_rom_only(_cartridge(chipset=0x45))

        # Act
        twice = rewrite.declare_rom_only(once)

        # Assert
        self.assertEqual(twice, once)


class DeclareChipsetTest(unittest.TestCase):
    def test_every_mirror_declares_the_chipset_given(self) -> None:
        # Arrange
        image = _cartridge(at=(0x007FC0, 0x017FC0), chipset=0x00)

        # Act
        declared = rewrite.declare_chipset(image, 0x43)

        # Assert
        self.assertEqual(
            [declared[at + rewrite.CHIPSET] for at in (0x007FC0, 0x017FC0)], [0x43, 0x43]
        )

    def test_its_checksum_covers_what_it_declared(self) -> None:
        # Arrange
        image = _cartridge(chipset=0x00)

        # Act
        declared = rewrite.declare_chipset(image, 0x43)

        # Assert
        at = 0x007FC0 + rewrite.CHECKSUM
        self.assertEqual(declared[at] | (declared[at + 1] << 8), rewrite.checksum(declared))

    def test_an_image_with_no_header_is_refused(self) -> None:
        # Arrange
        image = bytes(0x20000)

        # Act
        with self.assertRaises(NoHeader) as caught:
            rewrite.declare_chipset(image, 0x43)

        # Assert
        self.assertIn("no cartridge header", str(caught.exception))


if __name__ == "__main__":
    unittest.main()
