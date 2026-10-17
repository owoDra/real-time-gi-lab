    // Plan102: flatten the existing binary topology into eight-lane frontiers.
    // Original triangle arithmetic, build, order and scalar fallback survive.
    struct alignas(64) WideNode {
        double lo[3][8]{}, hi[3][8]{};
        uint32_t reference[8]{}, original[8]{}, valid{};
    };
    std::vector<WideNode> wide_nodes_;
    std::vector<uint32_t> wide_leaf_visits_;
    static constexpr uint32_t wide_leaf_bit=0x80000000U;

    uint32_t build_wide_node(uint32_t root) {
        if (nodes_[root].count) throw std::runtime_error("wide root must be internal");
        if (wide_nodes_.size()>=wide_leaf_bit) throw std::runtime_error("wide index overflow");
        const auto result=uint32_t(wide_nodes_.size());
        wide_nodes_.push_back({});
        struct Frontier {uint32_t node,depth;};
        Frontier front[8]{{root+1,1},{nodes_[root].right,1}};
        uint32_t count=2;
        while (count<8) {
            uint32_t selected=count,depth=UINT32_MAX;
            for (uint32_t i=0;i<count;++i)
                if (!nodes_[front[i].node].count&&front[i].depth<depth) {selected=i;depth=front[i].depth;}
            if (selected==count) break;
            const auto current=front[selected];
            for (uint32_t i=count;i>selected+1;--i) front[i]=front[i-1];
            front[selected]={current.node+1,current.depth+1};
            front[selected+1]={nodes_[current.node].right,current.depth+1};
            ++count;
        }
        WideNode node{};
        node.valid=(1U<<count)-1;
        for (uint32_t i=0;i<count;++i) {
            const auto original=front[i].node;
            node.original[i]=original;
            for (int a=0;a<3;++a) {node.lo[a][i]=nodes_[original].box.lo[a];node.hi[a][i]=nodes_[original].box.hi[a];}
            if (nodes_[original].count) {
                ++wide_leaf_visits_[original];
                node.reference[i]=wide_leaf_bit|original;
            } else node.reference[i]=build_wide_node(original);
        }
        wide_nodes_[result]=node;
        return result;
    }

    void build_wide() {
        if (nodes_.size()>=wide_leaf_bit) throw std::runtime_error("original node index overflow");
        for (uint32_t i=0;i<nodes_.size();++i) {
            const auto& p=nodes_[i];
            for (int a=0;a<3;++a)
                if (!std::isfinite(p.box.lo[a])||!std::isfinite(p.box.hi[a])||p.box.lo[a]>p.box.hi[a])
                    throw std::runtime_error("nonfinite/reversed original BVH box");
            if (!p.count) for (auto child:{i+1,p.right}) for (int a=0;a<3;++a)
                if (nodes_[child].box.lo[a]<p.box.lo[a]||nodes_[child].box.hi[a]>p.box.hi[a])
                    throw std::runtime_error("original child box escapes parent");
        }
        if (nodes_.empty()||nodes_[0].count) return;
        wide_leaf_visits_.assign(nodes_.size(),0);
        if (build_wide_node(0)!=0) throw std::runtime_error("wide root identity");
        for (uint32_t i=0;i<nodes_.size();++i)
            if (wide_leaf_visits_[i]!=(nodes_[i].count?1U:0U))
                throw std::runtime_error("wide frontier leaf coverage differs");
        wide_leaf_visits_.clear();wide_leaf_visits_.shrink_to_fit();
    }

    static uint32_t intersect_wide(const WideNode& node,const __m512d origin[3],
                                   const __m512d inverse[3],double tmin,double tmax,__m512d& lower) {
        lower=_mm512_set1_pd(tmin);
        auto upper=_mm512_set1_pd(tmax);
        __mmask8 invalid=0;
        for (int a=0;a<3;++a) {
            const auto lo=_mm512_load_pd(node.lo[a]),hi=_mm512_load_pd(node.hi[a]);
            const auto tn=_mm512_mul_pd(_mm512_sub_pd(lo,origin[a]),inverse[a]);
            const auto tf=_mm512_mul_pd(_mm512_sub_pd(hi,origin[a]),inverse[a]);
            const auto nan=_mm512_cmp_pd_mask(tn,tf,_CMP_UNORD_Q);
            const auto outside=_mm512_cmp_pd_mask(origin[a],lo,_CMP_LT_OQ)|_mm512_cmp_pd_mask(origin[a],hi,_CMP_GT_OQ);
            invalid|=nan&outside;
            const auto swap=_mm512_cmp_pd_mask(tn,tf,_CMP_GT_OQ);
            const auto near=_mm512_mask_blend_pd(swap,tn,tf);
            const auto far=_mm512_mul_pd(_mm512_mask_blend_pd(swap,tf,tn),
                _mm512_set1_pd(1.0+4.0*std::numeric_limits<double>::epsilon()));
            lower=_mm512_mask_mov_pd(lower,~nan&_mm512_cmp_pd_mask(lower,near,_CMP_LT_OQ),near);
            upper=_mm512_mask_mov_pd(upper,~nan&_mm512_cmp_pd_mask(upper,far,_CMP_GT_OQ),far);
            invalid|=~nan&_mm512_cmp_pd_mask(lower,upper,_CMP_GT_OQ);
        }
        return node.valid&~uint32_t(invalid);
    }

    template <class Visit>
    void traverse(const Ray& ray,double tmin,Visit&& visit,double& tmax) const {
        if (nodes_.empty()) return;
        if (!(tmin>=0&&tmin<=tmax)||nodes_[0].count||
            !std::isfinite(ray.origin.x)||!std::isfinite(ray.origin.y)||!std::isfinite(ray.origin.z)||
            !std::isfinite(ray.dir.x)||!std::isfinite(ray.dir.y)||!std::isfinite(ray.dir.z)) {
            traverse_scalar(ray,tmin,std::forward<Visit>(visit),tmax);return;
        }
        const WatertightRay wr(ray);
        const V3 inv{1.0/ray.dir.x,1.0/ray.dir.y,1.0/ray.dir.z};
        if (!slab(nodes_[0].box,ray.origin,inv,tmin,tmax)) return;
        const __m512d origins[3]{_mm512_set1_pd(ray.origin.x),_mm512_set1_pd(ray.origin.y),_mm512_set1_pd(ray.origin.z)};
        const __m512d inverses[3]{_mm512_set1_pd(inv.x),_mm512_set1_pd(inv.y),_mm512_set1_pd(inv.z)};
        struct Entry {uint32_t reference,original;double near;};
        Entry stack[512];uint32_t sp=0;
        stack[sp++]={0,0,tmin};
        while (sp) {
            const auto entry=stack[--sp];
            const bool hit=!(entry.near>tmax);
#ifdef N010_VERIFY_BVH
            ++paired_cached_slab_count;
            if (hit!=slab(nodes_[entry.original].box,ray.origin,inv,tmin,tmax))
                throw std::runtime_error("wide cached/original box predicate differs");
#endif
            if (!hit) continue;
            if (entry.reference&wide_leaf_bit) {
                const auto& leaf=nodes_[entry.reference&~wide_leaf_bit];
                for (auto i=leaf.first;i<leaf.first+leaf.count;++i) {
                    const auto id=order_[i];const double t=wr.intersect(tris_[id]);
                    if (t<kInf&&t<=tmax&&visit(id,t)) return;
                }
                continue;
            }
            const auto& node=wide_nodes_[entry.reference];
            __m512d lower;
            const auto mask=intersect_wide(node,origins,inverses,tmin,tmax,lower);
#ifdef N010_VERIFY_BVH
            for (uint32_t lane=0;lane<8;++lane) if (node.valid&(1U<<lane)) {
                ++paired_slab_count;
                if (bool(mask&(1U<<lane))!=slab(nodes_[node.original[lane]].box,ray.origin,inv,tmin,tmax))
                    throw std::runtime_error("wide/scalar acquired box predicate differs");
            }
#endif
            alignas(64) double near[8];_mm512_store_pd(near,lower);
            if (sp+8>512) throw std::runtime_error("wide BVH stack overflow");
            for (int lane=7;lane>=0;--lane) if (mask&(1U<<lane))
                stack[sp++]={node.reference[lane],node.original[lane],near[lane]};
        }
    }
