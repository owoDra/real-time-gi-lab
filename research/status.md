# 現状 — 2026-11-13

**S1（疎プローブのカスケード）を終えた（ネイティブのみ）。次の作業はスパイク S2（ボクセル StrataBrick）。**

## いまの状態

- 目的と必須要件：[憲章](../docs/charter.md)。
- 方向：Radiance Cascades 系の無ノイズ放射輝度場（可視サーフェス近傍のワールド格子プローブ）、
  区間ごとに切り替えるトレーサ、ボクセル化した StrataBrick、両端のスタイル演算子。すべて
  **未検証の仮説**（[architecture](../docs/architecture.md)。S0 で先行研究の本文を読んで改訂した）。
- 評価：同じコストでの品質。予算と指標の数値は仮置き（[evaluation](../docs/evaluation.md)）。
- 計画：S0 土台 ✓ → S1 疎プローブのカスケード ✓ → S2 ボクセル StrataBrick →
  S3 スタイル演算子 → チェックポイント C1（[roadmap](roadmap.md)）。
- 決定：[Program 2 開始](decisions/2026-11-13-program-2-start.md)、
  [ツールチェーンとネイティブ先行](decisions/2026-11-13-s0-toolchain-native-first.md)、
  [参照レンダラ（Mitsuba 3）](decisions/2026-11-13-reference-renderer.md)。

## S0 の結果（[記録](spikes/s0-foundation.md)）

- ツールチェーン：TypeScript ＋ WebGPU（WGSL）。ネイティブは Dawn（npm の `webgpu`、Vulkan）。
- シーン：Khronos glTF Sponza（26.2 万三角形）。G-buffer 1080p は GPU 時間の中央値 0.63 ms。
- ブラウザでの計測は後段に回した。この作業機のブラウザは WebGPU が SwiftShader に落ちる。

## S1 の結果（[記録](spikes/s1-sparse-cascades.md)、探索値、深度バッファだけのトレース）

- ワールド格子プローブ（P=32）で拡散 GI 2.9〜4.1 ms、使用 47 MiB。P=16 は 6.0〜9.5 ms。
  打ち切り基準には当たらない（境界）。
- ちらつき（カメラ移動、1/4 段の帯）：ワールド格子 13% に対しスクリーン配置 20%。配置だけを測ると
  ワールド格子は測定の床（4.0%）と同程度。静止時は決定的トレースなら 0、レイ分割は 9%。
- 太陽だけ（空なし）だと配置によらず 33〜47% がちらつく。原因は深度バッファのトレースそのもので、
  S2 で区間トレーサを替えて確かめる。
- 表面上の疎なプローブでは、上のカスケードほど光線数が増える（コストの構造的な問題）。
- 参照レンダラは Mitsuba 3（CPU の LLVM 版）。作業機で動くことは確認した。シーン変換は未作成。

## 次にやること（S2）

1. 多層ボクセルブリックを作り、区間をボクセルでトレースする。最初に、太陽だけの条件の移動時ちらつきが
   下がるかを S1 の測定器で測る。近距離の区間も深度バッファから替えるべきかを決める。
2. 上のカスケードの光線の増加を抑える案を合わせて試す。
3. 品質を初めて測るときに、Mitsuba 用のシーン変換を書く。

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
  - `assets/`：S0 で Khronos 版 Sponza に替え、旧 Vulkan-Samples-Assets 版（288 MB）は
    ユーザー判断で削除した。いまは 94 MB。
  - 旧クローン `../gi-lab-old-private`（別リポジトリ phos-gi-lab、3.6 GB）：ユーザー判断で
    ディレクトリごと削除した。リモートに無かったローカルブランチ 1 本とスタッシュ 4 件も
    一緒に失われている。
- Python 環境：参照レンダラ用の仮想環境を `build/refenv`（git 管理外）に作った（Mitsuba 3.6.4）。
  手順は[決定](decisions/2026-11-13-reference-renderer.md)。

### archive-local の扱い

このリポジトリは **public** である。アーカイブにはローカルの絶対パスが大量に含まれ、
Python 仮想環境のソースも混ざっているので、**このまま GitHub に上げない**。退避するなら
非公開のストレージに置く。展開は
`zstd -dc --long=27 program-1-text-evidence.tar.zst | tar -xf -`、チェックサムは
`archive-local/SHA256SUMS`。
