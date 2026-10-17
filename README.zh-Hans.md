# SNES ROM 镜像

用 Python 把 Super NES 卡带镜像当作文件处理：转储设备添加了什么，头部声明了什么，以及如何清除协处理器声明。一切以 Nintendo 的 SNES Development Manual 和一个包含 7,330 个卡带的库为准。

[English](README.md) | [日本語](README.ja.md) | 简体中文 | [繁體中文（香港）](README.zh-HK.md)

[![CI](https://github.com/gufranco/snes-rom-image-python/actions/workflows/ci.yml/badge.svg)](https://github.com/gufranco/snes-rom-image-python/actions/workflows/ci.yml)
[![Release](https://img.shields.io/github/v/release/gufranco/snes-rom-image-python)](https://github.com/gufranco/snes-rom-image-python/releases)
[![License](https://img.shields.io/badge/license-MIT-blue)](LICENSE)

重放 **489** 个声明，**0** 个失败，在全部 **7,330** 个卡带上逐一检查 **4** 项属性，计算出的校验和与 **2,780** 个零售版卡带中的 **2,768** 个一致，在手册中定位到 **20** 处引文，**781** 个测试，**100%** 语句与分支覆盖率，无依赖

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

示例构建了一个 512 KB 的镜像，其位于 `0x7FC0` 的头部声明芯片组 `0x03`，即 DSP。`needs_rewrite` 报告该声明必须去掉。`declare_rom_only` 把芯片组 `0x00` 和大小指数写入头部的每一份副本，然后基于结果重新计算校验和及其补码。第二次处理返回相同的字节。

## 安装

| 要求 | 版本 |
|:--|:--|
| Python | 3.12 或更高 |
| git | 任意版本，用于获取子模块 |

```bash
git clone --recurse-submodules https://github.com/gufranco/snes-rom-image-python.git
cd snes-rom-image-python
python3 romimage/doctor.py
```

本包只导入标准库和它唯一的子模块 [snes-mapper-python](https://github.com/gufranco/snes-mapper-python)，后者负责查找头部。通过下载 zip 链接得到的源码归档不含子模块，在那里每个读取头部的模块都会在导入时失败。如果检出时没有使用 `--recurse-submodules`，请运行 `git submodule update --init`。

本包无法从索引安装，也没有 `[project]` 块，因为它以按提交固定的子模块形式引入头部读取器，而不是以版本范围形式引入。

诊断脚本检查机器和检出：Python、子模块、语料库，以及对它自行构建的镜像执行两次的重写。任何检查失败时它以 1 退出。提交 bug 报告时请粘贴它的完整输出。它以一行结束：

```
  8 checks, nothing to report
```

发布遵循 [Semantic Versioning](https://semver.org/)，由 semantic-release 根据提交历史生成。每次发布都会打标签，并列在[发布页面](https://github.com/gufranco/snes-rom-image-python/releases)上。

## 接口

四个模块，每个回答关于文件的一个问题。

| 模块 | 问题 |
|:--|:--|
| [`dump`](romimage/dump.py) | 转储设备添加或拆分了什么 |
| [`identity`](romimage/identity.py) | 哪些摘要标识该文件，以及由哪一个决定 |
| [`rewrite`](romimage/rewrite.py) | 头部声明了什么，以及如何从中清除协处理器 |
| [`manifest`](romimage/manifest.py) | 当提供的文件不是预期的那个时，属于哪种不匹配 |

### 调用

| 调用 | 作用 |
|:--|:--|
| `dump.read(path)` | 返回镜像字节。文件会去掉拷贝机前缀。带编号分片的文件夹按名称顺序拼接。文件夹中没有分片时抛出 `NoParts` |
| `dump.form(path)` | 对文件按长度判断，返回 `"bare"` 或 `"copier header"`；对文件夹返回 `"N part set"` |
| `dump.strip_copier_stub(data)` | 当长度表明存在前缀时，去掉开头的 512 字节 |
| `dump.parts_in(folder)` | 带一到三位数字后缀的文件，按大写化后的名称排序 |
| `dump.join(parts)` | 去掉第一个分片的前缀后拼接所有分片 |
| `dump.deflate_ratio(block)` | deflate 级别 6 下压缩后大小与原始大小之比，空块为 0.0 |
| `dump.block_ratios(data, block=0x10000)` | 每个完整 64 KB 块的 `deflate_ratio` |
| `dump.measure_reuse(source, target, chunk=1024, stride=512)` | `(found, total)`：`source` 的 1 KB 块中有多少出现在 `target` 中 |
| `dump.chunk_index(data, chunk=1024, stride=512)` | `measure_reuse` 搜索所用的块到偏移的索引 |
| `identity.measure(data)` | 字节的 `size`、`crc32`、`md5`、`sha1` 和 `sha256` |
| `identity.agrees(found, expected)` | `sha256` 值相同时为 True。`expected` 没有 `sha256` 时抛出 `NoAuthority` |
| `rewrite.anchor_of(image)` | 读取器找到的头部的偏移，或 `None` |
| `rewrite.mirrors(image)` | 该头部每一份逐字节相同的副本的偏移 |
| `rewrite.describe(image)` | 每份副本一个字典：`at`、`title`、`map`、`chipset`、`coprocessor`、`size`、`sram`、`checksum` |
| `rewrite.needs_rewrite(image)` | 任一副本声明的芯片组不是 `0x00`，或大小字节与镜像自身不符时为 True。没有头部时抛出 `NoHeader` |
| `rewrite.declare_rom_only(image)` | 返回新的字节，其中每份副本都写入芯片组 `0x00`、正确的大小字节和重新计算的校验和。没有头部时抛出 `NoHeader` |
| `rewrite.checksum(image, places=None)` | 头部校验和，每份副本的四个校验和字节都按 `FF FF 00 00` 计入。`places` 默认为 `mirrors(image)` |
| `rewrite.mirrored_sum(data)` | 字节和，长度不是 2 的幂时镜像补足到 2 的幂 |
| `rewrite.size_byte(length)` | 大小指数：以千字节计的大小向上取整后的 2 的幂次 |
| `rewrite.identifies(block)` | 块中含有 `0x00`、`0x20` 或 `0xFF` 以外的字节时为 True |
| `rewrite.changes(before, after, block=0x1000)` | 所有字节不同的偏移 |

`declare_rom_only`、`needs_rewrite`、`AUTHORITATIVE`、`CHIPSET_ROM_ONLY` 和 `COPROCESSORS` 也在包的顶层公开。

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

同一个镜像前面加上 512 字节的前缀后，读回的仍是它自身的长度。它唯一的头部位于偏移 32704，即 `0x7FC0`，声明芯片组 3，[`rewrite.COPROCESSORS`](romimage/rewrite.py) 将其命名为 DSP。

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

普查用这两个函数描述一个库：每个 64 KB 块能压缩掉多少，以及一个镜像的 1 KB 块中有多少出现在另一个镜像中。

### 清单

`Manifest(document)` 接受一个带 `artifacts` 列表的映射。每个制品有一个 `name`、一个由已测量形式组成的 `accepted` 列表，以及可选的 `rewritten` 形式和 `bad` 列表，后者的每个条目带有 `why`。每个被接受的形式都需要 `sha256`。`Manifest.from_path(path)` 从 JSON 文件读取同样的文档。

| 调用 | 作用 |
|:--|:--|
| `document` | 构建它所用的映射，已经过上述检查 |
| `artifacts` | 所有制品，以元组形式 |
| `by_digest(found)` | 第一个其 accepted、rewritten 或 bad 形式与 `found` 一致的制品及其状态，或 `None` |
| `by_size(size)` | 所有带有该大小的被接受形式的制品 |
| `diagnose(data, form=None)` | 去掉前缀并测量，返回 `form`、`size`、`identity`、`state`、`artifact`、`why`、`same_size` 和 `headers` |
| `explain(found)` | 供人阅读的 `diagnose` 结果说明行，最后给出应采取的操作 |

| 状态 | 含义 |
|:--|:--|
| `known` | `sha256` 与某个被接受的形式一致 |
| `rewritten` | 与该制品的重写形式一致 |
| `bad dump` | 与已知的坏转储一致，`why` 说明它的问题 |
| `same size` | 没有摘要一致，但有一个被接受的形式大小相同 |
| `unknown` | 都不一致 |

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

带前缀的副本仍是 `known`，因为测量前会先去掉前缀。大小正确的全零文件是 `same size`，这指向不同的修订版或损坏的副本，而不是错误的游戏。

### 常量

| 名称 | 值 |
|:--|:--|
| `identity.AUTHORITATIVE` | `"sha256"`，唯一决定接受或拒绝的摘要 |
| `identity.INTEROPERABLE` | `("crc32", "md5", "sha1")`，为数据库查找而公开，从不用于决定 |
| `rewrite.CHIPSET_ROM_ONLY` | `0x00` |
| `rewrite.COPROCESSORS` | 本包已知的 18 个代码的芯片组字节到协处理器名称的映射，从 `0x03` DSP 到 `0xF9` SPC7110 |
| `rewrite.MAP_MODE`、`CHIPSET`、`ROM_SIZE`、`SRAM_SIZE` | 头部偏移 `0x15` 到 `0x18` |
| `rewrite.CHECKSUM_COMPLEMENT`、`CHECKSUM` | 头部偏移 `0x1C` 和 `0x1E` |
| `rewrite.CHECKSUM_FIELD_NEUTRAL` | `FF FF 00 00`，四个校验和字节计入时所取的值 |
| `rewrite.CHECKSUM_FIELD_BYTES`、`CHECKSUM_FIELD_SUM` | `4` 和 `0x01FE`，这些中性字节的长度及其和 |
| `rewrite.PADDING` | `0x00`、`0x20` 和 `0xFF`，`identifies` 视为填充的字节 |
| `rewrite.KILOBYTE` | `1024`，`size_byte` 向上取整所用的单位 |
| `rewrite.BLOCK_BYTES` | `0x1000`，`changes` 在逐字节比较之前所比较的块 |
| `dump.BARE`、`dump.COPIER` | `form` 对文件返回的两个名称 |
| `dump.PART_SUFFIX` | 带编号分片的后缀所匹配的模式：一个点加一到三位数字 |
| `dump.BLOCK_BYTES`、`DEFLATE_LEVEL` | `0x10000` 和 `6`，`block_ratios` 和 `deflate_ratio` 的默认值 |
| `dump.CHUNK_BYTES`、`CHUNK_STRIDE` | `1024` 和 `512`，`measure_reuse` 和 `chunk_index` 的默认值 |
| `manifest.KNOWN`、`REWRITTEN`、`BAD_DUMP`、`SAME_SIZE`、`UNKNOWN` | 五种状态 |
| `romimage.__version__` | 已安装的版本 |

### 错误

| 错误 | 抛出时机 |
|:--|:--|
| `NoParts` | `dump.read` 收到没有带编号分片的文件夹 |
| `NoAuthority` | `identity.agrees` 收到没有 `sha256` 的预期值 |
| `Malformed` | `Manifest` 收到没有制品、制品没有被接受的形式，或被接受的形式没有 `sha256` |
| `NoHeader` | `rewrite.needs_rewrite` 或 `rewrite.declare_rom_only` 找不到头部。它属于头部读取器，可通过 `rewrite.NoHeader` 访问 |

前三个位于 [`romimage/errors.py`](romimage/errors.py)，并在包的顶层公开。

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

两个相同的 CRC32 值会被拒绝而不是接受，因为只有 `sha256` 能决定。

### 命令行工具

| 命令 | 参数 | 退出码 |
|:--|:--|:--|
| `python3 romimage/doctor.py` | 无 | 每项检查都通过时为 0，否则为 1 |
| `python3 -m conformance.corpus` | 可选的语料库路径 | 每个声明都一致时为 0，有一个不一致时为 1，参数错误时为 2 |
| `python3 -m conformance.census` | `<library> <out.json> [limit]`。库是文件夹或 zip 归档 | 四项属性在每个镜像上都成立时为 0，有一项失败时为 1，参数错误时为 2 |
| `python3 -m conformance.documents` | `--check` 只校验不下载，`--only SUBSTRING` 选择单个文件 | 每份文档都校验通过时为 0，否则为 1 |
| `python3 -m conformance.quotes` | 无 | 每处引文都已定位或没有任何文档时为 0，否则为 1 |
| `python3 -m conformance.speed` | 无 | 每秒识别达到或超过 200 次时为 0，低于时为 1 |
| `python3 -m conformance.links` | 无 | 本文件中有地址返回 404 或 410 时为 1，否则为 0 |

## 本项目要防止的错误

### 拷贝机前缀会让文件中的每个偏移都发生移位

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

如果文件仍带有前缀，按已知地址写入的补丁会提前 512 字节落下。前缀按长度检测，因为它的内容没有标准，而且该规则从头部读取器导入，这样两个包对它的判断一致。

### 拆分集是分布在多个文件中的一个卡带

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

备份设备以大写写入文件名，并且只有第一个分片带有前缀。排序忽略大小写，所以改过名的分片集也按相同顺序拼接。

### 头部存在镜像，只改一份副本是不够的

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

镜像之所以存在，是因为同一个存储体在多个地址上可见，所以每份副本都与第一份逐字节相同。搜索匹配的是完整头部，因此一段看起来像标题的文本无法匹配。只更新一份副本的重写会让其他副本继续声明该协处理器。

### 校验和覆盖存放它的那些字节

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

求和覆盖整个镜像，包括存放结果的四个字节。Nintendo 的手册规定了这些字节按什么值计入，从而解决了这个问题："First, store 0FFH into the complement check area (FFDCH, FFDDH) and 00H into the check sum area (FFDEH, FFDFH). Then add each byte in the ROM data." 头部的每份副本都按同样方式处理。

### 长度不足 2 的幂的卡带会把尾部计入不止一次

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

2 的幂长度只求和一次。1.5 MB 的镜像按前 1 MB 加上剩余 512 KB 计两次来求和，这正是卡带呈现给总线的内容。手册写道："If ROM size cannot be expressed evenly in 2nM bit, such as 10M or 20M bit, add the remainder until a total of 2nM bit is reached." 本身不是 2 的幂的余数也按同样方式折叠。

在测量的 2,780 个零售版卡带中，有 633 个的长度不是 2 的幂。把它们的每个字节只加一次，只有 3 个与存储的校验和一致；而镜像求和有 626 个一致。

### 重写到一半的镜像不是卡带

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

`declare_rom_only` 在收到的镜像上只查找一次副本，并把结果传给 `checksum`。芯片组字节和大小字节是在这次查找与求和之间写入的，所以获得中性校验和字节的副本，就是在任何写入之前找到的那些。`checksum` 使用传入的偏移，只有在没有传入时才进行搜索。

### 大小字节是一个指数

```python
from romimage import rewrite

print(rewrite.size_byte(0x400000))
print(rewrite.size_byte(0x80000))
```

```
12
9
```

头部存储的是以千字节计的大小的 2 的幂次：4 MB 是 4,096 KB，即 2 的 12 次方。镜像增长超过某个 2 的幂后如果保留旧的字节，就会声明自己比实际小。

### 一个摘要做决定，其他摘要用于查找

```python
from romimage import identity

print(identity.AUTHORITATIVE)
print(sorted(identity.measure(b"a cartridge image would go here")))
```

```
sha256
['crc32', 'md5', 'sha1', 'sha256', 'size']
```

CRC32 是 32 位检错码，而 MD5 和 SHA-1 都有已公开的碰撞。三者都会公开，方便读者在以它们为索引的数据库中找到副本。它们都不能用来接受文件。

## 真实的库实际包含什么

在 **7,330** 个卡带上测量，另有 249 个因没有可读头部而被拒绝：

| 测量项 | 值 |
|:--|--:|
| 不同的声明 | 489 |
| 不同的镜像大小 | 108 |
| 不同的芯片组字节 | 36 |
| 需要重写的卡带 | 3,799 |
| 与头部读取器在是否有头部上的分歧 | 0 |

四项属性在每个卡带上检查，而不是抽样：

| 属性 | 成立数量 |
|:--|--:|
| 写入的校验和与其补码互为补码 | 7,330 / 7,330 |
| 基于结果重新计算得到写入的值 | 7,330 / 7,330 |
| 头部以外的内容没有改变 | 7,330 / 7,330 |
| 第二次重写不改变任何内容 | 7,330 / 7,330 |

有一项观察只做测量，不作为任何门禁检查：本包计算出的校验和是否就是卡带上已写入的那个。

| 群体 | 一致 |
|:--|--:|
| 头部自洽的授权零售版卡带 | 2,768 / 2,780 |
| 所有头部自洽的镜像，包括 hack | 4,502 / 7,167 |

修改了内容却没有重新计算校验和的 hack 不是本包的缺陷，所以这项观察只报告而不判定失败。四项属性询问的是代码是否与自身一致。这项观察询问的是卡带：一条在每个镜像上都以同样方式出错的校验和规则，能通过全部四项属性，却无法通过这项观察。[`conformance/divergences.json`](conformance/divergences.json) 列出了仍不一致的十二个零售版卡带，以及关于每个卡带的已知信息。

没有可读头部的文件计为被拒绝，普查不会为它捏造头部。

## 语料库，以及它为何可以随仓库发布

[`conformance/corpus.json`](conformance/corpus.json) 保存了 489 个不同的声明，以及各自有多少卡带带有该声明。

| 字段 | 性质 | 是否在语料库中 |
|:--|:--|:--|
| 大小、映射、芯片组、ROM 和 RAM 大小 | 关于实物的事实 | 是 |
| 共享某一组合的卡带数量 | 测量值 | 是 |
| 标题 | 名称 | 否 |
| 头部以外的任何内容 | 游戏本身 | 从不读取 |

依据 [17 U.S.C. 102(b)](https://www.law.cornell.edu/uscode/text/17/102) 和 *Feist*，事实和功能性要素不在版权保护范围内。[`conformance/census.py`](conformance/census.py) 不记录任何标题，语料库中的任何内容都无法重建任何卡带的任何部分。这是对仓库构建方式的说明，不是法律意见。

有两项断言仅凭语料库即可重放。每个声明记录的大小字节必须是 `size_byte` 根据其大小推导出的值。带有协处理器、或大小字节与自身不符的声明，必须是普查标记为需要重写的声明。第二项断言只在一个方向上成立：第一个头部干净的镜像仍可能因为后面的副本不一致而需要重写，而语料库记录的是第一份副本。

四项属性需要卡带本身，所以它们在普查中运行而不是在 CI 中运行，它们的计数作为测量记录随语料库一起保存。

### 对你自己的库进行普查

```bash
python3 -m conformance.census "/path/to/roms" census.json
python3 -m conformance.census library.zip census.json
```

它从文件夹或 zip 归档中读取 `.sfc`、`.smc`、`.fig` 和 `.swc` 文件。归档按成员逐个读取，而不是解压。它会打印上面的各项计数，并列出最多十个失败。

## 它是否正确

```bash
python3 -m conformance.corpus
```

```
  489 declarations from corpus.json
  measured across 7330 cartridges
  489 agreed, 0 did not
```

语料库的重放不需要机器上有任何卡带，并在 CI 中运行。有库时，`python3 -m conformance.census` 会在每个文件上检查四项属性。

[`conformance/hardware.json`](conformance/hardware.json) 逐条固定 Nintendo 手册中的事实，每条都附有出处原句及其所在页。[`conformance/hardware.test.py`](conformance/hardware.test.py) 让本包的常量与这些事实保持一致。存在手册副本时，`python3 -m conformance.quotes` 会在手册中定位全部 20 句引文。

手册未提及之处，由零售版卡带决定，其他一切都不算证据：不算模拟器，不算 wiki，也不算其他实现。[`conformance/divergences.json`](conformance/divergences.json) 记录了手册与卡带出现分歧的每一处、本包遵循哪一方，以及什么能解决该分歧。[OPEN-QUESTIONS.md](OPEN-QUESTIONS.md) 列出了仍未解决的 4 个问题。

## 参与开发

| 需求 | 位置 |
|:--|:--|
| 所有门禁检查及其运行顺序 | [CONTRIBUTING.md](CONTRIBUTING.md) |
| 面向编码代理的相同内容 | [AGENTS.md](AGENTS.md) |
| 本仓库与该系列其他仓库共享的标准 | [FAMILY.md](FAMILY.md) |
| bug 报告 | [GitHub Issues](https://github.com/gufranco/snes-rom-image-python/issues) |
| 安全报告 | [SECURITY.md](SECURITY.md) |

```bash
uvx ruff@0.16.3 format --check .
uvx ruff@0.16.3 check .
uvx --python 3.12 mypy==1.14.1
python3 romimage/rewrite.test.py
```

每个模块旁边都有一个以它命名的测试文件，并且每个测试文件都能像上面那样单独运行。覆盖率是一道硬性门禁检查，要求 100% 语句与分支覆盖，设置在 [`pyproject.toml`](pyproject.toml) 中：

```bash
python3 -m coverage erase
for file in $(find romimage conformance -name '*.test.py' | sort); do
  python3 -m coverage run -a "$file"
done
python3 -m coverage report
```

`python3 -m conformance.speed` 和 `python3 -m conformance.corpus` 在覆盖率步骤之外运行。

## 参考资料

- *SNES Development Manual, Book 1*，Nintendo of America Inc.，240 页，21,022,582 字节，SHA-256 `f1405241000046abba7849376d2ec53cf85f1ad2e9950d69a7c2cf1f3ff6b791`。它决定每个头部字节的含义以及校验和的计算方式。第 1-2-20 页定义了头部校验和。第 1-2-9 页为提交单定义了另一种简单求和，并明确说明："This method of calculation is different from the check sum on the ROM Registration Specification." 该手册不可再分发，也不在本仓库中。`python3 -m conformance.documents` 从 https://archive.org/download/SNESDevManual/book1_text.pdf 下载它到 git 忽略的 `docs/` 中，并拒绝任何其他文件。`python3 -m conformance.documents --check` 校验已存在的副本。
- 作者拥有的一个零售版卡带库，用于 [`conformance/corpus.json`](conformance/corpus.json) 中的 489 个声明，读取了 7,330 个文件。其中任何内容都未提交。
- [gufranco/snes-mapper-python](https://github.com/gufranco/snes-mapper-python)，用于查找头部，以按提交固定的子模块形式引入。

## 引用本项目

[CITATION.cff](CITATION.cff) 在每次发布时由写入包版本的脚本更新。

## 许可证

MIT。参见 [LICENSE](LICENSE)。
