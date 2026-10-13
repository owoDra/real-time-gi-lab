// N009 WP-PT: CPU-only counterfactual ladder of the Renderer's probe-indirect
// estimator on one GPU-run capture (N007 capture layout). Each stage changes one
// factor of the GPU estimator, in the preregistered order:
//   R0 exact integer replay of the GPU probe aggregation (must equal GPU indirect)
//   R1 R0 without 16-bit quantisation (float per-ray values from the GPU hits)
//   R2 R1 + shadow ray at every secondary hit (oracle BVH, two-sided)
//   R3 R2 for EVERY probe key a visible pixel looks up (CPU-traced; full coverage)
//   R4 R3 with the last cascade interval unbounded (no range truncation)
//   R5 R4 with N dense Fibonacci directions instead of the 8 cube diagonals
//   R6 pixel-centred cosine-weighted one-bounce estimator (the oracle definition)
// Geometry, intersection and RNG come from the independent N008 oracle header.
// Diagnostic only: the Renderer is not modified.
#include "n008_oracle.hpp"

#include <algorithm>
#include <array>
#include <atomic>
#include <memory>
#include <cmath>
#include <cstdint>
#include <cstring>
#include <filesystem>
#include <fstream>
#include <iostream>
#include <map>
#include <stdexcept>
#include <string>
#include <thread>
#include <unordered_map>
#include <vector>

namespace fs = std::filesystem;
namespace o = phos::gi::research::n008;
using o::V3;

namespace {

struct Params {
    float cam[4], right[4], up[4], fwd[4], origin[4], light[4];
    std::uint32_t counts[4], limits[4];
};
struct Work {
    std::int32_t px, py, pz;
    std::uint32_t cascade, ray, output, surface, tile;
    float imin, imax, dx, dy, dz, ppx, ppy, ppz;
};
struct GHit {
    float n[3], t;
    std::uint32_t prim, mat, inst, flag;
};
struct Contrib {
    std::uint32_t output, value;
};
static_assert(sizeof(Params) == 128 && sizeof(Work) == 64 && sizeof(GHit) == 32 && sizeof(Contrib) == 8);

std::vector<char> slurp(const fs::path& p) {
    std::ifstream in(p, std::ios::binary);
    if (!in) throw std::runtime_error("cannot open " + p.string());
    return std::vector<char>(std::istreambuf_iterator<char>(in), {});
}
template <class T> std::vector<T> records(const fs::path& p) {
    const auto raw = slurp(p);
    if (raw.size() % sizeof(T)) throw std::runtime_error("misaligned " + p.string());
    std::vector<T> out(raw.size() / sizeof(T));
    std::memcpy(out.data(), raw.data(), raw.size());
    return out;
}

using Key = std::array<std::int32_t, 4>;  // probe xyz + cascade
struct KeyHash {
    std::size_t operator()(const Key& k) const {
        std::uint64_t h = 1469598103934665603ULL;
        for (auto v : k) { h ^= std::uint32_t(v); h *= 1099511628211ULL; }
        return std::size_t(h);
    }
};

template <class F> void parallel_for(std::size_t n, unsigned threads, F&& f) {
    std::atomic<std::size_t> next{0};
    std::vector<std::thread> pool;
    for (unsigned t = 0; t < threads; ++t)
        pool.emplace_back([&] {
            for (;;) {
                const auto i = next.fetch_add(1);
                if (i >= n) return;
                f(i);
            }
        });
    for (auto& th : pool) th.join();
}

struct Model {
    std::vector<o::Triangle> tris;
    std::unordered_map<std::uint32_t, std::uint32_t> prim_index;
    std::unique_ptr<o::Bvh> bvh;
    Params p{};
    std::uint32_t w{}, h{};
    double eps{}, s{};
    V3 light;

