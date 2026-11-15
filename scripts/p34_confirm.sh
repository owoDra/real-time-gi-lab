#!/usr/bin/env bash
# Phase 34 confirmation runs (docs/spec/60-confirmation.md). Conditions, order and rules are fixed in that document;
# this script only runs them. Usage: bash scripts/p34_confirm.sh <block> [...]
#   prereq   default-image sha256 (stops on a mismatch: build or configuration failure)
#   refs     Mitsuba references of the held-out views (CPU; no GPU timing may run meanwhile)
#   quality  deterministic quality runs (their GPU timings are not used)
#   timing   GPU timing blocks T1-T7 (refuses to start while a reference renders)
#   compare  reference comparisons, overflow blocks, native/browser image matches (CPU only)
# Output: box/out/p34/run/<block>/<name>/ (one directory per process), logs next to it.
set -euo pipefail
cd "$(dirname "$0")/.."
OUT=box/out/p34/run
RC=world-48-voxel-rc2-vrel
RCOBJ=world-48-voxel-rc2-vrel-obj
DL=ddgi-100-128-u8-g1-noadapt
DH=ddgi-100-128-u8-h0.5-g1-noadapt
DF1=ddgi-150-64-u1-h0.8-g1-noadapt
DF2=ddgi-125-64-u2-h0.5-g1-noadapt
GL=gl2-8-8
N64=sponza-dynobj-n64-deform
VK="bash scripts/run_with_vulkan.sh"

stamp() { echo "$(date -Is) load $(cut -d' ' -f1-3 /proc/loadavg)"; }
# run <dir> <rc.mjs args...>: one independent process; skips a directory that already has a finished log (resume after
# a procedural failure re-runs only what did not finish).
run() {
  local dir=$1; shift
  if [[ -f $dir/done ]]; then echo "skip $dir"; return; fi
  mkdir -p "$dir"
  { stamp; echo "args: $*"; } > "$dir/log.txt"
  $VK node build/native/rc.mjs --out "$dir" "$@" >> "$dir/log.txt" 2>&1
  stamp >> "$dir/log.txt"; touch "$dir/done"; echo "ok $dir"
}
# brun <dir> <browser.mjs args...>
brun() {
  local dir=$1; shift
  if [[ -f $dir/done ]]; then echo "skip $dir"; return; fi
  mkdir -p "$dir"
  { stamp; echo "args: $*"; } > "$dir/log.txt"
  $VK node build/native/browser.mjs --browser brave --browser-flags "--ozone-platform=wayland" --out "$dir" "$@" >> "$dir/log.txt" 2>&1
  stamp >> "$dir/log.txt"
  grep -q "browser closed" "$dir/log.txt" || { echo "browser not closed cleanly: $dir" >&2; exit 1; }
  grep -qi "swiftshader" "$dir/log.txt" && { echo "software adapter: $dir" >&2; exit 1; }
  touch "$dir/done"; echo "ok $dir"
}
no_reference() { if pgrep -f reference_irradiance.py >/dev/null; then echo "a reference is rendering: no GPU timing" >&2; exit 1; fi; }

prereq() {
  local d=$OUT/prereq
  run $d/sponza --scene sponza --configs $RC --no-sky --static-only --dump-irr --frames 60
  run $d/dynobj --scene sponza-dynobj --pose-frame 0 --configs $RC --no-sky --static-only --dump-irr --frames 60
  sha256sum $d/sponza/$RC.static.irr.f32 | grep -q '^9589339d' || { echo "sponza image changed" >&2; exit 1; }
  sha256sum $d/dynobj/$RC.static.irr.f32 | grep -q '^44c7e830' || { echo "sponza-dynobj image changed" >&2; exit 1; }
  echo "default images unchanged"
}

refs() {
  local py=build/refenv/bin/python
  export DRJIT_LIBLLVM_PATH=${DRJIT_LIBLLVM_PATH:-$(nix-build '<nixpkgs>' -A llvmPackages_19.libllvm.lib --no-out-link)/lib/libLLVM.so}
  for s in town-cam2 sponza-cam2; do
    [[ -f box/out/mitsuba/$s/scene.json ]] || mise run ref:export -- --scene $s
    for seed in 0 1; do
      local f=box/out/mitsuba/$s/E-b0-960x540-256spp-sky0_0_0-seed$seed.pfm
      [[ -f $f ]] || $py scripts/reference_irradiance.py box/out/mitsuba/$s --spp 256 --bounces 0 --seed $seed
    done
  done
}

