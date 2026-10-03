#include "a001_runtime.hpp"
#include "vk_init.hpp"

#include <algorithm>
#include <array>
#include <cmath>
#include <cstring>
#include <filesystem>
#include <limits>
#include <stdexcept>
#include <string>

namespace phos::gi::lane_a {
namespace {

struct V3 { float x{}, y{}, z{}; };
V3 add(V3 a, V3 b) { return {a.x+b.x, a.y+b.y, a.z+b.z}; }
V3 sub(V3 a, V3 b) { return {a.x-b.x, a.y-b.y, a.z-b.z}; }
V3 mul(V3 a, float s) { return {a.x*s, a.y*s, a.z*s}; }
float dot(V3 a, V3 b) { return a.x*b.x + a.y*b.y + a.z*b.z; }
V3 cross(V3 a, V3 b) { return {a.y*b.z-a.z*b.y, a.z*b.x-a.x*b.z, a.x*b.y-a.y*b.x}; }
float length(V3 v) { return std::sqrt(dot(v,v)); }
V3 normalize(V3 v) { const float l=length(v); return l>1e-12f ? mul(v,1.0f/l) : V3{}; }

[[noreturn]] void fail(const char* what) { throw std::runtime_error(what); }
std::uint32_t groups(std::uint32_t count) { return (count + 63u) / 64u; }

VkBufferMemoryBarrier buffer_barrier(const GpuBuffer& buffer, VkAccessFlags src, VkAccessFlags dst) {
    auto b = detail::make_vk_info<VkBufferMemoryBarrier>(VK_STRUCTURE_TYPE_BUFFER_MEMORY_BARRIER);
    b.srcAccessMask = src;
    b.dstAccessMask = dst;
    b.srcQueueFamilyIndex = VK_QUEUE_FAMILY_IGNORED;
    b.dstQueueFamilyIndex = VK_QUEUE_FAMILY_IGNORED;
    b.buffer = buffer.buffer;
    b.offset = 0;
    b.size = buffer.size;
    return b;
}

} // namespace

const char* case_name(A001Case value) {
    switch (value) {
    case A001Case::Static: return "static";
    case A001Case::CameraMotion: return "camera-motion";
    case A001Case::LightMotion: return "light-motion";
    }
    return "unknown";
}

A001ParamsGpu build_a001_params(const SceneSurfaceSet& scene, const A001Settings& settings) {
    if (scene.samples.empty()) throw std::runtime_error("A001 scene is empty");
    if (settings.tile_width == 0 || settings.tile_height == 0 ||
        settings.cascade_count == 0 || settings.cascade_count > 16 ||
        settings.rays_per_probe != 8) {
        throw std::runtime_error(
            "A001 requires positive dimensions, <=16 cascades, and exactly 8 rays/probe for schema v1");
    }

    const V3 bmin{scene.min_position[0],scene.min_position[1],scene.min_position[2]};
    const V3 bmax{scene.max_position[0],scene.max_position[1],scene.max_position[2]};
    const V3 center=mul(add(bmin,bmax),0.5f);
    const float diagonal=std::max(length(sub(bmax,bmin)),1.0f);
    float orbit=0.0f;
    if (settings.case_id == A001Case::CameraMotion) orbit=0.35f;
    const V3 base=normalize({1.0f,0.32f,1.0f});
    const float co=std::cos(orbit), si=std::sin(orbit);
    const V3 offset{base.x*co-base.z*si,base.y,base.x*si+base.z*co};
    const V3 eye=add(center,mul(offset,diagonal*0.82f));
    const V3 forward=normalize(sub(center,eye));
    V3 right=normalize(cross(forward,{0.0f,1.0f,0.0f}));
    if (length(right)<1e-5f) right={1.0f,0.0f,0.0f};
    const V3 up=normalize(cross(right,forward));
    V3 light=add(center,{diagonal*0.15f,diagonal*0.35f,diagonal*0.10f});
    if (settings.case_id == A001Case::LightMotion)
        light=add(center,{-diagonal*0.30f,diagonal*0.22f,diagonal*0.28f});

    const std::uint64_t tile_count=std::uint64_t(settings.tile_width)*settings.tile_height;
    const std::uint64_t max_outputs=tile_count*settings.cascade_count;
    const std::uint64_t max_work=max_outputs*settings.rays_per_probe;
    if (max_work > std::numeric_limits<std::uint32_t>::max() ||
        scene.samples.size() > std::numeric_limits<std::uint32_t>::max())
        throw std::runtime_error("A001 exceeds 32-bit producer capacity");

    A001ParamsGpu p{};
    p.camera_pos_near[0]=eye.x; p.camera_pos_near[1]=eye.y; p.camera_pos_near[2]=eye.z;
    p.camera_pos_near[3]=diagonal*0.001f;
    const float tan_y=std::tan(70.0f*3.14159265358979323846f/360.0f);
    p.camera_right_tan_x[0]=right.x; p.camera_right_tan_x[1]=right.y; p.camera_right_tan_x[2]=right.z;
    p.camera_right_tan_x[3]=tan_y*(float(settings.tile_width)/float(settings.tile_height));
    p.camera_up_tan_y[0]=up.x; p.camera_up_tan_y[1]=up.y; p.camera_up_tan_y[2]=up.z; p.camera_up_tan_y[3]=tan_y;
    p.camera_forward_far[0]=forward.x; p.camera_forward_far[1]=forward.y; p.camera_forward_far[2]=forward.z;
    p.camera_forward_far[3]=diagonal*3.0f;
    p.scene_origin_spacing[0]=bmin.x; p.scene_origin_spacing[1]=bmin.y; p.scene_origin_spacing[2]=bmin.z;
    p.scene_origin_spacing[3]=diagonal/64.0f;
    p.light_pos_interval[0]=light.x; p.light_pos_interval[1]=light.y; p.light_pos_interval[2]=light.z;
    p.light_pos_interval[3]=diagonal/128.0f;
    p.counts[0]=static_cast<std::uint32_t>(scene.samples.size());
    p.counts[1]=settings.tile_width; p.counts[2]=settings.tile_height; p.counts[3]=settings.cascade_count;
    p.limits[0]=settings.rays_per_probe; p.limits[1]=static_cast<std::uint32_t>(max_work);
    p.limits[2]=static_cast<std::uint32_t>(max_outputs); p.limits[3]=settings.frame_id;
    return p;
}

struct A001Runtime::Impl {
    VulkanContext& ctx;
    A001ParamsGpu params{};
    std::uint32_t tile_count{};
    std::uint32_t max_work{};
    std::uint32_t max_outputs{};

