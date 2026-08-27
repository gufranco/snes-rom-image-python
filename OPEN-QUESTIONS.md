# Open questions

What this project does not know for certain, and what it would take to find out.

Everything here is a place where being faithful is still a claim rather than a
measurement. The shape of the list is unusual for this family, because the
authority above everything else is a manufacturer's specification and the second
rung is seven thousand real cartridges. Most of the entries are places the
specification is silent and the cartridges are not.

The settled surface is 489 distinct declarations replayed with no failures, four
properties checked on every one of 7,330 cartridges, and every constant here held
against the sentence Nintendo printed. What follows is the residue.

Every entry is also in
[`conformance/divergences.json`](conformance/divergences.json) with its status
and severity, so a program can read what a person reads here.

## Why a library cannot close these

A retail cartridge is the strongest evidence there is about what was built, and
it says nothing about what was specified. Where the specification is silent, a
library tells you what shipped and not what the rule was, so a pattern that holds
across seven thousand cartridges is still a pattern rather than a rule.

That distinction matters most in the last entry below, where twelve images
disagree with both readings and three of them look like ordinary retail releases.

## What would settle almost all of them

A later revision of the same manual. Three of the entries are tables the
revision read here is simply too old to contain, and Nintendo either extended
them later or assigned the codes without doing so.

## Where the specification is silent and the cartridges are not

### Which coprocessor codes exist.

**The document says.** Six upper nibbles: 0 for DSP, 1 for Super FX, 2 for OBC1,
3 for SA-1, E for Other and F for Custom Chip.

Source: Nintendo, *SNES Development Manual, Book 1*, manual page 1-2-18.

**What the cartridges do.** Carry `43H` and `45H` for the S-DD1 and `55H` for the
S-RTC, whose upper nibbles are 4 and 5. Neither appears in the table. Star Ocean
and Street Fighter Alpha 2 carry the S-DD1 codes; Daikaijuu Monogatari II carries
the S-RTC one.

**What this project follows.** The cartridges. It names those three codes and
treats them as coprocessor declarations, which is what a rewrite has to do to
clear them.

**Why.** The revision read here predates those parts, so the table is incomplete
rather than contradicted, and nothing about those three codes rests on a Nintendo
document.

**What would settle or reopen it.** A later revision of the manual with a longer
table, or a Nintendo licensee bulletin assigning the codes.

### Whether the size byte is a table or a rule.

**The document says.** A five row table covering 3 to 64 megabit, and nothing
below or above it.

Source: Nintendo, *SNES Development Manual, Book 1*, manual page 1-2-18.

**What this project follows.** The rule the table implies, which is the exponent
of the smallest power of two that holds the image.

**Why.** Real cartridges exist below and above the table's range, so a table
lookup has nothing to return for them. The rule reproduces every row the table
does print, which is the only evidence that it is the right rule.

**What was searched and did not settle it.** Book I itself, on 2026-08-27, with
the document on the machine and its pages rendered and read rather than searched
through a text layer. The five rows are on manual page 1-2-18 and read `3 ~ 4M
Bit`, `5 ~ 8M Bit`, `9 ~ 16M Bit`, `17 ~ 32M Bit` and `33 ~ 64M Bit`, with
nothing below or above them and no formula beside them. The book does print a
rounding rule for sizes that are not a power of two, and it is about the check
sum rather than this byte: it says to compute as if the image were the next power
of two, which is the mirroring this project already models and quotes. Reading
that rule as a rule for the size byte is the mistake this paragraph exists to
stop.

**What would settle or reopen it.** A Nintendo document giving the rule as a
formula, or a table with more rows. Book II is the obvious place and is not
pinned here.

### That an image carries several byte-identical copies of its header.

**The document says.** Nothing. It gives one registration area per map mode and
never mentions copies.

**What the cartridges do.** Carry up to thirty two identical copies, because the
same bank is visible at several addresses.

**What this project follows.** The cartridges. Every mirror is rewritten and
every mirror's neutral bytes are set before the sum.

**What would settle or reopen it.** Nothing needed. It is a consequence of the
address decoding rather than a question, and it is listed because a tool that
updates one copy produces an image that works in whichever reader it was tested
against and not on the machine it was built for.

## Where neither reading explains what shipped

### Twelve retail images whose stored checksum matches neither rule.

**The document says.** Every cartridge should carry the checksum the
specification defines.

**What the cartridges do.** Twelve of 2,780 do not, and five of those twelve are
a power of two, so mirroring is not what separates them. They fall into three
groups:

- **Competition and prototype cartridges.** Campus Challenge '92, two PowerFest
  94 titles, and a MACS training cartridge marked as a bad dump. Three of these
  store a checksum of zero, which is not a checksum. None was submitted through
  the process the specification governs.
- **Modern re-releases.** Four Trials of Mana images from a Collection of Mana
  build, all storing the same value, and one Switch Online build of Pop'n
  TwinBee. Assembled decades later by a process with no reason to honour a
  submission requirement.
- **Two SPC7110 cartridges and one other.** Both Tengai Makyou Zero images at 40
  megabit, and Momotarou Dentetsu Happy at 24 megabit. **Not explained.** These
  are ordinary retail Japanese releases with self-consistent headers, and they
  are the only entries here that might indicate a rule this package still has
  wrong.

**What this project follows.** The document. It computes the specified checksum
for these images, which is not the one they carry, so rewriting one of them
changes its checksum to the specified value.

**What would settle or reopen it.** For the last group, a second cartridge at the
same size from the same publisher, to tell a per-title accident from a rule. For
the SPC7110 pair specifically, whether the decompression hardware changes what
the console reads at the top of the address space.

## What is not in question

So the boundary is visible rather than implied:

- **Every declaration a real library contains.** 489 of them, replayed with no
  failures, measured across 7,330 cartridges.
- **What each byte of the header means and how the checksum is calculated.** From
  Nintendo's manual, pinned fact by fact in
  [`conformance/hardware.json`](conformance/hardware.json) with the sentence and
  the page, and held to this package's constants by
  [`conformance/hardware.test.py`](conformance/hardware.test.py).
- **That a rewrite touches every mirror.** Checked against a library rather than
  argued.
- **That a rewrite is idempotent.** Running it twice changes nothing, which is
  what makes it safe to run over a library.
- **Which of the published values decides.** SHA-256, and only it. CRC32, MD5 and
  SHA-1 are published because the databases a reader will search still index by
  them, and letting one accept a file would be an integrity claim from a 32-bit
  error code.
- **Where a header sits.** Not this package's answer at all. `snes-mapper` finds
  it, and the two share one answer rather than holding two opinions.

## What is deliberately not modelled

Absent rather than unknown, and absent on purpose:

- **Copier stubs as a specified thing.** They are a product of hardware Nintendo
  did not sell, so there is no document to be faithful to. What this package
  knows about them came from the library.
- **Anything with a clock.** These are files. There is no part here to drive.
- **Any cartridge content.** The corpus carries declarations and counts. Nothing
  in it could rebuild any part of any image, which is what lets a measurement
  over a library be published when the library cannot be.
