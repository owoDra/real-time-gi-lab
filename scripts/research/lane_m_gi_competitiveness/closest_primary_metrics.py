"""013 all-pixel primary/direct predicates; no file writes or GPU execution."""
import math
import numpy as np

INVALID = np.uint32(0xffffffff)
GPU_DTYPE = np.dtype([('n', '<f4', (3,)), ('t', '<f4'), ('prim', '<u4'),
                      ('mat', '<u4'), ('inst', '<u4'), ('flag', '<u4')])
ORACLE_DTYPE = np.dtype([('t', '<f8'), ('tri', '<u4'), ('front', '<u4')])


def require(value, message):
    if not value:
        raise ValueError(message)


def quality(components):
    for name in ('direct', 'indirect', 'total'):
        c = components[name]
        require(c['pixels'] == 57600 and c['scoring_exclusions'] == 0,
                'Incomplete/all-pixel scoring boundary')
        for key in ('nrmse', 'signed_sum_bias', 'whole_image_max_absolute'):
            value = c[key]
            require(value is not None and math.isfinite(value), 'Undefined/nonfinite HDR metric')
        require(c['nrmse'] >= 0 and c['whole_image_max_absolute'] >= 0, 'Negative HDR error magnitude')
    t, i = components['total'], components['indirect']
    return 'PASS' if t['nrmse'] <= .05 and i['nrmse'] <= .10 and abs(i['signed_sum_bias']) <= .05 else 'QUALITY_FAIL'


def primary(gpu, oracle, geometry_metadata, vertices, far):
    """Compare every registered pixel; geometry rows follow reference triangle IDs."""
    require(gpu.dtype == GPU_DTYPE and oracle.dtype == ORACLE_DTYPE,
            'Unexpected primary record ABI')
    require(gpu.shape == oracle.shape == (57600,), 'Incomplete primary coverage')
    require(math.isfinite(float(far)) and far >= 1e-4, 'Invalid primary ray far')
    meta = np.asarray(geometry_metadata)
    verts = np.asarray(vertices, dtype=np.float64)
    require(meta.ndim == 2 and meta.shape[1] == 4 and meta.dtype.kind == 'u'
            and verts.shape == (len(meta), 3, 3) and np.isfinite(verts).all(),
            'Invalid complete physical geometry')
    require(len(meta) > 0 and len(np.unique(meta[:, 0])) == len(meta), 'Duplicate/absent primitive identity')
    require(np.isin(gpu['flag'], [0, 1]).all(), 'Primary invalid/overflow flag')
    g_hit, r_hit = gpu['flag'] == 1, oracle['tri'] != INVALID
    require((oracle['tri'][r_hit] < len(meta)).all(), 'Reference primary triangle outside geometry')
    require(np.isfinite(oracle['t'][r_hit]).all() and (oracle['t'][r_hit] >= 0).all(), 'Invalid oracle hit distance')
    require((gpu['prim'][~g_hit] == INVALID).all()
            and (gpu['mat'][~g_hit] == INVALID).all() and (gpu['inst'][~g_hit] == INVALID).all()
            and np.isposinf(gpu['t'][~g_hit]).all() and (gpu['n'][~g_hit] == 0).all(),
            'Primary miss clear convention differs')
    require(np.isfinite(gpu['t'][g_hit]).all() and np.isfinite(gpu['n'][g_hit]).all(),
            'Nonfinite primary hit')
    require(((gpu['t'][g_hit] >= 1e-4) & (gpu['t'][g_hit] <= far)).all(), 'Primary hit outside ray bounds')
    order = np.argsort(meta[:, 0])
    where = np.searchsorted(meta[order, 0], gpu['prim'][g_hit])
    require((where < len(meta)).all(), 'GPU primary primitive outside geometry')
    rows = order[where]
    require((meta[rows, 0] == gpu['prim'][g_hit]).all()
            and (meta[rows, 1] == gpu['mat'][g_hit]).all()
            and (meta[rows, 2] == gpu['inst'][g_hit]).all(), 'GPU primary metadata inconsistent with geometry')
    norm = np.linalg.norm(gpu['n'].astype(np.float64), axis=1)
    require((np.abs(norm[g_hit] - 1) <= 1e-4).all(), 'Primary normal outside registered unit tolerance')
    expected_primitive = np.full(57600, INVALID, dtype=np.uint32)
    expected_primitive[r_hit] = meta[oracle['tri'][r_hit], 0]
    both = g_hit & r_hit
    depth_error = np.zeros(57600, dtype=np.float64)
    depth_bound = np.zeros(57600, dtype=np.float64)
    depth_error[both] = gpu['t'][both].astype(np.float64) - oracle['t'][both]
    depth_bound[r_hit] = np.maximum(1e-4, 1e-5 * np.abs(oracle['t'][r_hit]))
    depth_ok = np.ones(57600, dtype=bool)
    depth_ok[both] = np.abs(depth_error[both]) <= depth_bound[both]
    expected_normal = np.zeros((57600, 3), dtype=np.float64)
    tri = verts[oracle['tri'][r_hit]]
    normal = np.cross(tri[:, 1] - tri[:, 0], tri[:, 2] - tri[:, 0])
    length = np.linalg.norm(normal, axis=1)
    require((length > 0).all(), 'Oracle selected degenerate triangle')
    expected_normal[r_hit] = normal / length[:, None]
    normal_error = np.zeros(57600, dtype=np.float64)
    normal_error[both] = np.linalg.norm(gpu['n'][both].astype(np.float64) - expected_normal[both], axis=1)
    presence_mismatch = g_hit != r_hit
    primitive_mismatch = gpu['prim'] != expected_primitive
    report = dict(pixels=57600, scoring_exclusions=0,
                  gpu_hit_pixels=int(g_hit.sum()), reference_hit_pixels=int(r_hit.sum()),
                  hit_presence_mismatches=int(presence_mismatch.sum()),
                  primitive_mismatches=int(primitive_mismatch.sum()),
                  depth_bound_failures=int((both & ~depth_ok).sum()),
                  maximum_absolute_depth_error=float(np.abs(depth_error).max()),
                  maximum_normal_vector_error=float(normal_error.max()),
                  normal_vector_mismatch_pixels=int((both & (normal_error != 0)).sum()),
                  pass_=bool(not presence_mismatch.any() and depth_ok.all()))
    arrays = dict(gpu_hit=g_hit, reference_hit=r_hit, gpu_primitive=gpu['prim'].copy(),
                  reference_primitive=expected_primitive, depth_error=depth_error,
                  depth_bound=depth_bound, depth_within_bound=depth_ok,
                  normal_vector_error=normal_error)
    return report, arrays


