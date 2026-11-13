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
  - `build/`（1.4 GB）：削除。
  - `out/`（411 GB、Program 1 の生データと Python 仮想環境）：処分前（次のコミットで確定）。
  - `assets/`（288 MB、Sponza）：保持。
- Python 環境は未構築。必要な依存は S0 で決めて `mise.toml` に書く。
- この整理でビルド、テスト、GPU 実行は行っていない。
