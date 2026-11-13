# 作業ルール — Program 2

## どこに何があるか

| 場所 | 役割 |
|---|---|
| `docs/charter.md` | 目的、必須要件、止め方。めったに変えない |
| `docs/architecture.md` | 検証中の仮説。外れたら書き換える |
| `docs/evaluation.md` | 予算、指標、比較相手、健全性チェック |
| `research/status.md` | **唯一の現状要約。1 ページ以内** |
| `research/roadmap.md` | スパイクと打ち切り基準、チェックポイント |
| `research/decisions/` | 方針の決定。1 件 1 ファイル |
| `research/spikes/` | スパイクの記録。1 件 1 ページ |
| `docs/program-1/` | Program 1 から持ち越す知見 |
| `legacy/` | Program 1 の参照コード。ビルドしない |

コードとシェーダが実際の挙動である。文書でコードの事実を置き換えない。

## ブランチ

- `p2`：Program 2 の本線。探索中はここに直接コミットしてよい。
- `p2-<名前>`：大きな試行を分けたいときの短命ブランチ。
- `research`、`main`、`research-*`、タグ `archive/program-1`：Program 1 の記録。
  **書き換えない、消さない、force push しない。**
- `main` への昇格は、チェックポイントでユーザーが決めたときだけ行う。
- プルリクエストは必須ではない。GitHub Actions や CI は追加しない。

## 探索と確認

- **探索**（スパイク）：事前登録なし。速く回す。数値は「探索値」と明記する。
  手続き上の失敗（ビルド、設定、スクリプトの不具合）は直して続ける。記録に残すのは
  判断に効くものだけ。
- **確認**（M4 など）：条件、比較相手、指標、判定規則を先に書いてコミットし、1 回だけ
  測る。結果を見てから閾値を変えない。

## 計測と品質

1. 新しいシーン、新しいシーケンス、新しい結果は、**数値の前に画像を見る**。
2. 動的シーケンスは、参照がフレーム間でノイズを超えて変化することを生成時に assert する。
3. 性能判断は GPU タイムスタンプ。コストは GPU 時間とメモリの真のピークを併記する。
4. 比較は同じシーン、同じ解像度、同じ予算で行い、試した設定の範囲を書く。
5. 負の結果は残す。短く。
6. 開発機 1 台の結果を一般化しない。
7. GPU の電源・クロックを特権操作で固定しない（Program 1 の Lane G で事故があった）。
8. GPU ジョブは同時に 1 本。

## 生成物

- ビルドは `build/`、実行出力は `out/`。どちらも git 管理外。
- 数値の要約（JSON か Markdown、1 MB 以下）はコミットする。
- 生の出力は要約を作ったら消す。`out/` を溜めない。Program 1 では 411 GB 残った。

## コミット

- コミットメッセージに `Co-` で始まるトレーラーを付けない。
- プルリクエストに生成ツールの署名を書かない。
- `CLAUDE.md` と `.claude/` はコミットしない。

## AI による研究であることの開示

Program 1 は主に ChatGPT と OpenAI Codex CLI、N008 以降は Claude Code も使い、
人間の監督のもとで進めた。Program 2 は Claude Code を使う。目的と制約を定め、
採否を決めるのは人間である。AI がすべての主張を独立に検証したわけではない。
詳細は [docs/ai-research-workflow.md](docs/ai-research-workflow.md)。

## 基本コマンド

```bash
mise install
npm ci            # 依存はバージョン固定（package-lock.json）
mise run assets   # Khronos glTF Sponza を取得
mise run check    # 文書のリンクと legacy 目録を検査
mise run typecheck
mise run s0:native   # ネイティブ（Dawn / Vulkan）で G-buffer と GPU タイムスタンプ
mise run s1:native -- --configs world-32,screen-8 [--no-sky]   # S1 の RC（時間とちらつき率）
mise run s2:native -- --scene sponza --configs world-32-voxel,world-32-tri [--no-sky] [--bvh] [--static-only]
                     # S2：区間トレーサ（depth / voxel / hybrid / tri）、可視性の比較、リーク（--scene leak-<厚み>）
                     # 設定トークン vrel / norel：プローブの押し出しをボクセルから決める / しない（既定は G-buffer）
mise run s2:native -- --scene sponza --vox-bench   # 再ボクセル化の段ごとの時間（--scene sponza-wide10 / sponza-dense9）
mise run ref:export -- --scene sponza              # Mitsuba 用のシーン変換（out/mitsuba/<scene>）
build/refenv/bin/python scripts/reference_irradiance.py out/mitsuba/sponza --spp 512 [--sky r,g,b] [--seed N]
mise run ref:compare -- --ref A.pfm,B.pfm --ours <cfg>.static.irr.f32 [--png DIR]   # 参照との誤差（s2:native --dump-irr）
```

設定名の書式と引数は `src/native/rc.ts` の先頭に書いてある。

- コードは `src/core/`（共通、WebGPU のコア機能だけ）と `src/native/`（Node から Dawn を使う実行器）。
- **当面はネイティブだけで開発・計測する**
  （[決定](research/decisions/2026-11-13-s0-toolchain-native-first.md)）。ブラウザ用の実行器は
  消した。戻すときはコミット `876e2321` の `src/web/`、`tools/serve.ts`、`web/` を参照する。

実行していない検査は「未実行」と書く。PASS と書かない。
