# Phase 12（auto）：`vrel` の判定を画像を変えずに軽くする

## /goal プロンプト

```
/goal AGENTS.md と docs/plan/README.md と docs/plan/dynamic-stability/README.md と docs/plan/dynamic-stability/phase-12-auto-vrel-cost.md を読み、Phase 12（auto）を最後まで進めてください。既定の構成（world-48-voxel-rc2-vrel、固定窓、P2）のプローブの押し出しと遮り判定（vrel）の費用を、画像をビット単位で変えずに減らします。最初に既定の段ごとの GPU 時間（spec/30-measurements.md の 16 節）と sponza-dynobj の超過変動 0.01192 を再現し、目安と確かめ方をコミットしてから実装し、前と後を交互に 3 回測ってください（計測だけ、GPU ジョブは同時に 1 本、GPU の共有の有無を書く）。完了の根拠として、再現の数値、ビット一致の確認の出力、交互 3 回の GI と段ごとの時間、目安への判定、控えのどれに当たったか、typecheck と check の出力、コミットのハッシュを会話に示してください。目標か予算に関わる判断は AskUserQuestion で尋ね、技術の判断は自分で決めて最終報告に書いてください。
```

## 目的

P1 を 4 ms に入れる余りを作る。Phase 11 で、`vrel` の判定に 1.36 ms（押し出しと親の遮り判定 0.62 ms、画素の遮り判定 0.74 ms）
かかっていると測った（P1 の上乗せは +0.32〜0.39 ms）。このフェーズでは画像を変えずにこれを軽くする。P1 はまだ既定に入れない。

## 前提

- 測った値：[spec/30-measurements.md](../../spec/30-measurements.md) の 16 節、要約
  [phase11-review-p1-cost.json](../../reference/measurements/dynamic-stability/phase11-review-p1-cost.json)。決定は
  [spec/40-dynamic-stability.md](../../spec/40-dynamic-stability.md) の「方向の確認（Phase 11）」。
- コード：`src/core/rc.ts` の `relocateVox`（`compact` から呼ぶ）、`linkParents`、`segOccluded`、`probeOccluded`、`gatherWorld`。
- Phase 11 の報告ページ（非公開）：https://claude.ai/artifact/LtPefmG1GT1TNGKDT7yjE5

## 決定済みの方針

- 画像を変えない。`sponza` と `sponza-dynobj`（姿勢 0）の放射照度がビット単位で同じことで確かめる。浮動小数の足し算の順を
  変えない（読みだけをスレッドに並べ、和は今と同じ順で 1 つのスレッドが取る、など）。ビット一致しない最適化は入れない。
- 見立て（未検証）：build の側は、1 スレッドが 64〜260 回の占有の読みを順に待つ形で、待ち時間で重い（約 470 万回の読みに
  0.62 ms。gather は約 1 億回で 0.74 ms）。まず build の側を試し、gather の側はビット一致を保てる形があれば試す。
- 静的な形状からの結果を保存して次のフレームで使う形（キャッシュ）は、このフェーズでは使わない（カメラの切り替えで費用が
  跳ぶため）。登録を間引く形は画像が変わるので使わない。
- 予算（GI 4 ms、128 MB）と評価の指標は変えない。履歴を足さない。サンプルを増やさない。
- 費用は前と後を交互に 3 回、静止カメラと移動カメラで測り、段ごとの時間と GPU の共有の有無を書く。

## 確かめる決定と、その確かめ方

| 決定 | 確かめ方 |
|---|---|
| 画像を変えない | `sponza` と `sponza-dynobj --pose-frame 0` の `--dump-irr` が前後でビット単位で同じ。超過変動とちらつきが 5 桁まで同じ |
| 目安：既定の GI が 0.40 ms 以上下がる | `sponza-dynobj` の GI の中央値（静止カメラ）、前と後を交互に 3 回、組ごとの差の 3 つとも |
| 控え：0.2 ms 未満なら P1 は `p1` のまま、P1 なしで条件を広げる計測へ | 同上。0.2〜0.4 ms なら `p1` の GI が交互 3 回すべて（静止・移動）4 ms 以下のときだけ Phase 13 へ |
| メモリを増やさない | 使用と確保の MiB が前と同じか小さい |

目安と控えは Phase 11 で決めた。結果を見てから動かさない。

## やること

1. 再現：既定の段ごとの時間（16 節）と `sponza-dynobj` の超過変動 0.01192。
2. ビット一致の確かめ方（前の放射照度のダンプ）を用意し、目安をコミットする。
3. build の側（`relocateVox`、`linkParents` の `segOccluded`）を、読みを並べる形にする。測る。
4. gather の側で、ビット一致を保てる形があれば試す。測る。
5. `p1` も同じ組で測り、4 ms に入るかを書く（判定は控えの規則どおり）。
6. spec（20、30、40）に結果を書き、要約を `docs/reference/measurements/dynamic-stability/` に置き、次のフェーズのファイルを
   書き直し（控えに当たれば 13 を条件を広げる計測にする）、列の表を更新し、このファイルを消す。

## 完了条件

- ビット一致の確認と、交互 3 回の費用と目安への判定が会話と spec にある。
- 次のフェーズのファイルが、判定に合わせて書いてある。
- 共通の完了定義（[`../README.md`](../README.md)）を満たしている。
