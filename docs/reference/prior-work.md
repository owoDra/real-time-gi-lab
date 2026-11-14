# 先行研究

数値は各著者の自己申告で、こちらでは再現していない。「確認」の列は、何を読んで確かめたかを示す。

## 本文・ソースを確認したもの（2026-11-13）

| 先行 | 要点 | この研究との関係 |
|---|---|---|
| Split Radiance Cascades（Freeman, Sannikov, Pitt-Francis, arXiv 2607.20384 v2） | 可視画素から最寄りのワールド格子プローブをハッシュに登録（カスケードごと、LOD 付き）。画素から 1 本ずつレイを撃ち、ヒット距離で区間に振り分ける（レイ分割）。区間長と角度は ×4、c0 は 32 方向、4 カスケード。OptiX（HWRT）。単一フレームで Sponza 8.6 ms（RTX 3080 Laptop、G-buffer と影を除く。トレース 1.3 ms 以外が重い）。可動物体の時間蓄積は未対応、リークはマージ時の補間で出る、c0 間隔より小さい物体は落ちる | 最も近い先行。プローブ配置をこれに寄せた。差分は HWRT なし、ボクセルの区間トレーサ、スタイル演算子 |
| Gavras, "Exploration and Optimization of Radiance Cascades for Real-Time Applications"（Chalmers 修士, 2025） | スクリーン配置プローブ＋ワールド空間区間。全区間を三角形 BVH でトレース。1080p Sponza 144 ms（M1）。履歴なし。カメラ移動でちらつくのが最大の未解決点 | スクリーン配置をやめた根拠 |
| Abou Dan & Jensen, "Screen Space Global Illumination Using Radiance Cascades in 3D Video Games"（Chalmers 修士, 2025） | スクリーン配置＋スクリーン空間トレース。2〜26 ms。画面外は扱えない。小さな動きでもちらつく。**本文は非公開で、要旨だけ確認** | 近距離を深度バッファだけで済ませない根拠 |
| Godot HDDAGI（godotengine/godot #86267 ほか、2026-11 時点で未マージ） | カメラ中心のカスケード、8³ 領域 → 4³ ブロックの 64 ビット占有マスク → ボクセルの 3 段、分岐しない階層 DDA。プローブは 6〜32 フレームかけて収束。動的物体は場に寄与しない | ボクセルの構造の手本。差分は動的物体の寄与と履歴なし |
| three-rc（CodyJasonBennett/three-rc、WebGL2、ライセンスなし） | スクリーン配置、フラグメントシェーダで BVH をスタック走査。作者自身が WebGL での BVH 走査は実用的でないとしている | WebGL2 ティアをスクリーン空間のみとする方針を支持。コードは流用しない |
| gpuweb ray query（#11053〜#11056、2026-10-13 提出） | 2026-10-27 の WGSL 会合で提案として取り込むと決定、大幅な改訂が必要。Dawn に実装なし | BVH ティアは当面ネイティブ限定の将来枠 |

## 検索で確認したもの（2026-11-14、要旨と検索結果の範囲）

- [Split Radiance Cascades](https://www.alphaxiv.org/abs/2607.20384)：単一フレームと時間蓄積の両方の結果を報告している。
- [Holographic Radiance Cascades](https://arxiv.org/abs/2505.02041)：点サンプルのレイをやめる方向の RC。2D 限定で、
  3D への拡張はメモリが障害とされる。
- [gamedev.net の SVOGI スレッド](https://nene.gamedev.net/forums/topic/711743-svogi-implementation-details/?page=8)：
  二値のボクセル化を段階的な密度に替えて、動く物体の跳びを避けたという非公式の報告。
- 3D の Radiance Cascades で、動く物体によるちらつきを扱った公開研究は見つからなかった。

## 記憶に基づくもの（未確認。使う前に本文を確かめる）

- Crassin ら 2011（ボクセルコーントレーシング）：異方性の前置フィルタと、部分透過によるリーク。
- Lumen（Wright ら、SIGGRAPH 2022 コース）と AMD GI-1.0：ヒット点の放射を前置フィルタ済みのキャッシュから読む。
- Schied ら 2018（A-SVGF）：同じサンプルを引き直した時間勾配で履歴の重みを決める。
- Majercik ら 2019 / 2021（DDGI とその運用）：ヒステリシスと大きな変化への対処。
- Doi ら（Pacific Graphics 2021）：GI 対応のスタイライズ。本文未確認。
