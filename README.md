# real-time-gi-lab

完全動的・大規模・高密度のワールドで動き、写実と非写実を同じ空間で混在でき、
WebGPU で動くリアルタイム・グローバルイルミネーションの研究。

> **AI 主導、人間監督の研究です。** 設計、実装、実験、記録の大半を AI
> （Program 1 は ChatGPT と OpenAI Codex CLI、後半と Program 2 は Claude Code）が行い、
> 人間が目的と制約を定め、できた物を確かめています（技術の採否は 2026-11-14 から AI が決めて報告）。AI がすべての主張を独立に検証した
> わけではありません。[開示](docs/ai-research-workflow.md)

## 現在地

**Program 2（2026-11-13〜2026-11-16）は、一部達成で終えました。** Radiance Cascades 系の放射輝度場（RC。ボクセルでトレースし、建物を含む全形状を毎フレーム作り直す）を作り、
同じ予算（GI 4 ms、128 MB）の DDGI 系のプローブと比べ、条件を先に書いて 1 回だけ測る確認実験を行いました（26 の主張のうち 19 成立、7 不成立）。

- **確かめられたこと**：実際のブラウザの WebGPU（コア機能だけ）で動き、画像はネイティブとビット単位で同じ。静止時のちらつき 0、光源の切り替えへの応答 4 フレーム。
  同じくらい速く応答する DDGI 系より、物体が動くときの跳びが 1/7〜1/15。リークは DDGI 系の 1/3〜1/4。広さ 100 倍でメモリが増えず、三角形 10 倍で GI 1.07 倍。機能を絞った WebGL2 版も動く。
- **届かなかったこと**：建物そのものが動くと間接光が DDGI 系の 2.4〜30 倍跳ぶ。参照（Mitsuba）との誤差は DDGI 系より小さくない。GI の時間は予算の境（混んだ機械で 3.8〜4.1 ms）で、
  建物が並ぶ広いワールドでは 4 ms を超える。既定では動く物体が参照より 17〜22% 暗い。
- **限界**：開発機 1 台（AMD Radeon 8060S）と Brave 149 だけの結果で、一般化しません。

結論は [docs/spec/00-overview.md](docs/spec/00-overview.md) の「結論」、確認実験は [docs/spec/60-confirmation.md](docs/spec/60-confirmation.md)、残っている課題は [docs/spec/50-roadmap.md](docs/spec/50-roadmap.md)。

| 文書 | 内容 |
|---|---|
| [docs/README.md](docs/README.md) | 文書の入口 |
| [docs/spec/](docs/spec/README.md) | 正本：目的と必須要件と結論、評価方法、いまの構成、測った結果、動的な跳びの見立て、ロードマップ、確認実験 |
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
  --configs world-48-voxel-rc2-vrel --no-sky
```

レンダラは TypeScript と WebGPU（WGSL、コア機能のみ）で書き、ネイティブの Dawn を Node から使って
開発・計測しました（ブラウザの実行器は `src/web/`）。コマンドの一覧は [docs/project-structure.md](docs/project-structure.md)。

## ライセンス

本プロジェクトのソースと文書は [Apache License 2.0](LICENSE)。取得した依存物と
テストシーン（Khronos Sponza を含む）は、それぞれ元のライセンスに従います。
