"""023 immutable sources and reversible physical producer guide exports."""
from pathlib import Path
import integrated_pt_overlay as O
ROOT=O.ROOT
EXTERNAL=ROOT/'out/research/n010-comparison-readiness/external'
PINS={'NRD-e06852bd':'e06852bd545973cb224eb28820b891205cfc1624','ShaderMake-3f01623a':'3f01623a76b092ac127d2debd79a672f55d77665','MathLib-aa432ad9':'aa432ad9a80691eb8c3ec4d576bbad5ac100fdc8'}
DXC=EXTERNAL/'dxc-v1.9.2609/package/bin/dxc'
ARCHIVE=EXTERNAL/'dxc-v1.9.2609/linux_dxc_2026_09_28.curl-v2.tar.gz'
ARCHIVE_SHA='96faadc7f5c282d2ffda49804beb4c3ee38127bc252b723234e3c5cdf7aa39a1'


def producer(raw):
    before=O.producer(raw).decode()
    changes=[(O.EXPORTS,O.EXPORTS+'layout(std430,binding=6) writeonly buffer Secondary { vec2 secondary[]; };\n'),
             ('        sources[id]=0.0;','        sources[id]=0.0;\n        secondary[id]=vec2(0.0);'),
             ('    rng=mix32(pc.seed^mix32(id));','    float secondary_sum=0.0;\n    rng=mix32(pc.seed^mix32(id));'),
             ('        float indirect=0.0;','        float indirect=0.0;\n        float first_secondary=65504.0;'),
             ('            indirect+=direct_light(next_position,next_normal,next_primitive);','            if(vertex==1u) first_secondary=clamp(continuation_t,0.0,65504.0);\n            indirect+=direct_light(next_position,next_normal,next_primitive);'),
             ('        sum_indirect+=indirect;','        secondary_sum+=first_secondary;\n        sum_indirect+=indirect;'),
             ('    sources[id]=indirect;','    sources[id]=indirect;\n    secondary[id]=vec2(secondary_sum,secondary_sum/float(pc.spp));')]
    result=before
    for old,new in changes:result=O.once(result,old,new)
    restored=result
    for old,new in reversed(changes):restored=O.once(restored,new,old)
    if restored!=before:raise ValueError('023 inverse secondary export differs')
    return result.encode()
