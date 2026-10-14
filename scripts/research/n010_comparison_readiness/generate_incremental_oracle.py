#!/usr/bin/env python3
"""Amendment 6: restore exact power-of-two prefix sums, then continue sampling."""
import argparse
from pathlib import Path
import subprocess
import sys
from generate_rqmc_oracle import once

ROOT = Path(__file__).resolve().parents[3]

LOADER = r'''
std::vector<PixelStats> read_prefix(const std::string& path, const Scene& scene,
                                  uint64_t seed, uint32_t previous_spp) {
    if(previous_spp==0 || (previous_spp & (previous_spp-1)))
        throw std::runtime_error("prefix must be a positive power of two");
    std::ifstream in(path,std::ios::binary);
    char magic[8]{}; uint32_t header[3]{}; uint64_t stored_seed{};
    in.read(magic,8);in.read(reinterpret_cast<char*>(header),sizeof(header));
    in.read(reinterpret_cast<char*>(&stored_seed),sizeof(stored_seed));
    if(!in || std::memcmp(magic,"N008F64\0",8) || header[0]!=scene.width ||
       header[1]!=scene.height || header[2]!=previous_spp || stored_seed!=seed)
        throw std::runtime_error("prefix header/dimension/seed mismatch");
    std::vector<PixelStats> stats(size_t(scene.width)*scene.height);
    for(auto& ps:stats) {
        double rec[24]{};in.read(reinterpret_cast<char*>(rec),sizeof(rec));
        if(!in)throw std::runtime_error("truncated prefix");
        for(int k=0;k<=kComponents;++k)for(int c=0;c<3;++c) {
            const auto restore=[&](double value) {
                if(!std::isfinite(value) || value<0 || (value!=0 && std::fpclassify(value)==FP_SUBNORMAL))
                    throw std::runtime_error("nonfinite/negative/subnormal prefix moment");
                double sum=value*double(previous_spp);
                double roundtrip=sum*(1.0/double(previous_spp));
                if(!std::isfinite(sum) || std::memcmp(&roundtrip,&value,sizeof(value)))
                    throw std::runtime_error("prefix sum round trip failed");
                return sum;
            };
            ps.sum[k][c]=restore(rec[k*3+c]);
            ps.sum2[k][c]=restore(rec[12+k*3+c]);
        }
    }
    if(in.peek()!=std::char_traits<char>::eof())throw std::runtime_error("prefix trailing bytes");
    return stats;
}
std::vector<RenderCounters> parse_prefix_counters(const std::string& text) {
    std::vector<RenderCounters> result;
    std::stringstream stream(text);std::string item;
    while(std::getline(stream,item,';')) {
        std::stringstream row(item);std::string field;uint64_t values[4]{};
        for(int k=0;k<4;++k) {
            if(!std::getline(row,field,','))throw std::runtime_error("prefix counters missing field");
            size_t consumed{};values[k]=std::stoull(field,&consumed);
            if(consumed!=field.size())throw std::runtime_error("invalid prefix counter");
        }
        if(std::getline(row,field,','))throw std::runtime_error("extra prefix counter");
        RenderCounters count{};count.primary_hits=values[0];count.shadow_tests=values[1];
        count.shadow_blocked=values[2];count.backface_absorbed=values[3];result.push_back(count);
    }
    return result;
}
'''

if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out',type=Path,required=True)
    args=parser.parse_args()
    if args.out.exists():
        raise ValueError('refuse existing generated source')
    subprocess.run([sys.executable,str(ROOT/'scripts/research/n010_comparison_readiness/generate_cached_oracle.py'),
                    '--out',str(args.out)],check=True)
    path=args.out/'n010_rqmc_oracle.hpp';header=path.read_text()
    header=once(header,'                                   std::vector<std::vector<PixelStats>>* snapshots = nullptr) const {',
                '                                   std::vector<std::vector<PixelStats>>* snapshots = nullptr,\n'
                '                                   uint32_t start_spp=0, const std::vector<PixelStats>* initial=nullptr) const {')
    header=once(header,'        std::vector<PixelStats> stats(std::size_t(scene_.width) * scene_.height);',
                '        std::vector<PixelStats> stats = initial ? *initial : std::vector<PixelStats>(std::size_t(scene_.width) * scene_.height);\n'
                '        if(start_spp>=spp || stats.size()!=std::size_t(scene_.width)*scene_.height)\n'
                '            throw std::runtime_error("invalid incremental prefix");')
    header=once(header,'                        for (std::uint32_t s = 0; s < spp; ++s) {',
                '                        for (std::uint32_t s = start_spp; s < spp; ++s) {')
    header=once(header,'primary && s == 0 ? &(*primary)[pixel] : nullptr, &cache);',
                'primary && s == start_spp ? &(*primary)[pixel] : nullptr, &cache);')
    path.write_text(header)
    path=args.out/'n010_rqmc_main.cpp';main=path.read_text()
    main=once(main,'int main(int argc, char** argv) {',LOADER+'\nint main(int argc, char** argv) {')
    main=once(main,'        std::vector<std::uint32_t> checkpoints;',
                '        std::string prefix_path,prefix_counter_text;uint32_t prefix_spp{};\n'
                '        std::vector<std::uint32_t> checkpoints;')
    main=once(main,'            else if (a == "--checkpoints") {',
                '            else if(a=="--resume-prefix")prefix_path=value();\n'
                '            else if(a=="--resume-spp")prefix_spp=uint32_t(std::stoul(value()));\n'
                '            else if(a=="--resume-counters")prefix_counter_text=value();\n'
                '            else if (a == "--checkpoints") {')
    main=once(main,'        for (std::size_t i = 0; i < checkpoints.size(); ++i)',
                '        std::vector<RenderCounters> prefix_counters;\n'
                '        if(!prefix_path.empty()) {\n'
                '            if(prefix_spp==0 || prefix_spp>=spp || !checkpoints.empty())\n'
                '                throw std::runtime_error("invalid prefix/checkpoint combination");\n'
                '            prefix_counters=parse_prefix_counters(prefix_counter_text);\n'
                '            if(prefix_counters.size()!=seeds.size())throw std::runtime_error("prefix seed counter count");\n'
                '        } else if(prefix_spp || !prefix_counter_text.empty())throw std::runtime_error("missing prefix path");\n'
                '        for (std::size_t i = 0; i < checkpoints.size(); ++i)')
    main=once(main,'            RenderCounters counters;',
                '            RenderCounters counters = prefix_path.empty() ? RenderCounters{} : prefix_counters[si];\n'
                '            std::vector<PixelStats> initial;\n'
                '            if(!prefix_path.empty())initial=read_prefix(prefix_path+".s"+std::to_string(si)+".f64",scene,seeds[si],prefix_spp);')
    main=once(main,'                                             checkpoints, &snapshots);',
                '                                             checkpoints, &snapshots, prefix_path.empty()?0:prefix_spp, prefix_path.empty()?nullptr:&initial);')
    path.write_text(main)
