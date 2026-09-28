#pragma once
#include "traversal_common.hpp"
#include <algorithm>
#include <bit>
#include <limits>
#include <unordered_map>

namespace phos::gi::research::lane_b {
struct Cell{int x{},y{},z{};bool operator==(const Cell&)const noexcept=default;};
struct CellHash{std::size_t operator()(const Cell& k)const noexcept{std::uint64_t h=1469598103934665603ULL;for(auto v:{std::bit_cast<std::uint32_t>(k.x),std::bit_cast<std::uint32_t>(k.y),std::bit_cast<std::uint32_t>(k.z)}){h^=v;h*=1099511628211ULL;}return std::size_t(h);}};
class SparseGrid{
public:
    explicit SparseGrid(const std::vector<Triangle>& t,float size=4):cell_(size){rebuild(t);}
    void rebuild(const std::vector<Triangle>& t){tris_=&t;cells_.clear();membership_.assign(t.size(),{});visited_.assign(t.size(),0);gen_=1;for(std::uint32_t i=0;i<t.size();++i)insert(i);}
    void update(const std::vector<Triangle>& t,std::span<const std::uint32_t> ids){tris_=&t;for(auto id:ids){for(Cell c:membership_.at(id)){auto it=cells_.find(c);if(it==cells_.end())continue;std::erase(it->second,id);if(it->second.empty())cells_.erase(it);}membership_[id].clear();insert(id);}}
    Hit trace(Ray ray)const{
        if(!normalize_ray(ray)) return {};
        if(++gen_==0){std::fill(visited_.begin(),visited_.end(),0);gen_=1;}
        auto g=gen_;
        Cell c{fc(ray.origin.x),fc(ray.origin.y),fc(ray.origin.z)};
        int sx=ray.direction.x>=0?1:-1,sy=ray.direction.y>=0?1:-1,sz=ray.direction.z>=0?1:-1;
        auto init=[&](float o,float d,int q,int s){if(std::abs(d)<1e-8F)return std::pair{INFINITY,INFINITY};float b=float(q+(s>0))*cell_;return std::pair{std::max(0.0F,(b-o)/d),std::abs(cell_/d)};};auto[tx,dx]=init(ray.origin.x,ray.direction.x,c.x,sx);auto[ty,dy]=init(ray.origin.y,ray.direction.y,c.y,sy);auto[tz,dz]=init(ray.origin.z,ray.direction.z,c.z,sz);float cur=0;Hit best{};std::uint32_t steps=0,maxsteps=std::uint32_t(std::ceil(ray.t_max/cell_*4))+16;
        while(cur<=ray.t_max&&steps++<maxsteps){if(auto it=cells_.find(c);it!=cells_.end())for(auto id:it->second){if(visited_[id]==g)continue;visited_[id]=g;if(auto h=intersect_triangle(tris_->at(id),ray,best.hit?best.t:ray.t_max);h&&prefer_hit(*h,best))best=*h;}float next=std::min({tx,ty,tz});if((best.hit&&next>best.t+kHitDistanceAbsTolerance)||next>ray.t_max)break;constexpr float e=1e-6F;if(tx<=next+e){c.x+=sx;tx+=dx;}if(ty<=next+e){c.y+=sy;ty+=dy;}if(tz<=next+e){c.z+=sz;tz+=dz;}cur=next;}return best;
    }
    std::size_t persistent_bytes()const noexcept{std::size_t n=cells_.size()*(sizeof(Cell)+sizeof(std::vector<std::uint32_t>))+membership_.capacity()*sizeof(std::vector<Cell>);for(auto&[_,v]:cells_)n+=v.capacity()*sizeof(std::uint32_t);for(auto&v:membership_)n+=v.capacity()*sizeof(Cell);return n;}std::size_t scratch_bytes()const noexcept{return visited_.capacity()*sizeof(std::uint32_t);}
private:
    int fc(float v)const noexcept{return int(std::floor(v/cell_));}
    void insert(std::uint32_t id){Aabb a=triangle_bounds(tris_->at(id));Cell lo{fc(a.min.x),fc(a.min.y),fc(a.min.z)},hi{fc(a.max.x),fc(a.max.y),fc(a.max.z)};auto& m=membership_[id];std::int64_t nx=std::int64_t(hi.x)-lo.x+1,ny=std::int64_t(hi.y)-lo.y+1,nz=std::int64_t(hi.z)-lo.z+1;if(nx<=0||ny<=0||nz<=0||nx*ny*nz>4096)throw std::runtime_error("primitive spans too many cells");m.reserve(std::size_t(nx*ny*nz));for(int z=lo.z;z<=hi.z;++z)for(int y=lo.y;y<=hi.y;++y)for(int x=lo.x;x<=hi.x;++x){Cell c{x,y,z};cells_[c].push_back(id);m.push_back(c);}}
    float cell_{};const std::vector<Triangle>* tris_{};std::unordered_map<Cell,std::vector<std::uint32_t>,CellHash> cells_;std::vector<std::vector<Cell>> membership_;mutable std::vector<std::uint32_t> visited_;mutable std::uint32_t gen_{1};
};
} // namespace phos::gi::research::lane_b
