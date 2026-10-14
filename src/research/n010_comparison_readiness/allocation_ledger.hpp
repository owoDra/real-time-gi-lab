#pragma once
// All owned vkAllocateMemory lifetimes, across the role's Vulkan contexts.
// Driver-private allocations and non-Vulkan CPU memory are outside this ledger.
#include <vulkan/vulkan.h>
#include <algorithm>
#include <cstdint>
#include <cstdlib>
#include <filesystem>
#include <fstream>
#include <map>
#include <mutex>
#include <stdexcept>
#include <string>
#include <vector>

namespace phos::gi::research::n010 {
struct AllocationEvent {
    std::uint64_t sequence, allocation, bytes, live_bytes;
    std::uint32_t device, memory_type, requested_properties, usage;
    bool allocate;
    std::string phase;
};
class AllocationLedger {
public:
    static AllocationLedger& instance() { static AllocationLedger ledger; return ledger; }
    void allocate(VkDevice device, VkDeviceMemory memory, std::uint64_t bytes,
                  std::uint32_t type, std::uint32_t properties, std::uint32_t usage) {
        std::lock_guard lock(mutex_);
        const auto key=std::pair{device,memory};
        if (live_.contains(key)) throw std::runtime_error("duplicate live Vulkan memory allocation");
        if (!devices_.contains(device)) devices_[device]=std::uint32_t(devices_.size()+1);
        const auto id=++next_id_;
        live_[key]={id,bytes,type,properties,usage};
        live_bytes_+=bytes;
        peak_bytes_=std::max(peak_bytes_,live_bytes_);
        phase_peak_=std::max(phase_peak_,live_bytes_);
        events_.push_back({events_.size(),id,bytes,live_bytes_,devices_.at(device),type,properties,usage,true,phase_});
    }
    void release(VkDevice device, VkDeviceMemory memory) {
        std::lock_guard lock(mutex_);
        auto it=live_.find({device,memory});
        if (it==live_.end()) throw std::runtime_error("untracked Vulkan memory free");
        const auto a=it->second;
        live_bytes_-=a.bytes;
        events_.push_back({events_.size(),a.id,a.bytes,live_bytes_,devices_.at(device),
                           a.type,a.properties,a.usage,false,phase_});
        live_.erase(it);
    }
    void phase(const std::string& name) {
        std::lock_guard lock(mutex_);
        phases_.push_back({phase_,phase_peak_,live_bytes_});
        phase_=name;
        phase_peak_=live_bytes_;
    }
    void save(const std::filesystem::path& path) {
        std::lock_guard lock(mutex_);
        std::ofstream out(path);
        if (!out) throw std::runtime_error("allocation ledger open failed");
        out<<"{\"schema\":\"n010-allocation-lifetimes/1\",\"scope\":\"all owned Vulkan allocations; driver-private and CPU memory excluded\","
           <<"\"live_bytes_at_teardown\":"<<live_bytes_<<",\"teardown_zero\":"<<(live_.empty()?"true":"false")
           <<",\"true_peak_owned_bytes\":"<<peak_bytes_<<",\"device_contexts\":"<<devices_.size()<<",\"phases\":[";
        bool first=true;
        auto emit=[&](const Phase& p){out<<(first?"":",")<<"{\"name\":\""<<p.name<<"\",\"peak_bytes\":"<<p.peak
                                      <<",\"live_bytes_at_end\":"<<p.end<<'}';first=false;};
        for (const auto& p:phases_) emit(p);
        emit({phase_,phase_peak_,live_bytes_});
        out<<"],\"events\":[";
        first=true;
        for (const auto& e:events_) {
            out<<(first?"":",")<<"{\"sequence\":"<<e.sequence<<",\"allocation_id\":"<<e.allocation
               <<",\"device_context\":"<<e.device<<",\"action\":\""<<(e.allocate?"allocate":"free")
               <<"\",\"bytes\":"<<e.bytes<<",\"live_bytes\":"<<e.live_bytes<<",\"memory_type\":"<<e.memory_type
               <<",\"requested_properties\":"<<e.requested_properties<<",\"buffer_usage\":"<<e.usage
               <<",\"phase\":\""<<e.phase<<"\"}";first=false;
        }
        out<<"]}\n";
        if (!out) throw std::runtime_error("allocation ledger write failed");
    }
private:
    struct Live { std::uint64_t id,bytes; std::uint32_t type,properties,usage; };
    struct Phase { std::string name; std::uint64_t peak,end; };
    std::mutex mutex_;
    std::map<std::pair<VkDevice,VkDeviceMemory>,Live> live_;
    std::map<VkDevice,std::uint32_t> devices_;
    std::vector<AllocationEvent> events_;
    std::vector<Phase> phases_;
    std::uint64_t next_id_{},live_bytes_{},peak_bytes_{},phase_peak_{};
    std::string phase_{"startup"};
};
class LedgerOutput {
public:
    explicit LedgerOutput(std::filesystem::path path):path_(std::move(path)) {}
    ~LedgerOutput() noexcept {
        try { if (!path_.empty()) AllocationLedger::instance().save(path_); }
        catch (...) { std::terminate(); }
    }
private:
    std::filesystem::path path_;
};
}
