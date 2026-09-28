#include "cache_benchmark.hpp"
#include "vk_init.hpp"

#include <array>
#include <cstring>
#include <filesystem>
#include <stdexcept>

namespace phos::gi {
namespace {

struct PushConstants {
    std::uint32_t query_count;
    std::uint32_t mask_or_page_size;
    std::uint32_t lookup_limit;
    std::uint32_t pad;
};

[[noreturn]] void fail(const char* what) { throw std::runtime_error(what); }

} // namespace

CacheBenchmark::CacheBenchmark(VulkanContext& context) : ctx_(context) {
    std::array<VkDescriptorSetLayoutBinding, 4> bindings{};
    for (std::uint32_t i = 0; i < bindings.size(); ++i) {
        bindings[i].binding = i;
        bindings[i].descriptorType = VK_DESCRIPTOR_TYPE_STORAGE_BUFFER;
        bindings[i].descriptorCount = 1;
        bindings[i].stageFlags = VK_SHADER_STAGE_COMPUTE_BIT;
    }
    auto dli = detail::make_vk_info<VkDescriptorSetLayoutCreateInfo>(VK_STRUCTURE_TYPE_DESCRIPTOR_SET_LAYOUT_CREATE_INFO);
    dli.bindingCount = static_cast<std::uint32_t>(bindings.size());
    dli.pBindings = bindings.data();
    if (ctx_.vk().createDescriptorSetLayout(&dli, nullptr, &descriptor_layout_) != VK_SUCCESS) fail("descriptor layout");

    VkPushConstantRange pcr{VK_SHADER_STAGE_COMPUTE_BIT, 0, sizeof(PushConstants)};
    auto pli = detail::make_vk_info<VkPipelineLayoutCreateInfo>(VK_STRUCTURE_TYPE_PIPELINE_LAYOUT_CREATE_INFO);
    pli.setLayoutCount = 1;
    pli.pSetLayouts = &descriptor_layout_;
    pli.pushConstantRangeCount = 1;
    pli.pPushConstantRanges = &pcr;
    if (ctx_.vk().createPipelineLayout(&pli, nullptr, &pipeline_layout_) != VK_SUCCESS) fail("pipeline layout");

    hash_pipeline_ = create_pipeline("hash_lookup.spv");
    paged_pipeline_ = create_pipeline("paged_lookup.spv");

    VkDescriptorPoolSize ps{VK_DESCRIPTOR_TYPE_STORAGE_BUFFER, 4};
    auto dpi = detail::make_vk_info<VkDescriptorPoolCreateInfo>(VK_STRUCTURE_TYPE_DESCRIPTOR_POOL_CREATE_INFO);
    dpi.maxSets = 1;
    dpi.poolSizeCount = 1;
    dpi.pPoolSizes = &ps;
    if (ctx_.vk().createDescriptorPool(&dpi, nullptr, &descriptor_pool_) != VK_SUCCESS) fail("descriptor pool");

    auto cpi = detail::make_vk_info<VkCommandPoolCreateInfo>(VK_STRUCTURE_TYPE_COMMAND_POOL_CREATE_INFO);
    cpi.flags = VK_COMMAND_POOL_CREATE_RESET_COMMAND_BUFFER_BIT;
    cpi.queueFamilyIndex = ctx_.queue_family();
    if (ctx_.vk().createCommandPool(&cpi, nullptr, &command_pool_) != VK_SUCCESS) fail("command pool");

    auto cai = detail::make_vk_info<VkCommandBufferAllocateInfo>(VK_STRUCTURE_TYPE_COMMAND_BUFFER_ALLOCATE_INFO);
    cai.commandPool = command_pool_;
    cai.level = VK_COMMAND_BUFFER_LEVEL_PRIMARY;
    cai.commandBufferCount = 1;
    if (ctx_.vk().allocateCommandBuffers(&cai, &command_buffer_) != VK_SUCCESS) fail("command buffer");

    auto qpi = detail::make_vk_info<VkQueryPoolCreateInfo>(VK_STRUCTURE_TYPE_QUERY_POOL_CREATE_INFO);
    qpi.queryType = VK_QUERY_TYPE_TIMESTAMP;
    qpi.queryCount = 2;
    if (ctx_.vk().createQueryPool(&qpi, nullptr, &query_pool_) != VK_SUCCESS) fail("query pool");

    auto fi = detail::make_vk_info<VkFenceCreateInfo>(VK_STRUCTURE_TYPE_FENCE_CREATE_INFO);
    if (ctx_.vk().createFence(&fi, nullptr, &fence_) != VK_SUCCESS) fail("fence");
}

CacheBenchmark::~CacheBenchmark() {
    ctx_.vk().deviceWaitIdle();
    if (fence_) ctx_.vk().destroyFence(fence_, nullptr);
    if (query_pool_) ctx_.vk().destroyQueryPool(query_pool_, nullptr);
    if (command_pool_) ctx_.vk().destroyCommandPool(command_pool_, nullptr);
    if (descriptor_pool_) ctx_.vk().destroyDescriptorPool(descriptor_pool_, nullptr);
    if (hash_pipeline_) ctx_.vk().destroyPipeline(hash_pipeline_, nullptr);
    if (paged_pipeline_) ctx_.vk().destroyPipeline(paged_pipeline_, nullptr);
    if (pipeline_layout_) ctx_.vk().destroyPipelineLayout(pipeline_layout_, nullptr);
    if (descriptor_layout_) ctx_.vk().destroyDescriptorSetLayout(descriptor_layout_, nullptr);
}

VkPipeline CacheBenchmark::create_pipeline(const std::string& filename) {
    const auto path = std::filesystem::path(PHOS_GI_LAB_SHADER_DIR) / filename;
    auto code = read_binary_file(path.string());

    auto smi = detail::make_vk_info<VkShaderModuleCreateInfo>(VK_STRUCTURE_TYPE_SHADER_MODULE_CREATE_INFO);
    smi.codeSize = code.size();
    smi.pCode = reinterpret_cast<const std::uint32_t*>(code.data());

    VkShaderModule module{};
    if (ctx_.vk().createShaderModule(&smi, nullptr, &module) != VK_SUCCESS) fail("shader module");

    auto stage = detail::make_vk_info<VkPipelineShaderStageCreateInfo>(VK_STRUCTURE_TYPE_PIPELINE_SHADER_STAGE_CREATE_INFO);
    stage.stage = VK_SHADER_STAGE_COMPUTE_BIT;
    stage.module = module;
    stage.pName = "main";

    auto ci = detail::make_vk_info<VkComputePipelineCreateInfo>(VK_STRUCTURE_TYPE_COMPUTE_PIPELINE_CREATE_INFO);
    ci.stage = stage;
    ci.layout = pipeline_layout_;

    VkPipeline pipeline{};
    const auto result = ctx_.vk().createComputePipelines(VK_NULL_HANDLE, 1, &ci, nullptr, &pipeline);
    ctx_.vk().destroyShaderModule(module, nullptr);
    if (result != VK_SUCCESS) fail("compute pipeline");
    return pipeline;
}

GpuBuffer CacheBenchmark::upload(const void* data, std::size_t bytes) {
    return ctx_.upload_device_buffer(data, bytes, VK_BUFFER_USAGE_STORAGE_BUFFER_BIT);
}

std::vector<BenchmarkResult> CacheBenchmark::run(const Workload& w, std::uint32_t iterations) {
    const std::size_t hash_bytes =
        (w.hash_keys.size() + w.hash_payload.size()) * sizeof(std::uint32_t);
    const std::size_t paged_bytes =
        (w.page_table.size() + w.paged_payload.size()) * sizeof(std::uint32_t);

    std::vector<BenchmarkResult> out;
    out.push_back(run_variant(
        "hash", w.original, w.hash_keys, w.hash_payload, 0, w.hash_mask,
        w.hash_max_probe, iterations, hash_bytes, w.expected_checksum));
    out.push_back(run_variant(
        "paged", w.original, w.page_table, w.paged_payload, 1, w.page_size,
        1, iterations, paged_bytes, w.expected_checksum));
    out.push_back(run_variant(
        "paged-sorted", w.page_sorted, w.page_table, w.paged_payload, 1, w.page_size,
        1, iterations, paged_bytes, w.expected_checksum));
    return out;
}

BenchmarkResult CacheBenchmark::run_variant(
    const char* name,
    const std::vector<Query>& queries,
    const std::vector<std::uint32_t>& table0,
    const std::vector<std::uint32_t>& payload,
    std::uint32_t mode_value,
    std::uint32_t mask_or_page_size,
    std::uint32_t lookup_limit,
    std::uint32_t iterations,
    std::size_t logical_bytes,
    std::uint64_t expected_checksum) {

    auto qbuf = upload(queries.data(), queries.size() * sizeof(Query));
    auto tbuf = upload(table0.data(), table0.size() * sizeof(std::uint32_t));
    auto pbuf = upload(payload.data(), payload.size() * sizeof(std::uint32_t));
    auto obuf = ctx_.create_device_buffer(
        queries.size() * sizeof(std::uint32_t), VK_BUFFER_USAGE_STORAGE_BUFFER_BIT);

    ctx_.vk().resetDescriptorPool(descriptor_pool_, 0);

    VkDescriptorSet set{};
    auto ai = detail::make_vk_info<VkDescriptorSetAllocateInfo>(VK_STRUCTURE_TYPE_DESCRIPTOR_SET_ALLOCATE_INFO);
    ai.descriptorPool = descriptor_pool_;
    ai.descriptorSetCount = 1;
    ai.pSetLayouts = &descriptor_layout_;
    if (ctx_.vk().allocateDescriptorSets(&ai, &set) != VK_SUCCESS) fail("descriptor allocate");

    std::array<VkDescriptorBufferInfo, 4> infos{{
        {qbuf.buffer, 0, qbuf.size},
        {tbuf.buffer, 0, tbuf.size},
        {pbuf.buffer, 0, pbuf.size},
        {obuf.buffer, 0, obuf.size},
    }};

    std::array<VkWriteDescriptorSet, 4> writes{};
    for (std::uint32_t i = 0; i < writes.size(); ++i) {
        writes[i] = detail::make_vk_info<VkWriteDescriptorSet>(VK_STRUCTURE_TYPE_WRITE_DESCRIPTOR_SET);
        writes[i].dstSet = set;
        writes[i].dstBinding = i;
        writes[i].descriptorCount = 1;
        writes[i].descriptorType = VK_DESCRIPTOR_TYPE_STORAGE_BUFFER;
        writes[i].pBufferInfo = &infos[i];
    }
    ctx_.vk().updateDescriptorSets(
        static_cast<std::uint32_t>(writes.size()), writes.data(), 0, nullptr);

    ctx_.vk().resetCommandBuffer(command_buffer_, 0);

    auto bi = detail::make_vk_info<VkCommandBufferBeginInfo>(VK_STRUCTURE_TYPE_COMMAND_BUFFER_BEGIN_INFO);
    bi.flags = VK_COMMAND_BUFFER_USAGE_ONE_TIME_SUBMIT_BIT;
    ctx_.vk().beginCommandBuffer(command_buffer_, &bi);

    ctx_.vk().cmdResetQueryPool(command_buffer_, query_pool_, 0, 2);
    ctx_.vk().cmdBindPipeline(
        command_buffer_, VK_PIPELINE_BIND_POINT_COMPUTE,
        mode_value == 0 ? hash_pipeline_ : paged_pipeline_);
    ctx_.vk().cmdBindDescriptorSets(
        command_buffer_, VK_PIPELINE_BIND_POINT_COMPUTE, pipeline_layout_,
        0, 1, &set, 0, nullptr);

    PushConstants pc{
        static_cast<std::uint32_t>(queries.size()),
        mask_or_page_size,
        lookup_limit,
        0,
    };
    ctx_.vk().cmdPushConstants(
        command_buffer_, pipeline_layout_, VK_SHADER_STAGE_COMPUTE_BIT,
        0, sizeof(pc), &pc);

    const std::uint32_t groups = (pc.query_count + 255u) / 256u;

    for (std::uint32_t i = 0; i < 5u; ++i) {
        ctx_.vk().cmdDispatch(command_buffer_, groups, 1, 1);
    }

    ctx_.vk().cmdWriteTimestamp(
        command_buffer_, VK_PIPELINE_STAGE_COMPUTE_SHADER_BIT, query_pool_, 0);

    for (std::uint32_t i = 0; i < iterations; ++i) {
        ctx_.vk().cmdDispatch(command_buffer_, groups, 1, 1);
    }

    ctx_.vk().cmdWriteTimestamp(
        command_buffer_, VK_PIPELINE_STAGE_BOTTOM_OF_PIPE_BIT, query_pool_, 1);
    ctx_.vk().endCommandBuffer(command_buffer_);

    ctx_.vk().resetFences(1, &fence_);
    auto si = detail::make_vk_info<VkSubmitInfo>(VK_STRUCTURE_TYPE_SUBMIT_INFO);
    si.commandBufferCount = 1;
    si.pCommandBuffers = &command_buffer_;
    if (ctx_.vk().queueSubmit(ctx_.queue(), 1, &si, fence_) != VK_SUCCESS) fail("queue submit");
    ctx_.vk().waitForFences(1, &fence_, VK_TRUE, UINT64_MAX);

    std::array<std::uint64_t, 2> ts{};
    if (ctx_.vk().getQueryPoolResults(
            query_pool_, 0, 2, sizeof(ts), ts.data(), sizeof(std::uint64_t),
            VK_QUERY_RESULT_64_BIT | VK_QUERY_RESULT_WAIT_BIT) != VK_SUCCESS) {
        fail("timestamp results");
    }
    const double elapsed_ns =
        static_cast<double>(ts[1] - ts[0]) * ctx_.timestamp_period_ns();

    std::vector<std::uint32_t> downloaded(queries.size());
    ctx_.download_device_buffer(
        obuf, downloaded.data(), downloaded.size() * sizeof(std::uint32_t));

    std::uint64_t checksum = 0;
    for (const auto value : downloaded) checksum += value;

    const std::size_t pages = mode_value == 0 ? 0 : table0.size();
    BenchmarkResult result{
        name,
        queries.size(),
        pages,
        logical_bytes,
        elapsed_ns / 1000.0 / static_cast<double>(iterations),
        checksum,
        expected_checksum,
        checksum == expected_checksum,
    };

    ctx_.destroy_buffer(obuf);
    ctx_.destroy_buffer(pbuf);
    ctx_.destroy_buffer(tbuf);
    ctx_.destroy_buffer(qbuf);
    return result;
}

} // namespace phos::gi
