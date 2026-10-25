# 2026-10-26 セッション引き継ぎ — Lane M（RTCVS開発中、M003未登録）

唯一の現在要約は [research/status.md](../../../status.md)。前回の引き継ぎ
[265](265-session-handoff-reopen-2026-10-25.md) と
[再開決定](../../../decisions/2026-10-25-lane-m-reopen.md) の条件はそのまま有効
（完了＝研究目標の達成、複数GPUは対象外、ゲート緩和・クローズ判定での代替は不可）。

作業場所 `/var/owo/workspaces/projects/gi-lab`、ブランチ
`research-lane-m-gi-competitiveness`、[Issue #7](https://github.com/owoDra/real-time-gi-lab/issues/7)。
**実際のローカル/リモート HEAD を優先**。実行中の研究プロセスなし（停止済み）。

## 今回のセッションで完了したこと

| 項目 | 結果 | 文書 |
|---|---|---|
|048 M002 PTR失敗の診断（CPU）|DIAGNOSIS_COMPLETE：S4/S3Lは空間演算子がほぼ恒等（数画素の島）、S1Lは演算子自体のバイアス8–9%|[266](266-m002-ptr-failure-diagnosis.md)|
|049 候補設計の事前登録（RTCV）|登録済み。dev は無制限開示|[049](../experiments/049-rtcv-candidate-design-and-development.md)|
|049a 開発記録|RTCV→RTCVF→RTCVS の経緯|[049a](../experiments/049a-development-record-rtcvs.md)|
|開発要約|最新の開発表（証拠ではない）|[267](267-rtcvs-development-summary.md)|

## 現状の要点（開発、証拠ではない）

- 候補 **RTCVS**（ROLE 7）＝空間経路再利用（近傍経路を二次頂点で再接続、MIS）
  ＋双線形再投影累積＋光源変化時のみ再生制御変量。
- Sponza規模（dev視点）：光源 k1 6.9ms・剛体 k1 11.5ms で合格、最良PTAの約1.8–2.1倍速、raw PT比約380倍。
- 小規模シーン：光源移動では勝つが、カメラ/剛体/変形ではPTA k4（0.19–0.30ms）が同等以上に速い。
  主遮蔽物が大きく動くS1剛体はRTCVSが遅延で不合格。H02カメラ・H03・S1複合・S4カメラは全時間的手法が不合格。
- したがって、作成済み **050ドラフト**（[drafts/050](../drafts/050-m003-rtcvs-DRAFT-not-registered.md)、
  例外なしの厳格判定）のままM003を実行すると NOT_ACHIEVED の公算が大きい。

## 次セッションの作業（推奨順）

1. 事前確認：HEAD/Git状態/Issue #7、本書、267、049a、050ドラフト、status、protocol を読む。
   `pgrep -af rtcv` で残存プロセスがないこと。
2. 開発の残課題（devデータのみ、GPUジョブは必ず1本ずつ）：
   - 強い幾何運動（S1剛体）の遅延：実装済み未試験の `-DGEOM_NO_REPLAY=0 -DGEOM_SPARSE=9`
     （1/9画素の再生で変化検出→シュリンク補正＋アンチラグ）を S1/S2/H02/D-SP の剛体・変形で評価。
   - 小規模シーンの固定費（SPR/combine のパス数）削減、SPRのMIS近似バイアス（S4で−4.6%）低減。
   - Sponza開発シーケンス D-SP-camera/deform/static の評価（参照未生成、1本約25分）。
3. 候補を凍結し、050ドラフトを最新設計に合わせて `experiments/050-...md` として**コミット・Push（事前登録）**
   してから `m003.py scenes → lock → qualify(CPU) → build → ladders` →外部4ファミリー→較正→T1→公開。
   M003（特にSponza参照）は一度しか使えない。登録後のチューニング禁止。
4. 結果に関わらず全損失を保存し、Issue #7 を更新。

## 実行メモ

```bash
# Python（git/gh には LD_LIBRARY_PATH を付けない：git push が libcurl で失敗する）
LD_LIBRARY_PATH="${NIX_LD_LIBRARY_PATH}" OPENBLAS_NUM_THREADS=4 \
  PYTHONPATH=scripts/research/lane_m_gi_competitiveness \
  out/research/n010-comparison-readiness/venv/bin/python scripts/research/lane_m_gi_competitiveness/rtcv_dev.py \
  --tag TAG --k-new 32 --frames 192 --capture 0,96,128,160,191 \
  --build out/research/lane-m-gi-competitiveness/rtcv-dev-build41L --seqs L-S1-rigid --roles RTCVS:1:256 PTA:4:256
# 長ガード付きビルド（Sponza 192フレームに必須）
... venv/bin/python scripts/research/lane_m_gi_competitiveness/m003_build.py out/research/lane-m-gi-competitiveness/rtcv-dev-buildNN
# 個別シェーダ変種: build/n009/_deps/glslang-build/StandAlone/glslang -V --target-env vulkan1.3 -DROLE=7 -DNAME=VAL shaders/.../rtcv_sequence.comp.glsl -o DIR/rtcv_role7.spv
# 要約: rtcv_dev_summary.py <sweep logs...>
```

- 小規模devの参照はキャプチャ 0,96,128,160,191、Sponza devは 0,160,176,191（別フレームは参照が無い）。
- `pkill -f` で自分のシェルのコマンド文字列に一致させない（`pgrep`→`kill PID`）。
- Bash前景は最大10分：待機は `timeout 590 tail --pid=PID -f /dev/null` を繰り返す。
- コミットに Co- 行を付けない。`.claude/` と未追跡N010 json 3件はコミットしない。電源/クロック変更・CI追加・既存証拠上書き禁止。

## 次セッションの再開プロンプト

```text
Lane Mを再開してください。AGENTS.md、research/status.md、
research/decisions/2026-10-25-lane-m-reopen.md、
research/lanes/lane-m-gi-competitiveness/results/268-session-handoff-2026-10-26.md、
results/267-rtcvs-development-summary.md、experiments/049a-development-record-rtcvs.md、
drafts/050-m003-rtcvs-DRAFT-not-registered.md とIssue #7を読み、最新HEADから引き継いでください。
Lane Mの完了は「研究目標の達成」です（判定を記録して閉じることではありません）。複数GPUは対象外です。
候補RTCVSの開発残課題（強い幾何運動の遅延、小規模シーンの固定費、SPRのMIS近似バイアス、
Sponza dev のカメラ/変形/静止）を開発データだけで詰め、候補を凍結して050を事前登録（コミット・Push）してから、
未使用heldout M003（Sponza規模・時間方向の動的シーンを含む）で、raw PT・PT+既存再構成（PTR/PTA/PTG）・
NRD・DDGI・ReSTIR GI・RCと同ゲート・045規約で公平に品質・速度・メモリを比較してください。
CPU・GPUとも実行可（GPUジョブは同時に1本）。電源・クロック変更、既存証拠の上書き、根拠のない再実行、
CI追加は禁止。研究ブランチで自律的に進め、結果を記録・コミット・Pushし、Issue #7を更新してください。
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
