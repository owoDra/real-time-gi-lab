# 確認実験（Phase 34）

[10-evaluation.md](10-evaluation.md) の原則 2 の確認実験。ここまでの数値（[30-measurements.md](30-measurements.md)）はすべて探索値で、この文書は
**主張、場面、設定、回数と順序、指標、判定の規則、測り直してよい場合を、計測の前に書いてコミットしたもの**である。計測の後に
この文書の「条件」の節（主張の表と判定の規則を含む）は変えない。結果は最後の「結果」の節に足す。

- 実行：[`scripts/p34_confirm.sh`](../../scripts/p34_confirm.sh)（ブロック `prereq`、`refs`、`quality`、`timing`、`compare`）。
- 判定：[`scripts/p34_judge.py`](../../scripts/p34_judge.py)。下の規則をそのままコードにしたもので、主張ごとに成立 / 不成立を出す。
- 出力：`box/out/p34/run/`（git 管理外、要約を作ったら消す）。要約は `docs/reference/measurements/finish/phase34-confirmation.json`。

## 条件

### 機械と時間の主張の扱い

- 開発機 1 台（AMD Radeon 8060S、RADV）。ネイティブは Dawn / Vulkan、ブラウザは作業機の Brave 149（Phase 30 の起動の条件）。
- **機械は空かない**（2026-11-16、AskUserQuestion でユーザーが「空けられない」と答えた。godot、Brave、ほかのセッションが動き、負荷平均 3.5 前後）。
  GI の時間の絶対値の主張（4.0 ms 以下）は**混んだ機械での値で判定**し、「空いた機械では未実行」と結果に書く。各実行の最初と最後に負荷平均を記録する。
- 予算は GI 4 ms、128 MB。128 MB は 128 × 10⁶ バイト（122.07 MiB）として判定する（MiB との取り違えで甘くならない側）。
- 解像度 1920×1080、ウォームアップ 60 ＋ 240 フレーム、空なし（リークの部屋だけ空あり、60 フレーム）。GPU のクロックは固定しない。
- 時間は GI の GPU タイムスタンプの合計の、実行内の中央値（静止カメラ `static.timing.giTotal.median`、移動カメラ `moving.timing.giTotal.median`）。

### 設定

| 略号 | 設定名 | 役割 |
|---|---|---|
| RC | `world-48-voxel-rc2-vrel` | 既定の構成 |
| RC-obj | `world-48-voxel-rc2-vrel-obj` | 動く物体が跳ね返りを受けて遮る形（既定ではない） |
| DL | `ddgi-100-128-u8-g1-noadapt` | DDGI 系の線形（同じボクセル、同じ 4 ms で選んだ設定） |
| DH | `ddgi-100-128-u8-h0.5-g1-noadapt` | DDGI 系、応答を速めた設定（探索で 33 フレーム） |
| DF1 | `ddgi-150-64-u1-h0.8-g1-noadapt` | DDGI 系、応答 14 フレーム以下の候補（探索で 14） |
| DF2 | `ddgi-125-64-u2-h0.5-g1-noadapt` | DDGI 系、応答 14 フレーム以下の候補（探索で 9） |
| GL | `gl2-8-8` | WebGL2 ティア（ネイティブは WGSL 版、ブラウザは GLSL 版） |

DDGI 系は RC と同じトレーサ、同じ多重バウンス、同じ太陽の可視性の面の平均を使う（一方にだけ入れた改良は無い）。

### 探索で使っていない場面（-cam2）

`-cam2` は場面の静止カメラ（と移動カメラの始まり）を、探索で一度も使っていない視点に替える（`src/core/scenes.ts` の `withHeldOutCamera`。
物体、太陽、建物は元の場面のまま）。Sponza は回廊の反対の端から高さ 2.1 m で元のカメラの方を見る。`town` は家の前の右から約 45° ずれた高い視点。
健全性（計測の前に済ませた）：`sponza-cam2`、`town-cam2` の最終画像に場面が写る。`sponza-dynobj-cam2`、`sponza-dynobj-n64-deform-cam2-bwave`、
`town-dynobj-cam2-bwave` で動く物体が見え、最初と最後のフレームで画像が変わる（建物が変わる 2 場面は実行器の確かめ（0.5% 以上）を通る）。
`sponza-cam2` と `town-cam2` の参照（Mitsuba、多重バウンス、960×540、256 spp × 2 本、シード 0 と 1）はこのフェーズで描く。

