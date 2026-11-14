# real-time-gi-lab

完全動的・大規模・高密度のワールドで動き、写実と非写実を同じ空間で混在でき、
WebGPU で動くリアルタイム・グローバルイルミネーションの研究。

> **AI 主導、人間監督の研究です。** 設計、実装、実験、記録の大半を AI
> （Program 1 は ChatGPT と OpenAI Codex CLI、後半と Program 2 は Claude Code）が行い、
> 人間が目的と制約を定め、できた物を確かめています（技術の採否は 2026-11-14 から AI が決めて報告）。AI がすべての主張を独立に検証した
> わけではありません。[開示](docs/ai-research-workflow.md)

## 現在地

**Program 2（2026-11-13 開始）。Radiance Cascades 系の放射輝度場（履歴なし、ボクセルでトレース）と、比較相手の
DDGI 系のプローブを、完全動的な Sponza で同じ約 3.4 ms（予算 4 ms）で比べ終えました。RC は光源切替への応答
（1 フレーム）と静止したシーンの安定性で上、DDGI は静的な誤差と、物体や光源が動くシーンの安定性で上です。
RC は物体や光源が動くと場が広い範囲で跳びます。原因の切り分けを終え、RC を土台に続けて、跳びを遅れなしに抑える前置フィルタを作る段階です
（DDGI 系は比較相手として残します）。数値はすべてネイティブでの探索値です。**

次にやることは [docs/plan/README.md](docs/plan/README.md) の「列の一覧」から辿れます。

| 文書 | 内容 |
|---|---|
| [docs/README.md](docs/README.md) | 文書の入口 |
| [docs/spec/](docs/spec/README.md) | 正本：目的と必須要件、評価方法、いまの構成、測った結果、動的な跳びの見立て、ロードマップ |
| [docs/plan/](docs/plan/README.md) | 作業の計画（列とフェーズ） |
| [docs/project-structure.md](docs/project-structure.md) | ディレクトリとコマンド |
| [docs/reference/](docs/reference/) | 先行研究、Program 1 の知見、数値の要約 |
| [AGENTS.md](AGENTS.md) | 作業ルール |

## Program 1

2026-09-28 から 2026-11-13 までの研究（キャッシュ局所性、Split Radiance Cascades
レンダラ、GI 競争力比較）は、目標未達のまま終了しました。全記録はタグ
`archive/program-1` とブランチ `research` にあります。持ち越す知見は
[docs/reference/program-1/findings.md](docs/reference/program-1/findings.md)、引き継いだ参照コードは
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
mise run build:rc # 実行器をバンドル
bash scripts/run_with_vulkan.sh node build/native/rc.mjs --scene sponza-dyn \
  --configs world-48-voxel-rc2-vrel --no-sky --vox '{"anchor":"scene","local":true}'
```

レンダラは TypeScript と WebGPU（WGSL、コア機能のみ）で書き、当面はネイティブの Dawn を Node から使って
開発・計測します。コマンドの一覧は [docs/project-structure.md](docs/project-structure.md)。

## ライセンス

本プロジェクトのソースと文書は [Apache License 2.0](LICENSE)。取得した依存物と
テストシーン（Khronos Sponza を含む）は、それぞれ元のライセンスに従います。
