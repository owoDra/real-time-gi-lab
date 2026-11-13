# 2026-11-13 — ツールチェーンとネイティブ先行

ユーザー決定（S0 の中で）。

1. ツールチェーンは TypeScript ＋ WebGPU（WGSL）。ネイティブは npm の `webgpu`（Dawn、Vulkan）、
   ブラウザは Chrome 系。比較は [S0 の記録](../spikes/s0-foundation.md)。
2. テストシーンは Khronos glTF-Sample-Assets の Sponza に替える。
3. 参照レンダラは S1 の品質計測の前に決める。
4. **ある程度実証できるまでは、開発と計測をネイティブだけで行う。** ブラウザでの計測は
   S0 の出口から外し、後段（遅くとも M1 統合の前）に回す。

4 の理由：この作業機ではブラウザの WebGPU が SwiftShader（CPU）に落ちる。nix 版 Brave は
`libvulkan.so.1` を読めず（`gpu/vulkan/vulkan_instance.cc: Failed to load 'libvulkan.so.1'`）、
Claude Code から起動したものは ANGLE / EGL の初期化に失敗する。直すには環境側の手当てが要り、
仮説の検証より先にやる価値が低い。

影響：

- ブラウザで動くかどうかは、コードがブラウザ版を持ち、SwiftShader で描いた画像がネイティブと
  一致することまでしか確かめていない。ブラウザでの GPU 時間は未計測。
- Dawn をネイティブとブラウザで共有しているので、ネイティブの数値がブラウザから大きく外れる
  可能性は低いと見ているが、未確認である。
- WebGPU のコア機能だけで書くという制約（R6）は変えない。ネイティブ専用の機能は使わない。
