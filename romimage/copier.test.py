import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.append(str(ROOT / "snes-mapper-python"))

import hashlib  # noqa: E402
import random  # noqa: E402
import unittest  # noqa: E402

from mapper.header import HEADER_BYTES  # noqa: E402

from romimage import Unmappable, copier, rewrite  # noqa: E402

UCON64_LOROM_4MBIT = bytes([0x20] * 24)
UCON64_LOROM_8MBIT = bytes([0x20, 0x21] * 12)
UCON64_LOROM_16MBIT = bytes([0x20, 0x21, 0x22, 0x23] * 6)
UCON64_LOROM_32MBIT = bytes(
    [0x20, 0x21, 0x22, 0x23, 0x24, 0x25, 0x26, 0x27] * 2 + [0x24, 0x25, 0x26, 0x27] * 2
)
WHOLEBANK_MAP_SEEN_ON_A_GAME_DOCTOR_SF7 = bytes(range(0x20, 0x38))
WHOLEBANK_HEADER_SHA256 = "7512036728b6ca09e32effb6567d1f1b9ed927796fcf1a994984ca3803f16b7f"


def _image(size: int, seed: int, at: int, mapping: int, chipset: int, ram: int) -> bytes:
    generator = random.Random(seed)
    image = bytearray(generator.randbytes(size))
    block = bytearray(HEADER_BYTES)
    block[:21] = b"A CARTRIDGE          "
    block[rewrite.MAP_MODE] = mapping
    block[rewrite.CHIPSET] = chipset
    block[rewrite.ROM_SIZE] = rewrite.size_byte(size)
    block[rewrite.SRAM_SIZE] = ram
    block[0x19] = 0x01
    block[0x1A] = 0x33
    value = 0x1234
    block[0x1C:0x20] = bytes((~value & 0xFF, (~value >> 8) & 0xFF, value & 0xFF, value >> 8))
    image[at : at + HEADER_BYTES] = block
    image[at + 0x3C : at + 0x3E] = b"\x00\x80"
    return bytes(image)


def _lorom(size: int, ram: int = 0x00, seed: int = 3) -> bytes:
    return _image(size, seed, 0x7FC0, 0x20, 0x00, ram)


def _wholebank(chipset: int = 0x00, ram: int = 0x00) -> bytes:
    return _image(0xC00000, 5, 0x7FC0, 0x32, chipset, ram)


class GameDoctorMapTest(unittest.TestCase):
    def test_a_four_megabit_lorom_map_is_ucon64s(self) -> None:
        # Arrange
        place = copier.lorom_place(0x80000)

        # Act
        found = copier.game_doctor_map(place)

        # Assert
        self.assertEqual(found, UCON64_LOROM_4MBIT)

    def test_an_eight_megabit_lorom_map_is_ucon64s(self) -> None:
        # Arrange
        place = copier.lorom_place(0x100000)

        # Act
        found = copier.game_doctor_map(place)

        # Assert
        self.assertEqual(found, UCON64_LOROM_8MBIT)

    def test_a_sixteen_megabit_lorom_map_is_ucon64s(self) -> None:
        # Arrange
        place = copier.lorom_place(0x200000)

        # Act
        found = copier.game_doctor_map(place)

        # Assert
        self.assertEqual(found, UCON64_LOROM_16MBIT)

    def test_a_thirty_two_megabit_lorom_map_is_ucon64s(self) -> None:
        # Arrange
        place = copier.lorom_place(0x400000)

        # Act
        found = copier.game_doctor_map(place)

        # Assert
        self.assertEqual(found, UCON64_LOROM_32MBIT)

    def test_the_whole_bank_map_is_the_one_seen_running_on_a_game_doctor(self) -> None:
        # Arrange
        place = copier.wholebank_place(0xC00000)

        # Act
        found = copier.game_doctor_map(place)

        # Assert
        self.assertEqual(found, WHOLEBANK_MAP_SEEN_ON_A_GAME_DOCTOR_SF7)

    def test_a_map_that_does_not_start_a_chunk_is_refused(self) -> None:
        # Arrange
        def place(bank: int, page: int) -> int:
            return 0x8000 + (bank & 0x7F) * 0x8000 + (page & 0x7FFF)

        # Act
        with self.assertRaises(Unmappable) as caught:
            copier.game_doctor_map(place)

        # Assert
        self.assertIn("4 Mbit chunk", str(caught.exception))

    def test_a_map_whose_banks_leave_their_chunk_is_refused(self) -> None:
        # Arrange
        place = copier.lorom_place(0x60000)

        # Act
        with self.assertRaises(Unmappable) as caught:
            copier.game_doctor_map(place)

        # Assert
        self.assertIn("does not follow", str(caught.exception))


