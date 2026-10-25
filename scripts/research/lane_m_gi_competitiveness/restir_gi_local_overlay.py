"""040 reversible receiver-local observations/host/SDK adapter derivatives."""
from pathlib import Path
import restir_gi_gpu_overlay as P
import restir_gi_gpu_include_correction as H
G=H.G


def apply(text,changes):
    original=text
    for a,b in changes:text=P.O.once(text,a,b)
    restored=text
    for a,b in reversed(changes):restored=P.O.once(restored,b,a)
    G.need(restored==original,'040 exact inverse')
    return text


def producer(raw):
    text=P.producer(raw).decode()
    return apply(text,[
        ('layout(std430,binding=7) buffer Candidates { Candidate candidates[]; };','layout(std430,binding=7) buffer Candidates { Candidate candidates[]; };\nlayout(std430,binding=8) buffer LocalEndpoints { vec4 local_endpoints[]; };'),
        ('    Candidate candidate=Candidate(', '    local_endpoints[id]=vec4(0);\n    Candidate candidate=Candidate('),
        ('candidate.endpoint_normal.xyz=next_normal;}', 'candidate.endpoint_normal.xyz=next_normal;local_endpoints[id]=vec4(continuation_t*wi,continuation_t);}')]).encode()


def host(raw):
    text=raw.decode()
    # Native execution, fences, paths and original physical witnesses stay exact.
    changes=[
        ('//037 standalone physical producer -> actual SDK Make/Pack -> GPU Unpack/image.','//040 receiver-local physical producer -> actual SDK Make/Pack -> GPU Unpack/image.'),
        ('std::array<b::B002Buffer,11> buffers{};std::array<std::uint64_t,11> sizes{};','std::array<b::B002Buffer,12> buffers{};std::array<std::uint64_t,12> sizes{};'),
        ('96ull*N,sizeof(state.params)};', '96ull*N,sizeof(state.params),16ull*N};'),
        ('for(u32 j=0;j<11;j++){\n            need(sizes[j]+256','for(u32 j=0;j<12;j++){\n            need(sizes[j]+256'),
        ('{7,VK_DESCRIPTOR_TYPE_STORAGE_BUFFER,&buffers[7]});}', '{7,VK_DESCRIPTOR_TYPE_STORAGE_BUFFER,&buffers[7]});bind.push_back({8,VK_DESCRIPTOR_TYPE_STORAGE_BUFFER,&buffers[11]});}'),
        ('std::array<i::I001Binding,4> bind', 'std::array<i::I001Binding,5> bind'),
        ('{3,VK_DESCRIPTOR_TYPE_ACCELERATION_STRUCTURE_KHR,nullptr,hwrt.top_level()}}};','{3,VK_DESCRIPTOR_TYPE_ACCELERATION_STRUCTURE_KHR,nullptr,hwrt.top_level()},{4,VK_DESCRIPTOR_TYPE_STORAGE_BUFFER,&buffers[11]}}};'),
        ('const std::array<const char*,11> names','const std::array<const char*,12> names'),
        ('"sdk-output.f32","params.bin"};','"sdk-output.f32","params.bin","local-endpoints.f32"};'),
        ('for(u32 j=0;j<11;j++){\n            auto* ptr', 'for(u32 j=0;j<12;j++){\n            auto* ptr'),
        ('maxPerStageDescriptorStorageBuffers>=6','maxPerStageDescriptorStorageBuffers>=7'),
    ]
    for seed in ('0x12345678u','0x9abcdef0u','0x89abcdefu','0x76543210u'):changes.append((seed+'^0xa037a037u',seed+'^0xa040a040u'))
    return apply(text,changes).encode()


def shader(raw):
    text=H.corrected(raw).decode()
    return apply(text,[
        ('//037 actual GPU-produced finite suffixes. SDK algorithms remain unchanged.','//040 actual finite suffixes, receiver-local ray-parametric positions; unmodified SDK.'),
        ('[[vk::binding(3,0)]] RaytracingAccelerationStructure topLevel;', '[[vk::binding(3,0)]] RaytracingAccelerationStructure topLevel;\n[[vk::binding(4,0)]] StructuredBuffer<float4> localEndpoints;'),
        ('bool visible(Candidate c) {','bool visible(Candidate c,float3 localEndpoint) {'),
        ('float3 delta=c.endpoint_primitive.xyz-c.origin_pdf.xyz;', 'float3 delta=localEndpoint;'),
        ('RTXDI_MakeGIReservoir(c.endpoint_primitive.xyz,c.endpoint_normal.xyz,c.radiance_trial.xyz,c.origin_pdf.w)', 'RTXDI_MakeGIReservoir(localEndpoints[pixel].xyz,c.endpoint_normal.xyz,c.radiance_trial.xyz,c.origin_pdf.w)'),
        ('float3 delta=r.position-c.origin_pdf.xyz;', 'float3 delta=r.position;'),
        ('hemi=dot(r.normal,c.origin_pdf.xyz-r.position)>0;', 'hemi=dot(r.normal,-r.position)>0;'),
        ('clear=visible(c);','clear=visible(c,r.position);')]).encode()