    double l_dir(V3 pos, V3 n, V3 incoming, std::uint32_t self, bool shadow) const {
        n = o::normalize(n);
        if (o::dot(n, incoming * -1.0) < 0.0) n = n * -1.0;
        const V3 l = light - pos;
        const double d2 = o::dot(l, l);
        if (!(d2 > 1e-12)) return 0.0;
        const double d = std::sqrt(d2);
        const V3 wi = l * (1.0 / d);
        const double c = o::dot(n, wi);
        if (!(c > 0.0)) return 0.0;
        if (shadow && d > 2.0 * eps && bvh->occluded({pos + n * eps, wi}, d - eps, self, self)) return 0.0;
        const double sc = std::max(s, 1e-6);
        return c * (sc * sc / (sc * sc + d2)) / o::kPi;
    }
    // Closest hit like the Renderer's secondary traversal (t in (1e-4, tmax]).
    double trace_value(V3 origin, V3 dir, double tmax, double* t_out = nullptr) const {
        const o::Hit hit = bvh->closest({origin, dir}, 1e-4, tmax, std::numeric_limits<std::uint32_t>::max());
        if (t_out) *t_out = hit.hit() ? hit.t : -1.0;
        if (!hit.hit()) return 0.0;
        const auto& t = tris[hit.tri];
        const V3 ng = o::cross(t.v1 - t.v0, t.v2 - t.v0);
        return l_dir(origin + dir * hit.t, ng, dir, hit.tri, true);
    }
};

V3 fv(const float* v) { return {double(v[0]), double(v[1]), double(v[2])}; }

}  // namespace

