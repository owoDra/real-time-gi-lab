#include "n002_runtime.cpp"

namespace phos::gi::research::integration {

void I001Runtime::set_n004_motion_fraction(float fraction) {
    if (!std::isfinite(fraction) || fraction < 0.0F || fraction > 1.0F) {
        throw std::runtime_error("N004 motion fraction must be finite and within [0,1]");
    }
    impl_->settings.camera_motion_fraction = fraction;
    impl_->settings.light_motion_fraction = fraction;
}

} // namespace phos::gi::research::integration