quality() {
  local d=$OUT/quality
  # Static scenes: static flicker, irradiance for the references (RC and the WebGL2 tier at the default warmup).
  run $d/sponza --scene sponza --configs $RC,$DL,$DH,$DF1,$DF2,$GL --no-sky --static-only --dump-irr
  run $d/sponza-cam2 --scene sponza-cam2 --configs $RC,$DL,$DH,$DF1,$DF2 --no-sky --static-only --dump-irr
  run $d/town --scene town --configs $RC --no-sky --static-only --dump-irr
  run $d/town-cam2 --scene town-cam2 --configs $RC --no-sky --static-only --dump-irr
  # DDGI linear against the references: converged (warmup 2400).
  for s in sponza sponza-cam2 town town-cam2; do
    run $d/ddgiref-$s --scene $s --configs $DL --no-sky --static-only --dump-irr --warmup 2400
  done
  # Response to a light switch.
  run $d/response --scene sponza-dyn-switch200 --configs $RC,$DH,$DF1,$DF2 --no-sky --response 200,520
  # Objects moving (static camera): jumps.
  run $d/dynobj --scene sponza-dynobj --configs $RC,$DL,$DH,$DF1,$DF2 --no-sky --static-only
  run $d/dynobj-cam2 --scene sponza-dynobj-cam2 --configs $RC,$DL,$DH,$DF1,$DF2 --no-sky --static-only
  # Building moving (static camera): jumps.
  for s in town-dynobj-bwave $N64-bwave $N64-bcut $N64-cam2-bwave town-dynobj-cam2-bwave; do
    run $d/bld-$s --scene $s --configs $RC,$DL --no-sky --static-only
  done
  # Leak (sky, 60 frames).
  for t in 0.02 0.1 0.05; do run $d/leak-$t --scene leak-$t --configs $RC,$DL,$GL --frames 60; done
  # Toon ramp band.
  run $d/toon --scene sponza-dyn --configs $RC,$GL --no-sky --static-only
  run $d/toon-cam2 --scene sponza-dyn-cam2 --configs $RC --no-sky --static-only
  # Object pixels (poses 0 and 100) and the floor near the objects (sponza-dynobj pose 0).
  for f in 0 100; do
    run $d/obj-f$f --scene $N64 --pose-frame $f --configs $RC,$RCOBJ --no-sky --static-only --dump-irr
    run $d/obj-ddgi-f$f --scene $N64 --pose-frame $f --configs $DL --no-sky --static-only --dump-irr --warmup 2400
  done
  run $d/floor --scene sponza-dynobj --pose-frame 0 --configs $RC,$RCOBJ --no-sky --static-only --dump-irr
  # Overflow: the fast path with a small pool against a large one.
  run $d/fly-pool3072 --scene sponza-wide100-fly-bwave --configs $RC --no-sky --dump-moving 12 --vox '{"maxBricks":3072}'
  run $d/fly-pool12288 --scene sponza-wide100-fly-bwave --configs $RC --no-sky --dump-moving 12 --vox '{"maxBricks":12288,"maxVoxels":1572864}'
}

