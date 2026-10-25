"""031 full-data fsum audit; no path rerendering or reference generation."""
import math
from pathlib import Path
import resource
import numpy as np
import anchor_path_difference as R
import surface_residual_audit as G
from surface_residual_corrected_audit import metric, sums_and_variance


def independent_groups(info, folder):
    primary = np.fromfile(folder/'primary.bin', R.PRIMARY)
    original = info['primary_path'].read_bytes()
    R.K.need(original[:8] == b'N008HIT\0' and original[16:] == (folder/'primary.bin').read_bytes(), '031 complete original CPU primary identity')
    vertices = np.fromfile(folder/'vertices.f64', '<f8').reshape(-1, 3, 3)
    R.K.need(np.array_equal(vertices, info['vertices']), '031 complete owner/triangle vertex ordering')
    active = primary['tri'] != 0xffffffff; index = np.where(active, primary['tri'], 0)
    origins = np.fromfile(folder/'origins.f64', '<f8').reshape(57600, 3)
    normal = np.fromfile(folder/'normals.f64', '<f8').reshape(57600, 3)
    R.K.need(np.isfinite(origins).all() and np.isfinite(normal).all(), '031 complete finite primary geometry')
    triangles = vertices[index]; expected_n = np.cross(triangles[:, 1]-triangles[:, 0], triangles[:, 2]-triangles[:, 0])
    expected_n /= np.linalg.norm(expected_n, axis=1)[:, None]; expected_n[primary['front'] == 0] *= -1
    np.testing.assert_allclose(normal[active], expected_n[active], rtol=1e-12, atol=1e-12)
    hits = np.empty(57600, dtype=[('n', '<f8', (3,)), ('flag', '<u4'), ('inst', '<u4'), ('mat', '<u4')])
    hits['n'] = normal; hits['flag'] = active; hits['inst'] = info['metadata'][index, 2]; hits['mat'] = info['metadata'][index, 1]
    keys, groups, normalized, _, actual = G.independent_geometry(dict(hits=hits, origins=np.c_[origins, np.zeros(57600)], vertices=vertices, metadata=info['metadata']))
    anchors = []
    for group in range(len(keys)):
        members = [p for p in range(57600) if groups[p] == group]; anchors.append(members[len(members)//2])
    with np.load(folder/'field.npz') as z:
        R.K.need(np.array_equal(keys, z['keys']) and np.array_equal(groups, z['groups']) and np.array_equal(actual, z['active'])
                 and np.array_equal(np.array(anchors), z['anchors']), '031 independent complete partition/median anchors')
        np.testing.assert_allclose(normalized, z['normal'], rtol=0, atol=1e-14)
    R.K.need(np.array_equal(groups, np.fromfile(folder/'groups.i64', '<i8')) and
             np.array_equal(anchors, np.fromfile(folder/'anchors.u32', '<u4')), '031 native group/anchor input bytes')
    return groups, np.array(anchors), active


def audit(cell, depth, out):
    R.limits(); head = R.committed(); native = R.BASE/(R.tag(cell, depth)+'-v1/result.json'); n = R.B.read(native)
    R.K.need(n['complete'] and n['valid'] and n['source_commit'] == head, '031 valid unchanged-source native required')
    R.B.rehash(n['input_sha256']); R.B.rehash({str(native.parent/k): h for k, h in n['payload_sha256'].items()})
    R.K.need(R.B.inventory(native.parent) == n['payload_sha256'], '031 exact native complete inventory')
    out = R.reserve(out, R.BASE/(R.tag(cell, depth)+'-audit-v1'))
    pins = dict(n['input_sha256']); pins[str(native)] = R.B.SHA(native)
    r = dict(schema='m001-anchor031-independent-cpu-audit/1', cell=cell, depth=depth, source_commit=head,
             native_receipt=str(native), native_receipt_sha256=R.B.SHA(native), complete=False, valid=False, all_pass=False,
             classification='INVALID_STOP_NO_RETRY', gpu_executed=False, accepted_timing=False, input_sha256=pins)
    try:
        info = R.intake(cell, depth, out, pins); folder = native.parent
        groups, anchors, active = independent_groups(info, folder/'geometry')
        with np.load(folder/'images.npz') as z: images = {k: z[k] for k in z.files}
        reconstructed = {k: [] for k in ('baseline', 'signed')}; independent_counts = []
        scale = 1e-20; errors = {}; query_baseline = 57600; query_candidate = 57600
        native_paths = R.B.read(folder/'paths/paths.json')
        point_count = sum(line.startswith('point ') for line in info['scene'].read_text().splitlines())
        R.K.need(point_count > 0, '031 point-light boundary')
        for replicate in range(4):
            d = R.raw_seed(folder/'paths', replicate, groups)
            scale = max(scale, *(float(np.abs(d[k]).max()) for k in ('absolute', 'local', 'paired', 'extra', 'direct')))
            for key in ('local', 'paired', 'extra', 'direct', 'queries'): R.K.need((d[key][~active] == 0).all(), '031 complete sky sample support')
            R.K.need(np.array_equal(d['local'][anchors], d['paired'][anchors]), '031 actual identical receiver cancellation')
            R.K.need(np.array_equal(d['queries'][anchors, :2], d['queries'][anchors, 2:4]), '031 actual identical receiver full query charge')
            for offset in (0, 2, 4):
                closest, shadow = d['queries'][active, offset], d['queries'][active, offset+1]
                R.K.need(((closest >= 32) & (closest <= 16*depth) & (shadow <= closest*point_count)).all(), '031 local/pair/control query bounds')
            R.K.need(((d['bank_queries'][:, 0] >= 2048) & (d['bank_queries'][:, 0] <= 1024*depth)
                     & (d['bank_queries'][:, 1] <= d['bank_queries'][:, 0]*point_count)).all(), '031 complete bank query bounds')
            bank = np.array([math.fsum(map(float, row))/1024 for row in d['absolute']])
            candidate = np.zeros(57600); baseline = np.zeros(57600)
            for pixel in np.flatnonzero(active):
                candidate[pixel] = bank[groups[pixel]]+math.fsum(float(x)-float(y) for x, y in zip(d['local'][pixel], d['paired'][pixel]))/16
                baseline[pixel] = math.fsum([*map(float, d['local'][pixel]), *map(float, d['extra'][pixel])])/32
            reconstructed['signed'].append(candidate); reconstructed['baseline'].append(baseline)
            for name, expected in [('signed', candidate), ('baseline', baseline), ('clipped', np.maximum(candidate, 0))]:
                np.testing.assert_allclose(expected, images[name][replicate], rtol=1e-10, atol=1e-12*scale)
            R.K.need(np.array_equal(d['direct'], images['direct'][replicate]), '031 actual direct path value preserved')
            R.K.need(np.array_equal(images['clipped'][replicate], np.maximum(images['signed'][replicate], 0)), '031 actual signed/display clip')
            q = {key: sum(map(int, d['queries'][:, column])) for column, key in enumerate(('local_closest', 'local_shadow', 'paired_closest', 'paired_shadow', 'extra_closest', 'extra_shadow'))}
            q.update({key: sum(map(int, d['bank_queries'][:, column])) for column, key in enumerate(('bank_closest', 'bank_shadow'))})
            R.K.need(native_paths['rows'][replicate] == dict(seed=R.SEEDS[replicate], **q), '031 complete independent integer query sums')
            independent_counts.append(q)
            query_baseline += q['local_closest']+q['local_shadow']+q['extra_closest']+q['extra_shadow']
            query_candidate += q['local_closest']+q['local_shadow']+q['paired_closest']+q['paired_shadow']+q['bank_closest']+q['bank_shadow']
        reconstructed = {k: np.stack(v) for k, v in reconstructed.items()}
        _, vb = sums_and_variance(reconstructed['baseline']); _, vc = sums_and_variance(reconstructed['signed'])
        total_b, total_c = math.fsum(map(float, vb)), math.fsum(map(float, vc))
        ratio = total_b*query_baseline/(total_c*query_candidate)
        for key, value in [('baseline_variance', total_b), ('candidate_variance', total_c), ('ratio', ratio)]:
            R.K.need(math.isclose(value, n['efficiency'][key], rel_tol=1e-8, abs_tol=1e-12*scale), '031 independent fsum variance/efficiency')
        R.K.need(query_baseline == n['efficiency']['baseline_complete_queries'] and query_candidate == n['efficiency']['candidate_complete_queries'], '031 full cold-bank/primary queries')
        with np.load(folder/'variances.npz') as z:
            np.testing.assert_allclose(vb, z['baseline'], rtol=1e-8, atol=1e-12*scale)
            np.testing.assert_allclose(vc, z['signed'], rtol=1e-8, atol=1e-12*scale)
        reference = R.reference(info, out); decisions = []
        with np.load(folder/'full-hdr-errors.npz') as original_errors:
            for replicate in range(4):
                roles = {}
                for name in ('baseline', 'signed', 'clipped'):
                    values = dict(direct=images['direct'][replicate], indirect=images[name][replicate],
                                  total=images['direct'][replicate]+images[name][replicate]); components = {}
                    for component, actual in values.items():
                        ref = reference[component].ravel(); observed = metric(actual, ref, signed=name == 'signed' and component != 'direct')
                        saved = n['scores'][replicate]['roles'][name]['components'][component]
                        for key, value in observed.items(): R.K.need(math.isclose(value, saved[key], rel_tol=1e-8, abs_tol=1e-12*scale), '031 independent HDR fsum')
                        components[component] = observed; key = f'seed{replicate}_{name}_{component}'
                        error = (actual-ref).reshape(180, 320); np.testing.assert_array_equal(error, original_errors[key]); errors[key] = error
                    direct, indirect, total = (components[k] for k in ('direct', 'indirect', 'total'))
                    passed = total['nrmse'] <= .05 and indirect['nrmse'] <= .10 and abs(indirect['signed_sum_bias']) <= .05 and direct['nrmse'] <= 1e-4 and direct['whole_image_max_absolute'] <= 1e-5 and direct['gpu_zero_reference_positive'] == 0
                    R.K.need(bool(passed) == n['scores'][replicate]['roles'][name]['pass_'], '031 per-seed original image gate')
                    roles[name] = dict(pass_=bool(passed), components=components)
                decisions.append(dict(seed=R.SEEDS[replicate], roles=roles))
        passed = ratio >= 1.20 and all(x['roles'][k]['pass_'] for x in decisions for k in ('signed', 'clipped'))
        classification = 'CPU_FEASIBILITY_PASS' if passed else 'REJECTED_NO_GPU'
        R.K.need(n['pass_'] == bool(passed) and n['classification'] == classification, '031 complete final decision')
        np.savez(out/'complete-independent-audit.npz', candidate_mean_error=reconstructed['signed']-images['signed'], baseline_mean_error=reconstructed['baseline']-images['baseline'], baseline_variance=vb, candidate_variance=vc, **errors)
        R.B.rehash(pins)
        r.update(complete=True, valid=True, all_pass=True, classification=classification, pass_=bool(passed), ratio=ratio,
                 scores=decisions, all_pixels=57600, scoring_exclusions=0, all_groups_independent=len(anchors), all_samples_accounted=True,
                 independent_fsum_means_variances_hdr=True, physical_paths_independently_rerendered=False,
                 original_counted_physical_contracts_and_inverse_source_reused=True, baseline_complete_queries=query_baseline,
                 candidate_complete_queries=query_candidate, cpu_peak_rss_kib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)
    except Exception as e: r['error'] = type(e).__name__+': '+str(e)
    r['payload_sha256'] = R.B.inventory(out); R.write(out/'result.json', r); return r
