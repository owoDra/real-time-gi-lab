# プロジェクトの構成

## ディレクトリ

| 場所 | 役割 | git |
|---|---|---|
| `src/core/` | レンダラの本体。WebGPU のコア機能だけで書く（WGSL は TypeScript の中） | 管理 |
| `src/native/` | Node から Dawn を使う実行器（計測、参照との比較、シーンの変換）と、ブラウザの実行の駆動（`browser.ts`） | 管理 |
| `src/web/`、`web/` | ブラウザの実行器（`src/web/rc.ts` とページ `web/rc.html`。`src/core/` をそのまま使う） | 管理 |
| `src/runner/` | ネイティブとブラウザの実行器が共有する部分（設定名、場面名、ログと要約、テクスチャの大きさ） | 管理 |
| `scripts/` | 計測の掃引、要約、参照レンダラの積分器、文書の検査 | 管理 |
| `docs/spec/` | 正本（目的、評価、構成、測った結果、方向） | 管理 |
| `docs/plan/` | 作業の計画（列とフェーズ） | 管理 |
| `docs/reference/` | 先行研究、Program 1 の知見、数値の要約（`measurements/`） | 管理 |
| `legacy/` | Program 1 の参照コード。ビルドしない（[legacy/README.md](../legacy/README.md)） | 管理 |
| `box/out/` | 実行の出力（画像、ダンプ、ログ、参照）。要約を作ったら消す | 管理外 |
| `box/in/` | ユーザーとの一時ファイルの受け渡し | 管理外 |
| `build/` | バンドルした実行器と、参照レンダラの Python 環境（`build/refenv`） | 管理外 |
| `assets/` | テストシーン（`mise run assets` で取得） | 管理外 |
| `archive-local/` | Program 1 のテキスト記録の圧縮アーカイブ（下の「作業機にしかないもの」） | 管理外 |

`src/core/` の主なファイル：`rc.ts`（放射輝度場）、`voxel.ts`（ボクセル StrataBrick、静的な形状）、`dynlayer.ts`（動的物体の被覆率と放射のレイヤ）、`bounce.ts`（多重バウンスの跳ね返りボリューム）、`ddgi.ts`
（DDGI 系の比較相手）、`style.ts`（スタイル演算子）、`bvh.ts`（三角形の正解器）、`lighting.ts`（太陽と影）、
`gbuffer.ts`、`scenes.ts`（シーン）、`post.ts`（表示とちらつきの指標）、`rcrun.ts`（計測の実行）。

## コマンド

```bash
mise install
npm ci            # 依存はバージョン固定（package-lock.json）
mise run assets   # Khronos glTF Sponza を取得
mise run check    # 文書のリンクと legacy 目録を検査
mise run typecheck
mise run build:rc # 実行器をバンドル（build/native/rc.mjs）

# レンダラの実行と計測（ネイティブ、Dawn / Vulkan）
bash scripts/run_with_vulkan.sh node build/native/rc.mjs --scene <シーン> --configs <設定,...> \
  [--no-sky] [--vox JSON] [--frames N] [--warmup N] [--dump-irr] [--response FROM,TO] [--pose-frame F] \
  [--seq EVERY,COUNT] [--out box/out/<名前>]   # --seq：静止カメラで EVERY フレームおきに最終画像と間接光を保存（時間は乱れる）
mise run s2:native -- --scene sponza --vox-bench     # 再ボクセル化の段ごとの時間

# ブラウザ（Phase 30）。ページを 127.0.0.1 で配り、ブラウザを新しいプロファイルで開き、終わったら閉じる（同じプロファイルのプロセスが残らないことを確かめる）
mise run build:web
bash scripts/run_with_vulkan.sh node build/native/browser.mjs --scene <シーン> --configs <設定,...> [rc.mjs と同じ引数] \
  [--browser brave] [--browser-flags "--ozone-platform=wayland"] [--no-launch] [--out box/out/<名前>]
#   既定で付ける起動の引数：--enable-unsafe-webgpu --enable-webgpu-developer-features（タイムスタンプを丸めない）--ignore-gpu-blocklist
#   --no-launch：URL を出して待つ（別の機械や手で開くブラウザ用）。ネイティブの引数は全部使える（--bvh、--dyn-stages、--response、--seq、--vox-bench も）
node build/native/compare_runs.mjs --a <ネイティブの出力> --b <ブラウザの出力> --config <設定> [--png DIR]   # 画像の一致（8 ビットの差、間接光の相対差）
# --dyn-stages：動的レイヤ（と全再構築では建物のボクセル）の作成を段ごとのパスに分けて時間を測り、動的レイヤの仕事の量を CPU で数える（160 フレーム以下）
# 場面名の末尾 -bwave / -bcut：建物そのものが毎フレーム変わる（spec/10-evaluation.md）
# --vox：voxel.ts の DEFAULT_VOX の上書き（v0、levels、G、maxBricks、maxVoxels、dynBricks）

# 参照（Mitsuba）
mise run ref:export -- --scene sponza                # シーン変換（box/out/mitsuba/<シーン>）
build/refenv/bin/python scripts/reference_irradiance.py box/out/mitsuba/sponza --spp 512 [--sky r,g,b] [--seed N] [--bounces 0]  # 0: 打ち切りなしの多重バウンス
mise run ref:compare -- --ref A.pfm,B.pfm --ours <cfg>.static.irr.f32 [--png DIR]
mise run ref:style -- --ref-base A,B --ref-style C,D --ours-base x.irr.f32 --ours-style y.irr.f32 [--png DIR]
```

