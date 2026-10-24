"""022 reversible exports/chunking and bounded private legacy-source overlays."""
from pathlib import Path
import hashlib
import re

ROOT=Path(__file__).resolve().parents[3]
PT=ROOT/'shaders/research/n010_comparison_readiness/n010_pixel_pt.comp.glsl'
CONTEXT=ROOT/'build/n009/src/research/n010_comparison_readiness/generated/n010_b002_vulkan.cpp'
HWRT=ROOT/'src/research/lane_n_end_to_end_renderer/imported/lane_b_traversal/b002_hwrt.cpp'
PINS={PT:'ddb81baa0b701f96d78ffe297db589290d3fe4c2d6965a4df655c47a4a23d1c2',CONTEXT:'7b71943e2f2a7c454123632eda90e227af68a7e3ed358115fc14bfc6b9f31a5a',HWRT:'d5cc17a8335b5821cd4d3d0a93755d9eca776c17fcaadfb707b72defdc07cfb3'}
EXPORTS='''layout(std430,binding=4) writeonly buffer Primary { uint hits[]; };
layout(std430,binding=5) writeonly buffer Source { float sources[]; };
'''
CHUNK='''    uint id=pc.reserved+gl_GlobalInvocationID.x;
    if(id>=p.counts.y*p.counts.z || gl_GlobalInvocationID.x>=128u) return;
    uvec2 px=uvec2(id%p.counts.y,id/p.counts.y);'''
OLD_PIXEL='''    uvec2 px=gl_GlobalInvocationID.xy;
    if(px.x>=p.counts.y || px.y>=p.counts.z) return;
    uint id=px.y*p.counts.y+px.x;'''
MISS='''        for(uint a=0u;a<8u;a++) hits[id*8u+a]=0u;
        hits[id*8u+3u]=0x7f800000u;
        hits[id*8u+4u]=hits[id*8u+5u]=hits[id*8u+6u]=INVALID;
        sources[id]=0.0;
'''
HIT='''    hits[id*8u]=floatBitsToUint(normal.x);hits[id*8u+1u]=floatBitsToUint(normal.y);hits[id*8u+2u]=floatBitsToUint(normal.z);
    hits[id*8u+3u]=floatBitsToUint(primary_t);
    hits[id*8u+4u]=triangles[prim].metadata.x;hits[id*8u+5u]=triangles[prim].metadata.y;hits[id*8u+6u]=triangles[prim].metadata.z;hits[id*8u+7u]=1u;
'''


def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def once(text,old,new):
    if text.count(old)!=1:raise ValueError('022 nonunique overlay anchor: '+old[:80])
    return text.replace(old,new)


def producer(raw):
    if hashlib.sha256(raw).hexdigest()!=PINS[PT]:raise ValueError('022 original PT source differs')
    changes=[('layout(local_size_x=8, local_size_y=8) in;','layout(local_size_x=32) in;'),
             ('layout(binding=1) uniform accelerationStructureEXT top_level;',EXPORTS+'layout(binding=1) uniform accelerationStructureEXT top_level;'),
             ('out uint primitive, out vec3 position, out vec3 normal)','out uint primitive, out vec3 position, out vec3 normal, out float hit_t)'),
             ('    primitive=uint(rayQueryGetIntersectionPrimitiveIndexEXT(q,true));','    hit_t=rayQueryGetIntersectionTEXT(q,true);\n    primitive=uint(rayQueryGetIntersectionPrimitiveIndexEXT(q,true));'),
             (OLD_PIXEL,CHUNK),('    uint prim; vec3 pos,normal;','    uint prim; vec3 pos,normal; float primary_t;'),
             ('INVALID,prim,pos,normal))','INVALID,prim,pos,normal,primary_t))'),
             ('        pixels[id]=vec4(0,0,0,1); return;',MISS+'        pixels[id]=vec4(0,0,0,1); return;'),
             ('    float direct=direct_light(pos,normal,prim), sum_indirect=0.0;',HIT+'    float direct=direct_light(pos,normal,prim), sum_indirect=0.0;'),
             ('            vec3 wi=cosine_direction(n), next_position,next_normal; uint next_primitive;','            vec3 wi=cosine_direction(n), next_position,next_normal; uint next_primitive; float continuation_t;'),
             ('self,next_primitive,next_position,next_normal))','self,next_primitive,next_position,next_normal,continuation_t))'),
             ('    pixels[id]=vec4(direct,indirect,direct+indirect,1);','    sources[id]=indirect;\n    pixels[id]=vec4(direct,indirect,direct+indirect,1);')]
    text=raw.decode()
    for old,new in changes:text=once(text,old,new)
    restored=text
    for old,new in reversed(changes):restored=once(restored,new,old)
    if restored.encode()!=raw:raise ValueError('022 inverse PT overlay differs')
    return text.encode()


def bounded(raw,kind):
    path={'context':CONTEXT,'hwrt':HWRT}[kind]
    if hashlib.sha256(raw).hexdigest()!=PINS[path]:raise ValueError('022 original legacy source differs')
    changes=[('#include "b002_'+('vulkan' if kind=='context' else 'hwrt')+'.hpp"','#include "integrated_safety.hpp"\n#include "b002_'+('vulkan' if kind=='context' else 'hwrt')+'.hpp"')]
    text=raw.decode();matches=list(re.finditer(r'if \((?:dispatch_|context_\.vk\(\))\.?\.?waitForFences\([\s\S]*?UINT64_MAX\) != VK_SUCCESS\) \{',text))
    expected=1 if kind=='context' else 2
    if len(matches)!=expected:raise ValueError('022 legacy wait count differs')
    for index,match in enumerate(matches):
        old=match.group()
        # Build and trace share the same wait header; retain their distinct
        # following diagnostic so each reversible anchor is unique.
        suffix=('\n        fail("B002 HWRT '+('build' if index==0 else 'trace')+' wait");') if kind=='hwrt' else ''
        changes.append((old+suffix,old.replace('UINT64_MAX','250000000ull')+'\n        m022::incomplete_fence("legacy-'+kind+'");'+suffix))
    if kind=='context':
        changes += [('    if (dispatch_.allocateMemory(','    m022::reserve(allocation_info.allocationSize);\n    if (dispatch_.allocateMemory('),
                    ('        phos::gi::research::n010::AllocationLedger::instance().release(device(), buffer.memory);','        phos::gi::research::n010::AllocationLedger::instance().release(device(), buffer.memory);\n        m022::release(buffer.allocation_size);')]
    for old,new in changes:text=once(text,old,new)
    restored=text
    for old,new in reversed(changes):restored=once(restored,new,old)
    if restored.encode()!=raw or 'UINT64_MAX' in text:raise ValueError('022 inverse/bounded legacy overlay differs')
    return text.encode()