class GameDoctorHeaderTest(unittest.TestCase):
    def test_the_whole_bank_header_is_byte_for_byte_the_one_tested_on_hardware(self) -> None:
        # Arrange
        place = copier.wholebank_place(0xC00000)

        # Act
        header = copier.game_doctor_header(place)

        # Assert
        self.assertEqual(hashlib.sha256(header).hexdigest(), WHOLEBANK_HEADER_SHA256)

    def test_it_is_a_copier_header_long(self) -> None:
        # Arrange
        place = copier.lorom_place(0x80000)

        # Act
        header = copier.game_doctor_header(place)

        # Assert
        self.assertEqual(len(header), 512)

    def test_it_opens_with_the_magic_the_bios_looks_for(self) -> None:
        # Arrange
        place = copier.lorom_place(0x80000)

        # Act
        header = copier.game_doctor_header(place)

        # Assert
        self.assertEqual(header[:16], b"GAME DOCTOR SF 3")

    def test_save_ram_of_thirty_two_kilobytes_takes_ucon64s_two_lorom_slots(self) -> None:
        # Arrange
        place = copier.lorom_place(0x100000)

        # Act
        header = copier.game_doctor_header(place, 0x8000)

        # Assert
        self.assertEqual((header[0x10], header[0x24], header[0x28]), (0x80, 0x40, 0x40))

    def test_eight_kilobytes_of_save_ram_is_coded_as_ucon64_codes_it(self) -> None:
        # Arrange
        place = copier.lorom_place(0x100000)

        # Act
        header = copier.game_doctor_header(place, 0x2000)

        # Assert
        self.assertEqual(header[0x10], 0x81)

    def test_two_kilobytes_of_save_ram_is_coded_as_ucon64_codes_it(self) -> None:
        # Arrange
        place = copier.lorom_place(0x100000)

        # Act
        header = copier.game_doctor_header(place, 0x800)

        # Assert
        self.assertEqual(header[0x10], 0x82)

    def test_a_save_ram_size_with_no_code_is_refused(self) -> None:
        # Arrange
        place = copier.lorom_place(0x100000)

        # Act
        with self.assertRaises(Unmappable) as caught:
            copier.game_doctor_header(place, 0x4000)

        # Assert
        self.assertIn("16384 bytes", str(caught.exception))


class ForGameDoctorTest(unittest.TestCase):
    def test_a_lorom_image_gets_its_header_in_front(self) -> None:
        # Arrange
        image = _lorom(0x100000, ram=0x05)

        # Act
        written = copier.for_game_doctor(image)

        # Assert
        self.assertEqual(
            (written[0x11:0x29], written[0x10], written[0x200:]),
            (bytes([0x20, 0x21] * 9 + [0x20, 0x40, 0x20, 0x21, 0x20, 0x40]), 0x80, image),
        )

    def test_a_whole_bank_image_without_save_ram_gets_the_tested_header(self) -> None:
        # Arrange
        image = _wholebank()

        # Act
        written = copier.for_game_doctor(image)

        # Assert
        self.assertEqual(hashlib.sha256(written[:0x200]).hexdigest(), WHOLEBANK_HEADER_SHA256)

    def test_a_whole_bank_image_with_save_ram_is_refused(self) -> None:
        # Arrange
        image = _wholebank(chipset=0x02, ram=0x03)

        # Act
        with self.assertRaises(Unmappable) as caught:
            copier.for_game_doctor(image)

        # Assert
        self.assertIn("save RAM", str(caught.exception))

    def test_a_high_layout_image_is_refused(self) -> None:
        # Arrange
        image = _image(0x100000, 9, 0xFFC0, 0x21, 0x00, 0x00)

        # Act
        with self.assertRaises(Unmappable) as caught:
            copier.for_game_doctor(image)

        # Assert
        self.assertIn("hirom", str(caught.exception))


class ForSd2snesTest(unittest.TestCase):
    def test_it_is_the_size_the_firmware_wants(self) -> None:
        # Arrange
        image = _wholebank()

        # Act
        written = copier.for_sd2snes(image, 0x43)

        # Assert
        self.assertEqual(len(written), 0xC00200)

    def test_its_copier_header_is_empty(self) -> None:
        # Arrange
        image = _wholebank()

        # Act
        written = copier.for_sd2snes(image, 0x43)

        # Assert
        self.assertEqual(written[:0x200], bytes(0x200))

    def test_every_copy_declares_the_chipset_it_was_given(self) -> None:
        # Arrange
        image = _wholebank()

        # Act
        written = copier.for_sd2snes(image, 0x45)

        # Assert
        self.assertEqual(written[0x200 + 0x7FC0 + rewrite.CHIPSET], 0x45)

    def test_its_checksum_covers_the_chipset_it_declares(self) -> None:
        # Arrange
        image = _wholebank()

        # Act
        body = copier.for_sd2snes(image, 0x43)[0x200:]

        # Assert
        at = 0x7FC0 + rewrite.CHECKSUM
        self.assertEqual(body[at] | (body[at + 1] << 8), rewrite.checksum(body))

    def test_an_image_of_another_size_is_refused(self) -> None:
        # Arrange
        image = _lorom(0x100000)

        # Act
        with self.assertRaises(Unmappable) as caught:
            copier.for_sd2snes(image, 0x43)

        # Assert
        self.assertIn("runs on the firmware as it is", str(caught.exception))

    def test_a_chipset_the_firmware_does_not_map_this_way_is_refused(self) -> None:
        # Arrange
        image = _wholebank()

        # Act
        with self.assertRaises(Unmappable) as caught:
            copier.for_sd2snes(image, 0x00)

        # Assert
        self.assertIn("$43 or $45", str(caught.exception))


if __name__ == "__main__":
    unittest.main()
