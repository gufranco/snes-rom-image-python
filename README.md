# SNES ROM Image

A Super NES cartridge image as a file in Python: what the dumping device added, what the header declares, and how to clear a coprocessor declaration, held to Nintendo's SNES Development Manual and to a library of 7,330 cartridges.

English &nbsp;|&nbsp; [日本語](README.ja.md) &nbsp;|&nbsp; [简体中文](README.zh-Hans.md) &nbsp;|&nbsp; [繁體中文（香港）](README.zh-HK.md)

[![CI](https://github.com/gufranco/snes-rom-image-python/actions/workflows/ci.yml/badge.svg)](https://github.com/gufranco/snes-rom-image-python/actions/workflows/ci.yml)
[![Release](https://img.shields.io/github/v/release/gufranco/snes-rom-image-python)](https://github.com/gufranco/snes-rom-image-python/releases)
[![License](https://img.shields.io/badge/license-MIT-blue)](LICENSE)

**489** declarations replayed, **0** failures, **4** properties checked on every one of **7,330** cartridges, the computed checksum matches **2,768** of **2,780** retail cartridges, **20** quotes located in the manual, **751** tests, **100%** statement and branch coverage, no dependencies

```python
from romimage import rewrite

image = bytearray(0x80000)
image[0x7FC0 : 0x7FC0 + 21] = b"WORKED EXAMPLE       "
image[0x7FD5] = 0x20
image[0x7FD6] = 0x03

print(rewrite.needs_rewrite(image))

after = rewrite.declare_rom_only(image)

print(f"{after[0x7FD6]:#04x}")
print(rewrite.declare_rom_only(after) == after)
```

```
True
0x00
True
```

The example builds a 512 KB image whose header at `0x7FC0` declares chipset `0x03`, a DSP. `needs_rewrite` reports that the declaration has to go. `declare_rom_only` writes chipset `0x00` and the size exponent into every copy of the header, then recomputes the checksum and its complement over the result. A second pass returns the same bytes.

## Install

| Requirement | Version |
|:--|:--|
| Python | 3.12 or newer |
| git | Any, to fetch the submodule |

```bash
git clone --recurse-submodules https://github.com/gufranco/snes-rom-image-python.git
cd snes-rom-image-python
python3 romimage/doctor.py
```

The package imports nothing outside the standard library and its one submodule, [snes-mapper-python](https://github.com/gufranco/snes-mapper-python), which finds the header. A source archive from the download-zip link has no submodule, and every module that reads a header fails at import there. In a checkout made without `--recurse-submodules`, run `git submodule update --init`.

The package is not installable from an index and has no `[project]` block, because it takes the header reader as a submodule pinned by commit rather than as a version range.

The doctor checks the machine and the checkout: Python, the submodule, the corpus, and a rewrite performed twice on an image it builds. It exits 1 when a check fails. Paste its whole output into any bug report. It ends with one line:

```
  8 checks, nothing to report
```

Releases follow [Semantic Versioning](https://semver.org/) and are cut from the commit history by semantic-release. Every release is tagged and listed on the [releases page](https://github.com/gufranco/snes-rom-image-python/releases).

## The interface

Four modules, each answering one question about a file.

| Module | Question |
|:--|:--|
| [`dump`](romimage/dump.py) | What did the dumping device add or split off |
| [`identity`](romimage/identity.py) | Which digests identify the file, and which one decides |
| [`rewrite`](romimage/rewrite.py) | What the header declares, and how to clear a coprocessor from it |
| [`manifest`](romimage/manifest.py) | When a supplied file is not the expected one, which kind of miss it is |

### Calls

| Call | Effect |
|:--|:--|
| `dump.read(path)` | Returns the image bytes. A file loses its copier stub. A folder of numbered parts is joined in name order. Raises `NoParts` for a folder with none |
| `dump.form(path)` | `"bare"` or `"copier header"` for a file, judged by length, and `"N part set"` for a folder |
| `dump.strip_copier_stub(data)` | Drops the leading 512 bytes when the length says a stub is there |
| `dump.parts_in(folder)` | Files with a numeric suffix of one to three digits, sorted by upper-cased name |
| `dump.join(parts)` | Concatenates the parts after stripping the stub from the first |
| `dump.deflate_ratio(block)` | Compressed size over raw size at deflate level 6, 0.0 for an empty block |
| `dump.block_ratios(data, block=0x10000)` | `deflate_ratio` of each whole 64 KB block |
| `dump.measure_reuse(source, target, chunk=1024, stride=512)` | `(found, total)`: how many 1 KB chunks of `source` occur in `target` |
| `dump.chunk_index(data, chunk=1024, stride=512)` | The chunk-to-offset index `measure_reuse` searches |
| `identity.measure(data)` | `size`, `crc32`, `md5`, `sha1` and `sha256` of the bytes |
| `identity.agrees(found, expected)` | True when the `sha256` values match. Raises `NoAuthority` when `expected` has no `sha256` |
| `rewrite.anchor_of(image)` | Offset of the header the reader finds, or `None` |
| `rewrite.mirrors(image)` | Offsets of every byte-identical copy of that header |
| `rewrite.describe(image)` | One dictionary per copy: `at`, `title`, `map`, `chipset`, `coprocessor`, `size`, `sram`, `checksum` |
| `rewrite.needs_rewrite(image)` | True when any copy declares a chipset other than `0x00` or a size byte other than the image's own. Raises `NoHeader` when there is no header |
| `rewrite.declare_rom_only(image)` | Returns new bytes with chipset `0x00`, the right size byte and a recomputed checksum in every copy. Raises `NoHeader` when there is no header |
| `rewrite.checksum(image, places=None)` | The header checksum, with the four checksum bytes of every copy counted as `FF FF 00 00`. `places` defaults to `mirrors(image)` |
| `rewrite.mirrored_sum(data)` | The byte sum with a length that is not a power of two mirrored up to one |
| `rewrite.size_byte(length)` | The size exponent: the power of two of the size in kilobytes, rounded up |
| `rewrite.identifies(block)` | True when the block holds a byte other than `0x00`, `0x20` or `0xFF` |
| `rewrite.changes(before, after, block=0x1000)` | Every offset whose byte differs |

`declare_rom_only`, `needs_rewrite`, `AUTHORITATIVE`, `CHIPSET_ROM_ONLY` and `COPROCESSORS` are also published at the top of the package.

```python
import tempfile
from pathlib import Path

from romimage import dump, identity, rewrite

image = bytearray(0x80000)
image[0x7FC0 : 0x7FC0 + 21] = b"WORKED EXAMPLE       "
image[0x7FD5] = 0x20
image[0x7FD6] = 0x03
image[0x7FD7] = 0x09

with tempfile.TemporaryDirectory() as where:
    stubbed = Path(where) / "game.smc"
    stubbed.write_bytes(bytes(512) + image)
    print(dump.form(stubbed), len(dump.read(stubbed)))

print(rewrite.anchor_of(image), rewrite.mirrors(image))
print(rewrite.describe(image))
print(identity.measure(image)["crc32"], identity.INTEROPERABLE)
```

```
copier header 524288
32704 [32704]
[{'at': 32704, 'title': 'WORKED EXAMPLE', 'map': 32, 'chipset': 3, 'coprocessor': 'DSP', 'size': 9, 'sram': 0, 'checksum': 0}]
DF9EF438 ('crc32', 'md5', 'sha1')
```

The same image with a 512-byte stub in front reads back at its own length. Its one header sits at offset 32704, `0x7FC0`, and declares chipset 3, which [`rewrite.COPROCESSORS`](romimage/rewrite.py) names as a DSP.

```python
from romimage import dump

empty = bytes(0x10000)
varied = bytes(range(256)) * 256

print([round(ratio, 4) for ratio in dump.block_ratios(empty + varied)])
print(dump.measure_reuse(varied, empty + varied))
print(dump.measure_reuse(varied, empty))
```

```
[0.0013, 0.0089]
(64, 64)
(0, 64)
```

The census uses these two to describe a library: how much of each 64 KB block compresses away, and how many 1 KB chunks of one image appear in another.

### The manifest

`Manifest(document)` takes a mapping with an `artifacts` list. Each artifact has a `name`, an `accepted` list of measured forms, and optionally a `rewritten` form and a `bad` list whose entries carry a `why`. Every accepted form needs a `sha256`. `Manifest.from_path(path)` reads the same document from a JSON file.

| Call | Effect |
|:--|:--|
| `document` | The mapping it was built from, after the checks above |
| `artifacts` | The artifacts, as a tuple |
| `by_digest(found)` | The first artifact whose accepted, rewritten or bad form agrees with `found`, with its state, or `None` |
| `by_size(size)` | Every artifact with an accepted form of that size |
| `diagnose(data, form=None)` | Strips a stub, measures, and returns `form`, `size`, `identity`, `state`, `artifact`, `why`, `same_size` and `headers` |
| `explain(found)` | The lines a person reads for a `diagnose` result, ending with what to do |

| State | Meaning |
|:--|:--|
| `known` | The `sha256` matches an accepted form |
| `rewritten` | It matches the artifact's rewritten form |
| `bad dump` | It matches a known bad dump, and `why` says what is wrong with it |
| `same size` | No digest matches, and an accepted form has the same size |
| `unknown` | Nothing matches |

```python
from romimage import Manifest, identity, rewrite

image = bytearray(0x80000)
image[0x7FC0 : 0x7FC0 + 21] = b"WORKED EXAMPLE       "
image[0x7FD5] = 0x20
image[0x7FD6] = 0x03
image[0x7FD7] = 0x09
original = bytes(image)
patched = rewrite.declare_rom_only(original)

manifest = Manifest(
    {
        "artifacts": [
            {
                "name": "worked example",
                "accepted": [identity.measure(original)],
                "rewritten": identity.measure(patched),
            }
        ]
    }
)

for data in (original, bytes(512) + original, patched, bytes(0x80000)):
    found = manifest.diagnose(data)
    print(found["form"], "|", found["state"], "|", found["same_size"])

print(manifest.explain(manifest.diagnose(patched)))
```

```
bare | known | ['worked example']
copier header | known | ['worked example']
bare | rewritten | ['worked example']
bare | same size | ['worked example']
  size    524,288 bytes, read as bare
  crc32   CE667CA6
  sha256  714f22eee90f27debf6c5c0d1b26dc0dbb43b17db057eaa9e5b37acc82faace9
  header at 0x007fc0  'WORKED EXAMPLE'  map 20  chipset 00 (none)  size 09
  already rewritten: worked example
```

The stubbed copy is still `known`, because the stub is stripped before measuring. A file of zeros at the right size is `same size`, which points at a different revision or a damaged copy rather than at the wrong game.

### Constants

| Name | Value |
|:--|:--|
| `identity.AUTHORITATIVE` | `"sha256"`, the one digest that accepts or rejects |
| `identity.INTEROPERABLE` | `("crc32", "md5", "sha1")`, published for database lookups and never used to decide |
| `rewrite.CHIPSET_ROM_ONLY` | `0x00` |
| `rewrite.COPROCESSORS` | Chipset byte to coprocessor name for the 18 codes the package knows, from `0x03` DSP to `0xF9` SPC7110 |
| `rewrite.MAP_MODE`, `CHIPSET`, `ROM_SIZE`, `SRAM_SIZE` | Header offsets `0x15` to `0x18` |
| `rewrite.CHECKSUM_COMPLEMENT`, `CHECKSUM` | Header offsets `0x1C` and `0x1E` |
| `rewrite.CHECKSUM_FIELD_NEUTRAL` | `FF FF 00 00`, what the four checksum bytes count as |
| `rewrite.CHECKSUM_FIELD_BYTES`, `CHECKSUM_FIELD_SUM` | `4` and `0x01FE`, the length of those neutral bytes and their sum |
| `rewrite.PADDING` | `0x00`, `0x20` and `0xFF`, the bytes `identifies` treats as filler |
| `rewrite.KILOBYTE` | `1024`, the unit `size_byte` rounds up to |
| `rewrite.BLOCK_BYTES` | `0x1000`, the block `changes` compares before it looks at single bytes |
| `dump.BARE`, `dump.COPIER` | The two names `form` returns for a file |
| `dump.PART_SUFFIX` | The pattern a numbered part's suffix matches: a dot and one to three digits |
| `dump.BLOCK_BYTES`, `DEFLATE_LEVEL` | `0x10000` and `6`, the defaults of `block_ratios` and `deflate_ratio` |
| `dump.CHUNK_BYTES`, `CHUNK_STRIDE` | `1024` and `512`, the defaults of `measure_reuse` and `chunk_index` |
| `manifest.KNOWN`, `REWRITTEN`, `BAD_DUMP`, `SAME_SIZE`, `UNKNOWN` | The five states |
| `romimage.__version__` | The installed version |

### Errors

| Error | Raised when |
|:--|:--|
| `NoParts` | `dump.read` is given a folder with no numbered parts |
| `NoAuthority` | `identity.agrees` is given an expectation with no `sha256` |
| `Malformed` | `Manifest` is given no artifacts, an artifact with no accepted form, or an accepted form with no `sha256` |
| `NoHeader` | `rewrite.needs_rewrite` or `rewrite.declare_rom_only` finds no header. It belongs to the header reader and is reachable as `rewrite.NoHeader` |

The first three live in [`romimage/errors.py`](romimage/errors.py) and are published at the top of the package.

```python
import tempfile
from pathlib import Path

from romimage import Malformed, Manifest, NoAuthority, NoParts, dump, identity, rewrite


def refusal(call):
    try:
        call()
    except (Malformed, NoAuthority, NoParts, rewrite.NoHeader) as error:
        return f"{type(error).__name__}: {str(error).rsplit('/', 1)[-1]}"
    return "accepted"


with tempfile.TemporaryDirectory() as where:
    library = Path(where) / "library"
    library.mkdir()
    print(refusal(lambda: dump.read(library)))

print(refusal(lambda: identity.agrees({"crc32": "00000000"}, {"crc32": "00000000"})))
print(refusal(lambda: Manifest({"artifacts": []})))
print(refusal(lambda: Manifest({"artifacts": [{"name": "a game", "accepted": [{"size": 4}]}]})))
print(refusal(lambda: rewrite.needs_rewrite(bytes(0x8000))))
```

```
NoParts: library holds no numbered parts to join
NoAuthority: an expectation with no sha256 cannot accept or reject
Malformed: a manifest with no artifacts cannot accept or reject anything
Malformed: a game has an accepted form with no sha256, which is the only value that decides
NoHeader: no cartridge header at any documented position
```

Two matching CRC32 values are refused rather than accepted, because only `sha256` decides.

### Command-line tools

| Command | Arguments | Exit codes |
|:--|:--|:--|
| `python3 romimage/doctor.py` | None | 0 when every check passes, 1 otherwise |
| `python3 -m conformance.corpus` | An optional corpus path | 0 when every declaration agrees, 1 when one does not, 2 for wrong arguments |
| `python3 -m conformance.census` | `<library> <out.json> [limit]`. The library is a folder or a zip archive | 0 when the four properties hold on every image, 1 when one fails, 2 for wrong arguments |
| `python3 -m conformance.documents` | `--check` to verify without fetching, `--only SUBSTRING` to pick a file | 0 when every document verifies, 1 otherwise |
| `python3 -m conformance.quotes` | None | 0 when every quote is located or no document is present, 1 otherwise |
| `python3 -m conformance.speed` | None | 0 at or above 200 identifications per second, 1 below |
| `python3 -m conformance.links` | None | 1 when an address in this file answers 404 or 410, 0 otherwise |

## The mistakes this exists to stop

### A copier stub shifts every offset in the file

```python
from romimage import dump

bare = bytes(0x80000)
stubbed = bytes(512) + bare

print(len(stubbed) - len(dump.strip_copier_stub(stubbed)))
print(dump.strip_copier_stub(bare) == bare)
```

```
512
True
```

A patch written at a known address into a file that still carries the stub lands 512 bytes early. The stub is detected by length, because its content is not standardised, and the rule is imported from the header reader so the two packages agree on it.

### A split set is one cartridge in several files

```python
import tempfile
from pathlib import Path

from romimage import dump

with tempfile.TemporaryDirectory() as where:
    folder = Path(where)
    (folder / "GAME.078").write_bytes(b"the first part, ")
    (folder / "GAME.079").write_bytes(b"then the second")

    parts = dump.parts_in(folder)
    print([one.name for one in parts])
    print(dump.join([one.read_bytes() for one in parts]).decode())
```

```
['GAME.078', 'GAME.079']
the first part, then the second
```

A backup unit wrote the names in upper case, and only the first part carries the stub. The sort ignores case, so a renamed set joins in the same order.

### The header is mirrored, and one copy is not enough

```python
from romimage import rewrite

header = bytearray(0x40)
header[0:21] = b"WORKED EXAMPLE       "
header[0x15] = 0x20
header[0x16] = 0x03
header[0x17] = 0x0B

image = bytearray(0x180000)
for at in (0x7FC0, 0x87FC0, 0x107FC0):
    image[at : at + 0x40] = header

print([f"{one:#08x}" for one in rewrite.mirrors(image)])

after = rewrite.declare_rom_only(image)
print([after[one + 0x16] for one in rewrite.mirrors(image)])
```

```
['0x007fc0', '0x087fc0', '0x107fc0']
[0, 0, 0]
```

A mirror exists because the same bank is visible at more than one address, so every copy is byte-identical to the first. The search matches whole headers, so a run of text that resembles a title cannot match. A rewrite that updates one copy leaves the others declaring the coprocessor.

### The checksum covers the bytes that store it

```python
from romimage import rewrite

image = bytearray(0x80000)
image[0x7FC0 : 0x7FC0 + 21] = b"WORKED EXAMPLE       "
image[0x7FD5] = 0x20
image[0x7FD6] = 0x03
image[0x7FD7] = 0x0B

after = rewrite.declare_rom_only(image)
written = after[0x7FDE] | (after[0x7FDF] << 8)

print(rewrite.checksum(after) == written)
```

```
True
```

The sum runs over the whole image, including the four bytes that hold the result. Nintendo's manual settles that by naming what those bytes count as: "First, store 0FFH into the complement check area (FFDCH, FFDDH) and 00H into the check sum area (FFDEH, FFDFH). Then add each byte in the ROM data." Every copy of the header gets the same treatment.

### A cartridge shorter than a power of two counts its tail more than once

```python
from romimage import rewrite

whole = bytes([0x01]) * 0x100000
uneven = bytes([0x01]) * 0x180000

print(rewrite.mirrored_sum(whole))
print(rewrite.mirrored_sum(uneven))
```

```
1048576
2097152
```

A power of two is summed once. A 1.5 MB image is summed as its first 1 MB plus the remaining 512 KB counted twice, which is what the cartridge presents to the bus. The manual: "If ROM size cannot be expressed evenly in 2nM bit, such as 10M or 20M bit, add the remainder until a total of 2nM bit is reached." A remainder that is not itself a power of two folds the same way.

633 of the 2,780 retail cartridges measured are not a power of two. Summing each of their bytes once agrees with the stored checksum on 3 of them, and the mirrored sum agrees on 626.

### A rewrite in progress is not a cartridge

```python
from romimage import rewrite

image = bytearray(0x80000)
image[0x7FC0 : 0x7FC0 + 21] = b"WORKED EXAMPLE       "
image[0x7FD5] = 0x20
image[0x7FD7] = 0x0B
places = rewrite.mirrors(image)

image[0x7FD6] = 0x03
print(rewrite.checksum(image, places) == rewrite.checksum(image, rewrite.mirrors(image)))
```

```
True
```

`declare_rom_only` finds the copies once, on the image it was given, and passes them to `checksum`. The chipset and size bytes are written between that search and the sum, so the copies that get the neutral checksum bytes are the ones found before any write. `checksum` uses the offsets it is given and searches only when it is given none.

### The size byte is an exponent

```python
from romimage import rewrite

print(rewrite.size_byte(0x400000))
print(rewrite.size_byte(0x80000))
```

```
12
9
```

The header stores the power of two of the size in kilobytes: 4 MB is 4,096 KB, which is 2 to the 12th. An image that grew past a power of two and kept its old byte declares itself smaller than it is.

### One digest decides, and the others are for looking up

```python
from romimage import identity

print(identity.AUTHORITATIVE)
print(sorted(identity.measure(b"a cartridge image would go here")))
```

```
sha256
['crc32', 'md5', 'sha1', 'sha256', 'size']
```

CRC32 is a 32-bit error-detecting code, and MD5 and SHA-1 have published collisions. All three are published so a reader can find a copy in a database that indexes by them. None of them accepts a file.

## What a real library actually contains

Measured across **7,330** cartridges, with 249 more refused for carrying no readable header:

| Measurement | Value |
|:--|--:|
| Distinct declarations | 489 |
| Distinct image sizes | 108 |
| Distinct chipset bytes | 36 |
| Cartridges that would need rewriting | 3,799 |
| Disagreements with the header reader about having a header | 0 |

Four properties are checked on every cartridge, not on a sample:

| Property | Held on |
|:--|--:|
| The written checksum and its complement are complements | 7,330 of 7,330 |
| Recomputing over the result returns the written value | 7,330 of 7,330 |
| Nothing outside a header changed | 7,330 of 7,330 |
| A second rewrite changes nothing | 7,330 of 7,330 |

One observation is measured and gates nothing: whether the checksum this package computes is the one already written on the cartridge.

| Population | Agrees |
|:--|--:|
| Licensed retail cartridges with a self-consistent header | 2,768 of 2,780 |
| Every image with a self-consistent header, hacks included | 4,502 of 7,167 |

A hack that changed content without recomputing its checksum is not a defect in this package, so the observation reports rather than fails. The four properties ask whether the code agrees with itself. The observation asks the cartridge, and a checksum rule that was wrong the same way on every image passes all four properties while failing it. [`conformance/divergences.json`](conformance/divergences.json) names the twelve retail cartridges that still disagree and what is known about each.

A file with no readable header is counted as refused, and the census does not invent a header for it.

## The corpus, and why it can ship

[`conformance/corpus.json`](conformance/corpus.json) holds the 489 distinct declarations and how many cartridges carry each.

| Field | What it is | In the corpus |
|:--|:--|:--|
| Size, mapping, chipset, ROM and RAM size | Facts about a physical object | Yes |
| Count of cartridges sharing a combination | A measurement | Yes |
| The title | A name | No |
| Anything outside the header | The game | Never read |

Facts and functional elements sit outside what copyright reaches, per [17 U.S.C. 102(b)](https://www.law.cornell.edu/uscode/text/17/102) and *Feist*. [`conformance/census.py`](conformance/census.py) records no title, and nothing in the corpus could rebuild any part of any cartridge. This is how the repository is built, not legal advice.

Two claims replay from the corpus alone. The size byte recorded for each declaration must be the one `size_byte` derives from its size. A declaration with a coprocessor, or with a size byte that is not its own, must be one the census marked as needing a rewrite. That second claim runs one way only: a clean first header can still need a rewrite because a later copy disagrees, and the corpus records the first copy.

The four properties need the cartridges, so they run in the census rather than in CI, and their counts travel in the corpus as a record of what was measured.

### Taking a census of your own library

```bash
python3 -m conformance.census "/path/to/roms" census.json
python3 -m conformance.census library.zip census.json
```

It reads `.sfc`, `.smc`, `.fig` and `.swc` files from a folder or from a zip archive. An archive is read member by member rather than unpacked. It prints the counts above and lists up to ten failures.

## Is it right

```bash
python3 -m conformance.corpus
```

```
  489 declarations from corpus.json
  measured across 7330 cartridges
  489 agreed, 0 did not
```

The corpus replays with no cartridge on the machine, and runs in CI. With a library present, `python3 -m conformance.census` checks the four properties on every file.

[`conformance/hardware.json`](conformance/hardware.json) pins Nintendo's manual fact by fact, each with the sentence it came from and the page it is on. [`conformance/hardware.test.py`](conformance/hardware.test.py) holds the package's constants to those facts. `python3 -m conformance.quotes` locates all 20 quoted sentences in the manual when a copy is present.

Where the manual is silent, a retail cartridge decides, and nothing else is evidence: no emulator, no wiki, no other implementation. [`conformance/divergences.json`](conformance/divergences.json) records every place the manual and the cartridges part company, which one the package follows, and what would settle it. [OPEN-QUESTIONS.md](OPEN-QUESTIONS.md) lists the 4 questions still open.

## Working on it

| Need | Where |
|:--|:--|
| Every gate and the order to run them | [CONTRIBUTING.md](CONTRIBUTING.md) |
| The same material for a coding agent | [AGENTS.md](AGENTS.md) |
| The standard this repository shares with the rest of the family | [FAMILY.md](FAMILY.md) |
| Bug reports | [GitHub Issues](https://github.com/gufranco/snes-rom-image-python/issues) |
| Security reports | [SECURITY.md](SECURITY.md) |

```bash
uvx ruff@0.16.3 format --check .
uvx ruff@0.16.3 check .
uvx --python 3.12 mypy==1.14.1
python3 romimage/rewrite.test.py
```

Each module has a test file beside it, named after it, and each runs on its own as above. Coverage is a hard gate at 100% statement and branch, set in [`pyproject.toml`](pyproject.toml):

```bash
python3 -m coverage erase
for file in $(find romimage conformance -name '*.test.py' | sort); do
  python3 -m coverage run -a "$file"
done
python3 -m coverage report
```

`python3 -m conformance.speed` and `python3 -m conformance.corpus` run outside the coverage step.

## References

- *SNES Development Manual, Book 1*, Nintendo of America Inc. 240 pages, 21,022,582 bytes, SHA-256 `f1405241000046abba7849376d2ec53cf85f1ad2e9950d69a7c2cf1f3ff6b791`. It decides what each header byte means and how the checksum is calculated. Page 1-2-20 defines the header checksum. Page 1-2-9 defines a different, plain sum for the submission sheet and says so: "This method of calculation is different from the check sum on the ROM Registration Specification." The manual is not redistributable and is not in this repository. `python3 -m conformance.documents` downloads it from https://archive.org/download/SNESDevManual/book1_text.pdf into `docs/`, which git ignores, and refuses any other file. `python3 -m conformance.documents --check` verifies a copy already there.
- A retail cartridge library the author owns, for the 489 declarations in [`conformance/corpus.json`](conformance/corpus.json), read across 7,330 files. Nothing from it is committed.
- [gufranco/snes-mapper-python](https://github.com/gufranco/snes-mapper-python), for finding the header, carried as a submodule pinned by commit.

## Citing this

[CITATION.cff](CITATION.cff) is updated with each release by the script that stamps the package version.

## License

MIT. See [LICENSE](LICENSE).
