# SNES ROM 映像檔

以 Python 檔案形式處理 Super NES 卡帶映像檔：傾印裝置加入了甚麼、標頭聲明了甚麼，以及如何清除協處理器聲明。一切以 Nintendo 的 SNES Development Manual 及一個收錄 7,330 盒卡帶的資料庫為準。

[English](README.md) | [日本語](README.ja.md) | [简体中文](README.zh-Hans.md) | 繁體中文（香港）

[![CI](https://github.com/gufranco/snes-rom-image-python/actions/workflows/ci.yml/badge.svg)](https://github.com/gufranco/snes-rom-image-python/actions/workflows/ci.yml)
[![Release](https://img.shields.io/github/v/release/gufranco/snes-rom-image-python)](https://github.com/gufranco/snes-rom-image-python/releases)
[![License](https://img.shields.io/badge/license-MIT-blue)](LICENSE)

重播 **489** 項聲明，**0** 項失敗，在全部 **7,330** 盒卡帶上逐一檢查 **4** 項屬性，計算所得的校驗和與 **2,780** 盒零售版卡帶中的 **2,768** 盒相符，在手冊中定位 **20** 段引文，**800** 個測試，**100%** 語句及分支覆蓋率，沒有依賴項

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

此示例建立一個 512 KB 的映像檔，其位於 `0x7FC0` 的標頭聲明晶片組 `0x03`，即 DSP。`needs_rewrite` 報告該聲明必須移除。`declare_rom_only` 將晶片組 `0x00` 及容量指數寫入標頭的每一份副本，然後在結果上重新計算校驗和及其補數。第二次處理會傳回相同的位元組。

## 安裝

| 要求 | 版本 |
|:--|:--|
| Python | 3.12 或更新 |
| git | 任何版本，用於取得子模組 |

```bash
git clone --recurse-submodules https://github.com/gufranco/snes-rom-image-python.git
cd snes-rom-image-python
python3 romimage/doctor.py
```

此套件除標準庫及其唯一的子模組 [snes-mapper-python](https://github.com/gufranco/snes-mapper-python) 外不匯入任何東西，該子模組負責尋找標頭。從下載 zip 連結取得的原始碼封存檔不含子模組，在那裏每個讀取標頭的模組都會在匯入時失敗。若檢出時沒有使用 `--recurse-submodules`，請執行 `git submodule update --init`。

此套件無法從套件索引安裝，也沒有 `[project]` 區塊，因為它以按提交固定的子模組形式取用標頭讀取器，而非以版本範圍取用。

診斷腳本檢查機器及檢出內容：Python、子模組、語料庫，以及對它自行建立的映像檔執行兩次的改寫。任何檢查失敗時它以 1 結束。請將其完整輸出貼到任何錯誤報告中。它以一行作結：

```
  8 checks, nothing to report
```

版本發佈遵循 [Semantic Versioning](https://semver.org/)，由 semantic-release 根據提交歷史產生。每個版本都會加上標籤，並列於[版本發佈頁面](https://github.com/gufranco/snes-rom-image-python/releases)。

## 介面

四個模組，各自回答關於檔案的一個問題。

| 模組 | 問題 |
|:--|:--|
| [`dump`](romimage/dump.py) | 傾印裝置加入或分拆了甚麼 |
| [`identity`](romimage/identity.py) | 哪些摘要可識別該檔案，以及由哪一個決定 |
| [`rewrite`](romimage/rewrite.py) | 標頭聲明了甚麼，以及如何從中清除協處理器 |
| [`manifest`](romimage/manifest.py) | 當提供的檔案並非預期的檔案時，屬於哪一種不符 |

### 呼叫

| 呼叫 | 作用 |
|:--|:--|
| `dump.read(path)` | 傳回映像檔位元組。檔案會去除其複製機前置段。由編號分段組成的資料夾按名稱順序合併。資料夾內沒有分段時引發 `NoParts` |
| `dump.form(path)` | 對檔案按長度判斷，傳回 `"bare"` 或 `"copier header"`，對資料夾則傳回 `"N part set"` |
| `dump.strip_copier_stub(data)` | 當長度顯示存在前置段時，捨棄開頭的 512 個位元組 |
| `dump.parts_in(folder)` | 帶一至三位數字後綴的檔案，按轉為大寫後的名稱排序 |
| `dump.join(parts)` | 去除第一個分段的前置段後，將各分段串接 |
| `dump.deflate_ratio(block)` | 以 deflate 等級 6 壓縮後的大小除以原始大小，空區塊為 0.0 |
| `dump.block_ratios(data, block=0x10000)` | 每個完整 64 KB 區塊的 `deflate_ratio` |
| `dump.measure_reuse(source, target, chunk=1024, stride=512)` | `(found, total)`：`source` 中有多少個 1 KB 區段出現在 `target` 中 |
| `dump.chunk_index(data, chunk=1024, stride=512)` | `measure_reuse` 搜尋所用的區段至偏移索引 |
| `identity.measure(data)` | 位元組的 `size`、`crc32`、`md5`、`sha1` 及 `sha256` |
| `identity.agrees(found, expected)` | `sha256` 值相符時為 True。`expected` 沒有 `sha256` 時引發 `NoAuthority` |
| `rewrite.anchor_of(image)` | 讀取器找到的標頭的偏移，或 `None` |
| `rewrite.mirrors(image)` | 該標頭每一份逐位元組相同的副本的偏移 |
| `rewrite.describe(image)` | 每份副本一個字典：`at`、`title`、`map`、`chipset`、`coprocessor`、`size`、`sram`、`checksum` |
| `rewrite.needs_rewrite(image)` | 任何副本聲明的晶片組不是 `0x00`，或容量位元組與映像檔本身不符時為 True。沒有標頭時引發 `NoHeader` |
| `rewrite.declare_rom_only(image)` | 傳回新的位元組，每份副本都帶晶片組 `0x00`、正確的容量位元組及重新計算的校驗和。沒有標頭時引發 `NoHeader` |
| `rewrite.checksum(image, places=None)` | 標頭校驗和，每份副本的四個校驗和位元組均按 `FF FF 00 00` 計算。`places` 預設為 `mirrors(image)` |
| `rewrite.mirrored_sum(data)` | 位元組總和，長度不是 2 的冪時鏡像補足至 2 的冪 |
| `rewrite.size_byte(length)` | 容量指數：以千位元組計的容量向上取整後的 2 的冪次 |
| `rewrite.identifies(block)` | 區塊含有 `0x00`、`0x20` 或 `0xFF` 以外的位元組時為 True |
| `rewrite.changes(before, after, block=0x1000)` | 每個位元組不同的偏移 |

`declare_rom_only`、`needs_rewrite`、`AUTHORITATIVE`、`CHIPSET_ROM_ONLY` 及 `COPROCESSORS` 亦在套件頂層公開。

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

同一個映像檔前面加上 512 位元組的前置段後，讀回的長度仍是其本身的長度。它唯一的標頭位於偏移 32704，即 `0x7FC0`，並聲明晶片組 3，[`rewrite.COPROCESSORS`](romimage/rewrite.py) 將其命名為 DSP。

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

普查以這兩者描述一個資料庫：每個 64 KB 區塊有多少可被壓縮掉，以及一個映像檔有多少個 1 KB 區段出現在另一個映像檔中。

### 清單

`Manifest(document)` 接受一個帶 `artifacts` 列表的映射。每個工件有一個 `name`、一個由已量度形式組成的 `accepted` 列表，並可選擇帶一個 `rewritten` 形式及一個 `bad` 列表，其條目帶有 `why`。每個已接受形式都需要 `sha256`。`Manifest.from_path(path)` 從 JSON 檔案讀取同樣的文件。

| 呼叫 | 作用 |
|:--|:--|
| `document` | 建立它所用的映射，已通過上述檢查 |
| `artifacts` | 各工件，以元組形式 |
| `by_digest(found)` | 第一個其已接受、已改寫或損壞形式與 `found` 相符的工件及其狀態，或 `None` |
| `by_size(size)` | 每個帶有該大小的已接受形式的工件 |
| `diagnose(data, form=None)` | 去除前置段、量度，並傳回 `form`、`size`、`identity`、`state`、`artifact`、`why`、`same_size` 及 `headers` |
| `explain(found)` | 供人閱讀的 `diagnose` 結果各行，最後說明應如何處理 |

| 狀態 | 意思 |
|:--|:--|
| `known` | `sha256` 與某個已接受形式相符 |
| `rewritten` | 與該工件的已改寫形式相符 |
| `bad dump` | 與某個已知的損壞傾印相符，`why` 說明其問題所在 |
| `same size` | 沒有摘要相符，而某個已接受形式的大小相同 |
| `unknown` | 甚麼都不相符 |

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

帶前置段的副本仍是 `known`，因為前置段在量度前已被去除。大小正確但全為零的檔案是 `same size`，這指向不同的修訂版或損壞的副本，而非錯誤的遊戲。

### 常數

| 名稱 | 值 |
|:--|:--|
| `identity.AUTHORITATIVE` | `"sha256"`，唯一用於接受或拒絕的摘要 |
| `identity.INTEROPERABLE` | `("crc32", "md5", "sha1")`，供數據庫查詢而公開，從不用於決定 |
| `rewrite.CHIPSET_ROM_ONLY` | `0x00` |
| `rewrite.COPROCESSORS` | 晶片組位元組至協處理器名稱，涵蓋套件已知的 18 個代碼，由 `0x03` DSP 至 `0xF9` SPC7110 |
| `rewrite.MAP_MODE`、`CHIPSET`、`ROM_SIZE`、`SRAM_SIZE` | 標頭偏移 `0x15` 至 `0x18` |
| `rewrite.CHECKSUM_COMPLEMENT`、`CHECKSUM` | 標頭偏移 `0x1C` 及 `0x1E` |
| `rewrite.CHECKSUM_FIELD_NEUTRAL` | `FF FF 00 00`，四個校驗和位元組按此計算 |
| `rewrite.CHECKSUM_FIELD_BYTES`、`CHECKSUM_FIELD_SUM` | `4` 及 `0x01FE`，這些中性位元組的長度及其總和 |
| `rewrite.PADDING` | `0x00`、`0x20` 及 `0xFF`，`identifies` 視為填充的位元組 |
| `rewrite.KILOBYTE` | `1024`，`size_byte` 向上取整所用的單位 |
| `rewrite.BLOCK_BYTES` | `0x1000`，`changes` 在逐個位元組比較前先比較的區塊 |
| `dump.BARE`、`dump.COPIER` | `form` 對檔案傳回的兩個名稱 |
| `dump.PART_SUFFIX` | 編號分段後綴所匹配的模式：一個句點加一至三位數字 |
| `dump.BLOCK_BYTES`、`DEFLATE_LEVEL` | `0x10000` 及 `6`，`block_ratios` 及 `deflate_ratio` 的預設值 |
| `dump.CHUNK_BYTES`、`CHUNK_STRIDE` | `1024` 及 `512`，`measure_reuse` 及 `chunk_index` 的預設值 |
| `manifest.KNOWN`、`REWRITTEN`、`BAD_DUMP`、`SAME_SIZE`、`UNKNOWN` | 五種狀態 |
| `romimage.__version__` | 已安裝的版本 |

### 錯誤

| 錯誤 | 引發時機 |
|:--|:--|
| `NoParts` | `dump.read` 收到一個沒有編號分段的資料夾 |
| `NoAuthority` | `identity.agrees` 收到一個沒有 `sha256` 的預期值 |
| `Malformed` | `Manifest` 收到的內容沒有工件、有工件沒有已接受形式，或有已接受形式沒有 `sha256` |
| `NoHeader` | `rewrite.needs_rewrite` 或 `rewrite.declare_rom_only` 找不到標頭。它屬於標頭讀取器，可經 `rewrite.NoHeader` 取得 |

前三個位於 [`romimage/errors.py`](romimage/errors.py)，並在套件頂層公開。

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

兩個相符的 CRC32 值會被拒絕而非接受，因為只有 `sha256` 能作決定。

### 命令列工具

| 命令 | 參數 | 結束代碼 |
|:--|:--|:--|
| `python3 romimage/doctor.py` | 無 | 每項檢查都通過時為 0，否則為 1 |
| `python3 -m conformance.corpus` | 可選的語料庫路徑 | 每項聲明都相符時為 0，有一項不符時為 1，參數錯誤時為 2 |
| `python3 -m conformance.census` | `<library> <out.json> [limit]`。資料庫是一個資料夾或 zip 封存檔 | 四項屬性在每個映像檔上都成立時為 0，有一項失敗時為 1，參數錯誤時為 2 |
| `python3 -m conformance.documents` | `--check` 只驗證而不下載，`--only SUBSTRING` 挑選一個檔案 | 每份文件都通過驗證時為 0，否則為 1 |
| `python3 -m conformance.quotes` | 無 | 每段引文都已定位或沒有文件時為 0，否則為 1 |
| `python3 -m conformance.speed` | 無 | 每秒 200 次識別或以上時為 0，低於此數時為 1 |
| `python3 -m conformance.links` | 無 | 本檔案中有地址回應 404 或 410 時為 1，否則為 0 |

## 本套件要防止的錯誤

### 複製機前置段會令檔案中每個偏移移位

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

若在仍帶前置段的檔案中按已知地址寫入修補，寫入位置會提前 512 個位元組。前置段按長度偵測，因為其內容沒有標準，而這條規則從標頭讀取器匯入，令兩個套件對此保持一致。

### 分拆組合是分成多個檔案的一盒卡帶

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

備份裝置以大寫寫入名稱，且只有第一個分段帶前置段。排序忽略大小寫，因此重新命名的組合仍按相同順序合併。

### 標頭有鏡像，只改一份副本並不足夠

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

鏡像之所以存在，是因為同一個記憶庫在多於一個地址可見，所以每份副本都與第一份逐位元組相同。搜尋比對的是完整標頭，因此一段看似標題的文字不會被誤認。只更新一份副本的改寫，會令其他副本繼續聲明該協處理器。

### 校驗和涵蓋儲存它的位元組

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

總和涵蓋整個映像檔，包括存放結果的四個位元組。Nintendo 的手冊指明這些位元組按甚麼值計算，從而解決此問題："First, store 0FFH into the complement check area (FFDCH, FFDDH) and 00H into the check sum area (FFDEH, FFDFH). Then add each byte in the ROM data." 標頭的每一份副本都得到同樣處理。

### 容量不足 2 的冪的卡帶，其尾部會被計算多於一次

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

容量為 2 的冪的映像檔只加總一次。1.5 MB 的映像檔按其首 1 MB 加上餘下 512 KB 計算兩次來加總，這正是卡帶呈現給匯流排的內容。手冊寫道："If ROM size cannot be expressed evenly in 2nM bit, such as 10M or 20M bit, add the remainder until a total of 2nM bit is reached." 本身不是 2 的冪的餘數，也以同樣方式摺疊。

在量度過的 2,780 盒零售版卡帶中，有 633 盒的容量不是 2 的冪。將它們每個位元組只加總一次，只有 3 盒與已儲存的校驗和相符，而鏡像總和則有 626 盒相符。

### 改寫進行中的映像檔不是卡帶

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

`declare_rom_only` 在收到的映像檔上只尋找一次副本，並將它們傳給 `checksum`。晶片組及容量位元組在該次搜尋與加總之間寫入，因此取得中性校驗和位元組的副本，正是任何寫入之前找到的那些。`checksum` 使用收到的偏移，只有在沒有收到任何偏移時才搜尋。

### 容量位元組是一個指數

```python
from romimage import rewrite

print(rewrite.size_byte(0x400000))
print(rewrite.size_byte(0x80000))
```

```
12
9
```

標頭儲存的是以千位元組計的容量的 2 的冪次：4 MB 即 4,096 KB，亦即 2 的 12 次方。若映像檔增大超過某個 2 的冪卻保留舊的位元組，就會聲明自己比實際小。

### 由一個摘要決定，其他摘要供查詢

```python
from romimage import identity

print(identity.AUTHORITATIVE)
print(sorted(identity.measure(b"a cartridge image would go here")))
```

```
sha256
['crc32', 'md5', 'sha1', 'sha256', 'size']
```

CRC32 是 32 位元的錯誤偵測碼，而 MD5 及 SHA-1 均有已公開的碰撞。三者均會公開，讓讀者能在以它們作索引的數據庫中找到副本。它們之中沒有一個能接受檔案。

## 真實資料庫實際包含甚麼

在 **7,330** 盒卡帶上量度，另有 249 盒因沒有可讀標頭而被拒絕：

| 量度項目 | 值 |
|:--|--:|
| 不同的聲明 | 489 |
| 不同的映像檔大小 | 108 |
| 不同的晶片組位元組 | 36 |
| 需要改寫的卡帶 | 3,799 |
| 在是否有標頭一事上與標頭讀取器的分歧 | 0 |

四項屬性在每盒卡帶上檢查，而非在樣本上：

| 屬性 | 成立數量 |
|:--|--:|
| 寫入的校驗和與其補數互為補數 | 7,330 之中 7,330 |
| 在結果上重新計算會得出寫入的值 | 7,330 之中 7,330 |
| 標頭以外沒有任何改變 | 7,330 之中 7,330 |
| 第二次改寫不會改變任何東西 | 7,330 之中 7,330 |

有一項觀察只作量度，不作任何關卡檢查：本套件計算的校驗和是否就是卡帶上已寫入的那一個。

| 群體 | 相符 |
|:--|--:|
| 標頭自洽的正式授權零售版卡帶 | 2,780 之中 2,768 |
| 所有標頭自洽的映像檔，包括改版 | 7,167 之中 4,502 |

改版修改了內容卻沒有重新計算校驗和，並非本套件的缺陷，因此這項觀察只作報告而不判為失敗。四項屬性問的是程式碼是否與自身一致。這項觀察問的是卡帶，而一條在每個映像檔上都以同樣方式出錯的校驗和規則，會通過全部四項屬性，卻在這項觀察上失敗。[`conformance/divergences.json`](conformance/divergences.json) 列出仍然不符的十二盒零售版卡帶，以及每一盒的已知資訊。

沒有可讀標頭的檔案計為被拒絕，普查不會為它虛構標頭。

## 語料庫，以及它為何可以發佈

[`conformance/corpus.json`](conformance/corpus.json) 收錄 489 項不同的聲明，以及帶有每項聲明的卡帶數量。

| 欄位 | 是甚麼 | 是否在語料庫中 |
|:--|:--|:--|
| 大小、映射、晶片組、ROM 及 RAM 容量 | 關於實物的事實 | 是 |
| 共用某一組合的卡帶數量 | 一項量度 | 是 |
| 標題 | 一個名稱 | 否 |
| 標頭以外的任何內容 | 遊戲本身 | 從不讀取 |

根據 [17 U.S.C. 102(b)](https://www.law.cornell.edu/uscode/text/17/102) 及 *Feist* 案，事實及功能性元素不在版權涵蓋範圍內。[`conformance/census.py`](conformance/census.py) 不記錄任何標題，語料庫中亦沒有任何內容能重建任何卡帶的任何部分。這是本儲存庫的構建方式，並非法律意見。

有兩項主張單憑語料庫即可重播。每項聲明記錄的容量位元組，必須是 `size_byte` 從其容量推導出的那一個。帶協處理器的聲明，或容量位元組與自身不符的聲明，必須是普查標記為需要改寫的聲明。第二項主張只單向成立：第一個標頭乾淨，仍可能因後面某份副本不一致而需要改寫，而語料庫記錄的是第一份副本。

四項屬性需要卡帶，因此它們在普查中執行而非在 CI 中執行，其計數則作為量度紀錄隨語料庫一併保存。

### 為你自己的資料庫進行普查

```bash
python3 -m conformance.census "/path/to/roms" census.json
python3 -m conformance.census library.zip census.json
```

它從資料夾或 zip 封存檔讀取 `.sfc`、`.smc`、`.fig` 及 `.swc` 檔案。封存檔逐個成員讀取，而不會解壓。它輸出上述計數，並列出最多十項失敗。

## 它是否正確

```bash
python3 -m conformance.corpus
```

```
  489 declarations from corpus.json
  measured across 7330 cartridges
  489 agreed, 0 did not
```

語料庫在機器上沒有任何卡帶時也能重播，並在 CI 中執行。有資料庫時，`python3 -m conformance.census` 會在每個檔案上檢查四項屬性。

[`conformance/hardware.json`](conformance/hardware.json) 將 Nintendo 的手冊逐項事實固定下來，每項都附有出處的句子及所在頁碼。[`conformance/hardware.test.py`](conformance/hardware.test.py) 以這些事實約束套件的常數。有手冊副本時，`python3 -m conformance.quotes` 會在手冊中定位全部 20 段引文。

手冊沒有說明之處，由零售版卡帶決定，其他一切都不算證據：模擬器、wiki 及其他實作都不算。[`conformance/divergences.json`](conformance/divergences.json) 記錄手冊與卡帶分歧的每一處、套件遵循哪一方，以及甚麼能解決分歧。[OPEN-QUESTIONS.md](OPEN-QUESTIONS.md) 列出仍未解決的 4 個問題。

## 參與開發

| 需要 | 位置 |
|:--|:--|
| 每項關卡檢查及其執行順序 | [CONTRIBUTING.md](CONTRIBUTING.md) |
| 供編程代理使用的同一份材料 | [AGENTS.md](AGENTS.md) |
| 本儲存庫與家族其餘成員共用的標準 | [FAMILY.md](FAMILY.md) |
| 錯誤報告 | [GitHub Issues](https://github.com/gufranco/snes-rom-image-python/issues) |
| 安全報告 | [SECURITY.md](SECURITY.md) |

```bash
uvx ruff@0.16.3 format --check .
uvx ruff@0.16.3 check .
uvx --python 3.12 mypy==1.14.1
python3 romimage/rewrite.test.py
```

每個模組旁邊都有一個以其命名的測試檔案，每個測試檔案都可如上所示單獨執行。覆蓋率是硬性關卡檢查，要求 100% 語句及分支覆蓋，設定於 [`pyproject.toml`](pyproject.toml)：

```bash
python3 -m coverage erase
for file in $(find romimage conformance -name '*.test.py' | sort); do
  python3 -m coverage run -a "$file"
done
python3 -m coverage report
```

`python3 -m conformance.speed` 及 `python3 -m conformance.corpus` 在覆蓋率步驟以外執行。

## 參考資料

- *SNES Development Manual, Book 1*，Nintendo of America Inc. 出版。240 頁，21,022,582 位元組，SHA-256 `f1405241000046abba7849376d2ec53cf85f1ad2e9950d69a7c2cf1f3ff6b791`。它決定每個標頭位元組的意思及校驗和的計算方法。第 1-2-20 頁定義標頭校驗和。第 1-2-9 頁為提交表格定義另一種簡單總和，並明言如此："This method of calculation is different from the check sum on the ROM Registration Specification." 該手冊不可再分發，亦不在本儲存庫中。`python3 -m conformance.documents` 會從 https://archive.org/download/SNESDevManual/book1_text.pdf 將其下載至 git 忽略的 `docs/`，並拒絕任何其他檔案。`python3 -m conformance.documents --check` 驗證已存在的副本。
- 作者擁有的零售版卡帶資料庫，用於 [`conformance/corpus.json`](conformance/corpus.json) 中的 489 項聲明，讀取自 7,330 個檔案。其中任何內容都沒有提交。
- [gufranco/snes-mapper-python](https://github.com/gufranco/snes-mapper-python)，用於尋找標頭，以按提交固定的子模組形式納入。

## 引用本專案

[CITATION.cff](CITATION.cff) 在每次版本發佈時，由標記套件版本的腳本更新。

## 授權

MIT。請參閱 [LICENSE](LICENSE)。
