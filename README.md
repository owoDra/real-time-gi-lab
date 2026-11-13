# real-time-gi-lab

完全動的・大規模・高密度のワールドで動き、写実と非写実を同じ空間で混在でき、
WebGPU で動くリアルタイム・グローバルイルミネーションの研究。

> **AI 主導、人間監督の研究です。** 設計、実装、実験、記録の大半を AI
> （Program 1 は ChatGPT と OpenAI Codex CLI、後半と Program 2 は Claude Code）が行い、
> 人間が目的と制約を定め、採否を決めています。AI がすべての主張を独立に検証した
> わけではありません。[開示](docs/ai-research-workflow.md)

## 現在地

**Program 2 を 2026-11-13 に開始。土台（S0）として Sponza の G-buffer と GPU
タイムスタンプの計測までできています。GI はまだありません。**
最初に読むのは [research/status.md](research/status.md)。

| 文書 | 内容 |
|---|---|
| [docs/charter.md](docs/charter.md) | 目的、必須要件、止め方 |
| [docs/architecture.md](docs/architecture.md) | 検証中の仮説（Strata Cascades） |
| [docs/evaluation.md](docs/evaluation.md) | 予算、指標、比較相手 |
| [research/roadmap.md](research/roadmap.md) | スパイク S0〜S3 とチェックポイント |
| [AGENTS.md](AGENTS.md) | 作業ルール |

## Program 1

2026-09-28 から 2026-11-13 までの研究（キャッシュ局所性、Split Radiance Cascades
レンダラ、GI 競争力比較）は、目標未達のまま終了しました。全記録はタグ
`archive/program-1` とブランチ `research` にあります。持ち越す知見は
[docs/program-1/findings.md](docs/program-1/findings.md)、引き継いだ参照コードは
[legacy/](legacy/) です。

```bash
git show archive/program-1:research/status.md
```

## 使い方

```bash
mise install
npm ci            # TypeScript、esbuild、Dawn（npm の webgpu）
mise run assets   # Khronos glTF Sponza を assets/ に取得（git 管理外）
mise run check    # 文書のリンクと legacy 目録を検査
mise run typecheck
mise run s0:native   # Sponza G-buffer 1080p、ネイティブ Dawn（Vulkan）で GPU 時間を計測
mise run s0:serve    # 同じ計測をブラウザで（http://127.0.0.1:8765/）。当面は使わない
```

レンダラは TypeScript と WebGPU（WGSL）で書き、ネイティブでは Dawn を Node から、
ブラウザでは Chrome 系の WebGPU を使います（[S0 の記録](research/spikes/s0-foundation.md)）。

## ライセンス

本プロジェクトのソースと文書は [Apache License 2.0](LICENSE)。取得した依存物と
テストシーン（Khronos Sponza を含む）は、それぞれ元のライセンスに従います。
リポジトリを公開する前に、履歴全体の秘密情報スキャンが必要です
（[公開前チェック](docs/publication-readiness.md)）。