### 順序

1. `prereq`：既定の画像の sha256（`sponza` 9589339d…、`sponza-dynobj --pose-frame 0` 44c7e830…、`--no-sky --static-only --dump-irr --frames 60`）。違えば止める。
2. `refs`（CPU）と `quality`（GPU、決定的な品質の値）。`quality` の実行の時間の値は使わない。参照を描いている間に GPU の時間を測らない。
3. `timing`：参照を描いていないことを各実行の前に確かめてから（`reference_irradiance.py` のプロセスがあれば止まる）、T1〜T7 をこの順に。
4. `compare`（CPU）：参照との比べ、あふれのブロック、ネイティブとブラウザの画像の一致。
5. 判定（`p34_judge.py`）。数値の前に、各場面の最終画像と間接光を見る。

### 時間の計測（T1〜T7、1 実行 = 独立のプロセス 1 つ）

| ブロック | 場面 | 内容と順序 |
|---|---|---|
| T1 中立な対照 | `sponza-dynobj-n64-deform-bwave` | RC を 8 回続けて。隣り合う 4 組（1・2、3・4、…）の静止の GI の比 A/A′ の、1 からのずれの最大を**最小検出差（MDE）**とする |
| T2 | `sponza-dynobj-n64-deform-cam2-bwave` | RC と DL を AB、BA、AB、BA（各 4 回） |
| T3 広さ | Sponza（`sponza-dynobj-n64-deform-bwave`）、`sponza-wide10-…`、`sponza-wide100-…` | ラテン方格の 6 周（S W10 W100、W10 W100 S、W100 S W10、S W100 W10、W10 S W100、W100 W10 S）。RC の 18 回の後に DL の 18 回。静止カメラだけ（`--static-only`） |
| T4 密度 | `sponza-bwave`、`sponza-dense10-bwave` | AB、BA を 3 回（6 周）。RC の後に DL。静止カメラだけ |
| T5 速い移動 | `sponza-wide100-fly-bwave` | RC と DL を AB、BA、AB（各 3 回）。移動カメラの GI の中央値、99% 値、最大 |
| T6 WebGL2 | `sponza-dynobj-n64-deform-bwave` | GL と RC を AB、BA、AB（各 3 回）。静止カメラだけ |
| T7 ブラウザ | `sponza-dynobj-n64-deform-bwave`、`sponza` | RC をネイティブ → ブラウザで 3 周。その後、ブラウザの WebGL2 で `sponza` を 3 回。ブラウザは毎回閉じ、プロセスが残らないことを確かめる |

比の主張は、同じ周の 2 つの実行の比の中央値で判定する。中央値と閾値の差が MDE 以内なら、判定はそのままにして「MDE 内（揺れの範囲）」と書く。

### 品質の計測（決定的、1 回ずつ）

| 名前 | 場面と設定 | 取る値 |
|---|---|---|
| 静止の場面 | `sponza`（RC、DL、DH、DF1、DF2、GL）、`sponza-cam2`（RC、DL、DH、DF1、DF2）、`town`、`town-cam2`（RC） | 静止時のちらつき（細帯 `static.flicker.giFinePct`）、放射照度のダンプ |
| DDGI の参照用 | `sponza`、`sponza-cam2`、`town`、`town-cam2`（DL、ウォームアップ 2400） | 放射照度のダンプ（収束した DDGI） |
| 応答 | `sponza-dyn-switch200`、`--response 200,520`（RC、DH、DF1、DF2） | 90% / 50% までのフレーム数（終わりの値は姿勢を止めて収束させた値） |
| 物体が動く | `sponza-dynobj`、`sponza-dynobj-cam2`（RC、DL、DH、DF1、DF2） | 法線マップを外した超過変動 K = 16（`staticGeo.excess.k16.excessPerFrame`） |
| 建物が動く | `town-dynobj-bwave`、`sponza-dynobj-n64-deform-bwave`、`…-bcut`、`…-cam2-bwave`、`town-dynobj-cam2-bwave`（RC、DL） | 同上 |
| リーク | `leak-0.02`、`leak-0.1`、`leak-0.05`（RC、DL、GL、空あり、60 フレーム）。`leak-0.05` は探索で使っていない厚み | 外の床の太陽に対する中の平均照度（`leak.meanFractionOfSun`） |
| トゥーン | `sponza-dyn`（RC、GL）、`sponza-dyn-cam2`（RC） | ランプの帯の切り替わりと対照（`toonRampChangePct`、`controlRampChangePct`） |
| 物体の画素 | `sponza-dynobj-n64-deform --pose-frame 0 / 100`（RC、RC-obj。DL はウォームアップ 2400） | 参照（多重バウンス 128 spp、各 1 本）に対する物体の画素の偏り（画素、8×8） |
| 物体の近くの床 | `sponza-dynobj --pose-frame 0`（RC、RC-obj） | 4 つの矩形（12 節）の参照（多重バウンス 128 spp × 2）に対する比 |
| あふれ | `sponza-wide100-fly-bwave`（RC、`--dump-moving 12`、プール 3072 と 12288 / 1572864） | 8×8 ブロックの比が 0.8〜1.25 倍に入る割合 |

