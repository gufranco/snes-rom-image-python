<div align="center">

<h1>SNES ROM Image</h1>

<strong>A cartridge image as a file: what the dumper added, what it says about itself, and how to change that.</strong>

<br>
<br>

[![CI](https://github.com/gufranco/snes-rom-image-python/actions/workflows/ci.yml/badge.svg)](https://github.com/gufranco/snes-rom-image-python/actions/workflows/ci.yml)
[![Corpus](https://img.shields.io/badge/corpus-489%20%2F%20489-brightgreen)](#the-corpus-and-why-it-can-ship)
[![Cartridges](https://img.shields.io/badge/measured%20across-7%2C317%20cartridges-blue)](#what-a-real-library-actually-contains)
[![Coverage](https://img.shields.io/badge/coverage-100%25%20statement%20%2B%20branch-brightgreen)](#tests)
[![License](https://img.shields.io/badge/license-MIT-blue)](LICENSE)

</div>

<p align="center">
  <a href="#install">Install</a> &nbsp;|&nbsp;
  <a href="#the-interface">The interface</a> &nbsp;|&nbsp;
  <a href="#the-mistakes-this-exists-to-stop">The mistakes</a> &nbsp;|&nbsp;
  <a href="#is-it-right">Is it right</a> &nbsp;|&nbsp;
  <a href="#the-corpus-and-why-it-can-ship">Why the corpus is legal</a> &nbsp;|&nbsp;
  <a href="#what-a-real-library-actually-contains">What a library contains</a> &nbsp;|&nbsp;
  <a href="https://github.com/gufranco/snes-rom-image-python/issues">Issues</a>
</p>

**489** declarations replayed, **0** failures · **4** properties checked on every one of **7,330** cartridges · the computed checksum matches **2,768** of **2,780** retail cartridges · **467** tests · **100%** statement and branch coverage · no dependencies

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

The chipset byte now says the cartridge has no coprocessor, every mirror of the
header carries the change, and the checksum was recomputed over the result. Doing
it twice changes nothing, which is what makes it safe to run over a library.

---

## Install

```bash
git clone --recurse-submodules https://github.com/gufranco/snes-rom-image-python.git
cd snes-rom-image-python
```

Python 3.12 or newer. Nothing else at runtime.

> [!IMPORTANT]
> The download-zip link on the repository page produces a checkout that cannot
> run. A source archive cannot carry a submodule, and the header reader is one.
> Clone with `--recurse-submodules`, or run `git submodule update --init` in a
> checkout that already exists.

This package is not installable from an index and carries no `[project]` block,
because it consumes another member as a submodule rather than as a version range.
That is the price of the two never disagreeing about where a header sits, and it
is paid deliberately rather than discovered later.

## The interface

Four modules, answering four questions in the order they have to be asked.

| Module | Question |
|:-------|:---------|
| [`dump`](romimage/dump.py) | What did the dumping device add or split off |
| [`identity`](romimage/identity.py) | What makes this file itself, and which value decides |
| [`rewrite`](romimage/rewrite.py) | What does the cartridge say, and how is that changed safely |
| [`manifest`](romimage/manifest.py) | When a reader supplies the wrong file, which wrong is it |

| Call | Does | Returns |
|:--|:--|:--|
| `dump.read(path)` | Reads a dump, joining a split set and stripping a stub | `bytes` |
| `dump.form(path)` | Whether that file is bare or carries a copier stub | a name |
| `dump.strip_copier_stub(data)` / `dump.parts_in(folder)` / `dump.join(parts)` | The pieces of that, separately | `bytes` / paths / `bytes` |
| `identity.measure(data)` | Size and every published digest | a mapping |
| `identity.agrees(found, expected)` | Whether the one value that decides matches | `bool` |
| `rewrite.anchor_of(image)` / `rewrite.mirrors(image)` | Where the header sits, and every copy of it | offsets |
| `rewrite.needs_rewrite(image)` / `rewrite.declare_rom_only(image)` | Whether a chipset byte is claimed, and clearing it everywhere | `bool` / `bytes` |
| `rewrite.checksum(image)` / `rewrite.size_byte(length)` | The header's own arithmetic | `int` |
| `rewrite.changes(before, after)` | Which blocks a rewrite touched | offsets |
| `Manifest(document)` / `manifest.match(...)` | What a project expects, and which wrong a miss is | a `Manifest` |

Everything the package raises lives in [`romimage/errors.py`](romimage/errors.py)
and nowhere else: `NoParts`, `NoAuthority` and `Malformed`. All three are
published, because `except` takes a name and one that cannot be imported can only
be handled by catching everything.

Finding a header is not this package's job.
[`snes-mapper`](https://github.com/gufranco/snes-mapper-python) does that,
measured against the same library, and this depends on it rather than carrying a
second opinion.

## The problem

A file on disk is not a cartridge image, and the difference is invisible.

A copier writes 512 bytes in front of the image describing what it just read, shifting every offset in the file by an amount that appears nowhere in the file. A backup unit splits the image across numbered files, of which only the first carries that stub. A cartridge repeats its header in several places, and tools disagree about which copy they read.

Each of those is silent. A patch written at a known address into a dump with a stub still attached lands 512 bytes early, in the middle of something else, and the build succeeds. A header rewritten in one mirror produces an image that works in the tool it was tested in and not on the machine it was built for.

## The solution

Answer the four questions in the order they have to be asked, and check the answers against a real library.

| Module | Question |
|:-------|:---------|
| [`dump`](romimage/dump.py) | What did the dumping device add or split off |
| [`identity`](romimage/identity.py) | What makes this file itself, and which value decides |
| [`rewrite`](romimage/rewrite.py) | What does the cartridge say, and how is that changed safely |
| [`manifest`](romimage/manifest.py) | When a reader supplies the wrong file, which wrong is it |

Finding a header is not this package's job. [`snes-mapper`](https://github.com/gufranco/snes-mapper-python) does that, measured against the same library, and this depends on it rather than carrying a second opinion. An earlier version did carry one, and the library disagreed with it on **0** cartridges before the two were made to share an answer.

<table>
<tr>
<td width="50%" valign="top">

### Every mirror, not the first

A header repeats across the image. Updating one copy is the bug that only appears on hardware.

</td>
<td width="50%" valign="top">

### The checksum covers itself

The four bytes holding it count as `FF FF 00 00` whatever they hold. Nothing else resolves the circularity.

</td>
</tr>
<tr>
<td width="50%" valign="top">

### One value decides

SHA-256 accepts or rejects. CRC32, MD5 and SHA-1 are published to look up, never to decide.

</td>
<td width="50%" valign="top">

### A miss is a diagnosis

Stub attached, set not joined, known bad dump, right size and wrong content. Each has a different fix.

</td>
</tr>
</table>

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

A patch applied without stripping first lands 512 bytes early, in the middle of
something else, and the build succeeds.

Detected by length rather than content, because the stub's content is not standardised. The same test decides where a header reader looks, so it is imported from that package rather than restated.

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

The sort is case-insensitive, because the device wrote the names in upper case
and half the world has renamed them since.

The sort is case-insensitive, because the device wrote the names in upper case and half the world has renamed them since.

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

All of them have to change. Updating one copy is the bug that only appears on
hardware.

A mirror exists because the same bank is visible at more than one address, so every copy is byte-identical to the first. That makes the search exact, and a run of text that merely resembles a title cannot match.

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

The four bytes holding the pair count as `FF FF 00 00` whatever they hold.
Nothing else resolves the circularity.

The sum is taken over the whole image including the fields holding the result, which cannot be known before the sum. Nintendo's instruction resolves it by naming what those four bytes count as: "First, store 0FFH into the complement check area (FFDCH, FFDDH) and 00H into the check sum area (FFDEH, FFDFH). Then add each byte in the ROM data." Every mirror gets them, not only the first.

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

A power of two is summed once. An image that is not is summed as the largest
power of two it contains plus the remainder mirrored up to match, which is what
the cartridge itself presents to the bus.

Nintendo: "If ROM size cannot be expressed evenly in 2nM bit, such as 10M or 20M bit, add the remainder until a total of 2nM bit is reached." A remainder that is not itself a power of two folds the same way before it repeats.

A quarter of the retail library is built this way, and summing every byte once is wrong on almost all of it. That is not a rounding difference: it is the wrong number, and it is why this rule is checked against the cartridges rather than against itself.

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

The places are found once and passed in, so the sum is taken over the mirrors
that were there rather than over whatever a half-written header now scores as.

Clearing the coprocessor byte and correcting the size costs a header two of the four signals a reader scores it on, so for the moment before the new checksum is written it is less recognisable than it was. Re-deriving the mirrors from that intermediate finds none of them, and the sum comes out short by exactly one header's worth of the convention.

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

It is an exponent: the header stores the power of two, not the size in kilobytes
and not the size in megabits.

An image that grew past a power of two and kept its old byte declares itself smaller than it is, and a machine that trusts the declaration never reads the rest.

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

Five values are published and one of them decides. The other three are there
because the databases a reader will search still index by them.

CRC32 is a 32-bit error code. MD5 and SHA-1 are collision-broken. All three are published so a reader can find their copy in a database that still indexes by them, and none of them is allowed to accept a file.

## What a real library actually contains

Measured across **7,330** cartridges, with 249 refused for carrying no readable header:

| Measurement | Value |
|:------------|------:|
| Distinct declarations | 489 |
| Distinct image sizes | 108 |
| Distinct chipset bytes | 36 |
| Cartridges that would need rewriting | 3,799 |
| Disagreements with the header reader | 0 |

Four properties were checked on every cartridge, not on a sample:

| Property | Held on |
|:---------|--------:|
| The written checksum and its complement are complements | 7,330 of 7,330 |
| Recomputing over the result returns the written value | 7,330 of 7,330 |
| Nothing outside a header changed | 7,330 of 7,330 |
| A second rewrite changes nothing | 7,330 of 7,330 |

Every one of those four failed on some cartridge at some point in getting here, and each failure was a defect rather than a strange cartridge. A bootleg with a blank title. A public-domain demo too small for the size band a reader scores against. Neither would have been found by reasoning about the code.

One more thing is measured and reported without deciding anything: whether the checksum this package computes is the one already written on the cartridge.

| Population | Agrees |
|:-----------|-------:|
| Licensed retail cartridges | 2,768 of 2,780 |
| Every image with a self-consistent header, hacks included | 4,502 of 7,167 |

Those are two different populations and one number for both would be misleading. A hack that changed content without recomputing is not a defect here, which is why this is reported rather than enforced.

It is also the only one of the five that asks the cartridge rather than asking the code whether it agrees with itself, and it is the one that caught a checksum rule wrong on 630 of the 633 short retail cartridges it had been run over. The other four had held on all 7,330 the whole time. [`conformance/divergences.json`](conformance/divergences.json) names the twelve retail cartridges that still disagree and what is known about each.

> [!NOTE]
> A file with no readable header is counted as refused rather than guessed at. Prototypes and unfinished dumps often carry a blank one, and inventing a header for them would put fiction into a corpus of facts.

## The corpus, and why it can ship

A header is thirty two bytes in which a cartridge describes how it is built.

| Field | What it is | Ships? |
|:------|:-----------|:-------|
| Size, mapping, chipset, ROM and RAM size | Facts about a physical object | Yes |
| Counts of how many cartridges share a combination | A measurement | Yes |
| The title | A name rather than a measurement | No |
| Anything outside the header | The game | Never read |

Facts and functional elements sit outside what copyright reaches, per [17 U.S.C. 102(b)](https://www.law.cornell.edu/uscode/text/17/102) and `Feist`. [`conformance/census.py`](conformance/census.py) records no title, and nothing in [`conformance/corpus.json`](conformance/corpus.json) could rebuild any part of any cartridge.

Two claims replay from the corpus alone, which is what makes it worth shipping. The size exponent must be the one the model derives from the size. And a cartridge declaring a coprocessor, or declaring a size that is not its own, must be one the model says needs rewriting.

That second claim runs one way only, deliberately. A cartridge whose first header looks clean can still need a rewrite because a later mirror disagrees with it, and the corpus records the first. So a claim of "needs rewriting" is always allowed; a claim of "needs nothing" is checked.

The four properties above need the cartridges, so they run in the census rather than in CI, and their counts travel with the corpus as a record of what was measured.

> [!IMPORTANT]
> This is how the repository is built, not legal advice. The rule it follows: publish behaviour and identity, never the work itself.

### Taking a census of your own library

```bash
python3 -m conformance.census "/path/to/roms" census.json
python3 -m conformance.census library.zip census.json
```

An archive is read member by member rather than unpacked, because a census does not need a second copy of the library on disk.

## FAQ

<details>
<summary><strong>Why does this depend on another package just to find a header?</strong></summary>
<br>

Because finding one and rewriting one must never disagree about where to look. The offsets, the scoring and the copier-stub rule are one piece of knowledge, and a second copy of it is a second thing to keep true. When this package did carry its own copy, a real library disagreed with it on 0 cartridges, including Contra III, which declares a mapping byte that appears in no table anyone has written down.

</details>

<details>
<summary><strong>Why is CRC32 published if it cannot decide?</strong></summary>
<br>

Because the databases a reader will search still index by it. Publishing it saves them a step. Letting it accept a file would be an integrity claim from a 32-bit error code, which is a different thing entirely.

</details>

<details>
<summary><strong>Why does a mismatch print a diagnosis instead of just failing?</strong></summary>
<br>

Because "digest mismatch" tells the reader nothing they can act on, and most misses are entirely theirs to fix: a stub still attached, a set not joined, a different revision. Naming which one it is turns a dead end into an instruction.

</details>

<details>
<summary><strong>Does this ship or download any cartridge?</strong></summary>
<br>

No. It reads files a reader already owns, and it publishes measurements of them. It carries no cartridge content, links to no source, and nothing in the corpus could rebuild any part of any image.

</details>

## Is it right

Every distinct declaration the library contains is replayed against what this
package makes of it: **489 declarations, 0 failures**, measured across 7,330
cartridges. The corpus runs with no cartridge anywhere on the machine, because it
carries the measurements rather than the files they were taken from.

```bash
python3 -m conformance.corpus
```

```
  489 declarations from corpus.json
  measured across 7330 cartridges
  489 agreed, 0 did not
```

With a library present, the census walks it and checks all four properties on
every file:

```bash
python3 -m conformance.census "/path/to/roms" census.json
```

[`conformance/hardware.json`](conformance/hardware.json) pins Nintendo's manual
fact by fact, each with the sentence it came from and the page it is on, and
[`conformance/hardware.test.py`](conformance/hardware.test.py) holds this
package's constants to it, so a citation here is a test that can fail rather than
a claim in prose.
[`conformance/divergences.json`](conformance/divergences.json) records every
place a real cartridge and the specification part company, and
[`OPEN-QUESTIONS.md`](OPEN-QUESTIONS.md) carries every place fidelity here is a
claim rather than a measurement.

## Working on it

```bash
python3 -m coverage erase
for file in $(find romimage conformance -name '*.test.py' | sort); do
  python3 -m coverage run -a "$file"
done
python3 -m coverage report
```

| Suite | File | Covers |
|:------|:-----|:-------|
| Dump | [`romimage/dump.test.py`](romimage/dump.test.py) | Copier stubs, split sets, forms, compression ratios, reuse |
| Identity | [`romimage/identity.test.py`](romimage/identity.test.py) | The five values, and that only one of them decides |
| Rewrite | [`romimage/rewrite.test.py`](romimage/rewrite.test.py) | Mirrors, checksum convention, size exponent, confinement, idempotence |
| Manifest | [`romimage/manifest.test.py`](romimage/manifest.test.py) | Every diagnosis, and what each one tells the reader to do |
| Census | [`conformance/census.test.py`](conformance/census.test.py) | Folders, archives, tallies, the four properties, and the observation |
| Corpus | [`conformance/corpus.test.py`](conformance/corpus.test.py) | The whole shipped set, replayed |
| Specification | [`conformance/hardware.test.py`](conformance/hardware.test.py) | Every field offset, value, and checksum rule against the figures Nintendo printed |

`python3 romimage/doctor.py` says what is actually on this machine: the rewrite performed twice on an image built on the spot, every digest a report publishes, and whether the submodule this repository needs is checked out. It is run as a file rather than with `-m` so that it still runs when the package itself will not import, which is the case it exists for. Its report is what an issue asks for, because a report is only as good as what it says about the machine that produced it.

Coverage is enforced at 100% of statements and branches by [`pyproject.toml`](pyproject.toml).

### Development

| Command | Description |
|:--------|:------------|
| `ruff format .` | Format |
| `ruff check .` | Lint |
| `python3 -m coverage report` | Coverage, which fails below 100% |
| `python3 -m conformance.corpus` | Replay the shipped corpus |
| `python3 -m conformance.census <library> <out>` | Census a library you own |
| `python3 -m conformance.speed` | The throughput floor |

### Layout

```
romimage/
  __init__.py     the package
  dump.py         copier stubs, split sets, and survey statistics
  identity.py     size and digests, and which one decides
  rewrite.py      declaring no coprocessor, and the checksum that follows
  manifest.py     matching a supplied file, and diagnosing a miss
  version.py      rewritten by the release job and by nothing else
conformance/
  census.py       walks a library you own and checks the rewrite on all of it
  corpus.py       replays every declaration the library contained
  corpus.json     489 declarations covering 7,330 cartridges
  hardware.json   Nintendo's specification, pinned fact by fact
  hardware.test.py  this package's constants against those facts
  divergences.json  every place a real cartridge and the specification part company
packages/
  snes-mapper     the header reader, pinned rather than copied
```

### Versioning

This project follows [Semantic Versioning](https://semver.org/), and every release is tagged from `main` by semantic-release. See [releases](https://github.com/gufranco/snes-rom-image-python/releases).


[`AGENTS.md`](AGENTS.md) is the document for an agent working here.
[`FAMILY.md`](FAMILY.md) is the standard this repository shares with the rest of
the family, kept identical in every member above the marker at the end of its
shared part.

## References

Two sources, in order, and they are not the same kind of thing.

**Nintendo's SNES Development Manual, Book 1** decides what each byte of the header means, what its values are, and how the checksum is calculated. [`conformance/hardware.json`](conformance/hardware.json) pins it fact by fact, each with the sentence it came from and the page it is on, and [`conformance/hardware.test.py`](conformance/hardware.test.py) holds this package's constants to it, so a citation here is a test that can fail rather than a claim in prose.

**A retail cartridge** decides everything the manual does not. The manual is an instruction issued to licensees rather than a description of silicon, so a genuine cartridge can disagree with it and still be genuine. Where one does, the cartridge is the fact.

Nothing else is evidence. No emulator, no wiki, no other implementation of this same job.

> [!WARNING]
> The manual describes two different things called a check sum, and only one of them is in the header. Page 1-2-9 gives a plain sum for the submission sheet, and says outright that it "is different from the check sum on the ROM Registration Specification". Page 1-2-20 gives the real one. Reading the first is how this package summed every byte once for as long as it did.

[`conformance/divergences.json`](conformance/divergences.json) records every place the two sources part company, what this package follows, and what evidence would settle it.

| Document | Publisher | Pinned by | Redistributable |
|:---------|:----------|:----------|:----------------|
| *SNES Development Manual, Book 1* | Nintendo | Digest, page count and read-date in [`conformance/hardware.json`](conformance/hardware.json) | No |

| Source | Used for |
|:-------|:---------|
| A retail cartridge library the author owns | The 489 declarations behind [`conformance/corpus.json`](conformance/corpus.json), read across 7,330 files. Nothing from it is committed |
| [gufranco/snes-mapper-python](https://github.com/gufranco/snes-mapper-python) | Finding a header, as a submodule pinned by commit rather than a copied file |

## Citing this

[CITATION.cff](CITATION.cff) is kept in step with the released version by the
same script that stamps the package, so the version it names is the version that
shipped.

## License

[MIT](LICENSE)
