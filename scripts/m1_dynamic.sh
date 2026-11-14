#!/usr/bin/env bash
# M1 step 3: the integrated renderer (local voxel update) on the fully dynamic Sponza, RC against DDGI (exploratory).
#  A: sponza-dyn (moving toon objects and sun), sun only and with sky: GI time, flicker, toon ramp changes (R4).
#  B: R1, response to a light switch: the sun jumps at frame 200 (sponza-dyn-switch200), static camera.
#  C: no history: DDGI from a cold start after N frames, static Sponza, irradiance dumped for the Mitsuba comparison.
# No reference is rendered here (GPU timings).
# Usage: bash scripts/m1_dynamic.sh OUT_DIR rc_and_ddgi_configs ddgi_configs
set -euo pipefail
out=${1:?out dir}; configs=${2:?configs}; ddgi=${3:?ddgi configs}
run() { bash scripts/run_with_vulkan.sh node build/native/rc.mjs "$@"; }
V='{"anchor":"scene","local":true}'
mise run build:rc >/dev/null
mkdir -p "$out"
for sky in nosky sky; do
  flag=$([[ $sky == nosky ]] && echo --no-sky || true)
  run --scene sponza-dyn --configs "$configs" $flag --vox "$V" --out "$out/dyn-$sky" > "$out/dyn-$sky.log" 2>&1
done
run --scene sponza-dyn-switch200 --configs "$configs" --no-sky --vox "$V" --response 200,400 --out "$out/switch" > "$out/switch.log" 2>&1
for n in 1 2 4 8 16 32 64; do
  run --scene sponza --configs "$ddgi" --no-sky --static-only --warmup 0 --frames $n --dump-irr --out "$out/cold-$n" > "$out/cold-$n.log" 2>&1
done
echo done
