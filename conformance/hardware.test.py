import json
import random
import re
import sys
import unittest
from pathlib import Path
from typing import Any, override

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from romimage import rewrite

sys.path.append(str(Path(__file__).resolve().parent.parent / "snes-mapper-python"))

from mapper.header import HEADER_BYTES

HELD = json.loads((Path(__file__).resolve().parent / "hardware.json").read_text())

DIVERGENCES = json.loads((Path(__file__).resolve().parent / "divergences.json").read_text())

FACTS = HELD["facts"]

FIELDS = FACTS["fields"]


def offset(name: str) -> int:
    value: int = FIELDS[name]["offset"]
    return value


SEED = 1

OTHER_SEED = 2

BANK = 0x10000

LOROM_ANCHOR = 0x7FC0

TITLE = b"A CARTRIDGE          "

MBIT = 0x20000

CHOSEN = {
    "mapMode": ("values", "0x30"),
    "cartridgeType": ("withoutCoprocessor", "0x02"),
    "romSize": ("table", "0x0A"),
    "ramSize": ("table", "0x03"),
}

RULE = re.compile(r"first (\d+)M bit\) \+ \[\(Total of last (\d+)M bit\) x(\d+)\]")

FIRST_ADDRESS = re.compile(r"([0-9A-F]{6})H ~")

ALL_ONES = re.compile(r"= ([0-9A-F]+)H")


def printed_code(name: str) -> int:
    table, code = CHOSEN[name]
    assert code in FIELDS[name][table], f"{code} is not a code the record prints for {name}"
    return int(code, 16)


def a_header() -> dict[int, int]:
    block = dict(enumerate(TITLE))
    return {
        **block,
        offset("mapMode"): 0x20,
        offset("cartridgeType"): FIELDS["cartridgeType"]["romOnly"],
        offset("romSize"): 0x09,
        offset("ramSize"): 0x00,
        offset("fixedValue"): FIELDS["fixedValue"]["value"],
    }


def a_cartridge(writes: dict[int, int] | None = None, seed: int = SEED) -> bytes:
    generator = random.Random(seed)
    image = bytearray(generator.randrange(256) for _ in range(2 * BANK))
    for where, byte in {**a_header(), **(writes or {})}.items():
        image[LOROM_ANCHOR + where] = byte
    return bytes(image)


def word_at(image: bytes, where: int) -> int:
    return image[where] | (image[where + 1] << 8)


def neutralised(image: bytes, where: int, neutral: bytes) -> bytes:
    return image[:where] + neutral + image[where + len(neutral) :]


def worked(rule: str) -> tuple[bytes, int]:
    found = RULE.search(rule)
    assert found is not None, f"{rule} is not a rule this file can read"
    first, last, times = (int(group) for group in found.groups())
    head, tail = bytes([1]) * first * MBIT, bytes([2]) * last * MBIT
    return head + tail, sum(head) + sum(tail) * times


class DocumentTest(unittest.TestCase):
    def test_the_header_is_backed_by_a_named_document(self) -> None:
        self.assertEqual(
            HELD["documents"]["developmentManual"]["publisher"], "Nintendo of America Inc."
        )

    def test_it_carries_a_digest_so_the_reading_can_be_repeated(self) -> None:
        self.assertRegex(HELD["documents"]["developmentManual"]["sha256"], r"^[0-9a-f]{64}$")

    def test_every_field_names_the_page_it_was_read_from(self) -> None:
        missing = [
            name for name, field in FIELDS.items() if name != "note" and "manualPage" not in field
        ]

        self.assertEqual(missing, [])


class FieldOffsetTest(unittest.TestCase):
    def test_the_map_mode_byte_sits_where_the_specification_puts_it(self) -> None:
        self.assertEqual(rewrite.MAP_MODE, offset("mapMode"))

    def test_and_the_cartridge_type_byte(self) -> None:
        self.assertEqual(rewrite.CHIPSET, offset("cartridgeType"))

    def test_and_the_rom_size_byte(self) -> None:
        self.assertEqual(rewrite.ROM_SIZE, offset("romSize"))

    def test_and_the_ram_size_byte(self) -> None:
        self.assertEqual(rewrite.SRAM_SIZE, offset("ramSize"))

    def test_and_the_complement(self) -> None:
        self.assertEqual(rewrite.CHECKSUM_COMPLEMENT, offset("complementCheck"))

    def test_and_the_checksum(self) -> None:
        self.assertEqual(rewrite.CHECKSUM, offset("checkSum"))

    def test_the_complement_sits_two_bytes_before_the_checksum(self) -> None:
        self.assertEqual(offset("checkSum") - offset("complementCheck"), 2)

    def test_the_two_together_are_the_four_bytes_neutralised_before_the_sum(self) -> None:
        self.assertEqual(rewrite.CHECKSUM_FIELD_BYTES, 4)

    def test_every_offset_falls_inside_the_registration_area(self) -> None:
        outside = [
            name
            for name, field in FIELDS.items()
            if name != "note" and not 0 <= field["offset"] < FACTS["registrationArea"]["value"]
        ]

        self.assertEqual(outside, [])


