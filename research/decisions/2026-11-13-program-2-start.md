# 2026-11-13 — Program 2 開始

ユーザー決定。

1. Program 1 を終了し、タグ `archive/program-1` に保存する。経緯と理由は
   [docs/program-1/decision-2026-11-13.md](../../docs/program-1/decision-2026-11-13.md)。
2. Program 2 の目的は [憲章](../../docs/charter.md) のとおり：完全動的・大規模・高密度の
   ワールドで動き、写実と非写実を同じ空間で混在でき、WebGPU で動く GI。
3. 大規模ワールドと高密度ワールドへの対応は**必須**とする。
4. 新規性は必須ではない。新規の発想で既存を越えられるなら歓迎する。
5. 方向は Radiance Cascades 系の無ノイズ放射輝度場、区間ごとに切り替えるトレーサ、
   ボクセル化した StrataBrick、両端のスタイル演算子（[仮説](../../docs/architecture.md)）。
6. 評価は「同じコストでの品質」で行う（[評価方法](../../docs/evaluation.md)）。
   Program 1 の固定 HDR ゲートは使わない。
7. 作業ブランチは `p2`。Program 1 の資産のうち引き継ぐものだけを `legacy/` に置く。
8. 作業機に残っていた Program 1 のビルド成果物と生データは削除する。
   処分の内訳は [status.md](../status.md) に記録する。
