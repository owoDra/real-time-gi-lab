    // N010 plan 040: light-visible surface proposal; unchanged transport evaluator.
    struct GuideRay { V3 direction{}; uint32_t target{UINT32_MAX};
        double cosine_pdf{}; bool guided{}, valid{}; };
    std::vector<double> guide_cdf_;
    double guide_total_{};
    static constexpr double guide_cosine_fraction=0.75;
    void build_guide() {
        for(const auto& light:scene_.points) {
            const double weight=std::max({0.0,light.intensity[0],light.intensity[1],light.intensity[2]});
            guide_total_+=weight;guide_cdf_.push_back(guide_total_);
        }
        if(!(guide_total_>0)){guide_cdf_.clear();guide_total_=0;return;}
        if(!std::isfinite(guide_total_))throw std::runtime_error("invalid light guide CDF");
    }
    double guide_probability(uint32_t light) const {
        if(guide_cdf_.empty() || light>=guide_cdf_.size())return 0;
        return (guide_cdf_[light]-(light?guide_cdf_[light-1]:0))/guide_total_;
    }
    double guide_area_density(uint32_t triangle,V3 point,V3 normal) const {
        double density=0;
        for(uint32_t i=0;i<scene_.points.size();++i) {
            const double probability=guide_probability(i);
            if(!(probability>0))continue;
            const auto& light=scene_.points[i];
            const auto delta=point-light.position;const double d2=dot(delta,delta);
            if(!(d2>offset_*offset_))continue;
            const auto direction=delta*(1.0/std::sqrt(d2));
            const auto exposed=bvh_.closest({light.position,direction},offset_,kInf,UINT32_MAX);
            if(!exposed.hit() || exposed.tri!=triangle)continue;
            density+=probability*std::abs(dot(normal,direction))/(4*kPi*d2);
        }
        return density;
    }
    GuideRay guide_sample(V3 origin,V3 normal,double u1,double u2) const {
        if(guide_cdf_.empty() || u1<guide_cosine_fraction) {
            const auto direction=cosine_sample(normal,guide_cdf_.empty()?u1:u1/guide_cosine_fraction,u2);
            return {direction,UINT32_MAX,std::max(0.0,dot(normal,direction))/kPi,false,true};
        }
        const double pick=(u1-guide_cosine_fraction)/(1-guide_cosine_fraction)*guide_total_;
        const auto found=std::upper_bound(guide_cdf_.begin(),guide_cdf_.end(),pick);
        if(found==guide_cdf_.end())throw std::runtime_error("light guide CDF selection overflow");
        const uint32_t selected=uint32_t(found-guide_cdf_.begin());
        const double old=selected?guide_cdf_[selected-1]:0,width=*found-old;
        if(!(width>0))throw std::runtime_error("zero-width selected light");
        const double remap=(pick-old)/width;
        if(!(remap>=0 && remap<1))throw std::runtime_error("light conditional uniform outside range");
        const double z=1-2*remap,phi=2*kPi*u2,r=std::sqrt(std::max(0.0,1-z*z));
        const V3 emitted{r*std::cos(phi),r*std::sin(phi),z};
        const auto& light=scene_.points[selected];
        const auto target=bvh_.closest({light.position,emitted},offset_,kInf,UINT32_MAX);
        if(!target.hit())return {};
        const auto point=light.position+emitted*target.t;
        const auto delta=point-origin;const double d2=dot(delta,delta);
        if(!(d2>0))return {};
        const auto direction=delta*(1.0/std::sqrt(d2));const double cosine=dot(normal,direction);
        return {direction,target.tri,std::max(0.0,cosine)/kPi,true,cosine>0};
    }
