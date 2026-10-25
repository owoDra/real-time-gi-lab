"""030 independent geometry/SVD/full-field replay and signed-aware fsum audit."""
import math
from pathlib import Path
import resource
import numpy as np
import surface_residual_corrected_replay as R
from surface_residual_audit import independent_geometry, features, sums_and_variance


def percentile(values, fraction):
    values = sorted(map(float, values)); position = (len(values)-1)*fraction
    lo = math.floor(position); hi = math.ceil(position)
    return values[lo]+(values[hi]-values[lo])*(position-lo)


def metric(a, ref, *, signed=False):
    a, ref = np.asarray(a, float), np.asarray(ref, float)
    R.K.need(a.shape == ref.shape and a.size > 0 and np.isfinite(a).all() and np.isfinite(ref).all(),
             '030 audit HDR shape/finiteness/empty')
    a, ref = a.ravel(), ref.ravel()
    R.K.need((ref >= 0).all() and (signed or (a >= 0).all()), '030 audit negative physical radiance')
    error = a-ref; count = len(a)
    rms = math.sqrt(math.fsum(float(x)**2 for x in ref)/count)
    total = math.fsum(map(float, ref))
    R.K.need(math.isfinite(rms) and math.isfinite(total) and rms > 0 and total > 0,
             '030 audit undefined physical reference')
    rmse = math.sqrt(math.fsum(float(x)**2 for x in error)/count)
    active = ref > 0; absolute = np.abs(error[active]); relative = absolute/ref[active]
    return dict(pixels=count, scoring_exclusions=0, rmse=rmse, reference_rms=rms, nrmse=rmse/rms,
                signed_sum_bias=math.fsum(map(float, error))/total, reference_sum=total,
                gpu_sum=math.fsum(map(float, a)), active_pixels=int(active.sum()),
                active_p99_absolute=percentile(absolute, .99), active_p99_relative=percentile(relative, .99),
                active_max_relative=max(map(float, relative)),
                whole_image_max_absolute=max(abs(float(x)) for x in error),
                gpu_zero_reference_positive=int(((a <= 0) & active).sum()),
                reference_zero_leak_pixels=int(((a > 0) & ~active).sum()),
                reference_zero_leak_energy=math.fsum(map(float, a[~active])))


