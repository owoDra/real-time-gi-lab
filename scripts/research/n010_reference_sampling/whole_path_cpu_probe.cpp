// Plan110/111: original CPU all-split, eight fixed C1 pixels, sample index zero.
// Independent of GPU math and the host's manually assembled GPrimary records.
#include "n010_reference_snapshot.hpp"
#include <iomanip>
#include <iostream>
namespace N = phos::gi::research::n008;
int main(int argc, char** argv) {
    if (argc != 5) return 2;
    try {
        N::N010NetRng::load(argv[1]);
        std::ifstream file(argv[2]);
        if (!file) throw std::runtime_error("missing scene");
        const auto scene = N::parse_scene(file);
        if (scene.width != 320 || scene.height != 180 || scene.max_bounces != 8 ||
            scene.points.size() != 1 || scene.sampling != N::Sampling::Center)
            throw std::runtime_error("requires fixed C1 scope");
        const auto seed = std::stoull(argv[3]);
        const N::Oracle oracle(scene);
        std::ofstream out(argv[4]);
        out << std::setprecision(17) << "[";
        bool comma = false;
        for (uint32_t y : {30u, 150u}) for (uint32_t x : {40u, 120u, 200u, 280u}) {
            N::Oracle::PrimaryCache cache;
            N::RenderCounters counters;
            N::PrimaryRecord primary;
            N::Rgb components[N::kComponents]{};
            N::N010NetRng rng(seed, size_t(y)*320+x, 0);
            oracle.sample_all_split(x, y, rng, components, counters, &primary, &cache);
            if (!cache.hit.hit() || !std::isfinite(primary.t) || primary.t < 0 ||
                !cache.hit_ready || !cache.direct_ready)
                throw std::runtime_error("unexpected fixed primary");
            const auto ray=oracle.primary_ray(x,y,.5,.5);
            const auto state=oracle.whole_state({cache.hit.tri,ray.origin+ray.dir*cache.hit.t},ray.dir);
            const auto material=scene.materials[scene.triangles[cache.hit.tri].material];
            if ((!material.two_sided && !primary.front) || material.rho==N::Rgb{0,0,0})
                throw std::runtime_error("unexpected absorbed fixed primary");
            double values[12]{};
            for (int k=0; k<3; ++k) for (int c=0; c<3; ++c) values[k*3+c]=components[k][c];
            for (int c=0; c<3; ++c) values[9+c]=(values[c]+values[3+c])+values[6+c];
            for (double v : values) if (!std::isfinite(v) || v < 0)
                throw std::runtime_error("invalid CPU probe radiance");
            if (comma) out << ',';
            comma=true;
            out << "{\"x\":" << x << ",\"y\":" << y << ",\"seed\":" << seed
                << ",\"sample_index\":0,\"primary_t\":" << primary.t
                << ",\"primary_triangle\":" << primary.tri << ",\"primary_front\":" << primary.front
                << ",\"cache_shadow_tests\":" << cache.shadow_tests
                << ",\"cache_shadow_blocked\":" << cache.shadow_blocked
                << ",\"counters\":[" << counters.primary_hits << ',' << counters.shadow_tests
                << ',' << counters.shadow_blocked << ',' << counters.backface_absorbed << ']';
            const double primary_values[]={state.origin.x,state.origin.y,state.origin.z,1,
                state.normal.x,state.normal.y,state.normal.z,double(primary.tri),
                material.rho[0],material.rho[1],material.rho[2],0,
                components[N::kDirect][0],components[N::kDirect][1],components[N::kDirect][2],0,
                components[N::kEmission][0],components[N::kEmission][1],components[N::kEmission][2],0};
            out << ",\"primary_doubles\":[";
            for(int k=0;k<20;++k){if(k)out << ',';out << primary_values[k];}
            out << ']';
            for (int moment=0; moment<2; ++moment) {
                out << (moment ? ",\"second\":[" : ",\"mean\":[");
                for (int k=0; k<12; ++k) { if(k)out << ','; out << (moment ? values[k]*values[k] : values[k]); }
                out << ']';
            }
            out << '}';
        }
        out << "]\n";
        if (!out) throw std::runtime_error("CPU probe write failed");
        return 0;
    } catch (const std::exception& e) {
        std::cerr << e.what() << '\n';
        return 2;
    }
}