- 設定名の書式とトークン（`world-48-voxel-rc2-vrel`、`ddgi-100-128-u2-g1-noadapt` など）と引数は
  `src/native/rc.ts` の先頭に書いてある。シーン名は [spec/10-evaluation.md](spec/10-evaluation.md)。
- 既定の構成は `--configs world-48-voxel-rc2-vrel`（`--vox` なし。全形状を毎フレーム作り直す）
  （[spec/20-renderer.md](spec/20-renderer.md)）。
- `scripts/m1_sweep.sh` と `scripts/m1_dynamic.sh` は、[spec/30-measurements.md](spec/30-measurements.md) の 5 節と
  7 節を測った掃引。`scripts/m1_summary.py` と `scripts/m1_dynamic_summary.py` がその要約を作る。
- 光源切替への応答（`--response`）は 1080p の放射照度を毎フレーム読むので、設定 1 つに 1〜3 分かかる。

## 作業機の事情（開発機、NixOS）

- ネイティブの Vulkan / Dawn は `bash scripts/run_with_vulkan.sh <コマンド>` 経由で動かす（ライブラリのパスを足す）。
  その環境変数を `git` や `gh` に渡さない。
- ブラウザ（Brave 1.91、Chromium 149）の WebGPU は、既定の起動とヘッドレスでは SwiftShader（CPU）に落ちる。`scripts/run_with_vulkan.sh` 経由で
  起動し（Vulkan のローダーが見える）、Wayland の窓（`--ozone-platform=wayland`）にすると実 GPU（AMD Radeon 8060S、RADV）になる。GPU のサンドボックスは切らない。
  `brave` は起動用のスクリプトなので、それだけを止めると本体が残る（`browser.ts` はプロセスグループとプロファイルで止める）。
- 参照レンダラのセットアップは [spec/10-evaluation.md](spec/10-evaluation.md)。Mitsuba（CPU 32 スレッド）と GPU の計測は
  同じ電力枠を使うので、同時に走らせない。

## 作業機にしかないもの

- `box/out/mitsuba/`：Mitsuba 用のシーンと、512 spp の参照（`sponza`、`sponza-toon`、`sponza-objects`、
  `sponza-dyn-f140`、`sponza-dyn-f300`、`sponza-dynobj-f0`）。描き直すと 1 本約 5 分。`mise run clean` は `build` と `box/out` を消すので、
  参照も消える。
- `build/refenv`：参照レンダラの Python 環境。
- `archive-local/`（96 MB）：Program 1 のテキスト記録 35,854 ファイルの圧縮アーカイブと、全ファイルの目録。
  Program 1 の生データ（約 411 GB）は 2026-11-13 に削除し、バイナリの生キャプチャは残していない。
  **このリポジトリは公開である。** アーカイブにはローカルの絶対パスが大量に含まれ、Python 環境のソースも混ざって
  いるので、このまま GitHub に上げない。退避するなら非公開のストレージに置く。展開は
  `zstd -dc --long=27 program-1-text-evidence.tar.zst | tar -xf -`、チェックサムは `archive-local/SHA256SUMS`。

## ブランチ

- `p2`：Program 2 の本線。
- `research`、`main`、`research-*`、タグ `archive/program-1`：Program 1 の記録。書き換えない、消さない、
  force push しない。Program 1 のファイルは作業ツリーに無い。`git show archive/program-1:<path>` で読む。