timing() {
  local d=$OUT/timing
  no_reference
  # T1 neutral control and R1: the same config 8 times.
  for i in 1 2 3 4 5 6 7 8; do no_reference; run $d/t1/$i --scene $N64-bwave --configs $RC --no-sky; done
  # T2 held-out view: RC and DDGI linear, AB BA AB BA.
  local k=0
  for o in "$RC $DL" "$DL $RC" "$RC $DL" "$DL $RC"; do k=$((k + 1)); for c in $o; do no_reference; run $d/t2/$k-$c --scene $N64-cam2-bwave --configs $c --no-sky; done; done
  # T3 width: Sponza, 10x, 100x in a Latin square of 6 rounds, RC then DDGI linear (static camera).
  for c in $RC $DL; do
    k=0
    for o in "s w10 w100" "w10 w100 s" "w100 s w10" "s w100 w10" "w10 s w100" "w100 w10 s"; do
      k=$((k + 1))
      for w in $o; do
        local sc=$N64-bwave; [[ $w == w10 ]] && sc=sponza-wide10-dynobj-n64-deform-bwave; [[ $w == w100 ]] && sc=sponza-wide100-dynobj-n64-deform-bwave
        no_reference; run $d/t3/$c/$k-$w --scene $sc --configs $c --no-sky --static-only
      done
    done
  done
  # T4 density: sponza-bwave and sponza-dense10-bwave, AB BA x 3, RC then DDGI linear (static camera).
  for c in $RC $DL; do
    k=0
    for o in "s d" "d s" "s d" "d s" "s d" "d s"; do
      k=$((k + 1))
      for w in $o; do
        local sc=sponza-bwave; [[ $w == d ]] && sc=sponza-dense10-bwave
        no_reference; run $d/t4/$c/$k-$w --scene $sc --configs $c --no-sky --static-only
      done
    done
  done
  # T5 fast flight: RC and DDGI linear alternated, 3 each.
  k=0
  for o in "$RC $DL" "$DL $RC" "$RC $DL"; do k=$((k + 1)); for c in $o; do no_reference; run $d/t5/$k-$c --scene sponza-wide100-fly-bwave --configs $c --no-sky; done; done
  # T6 WebGL2 tier natively against RC (static camera).
  k=0
  for o in "$GL $RC" "$RC $GL" "$GL $RC"; do k=$((k + 1)); for c in $o; do no_reference; run $d/t6/$k-$c --scene $N64-bwave --configs $c --no-sky --static-only; done; done
  # T7 browser: RC native then browser, 3 rounds; then the WebGL2 tier in the browser on sponza, 3 runs.
  for k in 1 2 3; do
    no_reference; run $d/t7/$k-native --scene $N64-bwave --configs $RC --no-sky
    no_reference; brun $d/t7/$k-browser --scene $N64-bwave --configs $RC --no-sky
  done
  for k in 1 2 3; do no_reference; brun $d/t7/$k-gl2 --page gl2 --scene sponza --configs $GL --no-sky; done
}

compare() {
  local d=$OUT/compare q=$OUT/quality t=$OUT/timing
  mkdir -p $d
  npx esbuild src/native/compare_ref.ts --bundle --platform=node --format=esm --target=node22 --outfile=build/native/compare_ref.mjs --external:webgpu --external:pngjs --external:jpeg-js --log-level=warning
  mise run build:web >/dev/null
  local M=box/out/mitsuba
  cr() { local name=$1 ref=$2; shift 2; node build/native/compare_ref.mjs --ref "$ref" --json $d/$name.json --png $d/png "$@" > $d/$name.log; }
  mkdir -p $d/png
  for s in sponza sponza-cam2 town town-cam2; do
    local ref=$M/$s/E-b0-960x540-256spp-sky0_0_0-seed0.pfm,$M/$s/E-b0-960x540-256spp-sky0_0_0-seed1.pfm
    cr ref-$s-rc "$ref" --ours $q/$s/$RC.static.irr.f32
    cr ref-$s-ddgi "$ref" --ours $q/ddgiref-$s/$DL.static.irr.f32
  done
  cr ref-sponza-gl2 "$M/sponza/E-b0-960x540-256spp-sky0_0_0-seed0.pfm,$M/sponza/E-b0-960x540-256spp-sky0_0_0-seed1.pfm" --ours $q/sponza/$GL.static.irr.f32
  for f in 0 100; do
    local ref=$M/$N64-f$f/E-b0-960x540-128spp-sky0_0_0-seed0.pfm
    cr obj-f$f-rc "$ref" --objects --ours $q/obj-f$f/$RC.static.irr.f32
    cr obj-f$f-rcobj "$ref" --objects --ours $q/obj-f$f/$RCOBJ.static.irr.f32
    cr obj-f$f-ddgi "$ref" --objects --ours $q/obj-ddgi-f$f/$DL.static.irr.f32
  done
  local rects="1060,708,1260,735;1000,760,1300,860;720,700,940,760;300,800,600,900"
  local fref=$M/sponza-dynobj-f0/E-b0-960x540-128spp-sky0_0_0-seed0.pfm,$M/sponza-dynobj-f0/E-b0-960x540-128spp-sky0_0_0-seed1.pfm
  cr floor-rc "$fref" --rects "$rects" --ours $q/floor/$RC.static.irr.f32
  cr floor-rcobj "$fref" --rects "$rects" --ours $q/floor/$RCOBJ.static.irr.f32
  node build/native/compare_blocks.mjs --a $q/fly-pool12288 --b $q/fly-pool3072 > $d/overflow.log
  node build/native/compare_runs.mjs --a $t/t7/1-native --b $t/t7/1-browser --config $RC --png $d/png-browser > $d/browser-rc.log
  node build/native/compare_runs.mjs --a $q/sponza --b $t/t7/1-gl2 --config $GL --png $d/png-gl2 > $d/browser-gl2.log
}

for b in "$@"; do "$b"; done