def classify(primary_report, components, named_pixels):
    """Only valid all-pixel evidence reaches a scientific correctness decision."""
    require(primary_report['pixels'] == 57600 and primary_report['scoring_exclusions'] == 0
            and type(primary_report['pass_']) is bool, 'Invalid primary decision boundary')
    quality_decision = quality(components)
    direct = components['direct']
    require(isinstance(direct['gpu_zero_reference_positive'], int)
            and 0 <= direct['gpu_zero_reference_positive'] <= 57600,
            'Invalid direct support diagnostic')
    direct_pass = (direct['nrmse'] <= 1e-4 and direct['whole_image_max_absolute'] <= 1e-5
                   and direct['gpu_zero_reference_positive'] == 0)
    named_pass = True
    for row in named_pixels:
        require(row['reference_direct'] > 0 and math.isfinite(row['reference_direct'])
                and row['gpu_direct'] >= 0 and math.isfinite(row['gpu_direct']),
                'Invalid named-pixel physical radiance')
        named_pass &= (row['gpu_primitive'] == row['reference_primitive']
                       and row['gpu_direct'] > 0
                       and abs(row['gpu_direct'] - row['reference_direct']) / row['reference_direct'] < 1)
    return dict(classification='PASS' if primary_report['pass_'] and direct_pass and named_pass else 'CORRECTNESS_FAIL',
                correctness_evidence_valid=True, primary_pass=bool(primary_report['pass_']),
                direct_pass=bool(direct_pass), named_pixels_pass=bool(named_pass),
                quality_classification=quality_decision, accepted_timing=False)
