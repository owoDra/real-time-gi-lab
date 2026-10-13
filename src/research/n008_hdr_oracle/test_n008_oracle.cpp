// N008 oracle unit tests: hashing, RNG, watertightness, BVH-vs-brute-force,
// sampling moments, PFM layout. Physical controls live in the Python harness.
#include "n008_oracle.hpp"

#include <iostream>

using namespace phos::gi::research::n008;

namespace {

int failures = 0;
void check(bool ok, const std::string& name) {
    std::cout << (ok ? "PASS " : "FAIL ") << name << "\n";
    if (!ok) ++failures;
}

double brute_closest(const std::vector<Triangle>& tris, const Ray& ray, std::uint32_t& id) {
    const WatertightRay wr(ray);
    double best = kInf;
    id = std::numeric_limits<std::uint32_t>::max();
    for (std::uint32_t i = 0; i < tris.size(); ++i) {
        const double t = wr.intersect(tris[i]);
        if (t < best || (t == best && t < kInf && i < id)) { best = t; id = i; }
    }
    return best;
}

void test_sha256() {
    Sha256 a;
    a.update("abc", 3);
    check(a.hex() == "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad", "sha256 'abc'");
    Sha256 b;
    const std::string m = "abcdbcdecdefdefgefghfghighijhijkijkljklmklmnlmnomnopnopq";
    b.update(m.data(), m.size());
    check(b.hex() == "248d6a61d20638b8e5c026930c3e6039a33ce45964ff2167f6ecedd419db06c1", "sha256 two-block");
    Sha256 c;
    check(c.hex() == "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855", "sha256 empty");
}

void test_rng() {
    Xoshiro256 a(1, 2, 3), b(1, 2, 3), c(1, 2, 4);
    bool same = true, differ = false;
    double sum = 0.0;
    for (int i = 0; i < 1000; ++i) {
        const auto x = a.next();
        same &= x == b.next();
        differ |= x != c.next();
    }
    Xoshiro256 d(7, 0, 0);
    bool in_range = true;
    const int n = 1000000;
    for (int i = 0; i < n; ++i) {
        const double u = d.uniform();
        in_range &= u >= 0.0 && u < 1.0;
        sum += u;
    }
    check(same && differ, "rng stream determinism and separation");
    check(in_range && std::abs(sum / n - 0.5) < 5.0 * std::sqrt(1.0 / 12.0 / n), "rng uniform range and mean");
}

void test_watertight_shared_edges() {
    // Fan of triangles around a vertex: rays aimed exactly at shared edges and
    // the shared vertex must hit at least one triangle (no cracks).
    std::vector<Triangle> fan;
    const int k = 7;
    for (int i = 0; i < k; ++i) {
        // Shared vertices must be bit-identical: index modulo k (sin(2*pi) != 0).
        const double a0 = 2.0 * kPi * i / k, a1 = 2.0 * kPi * ((i + 1) % k) / k;
        fan.push_back({{0.1, 0.2, 0.0}, {std::cos(a0), std::sin(a0), 0.0}, {std::cos(a1), std::sin(a1), 0.0}, 0});
    }
    Xoshiro256 rng(11, 0, 0);
    int misses = 0, tested = 0;
    for (int i = 0; i < 200000; ++i) {
        const int e = int(rng.uniform() * k);
        const double s = rng.uniform();
        const double a = 2.0 * kPi * e / k;
        V3 target = V3{0.1, 0.2, 0.0} * (1.0 - s) + V3{std::cos(a), std::sin(a), 0.0} * s;
        if (i % 1000 == 0) target = {0.1, 0.2, 0.0};
        const V3 origin{rng.uniform() * 4 - 2, rng.uniform() * 4 - 2, 1.0 + rng.uniform() * 3};
        const Ray ray{origin, normalize(target - origin)};
        std::uint32_t id;
        if (brute_closest(fan, ray, id) == kInf) ++misses;
        ++tested;
    }
    check(misses == 0, "watertight: 0 misses on " + std::to_string(tested) + " shared-edge/vertex rays");
}

void test_bvh_matches_brute_force() {
    Xoshiro256 rng(99, 0, 0);
    std::vector<Triangle> tris;
    for (int i = 0; i < 3000; ++i) {
        const V3 c{rng.uniform() * 10 - 5, rng.uniform() * 10 - 5, rng.uniform() * 10 - 5};
        auto jitter = [&]() { return V3{rng.uniform() - 0.5, rng.uniform() - 0.5, rng.uniform() - 0.5}; };
        tris.push_back({c + jitter(), c + jitter(), c + jitter(), 0});
    }
    // Exact duplicates exercise the lower-index tie rule.
    tris.push_back(tris[5]);
    tris.push_back(tris[17]);
    const Bvh bvh(tris);
    int mismatches = 0, hits = 0, occl_mismatch = 0;
    for (int i = 0; i < 20000; ++i) {
        const V3 o{rng.uniform() * 14 - 7, rng.uniform() * 14 - 7, rng.uniform() * 14 - 7};
        V3 target = i % 10 == 0 ? (tris[5].v0 + tris[5].v1 + tris[5].v2) * (1.0 / 3.0)
                                : V3{rng.uniform() * 10 - 5, rng.uniform() * 10 - 5, rng.uniform() * 10 - 5};
        const Ray ray{o, normalize(target - o)};
        std::uint32_t bid;
        const double bt = brute_closest(tris, ray, bid);
        const Hit h = bvh.closest(ray, 0.0, kInf, std::numeric_limits<std::uint32_t>::max());
        if (bt == kInf) {
            if (h.hit()) ++mismatches;
        } else {
            ++hits;
            if (!h.hit() || h.t != bt || h.tri != bid) ++mismatches;
        }
        const double limit = 3.0;
        const bool occ = bvh.occluded(ray, limit, std::numeric_limits<std::uint32_t>::max(), std::numeric_limits<std::uint32_t>::max());
        if (occ != (bt < limit)) ++occl_mismatch;
    }
    check(mismatches == 0 && hits > 1000, "bvh closest == brute force (" + std::to_string(hits) + " hits)");
    check(occl_mismatch == 0, "bvh occlusion == brute force");
}

void test_cosine_sampling() {
    Xoshiro256 rng(5, 0, 0);
    const V3 normals[] = {{0, 0, 1}, {0, 0, -1}, normalize(V3{0.3, -0.8, 0.1}), {1, 0, 0}};
    for (const V3& n : normals) {
        const int count = 400000;
        double m1 = 0, m2 = 0;
        bool hemi = true;
        for (int i = 0; i < count; ++i) {
            const V3 d = Oracle::cosine_sample(n, rng.uniform(), rng.uniform());
            const double c = dot(d, n);
            hemi &= c >= 0.0 && std::abs(length(d) - 1.0) < 1e-12;
            m1 += c;
            m2 += c * c;
        }
        m1 /= count;
        m2 /= count;
        // cosine-weighted: E[cos]=2/3 (var 1/18), E[cos^2]=1/2 (var 1/12).
        check(hemi && std::abs(m1 - 2.0 / 3.0) < 5 * std::sqrt(1.0 / 18 / count) &&
                  std::abs(m2 - 0.5) < 5 * std::sqrt(1.0 / 12 / count),
              "cosine sampling moments");
    }
}

void test_pfm_layout() {
    const std::string path = "n008_test_layout.pfm";
    std::vector<float> rgb = {1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12};  // 2x2 top-down
    write_pfm(path, 2, 2, rgb);
    std::ifstream in(path, std::ios::binary);
    std::string magic;
    int w, h;
    double scale;
    in >> magic >> w >> h >> scale;
    in.get();
    std::vector<float> data(12);
    in.read(reinterpret_cast<char*>(data.data()), 48);
    std::remove(path.c_str());
    // PFM stores bottom row first.
    check(magic == "PF" && w == 2 && h == 2 && scale == -1.0 && data[0] == 7 && data[6] == 1, "pfm bottom-up layout");
}

void test_scene_parse_rejects() {
    auto rejects = [](const std::string& text) {
        std::istringstream in(text);
        try { parse_scene(in); } catch (const std::exception&) { return true; }
        return false;
    };
    const std::string base = "n008scene 1\nresolution 2 2\ncamera 0 0 0 0 0 -1 0 1 0 1 1 0 inf\n";
    check(rejects(base + "material m 1.5 0 0 0 0 0 1\n"), "parse rejects albedo > 1");
    check(rejects(base + "material m 0.5 0.5 0.5 0 0 0 1\ntri m 0 0 0 1 1 1 2 2 2\n"), "parse rejects degenerate triangle");
    check(rejects(base + "bogus 1\n"), "parse rejects unknown directive");
    check(!rejects(base + "material m 0.5 0.5 0.5 0 0 0 1\ntri m 0 0 -1 1 0 -1 0 1 -1\n"), "parse accepts valid scene");
}

}  // namespace

int main() {
    test_sha256();
    test_rng();
    test_watertight_shared_edges();
    test_bvh_matches_brute_force();
    test_cosine_sampling();
    test_pfm_layout();
    test_scene_parse_rejects();
    std::cout << (failures == 0 ? "ALL PASS" : "FAILURES: " + std::to_string(failures)) << "\n";
    return failures == 0 ? 0 : 1;
}