    GpuBuffer surfaces, depth, counters, work, contributions, accum, resolved, indirect, owners, uniform;
    VkDescriptorSetLayout descriptor_layout{VK_NULL_HANDLE};
    VkPipelineLayout pipeline_layout{VK_NULL_HANDLE};
    VkDescriptorPool descriptor_pool{VK_NULL_HANDLE};
    VkDescriptorSet descriptor_set{VK_NULL_HANDLE};
    std::array<VkPipeline,7> pipelines{};
    VkCommandPool command_pool{VK_NULL_HANDLE};
    VkCommandBuffer command_buffer{VK_NULL_HANDLE};
    VkQueryPool query_pool{VK_NULL_HANDLE};
    VkFence fence{VK_NULL_HANDLE};

    Impl(VulkanContext& c, const SceneSurfaceSet& scene, const A001ParamsGpu& p)
        : ctx(c), params(p) {
        tile_count=params.counts[1]*params.counts[2];
        max_work=params.limits[1];
        max_outputs=params.limits[2];

        std::vector<std::array<float,4>> positions(scene.samples.size());
        for (std::size_t i=0;i<scene.samples.size();++i)
            std::copy_n(scene.samples[i].position,4,positions[i].data());

        surfaces=ctx.upload_device_buffer(
            positions.data(),positions.size()*sizeof(positions[0]),
            VK_BUFFER_USAGE_STORAGE_BUFFER_BIT);
        depth=ctx.create_device_buffer(VkDeviceSize(tile_count)*4,VK_BUFFER_USAGE_STORAGE_BUFFER_BIT);
        counters=ctx.create_device_buffer(16,VK_BUFFER_USAGE_STORAGE_BUFFER_BIT);
        work=ctx.create_device_buffer(
            VkDeviceSize(max_work)*sizeof(SplitRcWorkItemV1),VK_BUFFER_USAGE_STORAGE_BUFFER_BIT);
        contributions=ctx.create_device_buffer(
            VkDeviceSize(max_work)*sizeof(std::uint32_t)*2,VK_BUFFER_USAGE_STORAGE_BUFFER_BIT);
        accum=ctx.create_device_buffer(
            VkDeviceSize(max_outputs)*sizeof(std::uint32_t)*2,VK_BUFFER_USAGE_STORAGE_BUFFER_BIT);
        resolved=ctx.create_device_buffer(
            VkDeviceSize(max_outputs)*sizeof(float),VK_BUFFER_USAGE_STORAGE_BUFFER_BIT);
        indirect=ctx.create_device_buffer(
            6*sizeof(std::uint32_t),
            VK_BUFFER_USAGE_STORAGE_BUFFER_BIT|VK_BUFFER_USAGE_INDIRECT_BUFFER_BIT);
        owners=ctx.create_device_buffer(
            VkDeviceSize(tile_count)*4,VK_BUFFER_USAGE_STORAGE_BUFFER_BIT);
        uniform=ctx.create_host_buffer(sizeof(A001ParamsGpu),VK_BUFFER_USAGE_UNIFORM_BUFFER_BIT);
        std::memcpy(uniform.mapped,&params,sizeof(params));

        init_descriptors();

        const std::array<const char*,7> names{{
            "lane_a_visibility_depth.spv",
            "lane_a_visibility_owner.spv",
            "lane_a_producer.spv",
            "lane_a_finalize.spv",
            "lane_a_gather.spv",
            "lane_a_merge.spv",
            "lane_a_resolve.spv",
        }};
        for (std::size_t i=0;i<names.size();++i) pipelines[i]=make_pipeline(names[i]);

        auto pci=detail::make_vk_info<VkCommandPoolCreateInfo>(
            VK_STRUCTURE_TYPE_COMMAND_POOL_CREATE_INFO);
        pci.flags=VK_COMMAND_POOL_CREATE_RESET_COMMAND_BUFFER_BIT;
        pci.queueFamilyIndex=ctx.queue_family();
        if(ctx.vk().createCommandPool(&pci,nullptr,&command_pool)!=VK_SUCCESS)
            fail("A001 command pool");

        auto cai=detail::make_vk_info<VkCommandBufferAllocateInfo>(
            VK_STRUCTURE_TYPE_COMMAND_BUFFER_ALLOCATE_INFO);
        cai.commandPool=command_pool;
        cai.level=VK_COMMAND_BUFFER_LEVEL_PRIMARY;
        cai.commandBufferCount=1;
        if(ctx.vk().allocateCommandBuffers(&cai,&command_buffer)!=VK_SUCCESS)
            fail("A001 command buffer");

        auto qpi=detail::make_vk_info<VkQueryPoolCreateInfo>(
            VK_STRUCTURE_TYPE_QUERY_POOL_CREATE_INFO);
        qpi.queryType=VK_QUERY_TYPE_TIMESTAMP;
        qpi.queryCount=8;
        if(ctx.vk().createQueryPool(&qpi,nullptr,&query_pool)!=VK_SUCCESS)
            fail("A001 query pool");

        auto fi=detail::make_vk_info<VkFenceCreateInfo>(
            VK_STRUCTURE_TYPE_FENCE_CREATE_INFO);
        if(ctx.vk().createFence(&fi,nullptr,&fence)!=VK_SUCCESS)
            fail("A001 fence");
    }

