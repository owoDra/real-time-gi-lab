# Phase 01（auto）：跳びの指標と、既存のスイッチでできる切り分け

## 開始プロンプト

```
/goal AGENTS.md と docs/plan/README.md と docs/plan/dynamic-stability/README.md と docs/plan/dynamic-stability/phase-01-auto-jump-metric-and-switches.md を読み、docs/spec/40-dynamic-stability.md の切り分けのうち、既存のスイッチだけでできるもの（E6、E5、E1）を測る。最初に docs/spec/30-measurements.md 7 節の値（world-48-voxel-rc2-vrel、局所更新、太陽だけ、静止カメラのちらつき：両方 19.6% / 太陽だけ 7.7% / 物体だけ 17.9%）を再現し、±2 ポイントに入らなければ止めて AskUserQuestion で報告する。次に、超過変動の指標と、動的物体の画素とその遮蔽・露出の画素の除外を src/core/post.ts に足す（既存の帯境界ちらつき率は変えずに残す）。それから E6、E5、E1 を測る。対策（P1、P2、P3）は実装しない。方向、スコープ、予算に関わる判断は AskUserQuestion で尋ねる。
完了条件（すべて会話内で示すこと）: (1) 再現した 3 つの値と元の値 (2) 足した指標の定義、静的なシーンで 0 になることの確認、RC と DDGI（線形、RTXGI 既定）の超過変動の値 (3) E6、E5、E1 の結果の表と、各候補（A〜F）が支持・棄却・未定のどれになったか (4) 見た画像の一覧（ちらつきの分布図を含む） (5) mise run typecheck と mise run check の出力の末尾 (6) 結果を docs/spec/40-dynamic-stability.md の「状態」の列と docs/spec/30-measurements.md に書き、数値の要約を docs/reference/measurements/dynamic-stability/ に置き、次のフェーズのファイルの「決定済みの方針」に結果を書き、このファイルを消し、列の README の表を更新し、Co- で始まるトレーラーを付けずにコミットし、git status --short が空（.claude/ を除く）。push はしない。
制約: 既定の構成の画像を変えない。予算（GI 4 ms、128 MB）と既存の指標の定義を変えない。計測はネイティブだけ、GPU ジョブは同時に 1 本、参照（Mitsuba）を描きながら GPU 時間を測らない。pkill -f を使わない。実行の出力は box/out/、要約を作ったら生の出力を消す。
```

## 目的

動的な跳びを「本物の変化」と分けて測れるようにし、コードを変えずに外せる候補を先に外す。

## 前提

なし。

## 決定済みの方針

- 見立てと候補 A〜F、実験 E1〜E6 の定義は `docs/spec/40-dynamic-stability.md`。見立ては未検証で、このフェーズの結果で
  書き換えてよい（書き換えるのは測った事実に基づく所だけ）。
- 実行の形（M1 の計測と同じ）：

  ```bash
  mise run build:rc
  bash scripts/run_with_vulkan.sh node build/native/rc.mjs --scene sponza-dyn --configs world-48-voxel-rc2-vrel \
    --no-sky --vox '{"anchor":"scene","local":true}' --out box/out/ds01/dyn
  ```

  シーンは `sponza-dyn`、`sponza-dyn-sunonly`、`sponza-dyn-objectsonly`、`sponza-dynobj`。設定名とトークンは
  `src/native/rc.ts` の先頭。比較の DDGI は `ddgi-75-128-u4-g1-noadapt`（線形）と `ddgi-100-128-u2`（RTXGI 既定）。
- 超過変動：窓 K フレームで Σ\|ΔE\| − \|E_end − E_start\|（間接放射照度の輝度）。K は 16 を既定にし、8 と 32 でも
  傾向が同じことを確かめる。正規化（平均の輝度で割るか、log2 で取るか）はこのフェーズで決めて spec 10 に書く。
- 動的物体の画素は G-buffer の材質の印（albedo の a）か、動的三角形の範囲から決める。遮蔽・露出の画素は、前フレームと
  今フレームのどちらかで動的物体だった画素とする。
- 写実材質で太陽だけ / 物体だけを動かすシーン名（`sponza-dynobj-sunonly` など）は、実行器に無ければ足す
  （`dynamicSponza` は引数で対応している）。
- 三角形 BVH は CPU で 1 回だけ構築している。動く頂点に追従するかは未確認。追従しなければ、毎フレームの再構築を
  計測の外で足す（GI の時間は見ない。ちらつきだけ見る）。フレーム数を減らしてよい（減らしたら値に添える）。

## 確かめる決定

| 決定 | 確かめ方 |
|---|---|
| 予算は GI 4 ms、128 MB。変えない | 既定の構成の GI 時間と使用量を再現の実行で読み、30 の 7 節と比べる |
| 既定の構成の画像を変えない | 指標を足す前後で、既定の構成の静的な放射照度（`--dump-irr`）がビット単位で同じ |
| 以前の数値を先に再現する | 19.6 / 7.7 / 17.9% が ±2 ポイント |
| 数値の前に画像を見る | 各シーンの最後のフレームとちらつきの分布図を見て、物体と太陽が動いていること、跳びが面で出ていることを確かめる |
| DDGI を本物の変化の上限に使わない | 候補の判定は超過変動と、マスクした画素での値で行う |
| 切り分けが終わるまで対策を実装しない | 差分に P1・P2・P3 の実装が無い |

## やること

1. 再現：`sponza-dyn`、`-sunonly`、`-objectsonly` を既定の構成で回す。
2. 指標：超過変動と画素の除外を `src/core/post.ts` に足し、静的な `sponza` で RC が 0 になること、DDGI の値、
   既存の帯境界ちらつき率が変わらないことを確かめる。
3. E6：動的な実行中のあふれと挿入失敗の計数を読む。物体を除いた G-buffer でプローブを登録した場合と、静的な面の
   画素のちらつきを比べる（登録の変更は診断用で、測ったら消す）。
4. E5：写実材質（`sponza-dynobj` と、その太陽だけ / 物体だけ）と `noemit` で分解を取り、トゥーンの放出の量子化の
   寄与を出す。
5. E1：三角形トレーサ（`world-48-tri-rc2-vrel`）で `sponza-dyn-objectsonly` を回し、ボクセルの値と比べる。
6. 結果を spec へ還元し、02 のファイルを結果に合わせて書き直す（外れた候補の実験を消す）。

## 完了条件

- 7 節の値を再現した（しなければ止めて報告した）。
- 超過変動の定義が spec 10 に書かれ、「未実装」の印が消えている。
- E6、E5、E1 の結果が spec 40 の表に入り、候補ごとに支持・棄却・未定が付いている。