class NeutralBytesTest(unittest.TestCase):
    def test_the_four_bytes_count_as_the_values_the_specification_names(self) -> None:
        self.assertEqual(rewrite.CHECKSUM_FIELD_NEUTRAL, bytes.fromhex("ffff0000"))

    def test_and_the_specification_names_those_values(self) -> None:
        self.assertEqual(FACTS["checksumNeutralBytes"]["value"], "ff ff 00 00")

    def test_they_total_the_constant_this_package_used_to_add(self) -> None:
        self.assertEqual(sum(rewrite.CHECKSUM_FIELD_NEUTRAL), rewrite.CHECKSUM_FIELD_SUM)

    def test_the_checksum_ignores_whatever_those_bytes_held(self) -> None:
        image = bytearray(0x10000)
        image[0x7FC0 : 0x7FC0 + 21] = b"A CARTRIDGE          "
        places = [0x7FC0]
        before = rewrite.checksum(bytes(image), places)
        image[0x7FC0 + rewrite.CHECKSUM_COMPLEMENT : 0x7FC0 + rewrite.CHECKSUM_COMPLEMENT + 4] = (
            b"\x12\x34\x56\x78"
        )

        self.assertEqual(rewrite.checksum(bytes(image), places), before)


class ShortImageTest(unittest.TestCase):
    def rule(self, size: str) -> str:
        for entry in FACTS["shortImageMirroring"]["workedExamples"]:
            if entry["size"] == size:
                return str(entry["ruleQuote"])
        raise AssertionError(f"the specification prints no worked example for {size}")

    def test_a_size_the_specification_does_not_work_through_is_refused(self) -> None:
        with self.assertRaises(AssertionError):
            self.rule("7 Mbit")

    def test_a_power_of_two_is_summed_once(self) -> None:
        data = bytes([3]) * 0x100000

        self.assertEqual(rewrite.mirrored_sum(data), 3 * 0x100000)

    def test_twelve_megabit(self) -> None:
        head = bytes([1]) * 0x100000
        tail = bytes([2]) * 0x80000

        self.assertEqual(
            (rewrite.mirrored_sum(head + tail), self.rule("12 Mbit")),
            (
                sum(head) + 2 * sum(tail),
                "(Total of first 8M bit) + [(Total of last 4M bit) x2] = Check Sum",
            ),
        )

    def test_ten_megabit(self) -> None:
        head = bytes([1]) * 0x100000
        tail = bytes([2]) * 0x40000

        self.assertEqual(
            (rewrite.mirrored_sum(head + tail), self.rule("10 Mbit")),
            (sum(head) + 4 * sum(tail), "(Total of first 8M bit) + [(Total of last 2M bit) x4]"),
        )

    def test_twenty_megabit(self) -> None:
        head = bytes([1]) * 0x200000
        tail = bytes([2]) * 0x80000

        self.assertEqual(
            (rewrite.mirrored_sum(head + tail), self.rule("20 Mbit")),
            (sum(head) + 4 * sum(tail), "(Total of first 16M bit) + [(Total of last 4M bit) x4]"),
        )

    def test_twenty_four_megabit(self) -> None:
        head = bytes([1]) * 0x200000
        tail = bytes([2]) * 0x100000

        self.assertEqual(
            (rewrite.mirrored_sum(head + tail), self.rule("24 Mbit")),
            (sum(head) + 2 * sum(tail), "(Total of first 16M bit) + [(Total of last 8M bit) x2]"),
        )

    def test_every_short_image_reaches_a_power_of_two(self) -> None:
        uneven = [0x180000, 0x140000, 0x280000, 0x300000, 0x500000, 0x600000, 0x160000]

        totals = [rewrite.mirrored_sum(bytes(size)) for size in uneven]
        reached = [rewrite.mirrored_sum(bytes([1]) * size) for size in uneven]

        self.assertEqual(
            (totals, [value & (value - 1) for value in reached]),
            ([0] * len(uneven), [0] * len(uneven)),
        )


