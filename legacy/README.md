# legacy — Program 1 から引き継いだ参照コード

**ビルドしない。** 移植と照合のための参照である。ファイルはタグ `archive/program-1` の
元の場所からバイト単位でそのまま移した。そのため `#include` の相対パスは元の配置の
ままで、単体ではコンパイルできない。動かす必要があるときはタグを取り出す。

| ここ | 元の場所 | 何に使うか |
|---|---|---|
| `stratabrick/hierarchical_stratabrick.hpp` | `src/research/lane_b_traversal/` | セグメント格子、所属、局所 refit / rebuild の実装。ボクセル StrataBrick の上位構造の手本 |
| `stratabrick/sparse_grid.hpp` | 同上 | 素の疎グリッド DDA（B001 で単体棄却）。区間限定での再検証の出発点 |
| `stratabrick/b003_micro_bvh8.hpp`、`b003_quantized_bvh8.hpp`、`b002_gpu_layout.hpp` | 同上 | セグメント内 BVH8 と量子化、GPU レイアウト。ボクセル近似の正解器、および S2 の代替案 |
| `stratabrick/software_bvh.hpp`、`traversal_common.hpp`、`traversal_contract.hpp` | 同上 | 共有 Hit 契約と基準実装 |
| `stratabrick/shaders/` | `shaders/research/lane_b_traversal/` | セグメント DDA＋ハッシュ探索、BVH8 トラバーサルの GLSL |
| `object-local/` | `src/research/lane_e_dynamic_geometry/`、`shaders/research/lane_e_dynamic_geometry/` | オブジェクト局所所有（剛体は変換のみ、変形は局所更新） |
| `split-rc/` | `shaders/research/lane_a_split_rc/` | Split RC の producer / gather / merge / resolve。カスケード合成の移植元 |
| `scenes/n004_scene_factory.py` | `scripts/research/lane_n_end_to_end_renderer/` | リーク（thin / thick / grazing / enclosed など）とワールド形状（dense / large-horizontal / vertical-tall）のシーン生成 |

計測値と結論は [docs/program-1/findings.md](../docs/program-1/findings.md)。

ここに無いもの（Split RC レンダラ本体、HWRT 経路、参照オラクル、タイミング較正、
DDGI / NRD / ReSTIR GI のハーネス、全実験記録）はタグにある：

```bash
git ls-tree -r --name-only archive/program-1 | grep <keyword>
git show archive/program-1:<path>
```
