#!/usr/bin/env python3
"""N010 probe model: consume attested GPU keys; retain the N009 stage definitions."""
import argparse
from pathlib import Path
from generate_capture import once

ROOT = Path(__file__).resolve().parents[3]


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", type=Path, required=True)
    a = ap.parse_args()
    s = (ROOT / "src/research/n009_scene_contract/n009_probe_model.cpp").read_text()
    s = once(s, "struct Contrib {",
             "struct LookupAudit { float position[4]; std::int32_t keys[4][4]; };\n"
             "static_assert(sizeof(LookupAudit) == 80);\nstruct Contrib {")
    s = once(s, "        const auto prim = records<GHit>(capture / \"gpu/hits.bin\");",
             "        const auto audit = records<LookupAudit>(capture / \"gpu/composite-lookup.bin\");\n"
             "        if (audit.size() != npx) throw std::runtime_error(\"lookup audit size mismatch\");\n"
             "        std::uint64_t reconstructed_key_mismatch_lookups = 0;\n"
             "        const auto prim = records<GHit>(capture / \"gpu/hits.bin\");")
    s = once(s, "                q.pos = fv(pos);", "                q.pos = fv(audit[id].position);")
    s = once(s, "                    q.key[c] = k;",
             "                    Key actual{};\n"
             "                    std::copy_n(audit[id].keys[c], 4, actual.begin());\n"
             "                    reconstructed_key_mismatch_lookups += k != actual;\n"
             "                    k = actual;\n"
             "                    q.key[c] = k;")
    s = once(s, '\\"schema\\":\\"n009-probe-model/1\\"', '\\"schema\\":\\"n010-probe-model/1\\"')
    s = once(s, '           << ",\\"cpu_retrace_matches_gpu_hit\\":" << traced_match << "}\\n";',
             '           << ",\\"reconstructed_key_mismatch_lookups\\":" << reconstructed_key_mismatch_lookups\n'
             '           << ",\\"cpu_retrace_matches_gpu_hit\\":" << traced_match << "}\\n";')
    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_text(s)
