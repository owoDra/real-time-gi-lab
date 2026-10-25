"""033 independent full host-array and actual SPIR-V data/call/resource inspection."""
from pathlib import Path
import re
import numpy as np


def need(value,message):
    if not value:raise ValueError('033 independent audit: '+message)


def inspect(out,host):
    import restir_gi_source_build as R
    out=Path(out);states=host['states'];need(len(states)==2880,'full SDK state coverage')
    seen=set();arrays={};total=0;max_bytes=0
    for row in states:
        w,h,c,mode,frame,rp,ap,initial,ti,to,si,so,final,owned=row
        key=(w,h,c,mode,frame);need(key not in seen,'unique SDK states');seen.add(key)
        rw=(w+1)//2 if c else w
        need(rp==((rw+15)//16)*256 and ap==rp*((h+15)//16),'independent padded pitches')
        need(owned==ap*64,'complete TWO 32-byte arrays');max_bytes=max(owned,max_bytes)
        if mode==0:need((initial,final)==(0,0),'none routing')
        if mode==1:need((initial,ti,to,final)==(frame%2,1-frame%2,frame%2,frame%2),'temporal routing')
        if mode==2:need((initial,si,so,final)==(0,0,1,1),'spatial routing')
        if mode==3:need((initial,ti,to,si,so,final)==(0,1,0,0,1,1),'separate temporal/spatial routing')
        if mode==4:need((initial,ti,so,final)==(frame%2,1-frame%2,frame%2,frame%2),'fused routing')
    for w,h in ((1,1),(320,180),(321,181)):
        for checker in range(3):
            rw=(w+1)//2 if checker else w
            y,x=np.indices((h,rw),dtype=np.uint32);nblock=(rw+15)//16
            one=((y//16*nblock+x//16)*256+(y%16)*16+x%16).ravel()
            ap=nblock*((h+15)//16)*256;expected=np.concatenate((one,one+ap))
            path=out/'host-data'/f'addresses-{w}x{h}-{checker}.u32';actual=np.fromfile(path,'<u4')
            need(np.array_equal(expected,actual) and len(np.unique(actual))==len(actual),'ALL address maps/arrays no alias')
            need((actual<2*ap).all(),'complete bounds');total+=len(actual)
            arrays[f'address_error_{w}_{h}_{checker}']=actual.astype(np.int64)-expected
            for mode in range(5):
                for frame in range(64):need((w,h,checker,mode,frame) in seen,'no missing SDK state')
    need(total==host['address_count'],'full address coverage count')
    offsets=np.fromfile(out/'host-data/neighbor-offsets.u8',np.int8).reshape(8192,2).astype(np.int32)
    need((np.sum(offsets*offsets,axis=1)<=125**2).all(),'actual SDK signed-byte disk coverage')
    need((offsets.min(axis=0)<0).all() and (offsets.max(axis=0)>0).all(),'actual SDK all signed quadrants')
    arrays['neighbor_offsets_signed']=offsets
    required=[{0,1,3,5,9},{0,1,3,4,5,6,9},{0,1,3,4,5,6,9},{0,1,2,3,5,7,9},{0,1,2,3,5,7,9},{0,1,2,3,4,5,8,9}]
    shader_rows=[]
    for index,name in enumerate(R.PERMUTATIONS):
        text=(out/(name+'.spvasm')).read_text()
        entry=re.search(r'OpEntryPoint GLCompute (%\S+) "main"',text);need(entry is not None,'actual compute entrypoint')
        bindings={int(x) for x in re.findall(r'OpDecorate %\S+ Binding (\d+)',text)}
        need(required[index]<=bindings,'retained actual buffer/parameter dependencies')
        # The actual packed SDK structure's member offsets must match the host ABI.
        layouts={}
        for identity,member,offset in re.findall(r'OpMemberDecorate (%\S+) (\d+) Offset (\d+)',text):layouts.setdefault(identity,{})[int(member)]=int(offset)
        need(any([v.get(i) for i in range(6)]==[0,12,16,20,24,28] for v in layouts.values()),'actual SDK SPIR-V 32-byte packed member layout')
        need(re.search(r'OpDecorate %\S+ ArrayStride 32',text) is not None,'actual packed array stride')
        names=dict(re.findall(r'OpName (%\S+) "([^"]*)"',text));calls={};current=None
        for line in text.splitlines():
            match=re.search(r'(%\S+) = OpFunction ',line)
            if match:current=match[1];calls.setdefault(current,set())
            if current:
                match=re.search(r'OpFunctionCall %\S+ (%\S+)',line)
                if match:calls[current].add(match[1])
            if 'OpFunctionEnd' in line:current=None
        reachable=set();queue=[entry[1]]
        while queue:
            v=queue.pop()
            if v in reachable:continue
            reachable.add(v);queue.extend(calls.get(v,()))
        reached={names.get(v,v) for v in reachable}
        for symbol in ['RTXDI_MakeGIReservoir','RTXDI_PackGIReservoir','RTXDI_UnpackGIReservoir']:
            need(any(symbol in n for n in reached),'reachable SDK '+symbol)
        if index in (1,2):need(any('RTXDI_GISpatialResampling' in n for n in reached),'actual spatial SDK call')
        if index in (3,4):need(any('RTXDI_GITemporalResampling' in n for n in reached),'actual temporal SDK call')
        if index==5:need(any('RTXDI_GISpatioTemporalResampling' in n for n in reached),'actual fused SDK call')
        if index>0:
            need(any('RTXDI_CalculateJacobian' in n for n in reached),'actual SDK reconnection Jacobian')
            need(any('RTXDI_FinalizeGIResampling' in n for n in reached),'actual SDK normalization')
        if index in (4,5):need(any('RAB_GetTemporalConservativeVisibility' in n for n in reached),'previous geometry visibility hook retained')
        shader_rows.append(dict(name=name,entry=entry[1],bindings=sorted(bindings),reachable_functions=sorted(reached),packed_layout_agrees=True))
    np.savez(out/'full-independent-source-audit.npz',**arrays)
    proof=dict(complete=True,all_pass=True,actual_host_states=2880,address_maps=9,all_array_addresses=total,
               maximum_two_reservoir_buffer_bytes=max_bytes,neighbor_offsets=8192,shader_permutations=shader_rows,
               independent_all_address_and_routing_checks=True,actual_sdk_shader_calls_reachable=True,
               sdk_host_executed=True,sdk_shaders_executed=False,physical_rays_executed=False,
               quality_or_timing_qualified=False)
    R.C.write(out/'independent-audit.json',proof);return proof
