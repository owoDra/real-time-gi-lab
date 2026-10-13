// N008 oracle CLI: scene file -> per-seed linear HDR PFMs + float64 moment sidecars.
#include "n008_oracle.hpp"

#include <chrono>
#include <iostream>

using namespace phos::gi::research::n008;

namespace {

std::string file_sha256(const std::string& path) {
    std::ifstream in(path, std::ios::binary);
    if (!in) throw std::runtime_error("cannot read " + path);
    Sha256 sha;
    char buf[1 << 16];
    while (in) {
        in.read(buf, sizeof buf);
        sha.update(buf, std::size_t(in.gcount()));
    }
    return sha.hex();
}

std::vector<std::uint64_t> parse_seeds(const std::string& s) {
    std::vector<std::uint64_t> seeds;
    std::stringstream ss(s);
    std::string item;
    while (std::getline(ss, item, ',')) seeds.push_back(std::stoull(item));
    if (seeds.empty()) throw std::runtime_error("no seeds");
    return seeds;
}

void write_sidecar(const std::string& path, const Scene& scene, std::uint64_t seed, std::uint32_t spp,
                   const std::vector<PixelStats>& stats) {
    std::ofstream out(path, std::ios::binary);
    if (!out) throw std::runtime_error("cannot write " + path);
    out.write("N008F64\0", 8);
    const std::uint32_t header[3] = {scene.width, scene.height, spp};
    out.write(reinterpret_cast<const char*>(header), sizeof header);
    out.write(reinterpret_cast<const char*>(&seed), sizeof seed);
    // Per pixel: mean[4][3] then second moment[4][3]; components emission,direct,indirect,total.
    const double inv = 1.0 / double(spp);
    for (const auto& ps : stats) {
        double rec[24];
        for (int k = 0; k <= kComponents; ++k)
            for (int c = 0; c < 3; ++c) {
                rec[k * 3 + c] = ps.sum[k][c] * inv;
                rec[12 + k * 3 + c] = ps.sum2[k][c] * inv;
            }
        out.write(reinterpret_cast<const char*>(rec), sizeof rec);
    }
    if (!out) throw std::runtime_error("short write " + path);
}

}  // namespace