class SizeByteTest(unittest.TestCase):
    def test_every_printed_row_is_reproduced(self) -> None:
        upper = {"0x09": 4, "0x0A": 8, "0x0B": 16, "0x0C": 32, "0x0D": 64}

        computed = {
            code: rewrite.size_byte(megabit * 1024 * 1024 // 8) for code, megabit in upper.items()
        }

        self.assertEqual(computed, {code: int(code, 16) for code in upper})

    def test_the_table_this_file_checks_is_the_one_in_the_document(self) -> None:
        self.assertEqual(set(FIELDS["romSize"]["table"]), {"0x09", "0x0A", "0x0B", "0x0C", "0x0D"})


class CartridgeTypeTest(unittest.TestCase):
    def test_rom_only_is_the_value_the_specification_gives_it(self) -> None:
        self.assertEqual(rewrite.CHIPSET_ROM_ONLY, FIELDS["cartridgeType"]["romOnly"])

    def test_and_the_specification_calls_that_value_rom_only(self) -> None:
        self.assertEqual(FIELDS["cartridgeType"]["withoutCoprocessor"]["0x00"], "ROM Only")

    def test_every_undocumented_coprocessor_nibble_is_written_down(self) -> None:
        documented = {int(key, 16) for key in FIELDS["cartridgeType"]["withCoprocessorUpperNibble"]}

        undocumented = sorted({value >> 4 for value in rewrite.COPROCESSORS} - documented)

        self.assertEqual(undocumented, [0x4, 0x5])

    def test_and_the_entry_that_writes_them_down_exists(self) -> None:
        named = {entry["id"] for entry in DIVERGENCES["divergences"]}

        self.assertIn("coprocessor-nibbles-outside-the-table", named)


class PrintedBehaviourTest(unittest.TestCase):
    def test_only_the_registration_area_decides_what_the_header_says(self) -> None:
        # Arrange
        image = a_cartridge()
        start = LOROM_ANCHOR + HEADER_BYTES - FACTS["registrationArea"]["value"]
        other = bytearray(a_cartridge(seed=OTHER_SEED))
        end = LOROM_ANCHOR + HEADER_BYTES
        other[start:end] = image[start:end]

        # Act
        described = [rewrite.describe(one) for one in (image, bytes(other))]

        # Assert
        self.assertEqual(described[0], described[1])

    def test_a_mode_20_header_is_found_where_the_printed_area_puts_it(self) -> None:
        # Arrange
        printed = FIRST_ADDRESS.search(FACTS["mapModeAddresses"]["quote"])
        assert printed is not None, "the record no longer prints the mode 20 address"
        before_base = FACTS["registrationArea"]["value"] - HEADER_BYTES

        # Act
        found = rewrite.anchor_of(a_cartridge())

        # Assert
        self.assertEqual(found, int(printed.group(1), 16) + before_base)

    def test_the_map_mode_is_read_from_the_printed_byte(self) -> None:
        # Arrange
        image = a_cartridge({offset("mapMode"): printed_code("mapMode")})

        # Act
        described = rewrite.describe(image)

        # Assert
        self.assertEqual(described[0]["map"], printed_code("mapMode"))

    def test_the_cartridge_type_is_read_from_the_printed_byte(self) -> None:
        # Arrange
        image = a_cartridge({offset("cartridgeType"): printed_code("cartridgeType")})

        # Act
        described = rewrite.describe(image)

        # Assert
        self.assertEqual(described[0]["chipset"], printed_code("cartridgeType"))

    def test_the_rom_size_is_read_from_the_printed_byte(self) -> None:
        # Arrange
        image = a_cartridge({offset("romSize"): printed_code("romSize")})

        # Act
        described = rewrite.describe(image)

        # Assert
        self.assertEqual(described[0]["size"], printed_code("romSize"))

    def test_the_ram_size_is_read_from_the_printed_byte(self) -> None:
        # Arrange
        image = a_cartridge({offset("ramSize"): printed_code("ramSize")})

        # Act
        described = rewrite.describe(image)

        # Assert
        self.assertEqual(described[0]["sram"], printed_code("ramSize"))

    def test_a_rewritten_header_stores_the_complement_where_the_record_says(self) -> None:
        # Arrange
        relation = ALL_ONES.search(FIELDS["complementCheck"]["relation"])
        assert relation is not None, "the record no longer prints the relation"

        # Act
        declared = rewrite.declare_rom_only(a_cartridge())

        # Assert
        self.assertEqual(
            word_at(declared, LOROM_ANCHOR + offset("complementCheck"))
            + word_at(declared, LOROM_ANCHOR + offset("checkSum")),
            int(relation.group(1), 16),
        )

    def test_a_rewritten_header_stores_the_printed_sum_low_byte_first(self) -> None:
        # Arrange
        image = a_cartridge()
        neutral_at = LOROM_ANCHOR + offset("complementCheck")
        neutral = bytes.fromhex(FACTS["checksumNeutralBytes"]["value"])

        # Act
        declared = rewrite.declare_rom_only(image)

        # Assert
        self.assertEqual(
            word_at(declared, LOROM_ANCHOR + offset("checkSum")),
            sum(neutralised(declared, neutral_at, neutral)) & 0xFFFF,
        )

    def test_a_rewritten_header_keeps_the_printed_fixed_value(self) -> None:
        # Arrange
        image = a_cartridge()

        # Act
        declared = rewrite.declare_rom_only(image)

        # Assert
        self.assertEqual(
            declared[LOROM_ANCHOR + offset("fixedValue")], FIELDS["fixedValue"]["value"]
        )

    def test_the_checksum_counts_its_own_bytes_as_the_printed_neutral_values(self) -> None:
        # Arrange
        image = a_cartridge()
        neutral_at = LOROM_ANCHOR + offset("complementCheck")
        neutral = bytes.fromhex(FACTS["checksumNeutralBytes"]["value"])
        expected = sum(neutralised(image, neutral_at, neutral)) & 0xFFFF

        # Act
        computed = rewrite.checksum(image)

        # Assert
        self.assertEqual(computed, expected)

    def test_a_short_image_sums_as_every_printed_worked_example_says(self) -> None:
        # Arrange
        examples = FACTS["shortImageMirroring"]["workedExamples"]
        cases = [worked(example["ruleQuote"]) for example in examples]

        # Act
        sums = [rewrite.mirrored_sum(data) for data, _ in cases]

        # Assert
        self.assertEqual(
            (sums, [len(data) // MBIT for data, _ in cases]),
            (
                [total for _, total in cases],
                [int(example["size"].split()[0]) for example in examples],
            ),
        )

    def test_the_header_checksum_is_not_the_plain_sum_the_submission_sheet_uses(self) -> None:
        # Arrange
        stated = FACTS["submissionChecksumIsADifferentThing"]["quote"]
        data, _ = worked(FACTS["shortImageMirroring"]["workedExamples"][1]["ruleQuote"])

        # Act
        mirrored = rewrite.mirrored_sum(data)

        # Assert
        self.assertIn("different from the check sum", stated)
        self.assertNotEqual(mirrored, sum(data))


class DivergenceTest(unittest.TestCase):
    @override
    def setUp(self) -> None:
        self.entries: list[dict[str, Any]] = DIVERGENCES["divergences"]

    def test_no_two_entries_share_an_id(self) -> None:
        names = [entry["id"] for entry in self.entries]

        self.assertEqual(len(names), len(set(names)))

    def test_every_entry_says_which_side_the_package_follows(self) -> None:
        missing = [entry["id"] for entry in self.entries if not entry.get("packageFollows")]

        self.assertEqual(missing, [])

    def test_every_open_entry_says_what_would_settle_it(self) -> None:
        missing = [
            entry["id"]
            for entry in self.entries
            if entry["status"] == "open" and not entry.get("wouldSettleIt")
        ]

        self.assertEqual(missing, [])

    def test_every_closed_entry_says_what_would_reopen_it(self) -> None:
        missing = [
            entry["id"]
            for entry in self.entries
            if entry["status"] == "closed" and not entry.get("wouldReopenIt")
        ]

        self.assertEqual(missing, [])

    def test_the_corrected_defect_records_what_was_measured_both_ways(self) -> None:
        found = next(entry for entry in self.entries if entry["id"] == "short-image-checksum")

        self.assertEqual(set(found["measured"]) >= {"before", "after", "subjects"}, True)

    def test_and_says_how_it_survived_the_checks_that_existed(self) -> None:
        found = next(entry for entry in self.entries if entry["id"] == "short-image-checksum")

        self.assertIn("howItSurvived", found)

    def test_the_cartridges_that_still_disagree_are_named_rather_than_averaged(self) -> None:
        found = next(
            entry for entry in self.entries if entry["id"] == "cartridges-that-still-disagree"
        )

        self.assertNotEqual(found["groups"], [])


if __name__ == "__main__":
    unittest.main()
