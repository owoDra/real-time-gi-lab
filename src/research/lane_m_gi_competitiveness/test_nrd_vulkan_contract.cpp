#include "nrd_vulkan_contract.hpp"
#include <iostream>
using namespace m024;
int main(){u32 checks{};auto check=[&](bool x){need(x,"024 actual scalar contract");checks++;};auto reject=[&](auto f){bool caught=false;try{f();}catch(const std::exception&){caught=true;}check(caught);};
 for(const auto& text:{"0","16","64","4294967295"})check(std::to_string(number(text))==text);
 for(const auto& text:{"","-1","+1","1.0"," 16","16x","4294967296"})reject([&]{number(text);});
 check(sample_bytes(pixels,16,16)==14745600ull);check(sample_bytes(pixels,64,4)==14745600ull);check(sample_bytes(pixels,64,16)==58982400ull);
 for(auto shape:{std::array<u32,3>{0,16,16},std::array<u32,3>{pixels+1,16,16},std::array<u32,3>{pixels,UINT32_MAX,16},std::array<u32,3>{pixels,64,UINT32_MAX}})reject([&]{sample_bytes(shape[0],shape[1],shape[2]);});
 budget(16,2);budget(64,8);check(true);for(auto v:{std::pair{1u,2u},std::pair{64u,0u},std::pair{16u,3u}})reject([&]{budget(v.first,v.second);});
 check(user_index(static_cast<nrd::ResourceType>(6))==0);check(user_index(nrd::ResourceType::IN_MV)==3);check(user_index(nrd::ResourceType::OUT_DIFF_RADIANCE_HITDIST)==4);
 reject([&]{user_index(nrd::ResourceType::IN_SPEC_RADIANCE_HITDIST);});reject([&]{user_index(nrd::ResourceType::PERMANENT_POOL);});
 check(format(nrd::Format::RGBA16_SFLOAT)==VK_FORMAT_R16G16B16A16_SFLOAT);check(texel_bytes(format(nrd::Format::R8_UNORM))==1);check(texel_bytes(VK_FORMAT_A2B10G10R10_UNORM_PACK32)==4);check(texel_bytes(VK_FORMAT_R32G32B32A32_SFLOAT)==16);
 reject([&]{format(nrd::Format::RGBA8_SRGB);});reject([&]{texel_bytes(VK_FORMAT_UNDEFINED);});
 std::cout<<"{\"complete\":true,\"gpu_initialized\":false,\"actual_cpp_checks\":"<<checks<<"}\n";
}
