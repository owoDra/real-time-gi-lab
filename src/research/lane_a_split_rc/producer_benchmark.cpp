#include "a001_analysis.hpp"
#include "a001_runtime.hpp"
#include "a001_scene.hpp"
#include "vk_context.hpp"
#include <cstdlib>
#include <filesystem>
#include <iomanip>
#include <iostream>
#include <stdexcept>
#include <string>

namespace phos::gi::lane_a {
namespace {

struct Cli {
    std::filesystem::path scene{
        "assets/Vulkan-Samples-Assets/scenes/sponza/Sponza01.gltf"};
    std::filesystem::path output_dir{};
    A001Settings settings{};
    std::uint32_t iterations{50};
    bool validation{};
    bool synthetic{};
};

A001Case parse_case(const std::string& value) {
    if(value=="static") return A001Case::Static;
    if(value=="camera-motion") return A001Case::CameraMotion;
    if(value=="light-motion") return A001Case::LightMotion;
    throw std::runtime_error("Unknown A001 case: "+value);
}

Cli parse(int argc,char**argv) {
    Cli c;
    for(int i=1;i<argc;++i){
        const std::string a=argv[i];
        const auto value=[&](const char* flag){
            if(i+1>=argc)
                throw std::runtime_error(std::string(flag)+" needs a value");
            return std::string(argv[++i]);
        };

        if(a=="--scene") c.scene=value("--scene");
        else if(a=="--output-dir") c.output_dir=value("--output-dir");
        else if(a=="--case") c.settings.case_id=parse_case(value("--case"));
        else if(a=="--iterations")
            c.iterations=static_cast<std::uint32_t>(std::stoul(value("--iterations")));
        else if(a=="--width")
            c.settings.tile_width=static_cast<std::uint32_t>(std::stoul(value("--width")));
        else if(a=="--height")
            c.settings.tile_height=static_cast<std::uint32_t>(std::stoul(value("--height")));
        else if(a=="--cascades")
            c.settings.cascade_count=static_cast<std::uint32_t>(std::stoul(value("--cascades")));
        else if(a=="--rays-per-probe")
            c.settings.rays_per_probe=static_cast<std::uint32_t>(std::stoul(value("--rays-per-probe")));
        else if(a=="--validation") c.validation=true;
        else if(a=="--synthetic") c.synthetic=true;
        else if(a=="--help"){
            std::cout
                <<"phos-lane-a-split-rc "
                  "--case static|camera-motion|light-motion "
                  "[--scene path] [--iterations N] "
                  "[--output-dir path] [--validation] [--synthetic]\n";
            std::exit(0);
        } else {
            throw std::runtime_error("Unknown argument: "+a);
        }
    }

    c.settings.frame_id=
        c.settings.case_id==A001Case::Static
            ? 0u
            : (c.settings.case_id==A001Case::CameraMotion ? 1u : 2u);

    if(c.iterations==0)
        throw std::runtime_error("A001 iterations must be positive");

    if(c.output_dir.empty())
        c.output_dir=
            std::filesystem::path(
                "out/research/lane-a-split-rc/"
                "001-representative-producer/manual")/
            case_name(c.settings.case_id);
    return c;
}

} // namespace
} // namespace phos::gi::lane_a

int main(int argc,char**argv) {
    using namespace phos::gi;
    using namespace phos::gi::lane_a;

    try{
        const auto cli=parse(argc,argv);
        SceneSurfaceSet scene;

        if(cli.synthetic){
            std::cerr
                <<"A001: synthetic bring-up workload "
                  "(not architectural evidence)\n";
            scene=make_synthetic_surface_samples(262144);
        }else{
            if(!std::filesystem::exists(cli.scene))
                throw std::runtime_error(
                    "Scene not found: "+cli.scene.string());
            scene=load_scene_surface_samples(cli.scene);
        }

        const auto params=build_a001_params(scene,cli.settings);
        VulkanContext vk(cli.validation);
        std::cerr << "GPU: " << vk.device_name() << '\n';
        A001Runtime runtime(vk,scene,params);

        const auto timings=runtime.measure(cli.iterations);
        const auto readback=runtime.readback();
        const auto analysis=analyze_a001(
            scene,cli.settings,params,readback);
        const auto memory=runtime.memory();

        const char* commit_env=std::getenv("PHOS_RESEARCH_GIT_COMMIT");
        const std::string commit=commit_env?commit_env:"unknown";

        write_a001_artifacts(
            cli.output_dir,
            scene,
            cli.settings,
            params,
            timings,
            memory,
            readback,
            analysis,
            vk.device_name(),
            commit);

        std::cout
            <<std::fixed
            <<std::setprecision(3)
            <<"case="<<case_name(cli.settings.case_id)
            <<" gpu=\""<<vk.device_name()<<"\""
            <<" surfaces="<<scene.samples.size()
            <<" visible_probes="<<analysis.visible_probe_count
            <<" work_items="<<readback.work_items.size()
            <<" producer_us="<<timings.producer_total_us
            <<" gather_us="<<timings.gather_us
            <<" merge_us="<<timings.merge_us
            <<" resolve_us="<<timings.resolve_us
            <<" end_to_end_us="<<timings.end_to_end_us
            <<" correctness="<<(analysis.correct()?"pass":"FAIL")
            <<'\n';

        if(!analysis.correct()){
            for(const auto& e:analysis.errors)
                std::cerr<<"correctness: "<<e<<'\n';
            return 2;
        }
        return 0;
    }catch(const std::exception&e){
        std::cerr<<"fatal: "<<e.what()<<'\n';
        return 1;
    }
}
