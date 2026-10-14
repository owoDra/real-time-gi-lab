#!/usr/bin/env python3
"""Opt-in neutral-work overlay and full-runtime calibration capture loop."""
def once(s,old,new):
 if s.count(old)!=1:raise ValueError('N010 calibration source drift: '+old[:70])
 return s.replace(old,new)
def runtime(s):
 s=once(s,'#include "n001_runtime.hpp"','#include "n001_runtime.hpp"\n#include "neutral_work.hpp"')
 s=once(s,'    B002Buffer primary_hits{}, image{}, n010_lookup_audit{};','    B002Buffer primary_hits{}, image{}, n010_lookup_audit{};\n    std::unique_ptr<phos::gi::research::n010::NeutralWork> n010_neutral;')
 s=once(s,'        n010_lookup_audit = context.create_device_buffer(', '        if(std::getenv("PHOS_N010_CALIBRATION")) n010_neutral=std::make_unique<phos::gi::research::n010::NeutralWork>(context);\n        n010_lookup_audit = context.create_device_buffer(')
 s=once(s,'        depth_stage.reset();','        depth_stage.reset();\n        n010_neutral.reset();')
 s=once(s,'        stamp(15);','        if(n010_neutral)n010_neutral->record(command);\n        stamp(15);')
 s=once(s,'        save("composite-lookup.bin", audit_bytes.data(), audit_bytes.size());','        save("composite-lookup.bin", audit_bytes.data(), audit_bytes.size());\n        if(impl_->n010_neutral)impl_->n010_neutral->save(std::filesystem::path(directory)/"neutral-work.bin");')
 return s
LOOP=r'''
        if(!calibration_doses.empty()) {
            setenv("PHOS_N010_CALIBRATION","1",1);
            std::ifstream dose_file(calibration_doses);std::vector<uint32_t> doses;
            uint32_t dose;while(dose_file>>dose)doses.push_back(dose);
            if(!dose_file.eof()||doses.empty()||doses.size()>256)throw std::runtime_error("invalid calibration dose file");
            std::ofstream timings(out/"calibration-timings.jsonl");timings<<std::setprecision(17);
            std::unique_ptr<r::I001Runtime> stable;
            if(!target) {
                stable=std::make_unique<r::I001Runtime>(opt);
                if(backend=="vanilla")stable->configure_n003_vanilla_software_baseline();
            }
            for(size_t index=0;index<doses.size();++index) {
                std::unique_ptr<r::I001Runtime> fresh;
                if(target) {
                    setenv("PHOS_N010_CALIBRATION_DOSE","0",1);
                    fresh=std::make_unique<r::I001Runtime>(opt);
                    if(backend=="vanilla")fresh->configure_n003_vanilla_software_baseline();
                    const auto source_frame=fresh->run_frame(false);
                    if(source_frame.stats.overflow)throw std::runtime_error("calibration source overflow");
                }
                auto& runtime=target ? *fresh : *stable;
                const auto text=std::to_string(doses[index]);setenv("PHOS_N010_CALIBRATION_DOSE",text.c_str(),1);
                const auto start=std::chrono::steady_clock::now();
                const auto f=topology ? runtime.run_topology_churn_frame() : runtime.run_frame(target);
                const auto wall=std::chrono::duration<double,std::micro>(std::chrono::steady_clock::now()-start).count();
                if(f.stats.overflow)throw std::runtime_error("calibration Renderer overflow");
                timings<<"{\"index\":"<<index<<",\"dose\":"<<doses[index]<<",\"gpu_us\":"<<f.timings.complete_renderer_gpu_us
                       <<",\"wall_us\":"<<wall<<",\"maintenance_gpu_us\":"<<f.timings.traversal_maintenance_gpu_us<<"}\n";
                const auto directory=out/"frames"/std::to_string(index);fs::create_directories(directory/"gpu");
                const auto gpu=fs::absolute(directory/"gpu");
                setenv("PHOS_N007_GPU_HITS",(gpu/"hits.bin").c_str(),1);
                setenv("PHOS_N007_GPU_PRIMARY_GEOMETRY",(gpu/"primary-geometry.bin").c_str(),1);
                setenv("PHOS_N007_PROBE_DIR",gpu.c_str(),1);
                const auto image=runtime.renderer_readback();capture_state(directory,image);
                for(uint32_t component=0;component<3;++component) {
                    std::vector<float> values(size_t(image.width)*image.height);
                    for(size_t px=0;px<values.size();++px)values[px]=image.image_rgba[4*px+component];
                    const char* names[]{"direct.pfm","indirect.pfm","total.pfm"};
                    pfm(gpu/names[component],image.width,image.height,values);
                }
            }
            if(!timings)throw std::runtime_error("calibration timings write failed");
            return 0;
        }
'''
def main(s):
 s=once(s,'        fs::path out,scene;','        fs::path out,scene,calibration_doses;')
 s=once(s,'            else if(arg=="--direct-profile")profile=arg_value(argc,argv,i);','            else if(arg=="--direct-profile")profile=arg_value(argc,argv,i);\n            else if(arg=="--calibration-doses")calibration_doses=arg_value(argc,argv,i);')
 s=once(s,'        r::I001Runtime runtime(opt);',LOOP+'        r::I001Runtime runtime(opt);')
 return s
