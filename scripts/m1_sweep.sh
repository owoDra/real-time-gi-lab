#!/usr/bin/env bash
# M1: DDGI comparator sweep against the cascades (exploratory). Runs every config on Sponza (sun only and with sky:
# static + moving, irradiance dumped for the Mitsuba comparison) and on the leak rooms (static), then compares the
# dumps with the 512-spp references in out/mitsuba/sponza (rendered in S2; no reference is rendered here, so the
# GPU timings are not disturbed).
# Usage: bash scripts/m1_sweep.sh OUT_DIR config1,config2,...
set -euo pipefail
out=${1:?out dir}; configs=${2:?configs}
run() { bash scripts/run_with_vulkan.sh node build/native/rc.mjs "$@"; }
mise run build:rc >/dev/null
mise run ref:compare -- --help >/dev/null 2>&1 || true
R=out/mitsuba/sponza
for sky in nosky sky; do
  flag=$([[ $sky == nosky ]] && echo --no-sky || true)
  run --scene sponza --configs "$configs" $flag --dump-irr --out "$out/$sky" > "$out/$sky.log" 2>&1
  s=$([[ $sky == nosky ]] && echo 0_0_0 || echo 0.45_0.6_0.9)
  ours=$(for c in ${configs//,/ }; do printf '%s,' "$out/$sky/$c.static.irr.f32"; done)
  node build/native/compare_ref.mjs --ref "$R/E-960x540-512spp-sky$s-seed0.pfm,$R/E-960x540-512spp-sky$s-seed1.pfm" \
    --ours "${ours%,}" --png "$out/$sky" --json "$out/$sky/reference.json" > "$out/$sky.ref.log" 2>&1
  rm -f "$out/$sky"/*.irr.f32
done
for t in 0.02 0.1; do
  run --scene leak-$t --configs "$configs" --frames 120 --out "$out/leak-$t" > "$out/leak-$t.log" 2>&1
done
echo done
