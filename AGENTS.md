# Working in this repository

This file is for a coding agent. A person reading it will not be harmed, but
[README.md](README.md) is the document written for them.

## What this project is, in one paragraph

A package that reads a Super NES cartridge image and rewrites its header, so that
a cartridge whose coprocessor has been removed stops declaring one. The header is
mirrored, the checksum covers the bytes that store it, and the size byte is an
exponent, so all three have to stay consistent at once. What the header means
comes from Nintendo's own submission specification; what real cartridges actually
contain comes from a library of several thousand, and the two are not the same
thing.

## The interface a caller drives

Four modules, answering four questions in the order they have to be asked: what
the dumping device added or split off, what makes this file itself, what the
cartridge says and how to change it safely, and which wrong a wrong file is.

- `dump.read(path)` joins a split set and strips a copier stub. The pieces are
  separately available, because a caller who already knows which they have should
  not pay for the guessing.
- `identity.measure(data)` publishes size and four digests, and
  `identity.AUTHORITATIVE` names the one that decides. The other three are there
  because the databases a reader will search still index by them.
- `rewrite.declare_rom_only(image)` clears the chipset byte in every mirror and
  recomputes the checksum over the result. `rewrite.needs_rewrite(image)` says
  whether it would change anything, and running it twice changes nothing.
- `Manifest(document)` matches a supplied file and, on a miss, says which miss it
  is rather than printing a digest.

Everything the package raises lives in [`romimage/errors.py`](romimage/errors.py)
and nowhere else, and that module imports nothing from the package, nor from the
member this one consumes. A refusal this package makes is this package's, and
inheriting one would make a caller's `except` depend on which of the two raised.

There is no clock. These are files.

## The authority ladder

This one is not shaped like the sibling projects, and the difference is
deliberate.

1. **`conformance/hardware.json`**, which is Nintendo's SNES Development Manual
   pinned fact by fact with the sentence each figure came from. It decides which
   byte holds what, what each value means, and how the checksum is calculated.
2. **A retail cartridge.** The specification is an instruction issued to
   licensees, not a description of silicon, so a genuine cartridge can disagree
   with it and still be genuine. Where one does, the cartridge is the fact and
   the specification is the intent.
3. **Nothing else.**

`conformance/divergences.json` records every place they part company.

## What is settled and what is not

**Settled: every declaration a real library contains.** 489 of them, replayed
with no failures, measured across 7,330 cartridges.

**Settled: what each byte of the header means.** From Nintendo's manual, pinned
fact by fact in [`conformance/hardware.json`](conformance/hardware.json) with the
sentence and the page, and held to this package's constants by
[`conformance/hardware.test.py`](conformance/hardware.test.py).

**Settled: that a rewrite touches every mirror and is idempotent.** Checked
against a library rather than argued.

**Not settled: 4 things**, each in [OPEN-QUESTIONS.md](OPEN-QUESTIONS.md) with
what would close it. Three are places the specification is silent and the
cartridges are not, and one is twelve retail images whose stored checksum matches
neither reading. Do not close one by argument.

## The submission checksum is not the header checksum

The manual carries two things called a check sum and only one of them is the one
in the header. Page 1-2-9 describes a plain sum for the submission sheet and says
outright: "This method of calculation is different from the check sum on the ROM
Registration Specification." Page 1-2-20 describes the real one, which neutralises
four bytes and counts a short image up to a power of two.

Reading the wrong page is how this package came to sum every byte once, which was
wrong on 630 of the 633 non-power-of-two retail cartridges it had been run over.

**If you are about to change anything about the checksum, read page 1-2-20 and
not page 1-2-9.**

## The census measures two different kinds of thing

Four **properties** must hold on every image, whatever it is, and a failure is a
defect: the value and its complement are complements, recomputing over the output
returns what was written, nothing outside a header moved, a second rewrite
changes nothing.

One **observation** is measured and reported without gating the verdict: whether
the checksum this package computes is the one the cartridge already carries.

The split is not bookkeeping. All four properties are internal, and a checksum
rule that was wrong the same way every time passed every one of them for as long
as it existed. The observation is the only check that asks the artefact instead
of asking the code whether it agrees with itself, and it is the one that caught
it.

It is an observation rather than a property because a hack that changed content
without recomputing its checksum is not a defect here, and a library of several
thousand contains a great many of those. Over the whole library it holds on about
sixty three percent; over the licensed retail regions alone it holds on 2,768 of
2,780. **Those are two different populations and reporting one number for both
would be misleading.**

## What is deliberately not here

- **No ROM, no fragment of one, no digest fine enough to reconstruct one.** The
  library is somebody's disk and stays there. The corpus records counts and
  declared bytes, never content.
- **No fetch at runtime.** Any file this package reads is one already on the
  machine because somebody put it there.

## Every gate, in the order to run them

```bash
ruff format --check .
ruff check .
mypy
pnpm run format:check
python3 -m coverage erase
for file in $(find romimage conformance -name '*.test.py' | sort); do
  python3 -m coverage run -a "$file"
done
python3 -m coverage report
```

Then the two that are not part of the coverage step:

```bash
python3 -m conformance.corpus
python3 -m conformance.speed
```

And, with a library present, the census that walks it:

