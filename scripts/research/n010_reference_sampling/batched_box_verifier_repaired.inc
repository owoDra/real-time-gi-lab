    struct alignas(32) BoxPacket { double lo[3][4]{}, hi[3][4]{}; };
    struct PacketGroup { BoxPacket children, grandchildren; uint32_t grandchildren_mask{}; };
    std::vector<PacketGroup> packet_groups_;
    std::vector<uint32_t> packet_index_;

    void build_packets() {
        packet_index_.assign(nodes_.size(), UINT32_MAX);
        std::vector<uint32_t> queue;
        if (!nodes_.empty() && !nodes_[0].count) queue.push_back(0);
        const auto copy_box=[](BoxPacket& packet, uint32_t lane, const Aabb& box) {
            for (int a=0;a<3;++a) { packet.lo[a][lane]=box.lo[a]; packet.hi[a][lane]=box.hi[a]; }
        };
        for (size_t i=0;i<queue.size();++i) {
            const uint32_t ni=queue[i];
            if (packet_index_[ni]!=UINT32_MAX) throw std::runtime_error("duplicate BVH packet index");
            PacketGroup group{};
            const uint32_t children[2]{ni+1,nodes_[ni].right};
            for (uint32_t side=0;side<2;++side) {
                const uint32_t child=children[side];
                copy_box(group.children,side,nodes_[child].box);
                if (nodes_[child].count) continue;
                const uint32_t grandchildren[2]{child+1,nodes_[child].right};
                for (uint32_t j=0;j<2;++j) {
                    const uint32_t lane=2*side+j, grandchild=grandchildren[j];
                    copy_box(group.grandchildren,lane,nodes_[grandchild].box);
                    group.grandchildren_mask|=1U<<lane;
                    if (!nodes_[grandchild].count) queue.push_back(grandchild);
                }
            }
            packet_index_[ni]=uint32_t(packet_groups_.size());
            packet_groups_.push_back(group);
        }
    }

    static uint32_t intersect_packet(const BoxPacket& packet, const __m256d origin[3],
                                    const __m256d inverse[3], double tmin, double tmax,
                                    uint32_t valid, __m256d& lower) {
        lower=_mm256_set1_pd(tmin);
        auto upper=_mm256_set1_pd(tmax), invalid=_mm256_setzero_pd();
        for (int a=0;a<3;++a) {
            const auto lo=_mm256_load_pd(packet.lo[a]), hi=_mm256_load_pd(packet.hi[a]);
            const auto tn=_mm256_mul_pd(_mm256_sub_pd(lo,origin[a]),inverse[a]);
            const auto tf=_mm256_mul_pd(_mm256_sub_pd(hi,origin[a]),inverse[a]);
            const auto nan=_mm256_cmp_pd(tn,tf,_CMP_UNORD_Q);
            const auto outside=_mm256_or_pd(_mm256_cmp_pd(origin[a],lo,_CMP_LT_OQ),
                                            _mm256_cmp_pd(origin[a],hi,_CMP_GT_OQ));
            invalid=_mm256_or_pd(invalid,_mm256_and_pd(nan,outside));
            const auto swap=_mm256_cmp_pd(tn,tf,_CMP_GT_OQ);
            const auto near=_mm256_blendv_pd(tn,tf,swap);
            const auto far=_mm256_mul_pd(_mm256_blendv_pd(tf,tn,swap),
                _mm256_set1_pd(1.0+4.0*std::numeric_limits<double>::epsilon()));
            // std::max/min retain their first operand on equality or NaN.
            const auto next_lower=_mm256_blendv_pd(lower,near,_mm256_cmp_pd(lower,near,_CMP_LT_OQ));
            const auto next_upper=_mm256_blendv_pd(upper,far,_mm256_cmp_pd(upper,far,_CMP_GT_OQ));
            lower=_mm256_blendv_pd(next_lower,lower,nan);
            upper=_mm256_blendv_pd(next_upper,upper,nan);
            invalid=_mm256_or_pd(invalid,_mm256_andnot_pd(nan,_mm256_cmp_pd(lower,upper,_CMP_GT_OQ)));
        }
        return valid & ~uint32_t(_mm256_movemask_pd(invalid));
    }