    ~Impl(){
        ctx.vk().deviceWaitIdle();
        if(fence) ctx.vk().destroyFence(fence,nullptr);
        if(query_pool) ctx.vk().destroyQueryPool(query_pool,nullptr);
        if(command_pool) ctx.vk().destroyCommandPool(command_pool,nullptr);
        for(auto p:pipelines) if(p) ctx.vk().destroyPipeline(p,nullptr);
        if(descriptor_pool) ctx.vk().destroyDescriptorPool(descriptor_pool,nullptr);
        if(pipeline_layout) ctx.vk().destroyPipelineLayout(pipeline_layout,nullptr);
        if(descriptor_layout) ctx.vk().destroyDescriptorSetLayout(descriptor_layout,nullptr);
        ctx.destroy_buffer(uniform);
        ctx.destroy_buffer(owners);
        ctx.destroy_buffer(indirect);
        ctx.destroy_buffer(resolved);
        ctx.destroy_buffer(accum);
        ctx.destroy_buffer(contributions);
        ctx.destroy_buffer(work);
        ctx.destroy_buffer(counters);
        ctx.destroy_buffer(depth);
        ctx.destroy_buffer(surfaces);
    }

    void init_descriptors(){
        std::array<VkDescriptorSetLayoutBinding,10> bindings{};
        for(std::uint32_t i=0;i<9;++i){
            bindings[i].binding=i;
            bindings[i].descriptorType=VK_DESCRIPTOR_TYPE_STORAGE_BUFFER;
            bindings[i].descriptorCount=1;
            bindings[i].stageFlags=VK_SHADER_STAGE_COMPUTE_BIT;
        }
        bindings[9].binding=9;
        bindings[9].descriptorType=VK_DESCRIPTOR_TYPE_UNIFORM_BUFFER;
        bindings[9].descriptorCount=1;
        bindings[9].stageFlags=VK_SHADER_STAGE_COMPUTE_BIT;

        auto dli=detail::make_vk_info<VkDescriptorSetLayoutCreateInfo>(
            VK_STRUCTURE_TYPE_DESCRIPTOR_SET_LAYOUT_CREATE_INFO);
        dli.bindingCount=static_cast<std::uint32_t>(bindings.size());
        dli.pBindings=bindings.data();
        if(ctx.vk().createDescriptorSetLayout(&dli,nullptr,&descriptor_layout)!=VK_SUCCESS)
            fail("A001 descriptor layout");

        auto pli=detail::make_vk_info<VkPipelineLayoutCreateInfo>(
            VK_STRUCTURE_TYPE_PIPELINE_LAYOUT_CREATE_INFO);
        pli.setLayoutCount=1;
        pli.pSetLayouts=&descriptor_layout;
        if(ctx.vk().createPipelineLayout(&pli,nullptr,&pipeline_layout)!=VK_SUCCESS)
            fail("A001 pipeline layout");

        std::array<VkDescriptorPoolSize,2> sizes{{
            {VK_DESCRIPTOR_TYPE_STORAGE_BUFFER,9},
            {VK_DESCRIPTOR_TYPE_UNIFORM_BUFFER,1},
        }};
        auto dpi=detail::make_vk_info<VkDescriptorPoolCreateInfo>(
            VK_STRUCTURE_TYPE_DESCRIPTOR_POOL_CREATE_INFO);
        dpi.maxSets=1;
        dpi.poolSizeCount=static_cast<std::uint32_t>(sizes.size());
        dpi.pPoolSizes=sizes.data();
        if(ctx.vk().createDescriptorPool(&dpi,nullptr,&descriptor_pool)!=VK_SUCCESS)
            fail("A001 descriptor pool");

        auto ai=detail::make_vk_info<VkDescriptorSetAllocateInfo>(
            VK_STRUCTURE_TYPE_DESCRIPTOR_SET_ALLOCATE_INFO);
        ai.descriptorPool=descriptor_pool;
        ai.descriptorSetCount=1;
        ai.pSetLayouts=&descriptor_layout;
        if(ctx.vk().allocateDescriptorSets(&ai,&descriptor_set)!=VK_SUCCESS)
            fail("A001 descriptor set");

        std::array<const GpuBuffer*,10> bu{{
            &surfaces,&depth,&counters,&work,&contributions,
            &accum,&resolved,&indirect,&owners,&uniform,
        }};
        std::array<VkDescriptorBufferInfo,10> infos{};
        std::array<VkWriteDescriptorSet,10> writes{};
        for(std::uint32_t i=0;i<10;++i){
            infos[i]={bu[i]->buffer,0,bu[i]->size};
            writes[i]=detail::make_vk_info<VkWriteDescriptorSet>(
                VK_STRUCTURE_TYPE_WRITE_DESCRIPTOR_SET);
            writes[i].dstSet=descriptor_set;
            writes[i].dstBinding=i;
            writes[i].descriptorCount=1;
            writes[i].descriptorType=
                i==9 ? VK_DESCRIPTOR_TYPE_UNIFORM_BUFFER : VK_DESCRIPTOR_TYPE_STORAGE_BUFFER;
            writes[i].pBufferInfo=&infos[i];
        }
        ctx.vk().updateDescriptorSets(
            static_cast<std::uint32_t>(writes.size()),writes.data(),0,nullptr);
    }

