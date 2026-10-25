# 2026-10-25 session handoff — user-requested research pause after 041

これは中断時点の引き継ぎスナップショットです。唯一の現在要約は
[research/status.md](../../../status.md)です。ユーザーが「本当にきりが良く
なったら、次のセッションで再開できるよう引き継ぎをまとめて一旦中断」と
指示したため、041の最後のH03/B8まで完了して区切りました。新規042以降は
事前登録・実装・実行していません。**研究目標は未達・一時停止であり、Lane M
完了ではありません。再開指示なしに新しい研究を開始しないでください。**

作業場所 `/var/owo/workspaces/projects/gi-lab`、研究ブランチ
`research-lane-m-gi-competitiveness`、管理 [Issue #7](https://github.com/owoDra/real-time-gi-lab/issues/7)。
041結果の確定コミットは `d671ef4b3015f2214e7c31ad1dea358897a42e71`、
実装は `1eab5504164232230afb2c21e150285347adba29`。この引き継ぎのコミットは
その後続です。**再開時は実際のローカル／リモートHEADを優先**し、古い指定
`d5d33d9e`や途中コミットへ戻さないこと。mainへの昇格はありません。

## 確定した状態と認定範囲

- M001のH01/H02/H03×B2/B8の6物理参照は16384sppで認定済み。最初の
  H01/B8 tarは過去セッションで実際に解析され、未確認状態は解消済み。
  再生成・再採取しない。根拠は[016](016-six-original-references-and-retained-rc-raw-replay.json)/
  [017](017-reference-and-retained-incumbent-outcome.md)。
- 041は **RAY_PARAMETRIC_FIXED_UNIT_GPU_CONSTRUCTION_PASS：6/6条件、24/24 seed**。
  [240 CPU準備](240-restir-gi-fixed-unit-cpu-preparation.json)、
  [241 全条件](241-restir-gi-fixed-unit-six-gpu-conditions.json)、
  [242 結果と限界](242-restir-gi-fixed-unit-six-gpu-outcome.md)、
  [243 検証](243-restir-gi-fixed-unit-verification.json)が確定証拠。
- GPU内で元の有限長PTと観測用PTを両方生成し、実際の公式SDK
  Make/Pack→別dispatchのLoad/Unpack→画像合成まで検証。CPU候補・画像・primary
  のアップロードや中間readbackはない。元PT/primary/sourceは全画素ビット一致。
- SDKの位置は受信点の実際のspawn原点Oを基準とした `D=float32(t*wi)`、受信点0。
  元のbarycentric世界交点H・その位置での直接光／suffix／次のspawnは別途保持。
  O+DとHが厳密ビット同一だとは主張せず、元の幾何許容誤差で同一三角形・実レイ
  との一致を検証する。元の方向PDF、有限深度、BRDF、黒い背景は変更していない。
- 一律のSDK放射輝度単位64でMake入力Liを掛け、パッキング前後の陰影結果を64で
  割ってから元単位のprimary directを1回加える。参照・画質閾値・画像の物理単位
  は変更しない。全画素・全条件共通であり、画素ごとの露出調整ではない。
- MISSはSDK M0、黒いHITはM1、元の試行数は常に1として別管理。偽の有限MISS点、
  追加1/r²・BRDF・bounce、問題候補の破棄はしない。
- 2,764,800新規camera/path試行（両role合計）、6,912,000観測vertex slot、
  43,200 bounded GPU unit。観測query1,579,382、secondary HIT31,358、MISS142,586、
  黒いHIT5,654。最大復元誤差は非圧縮1.164153218e-10、圧縮6.521295290e-6で、
  全件が元の相対＋絶対許容誤差内。旧世界座標H-O方向の不合格24画素も診断値として
  保存し、隠していない。実際のSDK相対方向は同じ3e-4/3e-6ゲートで全件合格。
- 最大所有GPU true peak59,060,784 bytes、各native21 allocation/free対、終了時0。
  AS/scratch/staging/pipelineを含みdriver-private/CPUメモリは除外。22実子プロセスの
  command/effective limits/PID/reaped exit/no-timeout証拠あり。GPU採取は累計196件。

**これは候補生成・格納・復元の認定だけ**です。空間／時間resampling、frame間
変換、previous motion、checkerboard、history/reset、動的状態、HDR品質、同品質の
速度／メモリ優位、新規アーキテクチャ、汎用的な不偏性は未認定です。元の世界座標
の不合格や他の研究の失敗を、今回の結果で合格へ書き換えてはいけません。

## このセッションの失敗と訂正を保存すること

- 037：公式Math.hlsliのinclude漏れで最初のHLSLコンパイル失敗。
  [226–228](227-restir-gi-physical-gpu-preparation-outcome.md)。GPU未実行、停止のまま。
- 038：includeだけを別途事前登録して修正。H01/B2のseed2で端点方向が不合格。
  [229–232](231-restir-gi-physical-gpu-float32-outcome.md)。後続5条件は未実行。
- 039：[233–235](234-restir-gi-frozen-endpoint-diagnosis-outcome.md)は固定出力のCPU診断。
  1.24mm区間のz交点ずれ0.666µmを特定しただけ。038を再認定していない。
- 040：[236–239](238-restir-gi-local-candidates-packing-stop-outcome.md)。相対位置表現は
  H01の2条件で全seed合格。H02/B2の最初のseedが元の2% RGBパッキング予算で失敗し、
  残り3条件は未実行。040全体は停止のまま。
- 041：[登録](../experiments/041-sdk-radiance-unit-range-correction.md) `7eb7af4f`、
  [厳密なblack-bin境界の実行前補足](../experiments/041a-exact-sdk-black-bin-addendum.md)
  `6f379d55`。CPU診断で040の63不合格が低輝度の黒への量子化だと確認。
  SDKの厳密な黒境界は `2^(-20+1/409.6)`。固定64はこの境界と元の2e-8誤差床から
  実行前に計算した値。33,374 bin境界／隣接float32値と8新規テストがPASS。
  040と**同じseed列**を使う制御比較で、新しい独立streamだとは称していない。
  6 GPUプロセスは新規にパスを生成し、040のGPU出力を再生していない。
- 035の215–218認定はouter audit wall guard不足で**撤回済み**。
  [219–221](220-restir-gi-physical-audit-envelope-outcome.md)を保持。
  [036/224](224-restir-gi-supervised-audit-outcome.md)が実際の監視付き6 CPU監査を認定。
  CPU double抽出をGPU float32・HDR・不偏性に拡張解釈しない。

## 再開時に読む実装と生データ

現在の入口は [restir_gi_unit_bridge.py](../../../../scripts/research/lane_m_gi_competitiveness/restir_gi_unit_bridge.py)、
[unit codec](../../../../scripts/research/lane_m_gi_competitiveness/restir_gi_unit_codec.py)、
[full unit model](../../../../scripts/research/lane_m_gi_competitiveness/restir_gi_unit_model.py)。
041は040のnative/GLSLをそのまま使い、単位のHLSLと全件モデルだけ変更する。
040の [local bridge](../../../../scripts/research/lane_m_gi_competitiveness/restir_gi_local_bridge.py)、
[reversible overlay](../../../../scripts/research/lane_m_gi_competitiveness/restir_gi_local_overlay.py)、
[local full model](../../../../scripts/research/lane_m_gi_competitiveness/restir_gi_local_model.py)も必要。
元nativeは [physical_gpu.cpp](../../../../src/research/lane_m_gi_competitiveness/restir_gi_physical_gpu.cpp)、
元shaderは [physical_make.hlsl](../../../../shaders/research/lane_m_gi_competitiveness/restir_gi_physical_make.hlsl)。
元037ファイルのinclude漏れを直接直さず、事前登録済みのprivate overlayを使う。

生データの基点は `out/research/lane-m-gi-competitiveness/`。

```text
m001-restir041-cpu-build-v1/result.json
m001-restir041-cpu-build-v1/diagnosis/     # 固定040データの全4seed/critical grid
m001-restir041-{h01,h02,h03}-b{2,8}-v1/result.json
  capture/seed-{0,1,2,3}/                # original/observed、全vertex、packet、local、SDK、PFM
  audit/seed-{0,1,2,3}-full-errors.npz    # 全件誤差・旧絶対座標失敗maskを含む
  native.* / numeric.*                  # 実command/limits/PID/terminal証拠
m001-restir041-six-summary-v1/           # input/payload SHA256 inventories
m001-restir040-*/                        # 成功2条件と失敗1条件を全て保持
```

公式SDKは `out/external/rtxdi-library-f12037fa033` @
`f12037fa8e97ebc08e9e3edfd2de528ed1772a4b`、sampleは
`out/external/rtxdi-a6efab96033` @ `a6efab966b7c3b272da0461578eb56ac61c7cbff`。
SDKを編集・更新しない。既存SDK/CPU契約033・synthetic device034はその範囲だけの証拠。
大きなデータはGit外のout/にあるため、**別環境へ移るときはGit cloneだけでは不足**。
必要なout/と外部SDK・ビルド成果物を、既存manifestのSHAを保って別途引き継ぐこと。
欠けた証拠を勝手な再実行で補わない。

中断・Push・Issue本文照合と全生データ再ハッシュの最終receiptは
`out/m001-restir041-pause-confirmation-v1.json`。
引き継ぎの検証は [245](245-session-pause-handoff-verification.json)。
GPU/CPU研究プロセスは全て終了・reap済みで、中断後に継続するジョブはない。

## 再開後の最初の仕事

1. ユーザーの再開指示を確認し、branch/HEAD/Git変更/Issue7と上の最終receiptを読む。
   [AGENTS.md](../../../../AGENTS.md)、[charter](../../../../docs/research.md)、
   [current status](../../../status.md)、[roadmap](../../../roadmap.md)、
   [protocol](../../../protocol.md)、[001](../experiments/001-first-cohort-preregistration.md)/
   [002](../experiments/002-reference-admission-prospective.md)、[index](index.json)を読む。
   過去の成功を再試験するのでなく、必要な実体とhash/terminalを確認する。
2. 次の042以降を**実験前に**事前登録する。主な未解決は、実シーンでのSDK空間・時間
   再利用の画像生成。per-receiverのDをそのまま隣接画素・前フレーム間で混ぜては
   いけない。source→destination frame変換、ownerのworld origin、previous surfaces/
   motion/reset/checkerboard/current-invalid、同じ64単位のhistory、可視性・両面と
   persistent/true-peak所有をCPU準備から検証する。SDKのLoad/StoreとRAB境界を読む。
3. MISS M0と全raw trial数の違いは再利用時の正規化／バイアスの未解決点。公式SDK
   miss policyを採用したことだけで物理一致・不偏性を主張せず、明示的なnull trial/
   エネルギー対照と全件監査を設ける。無断で偽MISS点やsample PDFを作らない。
4. 実際の再利用パイプラインが適格になった後、全6条件・全seedのcold/warm HDR品質と
   事前登録したbudgetを公平に比較する。022は**raw PTだけを相手にした速度認定を禁止**。
   026/028 NRD・030/032残差の失敗を設定自動探索で救済しない。原RC24敗・修正DDGI18敗
   は構成別結果でありfamily全体の棄却ではない。
5. 最終目標は新規で競争力のある実画像Renderer transport。代表GI family、独立した
   新規heldout、camera/light/rigid/deforming/topology/churn、Sponza以外の広いシーン、
   複数GPUクラス／software fallback／deployability、全E2E GPU costとpersistent/
   true-peak memoryを満たす。同品質のGPU時間／メモリ、または同コストの品質／機能の
   優位が必要。品質不合格の高速化や今回の候補単体を完了扱いしない。

## 運用・環境

- ユーザーは電源／クロック設定を変えない範囲のGPU実行を明示許可済み。ただし中断中
  の新規実行許可ではない。再開後もCPU準備・監査と事前登録、実行コマンドの告知が先。
- CPU/NumPy/buildには次の環境を使う。system PythonにはNumPyがない。再インストール
  しない。Git/ghネットワークにはこのLD_LIBRARY_PATHを付けない（Nix curlが壊れる）。

```bash
LD_LIBRARY_PATH="${NIX_LD_LIBRARY_PATH:-${LD_LIBRARY_PATH:-}}" OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 \
  out/research/n010-comparison-readiness/venv/bin/python <new-registered-entry>
```

- `anchor_process_limits.C.limits()`はparent CPU soft360/hard1200/AS4GiBにするだけで
  wall監視ではない。実numeric workerを必ず `C.guarded(cpu=1200,wall=1800)`から実行し、
  worker内でparent limitsへ下げない。compile/test/input/nativeは登録通り120/180。
  effective limits、SIGXCPU default/unblocked、PID、reaped terminalが必要。
- 既存の終了済みディレクトリに再実行しない。観測handleが失われたら同じPID/出力を
  調べ、再起動しない。全失敗を保存。raw/manifests/tarはout/、大きなデータはGit禁止。
- GPUはAMD Radeon 8060S Graphics (RADV STRIX_HALO)、Mesa26.1.2。clock/power/特権設定禁止。
  この1台で一般的な優越性を主張しない。CI/Actions追加、N001〜N010履歴編集、main昇格、
  force push/ref削除は禁止。default CMake/Rendererは不変。
- default Renderer build/runtime と validation layersは今回 NOT_RERUN / NOT_RUN。
  実行したstandalone GPU認定と混同しない。`mise run research:check`に加えてLane Mの
  index全pathと現在Markdownリンクを明示検証済み（通常checkだけではLane Mを覆わない）。
- 元からのユーザー未追跡 `.claude/` とN010の `072-recovered-dynamic-references.json`、
  `121-hybrid-reference-qualification.json`、`128-replayed-point-guided-reference-qualification.json`
  は保持した。削除・コミット・修正しない。

再開プロンプト例：
「Lane Mを再開。研究ブランチの最新HEADとIssue7を確認し、結果244の引き継ぎ、現在の
research/status.md、041/041aと240〜245を読んでください。041は候補生成だけ6条件合格。
過去の停止・撤回を維持し、実シーンの座標frame変換／SDK再利用／null trial正規化を
次の事前登録から進めてください。CPUは自分で実行、GPUは電源・クロック変更なしで可。
元のLane M全目標は縮小しないこと。」
