# 現状 — 2026-11-13

**Program 2 を開始した。実装も計測もまだない。次の作業はスパイク S0。**

## いまの状態

- 目的と必須要件：[憲章](../docs/charter.md)。
- 方向：Radiance Cascades 系の無ノイズ放射輝度場、区間ごとに切り替えるトレーサ、
  ボクセル化した StrataBrick、両端のスタイル演算子。すべて**未検証の仮説**
  （[architecture](../docs/architecture.md)）。
- 評価：同じコストでの品質。予算と指標の数値は仮置き（[evaluation](../docs/evaluation.md)）。
- 計画：S0 土台 → S1 スクリーン空間カスケード → S2 ボクセル StrataBrick →
  S3 スタイル演算子 → チェックポイント C1（[roadmap](roadmap.md)）。
- 決定：[2026-11-13 Program 2 開始](decisions/2026-11-13-program-2-start.md)。

## 次にやること（S0）

1. ツールチェーンを決める（C++ と Dawn / Rust と wgpu / TypeScript 直書き）。
2. 参照レンダラを決める。
3. 先行研究の本文を読む（architecture 末尾のリスト）。
4. Sponza の G-buffer を 1080p で描き、GPU タイムスタンプをネイティブとブラウザで取る。

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
  - `archive-local/`（96 MB）：git 管理外で、**この作業機にしかない**。GitHub の
    ドラフトリリースへの添付は未実施（手順は下）。
  - `assets/`（288 MB、Sponza）：保持。
  - 旧クローン `../gi-lab-old-private`（別リポジトリ phos-gi-lab、3.6 GB）：ユーザー判断で
    ディレクトリごと削除した。リモートに無かったローカルブランチ 1 本とスタッシュ 4 件も
    一緒に失われている。
- Python 環境は未構築。必要な依存は S0 で決めて `mise.toml` に書く。
- この整理でビルド、テスト、GPU 実行は行っていない。

### archive-local を GitHub に退避する手順（未実施）

```bash
gh release create archive/program-1 --draft --verify-tag \
  --title "Program 1 text evidence archive (2026-11-13)" \
  --notes "Text records and file inventory of the deleted Program 1 out/ directory." \
  archive-local/program-1-text-evidence.tar.zst archive-local/program-1-out-inventory.tsv.zst
```

展開は `zstd -dc --long=27 program-1-text-evidence.tar.zst | tar -xf -`。
チェックサムは `archive-local/SHA256SUMS`。