参照との誤差は多重バウンスの参照の 8×8 ブロックの `meanAbsRel`（写実の画素）。`sponza`、`town` は既存の 256 spp × 2 本。

### 主張と判定の規則

| ID | 要件 | 主張 | 成立の規則 |
|---|---|---|---|
| C1 | R1 | 建物が波打ち物体 64 個が動く場面で、RC の GI が 4.0 ms 以下、確保 128 MB 以下 | T1 の 8 回とも静止・移動の中央値 ≤ 4.0 ms、確保 ≤ 122.07 MiB |
| C2 | R1 | 同じ場面の探索で使っていない視点でも同じ | T2 の RC 4 回とも静止・移動 ≤ 4.0 ms、確保 ≤ 122.07 MiB |
| C3 | R4 | 何も動かない場面で静止時のちらつき 0 | RC の細帯が `sponza`、`sponza-cam2`、`town-cam2` で 0 |
| C4 | R1 | 光源の切り替えへの応答が数フレーム以内 | RC の 90% までのフレーム数 ≤ 4 |
| C5 | R1・R4（Phase 26 の優位） | 応答 14 フレーム以下の DDGI 系のどの設定よりも、物体が動く跳びと静止時のちらつきが小さい | 比べる組 = DH、DF1、DF2 のうち**この計測で** 90% まで ≤ 14 フレームのもの（空なら不成立）。その全部に対して、RC の跳びが `sponza-dynobj`、`-cam2` の両方で小さく、静止時のちらつきが `sponza`、`-cam2` の両方で小さい |
| C6 | R1・R4 | 建物が動く場面の跳びが Phase 29 の到達値を再現する | RC の跳び ≤ 到達値の 1.1 倍（到達値 `town-dynobj-bwave` 0.19359、`sponza-dynobj-n64-deform-bwave` 0.09037、`…-bcut` 0.0171） |
| C7 | R1・R4（限界） | 建物が動く場面では RC が DDGI 線形より跳ぶ | 建物が動く 5 場面すべてで RC の跳び > DL の跳び |
| C8 | 高品質（壁を抜けない） | リークが DDGI 線形より小さい | 3 つの部屋すべてで RC < DL |
| C9 | 高品質（誤差） | `town` 系では RC が DDGI 線形より参照に近い | `town`、`town-cam2` の両方で RC の誤差 ≤ DL の誤差 |
| C10 | 高品質（誤差、限界） | Sponza 系では DDGI 線形が RC より参照に近い | `sponza`、`sponza-cam2` の両方で DL の誤差 < RC の誤差 |
| C11 | R5 | 動く物体の画素の偏りが Phase 31 の目安 O1 に入る | 既定の RC で、姿勢 0 \|偏り\| ≤ 10.9%、姿勢 100 ≤ 7.45%（画素と 8×8 の両方）。RC-obj が満たすかは併記する |
| C12 | R5 | 物体の近くの床が参照に近い（Phase 31 の O2） | 既定の RC で 4 つの矩形の比がすべて 0.7〜1.4 倍。RC-obj が満たすかは併記する |
| C13 | R4・R5 | トゥーンのランプの帯の切り替わりが対照の 2 倍以下 | RC の `toonRampChangePct` ≤ 2 × `controlRampChangePct`（`sponza-dyn`、`sponza-dyn-cam2` の両方） |
| C14 | R2 | 広さ 100 倍の GI が 10 倍の 1.1 倍以内、確保が同じ | T3 の RC の W100 / W10 の比の中央値 ≤ 1.10、確保 W100 ≤ 1.1 × W10、≤ 122.07 MiB |
| C15 | R2 | 広さ 100 倍でも 4.0 ms 以下で、Sponza の 1.1 倍以内 | T3 の RC の W100 が 6 回とも ≤ 4.0 ms、W100 / S の比の中央値 ≤ 1.10 |
| C16 | R3 | 三角形 10 倍の GI が 1.25 倍以内 | T4 の RC の dense10 / sponza-bwave の比の中央値 ≤ 1.25 |
| C17 | R2 | 速い移動でフレーム時間が跳ねない | T5 の RC 3 回とも移動の GI の最大 ≤ 4.0 ms、99% 値 ÷ 中央値 ≤ 1.2 |
| C18 | R2 | 入れ物が足りなくても間接光が黙って欠けない | プール 3072 の実行の 8×8 ブロックの 95% 以上が、12288 の実行の 0.8〜1.25 倍（全フレーム） |
| C19a | R6 | ブラウザで GI 4.0 ms 以下 | T7 のブラウザ 3 回とも静止・移動 ≤ 4.0 ms |
| C19b | R6 | ブラウザの画像がネイティブと一致する | T7 の 1 周目の間接光の 8 ビットの平均の差 ≤ 0.5 段 |
| C19c | R6 | ブラウザとネイティブの時間に差が見えない | 静止の中央値の比（ブラウザ 3 回 / ネイティブ 3 回）の 1 からのずれ ≤ MDE |
| C20a | 望ましい（WebGL2） | ブラウザの WebGL2 で `sponza` の GI 4.0 ms 以下 | T7 の WebGL2 3 回とも ≤ 4.0 ms |
| C20b | 望ましい（WebGL2） | ブラウザの WebGL2 の画像がネイティブの WGSL 版と一致する | 間接光の 8 ビットの平均の差 ≤ 0.5 段（ネイティブは品質の計測の `sponza` の GL） |
| C20c | 望ましい（WebGL2） | 建物が波打ち物体 64 個の場面で WebGL2 版の GI 4.0 ms 以下 | T6 の GL 3 回とも ≤ 4.0 ms |
| C20d | 望ましい（WebGL2） | WebGL2 版の静止時のちらつき 0 | `sponza` の GL の細帯 0 |
| C20e | 望ましい（WebGL2） | WebGL2 版のトゥーンの帯が RC の 2 倍以下 | `sponza-dyn` の GL の `toonRampChangePct` ≤ 2 × 同じ計測の RC |

判定はしないが並べて書く値：参照との誤差と偏り（RC、DL、GL）、物体が動く跳びと静止時のちらつきの DDGI 系の並び、建物が動く跳びの RC / DL の比、
リーク（GL を含む）、物体の画素の偏りと床の比（RC、RC-obj、DL）、T2〜T6 の DDGI 線形の時間、移動カメラの鎖の超過変動。

この確認に入れなかったもの（理由）：動いている途中の遅れ（姿勢ごとに参照が要り、今の参照の組では足りない）、空いた機械の時間（機械が空かない）、
`obj` の時間（既定ではない）、ほかの GPU とブラウザ（開発機 1 台）。

### 測り直してよい場合

手続きの失敗だけ：ビルドの失敗、設定や引数の誤り、スクリプトの不具合、プロセスの異常終了、ブラウザが実 GPU に届かない（ソフトウェア描画）か閉じない、
参照の描画の異常終了。測り直すのは失敗した実行（とその比べの組）だけで、理由をこの文書の結果の節に書く。機械の負荷、値が目安に届かないことは理由にしない。
判定のスクリプトの不具合（規則の写し間違い）は、規則をこの文書のとおりに直して判定し直す（計測はしない）。

## 結果

（計測の後に足す。）