int main(int argc, char** argv) {
    try {
        fs::path state, capture, out;
        unsigned dense = 256, cos_spp = 256;
        unsigned threads = std::max(1U, std::thread::hardware_concurrency());
        for (int i = 1; i < argc; ++i) {
            const std::string a = argv[i];
            if (i + 1 >= argc) throw std::runtime_error("missing value for " + a);
            if (a == "--state") state = argv[++i];
            else if (a == "--capture") capture = argv[++i];
            else if (a == "--out") out = argv[++i];
            else if (a == "--dense") dense = unsigned(std::stoul(argv[++i]));
            else if (a == "--cos-spp") cos_spp = unsigned(std::stoul(argv[++i]));
            else if (a == "--threads") threads = unsigned(std::stoul(argv[++i]));
            else throw std::runtime_error("unknown argument " + a);
        }
        if (state.empty() || capture.empty() || out.empty())
            throw std::runtime_error("required: --state DIR --capture DIR --out PREFIX");
        // Attestation: the capture must be the exact frozen state.
        for (const char* f : {"geometry-state.bin", "frame-state.bin"})
            if (slurp(state / f) != slurp(capture / f)) throw std::runtime_error(std::string("capture state differs: ") + f);
        Model m;
        {
            const auto g = slurp(state / "geometry-state.bin");
            std::uint32_t ver, n;
            std::memcpy(&ver, g.data(), 4); std::memcpy(&n, g.data() + 4, 4);
            if (ver != 1 || g.size() != 8 + std::size_t(52) * n) throw std::runtime_error("bad geometry-state");
            o::Aabb box;
            for (std::uint32_t i = 0; i < n; ++i) {
                float v[9]; std::uint32_t meta[4];
                std::memcpy(v, g.data() + 8 + 52 * std::size_t(i), 36);
                std::memcpy(meta, g.data() + 8 + 52 * std::size_t(i) + 36, 16);
                o::Triangle t{{v[0], v[1], v[2]}, {v[3], v[4], v[5]}, {v[6], v[7], v[8]}, 0};
                box.grow(t.v0); box.grow(t.v1); box.grow(t.v2);
                m.tris.push_back(t);
                if (!m.prim_index.emplace(meta[0], i).second) throw std::runtime_error("duplicate primitive id");
            }
            m.eps = 1e-5 * o::length(box.hi - box.lo);
            const auto f = slurp(state / "frame-state.bin");
            if (f.size() != 148 || std::memcmp(f.data(), "N007-STATE1", 12) != 0) throw std::runtime_error("bad frame-state");
            std::memcpy(&m.w, f.data() + 12, 4); std::memcpy(&m.h, f.data() + 16, 4);
            std::memcpy(&m.p, f.data() + 20, 128);
            m.s = m.p.light[3];
            m.light = fv(m.p.light);
        }
        m.bvh = std::make_unique<o::Bvh>(m.tris);
        const std::size_t npx = std::size_t(m.w) * m.h;
        const auto prim = records<GHit>(capture / "gpu/hits.bin");
        const auto work = records<Work>(capture / "gpu/probe-work.bin");
        const auto phit = records<GHit>(capture / "gpu/probe-hits.bin");
        const auto fixed = records<Contrib>(capture / "gpu/probe-contributions.bin");
        if (prim.size() != npx || work.size() != phit.size() || work.size() != fixed.size())
            throw std::runtime_error("capture payload sizes inconsistent");
        const std::uint32_t ncas = m.p.counts[3];
        const V3 cam = fv(m.p.cam);

        // ---- per work item: float value from the GPU hit, shadow, CPU re-trace.
        std::vector<double> v_unsh(work.size()), v_sh(work.size());
        std::vector<std::uint8_t> trace_ok(work.size());
        parallel_for(work.size(), threads, [&](std::size_t k) {
            const auto& it = work[k];
            const auto& g = phit[k];
            const V3 dir = o::normalize({it.dx, it.dy, it.dz});
            const V3 origin = V3{it.ppx, it.ppy, it.ppz} + dir * double(it.imin);
            double t_cpu = -1.0;
            (void)m.trace_value(origin, dir, double(it.imax) - double(it.imin), &t_cpu);
            const bool gh = g.flag == 1U && std::isfinite(g.t);
            trace_ok[k] = (!gh && t_cpu < 0) ||
                          (gh && t_cpu >= 0 && std::abs(t_cpu - g.t) <= 1e-3 * std::max(1.0, double(g.t)));
            if (!gh) return;
            const V3 pos = origin + dir * double(g.t);
            const auto self = m.prim_index.count(g.prim) ? m.prim_index.at(g.prim) : std::numeric_limits<std::uint32_t>::max();
            v_unsh[k] = m.l_dir(pos, fv(g.n), dir, self, false);
            v_sh[k] = m.l_dir(pos, fv(g.n), dir, self, true);
        });
        std::uint64_t q_exact = 0, q_one = 0, q_other = 0, traced_match = 0;
        for (std::size_t k = 0; k < work.size(); ++k) {
            const auto pred = std::uint32_t(std::lround(std::clamp(v_unsh[k], 0.0, 1.0) * 65535.0));
            const auto d = std::abs(std::int64_t(pred) - std::int64_t(fixed[k].value));
            (d == 0 ? q_exact : d == 1 ? q_one : q_other)++;
            traced_match += trace_ok[k];
        }
        // ---- produced keys: integer replay (R0) and float aggregations (R1, R2).
        struct Acc { std::uint64_t sum{}, n{}; double f{}, fs{}; };
        std::map<std::uint32_t, Acc> outputs;
        std::map<std::uint32_t, Key> owner;
        for (std::size_t k = 0; k < work.size(); ++k) {
            auto& a = outputs[work[k].output];
            a.sum += fixed[k].value; ++a.n; a.f += v_unsh[k]; a.fs += v_sh[k];
            if (work[k].ray == 0) owner[work[k].output] = {work[k].px, work[k].py, work[k].pz, std::int32_t(work[k].cascade)};
        }
        if (owner.size() != outputs.size()) throw std::runtime_error("output grouping not one-to-one with ray-zero owners");
        struct KeyAcc { std::uint64_t imean{}; std::uint64_t n{}; double f{}, fs{}; };
        std::unordered_map<Key, KeyAcc, KeyHash> produced;
        for (const auto& [id, a] : outputs) {
            auto& ka = produced[owner.at(id)];
            ka.imean += (a.sum + a.n / 2) / a.n; ++ka.n; ka.f += a.f / double(a.n); ka.fs += a.fs / double(a.n);
        }
        // ---- pixels: GPU-identical float key computation (composite shader).
        struct Px { bool hit{}; V3 pos, n; std::uint32_t self{}; Key key[4]{}; };
        std::vector<Px> px(npx);
        std::unordered_map<Key, std::uint32_t, KeyHash> required;
        std::vector<Key> keys;
        for (std::uint32_t y = 0; y < m.h; ++y)
            for (std::uint32_t x = 0; x < m.w; ++x) {
                const auto id = std::size_t(y) * m.w + x;
                const auto& g = prim[id];
                if (g.flag != 1U || !std::isfinite(g.t)) continue;
                const float nx = (2.0F * (float(x) + 0.5F) / float(m.w)) - 1.0F;
                const float ny = 1.0F - (2.0F * (float(y) + 0.5F) / float(m.h));
                float d[3];
                for (int i = 0; i < 3; ++i) d[i] = m.p.fwd[i] + m.p.right[i] * (nx * m.p.right[3]) + m.p.up[i] * (ny * m.p.up[3]);
                const float len = std::sqrt(d[0] * d[0] + d[1] * d[1] + d[2] * d[2]);
                float pos[3];
                for (int i = 0; i < 3; ++i) { d[i] /= len; pos[i] = m.p.cam[i] + d[i] * g.t; }
                auto& q = px[id];
                q.hit = true;
                q.pos = fv(pos);
                q.n = fv(g.n);
                if (o::dot(q.n, fv(d)) > 0.0) q.n = q.n * -1.0;
                q.self = m.prim_index.count(g.prim) ? m.prim_index.at(g.prim) : std::numeric_limits<std::uint32_t>::max();
                for (std::uint32_t c = 0; c < ncas && c < 4; ++c) {
                    const float spacing = m.p.origin[3] * float(1U << c);
                    Key k{};
                    for (int i = 0; i < 3; ++i) k[i] = std::int32_t(std::floor((pos[i] - m.p.origin[i]) / spacing));
                    k[3] = std::int32_t(c);
                    q.key[c] = k;
                    if (required.emplace(k, std::uint32_t(keys.size())).second) keys.push_back(k);
                }
            }
        // ---- CPU-traced probe values for every required key (R3, R4, R5).
        std::vector<V3> fib(dense);
        for (unsigned i = 0; i < dense; ++i) {
            const double z = 1.0 - (2.0 * i + 1.0) / dense, r = std::sqrt(std::max(0.0, 1.0 - z * z));
            const double phi = i * o::kPi * (3.0 - std::sqrt(5.0));
            fib[i] = {r * std::cos(phi), r * std::sin(phi), z};
        }
        std::vector<double> r3(keys.size()), r4(keys.size()), r5(keys.size());
        parallel_for(keys.size(), threads, [&](std::size_t i) {
            const auto& k = keys[i];
            const std::uint32_t c = std::uint32_t(k[3]);
            const float spacing = m.p.origin[3] * float(1U << c);
            float pp[3];
            for (int a = 0; a < 3; ++a) pp[a] = m.p.origin[a] + (float(k[a]) + 0.5F) * spacing;
            const double imax = double(m.p.light[3] * float(1U << c));
            const double imin = c > 0 ? double(m.p.light[3] * float(1U << (c - 1U))) : 0.0;
            const bool last = c + 1 == ncas;
            const V3 probe = fv(pp);
            double a3 = 0, a4 = 0, a5 = 0;
            for (unsigned r = 0; r < 8; ++r) {
                const double v = 0.5773502691896258;
                const V3 dir = o::normalize({(r & 1U) ? v : -v, (r & 2U) ? v : -v, (r & 4U) ? v : -v});
                const V3 org = probe + dir * imin;
                a3 += m.trace_value(org, dir, imax - imin);
                a4 += last ? m.trace_value(org, dir, o::kInf) : m.trace_value(org, dir, imax - imin);
            }
            for (const auto& dir : fib) {
                const V3 org = probe + dir * imin;
                a5 += m.trace_value(org, dir, last ? o::kInf : imax - imin);
            }
            r3[i] = a3 / 8.0; r4[i] = a4 / 8.0; r5[i] = a5 / double(dense);
        });
        // ---- stage images.
        constexpr int kStages = 7;
        std::vector<double> img(std::size_t(kStages) * npx, 0.0);
        std::uint64_t px_hit = 0, px_any_missing = 0, lookups = 0, lookups_missing = 0;
        for (std::size_t id = 0; id < npx; ++id) {
            const auto& q = px[id];
            if (!q.hit) continue;
            ++px_hit;
            bool missing = false;
            for (std::uint32_t c = 0; c < ncas && c < 4; ++c) {
                ++lookups;
                const auto it = produced.find(q.key[c]);
                if (it != produced.end()) {
                    const auto& ka = it->second;
                    img[0 * npx + id] += double(ka.imean) / (double(ka.n) * 65535.0);
                    img[1 * npx + id] += ka.f / double(ka.n);
                    img[2 * npx + id] += ka.fs / double(ka.n);
                } else {
                    ++lookups_missing; missing = true;
                }
                const auto j = required.at(q.key[c]);
                img[3 * npx + id] += r3[j];
                img[4 * npx + id] += r4[j];
                img[5 * npx + id] += r5[j];
            }
            px_any_missing += missing;
        }
        parallel_for(npx, threads, [&](std::size_t id) {
            const auto& q = px[id];
            if (!q.hit) return;
            const V3 org = q.pos + q.n * m.eps;
            double acc = 0.0;
            for (unsigned smp = 0; smp < cos_spp; ++smp) {
                o::Xoshiro256 rng(0x4E30303952364FULL, id, smp);
                const double u1 = rng.uniform(), u2 = rng.uniform();
                const V3 dir = o::Oracle::cosine_sample(q.n, u1, u2);
                const o::Hit hit = m.bvh->closest({org, dir}, 0.0, o::kInf, q.self);
                if (!hit.hit()) continue;
                const auto& t = m.tris[hit.tri];
                acc += m.l_dir(org + dir * hit.t, o::cross(t.v1 - t.v0, t.v2 - t.v0), dir, hit.tri, true);
            }
            img[6 * npx + id] = acc / double(cos_spp);
        });
        std::uint64_t traced_items = work.size();
        {
            std::ofstream f(out.string() + ".stages.f64", std::ios::binary);
            f.write("N009PM1", 8);
            const std::uint32_t hdr[3] = {m.w, m.h, kStages};
            f.write(reinterpret_cast<const char*>(hdr), sizeof hdr);
            f.write(reinterpret_cast<const char*>(img.data()), std::streamsize(img.size() * sizeof(double)));
            if (!f) throw std::runtime_error("stage write failed");
        }
        std::ofstream js(out.string() + ".json");
        js << "{\"schema\":\"n009-probe-model/1\",\"stages\":[\"R0_gpu_integer_replay\",\"R1_dequantized\",\"R2_secondary_shadow\","
              "\"R3_full_probe_coverage\",\"R4_unbounded_range\",\"R5_dense_directions\",\"R6_pixel_cosine_one_bounce\"],"
           << "\"dense_directions\":" << dense << ",\"cos_spp\":" << cos_spp << ",\"shadow_eps\":" << m.eps
           << ",\"work_items\":" << traced_items << ",\"outputs\":" << outputs.size() << ",\"produced_keys\":" << produced.size()
           << ",\"required_keys\":" << keys.size() << ",\"pixels_hit\":" << px_hit << ",\"lookups\":" << lookups
           << ",\"lookups_missing_produced_key\":" << lookups_missing << ",\"pixels_with_missing_key\":" << px_any_missing
           << ",\"quantization_check\":{\"exact\":" << q_exact << ",\"off_by_one\":" << q_one << ",\"other\":" << q_other << "}"
           << ",\"cpu_retrace_matches_gpu_hit\":" << traced_match << "}\n";
        std::cout << "n009_probe_model: " << out << " written\n";
        return 0;
    } catch (const std::exception& e) {
        std::cerr << "n009_probe_model: " << e.what() << "\n";
        return 1;
    }
}