def audit(cell, depth, out):
    R.limits(); head = R.committed(); native = R.BASE/(R.tag(cell, depth)+'-v1/result.json')
    n = R.B.read(native)
    R.K.need(n['complete'] and n['valid'] and n['source_commit'] == head, '030 audit requires valid unchanged-source native')
    R.B.rehash(n['input_sha256']); R.B.rehash({str(native.parent/k): h for k, h in n['payload_sha256'].items()})
    R.K.need(R.B.inventory(native.parent) == n['payload_sha256'], '030 native inventory drift')
    out = R.reserve(out, R.BASE/(R.tag(cell, depth)+'-audit-v1'))
    r = dict(schema='m001-residual030-independent-cpu-audit/1', cell=cell, depth=depth, source_commit=head,
             native_receipt=str(native), native_receipt_sha256=R.B.SHA(native), complete=False, valid=False,
             all_pass=False, gpu_executed=False, accepted_timing=False, classification='INVALID_STOP_NO_RETRY',
             input_sha256={**n['input_sha256'], str(native): R.B.SHA(native)})
    try:
        pins = r['input_sha256']; info = R.intake(cell, depth, out, pins)
        artifact = Path(n['artifact_directory'])
        R.B.rehash({str(artifact/k): h for k, h in n['artifact_sha256'].items()})
        with np.load(artifact/'field.npz') as z: field = {k: z[k] for k in z.files}
        with np.load(artifact/'frames.npz') as z: saved = {k: z[k] for k in z.files}
        with np.load(artifact/'images.npz') as z: images = {k: z[k] for k in z.files}
        frozen = R.B.read(artifact/'fit-frozen.json'); final = R.B.read(artifact/'evaluation-frozen.json')
        R.K.need(frozen['field_sha256'] == final['field_sha256'] == R.B.SHA(artifact/'field.npz')
                 and final['frames_sha256'] == R.B.SHA(artifact/'frames.npz')
                 and final['images_sha256'] == R.B.SHA(artifact/'images.npz')
                 and frozen['training_frames'] == list(range(8)) and not frozen['evaluation_radiance_decoded']
                 and not frozen['reference_radiance_decoded'] and not final['reference_radiance_decoded'], '030 freeze/source chronology')
        keys, groups, normal, mu, active = independent_geometry(info)
        R.K.need(np.array_equal(keys, field['keys']) and np.array_equal(groups, field['groups'])
                 and np.array_equal(active, field['active']), '030 independent geometry-only partition')
        np.testing.assert_allclose(normal, field['normal'], rtol=0, atol=1e-14)
        np.testing.assert_allclose(mu, field['mu'], rtol=0, atol=1e-14)
        raw = []; direct = []; phi = []
        for i in range(64):
            y, d, _ = R.read_frame(info, i, out); raw.append(y); direct.append(d)
            w = np.fromfile(info['capture']/f'frame-{i}/secondary-rays.f32', dtype='<f4').reshape(57600, 4)[:, :3].astype(float)
            w[~active] = [0, 0, 1]; phi.append(features(w))
        raw = np.array(raw); direct = np.array(direct); phi = np.array(phi)
        R.K.need(np.array_equal(raw, saved['raw_indirect']) and np.array_equal(direct, saved['raw_direct']),
                 '030 complete new sample copies differ from actual026')
        scale_train = max(float(np.abs(raw[:8]).max()), 1e-20); scale = max(float(np.abs(raw).max()), 1e-20)
        coefficients = np.empty_like(field['coefficients']); lambdas = []
        for group in range(len(keys)):
            x = phi[:8, groups == group].reshape(-1, 9); y = raw[:8, groups == group].ravel()
            gram = x.T@x; lam = 1e-3*np.trace(gram)/9
            coefficients[group] = np.linalg.lstsq(np.vstack((x, math.sqrt(lam)*np.eye(9))), np.r_[y, np.zeros(9)], rcond=None)[0]
            np.testing.assert_allclose(gram, field['gram'][group], rtol=1e-12, atol=1e-10)
            np.testing.assert_allclose(x.T@y, field['rhs'][group], rtol=1e-12, atol=1e-12*scale_train)
            R.K.need(math.isclose(lam, float(field['lambdas'][group]), rel_tol=1e-12)
                     and field['training_samples'][group] == len(y), '030 all training samples/ridge scale')
            lambdas.append(lam)
        np.testing.assert_allclose(coefficients, field['coefficients'], rtol=1e-8, atol=1e-12*scale_train)
        per_pixel = np.zeros((57600, 9)); per_pixel[active] = coefficients[groups[active]]
        corrected = raw[8:].copy()
        for column in range(9): corrected += (mu[:, column]-phi[8:, :, column])*per_pixel[:, column]
        np.testing.assert_allclose(corrected, saved['corrected_evaluation'], rtol=1e-10, atol=1e-12*scale)
        drift = phi[8:].mean(axis=0)-mu; drift[~active] = 0
        np.testing.assert_allclose(drift, saved['moment_drift'], rtol=1e-10, atol=1e-12)
        train_mean, train_var = sums_and_variance(raw[:8])
        raw_mean, raw_var = sums_and_variance(raw[8:])
        corrected_mean, corrected_var = sums_and_variance(corrected)
        expected = dict(baseline=(8*train_mean+56*raw_mean)/64, signed=(8*train_mean+56*corrected_mean)/64)
        expected['clipped'] = np.maximum(expected['signed'], 0)
        direct_mean = np.array([math.fsum(map(float, direct[:, p]))/64 for p in range(57600)])
        np.testing.assert_allclose(direct_mean, images['direct'], rtol=1e-10, atol=1e-12*scale)
        for name in expected: np.testing.assert_allclose(expected[name], images[name], rtol=1e-10, atol=1e-12*scale)
        t, raw_v, s = [math.fsum(map(float, x)) for x in (train_var, raw_var, corrected_var)]
        R.K.need(min(t, raw_v, s) > 0, '030 audit zero empirical variance')
        ratio = (8*t+56*raw_v)/(8*t+56*s)
        for key, value in [('training_variance', t), ('raw_evaluation_variance', raw_v), ('corrected_evaluation_variance', s), ('ratio', ratio)]:
            R.K.need(math.isclose(value, n['variance'][key], rel_tol=1e-10, abs_tol=1e-30), '030 independent fsum variance mismatch')
        reference = R.reference(info, out); scores = {}; error_maps = {}
        for name in expected:
            # Reconstruction has passed; metrics use the actual saved signed
            # estimator, preserving exact support near zero.
            indirect = images[name]; vals = dict(direct=images['direct'], indirect=indirect, total=images['direct']+indirect)
            metrics = {}
            for component, image in vals.items():
                ref = reference[component].ravel(); observed = metric(image, ref, signed=name == 'signed' and component != 'direct'); old = n['scores'][name]['components'][component]
                R.K.need(old['pixels'] == 57600 and old['scoring_exclusions'] == 0, '030 all-pixel scoring domain')
                for key, value in observed.items():
                    R.K.need(math.isclose(value, old[key], rel_tol=1e-8, abs_tol=1e-12*scale), '030 independent HDR fsum mismatch')
                metrics[component] = observed; error_maps[name+'_'+component] = (image-ref).reshape(180, 320)
            d, i, total = [metrics[k] for k in ('direct', 'indirect', 'total')]
            passed = total['nrmse'] <= .05 and i['nrmse'] <= .10 and abs(i['signed_sum_bias']) <= .05 and d['nrmse'] <= 1e-4 and d['whole_image_max_absolute'] <= 1e-5 and d['gpu_zero_reference_positive'] == 0
            R.K.need(bool(passed) == n['scores'][name]['pass_'], '030 saved image decision')
            scores[name] = dict(pass_=bool(passed), components=metrics)
        with np.load(native.parent/'full-hdr-errors.npz') as z:
            for name, value in error_maps.items(): np.testing.assert_allclose(value, z[name], rtol=1e-10, atol=1e-12*scale)
        # The signed image is checked against the independent replay above.
        # Report the actual saved estimator's negative support, so permitted
        # SVD roundoff cannot invent or erase a recorded near-zero negative.
        R.K.need(np.array_equal(images['clipped'], np.maximum(images['signed'], 0)), '030 actual clip rule')
        negative = images['signed'] < 0
        R.K.need(int(negative.sum()) == n['clipping']['negative_pixels'], '030 clipping support')
        for key, value in [('minimum', float(images['signed'].min())), ('negative_absolute_energy', float(-images['signed'][negative].sum())), ('clipping_delta_sum', float((images['clipped']-images['signed']).sum()))]:
            R.K.need(math.isclose(value, n['clipping'][key], rel_tol=1e-8, abs_tol=1e-12*scale), '030 clipping contribution')
        passed = ratio >= 1.20 and scores['signed']['pass_'] and scores['clipped']['pass_']
        classification = 'CPU_FEASIBILITY_PASS' if passed else 'REJECTED_NO_GPU'
        R.K.need(n['pass_'] == bool(passed) and n['classification'] == classification, '030 joint decision')
        np.savez(out/'complete-independent-replay.npz', coefficient_error=coefficients-field['coefficients'],
                 corrected_error=corrected-saved['corrected_evaluation'], train_variance=train_var,
                 raw_variance=raw_var, corrected_variance=corrected_var, **error_maps)
        R.B.rehash(info['pins']); R.B.rehash(n['input_sha256'])
        r.update(complete=True, valid=True, all_pass=True, classification=classification, pass_=bool(passed), ratio=ratio,
                 scores=scores, all_groups_independent_augmented_svd=len(keys), all_pixels=57600, scoring_exclusions=0,
                 all56_corrected_fields_replayed=True, independent_fsum_variances_and_metrics=True,
                 new_physical_or_reference_samples=0, new_secondary_intersections=0,
                 reused026_full_secondary_intersection_frames=[0, 1, 63],
                 cpu_peak_rss_kib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)
    except Exception as e:
        r['error'] = type(e).__name__+': '+str(e)
    r['payload_sha256'] = R.B.inventory(out); R.write(out/'result.json', r); return r
