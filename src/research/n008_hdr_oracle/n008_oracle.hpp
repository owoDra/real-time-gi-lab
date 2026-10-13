// N008 independent CPU HDR light-transport oracle (Phase A).
// Deliberately shares no code with N001 / Lane B: double precision, watertight
// ray/triangle test, own BVH, RNG and SHA-256. Transport definition:
// research/lanes/n008-hdr-oracle/experiments/001-phase-a-oracle-spec-and-controls.md
#pragma once

#include <algorithm>
#include <array>
#include <atomic>
#include <cmath>
#include <cstdint>
#include <cstdio>
#include <cstring>
#include <fstream>
#include <limits>
#include <map>
#include <sstream>
#include <stdexcept>
#include <string>
#include <thread>
#include <vector>

namespace phos::gi::research::n008 {

constexpr double kPi = 3.14159265358979323846264338327950288;
constexpr double kInf = std::numeric_limits<double>::infinity();

struct V3 {
    double x{}, y{}, z{};
    double operator[](int i) const { return i == 0 ? x : (i == 1 ? y : z); }
};
inline V3 operator+(V3 a, V3 b) { return {a.x + b.x, a.y + b.y, a.z + b.z}; }
inline V3 operator-(V3 a, V3 b) { return {a.x - b.x, a.y - b.y, a.z - b.z}; }
inline V3 operator*(V3 a, double s) { return {a.x * s, a.y * s, a.z * s}; }
inline double dot(V3 a, V3 b) { return a.x * b.x + a.y * b.y + a.z * b.z; }
inline V3 cross(V3 a, V3 b) {
    return {a.y * b.z - a.z * b.y, a.z * b.x - a.x * b.z, a.x * b.y - a.y * b.x};
}
inline double length(V3 a) { return std::sqrt(dot(a, a)); }
inline V3 normalize(V3 a) { return a * (1.0 / length(a)); }

using Rgb = std::array<double, 3>;

// ---------------------------------------------------------------- SHA-256
class Sha256 {
public:
    Sha256() { reset(); }
    void reset() {
        static constexpr std::uint32_t init[8] = {
            0x6a09e667, 0xbb67ae85, 0x3c6ef372, 0xa54ff53a,
            0x510e527f, 0x9b05688c, 0x1f83d9ab, 0x5be0cd19};
        std::memcpy(h_, init, sizeof h_);
        len_ = 0;
        fill_ = 0;
    }
    void update(const void* data, std::size_t n) {
        const auto* p = static_cast<const std::uint8_t*>(data);
        len_ += n;
        while (n > 0) {
            const std::size_t take = std::min<std::size_t>(64 - fill_, n);
            std::memcpy(buf_ + fill_, p, take);
            fill_ += take;
            p += take;
            n -= take;
            if (fill_ == 64) {
                block(buf_);
                fill_ = 0;
            }
        }
    }
    std::string hex() {
        const std::uint64_t bits = len_ * 8;
        const std::uint8_t pad = 0x80;
        update(&pad, 1);
        const std::uint8_t zero = 0;
        while (fill_ != 56) update(&zero, 1);
        std::uint8_t lenb[8];
        for (int i = 0; i < 8; ++i) lenb[i] = std::uint8_t(bits >> (56 - 8 * i));
        update(lenb, 8);
        char out[65];
        for (int i = 0; i < 8; ++i) std::snprintf(out + 8 * i, 9, "%08x", h_[i]);
        return std::string(out, 64);
    }

private:
    static std::uint32_t rotr(std::uint32_t x, int n) { return (x >> n) | (x << (32 - n)); }
    void block(const std::uint8_t* b) {
        static constexpr std::uint32_t k[64] = {
            0x428a2f98, 0x71374491, 0xb5c0fbcf, 0xe9b5dba5, 0x3956c25b, 0x59f111f1, 0x923f82a4, 0xab1c5ed5,
            0xd807aa98, 0x12835b01, 0x243185be, 0x550c7dc3, 0x72be5d74, 0x80deb1fe, 0x9bdc06a7, 0xc19bf174,
            0xe49b69c1, 0xefbe4786, 0x0fc19dc6, 0x240ca1cc, 0x2de92c6f, 0x4a7484aa, 0x5cb0a9dc, 0x76f988da,
            0x983e5152, 0xa831c66d, 0xb00327c8, 0xbf597fc7, 0xc6e00bf3, 0xd5a79147, 0x06ca6351, 0x14292967,
            0x27b70a85, 0x2e1b2138, 0x4d2c6dfc, 0x53380d13, 0x650a7354, 0x766a0abb, 0x81c2c92e, 0x92722c85,
            0xa2bfe8a1, 0xa81a664b, 0xc24b8b70, 0xc76c51a3, 0xd192e819, 0xd6990624, 0xf40e3585, 0x106aa070,
            0x19a4c116, 0x1e376c08, 0x2748774c, 0x34b0bcb5, 0x391c0cb3, 0x4ed8aa4a, 0x5b9cca4f, 0x682e6ff3,
            0x748f82ee, 0x78a5636f, 0x84c87814, 0x8cc70208, 0x90befffa, 0xa4506ceb, 0xbef9a3f7, 0xc67178f2};
        std::uint32_t w[64];
        for (int i = 0; i < 16; ++i)
            w[i] = (std::uint32_t(b[4 * i]) << 24) | (std::uint32_t(b[4 * i + 1]) << 16) |
                   (std::uint32_t(b[4 * i + 2]) << 8) | std::uint32_t(b[4 * i + 3]);
        for (int i = 16; i < 64; ++i) {
            const auto s0 = rotr(w[i - 15], 7) ^ rotr(w[i - 15], 18) ^ (w[i - 15] >> 3);
            const auto s1 = rotr(w[i - 2], 17) ^ rotr(w[i - 2], 19) ^ (w[i - 2] >> 10);
            w[i] = w[i - 16] + s0 + w[i - 7] + s1;
        }
        auto a = h_[0], bb = h_[1], c = h_[2], d = h_[3], e = h_[4], f = h_[5], g = h_[6], h = h_[7];
        for (int i = 0; i < 64; ++i) {
            const auto t1 = h + (rotr(e, 6) ^ rotr(e, 11) ^ rotr(e, 25)) + ((e & f) ^ (~e & g)) + k[i] + w[i];
            const auto t2 = (rotr(a, 2) ^ rotr(a, 13) ^ rotr(a, 22)) + ((a & bb) ^ (a & c) ^ (bb & c));
            h = g; g = f; f = e; e = d + t1; d = c; c = bb; bb = a; a = t1 + t2;
        }
        h_[0] += a; h_[1] += bb; h_[2] += c; h_[3] += d; h_[4] += e; h_[5] += f; h_[6] += g; h_[7] += h;
    }
    std::uint32_t h_[8]{};
    std::uint8_t buf_[64]{};
    std::size_t fill_{};
    std::uint64_t len_{};
};

// ---------------------------------------------------------------- RNG
inline std::uint64_t splitmix64(std::uint64_t& s) {
    std::uint64_t z = (s += 0x9e3779b97f4a7c15ULL);
    z = (z ^ (z >> 30)) * 0xbf58476d1ce4e5b9ULL;
    z = (z ^ (z >> 27)) * 0x94d049bb133111ebULL;
    return z ^ (z >> 31);
}

class Xoshiro256 {
public:
    Xoshiro256(std::uint64_t seed, std::uint64_t pixel, std::uint64_t sample) {
        std::uint64_t s = seed;
        s = splitmix64(s) ^ (pixel * 0x9fb21c651e98df25ULL);
        s = splitmix64(s) ^ (sample * 0xc2b2ae3d27d4eb4fULL);
        for (auto& v : s_) v = splitmix64(s);
    }
    std::uint64_t next() {
        const auto result = rotl(s_[1] * 5, 7) * 9;
        const auto t = s_[1] << 17;
        s_[2] ^= s_[0]; s_[3] ^= s_[1]; s_[1] ^= s_[2]; s_[0] ^= s_[3];
        s_[2] ^= t;
        s_[3] = rotl(s_[3], 45);
        return result;
    }
    double uniform() { return double(next() >> 11) * (1.0 / 9007199254740992.0); }  // [0,1)

private:
    static std::uint64_t rotl(std::uint64_t x, int k) { return (x << k) | (x >> (64 - k)); }
    std::uint64_t s_[4]{};
};

// ---------------------------------------------------------------- scene
struct Material {
    Rgb rho{};
    Rgb emit{};
    bool two_sided{true};
};
struct Triangle {
    V3 v0, v1, v2;
    std::uint32_t material{};
};
struct PointLight {
    V3 position;
    Rgb intensity{};
};
struct Camera {
    V3 origin, forward, up;
    double tan_x{}, tan_y{}, near{}, far{kInf};
};
enum class Falloff { InverseSquare, N001Soft };
enum class Sampling { Center, Box };

struct Scene {
    std::uint32_t width{}, height{};
    Camera camera;
    Sampling sampling{Sampling::Center};
    std::uint32_t max_bounces{1};
    Falloff falloff{Falloff::InverseSquare};
    double soft_scale{0.0};
    bool secondary_far_camera{false};
    std::vector<Material> materials;
    std::vector<Triangle> triangles;
    std::vector<PointLight> points;
};

inline Scene parse_scene(std::istream& in) {
    Scene scene;
    std::map<std::string, std::uint32_t> material_ids;
    std::string line, word;
    bool header = false, has_resolution = false, has_camera = false;
    std::size_t line_no = 0;
    auto fail = [&](const std::string& msg) {
        throw std::runtime_error("scene line " + std::to_string(line_no) + ": " + msg);
    };
    while (std::getline(in, line)) {
        ++line_no;
        const auto hash = line.find('#');
        if (hash != std::string::npos) line.resize(hash);
        std::istringstream ls(line);
        if (!(ls >> word)) continue;
        auto num = [&]() {
            double v;
            if (!(ls >> v) || !std::isfinite(v)) fail("expected finite number");
            return v;
        };
        auto vec = [&]() { V3 v; v.x = num(); v.y = num(); v.z = num(); return v; };
        if (!header) {
            int version = 0;
            if (word != "n008scene" || !(ls >> version) || version != 1) fail("expected 'n008scene 1'");
            header = true;
            continue;
        }
        if (word == "resolution") {
            long w, h;
            if (!(ls >> w >> h) || w <= 0 || h <= 0) fail("bad resolution");
            scene.width = std::uint32_t(w);
            scene.height = std::uint32_t(h);
            has_resolution = true;
        } else if (word == "camera") {
            scene.camera.origin = vec();
            scene.camera.forward = vec();
            scene.camera.up = vec();
            scene.camera.tan_x = num();
            scene.camera.tan_y = num();
            scene.camera.near = num();
            std::string far;
            if (!(ls >> far)) fail("missing far");
            scene.camera.far = far == "inf" ? kInf : std::stod(far);
            if (!(scene.camera.far > scene.camera.near) || scene.camera.near < 0) fail("bad near/far");
            has_camera = true;
        } else if (word == "sampling") {
            std::string s;
            ls >> s;
            if (s == "center") scene.sampling = Sampling::Center;
            else if (s == "box") scene.sampling = Sampling::Box;
            else fail("sampling must be center|box");
        } else if (word == "max_bounces") {
            long d;
            if (!(ls >> d) || d < 1 || d > 1024) fail("bad max_bounces");
            scene.max_bounces = std::uint32_t(d);
        } else if (word == "falloff") {
            std::string s;
            ls >> s;
            if (s == "inverse_square") scene.falloff = Falloff::InverseSquare;
            else if (s == "n001_soft") {
                scene.falloff = Falloff::N001Soft;
                scene.soft_scale = num();
            } else fail("falloff must be inverse_square|n001_soft");
        } else if (word == "secondary_far") {
            std::string s;
            ls >> s;
            if (s == "inf") scene.secondary_far_camera = false;
            else if (s == "camera") scene.secondary_far_camera = true;
            else fail("secondary_far must be inf|camera");
        } else if (word == "material") {
            std::string name;
            ls >> name;
            Material m;
            for (auto& c : m.rho) c = num();
            for (auto& c : m.emit) c = num();
            const double two = num();
            m.two_sided = two != 0.0;
            for (auto c : m.rho) if (c < 0.0 || c > 1.0) fail("albedo outside [0,1]");
            for (auto c : m.emit) if (c < 0.0) fail("negative emission");
            if (material_ids.count(name)) fail("duplicate material " + name);
            material_ids[name] = std::uint32_t(scene.materials.size());
            scene.materials.push_back(m);
        } else if (word == "point") {
            PointLight p;
            p.position = vec();
            for (auto& c : p.intensity) c = num();
            for (auto c : p.intensity) if (c < 0.0) fail("negative intensity");
            scene.points.push_back(p);
        } else if (word == "tri") {
            std::string name;
            ls >> name;
            const auto it = material_ids.find(name);
            if (it == material_ids.end()) fail("unknown material " + name);
            Triangle t;
            t.v0 = vec(); t.v1 = vec(); t.v2 = vec();
            t.material = it->second;
            if (length(cross(t.v1 - t.v0, t.v2 - t.v0)) <= 0.0) fail("degenerate triangle");
            scene.triangles.push_back(t);
        } else {
            fail("unknown directive " + word);
        }
    }
    if (!header || !has_resolution || !has_camera) throw std::runtime_error("scene missing header/resolution/camera");
    return scene;
}

// Canonical attestation of the world-space geometry actually loaded.
inline std::string geometry_sha256(const Scene& scene) {
    Sha256 sha;
    auto put = [&](double v) {
        std::uint64_t bits;
        std::memcpy(&bits, &v, 8);
        std::uint8_t b[8];
        for (int i = 0; i < 8; ++i) b[i] = std::uint8_t(bits >> (8 * i));
        sha.update(b, 8);
    };
    for (const auto& t : scene.triangles) {
        for (const V3& v : {t.v0, t.v1, t.v2}) { put(v.x); put(v.y); put(v.z); }
        std::uint8_t m[4];
        for (int i = 0; i < 4; ++i) m[i] = std::uint8_t(t.material >> (8 * i));
        sha.update(m, 4);
    }
    return sha.hex();
}

// ---------------------------------------------------------------- intersection
struct Ray {
    V3 origin, dir;
};
struct Hit {
    double t{kInf};
    std::uint32_t tri{std::numeric_limits<std::uint32_t>::max()};
    bool hit() const { return tri != std::numeric_limits<std::uint32_t>::max(); }
};

// Woop, Benthin, Wald 2013 "Watertight Ray/Triangle Intersection", double.
// Closed triangles (edges inclusive), so shared edges never leak.
struct WatertightRay {
    int kx, ky, kz;
    double sx, sy, sz;
    V3 origin;
    explicit WatertightRay(const Ray& r) : origin(r.origin) {
        const double ax = std::abs(r.dir.x), ay = std::abs(r.dir.y), az = std::abs(r.dir.z);
        kz = ax > ay ? (ax > az ? 0 : 2) : (ay > az ? 1 : 2);
        kx = (kz + 1) % 3;
        ky = (kx + 1) % 3;
        if (r.dir[kz] < 0.0) std::swap(kx, ky);
        sx = r.dir[kx] / r.dir[kz];
        sy = r.dir[ky] / r.dir[kz];
        sz = 1.0 / r.dir[kz];
    }
    // Returns t (or +inf when missed).
    double intersect(const Triangle& tri) const {
        const V3 a = tri.v0 - origin, b = tri.v1 - origin, c = tri.v2 - origin;
        const double ax = a[kx] - sx * a[kz], ay = a[ky] - sy * a[kz];
        const double bx = b[kx] - sx * b[kz], by = b[ky] - sy * b[kz];
        const double cx = c[kx] - sx * c[kz], cy = c[ky] - sy * c[kz];
        const double u = cx * by - cy * bx;
        const double v = ax * cy - ay * cx;
        const double w = bx * ay - by * ax;
        if ((u < 0.0 || v < 0.0 || w < 0.0) && (u > 0.0 || v > 0.0 || w > 0.0)) return kInf;
        const double det = u + v + w;
        if (det == 0.0) return kInf;
        const double t_scaled = u * (sz * a[kz]) + v * (sz * b[kz]) + w * (sz * c[kz]);
        const double t = t_scaled / det;
        return t > 0.0 ? t : kInf;
    }
};

struct Aabb {
    V3 lo{kInf, kInf, kInf}, hi{-kInf, -kInf, -kInf};
    void grow(V3 p) {
        lo = {std::min(lo.x, p.x), std::min(lo.y, p.y), std::min(lo.z, p.z)};
        hi = {std::max(hi.x, p.x), std::max(hi.y, p.y), std::max(hi.z, p.z)};
    }
    void grow(const Aabb& b) { grow(b.lo); grow(b.hi); }
    double area() const {
        const V3 d = hi - lo;
        return d.x < 0 ? 0.0 : 2.0 * (d.x * d.y + d.y * d.z + d.z * d.x);
    }
};

class Bvh {
public:
    explicit Bvh(const std::vector<Triangle>& tris) : tris_(tris) {
        order_.resize(tris.size());
        for (std::uint32_t i = 0; i < order_.size(); ++i) order_[i] = i;
        if (!tris.empty()) {
            nodes_.reserve(tris.size() * 2);
            build(0, std::uint32_t(tris.size()));
        }
    }