    VkPipeline make_pipeline(const std::string& filename){
        auto code=read_binary_file(
            (std::filesystem::path(PHOS_GI_LANE_A_SHADER_DIR)/filename).string());

        auto smi=detail::make_vk_info<VkShaderModuleCreateInfo>(
            VK_STRUCTURE_TYPE_SHADER_MODULE_CREATE_INFO);
        smi.codeSize=code.size();
        smi.pCode=reinterpret_cast<const std::uint32_t*>(code.data());
        VkShaderModule module{};
        if(ctx.vk().createShaderModule(&smi,nullptr,&module)!=VK_SUCCESS)
            fail("A001 shader module");

        auto stage=detail::make_vk_info<VkPipelineShaderStageCreateInfo>(
            VK_STRUCTURE_TYPE_PIPELINE_SHADER_STAGE_CREATE_INFO);
        stage.stage=VK_SHADER_STAGE_COMPUTE_BIT;
        stage.module=module;
        stage.pName="main";

        auto ci=detail::make_vk_info<VkComputePipelineCreateInfo>(
            VK_STRUCTURE_TYPE_COMPUTE_PIPELINE_CREATE_INFO);
        ci.stage=stage;
        ci.layout=pipeline_layout;

        VkPipeline p{};
        const auto result=ctx.vk().createComputePipelines(
            VK_NULL_HANDLE,1,&ci,nullptr,&p);
        ctx.vk().destroyShaderModule(module,nullptr);
        if(result!=VK_SUCCESS) fail("A001 compute pipeline");
        return p;
    }

