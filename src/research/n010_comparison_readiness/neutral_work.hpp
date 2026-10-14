#pragma once
// Calibration-only known work; image and transport buffers are inaccessible.
#include "i001_compute.hpp"
#include <array>
#include <cstdlib>
#include <fstream>
#include <filesystem>
#include <memory>
namespace phos::gi::research::n010 {
class NeutralWork {
public:
    explicit NeutralWork(lane_b::B002VulkanContext& context):context_(context) {
        scratch_=context_.create_device_buffer(16384U*4U,VK_BUFFER_USAGE_STORAGE_BUFFER_BIT);
        const std::array<integration::I001Binding,1> binding{{{0,VK_DESCRIPTOR_TYPE_STORAGE_BUFFER,&scratch_}}};
        stage_=std::make_unique<integration::I001ComputeStage>(context_,std::string(PHOS_GI_INTEGRATION_SHADER_DIR)+"/n010_neutral_work.spv",binding,8);
    }
    ~NeutralWork() {stage_.reset();context_.destroy_buffer(scratch_);}
    void record(VkCommandBuffer command) const {
        const char* value=std::getenv("PHOS_N010_CALIBRATION_DOSE");
        const auto dose=value ? std::stoul(value) : 0UL;
        if(dose>10000000UL) throw std::runtime_error("calibration dose exceeds bound");
        const std::array<uint32_t,2> push{16384U,uint32_t(dose)};
        stage_->record(command,256,1,1,push.data(),sizeof(push));
        integration::i001_compute_barrier(context_,command);
    }
    void save(const std::filesystem::path& path) const {
        std::array<uint32_t,16384> data{};
        context_.download_device_buffer(scratch_,data.data(),sizeof(data));
        std::ofstream out(path,std::ios::binary);out.write(reinterpret_cast<const char*>(data.data()),sizeof(data));
        if(!out)throw std::runtime_error("calibration scratch write failed");
    }
private:
    lane_b::B002VulkanContext& context_;
    lane_b::B002Buffer scratch_{};
    std::unique_ptr<integration::I001ComputeStage> stage_;
};
}
