    // Plan139 private candidate. High points preserve the original spawn input.
    static WholeRaw whole_precise_hit(uint32_t triangle,V3 origin,V3 direction,double t) {
        const V3 product=direction*t;
        const V3 point=origin+product;
        const V3 z=point-origin;
        const V3 addition_low=(origin-(point-z))+(product-z);
        const V3 product_low={std::fma(direction.x,t,-product.x),
                              std::fma(direction.y,t,-product.y),
                              std::fma(direction.z,t,-product.z)};
        return {triangle,point,addition_low+product_low};
    }

    static V3 whole_precise_delta(const WholeRaw& target,V3 origin) {
        const V3 delta=target.point-origin;
        const V3 z=delta-target.point;
        const V3 subtraction_low=(target.point-(delta-z))-(origin+z);
        return delta+(subtraction_low+target.low);
    }

    static void whole_log_precision(const char* stage,bool light,uint32_t index,
                                    const WholeRaw& target,V3 delta) {
        if(!n010_density_witness_enabled||n010_density_witness_k!=4)return;
        std::fprintf(stderr,"RAW_PRECISION {\"stage\":\"%s\",\"light\":%s,\"index\":%u,\"low\":[%.17g,%.17g,%.17g],\"delta\":[%.17g,%.17g,%.17g]}\n",
            stage,light?"true":"false",index,target.low.x,target.low.y,target.low.z,
            delta.x,delta.y,delta.z);
    }