int main(int argc, char** argv) {
    try {
        std::string scene_path, out_prefix, seeds_arg = "305419896";
        std::uint32_t spp = 1;
        std::vector<std::uint32_t> checkpoints;
        unsigned threads = std::max(1U, std::thread::hardware_concurrency());
        for (int i = 1; i < argc; ++i) {
            const std::string a = argv[i];
            auto value = [&]() -> std::string {
                if (i + 1 >= argc) throw std::runtime_error("missing value for " + a);
                return argv[++i];
            };
            if (a == "--scene") scene_path = value();
            else if (a == "--out") out_prefix = value();
            else if (a == "--seeds") seeds_arg = value();
            else if (a == "--spp") spp = std::uint32_t(std::stoul(value()));
            else if (a == "--threads") threads = unsigned(std::stoul(value()));
            else if (a == "--checkpoints") {
                std::stringstream ss(value());
                std::string item;
                while (std::getline(ss, item, ',')) checkpoints.push_back(std::uint32_t(std::stoul(item)));
            }
            else throw std::runtime_error("unknown argument " + a);
        }
        if (scene_path.empty() || out_prefix.empty() || spp == 0 || threads == 0)
            throw std::runtime_error("usage: n008_oracle --scene FILE --out PREFIX [--seeds a,b] [--spp N] [--threads N]");

        std::ifstream in(scene_path);
        if (!in) throw std::runtime_error("cannot open " + scene_path);
        const Scene scene = parse_scene(in);
        const Oracle oracle(scene);
        const auto seeds = parse_seeds(seeds_arg);
        for (std::size_t i = 0; i < checkpoints.size(); ++i)
            if (checkpoints[i] == 0 || checkpoints[i] >= spp || (i && checkpoints[i] <= checkpoints[i - 1]))
                throw std::runtime_error("checkpoints must be ascending, positive and < spp");

        std::cout << "{\"oracle\":\"n008\",\"version\":1"
                  << ",\"scene_sha256\":\"" << file_sha256(scene_path) << "\""
                  << ",\"geometry_sha256\":\"" << geometry_sha256(scene) << "\""
                  << ",\"triangles\":" << scene.triangles.size()
                  << ",\"point_lights\":" << scene.points.size()
                  << ",\"width\":" << scene.width << ",\"height\":" << scene.height
                  << ",\"spp\":" << spp << ",\"seeds\":[";
        for (std::size_t i = 0; i < seeds.size(); ++i) std::cout << (i ? "," : "") << seeds[i];
        std::printf("],\"ray_offset\":%.17g,\"runs\":[", oracle.offset());
        std::cout << std::flush;

        for (std::size_t si = 0; si < seeds.size(); ++si) {
            const auto t0 = std::chrono::steady_clock::now();
            RenderCounters counters;
            std::vector<PrimaryRecord> primary;
            std::vector<std::vector<PixelStats>> snapshots;
            const auto stats = oracle.render(seeds[si], spp, threads, counters, si == 0 ? &primary : nullptr,
                                             checkpoints, &snapshots);
            const double secs = std::chrono::duration<double>(std::chrono::steady_clock::now() - t0).count();
            const std::string base = out_prefix + ".s" + std::to_string(si);
            static const char* names[] = {"emission", "direct", "indirect", "total"};
            auto emit = [&](const std::string& prefix, const std::vector<PixelStats>& st, std::uint32_t n) {
                for (int k = 0; k <= kComponents; ++k) {
                    std::vector<float> rgb(st.size() * 3);
                    for (std::size_t p = 0; p < st.size(); ++p)
                        for (int c = 0; c < 3; ++c) rgb[p * 3 + c] = float(st[p].sum[k][c] / double(n));
                    write_pfm(prefix + "." + names[k] + ".pfm", scene.width, scene.height, rgb);
                }
                write_sidecar(prefix + ".f64", scene, seeds[si], n, st);
            };
            for (std::size_t k = 0; k < checkpoints.size(); ++k)
                emit(base + ".c" + std::to_string(checkpoints[k]), snapshots[k], checkpoints[k]);
            emit(base, stats, spp);
            if (si == 0) {
                // Per pixel (first sample of first seed): f64 t (-1 = miss), u32 triangle, u32 front flag.
                std::ofstream hits(out_prefix + ".hits", std::ios::binary);
                hits.write("N008HIT\0", 8);
                const std::uint32_t wh[2] = {scene.width, scene.height};
                hits.write(reinterpret_cast<const char*>(wh), sizeof wh);
                for (const auto& r : primary) {
                    hits.write(reinterpret_cast<const char*>(&r.t), 8);
                    hits.write(reinterpret_cast<const char*>(&r.tri), 4);
                    hits.write(reinterpret_cast<const char*>(&r.front), 4);
                }
                if (!hits) throw std::runtime_error("short write hits");
            }
            std::printf("%s{\"seed\":%llu,\"prefix\":\"%s\",\"primary_hits\":%llu,\"shadow_tests\":%llu,"
                        "\"shadow_blocked\":%llu,\"backface_absorbed\":%llu,\"cpu_seconds_diagnostic\":%.3f}",
                        si ? "," : "", static_cast<unsigned long long>(seeds[si]), base.c_str(),
                        static_cast<unsigned long long>(counters.primary_hits),
                        static_cast<unsigned long long>(counters.shadow_tests),
                        static_cast<unsigned long long>(counters.shadow_blocked),
                        static_cast<unsigned long long>(counters.backface_absorbed), secs);
            std::fflush(stdout);
        }
        std::printf("]}\n");
        return 0;
    } catch (const std::exception& e) {
        std::cerr << "n008_oracle: " << e.what() << "\n";
        return 1;
    }
}
