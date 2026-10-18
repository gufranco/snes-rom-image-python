# SNES ROM Image

スーパーファミコンのカートリッジイメージをPythonでファイルとして扱います。ダンプ機器が付け加えたもの、ヘッダーが宣言している内容、コプロセッサの宣言を消す方法を扱い、NintendoのSNES Development Manualと7,330本のカートリッジのライブラリに照らして検証しています。

[English](README.md) | 日本語 | [简体中文](README.zh-Hans.md) | [繁體中文（香港）](README.zh-HK.md)

[![CI](https://github.com/gufranco/snes-rom-image-python/actions/workflows/ci.yml/badge.svg)](https://github.com/gufranco/snes-rom-image-python/actions/workflows/ci.yml)
[![Release](https://img.shields.io/github/v/release/gufranco/snes-rom-image-python)](https://github.com/gufranco/snes-rom-image-python/releases)
[![License](https://img.shields.io/badge/license-MIT-blue)](LICENSE)

**489**件の宣言を再生し、失敗は**0**件、**7,330**本のカートリッジすべてで**4**つの性質を確認、計算したチェックサムは市販カートリッジ**2,780**本中**2,768**本で一致、マニュアル内で**20**件の引用を特定、テスト**800**件、ステートメントとブランチのカバレッジ**100%**、依存関係なし

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

この例は512 KBのイメージを作ります。その`0x7FC0`にあるヘッダーはチップセット`0x03`、つまりDSPを宣言しています。`needs_rewrite`は、この宣言を取り除く必要があると報告します。`declare_rom_only`はヘッダーのすべてのコピーにチップセット`0x00`とサイズ指数を書き込み、その結果に対してチェックサムとその補数を再計算します。2回目の処理では同じバイト列が返ります。

## インストール

| 要件 | バージョン |
|:--|:--|
| Python | 3.12以降 |
| git | 任意。サブモジュールの取得に使います |

```bash
git clone --recurse-submodules https://github.com/gufranco/snes-rom-image-python.git
cd snes-rom-image-python
python3 romimage/doctor.py
```

このパッケージは標準ライブラリと、ヘッダーを見つける唯一のサブモジュール[snes-mapper-python](https://github.com/gufranco/snes-mapper-python)以外は何もインポートしません。download-zipリンクから得たソースアーカイブにはサブモジュールが含まれず、そこではヘッダーを読むモジュールがすべてインポート時に失敗します。`--recurse-submodules`なしで作ったチェックアウトでは、`git submodule update --init`を実行してください。

このパッケージはインデックスからインストールできず、`[project]`ブロックもありません。ヘッダーリーダーをバージョン範囲ではなく、コミットで固定したサブモジュールとして取り込んでいるためです。

ドクターはマシンとチェックアウトを確認します。対象はPython、サブモジュール、コーパス、そして自分で作ったイメージに対して2回実行する書き換えです。確認が1つでも失敗すると終了コード1で終了します。バグ報告には出力全体を貼り付けてください。出力は次の1行で終わります。

```
  8 checks, nothing to report
```

リリースは[Semantic Versioning](https://semver.org/)に従い、semantic-releaseがコミット履歴から作成します。すべてのリリースにはタグが付き、[リリースページ](https://github.com/gufranco/snes-rom-image-python/releases)に掲載されます。

## インターフェース

4つのモジュールがあり、それぞれがファイルについての1つの問いに答えます。

| モジュール | 問い |
|:--|:--|
| [`dump`](romimage/dump.py) | ダンプ機器は何を付け加え、何を分割したか |
| [`identity`](romimage/identity.py) | どのダイジェストがファイルを識別し、どれが判定を下すか |
| [`rewrite`](romimage/rewrite.py) | ヘッダーは何を宣言しているか、そこからコプロセッサをどう消すか |
| [`manifest`](romimage/manifest.py) | 渡されたファイルが期待したものでないとき、それはどの種類の不一致か |

### 呼び出し

| 呼び出し | 効果 |
|:--|:--|
| `dump.read(path)` | イメージのバイト列を返します。ファイルからはコピー機のスタブを取り除きます。番号付きパートのフォルダは名前順に連結します。パートが1つもないフォルダには`NoParts`を送出します |
| `dump.form(path)` | ファイルには長さで判断した`"bare"`または`"copier header"`を、フォルダには`"N part set"`を返します |
| `dump.strip_copier_stub(data)` | 長さからスタブがあると判断できるとき、先頭の512バイトを取り除きます |
| `dump.parts_in(folder)` | 1桁から3桁の数字のサフィックスを持つファイルを、大文字化した名前順に並べて返します |
| `dump.join(parts)` | 最初のパートからスタブを取り除いたうえで、パートを連結します |
| `dump.deflate_ratio(block)` | deflateレベル6での圧縮後サイズを元のサイズで割った値です。空のブロックでは0.0です |
| `dump.block_ratios(data, block=0x10000)` | 64 KBの完全なブロックそれぞれの`deflate_ratio`です |
| `dump.measure_reuse(source, target, chunk=1024, stride=512)` | `(found, total)`です。`source`の1 KBチャンクのうち、いくつが`target`に現れるかを示します |
| `dump.chunk_index(data, chunk=1024, stride=512)` | `measure_reuse`が検索する、チャンクからオフセットへのインデックスです |
| `identity.measure(data)` | バイト列の`size`、`crc32`、`md5`、`sha1`、`sha256`です |
| `identity.agrees(found, expected)` | `sha256`の値が一致するときTrueです。`expected`に`sha256`がないときは`NoAuthority`を送出します |
| `rewrite.anchor_of(image)` | リーダーが見つけたヘッダーのオフセット、または`None`です |
| `rewrite.mirrors(image)` | そのヘッダーとバイト単位で同一なすべてのコピーのオフセットです |
| `rewrite.describe(image)` | コピーごとに1つの辞書です。`at`、`title`、`map`、`chipset`、`coprocessor`、`size`、`sram`、`checksum`を持ちます |
| `rewrite.needs_rewrite(image)` | いずれかのコピーが`0x00`以外のチップセット、またはイメージ自身のものと異なるサイズバイトを宣言しているときTrueです。ヘッダーがないときは`NoHeader`を送出します |
| `rewrite.declare_rom_only(image)` | すべてのコピーでチップセットを`0x00`、サイズバイトを正しい値にし、チェックサムを再計算した新しいバイト列を返します。ヘッダーがないときは`NoHeader`を送出します |
| `rewrite.checksum(image, places=None)` | ヘッダーのチェックサムです。すべてのコピーの4つのチェックサムバイトを`FF FF 00 00`として数えます。`places`のデフォルトは`mirrors(image)`です |
| `rewrite.mirrored_sum(data)` | バイトの合計です。長さが2の累乗でない場合は、2の累乗になるまでミラーします |
| `rewrite.size_byte(length)` | サイズ指数です。キロバイト単位のサイズを2の累乗で表した指数を、切り上げて返します |
| `rewrite.identifies(block)` | ブロックに`0x00`、`0x20`、`0xFF`以外のバイトが含まれるときTrueです |
| `rewrite.changes(before, after, block=0x1000)` | バイトが異なるすべてのオフセットです |

`declare_rom_only`、`needs_rewrite`、`AUTHORITATIVE`、`CHIPSET_ROM_ONLY`、`COPROCESSORS`はパッケージのトップレベルでも公開しています。

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

同じイメージの前に512バイトのスタブを付けても、読み戻すと元の長さになります。唯一のヘッダーはオフセット32704、つまり`0x7FC0`にあり、チップセット3を宣言しています。[`rewrite.COPROCESSORS`](romimage/rewrite.py)はこれをDSPと名付けています。

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

全数調査はこの2つを使ってライブラリを記述します。64 KBの各ブロックが圧縮でどれだけ小さくなるか、そしてあるイメージの1 KBチャンクのうちいくつが別のイメージに現れるかです。

### マニフェスト

`Manifest(document)`は`artifacts`リストを持つマッピングを受け取ります。各アーティファクトは`name`と、計測済みの形式を並べた`accepted`リストを持ち、省略可能な項目として`rewritten`形式と、各エントリが`why`を持つ`bad`リストがあります。受け入れる形式にはすべて`sha256`が必要です。`Manifest.from_path(path)`は同じドキュメントをJSONファイルから読み込みます。

| 呼び出し | 効果 |
|:--|:--|
| `document` | 上記の確認を経た、構築元のマッピングです |
| `artifacts` | アーティファクトのタプルです |
| `by_digest(found)` | accepted、rewritten、badのいずれかの形式が`found`と一致する最初のアーティファクトとその状態、または`None`です |
| `by_size(size)` | そのサイズのaccepted形式を持つすべてのアーティファクトです |
| `diagnose(data, form=None)` | スタブを取り除いて計測し、`form`、`size`、`identity`、`state`、`artifact`、`why`、`same_size`、`headers`を返します |
| `explain(found)` | `diagnose`の結果について人が読む行です。最後にすべきことを示します |

| 状態 | 意味 |
|:--|:--|
| `known` | `sha256`がaccepted形式と一致します |
| `rewritten` | アーティファクトのrewritten形式と一致します |
| `bad dump` | 既知の不良ダンプと一致し、`why`がその問題を説明します |
| `same size` | どのダイジェストも一致せず、同じサイズのaccepted形式があります |
| `unknown` | 何も一致しません |

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

スタブ付きのコピーも`known`のままです。計測の前にスタブを取り除くためです。正しいサイズのゼロだけのファイルは`same size`になります。これは別のゲームではなく、別のリビジョンか破損したコピーを示しています。

### 定数

| 名前 | 値 |
|:--|:--|
| `identity.AUTHORITATIVE` | `"sha256"`。受け入れと拒否を決める唯一のダイジェストです |
| `identity.INTEROPERABLE` | `("crc32", "md5", "sha1")`。データベース検索のために公開しており、判定には一切使いません |
| `rewrite.CHIPSET_ROM_ONLY` | `0x00` |
| `rewrite.COPROCESSORS` | パッケージが知っている18個のコードについて、チップセットバイトからコプロセッサ名への対応です。`0x03`のDSPから`0xF9`のSPC7110まであります |
| `rewrite.MAP_MODE`、`CHIPSET`、`ROM_SIZE`、`SRAM_SIZE` | ヘッダーオフセット`0x15`から`0x18` |
| `rewrite.CHECKSUM_COMPLEMENT`、`CHECKSUM` | ヘッダーオフセット`0x1C`と`0x1E` |
| `rewrite.CHECKSUM_FIELD_NEUTRAL` | `FF FF 00 00`。4つのチェックサムバイトをこの値として数えます |
| `rewrite.CHECKSUM_FIELD_BYTES`、`CHECKSUM_FIELD_SUM` | `4`と`0x01FE`。その中立バイトの長さと合計です |
| `rewrite.PADDING` | `0x00`、`0x20`、`0xFF`。`identifies`が埋め草として扱うバイトです |
| `rewrite.KILOBYTE` | `1024`。`size_byte`が切り上げる単位です |
| `rewrite.BLOCK_BYTES` | `0x1000`。`changes`が個々のバイトを見る前に比較するブロックです |
| `dump.BARE`、`dump.COPIER` | `form`がファイルに対して返す2つの名前です |
| `dump.PART_SUFFIX` | 番号付きパートのサフィックスが一致するパターンです。ドットと1桁から3桁の数字です |
| `dump.BLOCK_BYTES`、`DEFLATE_LEVEL` | `0x10000`と`6`。`block_ratios`と`deflate_ratio`のデフォルトです |
| `dump.CHUNK_BYTES`、`CHUNK_STRIDE` | `1024`と`512`。`measure_reuse`と`chunk_index`のデフォルトです |
| `manifest.KNOWN`、`REWRITTEN`、`BAD_DUMP`、`SAME_SIZE`、`UNKNOWN` | 5つの状態です |
| `romimage.__version__` | インストールされているバージョンです |

### エラー

| エラー | 送出される条件 |
|:--|:--|
| `NoParts` | `dump.read`に番号付きパートのないフォルダが渡されたとき |
| `NoAuthority` | `identity.agrees`に`sha256`のない期待値が渡されたとき |
| `Malformed` | `Manifest`にアーティファクトがない、accepted形式のないアーティファクトがある、または`sha256`のないaccepted形式が渡されたとき |
| `NoHeader` | `rewrite.needs_rewrite`または`rewrite.declare_rom_only`がヘッダーを見つけられないとき。ヘッダーリーダーに属するエラーで、`rewrite.NoHeader`として参照できます |

最初の3つは[`romimage/errors.py`](romimage/errors.py)にあり、パッケージのトップレベルで公開しています。

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

一致する2つのCRC32値は受け入れられず、拒否されます。判定を下すのは`sha256`だけだからです。

### コマンドラインツール

| コマンド | 引数 | 終了コード |
|:--|:--|:--|
| `python3 romimage/doctor.py` | なし | すべての確認が通れば0、それ以外は1 |
| `python3 -m conformance.corpus` | 省略可能なコーパスのパス | すべての宣言が一致すれば0、1つでも一致しなければ1、引数が誤っていれば2 |
| `python3 -m conformance.census` | `<library> <out.json> [limit]`。ライブラリはフォルダまたはzipアーカイブです | すべてのイメージで4つの性質が成り立てば0、1つでも失敗すれば1、引数が誤っていれば2 |
| `python3 -m conformance.documents` | 取得せずに検証する`--check`、ファイルを選ぶ`--only SUBSTRING` | すべてのドキュメントが検証を通れば0、それ以外は1 |
| `python3 -m conformance.quotes` | なし | すべての引用が見つかるか、ドキュメントが1つもなければ0、それ以外は1 |
| `python3 -m conformance.speed` | なし | 毎秒200件以上の識別で0、それ未満で1 |
| `python3 -m conformance.links` | なし | このファイル内のアドレスが404または410を返せば1、それ以外は0 |

## このパッケージが防ぐ間違い

### コピー機のスタブはファイル内のすべてのオフセットをずらす

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

スタブが残ったままのファイルに既知のアドレスでパッチを書き込むと、512バイト手前に書き込まれます。スタブの内容は標準化されていないため、スタブは長さで検出します。その規則はヘッダーリーダーからインポートしているので、2つのパッケージの判断は一致します。

### 分割セットは1本のカートリッジを複数のファイルにしたもの

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

バックアップ機器は名前を大文字で書き込み、スタブを持つのは最初のパートだけです。並べ替えは大文字と小文字を区別しないので、名前を変えたセットも同じ順序で連結されます。

### ヘッダーはミラーされており、1つのコピーだけでは足りない

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

ミラーが存在するのは、同じバンクが複数のアドレスから見えるためです。そのため、どのコピーも最初のものとバイト単位で同一です。検索はヘッダー全体で照合するので、タイトルに似た文字列が一致することはありません。1つのコピーだけを更新する書き換えでは、残りのコピーがコプロセッサを宣言したままになります。

### チェックサムは、それを格納するバイト自身も対象に含む

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

合計はイメージ全体にわたり、結果を格納する4バイトも含みます。Nintendoのマニュアルは、それらのバイトを何として数えるかを定めることでこの問題を解決しています。「First, store 0FFH into the complement check area (FFDCH, FFDDH) and 00H into the check sum area (FFDEH, FFDFH). Then add each byte in the ROM data.」ヘッダーのすべてのコピーが同じ扱いを受けます。

### 2の累乗より短いカートリッジは末尾を複数回数える

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

2の累乗のサイズは1回だけ合計します。1.5 MBのイメージは、最初の1 MBに、残りの512 KBを2回数えたものを加えて合計します。これはカートリッジがバスに見せる内容と同じです。マニュアルには次のようにあります。「If ROM size cannot be expressed evenly in 2nM bit, such as 10M or 20M bit, add the remainder until a total of 2nM bit is reached.」残りの部分自体が2の累乗でない場合も、同じように折り返します。

計測した市販カートリッジ2,780本のうち、633本は2の累乗ではありません。それらの各バイトを1回ずつ合計すると、格納されたチェックサムと一致するのは3本で、ミラーした合計では626本が一致します。

### 書き換え途中のものはカートリッジではない

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

`declare_rom_only`は渡されたイメージ上でコピーを一度だけ探し、それを`checksum`に渡します。チップセットとサイズのバイトはその検索と合計の間に書き込まれるので、中立のチェックサムバイトを受け取るコピーは、書き込み前に見つかったものです。`checksum`は渡されたオフセットを使い、何も渡されなかったときだけ検索します。

### サイズバイトは指数

```python
from romimage import rewrite

print(rewrite.size_byte(0x400000))
print(rewrite.size_byte(0x80000))
```

```
12
9
```

ヘッダーには、キロバイト単位のサイズを2の累乗で表した指数が格納されます。4 MBは4,096 KBで、2の12乗です。2の累乗を超えて大きくなったのに古いバイトを残したイメージは、実際より小さいと宣言することになります。

### 判定を下すダイジェストは1つで、他は検索用

```python
from romimage import identity

print(identity.AUTHORITATIVE)
print(sorted(identity.measure(b"a cartridge image would go here")))
```

```
sha256
['crc32', 'md5', 'sha1', 'sha256', 'size']
```

CRC32は32ビットの誤り検出符号で、MD5とSHA-1には衝突が公表されています。3つとも、それらで索引付けしたデータベースからコピーを探せるように公開しています。いずれもファイルを受け入れる根拠にはなりません。

## 実際のライブラリに含まれているもの

**7,330**本のカートリッジで計測しました。このほか249本は読めるヘッダーがないため拒否しました。

| 計測項目 | 値 |
|:--|--:|
| 異なる宣言の数 | 489 |
| 異なるイメージサイズの数 | 108 |
| 異なるチップセットバイトの数 | 36 |
| 書き換えが必要になるカートリッジ | 3,799 |
| ヘッダーの有無についてヘッダーリーダーと食い違った数 | 0 |

4つの性質は、サンプルではなくすべてのカートリッジで確認しています。

| 性質 | 成り立った数 |
|:--|--:|
| 書き込んだチェックサムとその補数が互いに補数になっている | 7,330本中7,330本 |
| 結果に対して再計算すると書き込んだ値が返る | 7,330本中7,330本 |
| ヘッダーの外側は何も変わっていない | 7,330本中7,330本 |
| 2回目の書き換えでは何も変わらない | 7,330本中7,330本 |

1つの観測は計測するだけで、何のゲートにもなりません。このパッケージが計算したチェックサムが、カートリッジにすでに書かれているものと同じかどうかです。

| 母集団 | 一致 |
|:--|--:|
| 自己矛盾のないヘッダーを持つライセンス済み市販カートリッジ | 2,780本中2,768本 |
| 自己矛盾のないヘッダーを持つすべてのイメージ（ハックを含む） | 7,167本中4,502本 |

内容を変えてチェックサムを再計算しなかったハックは、このパッケージの欠陥ではありません。そのため、この観測は失敗とせず報告するだけです。4つの性質は、コードが自分自身と一致するかを問います。観測はカートリッジに問います。すべてのイメージで同じように誤っているチェックサム規則は、4つの性質をすべて通りながら、この観測では失敗します。[`conformance/divergences.json`](conformance/divergences.json)は、まだ一致しない12本の市販カートリッジと、それぞれについてわかっていることを挙げています。

読めるヘッダーのないファイルは拒否として数え、全数調査はそのファイルにヘッダーをでっち上げません。

## コーパスと、それを配布できる理由

[`conformance/corpus.json`](conformance/corpus.json)は、489件の異なる宣言と、それぞれを持つカートリッジの数を保持しています。

| フィールド | 内容 | コーパスに含むか |
|:--|:--|:--|
| サイズ、マッピング、チップセット、ROMとRAMのサイズ | 物理的な物体についての事実 | はい |
| ある組み合わせを共有するカートリッジの数 | 計測値 | はい |
| タイトル | 名前 | いいえ |
| ヘッダーの外側すべて | ゲームそのもの | 一切読みません |

事実と機能的要素は、[17 U.S.C. 102(b)](https://www.law.cornell.edu/uscode/text/17/102)と*Feist*により、著作権の及ぶ範囲の外にあります。[`conformance/census.py`](conformance/census.py)はタイトルを記録せず、コーパスのどの部分からもカートリッジのいかなる部分も再構築できません。これはこのリポジトリの作り方の説明であり、法的助言ではありません。

コーパスだけで再生できる主張が2つあります。各宣言について記録されたサイズバイトは、`size_byte`がそのサイズから導くものでなければなりません。コプロセッサを持つ宣言、または自身のものではないサイズバイトを持つ宣言は、全数調査が書き換えの必要ありと記録したものでなければなりません。2つ目の主張は一方向にしか成り立ちません。最初のヘッダーに問題がなくても、後のコピーが食い違っていれば書き換えが必要になることがあり、コーパスが記録するのは最初のコピーだからです。

4つの性質にはカートリッジが必要なので、CIではなく全数調査で実行します。その件数は、何を計測したかの記録としてコーパスに含めています。

### 自分のライブラリを全数調査する

```bash
python3 -m conformance.census "/path/to/roms" census.json
python3 -m conformance.census library.zip census.json
```

フォルダまたはzipアーカイブから`.sfc`、`.smc`、`.fig`、`.swc`ファイルを読み込みます。アーカイブは展開せず、メンバーごとに読みます。上記の件数を出力し、失敗を最大10件まで一覧表示します。

## 正しいかどうか

```bash
python3 -m conformance.corpus
```

```
  489 declarations from corpus.json
  measured across 7330 cartridges
  489 agreed, 0 did not
```

コーパスはマシン上にカートリッジがなくても再生でき、CIで実行されます。ライブラリがある場合は、`python3 -m conformance.census`がすべてのファイルで4つの性質を確認します。

[`conformance/hardware.json`](conformance/hardware.json)はNintendoのマニュアルを事実ごとに固定しており、それぞれに出典の文と掲載ページを付けています。[`conformance/hardware.test.py`](conformance/hardware.test.py)は、パッケージの定数をそれらの事実に照らして検証します。`python3 -m conformance.quotes`は、マニュアルのコピーがあれば、引用した20の文すべてをマニュアル内で特定します。

マニュアルに記述がない点は市販カートリッジが決め、それ以外は証拠として扱いません。エミュレータも、wikiも、他の実装も証拠にはなりません。[`conformance/divergences.json`](conformance/divergences.json)は、マニュアルとカートリッジが食い違うすべての箇所について、パッケージがどちらに従うか、そして何があれば決着するかを記録しています。[OPEN-QUESTIONS.md](OPEN-QUESTIONS.md)には、まだ未解決の4つの問いを挙げています。

## 開発に参加する

| 必要なもの | 場所 |
|:--|:--|
| すべてのゲートとその実行順序 | [CONTRIBUTING.md](CONTRIBUTING.md) |
| コーディングエージェント向けの同じ内容 | [AGENTS.md](AGENTS.md) |
| このリポジトリがファミリーの他のリポジトリと共有する基準 | [FAMILY.md](FAMILY.md) |
| バグ報告 | [GitHub Issues](https://github.com/gufranco/snes-rom-image-python/issues) |
| セキュリティ報告 | [SECURITY.md](SECURITY.md) |

```bash
uvx ruff@0.16.3 format --check .
uvx ruff@0.16.3 check .
uvx --python 3.12 mypy==1.14.1
python3 romimage/rewrite.test.py
```

各モジュールには、その横に同じ名前のテストファイルがあり、上のようにそれぞれ単独で実行できます。カバレッジはステートメントとブランチの100%を必須とするゲートで、[`pyproject.toml`](pyproject.toml)で設定しています。

```bash
python3 -m coverage erase
for file in $(find romimage conformance -name '*.test.py' | sort); do
  python3 -m coverage run -a "$file"
done
python3 -m coverage report
```

`python3 -m conformance.speed`と`python3 -m conformance.corpus`は、カバレッジの手順の外で実行します。

## 参考資料

- *SNES Development Manual, Book 1*、Nintendo of America Inc.。240ページ、21,022,582バイト、SHA-256 `f1405241000046abba7849376d2ec53cf85f1ad2e9950d69a7c2cf1f3ff6b791`。各ヘッダーバイトの意味と、チェックサムの計算方法を決めるものです。1-2-20ページがヘッダーのチェックサムを定義しています。1-2-9ページは提出用シートのための別の単純な合計を定義しており、そのことを明記しています。「This method of calculation is different from the check sum on the ROM Registration Specification.」このマニュアルは再配布できず、このリポジトリには含まれていません。`python3 -m conformance.documents`は https://archive.org/download/SNESDevManual/book1_text.pdf からgitが無視する`docs/`にダウンロードし、それ以外のファイルは拒否します。`python3 -m conformance.documents --check`は、すでにあるコピーを検証します。
- 作者が所有する市販カートリッジのライブラリ。[`conformance/corpus.json`](conformance/corpus.json)の489件の宣言の元になったもので、7,330ファイルにわたって読み込みました。そこからは何もコミットしていません。
- [gufranco/snes-mapper-python](https://github.com/gufranco/snes-mapper-python)。ヘッダーを見つけるためのもので、コミットで固定したサブモジュールとして取り込んでいます。

## 引用

[CITATION.cff](CITATION.cff)は、リリースのたびにパッケージのバージョンを刻むスクリプトによって更新されます。

## ライセンス

MITです。[LICENSE](LICENSE)を参照してください。
