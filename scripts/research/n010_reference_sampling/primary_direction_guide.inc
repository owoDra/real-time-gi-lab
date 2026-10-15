    // Plan 043: deterministic direction histogram at the fixed primary surface.
    struct DirectionGuide {
        std::array<double,256> cdf{};
        bool ready{};
    };
    mutable std::vector<DirectionGuide> direction_guides_;
    const DirectionGuide& primary_direction_guide(uint32_t x,uint32_t y,
                                                  V3 origin,V3 normal,uint32_t self) const {
        auto& guide=direction_guides_[size_t(y)*scene_.width+x];
        if(guide.ready)return guide;
        double total=0;
        const double far=scene_.secondary_far_camera?scene_.camera.far:kInf;
        for(uint32_t bin=0;bin<256;++bin) {
            double weight=0;
            for(uint32_t sv=0;sv<2;++sv)for(uint32_t su=0;su<2;++su) {
                const double u=(double(bin%16)+(double(su)+0.5)/2)/16;
                const double v=(double(bin/16)+(double(sv)+0.5)/2)/16;
                const auto direction=cosine_sample(normal,u,v);
                const auto hit=bvh_.closest({origin,direction},0.0,far,self);
                if(!hit.hit())continue;
                const auto& triangle=scene_.triangles[hit.tri];
                const auto& material=scene_.materials[triangle.material];
                const auto ng=normalize(cross(triangle.v1-triangle.v0,triangle.v2-triangle.v0));
                const bool front=dot(ng,direction)<0;
                if(!front&&!material.two_sided)continue;
                const auto n=front?ng:ng*-1.0;
                const auto point=nudge_inside(triangle,origin+direction*hit.t)+n*offset_;
                Xoshiro256 unused_rng(0,0,0);RenderCounters pilot_counters{};
                const auto e=direct(point,n,hit.tri,unused_rng,pilot_counters);
                weight+=std::max({material.rho[0]*e[0]/kPi,
                                  material.rho[1]*e[1]/kPi,material.rho[2]*e[2]/kPi});
            }
            if(!(weight>=0)||!std::isfinite(weight))throw std::runtime_error("invalid directional pilot weight");
            total+=weight;guide.cdf[bin]=total;
        }
        if(!std::isfinite(total))throw std::runtime_error("invalid directional CDF");
        guide.ready=true;
        return guide;
    }
    struct DirectionDraw {V3 direction;double correction;};
    DirectionDraw primary_direction_sample(const DirectionGuide& guide,V3 normal,double u,double v) const {
        const double total=guide.cdf.back();
        if(!(total>0))return {cosine_sample(normal,u,v),1};
        uint32_t bin;
        if(u<0.5) {
            u*=2;
            bin=uint32_t(v*16)*16+uint32_t(u*16);
        } else {
            const double pick=(u-0.5)*2*total;
            const auto found=std::upper_bound(guide.cdf.begin(),guide.cdf.end(),pick);
            if(found==guide.cdf.end())throw std::runtime_error("direction CDF selection overflow");
            bin=uint32_t(found-guide.cdf.begin());
            const double old=bin?guide.cdf[bin-1]:0,width=*found-old;
            if(!(width>0))throw std::runtime_error("zero selected direction bin");
            const double remap=(pick-old)/width;
            if(!(remap>=0&&remap<1))throw std::runtime_error("direction conditional uniform outside range");
            u=(double(bin%16)+remap)/16;
            v=(double(bin/16)+v)/16;
        }
        const double old=bin?guide.cdf[bin-1]:0;
        const double probability=(guide.cdf[bin]-old)/total;
        const double density=0.5+128*probability;
        if(!(density>=0.5)||!std::isfinite(density))throw std::runtime_error("invalid direction density");
        return {cosine_sample(normal,u,v),1/density};
    }