    // Closest hit with t in (tmin, tmax); ties resolve to the lower triangle index.
    Hit closest(const Ray& ray, double tmin, double tmax, std::uint32_t ignore) const {
        Hit best;
        best.t = tmax;
        traverse(ray, tmin, [&](std::uint32_t id, double t) {
            if (id == ignore || !(t > tmin)) return false;
            // First hit may lie exactly at tmax (interval (tmin, tmax]).
            if ((!best.hit() && t <= best.t) || t < best.t || (t == best.t && id < best.tri)) {
                best.t = t;
                best.tri = id;
            }
            return false;
        }, best.t);
        if (!best.hit()) best.t = kInf;
        return best;
    }

    bool occluded(const Ray& ray, double tmax, std::uint32_t ignore_a, std::uint32_t ignore_b) const {
        bool blocked = false;
        double limit = tmax;
        traverse(ray, 0.0, [&](std::uint32_t id, double t) {
            if (id == ignore_a || id == ignore_b) return false;
            if (t > 0.0 && t < tmax) { blocked = true; return true; }
            return false;
        }, limit);
        return blocked;
    }

private:
    struct Node {
        Aabb box;
        std::uint32_t first{}, count{}, right{};  // leaf when count>0; left child = this+1
    };

    std::uint32_t build(std::uint32_t begin, std::uint32_t end) {
        const auto index = std::uint32_t(nodes_.size());
        nodes_.push_back({});
        Aabb box, centroids;
        for (auto i = begin; i < end; ++i) {
            const auto& t = tris_[order_[i]];
            box.grow(t.v0); box.grow(t.v1); box.grow(t.v2);
            centroids.grow(centroid(t));
        }
        nodes_[index].box = box;
        const auto n = end - begin;
        if (n <= 4) {
            nodes_[index].first = begin;
            nodes_[index].count = n;
            return index;
        }
        // Binned SAH over the largest centroid axis.
        const V3 extent = centroids.hi - centroids.lo;
        int axis = extent.x > extent.y ? (extent.x > extent.z ? 0 : 2) : (extent.y > extent.z ? 1 : 2);
        std::uint32_t mid = begin + n / 2;
        if (extent[axis] > 0.0) {
            constexpr int kBins = 16;
            Aabb bins[kBins];
            std::uint32_t counts[kBins]{};
            const double lo = centroids.lo[axis], scale = kBins / extent[axis];
            auto bin_of = [&](std::uint32_t id) {
                return std::min(kBins - 1, int((centroid(tris_[id])[axis] - lo) * scale));
            };
            for (auto i = begin; i < end; ++i) {
                const auto b = bin_of(order_[i]);
                const auto& t = tris_[order_[i]];
                bins[b].grow(t.v0); bins[b].grow(t.v1); bins[b].grow(t.v2);
                ++counts[b];
            }
            double best_cost = kInf;
            int best_split = -1;
            for (int s = 1; s < kBins; ++s) {
                Aabb l, r;
                std::uint32_t cl = 0, cr = 0;
                for (int b = 0; b < s; ++b) if (counts[b]) { l.grow(bins[b]); cl += counts[b]; }
                for (int b = s; b < kBins; ++b) if (counts[b]) { r.grow(bins[b]); cr += counts[b]; }
                if (cl == 0 || cr == 0) continue;
                const double cost = l.area() * cl + r.area() * cr;
                if (cost < best_cost) { best_cost = cost; best_split = s; }
            }
            if (best_split > 0) {
                const auto it = std::partition(order_.begin() + begin, order_.begin() + end,
                    [&](std::uint32_t id) { return bin_of(id) < best_split; });
                mid = std::uint32_t(it - order_.begin());
            }
        }
        if (mid == begin || mid == end) {
            std::nth_element(order_.begin() + begin, order_.begin() + begin + n / 2, order_.begin() + end,
                [&](std::uint32_t a, std::uint32_t b) {
                    const double ca = centroid(tris_[a])[axis], cb = centroid(tris_[b])[axis];
                    return ca < cb || (ca == cb && a < b);
                });
            mid = begin + n / 2;
        }
        build(begin, mid);
        nodes_[index].right = build(mid, end);
        return index;
    }

