#!/usr/bin/env python3
"""Independent dense, cache-free control of the repository RC estimator."""
import argparse
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
BLOCK='''    float sum_indirect=0.0;
    for(uint cascade=0u;cascade<p.counts.w;++cascade) {
        float spacing=p.scene_origin_spacing.w*float(1u<<cascade);
        ivec3 probe=ivec3(floor((pos-p.scene_origin_spacing.xyz)/spacing));
        vec3 centre=p.scene_origin_spacing.xyz+(vec3(probe)+vec3(0.5))*spacing;
        float upper=p.light_pos_interval.w*float(1u<<cascade);
        float lower=cascade==0u ? 0.0 : p.light_pos_interval.w*float(1u<<(cascade-1u));
        uint fixed_sum=0u;
        for(uint ray=0u;ray<8u;++ray) {
            const float v=0.5773502691896258;
            vec3 wi=normalize(vec3((ray&1u)!=0u?v:-v,(ray&2u)!=0u?v:-v,(ray&4u)!=0u?v:-v));
            uint hit; vec3 position,geometric_normal;
            float value=0.0;
            if(trace(centre+wi*lower,wi,upper-lower,INVALID,hit,position,geometric_normal)) {
                // Preserve the incumbent estimator's unshadowed secondary
                // Lambert term; its light leak is a scored weakness.
                vec3 lv=p.light_pos_interval.xyz-position;
                float d2=dot(lv,lv),s=p.light_pos_interval.w;
                if(d2>1.0e-12) value=max(0.0,dot(geometric_normal,normalize(lv)))*s*s/(PI*(s*s+d2));
            }
            fixed_sum+=uint(round(clamp(value,0.0,1.0)*65535.0));
        }
        sum_indirect+=float(fixed_sum)/(8.0*65535.0);
    }
    float indirect=sum_indirect;
'''
if __name__=='__main__':
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--out',type=Path,required=True)
    a=ap.parse_args()
    source=(ROOT/'shaders/research/n010_comparison_readiness/n010_pixel_pt.comp.glsl').read_text()
    start=source.index('    float direct=direct_light(pos,normal,prim), sum_indirect=0.0;')
    end=source.index('    pixels[id]=vec4(direct,indirect,direct+indirect,1);',start)
    source=source[:start]+'    float direct=direct_light(pos,normal,prim);\n'+BLOCK+source[end:]
    source=source.replace('// Independent pixel path tracing: grey rho=1, opaque two-sided surfaces,',
                          '// Dense cache-free repository RC estimator control; NOT external production RC.\n// Grey rho=1, opaque two-sided surfaces,')
    a.out.parent.mkdir(parents=True,exist_ok=True)
    a.out.write_text(source)
