#!/usr/bin/env python3
"""Sampling-only overlay of immutable N008 oracle; transport stays verbatim."""
import argparse
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]


def once(s, old, new):
    if s.count(old) != 1:
        raise ValueError(f"N010 oracle source drift: {old[:90]}")
    return s.replace(old, new)


RNG = r"""
// N010 randomized digital shift of a 32-bit Sobol net (Joe/Kuo via SciPy).
// Replicate means, not iid per-sample moments, define uncertainty.
class N010NetRng {
public:
    inline static std::vector<std::uint32_t> net;
    inline static std::uint32_t dimensions{}, samples{};
    static void load(const std::string& file) {
        std::ifstream in(file, std::ios::binary);
        char magic[8]; in.read(magic, 8);
        in.read(reinterpret_cast<char*>(&dimensions), 4);
        in.read(reinterpret_cast<char*>(&samples), 4);
        if (!in || std::memcmp(magic,"N010NET1",8) || dimensions != 16 || samples != 262144)
            throw std::runtime_error("bad N010 Sobol table header");
        net.resize(std::size_t(dimensions) * samples);
        in.read(reinterpret_cast<char*>(net.data()), std::streamsize(net.size()*4));
        if (!in || in.peek() != std::char_traits<char>::eof()) throw std::runtime_error("bad N010 Sobol table length");
    }
    static std::uint64_t mix(std::uint64_t x) {
        x += 0x9e3779b97f4a7c15ULL;
        x = (x ^ (x >> 30)) * 0xbf58476d1ce4e5b9ULL;
        x = (x ^ (x >> 27)) * 0x94d049bb133111ebULL;
        return x ^ (x >> 31);
    }
    N010NetRng(std::uint64_t seed, std::uint64_t pixel, std::uint32_t sample)
        : seed_(seed), pixel_(pixel), sample_(sample) {
        if (net.empty() || sample >= samples) throw std::runtime_error("N010 Sobol table missing/sample beyond cap");
    }
    double uniform() {
        if (dim_ >= dimensions) throw std::runtime_error("N010 Sobol dimensions exhausted");
        const auto shift = std::uint32_t(mix(seed_ ^ mix(pixel_) ^ mix(dim_ + 0x4e303130ULL)));
        const auto x = net[std::size_t(sample_) * dimensions + dim_++] ^ shift;
        return (double(x) + 0.5) * 0x1p-32;
    }
private:
    std::uint64_t seed_, pixel_;
    std::uint32_t sample_, dim_{};
};
"""


def generate(out):
    src = ROOT / "src/research/n008_hdr_oracle"
    header = (src / "n008_oracle.hpp").read_text()
    header = once(header, "class Oracle {", RNG + "\nclass Oracle {")
    header = once(header, "    void sample(std::uint32_t x, std::uint32_t y, Xoshiro256& rng,",
                  "    template<class Rng>\n    void sample(std::uint32_t x, std::uint32_t y, Rng& rng,")
    header = once(header, "    Rgb direct(V3 origin, V3 n, std::uint32_t self, Xoshiro256& rng,",
                  "    template<class Rng>\n    Rgb direct(V3 origin, V3 n, std::uint32_t self, Rng& rng,")
    header = once(header, "                            Xoshiro256 rng(seed, pixel, s);",
                  "                            N010NetRng rng(seed, pixel, s);")
    header = once(header, "            ray = {origin, cosine_sample(n, rng.uniform(), rng.uniform())};",
                  "            const double n010_u1 = rng.uniform(), n010_u2 = rng.uniform();\n"
                  "            ray = {origin, cosine_sample(n, n010_u1, n010_u2)};")
    main = (src / "n008_oracle_main.cpp").read_text()
    main = once(main, "#include \"n008_oracle.hpp\"", '#include "n010_rqmc_oracle.hpp"')
    main = once(main, "            else if (a == \"--threads\")",
                '            else if (a == "--net") N010NetRng::load(value());\n'
                '            else if (a == "--threads")')
    main = once(main, "        const Oracle oracle(scene);",
                "        if (scene.sampling != Sampling::Center || scene.max_bounces > 8)\n"
                '            throw std::runtime_error("N010 supports center sampling and at most 8 vertices");\n'
                "        for (const auto& m : scene.materials)\n"
                "            if (m.emit[0] != 0 || m.emit[1] != 0 || m.emit[2] != 0)\n"
                '                throw std::runtime_error("N010 RQMC point-light-only validation scope");\n'
                "        const Oracle oracle(scene);")
    main = once(main, '\\"oracle\\":\\"n008\\"', '\\"oracle\\":\\"n010-rqmc-digital-shift\\"')
    out.mkdir(parents=True, exist_ok=True)
    (out / "n010_rqmc_oracle.hpp").write_text(header)
    (out / "n010_rqmc_main.cpp").write_text(main)
    (out / "source-manifest.json").write_text(json.dumps({
        p.name: hashlib.sha256(p.read_bytes()).hexdigest()
        for p in (src / "n008_oracle.hpp", src / "n008_oracle_main.cpp")}, indent=2) + "\n")


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", type=Path, required=True)
    a = ap.parse_args()
    generate(a.out)