    static V3 centroid(const Triangle& t) { return (t.v0 + t.v1 + t.v2) * (1.0 / 3.0); }

    // Conservative slab test: interval widened by a few ulps so that box
    // rounding can never reject a ray that hits a contained triangle.
    static bool slab(const Aabb& b, const V3& o, const V3& inv, double tmin, double tmax) {
        double t0 = tmin, t1 = tmax;
        for (int a = 0; a < 3; ++a) {
            double tn = (b.lo[a] - o[a]) * inv[a];
            double tf = (b.hi[a] - o[a]) * inv[a];
            if (std::isnan(tn) || std::isnan(tf)) {  // origin on slab plane with zero direction
                if (o[a] < b.lo[a] || o[a] > b.hi[a]) return false;
                continue;
            }
            if (tn > tf) std::swap(tn, tf);
            tf *= 1.0 + 4.0 * std::numeric_limits<double>::epsilon();
            t0 = std::max(t0, tn);
            t1 = std::min(t1, tf);
            if (t0 > t1) return false;
        }
        return true;
    }

    template <class Visit>
    void traverse(const Ray& ray, double tmin, Visit&& visit, double& tmax) const {
        if (nodes_.empty()) return;
        const WatertightRay wr(ray);
        const V3 inv{1.0 / ray.dir.x, 1.0 / ray.dir.y, 1.0 / ray.dir.z};
        std::uint32_t stack[128];
        int sp = 0;
        stack[sp++] = 0;
        while (sp > 0) {
            const auto ni = stack[--sp];
            const Node& node = nodes_[ni];
            if (!slab(node.box, ray.origin, inv, tmin, tmax)) continue;
            if (node.count > 0) {
                for (auto i = node.first; i < node.first + node.count; ++i) {
                    const auto id = order_[i];
                    const double t = wr.intersect(tris_[id]);
                    if (t < kInf && t <= tmax && visit(id, t)) return;
                }
            } else {
                if (sp + 2 > 128) throw std::runtime_error("BVH stack overflow");
                stack[sp++] = node.right;
                stack[sp++] = ni + 1;
            }
        }
    }

