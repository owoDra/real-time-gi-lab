"""035 reversible observation-only private N008 derivative; historical source is read-only."""
from pathlib import Path
import hashlib

ROOT=Path(__file__).resolve().parents[3]
ORIGINAL=ROOT/'src/research/n008_hdr_oracle/n008_oracle.hpp'
VERTEX='''struct PathVertex {
    V3 ray_origin{}, direction{}, hit_position{}, nudged{}, spawn{}, normal{}, reflected{};
    double t{};
    std::uint32_t triangle{}, kind{}, front{}, padding{};
};
static_assert(sizeof(PathVertex)==192);
'''


def overlay(raw):
    changes=[('namespace phos::gi::research::n008 {','namespace phos::gi::research::restir035 {'),
             ('class Oracle {',VERTEX+'\nclass Oracle {'),
             ('PrimaryRecord* primary = nullptr) const {','PrimaryRecord* primary = nullptr, PathVertex* observations = nullptr) const {'),
             ('            const Hit hit = bvh_.closest(ray, tmin, tmax, ignore);',
              '            if (observations) { auto& v=observations[bounce]; v.ray_origin=ray.origin; v.direction=ray.dir; v.kind=1; }\n            const Hit hit = bvh_.closest(ray, tmin, tmax, ignore);'),
             ('            if (!hit.hit()) return;',
              '            if (!hit.hit()) return;\n            if (observations) { auto& v=observations[bounce]; v.kind=2; v.triangle=hit.tri; v.t=hit.t; v.hit_position=ray.origin+ray.dir*hit.t; }'),
             ('            const V3 origin = p + n * offset_;',
              '            const V3 origin = p + n * offset_;\n            if (observations) { auto& v=observations[bounce]; v.nudged=p; v.spawn=origin; v.normal=n; v.front=front?1:0; }'),
             ('            const Rgb e = direct(origin, n, hit.tri, rng, cnt);',
              '            const Rgb e = direct(origin, n, hit.tri, rng, cnt);\n            if (observations) { auto& v=observations[bounce]; v.reflected={f[0]*e[0],f[1]*e[1],f[2]*e[2]}; }')]
    text=raw.decode()
    for old,new in changes:
        if text.count(old)!=1:raise ValueError('035 nonunique observation anchor: '+old[:70])
        text=text.replace(old,new)
    restored=text
    for old,new in reversed(changes):
        if restored.count(new)!=1:raise ValueError('035 nonunique inverse anchor')
        restored=restored.replace(new,old)
    if restored.encode()!=raw:raise ValueError('035 observation inverse differs')
    return text.encode(),dict(exact_inverse=True,original_sha256=hashlib.sha256(raw).hexdigest(),generated_sha256=hashlib.sha256(text.encode()).hexdigest(),changes='namespace, optional observation pointer and writes only; original sampling statements retained')
