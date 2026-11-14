# 文書の入口

| 知りたいこと | 読む場所 |
|---|---|
| いま何をしていて、次に何をするか | [`plan/README.md`](plan/README.md) の「列の一覧」→ 列の `README.md` →「次」のフェーズのファイル |
| 目的、評価、構成、測った結果、方向 | [`spec/`](spec/README.md)（正本） |
| ディレクトリ、コマンド、作業機にしかないもの | [`project-structure.md`](project-structure.md) |
| 作業のきまり | [`../AGENTS.md`](../AGENTS.md) |
| AI による研究であることの開示 | [`ai-research-workflow.md`](ai-research-workflow.md) |
| 先行研究、Program 1 の知見、数値の要約 | [`reference/`](reference/) |

## 三つの置き場

- **`spec/`**：正本。決まったこと、いまの構成、測った事実、未検証の見立て（未検証と明記する）。実装を変えたら同じ
  変更で更新する。
- **`plan/`**：作業の計画。列ごとのディレクトリに、段階（問いと出口の条件）とフェーズのファイルを置く。
  終えたフェーズは、結果を `spec/` へ還元して消す。
- **`reference/`**：参照する資料とデータ。先行研究、Program 1 から持ち越す知見、計測の数値の要約（JSON）。
  判断や方針は置かない。