    const std::vector<Triangle>& tris_;
    std::vector<std::uint32_t> order_;
    std::vector<Node> nodes_;
};

// ---------------------------------------------------------------- integrator
enum Component { kEmission = 0, kDirect = 1, kIndirect = 2, kComponents = 3 };

struct PixelStats {
    // Per component and channel: sum and sum of squares over samples; plus total.
    double sum[kComponents + 1][3]{};
    double sum2[kComponents + 1][3]{};
};

struct RenderCounters {
    std::uint64_t primary_hits{}, shadow_tests{}, shadow_blocked{}, backface_absorbed{};
};

class Oracle {
public:
    explicit Oracle(const Scene& scene) : scene_(scene), bvh_(scene.triangles) {
        Aabb box;
        for (const auto& t : scene.triangles) { box.grow(t.v0); box.grow(t.v1); box.grow(t.v2); }
        const double diag = scene.triangles.empty() ? 1.0 : length(box.hi - box.lo);
        offset_ = 1e-12 * std::max(diag, 1e-12);  // protocol Amendment 1
        edge_inset_ = 1e-11 * std::max(diag, 1e-12);  // protocol Amendment 2
        const auto& c = scene.camera;
        forward_ = normalize(c.forward);
        right_ = normalize(cross(forward_, c.up));
        up_ = cross(right_, forward_);
        for (std::uint32_t i = 0; i < scene.triangles.size(); ++i) {
            const auto& m = scene.materials[scene.triangles[i].material];
            if (m.emit[0] > 0 || m.emit[1] > 0 || m.emit[2] > 0) {
                const auto& t = scene.triangles[i];
                emitter_area_ += 0.5 * length(cross(t.v1 - t.v0, t.v2 - t.v0));
                emitters_.push_back(i);
                emitter_cdf_.push_back(emitter_area_);
            }
        }
    }

