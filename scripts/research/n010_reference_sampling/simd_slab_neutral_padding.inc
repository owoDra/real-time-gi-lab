    struct alignas(32) PackedBox { double lo[4], hi[4]; };
    std::vector<PackedBox> packed_boxes_;

    static bool slab_simd(const PackedBox& box, __m256d origin, __m256d inverse,
                          double tmin, double tmax) {
        const auto lo = _mm256_load_pd(box.lo), hi = _mm256_load_pd(box.hi);
        const auto a = _mm256_mul_pd(_mm256_sub_pd(lo, origin), inverse);
        const auto b = _mm256_mul_pd(_mm256_sub_pd(hi, origin), inverse);
        const auto nan = _mm256_or_pd(_mm256_cmp_pd(a, b, _CMP_UNORD_Q),
            _mm256_castsi256_pd(_mm256_set_epi64x(-1LL, 0, 0, 0)));
        const auto outside = _mm256_or_pd(_mm256_cmp_pd(origin, lo, _CMP_LT_OQ),
                                          _mm256_cmp_pd(origin, hi, _CMP_GT_OQ));
        if (_mm256_movemask_pd(_mm256_and_pd(nan, outside)) & 7) return false;
        // The scalar predicate skips an axis if either product is NaN.
        const auto swap = _mm256_cmp_pd(a, b, _CMP_GT_OQ);
        auto near = _mm256_blendv_pd(a, b, swap);
        auto far = _mm256_blendv_pd(b, a, swap);
        far = _mm256_mul_pd(far, _mm256_set1_pd(1.0 + 4.0 * std::numeric_limits<double>::epsilon()));
        near = _mm256_blendv_pd(near, _mm256_set1_pd(-kInf), nan);
        far = _mm256_blendv_pd(far, _mm256_set1_pd(kInf), nan);
        const auto near2 = _mm_max_pd(_mm256_castpd256_pd128(near), _mm256_extractf128_pd(near, 1));
        const auto far2 = _mm_min_pd(_mm256_castpd256_pd128(far), _mm256_extractf128_pd(far, 1));
        const double lower = _mm_cvtsd_f64(_mm_max_sd(near2, _mm_unpackhi_pd(near2, near2)));
        const double upper = _mm_cvtsd_f64(_mm_min_sd(far2, _mm_unpackhi_pd(far2, far2)));
        if ((_mm256_movemask_pd(nan) & 7) == 7) return true;
        return !(std::max(tmin, lower) > std::min(tmax, upper));
    }
