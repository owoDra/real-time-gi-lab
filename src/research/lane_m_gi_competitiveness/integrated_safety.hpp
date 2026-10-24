#pragma once
//022 used by the actual private context/HWRT and integrated host, not old builds.
#include "allocation_ledger.hpp"
#include <chrono>
#include <cstdint>
#include <cstdlib>
#include <filesystem>
#include <fstream>
#include <stdexcept>
#include <string>
namespace m022 {
using Ledger=phos::gi::research::n010::AllocationLedger;
using Clock=std::chrono::steady_clock;
inline std::filesystem::path safety_output;
inline Clock::time_point safety_started=Clock::now();
inline std::uint64_t reserved_bytes{},reserved_peak{};
inline constexpr std::uint64_t cap=8ull*1024*1024*1024;
inline void need(bool b,const char* m){if(!b)throw std::runtime_error(m);}
inline void wall_guard(){need(std::chrono::duration<double>(Clock::now()-safety_started).count()<180,"022 native wall guard");}
inline void reserve(std::uint64_t bytes){wall_guard();need(bytes>0 && bytes<=cap && reserved_bytes<=cap-bytes,"022 aggregate ownership cap");reserved_bytes+=bytes;reserved_peak=std::max(reserved_peak,reserved_bytes);}
inline void release(std::uint64_t bytes){need(bytes>0 && bytes<=reserved_bytes,"022 ownership counter underflow");reserved_bytes-=bytes;}
[[noreturn]] inline void incomplete_fence(const char* label){
    if(!safety_output.empty()){
        Ledger::instance().save(safety_output/"allocation-ledger.json");
        std::ofstream(safety_output/"failure.json")<<"{\"classification\":\"INCOMPLETE_FENCE\",\"label\":\""<<label<<"\",\"gpu_completion_proven\":false,\"teardown_claim\":false}\n";
    }
    std::_Exit(3);
}
}