```bash
python3 -m conformance.census <library> conformance/corpus.json
```

The submodule needs no `PYTHONPATH`. `mapper` is put on the path by the modules
that reach for it, so a checkout works as it stands and CI sets nothing. What it
does need is to be there: a checkout without `--recurse-submodules` fails at
import, which is a different failure and says so.

Everything under `conformance/` runs as a module. Run as a script, its own
directory goes on the import path and a file there shadows any standard library
module of the same name.

## Conventions that are not negotiable

| Thing | Rule |
|:------|:-----|
| Language | Python only |
| Comments | None in source. Docstrings carry the reasoning, and say why rather than what |
| Test layout | `<module>.test.py` beside the module it covers |
| Test shape | Arrange, blank line, one act, blank line, assert. No section labels |
| Coverage | 100% statements and branches, enforced |
| Types | `mypy` at strict, plus every optional error class |
| Package manager for tooling | pnpm, never npm |
| Commits | Conventional Commits, subject under 50 characters |
| Documents | Read, quoted and pinned by digest. Never committed: none is redistributable |
| Cartridges | Never committed, in any form, for any reason |
| Only retail dumps | A hack is somebody's edit. It is fine as a census subject and it is not evidence about what a cartridge is |
| The dependency | A submodule pinned by commit, never a copied file. See [FAMILY.md](FAMILY.md) |

## Layout

```
romimage/
  dump.py        copier stubs, split sets, and survey statistics
  identity.py    size and digests, and which one decides
  rewrite.py     declaring no coprocessor, and the checksum that follows
  manifest.py    matching a supplied file, and diagnosing a miss
  errors.py      everything this package raises, importing nothing from it or from mapper
  version.py     rewritten by the release job and by nothing else
conformance/
  corpus.py         replays every declaration the library contained
  corpus.json       489 declarations covering 7,330 cartridges
  census.py         walks a library you own and checks the rewrite on all of it
  hardware.json     Nintendo's specification, pinned fact by fact
  hardware.test.py  this package's constants against those facts
  divergences.json  every place a real cartridge and the specification part company
  links.py          the weekly check that every cited address still answers
  speed.py          the throughput floor
snes-mapper-python/  the header reader, a submodule pinned by commit
```

## Things that will bite you

**A quarter of the retail library is not a power of two.** Any change to
`mirrored_sum` has to be checked against a real library, not against a synthetic
image, because a synthetic one is whatever length you made it.

**The four checksum bytes are written, not added afterwards.** Setting them to
`FF FF 00 00` and summing is not the same as zeroing them and adding `0x01FE` per
header, because on a short image the tail is counted more than once and a
constant added once is wrong. That equivalence is why the old code looked correct.

**Every mirror gets the neutral bytes, not just the first.** A cartridge carries
up to thirty two copies of its header and all of them are inside the region being
summed.

**The checksum is computed over the mirrors already found**, not over the mirrors
of the half-written image. A header with its coprocessor byte cleared and its size
byte corrected is momentarily less recognisable as a header than it was, and
re-deriving the mirrors from that intermediate finds none of them.

**Finding the header is not this package's job.** `mapper` decides, by scoring
four independent signals against the same library. An earlier version of this
package kept its own list of plausible mapping bytes and disagreed with reality on
six hundred cartridges.

## Before calling anything finished

[`FAMILY.md`](FAMILY.md) carries a checklist under "What a new repository has to
have before it is a member". Every line on it was a defect found in one of these
repositories and fixed in all of them, so it is the list of things that have
actually gone wrong here rather than a list of good intentions. Read it before
adding a surface, and read it again before saying a change is done.

**A submodule pin is a claim about this package's behaviour until proven
otherwise.** Run the suite against the newer copy before committing a bump, and
when the output changes, find out which upstream commit changed it and why before
touching anything that records what the output should be. A digest updated to
make a check pass is the failure this whole standard exists to prevent.

A change to `FAMILY.md` is a change to every member. Nothing here can catch it
being made in one of them and forgotten in the others, because a test in this
repository cannot see the others, so the check is a command rather than a suite:

```sh
shared() { sed '/^\*Everything above this line/q' "$1"; }

grep -o 'github\.com/[^/]*/\([a-z0-9-]*\))' FAMILY.md | sed 's|.*/||; s|)||' | sort -u |
while read -r member; do
  other="../$member/FAMILY.md"
  [ -f "$other" ] || { echo "not on this machine: $member"; continue; }
  cmp <(shared FAMILY.md) <(shared "$other") && echo "match: $member"
done
```

The members come from the table at the top of `FAMILY.md` rather than from a glob
over the parent directory. The submodule under this repository carries a copy of
that file too, and it is a member in its own right rather than a copy to compare
against from here.

Two rules from that file are worth repeating because they are the ones skipped
most often:

**A check nobody has seen fail is not known to work.** Drive it, once,
deliberately, against input that should fail it.

**Silence and success produce the same output.** A census that walked no file
exits zero exactly like one that walked a library, which is why it prints what it
read and says so when the answer is nothing.

## What a change is expected to leave behind

A gate that would have caught the bug. A change to the checksum, to the mirrors,
or to the size byte also runs the census over a real library, because the four
properties are internal and a rule wrong the same way every time passes all of
them. The observation is the only check that asks the artefact.
