#!/usr/bin/env python3
"""Build a separate sampling/importance-weight overlay; original physics untouched."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys
from generate_rqmc_oracle import ROOT, once

GUIDE = r'''
    // Prospective N010 plan 030: fixed mixture; geometry/direct-only CDF.
    struct GuideRay { V3 direction{}; uint32_t target{UINT32_MAX};
        double cosine_pdf{}; bool guided{}, valid{}; };
    std::vector<double> guide_area_,guide_cdf_;
    double guide_total_{};
    static constexpr double guide_cosine_fraction=0.75,guide_area_floor=0.10;
    void build_guide() {
        const size_t count=scene_.triangles.size();
        guide_area_.resize(count);guide_cdf_.resize(count);
        std::vector<double> proxy(count);double total_area=0,total_proxy=0;
        for(size_t i=0;i<count;++i) {
            const auto& t=scene_.triangles[i];const auto& m=scene_.materials[t.material];
            auto normal=cross(t.v1-t.v0,t.v2-t.v0);const double twice_area=length(normal);
            const double area=0.5*twice_area;guide_area_[i]=area;total_area+=area;
            if(!(area>0))continue;normal=normal*(1.0/twice_area);
            const auto centre=(t.v0+t.v1+t.v2)*(1.0/3.0);
            double irradiance=0;
            for(const auto& light:scene_.points) {
                const auto delta=light.position-centre;const double d2=dot(delta,delta);
                if(!(d2>0))continue;
                const double facing=dot(normal,delta*(1.0/std::sqrt(d2)));
                const double cosine=m.two_sided?std::abs(facing):std::max(0.0,facing);
                const double denominator=scene_.falloff==Falloff::InverseSquare?d2:scene_.soft_scale*scene_.soft_scale+d2;
                irradiance+=std::max({light.intensity[0],light.intensity[1],light.intensity[2]})*cosine/std::max(denominator,offset_*offset_);
            }
            proxy[i]=area*irradiance*std::max({m.rho[0],m.rho[1],m.rho[2]});total_proxy+=proxy[i];
        }
        if(!(total_area>0)){guide_cdf_.clear();return;}
        for(size_t i=0;i<count;++i) {
            const double weight=total_proxy>0 ? guide_area_floor*guide_area_[i]/total_area
                +(1-guide_area_floor)*proxy[i]/total_proxy : guide_area_[i]/total_area;
            guide_total_+=weight;guide_cdf_[i]=guide_total_;
        }
        if(!(guide_total_>0)||!std::isfinite(guide_total_))throw std::runtime_error("invalid guide CDF");
    }
    double guide_probability(uint32_t triangle) const {
        if(guide_cdf_.empty() || triangle>=guide_cdf_.size())return 0;
        const double old=triangle?guide_cdf_[triangle-1]:0;
        return (guide_cdf_[triangle]-old)/guide_total_;
    }
    GuideRay guide_sample(V3 origin,V3 normal,double u1,double u2) const {
        if(guide_cdf_.empty() || u1<guide_cosine_fraction) {
            auto direction=cosine_sample(normal,guide_cdf_.empty()?u1:u1/guide_cosine_fraction,u2);
            return {direction,UINT32_MAX,std::max(0.0,dot(normal,direction))/kPi,false,true};
        }
        const double pick=(u1-guide_cosine_fraction)/(1-guide_cosine_fraction)*guide_total_;
        auto found=std::upper_bound(guide_cdf_.begin(),guide_cdf_.end(),pick);
        if(found==guide_cdf_.end())throw std::runtime_error("guide CDF selection overflow");
        const uint32_t target=uint32_t(found-guide_cdf_.begin());
        const double old=target?guide_cdf_[target-1]:0,width=*found-old;
        if(!(width>0))throw std::runtime_error("zero-width selected guide triangle");
        const double remap=(pick-old)/width;
        if(!(remap>=0 && remap<1))throw std::runtime_error("guide conditional uniform outside range");
        const double root=std::sqrt(remap);
        const auto& t=scene_.triangles[target];
        const auto point=t.v0*(1-root)+t.v1*(root*(1-u2))+t.v2*(root*u2);
        const auto delta=point-origin;const double d2=dot(delta,delta);
        if(!(d2>0))return {};
        const auto direction=delta*(1.0/std::sqrt(d2));
        const double cosine=dot(normal,direction);
        return {direction,target,std::max(0.0,cosine)/kPi,true,cosine>0};
    }
'''


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


if __name__ == '__main__':
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--work', type=Path, required=True)
    ap.add_argument('--output', type=Path, required=True)
    a = ap.parse_args()
    if a.work.exists() or a.output.exists():
        raise ValueError('refuse existing guided build attempt')
    plan = ROOT/'research/lanes/n010-comparison-readiness/experiments/030-prospective-point-guided-reference-sampling.md'
    inputs = {str(p.resolve()): sha(p) for p in (Path(__file__), plan,
        ROOT/'scripts/research/n010_comparison_readiness/generate_cached_oracle.py',
        ROOT/'scripts/research/n010_comparison_readiness/generate_rqmc_oracle.py',
        ROOT/'src/research/n008_hdr_oracle/n008_oracle.hpp',
        ROOT/'src/research/n008_hdr_oracle/n008_oracle_main.cpp')}
    result = {'schema': 'n010-point-guided-oracle-build/1', 'complete': False,
        'all_pass': False, 'gpu_run': False, 'eligible_for_references': False,
        'input_sha256': inputs, 'steps': [], 'source_commit': subprocess.check_output(
            ['git', 'rev-parse', 'HEAD'], text=True).strip(),
        'constants': {'cosine_branch_probability': 0.75, 'area_floor_fraction': 0.10},
        'scope': 'Standalone CPU sampling prototype build only; no physical validation or reference admission'}
    def save():
        a.output.write_text(json.dumps(result, indent=2)+'\n')
    try:
        subprocess.run([sys.executable, str(ROOT/'scripts/research/n010_comparison_readiness/generate_cached_oracle.py'),
                        '--out', str(a.work)], check=True)
        path = a.work/'n010_rqmc_oracle.hpp'
        header = path.read_text()
        header = once(header, 'private:\n    const Scene& scene_;', 'private:\n'+GUIDE+'\n    const Scene& scene_;')
        header = once(header, '                emitter_cdf_.push_back(emitter_area_);\n            }\n        }\n    }',
                      '                emitter_cdf_.push_back(emitter_area_);\n            }\n        }\n        build_guide();\n    }')
        header = once(header, '    std::uint64_t primary_hits{}, shadow_tests{}, shadow_blocked{}, backface_absorbed{};',
                      '    std::uint64_t primary_hits{}, shadow_tests{}, shadow_blocked{}, backface_absorbed{}, proposal_null_samples{};')
        header = once(header, '        Rgb throughput{1, 1, 1};',
                      '        Rgb throughput{1, 1, 1};\n        GuideRay pending{};bool has_pending=false;')
        header = once(header, '            if (!hit.hit()) return;',
                      '            if (!hit.hit()) {if(has_pending && pending.guided)++cnt.proposal_null_samples;return;}\n'
                      '            if(has_pending && pending.guided && hit.tri!=pending.target){++cnt.proposal_null_samples;return;}')
        header = once(header, '            const bool front = dot(ng, ray.dir) < 0.0;',
                      '            if(has_pending){\n'
                      '                const double cy=std::abs(dot(ng,ray.dir));\n'
                      '                const double pg=cy>0 && guide_area_[hit.tri]>0 ? guide_probability(hit.tri)*hit.t*hit.t/(guide_area_[hit.tri]*cy):0;\n'
                      '                const double alpha=guide_cdf_.empty()?1.0:guide_cosine_fraction;\n'
                      '                const double density=alpha*pending.cosine_pdf+(1-alpha)*pg;\n'
                      '                if(!(density>0)||!std::isfinite(density))throw std::runtime_error("invalid guide mixture density");\n'
                      '                const double correction=pending.cosine_pdf/density;\n'
                      '                for(int channel=0;channel<3;++channel)throughput[channel]*=correction;\n'
                      '            }\n            const bool front = dot(ng, ray.dir) < 0.0;')
        header = once(header, '            ray = {origin, cosine_sample(n, n010_u1, n010_u2)};',
                      '            pending=guide_sample(origin,n,n010_u1,n010_u2);has_pending=true;\n'
                      '            if(!pending.valid){++cnt.proposal_null_samples;return;}\n'
                      '            ray = {origin,pending.direction};')
        header = once(header, '            total.backface_absorbed += c.backface_absorbed;',
                      '            total.backface_absorbed += c.backface_absorbed;\n            total.proposal_null_samples += c.proposal_null_samples;')
        path.write_text(header)
        path = a.work/'n010_rqmc_main.cpp'
        main = path.read_text()
        main = once(main, 'n010-rqmc-digital-shift', 'n010-rqmc-point-guided-mixture')
        main = once(main, '\\"backface_absorbed\\":%llu,\\"cpu_seconds_diagnostic\\":%.3f}',
                    '\\"backface_absorbed\\":%llu,\\"proposal_null_samples\\":%llu,\\"cpu_seconds_diagnostic\\":%.3f}')
        main = once(main, 'static_cast<unsigned long long>(counters.backface_absorbed), secs);',
                    'static_cast<unsigned long long>(counters.backface_absorbed),\n'
                    '                        static_cast<unsigned long long>(counters.proposal_null_samples), secs);')
        path.write_text(main)
        binary = a.work/'n010_point_guided_oracle'
        command = ['c++', '-std=c++20', '-O3', '-fno-fast-math', '-ffp-contract=off', '-pthread',
                   '-I', str(ROOT/'src/research/n008_hdr_oracle'), str(path), '-o', str(binary)]
        proc = subprocess.run(command, text=True, capture_output=True)
        result['steps'].append({'command': command, 'returncode': proc.returncode,
                               'stdout': proc.stdout, 'stderr': proc.stderr})
        result['all_pass'] = proc.returncode == 0
        result['generated_sha256'] = {p.name: sha(p) for p in a.work.iterdir() if p.is_file()}
        if any(sha(Path(p)) != h for p, h in inputs.items()):
            raise ValueError('source changed during build')
    except (OSError, ValueError, subprocess.CalledProcessError) as error:
        result['failure'] = str(error)
        result['all_pass'] = False
    result['complete'] = True
    save()
    raise SystemExit(0 if result['all_pass'] else 2)
