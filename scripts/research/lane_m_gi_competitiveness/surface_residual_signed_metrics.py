"""030 signed-estimate adapter; historical physical HDR scorer stays immutable."""
import numpy as np
import surface_residual_cv as K
import closest_primary_metrics as M


def metric(candidate, reference, *, signed=False):
    a, r = np.asarray(candidate, float), np.asarray(reference, float)
    K.need(a.shape == r.shape and a.size > 0 and np.isfinite(a).all()
           and np.isfinite(r).all(), '030 HDR shape/finiteness/empty')
    a, r = a.ravel(), r.ravel()
    K.need((r >= 0).all() and (signed or (a >= 0).all()), '030 negative physical radiance')
    error = a-r; rms = float(np.sqrt(np.mean(r*r))); total = float(r.sum())
    K.need(np.isfinite([rms, total]).all() and rms > 0 and total > 0,
           '030 undefined physical reference')
    active = r > 0
    result = dict(pixels=len(r), scoring_exclusions=0, rmse=float(np.sqrt(np.mean(error*error))),
                  reference_rms=rms, nrmse=float(np.sqrt(np.mean(error*error)))/rms,
                  signed_sum_bias=float(error.sum())/total, reference_sum=total, gpu_sum=float(a.sum()),
                  active_pixels=int(active.sum()),
                  active_p99_absolute=float(np.quantile(np.abs(error[active]), .99)),
                  active_p99_relative=float(np.quantile(np.abs(error[active])/r[active], .99)),
                  active_max_relative=float((np.abs(error[active])/r[active]).max()),
                  gpu_zero_reference_positive=int(((a <= 0) & active).sum()),
                  reference_zero_leak_pixels=int(((a > 0) & ~active).sum()),
                  reference_zero_leak_energy=float(a[~active].sum()),
                  whole_image_max_absolute=float(np.abs(error).max()))
    K.need(np.isfinite(list(result.values())).all(), '030 nonfinite HDR metric')
    return result


def score(images, direct, reference):
    rows, errors = {}, {}
    K.need(set(images) == {'baseline', 'signed', 'clipped'}, '030 missing image role')
    for name in ('baseline', 'signed', 'clipped'):
        indirect = np.asarray(images[name]).reshape(180, 320)
        d = np.asarray(direct).reshape(180, 320)
        values = dict(direct=d, indirect=indirect, total=d+indirect)
        components = {key: metric(value, reference[key], signed=name == 'signed' and key != 'direct')
                      for key, value in values.items()}
        physical_direct = components['direct']
        direct_ok = (physical_direct['nrmse'] <= 1e-4 and
                     physical_direct['whole_image_max_absolute'] <= 1e-5 and
                     physical_direct['gpu_zero_reference_positive'] == 0)
        rows[name] = dict(components=components,
                          pass_=bool(direct_ok and M.quality(components) == 'PASS'))
        errors.update({name+'_'+key: value-reference[key] for key, value in values.items()})
    return rows, errors