    double offset() const { return offset_; }

    // Amendment 2: a hit within `edge_inset_` of its triangle's boundary is moved
    // toward the centroid so that spawned rays never start on the plane of an
    // adjacent face (concave edges, room seams). Points farther inside are untouched.
    V3 nudge_inside(const Triangle& t, V3 p) const {
        const V3 v[3] = {t.v0, t.v1, t.v2};
        double min_dist = kInf, max_edge = 0.0;
        for (int i = 0; i < 3; ++i) {
            const V3 a = v[(i + 1) % 3], b = v[(i + 2) % 3];
            const double len = length(b - a);
            max_edge = std::max(max_edge, len);
            min_dist = std::min(min_dist, length(cross(b - a, p - a)) / len);
        }
        if (min_dist >= edge_inset_) return p;
        const double h_min = length(cross(t.v1 - t.v0, t.v2 - t.v0)) / max_edge;
        const double alpha = std::min(0.5, 3.0 * edge_inset_ / h_min);
        const V3 c = (t.v0 + t.v1 + t.v2) * (1.0 / 3.0);
        return p + (c - p) * alpha;
    }

    Ray primary_ray(std::uint32_t x, std::uint32_t y, double u, double v) const {
        const double nx = 2.0 * (double(x) + u) / double(scene_.width) - 1.0;
        const double ny = 1.0 - 2.0 * (double(y) + v) / double(scene_.height);
        const auto d = normalize(forward_ + right_ * (nx * scene_.camera.tan_x) + up_ * (ny * scene_.camera.tan_y));
        return {scene_.camera.origin, d};
    }

