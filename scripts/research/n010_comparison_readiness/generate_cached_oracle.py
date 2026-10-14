#!/usr/bin/env python3
"""Computationally equivalent deterministic primary/direct cache (Amendment 3)."""
import argparse
from pathlib import Path
from generate_rqmc_oracle import generate,once
if __name__=='__main__':
 ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--out',type=Path,required=True);a=ap.parse_args()
 generate(a.out)
 p=a.out/'n010_rqmc_oracle.hpp';s=p.read_text()
 s=once(s,'    // One camera sample; writes per-component radiance.', '''    struct PrimaryCache {
        bool hit_ready{}, direct_ready{};
        Hit hit{}; Rgb direct{};
        uint64_t shadow_tests{},shadow_blocked{};
    };
    // One camera sample; writes per-component radiance.''')
 s=once(s,'                PrimaryRecord* primary = nullptr) const {','                PrimaryRecord* primary = nullptr, PrimaryCache* cache = nullptr) const {')
 s=once(s,'            const Hit hit = bvh_.closest(ray, tmin, tmax, ignore);','''            const Hit hit = bounce==0 && cache && cache->hit_ready ? cache->hit : bvh_.closest(ray, tmin, tmax, ignore);
            if(bounce==0 && cache && !cache->hit_ready) {cache->hit=hit;cache->hit_ready=true;}''')
 s=once(s,'            const Rgb e = direct(origin, n, hit.tri, rng, cnt);','''            Rgb e{};
            if(bounce==0 && cache && cache->direct_ready) {
                e=cache->direct;cnt.shadow_tests+=cache->shadow_tests;cnt.shadow_blocked+=cache->shadow_blocked;
            } else {
                const auto tests=cnt.shadow_tests,blocked=cnt.shadow_blocked;
                e=direct(origin,n,hit.tri,rng,cnt);
                if(bounce==0 && cache) {
                    cache->direct=e;cache->direct_ready=true;
                    cache->shadow_tests=cnt.shadow_tests-tests;cache->shadow_blocked=cnt.shadow_blocked-blocked;
                }
            }''')
 s=once(s,'                        std::size_t next_cp = 0;','                        std::size_t next_cp = 0;\n                        PrimaryCache cache;')
 s=once(s,'                                   primary && s == 0 ? &(*primary)[pixel] : nullptr);','                                   primary && s == 0 ? &(*primary)[pixel] : nullptr, &cache);')
 p.write_text(s)
