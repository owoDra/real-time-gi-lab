#pragma once
#include "traversal_common.hpp"
#include <algorithm>
#include <array>
#include <numeric>
#include <vector>

namespace phos::gi::research::lane_b {
class SoftwareBvh {
    struct Node{Aabb b{};std::uint32_t l{},r{},begin{},count{};bool leaf{};};
public:
    explicit SoftwareBvh(const std::vector<Triangle>& t){rebuild(t);}
    void rebuild(const std::vector<Triangle>& t){tris_=&t;ids_.resize(t.size());std::iota(ids_.begin(),ids_.end(),0U);nodes_.clear();nodes_.reserve(t.size()*2+1);if(!t.empty())root_=build(0,std::uint32_t(t.size()));}
    void refit(const std::vector<Triangle>& t){tris_=&t;if(!nodes_.empty())refit_node(root_);}
    Hit trace(Ray ray) const{
        if(nodes_.empty()||!normalize_ray(ray)) return {};
        Hit best{};
        std::array<std::uint32_t,128> st{};
        std::size_t sp=0;
        st[sp++]=root_;
        while(sp){const Node& n=nodes_[st[--sp]];if(!ray_aabb(ray,n.b,best.hit?best.t:ray.t_max))continue;if(n.leaf){for(std::uint32_t j=0;j<n.count;++j){const auto& tri=tris_->at(ids_[n.begin+j]);if(auto h=intersect_triangle(tri,ray,best.hit?best.t:ray.t_max);h&&prefer_hit(*h,best))best=*h;}}else{if(sp+2>st.size())throw std::runtime_error("BVH stack overflow");st[sp++]=n.l;st[sp++]=n.r;}}
        return best;
    }
    std::size_t persistent_bytes() const noexcept{return nodes_.capacity()*sizeof(Node)+ids_.capacity()*sizeof(std::uint32_t);} static constexpr std::size_t scratch_bytes() noexcept{return sizeof(std::array<std::uint32_t,128>);}
private:
    std::uint32_t build(std::uint32_t begin,std::uint32_t end){
        auto idx=std::uint32_t(nodes_.size());nodes_.push_back({});Aabb b{},c{};for(auto i=begin;i<end;++i){Aabb a=triangle_bounds(tris_->at(ids_[i]));b=merge(b,a);Vec3 p=center(a);c=merge(c,{p,p});}auto count=end-begin;if(count<=4){nodes_[idx]={b,0,0,begin,count,true};return idx;}Vec3 e=c.max-c.min;int axis=(e.y>e.x&&e.y>=e.z)?1:(e.z>e.x?2:0);auto mid=begin+count/2;auto coord=[&](std::uint32_t id){Vec3 p=center(triangle_bounds(tris_->at(id)));return axis==0?p.x:(axis==1?p.y:p.z);};std::nth_element(ids_.begin()+begin,ids_.begin()+mid,ids_.begin()+end,[&](auto a,auto d){return coord(a)<coord(d);});auto l=build(begin,mid),r=build(mid,end);nodes_[idx]={b,l,r,0,0,false};return idx;
    }
    Aabb refit_node(std::uint32_t i){Node& n=nodes_[i];if(n.leaf){Aabb b{};for(std::uint32_t j=0;j<n.count;++j)b=merge(b,triangle_bounds(tris_->at(ids_[n.begin+j])));return n.b=b;}return n.b=merge(refit_node(n.l),refit_node(n.r));}
    const std::vector<Triangle>* tris_{};std::vector<std::uint32_t> ids_;std::vector<Node> nodes_;std::uint32_t root_{};
};
} // namespace phos::gi::research::lane_b
