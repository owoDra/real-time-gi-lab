# 仕様インデックス

`docs/spec/` は、目的、評価、いまの構成、測った結果、方向の正本である。挙動の正本はソース（`src/core/`）。
古い推測や採らなかった方針は残さない（測った負の結果だけを 1 行で残す）。

| 作業内容 | 読むファイル |
|---|---|
| 目的、必須要件（R1〜R6）、成功条件、ユーザーの決定、止め方 | [`00-overview.md`](00-overview.md) |
| 予算、指標、比較相手、シーン、健全性チェック、計測の作法、参照レンダラ | [`10-evaluation.md`](10-evaluation.md) |
| いまのレンダラの構成、仮説の状態、採らなかったもの、既知の弱点 | [`20-renderer.md`](20-renderer.md) |
| 測った結果（探索値）の表 | [`30-measurements.md`](30-measurements.md) |
| 動的なシーンでの跳び：見立て、切り分けの実験、対策の案 | [`40-dynamic-stability.md`](40-dynamic-stability.md) |
| 全体の順、未決のこと、持ち越している課題 | [`50-roadmap.md`](50-roadmap.md) |
| 確認実験（先に書いた条件、主張、判定の規則と、1 回の計測の結果） | [`60-confirmation.md`](60-confirmation.md) |
| 今のフェーズと後のフェーズの計画（正本ではない） | [`../plan/README.md`](../plan/README.md) |
| 先行研究、Program 1 の知見、数値の要約（JSON） | [`../reference/`](../reference/) |

仕様の作業では `00-overview.md` を先に読み、関係する文書だけを読む。
