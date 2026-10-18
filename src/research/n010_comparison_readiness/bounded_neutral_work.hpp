#pragma once
// Standalone research fixture only. The bindings expose no image or GI state.
#include "i001_compute.hpp"
#include <array>
#include <cstdint>
#include <filesystem>
#include <fstream>
#include <memory>
#include <stdexcept>
#include <string>
namespace phos::gi::research::n010 {
class BoundedNeutralWork {
public:
    static constexpr uint32_t count=16384U,chunk=65536U,max_dose=100000000U;
    explicit BoundedNeutralWork(lane_b::B002VulkanContext& context):context_(context) {
        values_=context_.create_device_buffer(count*4U,VK_BUFFER_USAGE_STORAGE_BUFFER_BIT);
        progress_=context_.create_device_buffer(count*4U,VK_BUFFER_USAGE_STORAGE_BUFFER_BIT);
        const std::array<integration::I001Binding,2> bindings{{
            {0,VK_DESCRIPTOR_TYPE_STORAGE_BUFFER,&values_},
            {1,VK_DESCRIPTOR_TYPE_STORAGE_BUFFER,&progress_}}};
        stage_=std::make_unique<integration::I001ComputeStage>(context_,
            std::string(PHOS_GI_INTEGRATION_SHADER_DIR)+"/n010_history_neutral_work.spv",bindings,12);
    }
    ~BoundedNeutralWork() {
        stage_.reset();context_.destroy_buffer(progress_);context_.destroy_buffer(values_);
    }
    void record(VkCommandBuffer command,uint32_t begin,uint32_t end) const {
        if(begin>end || end>max_dose || end-begin>chunk)
            throw std::runtime_error("bounded known-work interval differs");
        const std::array<uint32_t,3> push{count,begin,end};
        stage_->record(command,count/64U,1,1,push.data(),sizeof(push));
        integration::i001_compute_barrier(context_,command);
    }
    void save(const std::filesystem::path& directory,uint32_t dose) const {
        std::array<uint32_t,count> values{},progress{};
        context_.download_device_buffer(values_,values.data(),sizeof(values));
        context_.download_device_buffer(progress_,progress.data(),sizeof(progress));
        for(const auto next:progress)
            if(next!=dose)throw std::runtime_error("incomplete known-work progress");
        const auto write=[&](const char* name,const auto& words) {
            std::ofstream stream(directory/name,std::ios::binary);
            stream.write(reinterpret_cast<const char*>(words.data()),sizeof(words));
            if(!stream)throw std::runtime_error("known-work readback write failed");
        };
        write("neutral-work.bin",values);write("neutral-progress.bin",progress);
    }
private:
    lane_b::B002VulkanContext& context_;
    lane_b::B002Buffer values_{},progress_{};
    std::unique_ptr<integration::I001ComputeStage> stage_;
};
}
