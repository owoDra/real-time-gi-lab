    // Plan078: general RGB/one-sided finite-depth target; one-point proposal.
    // The original physical sample(), direct(), BVH and numeric policy remain.
    struct WholeRaw {uint32_t triangle{UINT32_MAX};V3 point{};};
    struct WholeState {WholeRaw raw;V3 normal{},origin{};uint32_t alternative_self{UINT32_MAX};};
    struct WholeAudit {
        uint64_t eye_samples{},light_samples{},prefixes{},forward_null{},opposite_zero{},
                 density_reconstructions{},bvh_queries{},own_checks{},coincident_matches{},alternative_ray_checks{},alternative_direct_checks{},unmatched_visibility{};
        std::map<std::pair<uint32_t,uint32_t>,uint64_t> coincident_pairs;
        double max_coincident_normal_difference{};
        double max_own_log_error{},max_target_error_fraction{},max_weight{},max_unconditioned_target_error_fraction{};
        uint64_t strategy_counts[8][8]{},component_attempts{},component_nulls{};
        double max_depth_weight[8]{};
        RenderCounters direct_counters;
    };

    WholeState whole_state(WholeRaw raw,V3 incoming) const {
        const auto& triangle=scene_.triangles.at(raw.triangle);
        const auto normal=normalize(cross(triangle.v1-triangle.v0,triangle.v2-triangle.v0));
        const auto oriented=dot(normal,incoming)<0?normal:normal*-1.0;
        return {raw,oriented,nudge_inside(triangle,raw.point)+oriented*offset_};
    }


    static bool whole_bits(V3 a,V3 b) {
        return std::memcmp(&a.x,&b.x,sizeof(double))==0&&
               std::memcmp(&a.y,&b.y,sizeof(double))==0&&
               std::memcmp(&a.z,&b.z,sizeof(double))==0;
    }

    bool whole_coincident(const WholeRaw& target,uint32_t other,V3 incoming,WholeAudit& audit) const {
        const auto& a=scene_.triangles.at(target.triangle);
        const auto& b=scene_.triangles.at(other);
        int axis=-1;
        for(int j=0;j<3;++j)if(a.v0[j]==a.v1[j]&&a.v0[j]==a.v2[j]&&
            a.v0[j]==b.v0[j]&&a.v0[j]==b.v1[j]&&a.v0[j]==b.v2[j])axis=j;
        if(axis<0)return false;
        const auto& ma=scene_.materials.at(a.material);const auto& mb=scene_.materials.at(b.material);
        if(ma.rho!=mb.rho||ma.emit!=mb.emit||ma.two_sided!=mb.two_sided)return false;
        if(!ma.two_sided) {
            const auto na=normalize(cross(a.v1-a.v0,a.v2-a.v0)),nb=normalize(cross(b.v1-b.v0,b.v2-b.v0));
            if((dot(na,incoming)<0)!=(dot(nb,incoming)<0))return false;
        }
        const auto interior=[&](const Triangle& t) {
            const int i=(axis+1)%3,j=(axis+2)%3;
            const long double ax=t.v0[i],ay=t.v0[j],bx=t.v1[i],by=t.v1[j],cx=t.v2[i],cy=t.v2[j];
            const long double px=target.point[i],py=target.point[j];
            const long double d=(bx-ax)*(cy-ay)-(by-ay)*(cx-ax);
            if(d==0)return false;
            const long double u=((px-ax)*(cy-ay)-(py-ay)*(cx-ax))/d;
            const long double v=((bx-ax)*(py-ay)-(by-ay)*(px-ax))/d;
            return u>0&&v>0&&u+v<1;
        };
        if(!interior(a)||!interior(b))return false;
        const auto sa=whole_state(target,incoming),sb=whole_state({other,target.point},incoming);
        if(!whole_bits(nudge_inside(a,target.point),nudge_inside(b,target.point))||!whole_bits(sa.origin,sb.origin))return false;
        const double difference=length(sa.normal-sb.normal);
        if(difference>32*std::numeric_limits<double>::epsilon())return false;
        if((sa.origin[axis]-a.v0[axis])*sa.normal[axis]<offset_/2||
           (sb.origin[axis]-b.v0[axis])*sb.normal[axis]<offset_/2)return false;
        ++audit.coincident_matches;++audit.coincident_pairs[{target.triangle,other}];
        audit.max_coincident_normal_difference=std::max(audit.max_coincident_normal_difference,difference);
        return true;
    }

    // Conditional area densities use raw target points. The ordered source
    // spawn, normals, self-ignore and range are recomputed for each family.
    double whole_density(WholeState current,const std::vector<WholeRaw>& targets,
                         bool light_first,WholeAudit& audit,WholeState* endpoint=nullptr) const {
        ++audit.density_reconstructions;
        double log_density=0;
        for(size_t i=0;i<targets.size();++i) {
            const auto& target=targets[i];const auto delta=target.point-current.origin;
            const double d2=dot(delta,delta);
            if(!(d2>0))return -kInf;
            const double distance=std::sqrt(d2);const V3 direction=delta*(1.0/distance);
            const bool sphere=light_first&&i==0;
            const double pdf=sphere?1.0/(4*kPi):std::max(0.0,dot(current.normal,direction))/kPi;
            if(!(pdf>0))return -kInf;
            ++audit.bvh_queries;
            const auto hit=bvh_.closest({current.origin,direction},sphere?offset_:0.0,
                sphere?kInf:(scene_.secondary_far_camera?scene_.camera.far:kInf),current.raw.triangle);
            if(current.alternative_self!=UINT32_MAX) {
                ++audit.bvh_queries;++audit.alternative_ray_checks;
                const auto alternative=bvh_.closest({current.origin,direction},sphere?offset_:0.0,
                    sphere?kInf:(scene_.secondary_far_camera?scene_.camera.far:kInf),current.alternative_self);
                if(hit.hit()!=alternative.hit()||(hit.hit()&&
                    (hit.tri!=alternative.tri||std::memcmp(&hit.t,&alternative.t,sizeof(double))!=0)))
                    throw std::runtime_error("coincident alternative self changes actual visibility");
            }
            if(!hit.hit())return -kInf;
            const bool coincident=hit.tri!=target.triangle;
            if(coincident&&!whole_coincident(target,hit.tri,direction,audit)) {
                if(audit.unmatched_visibility++<8)std::fprintf(stderr,"unmatched target=%u hit=%u point=%.17g,%.17g,%.17g\n",
                    target.triangle,hit.tri,target.point.x,target.point.y,target.point.z);
                return -kInf;
            }
            const V3 actual=current.origin+direction*hit.t;
            const double error=length(actual-target.point);
            const double bound=256*std::numeric_limits<double>::epsilon()*
                (1+length(current.origin)+length(target.point)+distance);
            const auto& numeric_triangle=scene_.triangles.at(target.triangle);
            const auto numeric_normal=normalize(cross(numeric_triangle.v1-numeric_triangle.v0,numeric_triangle.v2-numeric_triangle.v0));
            const double target_plane_error=std::abs(dot(numeric_normal,target.point-numeric_triangle.v0));
            const double actual_plane_error=std::abs(dot(numeric_normal,actual-numeric_triangle.v0));
            const double conditioned_error=error*std::abs(dot(numeric_normal,direction));
            const double certified_error=std::max({target_plane_error,actual_plane_error,conditioned_error});
            audit.max_unconditioned_target_error_fraction=std::max(audit.max_unconditioned_target_error_fraction,error/bound);
            audit.max_target_error_fraction=std::max(audit.max_target_error_fraction,certified_error/bound);
            if(certified_error>bound)throw std::runtime_error("conditioned raw-target/plane reconstruction error");
            const auto& triangle=scene_.triangles.at(target.triangle);
            const auto normal=normalize(cross(triangle.v1-triangle.v0,triangle.v2-triangle.v0));
            const double cosine=std::abs(dot(normal,direction));
            if(!(cosine>0))return -kInf;
            log_density+=std::log(pdf)+std::log(cosine)-std::log(d2);
            current=whole_state(target,direction);
            if(coincident)current.alternative_self=hit.tri;
        }
        if(endpoint)*endpoint=current;
        return log_density;
    }

    void whole_density_prefixes(WholeState current,const std::vector<WholeRaw>& targets,
                         bool light_first,WholeAudit& audit,double cumulative[8],WholeState* endpoint=nullptr,Rgb* physical=nullptr) const {
        std::fill(cumulative,cumulative+8,-kInf);cumulative[0]=0;
        ++audit.density_reconstructions;
        double log_density=0;
        for(size_t i=0;i<targets.size();++i) {
            const auto& target=targets[i];const auto delta=target.point-current.origin;
            const double d2=dot(delta,delta);
            if(!(d2>0))return;
            const double distance=std::sqrt(d2);const V3 direction=delta*(1.0/distance);
            const bool sphere=light_first&&i==0;
            const double pdf=sphere?1.0/(4*kPi):std::max(0.0,dot(current.normal,direction))/kPi;
            if(!(pdf>0))return;
            ++audit.bvh_queries;
            const auto hit=bvh_.closest({current.origin,direction},sphere?offset_:0.0,
                sphere?kInf:(scene_.secondary_far_camera?scene_.camera.far:kInf),current.raw.triangle);
            if(current.alternative_self!=UINT32_MAX) {
                ++audit.bvh_queries;++audit.alternative_ray_checks;
                const auto alternative=bvh_.closest({current.origin,direction},sphere?offset_:0.0,
                    sphere?kInf:(scene_.secondary_far_camera?scene_.camera.far:kInf),current.alternative_self);
                if(hit.hit()!=alternative.hit()||(hit.hit()&&
                    (hit.tri!=alternative.tri||std::memcmp(&hit.t,&alternative.t,sizeof(double))!=0)))
                    throw std::runtime_error("coincident alternative self changes actual visibility");
            }
            if(!hit.hit())return;
            const bool coincident=hit.tri!=target.triangle;
            if(coincident&&!whole_coincident(target,hit.tri,direction,audit)) {
                if(audit.unmatched_visibility++<8)std::fprintf(stderr,"unmatched target=%u hit=%u point=%.17g,%.17g,%.17g\n",
                    target.triangle,hit.tri,target.point.x,target.point.y,target.point.z);
                return;
            }
            const V3 actual=current.origin+direction*hit.t;
            const double error=length(actual-target.point);
            const double bound=256*std::numeric_limits<double>::epsilon()*
                (1+length(current.origin)+length(target.point)+distance);
            const auto& numeric_triangle=scene_.triangles.at(target.triangle);
            const auto numeric_normal=normalize(cross(numeric_triangle.v1-numeric_triangle.v0,numeric_triangle.v2-numeric_triangle.v0));
            const double target_plane_error=std::abs(dot(numeric_normal,target.point-numeric_triangle.v0));
            const double actual_plane_error=std::abs(dot(numeric_normal,actual-numeric_triangle.v0));
            const double conditioned_error=error*std::abs(dot(numeric_normal,direction));
            const double certified_error=std::max({target_plane_error,actual_plane_error,conditioned_error});
            audit.max_unconditioned_target_error_fraction=std::max(audit.max_unconditioned_target_error_fraction,error/bound);
            audit.max_target_error_fraction=std::max(audit.max_target_error_fraction,certified_error/bound);
            if(certified_error>bound)throw std::runtime_error("conditioned raw-target/plane reconstruction error");
            const auto& triangle=scene_.triangles.at(target.triangle);
            const auto normal=normalize(cross(triangle.v1-triangle.v0,triangle.v2-triangle.v0));
            const double cosine=std::abs(dot(normal,direction));
            if(!(cosine>0))return;
            log_density+=std::log(pdf)+std::log(cosine)-std::log(d2);
            if(physical) {
                const auto& material=scene_.materials[triangle.material];
                if(!material.two_sided&&!(dot(normal,direction)<0))*physical={0,0,0};
                if(i+1<targets.size())for(int c=0;c<3;++c)(*physical)[c]*=material.rho[c];
            }
            current=whole_state(target,direction);
            if(coincident)current.alternative_self=hit.tri;
            cumulative[i+1]=log_density;
        }
        if(endpoint)*endpoint=current;

    }

    static void whole_check_density(double sampled,double reconstructed,WholeAudit& audit) {
        if(!std::isfinite(sampled)||!std::isfinite(reconstructed))
            throw std::runtime_error("generated own-family prefix has zero/nonfinite density");
        const double error=std::abs(sampled-reconstructed);
        ++audit.own_checks;audit.max_own_log_error=std::max(audit.max_own_log_error,error);
        if(error>1e-6)throw std::runtime_error("own-family area-density mismatch");
    }

    static double whole_weight(double log_eye,double log_light,WholeAudit& audit) {
        if(!std::isfinite(log_eye))return 0;
        if(!std::isfinite(log_light)){audit.max_weight=std::max(audit.max_weight,2.0);return 2;}
        const double delta=log_light-log_eye;
        const double weight=delta>0?2*std::exp(-delta)/(1+std::exp(-delta)):2/(1+std::exp(delta));
        if(!std::isfinite(weight)||weight<0||weight>2)throw std::runtime_error("path mixture weight");
        audit.max_weight=std::max(audit.max_weight,weight);return weight;
    }

    Rgb whole_direct(const WholeState& endpoint,WholeAudit& audit) const {
        struct NoRandom {double uniform(){throw std::runtime_error("whole-path point-light RNG assumption");}} rng;
        const auto e=direct(endpoint.origin,endpoint.normal,endpoint.raw.triangle,rng,audit.direct_counters);
        if(endpoint.alternative_self!=UINT32_MAX) {
            RenderCounters original_counters,alternative_counters;
            const auto control=direct(endpoint.origin,endpoint.normal,endpoint.raw.triangle,rng,original_counters);
            const auto alternative=direct(endpoint.origin,endpoint.normal,endpoint.alternative_self,rng,alternative_counters);
            ++audit.alternative_direct_checks;
            if(std::memcmp(control.data(),alternative.data(),3*sizeof(double))!=0||
               original_counters.shadow_tests!=alternative_counters.shadow_tests||
               original_counters.shadow_blocked!=alternative_counters.shadow_blocked)
                throw std::runtime_error("coincident alternative self changes direct visibility");
        }
        const auto& material=scene_.materials[scene_.triangles[endpoint.raw.triangle].material];
        Rgb reflected{};for(int c=0;c<3;++c)reflected[c]=material.rho[c]/kPi*e[c];
        return reflected;
    }


    // Plan075: all split strategies, one uniformly selected per depth.
    template<class Rng>
    void whole_sample_legacy(uint32_t x,uint32_t y,Rng& rng,Rgb out[kComponents],
                      const PrimaryCache& cache,WholeAudit& audit,double depth[8]) const {
        for(int c=0;c<kComponents;++c)out[c]={0,0,0};
        if(!cache.hit_ready)throw std::runtime_error("all-split primary cache not initialized");
        if(!cache.hit.hit())return;
        if(!cache.direct_ready)throw std::runtime_error("all-split primary direct cache missing");
        const auto camera_ray=primary_ray(x,y,0.5,0.5);
        const WholeState primary=whole_state({cache.hit.tri,camera_ray.origin+camera_ray.dir*cache.hit.t},camera_ray.dir);
        const auto& primary_material=scene_.materials[scene_.triangles[cache.hit.tri].material];
        for(int c=0;c<3;++c)out[kDirect][c]=primary_material.rho[c]/kPi*cache.direct[c];
        const WholeState light{{UINT32_MAX,scene_.points[0].position},{},scene_.points[0].position};
        double uniform[14];for(auto& u:uniform)u=rng.uniform();
        for(uint32_t k=1;k<8;++k) {
            const uint32_t split=std::min(k,uint32_t((k+1)*uniform[0])),eye_length=k-split;
            ++audit.strategy_counts[k][split];++audit.component_attempts;
            const double remap=(k+1)*uniform[0]-split;
            uint32_t dimension=0;double sampled_log=0;
            const auto next_uniform=[&]() {const auto d=dimension++;return d==0?remap:uniform[d];};
            std::vector<WholeRaw> eye,from_light;
            const auto generate=[&](WholeState current,uint32_t count,bool light_first,std::vector<WholeRaw>& vertices) {
                for(uint32_t i=0;i<count;++i) {
                    const double u=next_uniform(),v=next_uniform();const bool sphere=light_first&&i==0;
                    V3 direction;
                    if(sphere) {const double z=1-2*u,r=std::sqrt(std::max(0.0,1-z*z)),phi=2*kPi*v;
                        direction={r*std::cos(phi),r*std::sin(phi),z};}
                    else direction=cosine_sample(current.normal,u,v);
                    const double pdf=sphere?1.0/(4*kPi):std::max(0.0,dot(current.normal,direction))/kPi;
                    ++audit.bvh_queries;
                    const auto hit=bvh_.closest({current.origin,direction},sphere?offset_:0.0,
                        sphere?kInf:(scene_.secondary_far_camera?scene_.camera.far:kInf),current.raw.triangle);
                    if(!hit.hit())return false;
                    const auto& triangle=scene_.triangles.at(hit.tri);
                    const auto normal=normalize(cross(triangle.v1-triangle.v0,triangle.v2-triangle.v0));
                    const double cosine=std::abs(dot(normal,direction));
                    if(!(pdf>0&&cosine>0&&hit.t>0))throw std::runtime_error("all-split sampled density nonpositive");
                    sampled_log+=std::log(pdf)+std::log(cosine)-std::log(hit.t*hit.t);
                    vertices.push_back({hit.tri,current.origin+direction*hit.t});
                    current=whole_state(vertices.back(),direction);++audit.prefixes;
                }
                return true;
            };
            if(!generate(primary,eye_length,false,eye)||!generate(light,split,true,from_light)) {
                ++audit.component_nulls;continue;
            }
            if(dimension!=2*k)throw std::runtime_error("all-split net dimension boundary");
            std::vector<WholeRaw> path=eye;path.insert(path.end(),from_light.rbegin(),from_light.rend());
            double log_q[8];WholeState endpoint;
            for(uint32_t j=0;j<=k;++j) {
                const std::vector<WholeRaw> prefix(path.begin(),path.begin()+(k-j));
                const std::vector<WholeRaw> suffix(path.rbegin(),path.rbegin()+j);
                const double e=whole_density(primary,prefix,false,audit,j==0?&endpoint:nullptr);
                const double l=whole_density(light,suffix,true,audit);
                log_q[j]=e+l;
            }
            try {whole_check_density(sampled_log,log_q[split],audit);}
            catch(...) {
                std::fprintf(stderr,"ALL_SPLIT_OWN x=%u y=%u k=%u split=%u sampled=%.17g reconstructed=%.17g\n",x,y,k,split,sampled_log,log_q[split]);
                for(const auto& raw:path)std::fprintf(stderr,"OWN_VERTEX tri=%u point=%.17g,%.17g,%.17g\n",raw.triangle,raw.point.x,raw.point.y,raw.point.z);
                throw;
            }
            if(!std::isfinite(log_q[0])){++audit.forward_null;continue;}
            double largest=log_q[0];for(uint32_t j=1;j<=k;++j)largest=std::max(largest,log_q[j]);
            double sum=0;for(uint32_t j=0;j<=k;++j)sum+=std::exp(log_q[j]-largest);
            const double weight=(k+1)*std::exp(log_q[0]-largest)/sum;
            if(!std::isfinite(weight)||weight<0||weight>k+1)throw std::runtime_error("all-split bounded weight");
            audit.max_weight=std::max(audit.max_weight,weight);audit.max_depth_weight[k]=std::max(audit.max_depth_weight[k],weight);
            const auto reflected=whole_direct(endpoint,audit);
            for(int c=0;c<3;++c)out[kIndirect][c]+=weight*reflected[c];
            depth[k]=weight*(0.2126*reflected[0]+0.7152*reflected[1]+0.0722*reflected[2]);
        }
    }

    // Plan078: same proposal, ordered-prefix reuse and general physical target.
    template<class Rng>
    void whole_sample(uint32_t x,uint32_t y,Rng& rng,Rgb out[kComponents],
                      const PrimaryCache& cache,WholeAudit& audit,double depth[8]) const {
        for(int c=0;c<kComponents;++c)out[c]={0,0,0};
        if(!cache.hit_ready)throw std::runtime_error("all-split primary cache not initialized");
        if(!cache.hit.hit())return;
        const auto camera_ray=primary_ray(x,y,0.5,0.5);
        const WholeState primary=whole_state({cache.hit.tri,camera_ray.origin+camera_ray.dir*cache.hit.t},camera_ray.dir);
        const auto& primary_material=scene_.materials[scene_.triangles[cache.hit.tri].material];
        const auto& primary_triangle=scene_.triangles[cache.hit.tri];
        const auto primary_ng=normalize(cross(primary_triangle.v1-primary_triangle.v0,primary_triangle.v2-primary_triangle.v0));
        if(!primary_material.two_sided&&!(dot(primary_ng,camera_ray.dir)<0))return;
        if(primary_material.rho==Rgb{0,0,0})return;
        if(!cache.direct_ready)throw std::runtime_error("all-split primary direct cache missing");
        for(int c=0;c<3;++c)out[kDirect][c]=primary_material.rho[c]/kPi*cache.direct[c];
        if(scene_.max_bounces==1)return;
        const WholeState light{{UINT32_MAX,scene_.points[0].position},{},scene_.points[0].position};
        double uniform[14];for(auto& u:uniform)u=rng.uniform();
        for(uint32_t k=1;k<scene_.max_bounces;++k) {
            const uint32_t split=std::min(k,uint32_t((k+1)*uniform[0])),eye_length=k-split;
            ++audit.strategy_counts[k][split];++audit.component_attempts;
            const double remap=(k+1)*uniform[0]-split;
            uint32_t dimension=0;double sampled_log=0;
            const auto next_uniform=[&]() {const auto d=dimension++;return d==0?remap:uniform[d];};
            std::vector<WholeRaw> eye,from_light;
            const auto generate=[&](WholeState current,uint32_t count,bool light_first,std::vector<WholeRaw>& vertices) {
                for(uint32_t i=0;i<count;++i) {
                    const double u=next_uniform(),v=next_uniform();const bool sphere=light_first&&i==0;
                    V3 direction;
                    if(sphere) {const double z=1-2*u,r=std::sqrt(std::max(0.0,1-z*z)),phi=2*kPi*v;
                        direction={r*std::cos(phi),r*std::sin(phi),z};}
                    else direction=cosine_sample(current.normal,u,v);
                    const double pdf=sphere?1.0/(4*kPi):std::max(0.0,dot(current.normal,direction))/kPi;
                    ++audit.bvh_queries;
                    const auto hit=bvh_.closest({current.origin,direction},sphere?offset_:0.0,
                        sphere?kInf:(scene_.secondary_far_camera?scene_.camera.far:kInf),current.raw.triangle);
                    if(!hit.hit())return false;
                    const auto& triangle=scene_.triangles.at(hit.tri);
                    const auto normal=normalize(cross(triangle.v1-triangle.v0,triangle.v2-triangle.v0));
                    const double cosine=std::abs(dot(normal,direction));
                    if(!(pdf>0&&cosine>0&&hit.t>0))throw std::runtime_error("all-split sampled density nonpositive");
                    sampled_log+=std::log(pdf)+std::log(cosine)-std::log(hit.t*hit.t);
                    vertices.push_back({hit.tri,current.origin+direction*hit.t});
                    current=whole_state(vertices.back(),direction);++audit.prefixes;
                }
                return true;
            };
            if(!generate(primary,eye_length,false,eye)||!generate(light,split,true,from_light)) {
                ++audit.component_nulls;continue;
            }
            if(dimension!=2*k)throw std::runtime_error("all-split net dimension boundary");
            std::vector<WholeRaw> path=eye;path.insert(path.end(),from_light.rbegin(),from_light.rend());
            double log_q[8],eye_logs[8],light_logs[8];WholeState endpoint;
            Rgb throughput=primary_material.rho;
            const std::vector<WholeRaw> reverse(path.rbegin(),path.rend());
            whole_density_prefixes(primary,path,false,audit,eye_logs,&endpoint,&throughput);
            whole_density_prefixes(light,reverse,true,audit,light_logs);
            for(uint32_t j=0;j<=k;++j)log_q[j]=eye_logs[k-j]+light_logs[j];
            try {whole_check_density(sampled_log,log_q[split],audit);}
            catch(...) {
                std::fprintf(stderr,"ALL_SPLIT_OWN x=%u y=%u k=%u split=%u sampled=%.17g reconstructed=%.17g\n",x,y,k,split,sampled_log,log_q[split]);
                for(const auto& raw:path)std::fprintf(stderr,"OWN_VERTEX tri=%u point=%.17g,%.17g,%.17g\n",raw.triangle,raw.point.x,raw.point.y,raw.point.z);
                throw;
            }
            if(!std::isfinite(log_q[0])){++audit.forward_null;continue;}
            double largest=log_q[0];for(uint32_t j=1;j<=k;++j)largest=std::max(largest,log_q[j]);
            double sum=0;for(uint32_t j=0;j<=k;++j)sum+=std::exp(log_q[j]-largest);
            const double weight=(k+1)*std::exp(log_q[0]-largest)/sum;
            if(!std::isfinite(weight)||weight<0||weight>k+1)throw std::runtime_error("all-split bounded weight");
            audit.max_weight=std::max(audit.max_weight,weight);audit.max_depth_weight[k]=std::max(audit.max_depth_weight[k],weight);
            if(throughput==Rgb{0,0,0})continue;
            auto reflected=whole_direct(endpoint,audit);
            for(int c=0;c<3;++c)reflected[c]*=throughput[c];
            for(int c=0;c<3;++c)out[kIndirect][c]+=weight*reflected[c];
            depth[k]=weight*(0.2126*reflected[0]+0.7152*reflected[1]+0.0722*reflected[2]);
        }
    }