    // One camera sample; writes per-component radiance.
    void sample(std::uint32_t x, std::uint32_t y, Xoshiro256& rng, Rgb out[kComponents], RenderCounters& cnt) const {
        for (int c = 0; c < kComponents; ++c) out[c] = {0, 0, 0};
        double u = 0.5, v = 0.5;
        if (scene_.sampling == Sampling::Box) { u = rng.uniform(); v = rng.uniform(); }
        Ray ray = primary_ray(x, y, u, v);
        double tmin = scene_.camera.near, tmax = scene_.camera.far;
        const double secondary_far = scene_.secondary_far_camera ? scene_.camera.far : kInf;
        std::uint32_t ignore = std::numeric_limits<std::uint32_t>::max();
        Rgb throughput{1, 1, 1};
        for (std::uint32_t bounce = 0; bounce < scene_.max_bounces; ++bounce) {
            const Hit hit = bvh_.closest(ray, tmin, tmax, ignore);
            if (!hit.hit()) return;
            if (bounce == 0) ++cnt.primary_hits;
            const Triangle& tri = scene_.triangles[hit.tri];
            const Material& m = scene_.materials[tri.material];
            const V3 ng = normalize(cross(tri.v1 - tri.v0, tri.v2 - tri.v0));
            const bool front = dot(ng, ray.dir) < 0.0;
            if (bounce == 0 && front) out[kEmission] = m.emit;
            if (!front && !m.two_sided) { ++cnt.backface_absorbed; return; }
            const V3 n = front ? ng : ng * -1.0;
            const V3 p = nudge_inside(tri, ray.origin + ray.dir * hit.t);
            const V3 origin = p + n * offset_;
            Rgb f{m.rho[0] / kPi, m.rho[1] / kPi, m.rho[2] / kPi};
            if (f[0] == 0 && f[1] == 0 && f[2] == 0) return;
            const Rgb e = direct(origin, n, hit.tri, rng, cnt);
            auto& dst = out[bounce == 0 ? kDirect : kIndirect];
            for (int c = 0; c < 3; ++c) dst[c] += throughput[c] * f[c] * e[c];
            if (bounce + 1 >= scene_.max_bounces) return;
            // Cosine-weighted hemisphere: f*cos/pdf = rho.
            for (int c = 0; c < 3; ++c) throughput[c] *= m.rho[c];
            ray = {origin, cosine_sample(n, rng.uniform(), rng.uniform())};
            tmin = 0.0;
            tmax = secondary_far;
            ignore = hit.tri;
        }
    }

