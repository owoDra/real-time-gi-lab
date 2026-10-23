"""011 unique reversible overlays; original source/SDK files are never written."""
import hashlib

SDK_SHA = 'a8bc4622974926a6b4403b55609294ab55d423dfe3cb2ad14758ac9265eaa27e'
HOST_SHA = {
    'ddgi_scene_main.cpp': 'd90d4684c0798c89c7507224c723d3833e7888bdcc98c91ec72d429f7ff68e9a',
    'ddgi_transition_main.cpp': '40038261e350d4d06d494e4639412d77fcbad14a64ffc8a4f4af282211879713',
}
SDK_TAIL = '''    // Wait for all threads in the group to finish all memory operations
    AllMemoryBarrierWithGroupSync();

    // Update the texel with the latest blended data
    UpdateBorderTexel(DispatchThreadID, GroupThreadID, GroupID, Output, volume);'''
SDK_REPLACEMENT = '''    // M001/011 modified SDK: interior-only. Border copy is a separate dispatch.
    // No group barrier or cross-invocation image read occurs here.'''
KERNEL_ANCHOR = '    std::array<D::DDGIVolume,2> volumes;'
KERNEL_ADDITION = '''    auto border_irradiance=c.kernel(o.shaders/"border-irradiance.spv","CopyIrradianceBorder",c.sdk_layout);
    auto border_distance=c.kernel(o.shaders/"border-distance.spv","CopyDistanceBorder",c.sdk_layout);
'''
CAPTURE_ANCHOR = '        for(int j=0;j<4;++j)c.capture(current.images[j],staging,prefix+"-current-"+std::to_string(j));'
COPY_ADDITION = '''        // M001/011 proof captures occur after interior-only SDK blend, before copy.
        for(int j=1;j<=2;++j)c.capture(current.images[j],staging,prefix+"-pre-border-"+std::to_string(j));
        auto copy_border=[&](const Kernel& kernel,const char* suffix){
            c.dispatch(prefix+suffix,[&]{
                c.memory_barrier(VK_ACCESS_MEMORY_READ_BIT|VK_ACCESS_MEMORY_WRITE_BIT,VK_ACCESS_SHADER_READ_BIT|VK_ACCESS_SHADER_WRITE_BIT,VK_PIPELINE_STAGE_ALL_COMMANDS_BIT,VK_PIPELINE_STAGE_COMPUTE_SHADER_BIT);
                vkCmdBindPipeline(c.command,VK_PIPELINE_BIND_POINT_COMPUTE,kernel.pipeline);
                vkCmdBindDescriptorSets(c.command,VK_PIPELINE_BIND_POINT_COMPUTE,c.sdk_layout,0,1,&current.sdk_set,0,nullptr);
                vkCmdDispatch(c.command,o.side,o.side,o.side);
                c.memory_barrier(VK_ACCESS_SHADER_WRITE_BIT,VK_ACCESS_SHADER_READ_BIT|VK_ACCESS_SHADER_WRITE_BIT,VK_PIPELINE_STAGE_COMPUTE_SHADER_BIT,VK_PIPELINE_STAGE_COMPUTE_SHADER_BIT);
            });
        };
        copy_border(border_irradiance,"-border-irradiance");
        copy_border(border_distance,"-border-distance");
'''


def digest(source):
    return hashlib.sha256(source).hexdigest()


def replace_unique(source, before, after):
    if source.count(before) != 1 or after in source:
        raise ValueError('Ambiguous or already modified source overlay')
    result = source.replace(before, after)
    if result.count(after) != 1 or result.replace(after, before) != source:
        raise ValueError('Overlay inverse is not exact')
    return result


def interior_shader(source):
    if digest(source) != SDK_SHA:
        raise ValueError('Pinned original SDK shader differs')
    text = source.decode()
    result = replace_unique(text, SDK_TAIL, SDK_REPLACEMENT)
    if result.replace(SDK_REPLACEMENT, SDK_TAIL) != text:
        raise ValueError('SDK inverse mismatch')
    return result.encode()


def host(source, name):
    if name not in HOST_SHA or digest(source) != HOST_SHA[name]:
        raise ValueError('Pinned original host differs')
    text = source.decode()
    result = replace_unique(text, KERNEL_ANCHOR, KERNEL_ADDITION + KERNEL_ANCHOR)
    result = replace_unique(result, CAPTURE_ANCHOR, COPY_ADDITION + CAPTURE_ANCHOR)
    inverse = result.replace(COPY_ADDITION + CAPTURE_ANCHOR, CAPTURE_ANCHOR)
    inverse = inverse.replace(KERNEL_ADDITION + KERNEL_ANCHOR, KERNEL_ANCHOR)
    if inverse != text:
        raise ValueError('Host inverse mismatch')
    return result.encode()
