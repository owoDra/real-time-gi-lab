#include "i001_contract.hpp"
#include "i001_runtime.hpp"
#include "vk_context.hpp"

#include <array>
#include <cstdint>
#include <cstdlib>
#include <filesystem>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <stdexcept>
#include <string>

namespace lane_i = phos::gi::research::lane_i;
using phos::gi::VulkanContext;

namespace {

struct Cli {
    enum class Mode { Validate, Measure } mode{Mode::Validate};
    lane_i::CalibrationVariant candidate{lane_i::CalibrationVariant::Plus20};
    std::string start_order{"AB"};
    std::uint32_t elements{lane_i::kDefaultElementCount};
    std::uint32_t batch_dispatches{lane_i::kDefaultBatchDispatches};
    std::uint32_t warmup_pairs{4};
    std::uint32_t measured_pairs{16};
    bool validation{};
};

[[noreturn]] void fail(const std::string& message) {
    throw std::runtime_error(message);
}

std::filesystem::path artifact_root() {
    if (const char* value = std::getenv("PHOS_RESEARCH_ARTIFACT_DIR");
        value != nullptr && *value != '\0') {
        return value;
    }
    return "out/research/lane-i-measurement-calibration/001-calibration-workload/manual";
}

Cli parse_cli(int argc, char** argv) {
    Cli cli;
    for (int index = 1; index < argc; ++index) {
        const std::string argument = argv[index];
        const auto value = [&](const char* option) -> std::string {
            if (index + 1 >= argc) fail(std::string(option) + " requires a value");
            return argv[++index];
        };
        if (argument == "--mode") {
            const auto mode = value("--mode");
            if (mode == "validate") cli.mode = Cli::Mode::Validate;
            else if (mode == "measure") cli.mode = Cli::Mode::Measure;
            else fail("--mode must be validate or measure");
        } else if (argument == "--candidate") {
            cli.candidate = lane_i::parse_variant(value("--candidate"));
        } else if (argument == "--start-order") {
            cli.start_order = value("--start-order");
            if (cli.start_order != "AB" && cli.start_order != "BA") {
                fail("--start-order must be AB or BA");
            }
        } else if (argument == "--elements") {
            cli.elements = static_cast<std::uint32_t>(std::stoul(value("--elements")));
        } else if (argument == "--batch-dispatches") {
            cli.batch_dispatches = static_cast<std::uint32_t>(
                std::stoul(value("--batch-dispatches")));
        } else if (argument == "--warmup-pairs") {
            cli.warmup_pairs = static_cast<std::uint32_t>(
                std::stoul(value("--warmup-pairs")));
        } else if (argument == "--measured-pairs") {
            cli.measured_pairs = static_cast<std::uint32_t>(
                std::stoul(value("--measured-pairs")));
        } else if (argument == "--validation") {
            cli.validation = true;
        } else if (argument == "--help") {
            std::cout
                << "phos-lane-i-i001 --mode validate|measure "
                   "[--candidate baseline|plus5|plus10|plus20] "
                   "[--start-order AB|BA] [--elements N] [--batch-dispatches N] "
                   "[--warmup-pairs N] [--measured-pairs N] [--validation]\n";
            std::exit(0);
        } else {
            fail("unknown Lane I argument: " + argument);
        }
    }
    if (cli.measured_pairs == 0U && cli.mode == Cli::Mode::Measure) {
        fail("measurement mode requires at least one measured pair");
    }
    (void)lane_i::make_work_spec(
        lane_i::CalibrationVariant::Baseline, cli.elements, cli.batch_dispatches);
    return cli;
}

void write_device(const std::filesystem::path& root, const VulkanContext& vk, bool validation) {
    std::ofstream out(root / "i001-device.json");
    if (!out) fail("cannot create Lane I device metadata");
    out << "{\n"
        << "  \"schema_version\": 1,\n"
        << "  \"device\": \"" << vk.device_name() << "\",\n"
        << "  \"timestamp_period_ns\": " << vk.timestamp_period_ns() << ",\n"
        << "  \"validation\": " << (validation ? "true" : "false") << "\n"
        << "}\n";
}

void run_validation(const Cli& cli, VulkanContext& vk, lane_i::CalibrationGpu& gpu) {
    const auto root = artifact_root();
    std::filesystem::create_directories(root);
    write_device(root, vk, cli.validation);

    std::ofstream out(root / "i001-validation.csv");
    if (!out) fail("cannot create Lane I validation CSV");
    out << "variant,elements,work_iterations,batch_dispatches,controlled_work_units,"
           "gpu_checksum,reference_checksum,correct\n";

    const std::array variants{
        lane_i::CalibrationVariant::Baseline,
        lane_i::CalibrationVariant::Plus5,
        lane_i::CalibrationVariant::Plus10,
        lane_i::CalibrationVariant::Plus20,
    };
    bool all_correct = true;
    for (const auto variant : variants) {
        const auto result = gpu.run(variant, cli.batch_dispatches);
        const auto gpu_checksum = gpu.download_checksum();
        const auto reference_checksum = gpu.reference_checksum(variant, cli.batch_dispatches);
        const bool correct = gpu_checksum == reference_checksum;
        all_correct = all_correct && correct;
        out << lane_i::variant_name(variant) << ',' << cli.elements << ','
            << lane_i::work_iterations(variant) << ',' << cli.batch_dispatches << ','
            << result.controlled_work_units << ',' << gpu_checksum << ','
            << reference_checksum << ',' << (correct ? "true" : "false") << '\n';
    }
    if (!all_correct) fail("Lane I GPU/reference checksum validation failed");
}

void write_measurement_row(
    std::ostream& out,
    const char* phase,
    std::uint32_t pair_index,
    const char* role,
    const char* order,
    const lane_i::BatchResult& result) {
    out << phase << ',' << pair_index << ',' << role << ',' << order << ','
        << lane_i::variant_name(result.variant) << ',' << result.controlled_work_units << ','
        << std::fixed << std::setprecision(6) << result.gpu_us << ',' << result.wall_us << '\n';
}

void run_pairs(const Cli& cli, VulkanContext& vk, lane_i::CalibrationGpu& gpu) {
    const auto root = artifact_root();
    std::filesystem::create_directories(root);
    write_device(root, vk, cli.validation);
    std::ofstream out(root / "i001-samples.csv");
    if (!out) fail("cannot create Lane I sample CSV");
    out << "phase,pair_index,role,order,variant,controlled_work_units,gpu_us,complete_wall_us\n";

    const auto run_phase = [&](const char* phase, std::uint32_t pair_count) {
        for (std::uint32_t pair = 0; pair < pair_count; ++pair) {
            const bool start_ab = cli.start_order == "AB";
            const bool ab = (pair & 1U) == 0U ? start_ab : !start_ab;
            const char* order = ab ? "AB" : "BA";
            const auto run_a = [&]() {
                return gpu.run(lane_i::CalibrationVariant::Baseline, cli.batch_dispatches);
            };
            const auto run_b = [&]() { return gpu.run(cli.candidate, cli.batch_dispatches); };
            if (ab) {
                const auto a = run_a();
                const auto b = run_b();
                write_measurement_row(out, phase, pair, "A", order, a);
                write_measurement_row(out, phase, pair, "B", order, b);
            } else {
                const auto b = run_b();
                const auto a = run_a();
                write_measurement_row(out, phase, pair, "B", order, b);
                write_measurement_row(out, phase, pair, "A", order, a);
            }
        }
    };

    run_phase("warmup", cli.warmup_pairs);
    run_phase("measured", cli.measured_pairs);
}

} // namespace

int main(int argc, char** argv) {
    try {
        const auto cli = parse_cli(argc, argv);
        VulkanContext vk(cli.validation);
        std::cout << "GPU: " << vk.device_name() << '\n';
        lane_i::CalibrationGpu gpu(vk, cli.elements);
        if (cli.mode == Cli::Mode::Validate) run_validation(cli, vk, gpu);
        else run_pairs(cli, vk, gpu);
        return 0;
    } catch (const std::exception& error) {
        std::cerr << "Lane I I001 error: " << error.what() << '\n';
        return 1;
    }
}