    static V3 cosine_sample(V3 n, double u1, double u2) {
        const double r = std::sqrt(u1), phi = 2.0 * kPi * u2;
        const double lx = r * std::cos(phi), ly = r * std::sin(phi), lz = std::sqrt(std::max(0.0, 1.0 - u1));
        // Duff et al. 2017 orthonormal basis.
        const double sign = std::copysign(1.0, n.z);
        const double a = -1.0 / (sign + n.z), b = n.x * n.y * a;
        const V3 t{1.0 + sign * n.x * n.x * a, sign * b, -sign * n.x};
        const V3 s{b, sign + n.y * n.y * a, -n.y};
        return normalize(t * lx + s * ly + n * lz);
    }

    // Irradiance-like term E such that reflected radiance = f * E.
    Rgb direct(V3 origin, V3 n, std::uint32_t self, Xoshiro256& rng, RenderCounters& cnt) const {
        Rgb e{0, 0, 0};
        for (const auto& light : scene_.points) {
            const V3 l = light.position - origin;
            const double d2 = dot(l, l);
            if (!(d2 > 0.0)) continue;
            const double d = std::sqrt(d2);
            const V3 wi = l * (1.0 / d);
            const double cosx = dot(n, wi);
            if (cosx <= 0.0) continue;
            ++cnt.shadow_tests;
            if (bvh_.occluded({origin, wi}, d * (1.0 - 1e-12) - offset_, self, self)) { ++cnt.shadow_blocked; continue; }
            const double g = scene_.falloff == Falloff::InverseSquare
                ? cosx / d2
                : cosx / (scene_.soft_scale * scene_.soft_scale + d2);
            for (int c = 0; c < 3; ++c) e[c] += light.intensity[c] * g;
        }
        if (!emitters_.empty()) {
            const double pick = rng.uniform() * emitter_area_;
            const auto k = std::size_t(std::upper_bound(emitter_cdf_.begin(), emitter_cdf_.end(), pick) - emitter_cdf_.begin());
            const auto id = emitters_[std::min(k, emitters_.size() - 1)];
            const Triangle& t = scene_.triangles[id];
            double a = rng.uniform(), b = rng.uniform();
            if (a + b > 1.0) { a = 1.0 - a; b = 1.0 - b; }
            const V3 q = t.v0 + (t.v1 - t.v0) * a + (t.v2 - t.v0) * b;
            const V3 nl = normalize(cross(t.v1 - t.v0, t.v2 - t.v0));
            const V3 l = q - origin;
            const double d2 = dot(l, l);
            if (d2 > 0.0 && id != self) {
                const double d = std::sqrt(d2);
                const V3 wi = l * (1.0 / d);
                const double cosx = dot(n, wi), cosl = -dot(nl, wi);
                if (cosx > 0.0 && cosl > 0.0) {
                    ++cnt.shadow_tests;
                    if (bvh_.occluded({origin, wi}, d * (1.0 - 1e-12), self, id)) {
                        ++cnt.shadow_blocked;
                    } else {
                        const double g = cosx * cosl / d2 * emitter_area_;  // pdf_area = 1/A
                        const auto& le = scene_.materials[t.material].emit;
                        for (int c = 0; c < 3; ++c) e[c] += le[c] * g;
                    }
                }
            }
        }
        return e;
    }

