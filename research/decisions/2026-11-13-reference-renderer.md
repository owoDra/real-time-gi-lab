# 2026-11-13 — 参照レンダラ

S1 の中で決めた（ロードマップの「品質を測る前に決める」）。ユーザーの確認はまだ取っていない。

1. 参照レンダラは **Mitsuba 3**（3.6.4、`llvm_ad_rgb` バリアント、CPU）にする。
2. シーンは glTF を直接ではなく、こちらの glTF 読み込み（`src/core/gltf.ts` の `SceneData`）から変換して渡す。
   アルファマスク、法線マップ、両面材質の解釈を製品側と揃えるため。変換は、品質を初めて測るとき
   （ワールド空間のトレースが入る S2 以降）に書く。
3. 放出側プロキシは「放射のみ・反射率 0」の材質として変換で表す。

理由：

- 正解器は製品のコードと独立しているほうがよい（同じ誤りを共有しない）。自前のパストレーサ（Vulkan の
  ハードウェアレイトレーシングでも WebGPU のコンピュートでも）は、結局 Mitsuba との点検が要る。
- この作業機で動くことを確認した（Cornell box を描画）。CUDA は使えないので LLVM（CPU、32 スレッド）。
- 遅さ（特に動的シーケンスの多フレーム）が問題になったら、Mitsuba で点検した GPU のパストレーサを足す。
  そのときも正解の定義は Mitsuba に置く。

セットアップ（作業機、NixOS）：

```bash
mise exec -- python -m venv build/refenv
build/refenv/bin/pip install mitsuba==3.6.4
export DRJIT_LIBLLVM_PATH=$(nix-build '<nixpkgs>' -A llvmPackages_19.libllvm.lib --no-out-link)/lib/libLLVM.so
```

`nix build nixpkgs#...`（flake の最新 nixpkgs）の LLVM は `GLIBC_2.44` を要求して読めなかった。システムと同じ
チャンネルの `<nixpkgs>` から取る。

追記（S2）：変換（`src/native/mitsuba_export.ts`）と、GI パスと同じ量（1 バウンスの間接放射照度）を正確な可視性で
計算する積分器（`scripts/reference_irradiance.py`）を書いた。比較は 960×540、512 spp × 2 本（各約 5 分）。
numpy は入れずに PFM で受け渡している。