    void bind(VkPipeline p){
        ctx.vk().cmdBindPipeline(
            command_buffer,VK_PIPELINE_BIND_POINT_COMPUTE,p);
        ctx.vk().cmdBindDescriptorSets(
            command_buffer,VK_PIPELINE_BIND_POINT_COMPUTE,pipeline_layout,
            0,1,&descriptor_set,0,nullptr);
    }

    void sync_compute(const GpuBuffer& b){
        auto x=buffer_barrier(
            b,VK_ACCESS_SHADER_WRITE_BIT,
            VK_ACCESS_SHADER_READ_BIT|VK_ACCESS_SHADER_WRITE_BIT);
        ctx.vk().cmdPipelineBarrier(
            command_buffer,
            VK_PIPELINE_STAGE_COMPUTE_SHADER_BIT,
            VK_PIPELINE_STAGE_COMPUTE_SHADER_BIT,
            0,0,nullptr,1,&x,0,nullptr);
    }

    std::array<std::uint64_t,8> run(bool read_timestamps){
        ctx.vk().resetCommandBuffer(command_buffer,0);

        auto bi=detail::make_vk_info<VkCommandBufferBeginInfo>(
            VK_STRUCTURE_TYPE_COMMAND_BUFFER_BEGIN_INFO);
        bi.flags=VK_COMMAND_BUFFER_USAGE_ONE_TIME_SUBMIT_BIT;
        if(ctx.vk().beginCommandBuffer(command_buffer,&bi)!=VK_SUCCESS)
            fail("A001 begin command buffer");

        ctx.vk().cmdResetQueryPool(command_buffer,query_pool,0,8);
        ctx.vk().cmdWriteTimestamp(
            command_buffer,VK_PIPELINE_STAGE_TOP_OF_PIPE_BIT,query_pool,0);

        ctx.vk().cmdFillBuffer(command_buffer,depth.buffer,0,depth.size,0x7f800000u);
        ctx.vk().cmdFillBuffer(command_buffer,owners.buffer,0,owners.size,0xffffffffu);
        ctx.vk().cmdFillBuffer(command_buffer,counters.buffer,0,counters.size,0u);
        ctx.vk().cmdFillBuffer(command_buffer,accum.buffer,0,accum.size,0u);

        std::array<VkBufferMemoryBarrier,4> clears{{
            buffer_barrier(depth,VK_ACCESS_TRANSFER_WRITE_BIT,
                VK_ACCESS_SHADER_READ_BIT|VK_ACCESS_SHADER_WRITE_BIT),
            buffer_barrier(owners,VK_ACCESS_TRANSFER_WRITE_BIT,
                VK_ACCESS_SHADER_READ_BIT|VK_ACCESS_SHADER_WRITE_BIT),
            buffer_barrier(counters,VK_ACCESS_TRANSFER_WRITE_BIT,
                VK_ACCESS_SHADER_READ_BIT|VK_ACCESS_SHADER_WRITE_BIT),
            buffer_barrier(accum,VK_ACCESS_TRANSFER_WRITE_BIT,
                VK_ACCESS_SHADER_READ_BIT|VK_ACCESS_SHADER_WRITE_BIT),
        }};
        ctx.vk().cmdPipelineBarrier(
            command_buffer,
            VK_PIPELINE_STAGE_TRANSFER_BIT,
            VK_PIPELINE_STAGE_COMPUTE_SHADER_BIT,
            0,0,nullptr,
            static_cast<std::uint32_t>(clears.size()),clears.data(),
            0,nullptr);

        bind(pipelines[0]);
        ctx.vk().cmdDispatch(command_buffer,groups(params.counts[0]),1,1);
        sync_compute(depth);
        ctx.vk().cmdWriteTimestamp(
            command_buffer,VK_PIPELINE_STAGE_COMPUTE_SHADER_BIT,query_pool,1);

        bind(pipelines[1]);
        ctx.vk().cmdDispatch(command_buffer,groups(params.counts[0]),1,1);
        sync_compute(owners);
        ctx.vk().cmdWriteTimestamp(
            command_buffer,VK_PIPELINE_STAGE_COMPUTE_SHADER_BIT,query_pool,2);

        bind(pipelines[2]);
        ctx.vk().cmdDispatch(command_buffer,groups(params.counts[0]),1,1);
        sync_compute(counters);
        sync_compute(work);
        ctx.vk().cmdWriteTimestamp(
            command_buffer,VK_PIPELINE_STAGE_COMPUTE_SHADER_BIT,query_pool,3);

        bind(pipelines[3]);
        ctx.vk().cmdDispatch(command_buffer,1,1,1);
        auto indirect_ready=buffer_barrier(
            indirect,VK_ACCESS_SHADER_WRITE_BIT,VK_ACCESS_INDIRECT_COMMAND_READ_BIT);
        ctx.vk().cmdPipelineBarrier(
            command_buffer,
            VK_PIPELINE_STAGE_COMPUTE_SHADER_BIT,
            VK_PIPELINE_STAGE_DRAW_INDIRECT_BIT,
            0,0,nullptr,1,&indirect_ready,0,nullptr);
        ctx.vk().cmdWriteTimestamp(
            command_buffer,VK_PIPELINE_STAGE_COMPUTE_SHADER_BIT,query_pool,4);

        bind(pipelines[4]);
        ctx.vk().cmdDispatchIndirect(command_buffer,indirect.buffer,0);
        sync_compute(contributions);
        ctx.vk().cmdWriteTimestamp(
            command_buffer,VK_PIPELINE_STAGE_COMPUTE_SHADER_BIT,query_pool,5);

        bind(pipelines[5]);
        ctx.vk().cmdDispatchIndirect(command_buffer,indirect.buffer,0);
        sync_compute(accum);
        ctx.vk().cmdWriteTimestamp(
            command_buffer,VK_PIPELINE_STAGE_COMPUTE_SHADER_BIT,query_pool,6);

        bind(pipelines[6]);
        ctx.vk().cmdDispatchIndirect(
            command_buffer,indirect.buffer,3*sizeof(std::uint32_t));
        auto resolved_ready=buffer_barrier(
            resolved,VK_ACCESS_SHADER_WRITE_BIT,VK_ACCESS_TRANSFER_READ_BIT);
        ctx.vk().cmdPipelineBarrier(
            command_buffer,
            VK_PIPELINE_STAGE_COMPUTE_SHADER_BIT,
            VK_PIPELINE_STAGE_TRANSFER_BIT,
            0,0,nullptr,1,&resolved_ready,0,nullptr);
        ctx.vk().cmdWriteTimestamp(
            command_buffer,VK_PIPELINE_STAGE_BOTTOM_OF_PIPE_BIT,query_pool,7);

        if(ctx.vk().endCommandBuffer(command_buffer)!=VK_SUCCESS)
            fail("A001 end command buffer");

        ctx.vk().resetFences(1,&fence);
        auto si=detail::make_vk_info<VkSubmitInfo>(VK_STRUCTURE_TYPE_SUBMIT_INFO);
        si.commandBufferCount=1;
        si.pCommandBuffers=&command_buffer;
        if(ctx.vk().queueSubmit(ctx.queue(),1,&si,fence)!=VK_SUCCESS)
            fail("A001 submit");
        if(ctx.vk().waitForFences(1,&fence,VK_TRUE,UINT64_MAX)!=VK_SUCCESS)
            fail("A001 wait");

        std::array<std::uint64_t,8> ts{};
        if(read_timestamps &&
           ctx.vk().getQueryPoolResults(
               query_pool,0,8,sizeof(ts),ts.data(),sizeof(std::uint64_t),
               VK_QUERY_RESULT_64_BIT|VK_QUERY_RESULT_WAIT_BIT)!=VK_SUCCESS)
            fail("A001 timestamps");
        return ts;
    }
};

A001Runtime::A001Runtime(
    VulkanContext& c,const SceneSurfaceSet& s,const A001ParamsGpu& p)
    : impl_(std::make_unique<Impl>(c,s,p)) {}
A001Runtime::~A001Runtime()=default;

A001Timings A001Runtime::measure(std::uint32_t iterations){
    if(iterations==0) throw std::runtime_error("A001 iterations must be positive");
    for(int i=0;i<3;++i) impl_->run(false);

    std::array<double,9> sum{};
    for(std::uint32_t i=0;i<iterations;++i){
        const auto t=impl_->run(true);
        const auto us=[&](int a,int b){
            return double(t[b]-t[a])*impl_->ctx.timestamp_period_ns()/1000.0;
        };
        sum[0]+=us(0,1);
        sum[1]+=us(1,2);
        sum[2]+=us(2,3);
        sum[3]+=us(3,4);
        sum[4]+=us(0,4);
        sum[5]+=us(4,5);
        sum[6]+=us(5,6);
        sum[7]+=us(6,7);
        sum[8]+=us(0,7);
    }
    for(auto& v:sum) v/=double(iterations);

    return{
        sum[0],sum[1],sum[2],sum[3],sum[4],
        sum[5],sum[6],sum[7],sum[8],
    };
}

A001Readback A001Runtime::readback(){
    A001Readback out;
    impl_->ctx.download_device_buffer(
        impl_->counters,out.counters.data(),sizeof(out.counters));
    if(out.counters[0]>impl_->max_work || out.counters[1]>impl_->max_outputs)
        throw std::runtime_error("A001 GPU counters exceeded allocated capacity");

    out.tile_owner.resize(impl_->tile_count);
    impl_->ctx.download_device_buffer(
        impl_->owners,out.tile_owner.data(),
        VkDeviceSize(out.tile_owner.size())*sizeof(std::uint32_t));

    out.work_items.resize(out.counters[0]);
    if(!out.work_items.empty())
        impl_->ctx.download_device_buffer(
            impl_->work,out.work_items.data(),
            VkDeviceSize(out.work_items.size())*sizeof(SplitRcWorkItemV1));

    out.resolved.resize(out.counters[1]);
    if(!out.resolved.empty())
        impl_->ctx.download_device_buffer(
            impl_->resolved,out.resolved.data(),
            VkDeviceSize(out.resolved.size())*sizeof(float));
    return out;
}

A001Memory A001Runtime::memory() const {
    const auto& i=*impl_;
    const std::size_t persistent=i.surfaces.size+i.uniform.size+i.resolved.size;
    const std::size_t transient=
        i.depth.size+i.owners.size+i.counters.size+i.work.size+
        i.contributions.size+i.accum.size+i.indirect.size;
    return{
        persistent,
        transient,
        persistent+transient,
        static_cast<std::size_t>(i.work.size),
    };
}

} // namespace phos::gi::lane_a
