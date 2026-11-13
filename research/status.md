# 現状 — 2026-11-13

**S0（土台）を終えた（ネイティブのみ）。GI はまだない。次の作業はスパイク S1。**

## いまの状態

- 目的と必須要件：[憲章](../docs/charter.md)。
- 方向：Radiance Cascades 系の無ノイズ放射輝度場（可視サーフェス近傍のワールド格子プローブ）、
  区間ごとに切り替えるトレーサ、ボクセル化した StrataBrick、両端のスタイル演算子。すべて
  **未検証の仮説**（[architecture](../docs/architecture.md)。S0 で先行研究の本文を読んで改訂した）。
- 評価：同じコストでの品質。予算と指標の数値は仮置き（[evaluation](../docs/evaluation.md)）。
- 計画：S0 土台 ✓ → S1 疎プローブのカスケード → S2 ボクセル StrataBrick →
  S3 スタイル演算子 → チェックポイント C1（[roadmap](roadmap.md)）。
- 決定：[Program 2 開始](decisions/2026-11-13-program-2-start.md)、
  [ツールチェーンとネイティブ先行](decisions/2026-11-13-s0-toolchain-native-first.md)。

## S0 の結果（[記録](spikes/s0-foundation.md)）

- ツールチェーン：TypeScript ＋ WebGPU（WGSL）。ネイティブは Dawn（npm の `webgpu`、Vulkan）。
- シーン：Khronos glTF Sponza（26.2 万三角形）。参照レンダラは S1 の品質計測の前に決める。
- Sponza G-buffer 1080p：GPU 時間の中央値 0.63 ms（探索値、ネイティブ、3 回）。画像は目視で確認。
- ブラウザでの計測は後段に回した。この作業機のブラウザは WebGPU が SwiftShader に落ちる。
- 先行研究で最も近いのは Split RC（HWRT ありの dGPU で Sponza 8.6 ms）。GI 4 ms の予算は厳しい。

## 次にやること（S1）

1. 可視画素から疎なワールド格子プローブを作り、深度バッファ区間だけで拡散 GI を出す。
2. スクリーン配置プローブをベースラインとして並べ、静止時とカメラ移動時のちらつきを測る。
3. 区間の埋め方（方向ごとの決定的トレースとレイ分割）を比べる。
4. 品質を測る前に参照レンダラを決める。

## リポジトリと作業機

- 本線は `p2`。Program 1 の全記録はタグ `archive/program-1`（ブランチ `research` の先端）。
- `p2` の作業ツリーには Program 1 のソース、シェーダ、スクリプト、実験記録を置いていない。
  引き継いだ参照コードは [legacy/](../legacy/)、知見は
  [docs/program-1/findings.md](../docs/program-1/findings.md)。
- 作業機の整理（2026-11-13）：
  - `build/`（1.4 GB）：削除した。
  - `out/`（411 GB、379,014 ファイル。Program 1 の生データと Python 仮想環境）：削除した。
    削除前にテキスト記録 35,854 ファイル（JSON、JSONL、標準出力・エラー、ログ、小さな
    証跡 tar、非公開ビルドのソース差分）を 95 MB に圧縮し、全ファイルの目録（サイズ、
    日付、パス）とともに `archive-local/` に置いた。バイナリの生キャプチャ（約 410 GB）は
    残していない。
  - `archive-local/`（96 MB）：git 管理外で、**この作業機にしかない**。外部への
    退避はしていない（下の「archive-local の扱い」）。
  - `assets/`（288 MB、Sponza）：保持。S0 で Khronos 版 Sponza（51 MB）を追加した。
    旧 Vulkan-Samples-Assets 版は使っていないが消していない。
  - 旧クローン `../gi-lab-old-private`（別リポジトリ phos-gi-lab、3.6 GB）：ユーザー判断で
    ディレクトリごと削除した。リモートに無かったローカルブランチ 1 本とスタッシュ 4 件も
    一緒に失われている。
- Python 環境は未構築。S0 では不要だった（コードは TypeScript、依存は `package-lock.json`）。

### archive-local の扱い

このリポジトリは **public** である。アーカイブにはローカルの絶対パスが大量に含まれ、
Python 仮想環境のソースも混ざっているので、**このまま GitHub に上げない**。退避するなら
非公開のストレージに置く。展開は
`zstd -dc --long=27 program-1-text-evidence.tar.zst | tar -xf -`、チェックサムは
`archive-local/SHA256SUMS`。
