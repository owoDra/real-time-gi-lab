# 2026-10-25 セッション引き継ぎ — Lane M 再開（目標達成まで）

唯一の現在要約は [research/status.md](../../../status.md)。本書は次セッションの
再開点。ユーザー決定は [再開決定](../../../decisions/2026-10-25-lane-m-reopen.md)：

- Lane M を再開。**完了＝研究目標の達成**（判定を記録して閉じることではない）。
  クローズ記録263/決定 [closure](../../../decisions/2026-10-25-lane-m-closure.md) は
  履歴として保存し、書き換えない。047 は完了条件として無効。
- **複数GPUは研究対象外**（ゲーム向けで主流でなく高コスト）。単一GPUの結果は
  単一GPUの結果として述べ、一般化しない。
- 再開は次セッションから。本セッション中は新規研究を開始しない。

作業場所 `/var/owo/workspaces/projects/gi-lab`、ブランチ
`research-lane-m-gi-competitiveness`、[Issue #7](https://github.com/owoDra/real-time-gi-lab/issues/7)
（再オープン済み）。**実際のローカル/リモート HEAD を優先**。main 昇格なし。

## 完了ゲート（再開決定より、緩和禁止）

新規で競争力のあるリアルタイムGI transport を、画像を生成するGPUパイプラインで
実装し、事前登録した未見heldout（Sponza規模、カメラ/光源/剛体/変形の動的シーン、
AS更新・history コストを計上）で固定HDRゲート（全画素：総NRMSE≤5%、間接≤10%、
|間接バイアス|≤5%）を満たし、公正な代表ファミリー（raw PT、PT+既存再構成、NRD、
DDGI、ReSTIR GI、RC）に対して、較正済み（045規約、MDE 5%、実用比1.20）の同品質
GPU時間/メモリ優位、または同コスト品質優位を示すこと。損失・停止は全て保存。

## 本セッションの結果（042–046、全て事前登録・公開済み）

| 研究 | 結果 | 主要文書 |
|---|---|---|
|042 ReSTIR GI 実シーン再利用|実装6/6、CPU独立replay不一致0、MISS=M0は+258–377%バイアス、null trialで±0.9%、品質0/6|[248](248-restir-gi-reuse-outcome.md)|
|043 ReSTIR+二次回帰再構成(CPU)|単フレーム0/6（warm間接12.5–26%）|[251](251-restir-reconstruction-cpu-outcome.md)|
|044 較正タイミング|v1順序パリティ欠陥で停止、v2対照順序バイアス超過→全判定不確定|[254](254-calibrated-timing-outcome.md)|
|045 最終規約改訂(32ペア)|MDE 5%採用。PT+再構成(PTR)がraw PTより品質一致で高速：H01/B2 2.2×、H03/B2 1.48×、H03/B8 10×採用、他3件不確定。PT16R がReSTIR+再構成を同コストで6/6支配|[257](257-final-timing-revision-outcome.md)|
|046 M002 新規heldout/動的状態|参照12/16認定。PTR 6/12合格（S4箱群・light-motion で不合格）、PT 10/12。高速化採用 S1/B2・S1C/B2、他4件不確定|[260](260-m002-outcome.md)|
|クローズ（撤回済み）|比較マトリクスと憲章判定は参考として有効|[262](262-lane-m-closure-matrix.json)/[263](263-lane-m-closure-outcome.md)|

要点：固定ゲートを満たすのはPT系のみ。唯一の採用済み高速化は既存部品（PT+幾何のみ
二次回帰）で、メモリ6.6倍・M002で一般化せず。新規性はまだない。GPU累計465件。

## 次セッションの作業（推奨順）

1. 再開の事前確認：HEAD/Git状態/Issue #7、本書、status、roadmap、protocol、
   決定2件を読む。残存研究プロセスがないことを確認。
2. **失敗原因の診断（CPU、既存データのみ）**：M002 の S4（world large-horizontal）、
   S1L/S3L（light-motion）で PTR が落ちた理由を、保存済み画像
   `out/research/lane-m-gi-competitiveness/m002-captures-v1/` と参照
   `m002-references-v1/` で事前登録のうえ診断（幾何マスクの破綻、小物体の照明
   詳細喪失、光源近傍の高周波など）。M001/M002 はもう開発データ扱い。
3. **新しいtransport候補の設計**（新規性の核）：例として、PTのパス生成側と
   再構成の統合（幾何+照明特徴を使う誤差制御付き適応サンプリング、
   直接/間接の分離再構成、光源近傍の重点化など）。prior art を調べ、新規性主張は
   根拠付きで。M001/M002 で開発→**未使用のM003 heldout**で事前登録検証。
4. **Sponza規模**：`integrated_state.hpp` の2048三角形上限を private コピーで外し、
   `n009_state_export` で Sponza 状態、N010 RQMC オラクルで参照（CPUコストを
   事前見積り）。
5. **時間方向の動的シーケンス**：カメラ/光源/剛体/変形の連続フレーム、BLAS/TLAS
   更新と history コストを計上（エクスポータは1ステップのみ→シーケンス生成を実装）。
6. **公正比較**：候補を NRD・DDGI・ReSTIR・PT+再構成・raw PT と同ゲート・045規約で比較。

## 環境・規約

```bash
LD_LIBRARY_PATH="${NIX_LD_LIBRARY_PATH:-${LD_LIBRARY_PATH:-}}" OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 \
  PYTHONPATH=scripts/research/lane_m_gi_competitiveness \
  out/research/n010-comparison-readiness/venv/bin/python <script>
```

- git/gh には上の LD_LIBRARY_PATH を付けない。system Python に NumPy なし。
- 状態生成（GPU不要）：`PHOS_N009_CONTRACT=out/research/n010-comparison-readiness/light-selection-v1/sponza-local-motion.n009contract build/n009/src/research/n009_scene_contract/n009_state_export --scene X.gltf --out DIR --regime static|camera-motion|light-motion|moving-rigid|deforming|topology-churn --frame-id 1`
  （M001 H01 をバイト一致で再現確認済み）。参照：`scripts/research/lane_m_gi_competitiveness/m002_states.py`
  の qualify（`qualify_references.py` ラッパ）。H01/B2 16384spp は1 seed約7 CPU秒。
- タイミング：`frame_timing_bridge.py`（045規約）、ハーネス `frame_timing_gpu.cpp`
  （--capture/--target/--calibration）。M002 ブリッジ `m002_bridge.py`。
- 規約：事前登録をコミット・Push してからコード/GPU、変更は補足(addendum)で、
  dev GPU 実行は事前開示のみ。電源/クロック変更・CI追加・既存証拠上書き・根拠のない
  再実行は禁止。quiet ゲートは CPU オラクル実行中は GPU 起動を拒否する（正常）。
- コミットメッセージに Co- 行を付けない、.claude/ と未追跡 N010 json 3件はコミットしない。

## 次セッションの再開プロンプト

```text
Lane Mを再開してください。AGENTS.md、research/status.md、research/roadmap.md、
research/decisions/2026-10-25-lane-m-reopen.md、
research/lanes/lane-m-gi-competitiveness/results/265-session-handoff-reopen-2026-10-25.md
とIssue #7を読み、最新HEADから引き継いでください。
Lane Mの完了は「研究目標の達成」です（判定を記録して閉じることではありません）。
複数GPUは研究対象外です。M002でPT+再構成が落ちた原因の診断から始め、
新規transport候補を設計し、未使用heldout（M003、Sponza規模・時間方向の動的シーンを含む）
で事前登録して検証し、NRD・DDGI・ReSTIR・PT+再構成・raw PTと同ゲート・045規約で
公平に品質・速度・メモリを比較してください。
CPU・GPUとも実行可。電源・クロック変更、既存証拠の上書き、根拠のない再実行、CI追加は禁止。
研究ブランチで自律的に進め、結果を記録・コミット・Pushし、Issue #7を更新してください。
```

## goal 用プロンプト

```text
Lane Mの研究目標を達成する：新規で競争力のあるリアルタイムGI transportを画像生成GPU
パイプラインで実装し、事前登録した未使用heldout（Sponza規模、カメラ/光源/剛体/変形の
時間方向動的シーンを含み、AS更新・historyコストを計上）で固定HDRゲート（総NRMSE≤5%、
間接NRMSE≤10%、|間接バイアス|≤5%、全画素）を満たし、raw PT・PT+既存再構成・NRD・
DDGI・ReSTIR GI・RCに対して045規約で較正した同品質GPU時間/メモリ優位または同コスト
品質優位を示す。複数GPUは対象外。ゲート緩和・クローズ判定での代替は不可。
```