    std::vector<PixelStats> render(std::uint64_t seed, std::uint32_t spp, unsigned threads, RenderCounters& total) const {
        std::vector<PixelStats> stats(std::size_t(scene_.width) * scene_.height);
        std::atomic<std::uint32_t> next_row{0};
        std::vector<RenderCounters> per_thread(threads);
        std::vector<std::thread> pool;
        for (unsigned t = 0; t < threads; ++t) {
            pool.emplace_back([&, t] {
                for (;;) {
                    const auto y = next_row.fetch_add(1);
                    if (y >= scene_.height) return;
                    for (std::uint32_t x = 0; x < scene_.width; ++x) {
                        const auto pixel = std::size_t(y) * scene_.width + x;
                        auto& ps = stats[pixel];
                        for (std::uint32_t s = 0; s < spp; ++s) {
                            Xoshiro256 rng(seed, pixel, s);
                            Rgb comp[kComponents];
                            sample(x, y, rng, comp, per_thread[t]);
                            for (int c = 0; c < 3; ++c) {
                                double tot = 0.0;
                                for (int k = 0; k < kComponents; ++k) {
                                    ps.sum[k][c] += comp[k][c];
                                    ps.sum2[k][c] += comp[k][c] * comp[k][c];
                                    tot += comp[k][c];
                                }
                                ps.sum[kComponents][c] += tot;
                                ps.sum2[kComponents][c] += tot * tot;
                            }
                        }
                    }
                }
            });
        }
        for (auto& th : pool) th.join();
        for (const auto& c : per_thread) {
            total.primary_hits += c.primary_hits;
            total.shadow_tests += c.shadow_tests;
            total.shadow_blocked += c.shadow_blocked;
            total.backface_absorbed += c.backface_absorbed;
        }
        return stats;
    }

    const Bvh& bvh() const { return bvh_; }

private:
    const Scene& scene_;
    Bvh bvh_;
    double offset_{};
    double edge_inset_{};
    V3 forward_, right_, up_;
    std::vector<std::uint32_t> emitters_;
    std::vector<double> emitter_cdf_;
    double emitter_area_{0.0};
};

// ---------------------------------------------------------------- output
// RGB PFM, little-endian (scale -1), rows bottom-up per the PFM convention.
inline void write_pfm(const std::string& path, std::uint32_t w, std::uint32_t h, const std::vector<float>& rgb_top_down) {
    std::ofstream out(path, std::ios::binary);
    if (!out) throw std::runtime_error("cannot write " + path);
    out << "PF\n" << w << ' ' << h << "\n-1\n";
    for (std::uint32_t row = 0; row < h; ++row) {
        const auto y = h - 1 - row;
        out.write(reinterpret_cast<const char*>(rgb_top_down.data() + std::size_t(y) * w * 3), std::streamsize(w) * 3 * sizeof(float));
    }
    if (!out) throw std::runtime_error("short write " + path);
}

}  // namespace phos::gi::research::n008
