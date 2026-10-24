#pragma once
//024 actual adapter mapping/size/CLI contracts, no graphics initialization.
#include "integrated_state.hpp"
#include "nrd_guide_contract.hpp"
#include <charconv>
#include <map>
namespace m024 {
using m022::need;using u32=std::uint32_t;using u64=std::uint64_t;
inline constexpr u32 pixels=320*180;
inline u32 number(const std::string& text){u32 value{};auto r=std::from_chars(text.data(),text.data()+text.size(),value);need(!text.empty()&&r.ec==std::errc{}&&r.ptr==text.data()+text.size(),"024 integer syntax/range");return value;}
inline void budget(u32 spp,u32 vertices){need((spp==16||spp==64)&&(vertices==2||vertices==8),"024 unregistered budget");}
inline u64 sample_bytes(u32 count,u32 spp,u32 stride){need(count>0&&count<=pixels&&(spp==16||spp==64)&&(stride==4||stride==16),"024 sample buffer shape/overflow");return u64(count)*spp*stride;}
inline VkFormat format(nrd::Format f){switch(f){case nrd::Format::R8_UNORM:return VK_FORMAT_R8_UNORM;case nrd::Format::RGBA8_UNORM:return VK_FORMAT_R8G8B8A8_UNORM;case nrd::Format::RGBA16_SFLOAT:return VK_FORMAT_R16G16B16A16_SFLOAT;case nrd::Format::R32_SFLOAT:return VK_FORMAT_R32_SFLOAT;default:throw std::runtime_error("024 unregistered SDK pool format");}}
inline u32 texel_bytes(VkFormat f){switch(f){case VK_FORMAT_R8_UNORM:return 1;case VK_FORMAT_R8G8B8A8_UNORM:case VK_FORMAT_R32_SFLOAT:case VK_FORMAT_A2B10G10R10_UNORM_PACK32:return 4;case VK_FORMAT_R16G16B16A16_SFLOAT:return 8;case VK_FORMAT_R32G32B32A32_SFLOAT:return 16;default:throw std::runtime_error("024 unknown texture format");}}
inline u32 user_index(nrd::ResourceType type){switch(type){case nrd::ResourceType::IN_DIFF_RADIANCE_HITDIST:return 0;case nrd::ResourceType::IN_NORMAL_ROUGHNESS:return 1;case nrd::ResourceType::IN_VIEWZ:return 2;case nrd::ResourceType::IN_MV:return 3;case nrd::ResourceType::OUT_DIFF_RADIANCE_HITDIST:return 4;default:throw std::runtime_error("024 unbound user resource enum");}}
}