#ifdef N010_VERIFY_BVH
    void verify_packet(const BoxPacket& packet, const Ray& ray, const V3& inv,
                       double tmin, double tmax, uint32_t valid, uint32_t actual) const {
        for (uint32_t lane=0;lane<4;++lane) if (valid&(1U<<lane)) {
            Aabb box;
            box.lo={packet.lo[0][lane],packet.lo[1][lane],packet.lo[2][lane]};
            box.hi={packet.hi[0][lane],packet.hi[1][lane],packet.hi[2][lane]};
            ++paired_slab_count;
            if (bool(actual&(1U<<lane))!=slab(box,ray.origin,inv,tmin,tmax))
                throw std::runtime_error("batched/scalar acquired box predicate differs");
        }
    }
#endif

    template <class Visit>
    void traverse(const Ray& ray, double tmin, Visit&& visit, double& tmax) const {
        // Exceptional intervals use the preserved original traversal, not a
        // newly inferred interval rule. Normal oracle calls have 0<=tmin<=tmax.
        if (!(tmin<=tmax)) { traverse_scalar(ray,tmin,std::forward<Visit>(visit),tmax); return; }
        if (nodes_.empty()) return;
        const WatertightRay wr(ray);
        const V3 inv{1.0/ray.dir.x,1.0/ray.dir.y,1.0/ray.dir.z};
        if (!slab(nodes_[0].box,ray.origin,inv,tmin,tmax)) return;
        const __m256d origin4[3]{_mm256_set1_pd(ray.origin.x),_mm256_set1_pd(ray.origin.y),_mm256_set1_pd(ray.origin.z)};
        const __m256d inverse4[3]{_mm256_set1_pd(inv.x),_mm256_set1_pd(inv.y),_mm256_set1_pd(inv.z)};
        struct Entry { uint32_t node{}, child_mask{}; double lower{}, child_lower[2]{}; bool cached_children{}; };
        Entry stack[128]; int sp=0;
        stack[sp++]={0,0,tmin,{0,0},false};
        while (sp>0) {
            const Entry entry=stack[--sp]; const uint32_t ni=entry.node;
            const Node& node=nodes_[ni];
            const bool intersects=!(entry.lower>tmax);
#ifdef N010_VERIFY_BVH
            ++paired_cached_slab_count;
            if (intersects!=slab(node.box,ray.origin,inv,tmin,tmax))
                throw std::runtime_error("cached/current scalar box predicate differs");
#endif
            if (!intersects) continue;
            if (node.count) {
                for (auto i=node.first;i<node.first+node.count;++i) {
                    const auto id=order_[i];const double t=wr.intersect(tris_[id]);
                    if (t<kInf&&t<=tmax&&visit(id,t)) return;
                }
                continue;
            }
            if (entry.cached_children) {
                if (sp+2>128) throw std::runtime_error("BVH stack overflow");
                if (entry.child_mask&2) stack[sp++]={node.right,0,entry.child_lower[1],{0,0},false};
                if (entry.child_mask&1) stack[sp++]={ni+1,0,entry.child_lower[0],{0,0},false};
                continue;
            }
            if (packet_index_[ni]==UINT32_MAX) throw std::runtime_error("missing BVH packet group");
            const auto& group=packet_groups_[packet_index_[ni]];
            __m256d child_lower,grand_lower;
            const auto cm=intersect_packet(group.children,origin4,inverse4,tmin,tmax,3,child_lower);
            uint32_t gm=0;
            alignas(32) double cn[4],gn[4]{};
            _mm256_store_pd(cn,child_lower);
            if (group.grandchildren_mask) {
                gm=intersect_packet(group.grandchildren,origin4,inverse4,tmin,tmax,group.grandchildren_mask,grand_lower);
                _mm256_store_pd(gn,grand_lower);
            }
#ifdef N010_VERIFY_BVH
            verify_packet(group.children,ray,inv,tmin,tmax,3,cm);
            if (group.grandchildren_mask) verify_packet(group.grandchildren,ray,inv,tmin,tmax,group.grandchildren_mask,gm);
#endif
            // Keep each original parent event. Parent predicates are not
            // merged into a descendant entry or retested after its first child.
            if (sp+2>128) throw std::runtime_error("BVH stack overflow");
            if (cm&2) stack[sp++]={node.right,(gm>>2)&3,cn[1],{gn[2],gn[3]},true};
            if (cm&1) stack[sp++]={ni+1,gm&3,cn[0],{gn[0],gn[1]},true};
        }
    }
