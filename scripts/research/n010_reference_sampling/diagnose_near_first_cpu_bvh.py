#!/usr/bin/env python3
"""Plan090: isolated traversal ordering, every-query original pairing, fixed cost."""
import hashlib
import json
import os
from pathlib import Path
import resource
import subprocess
import time

import diagnose_selected_bounce_paths as D
from run_primary_direction_sequence import require_no_other_research_worker

WORK = D.OUT / 'near-first-cpu-bvh-v1'
OUTPUT = D.RESULTS / '238-near-first-cpu-bvh-prototype.json'
PLAN = D.RESULTS.parent / 'experiments/090-near-first-exact-cpu-bvh-prototype.md'
PIXELS = ((40, 30), (120, 30), (200, 30), (280, 30),
          (40, 150), (120, 150), (200, 150), (280, 150))


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def optimize(header):
    start = header.index('class Bvh {')
    end = header.index('// ---------------------------------------------------------------- integrator', start)
    original = header[start:end]
    legacy = D.once(original, 'class Bvh {', 'class LegacyBvh {')
    legacy = D.once(legacy, 'explicit Bvh(', 'explicit LegacyBvh(')
    slab_start = original.index('    static bool slab(')
    traverse_start = original.index('    template <class Visit>\n    void traverse(')
    traverse_end = original.index('    const std::vector<Triangle>& tris_;', traverse_start)
    slab = original[slab_start:traverse_start]
    slab_entry = D.once(slab, 'static bool slab(', 'static bool slab_entry(')
    slab_entry = D.once(slab_entry, 'double tmin, double tmax) {',
                        'double tmin, double tmax, double& entry) {')
    slab_entry = D.once(slab_entry, '        return true;', '        entry = t0; return true;')
    traversal = D.checked(D.HERE / 'near_first_cpu_bvh_traverse.inc').decode()
    edits = [
        (original[traverse_start:traverse_end], slab_entry + traversal + '\n'),
        (': tris_(tris) {', ': tris_(tris)\n#ifdef N010_VERIFY_BVH\n        , legacy_(tris)\n#endif\n    {'),
        ('        return best;', '''#ifdef N010_VERIFY_BVH
        const auto expected = legacy_.closest(ray, tmin, tmax, ignore);
        ++paired_closest_count;
        if (best.tri != expected.tri || std::memcmp(&best.t, &expected.t, sizeof(double)))
            throw std::runtime_error("near-first/original closest identity differs");
#endif
        return best;'''),
        ('        return blocked;', '''#ifdef N010_VERIFY_BVH
        const bool expected = legacy_.occluded(ray, tmax, ignore_a, ignore_b);
        ++paired_occluded_count;
        if (blocked != expected) throw std::runtime_error("near-first/original occlusion differs");
#endif
        return blocked;'''),
        ('private:\n    struct Node {',
         'public:\n    mutable uint64_t paired_closest_count{}, paired_occluded_count{};\nprivate:\n    struct Node {'),
        ('    std::vector<Node> nodes_;',
         '    std::vector<Node> nodes_;\n#ifdef N010_VERIFY_BVH\n    LegacyBvh legacy_;\n#endif'),
    ]
    revised = original
    for old, new in edits:
        revised = D.once(revised, old, new)
    inverse = revised
    for old, new in reversed(edits):
        inverse = D.once(inverse, new, old)
    if inverse != original:
        raise ValueError('class edit inverse differs')
    combined = legacy + revised
    changed = D.once(header, original, combined)
    if D.once(changed, combined, original) != header:
        raise ValueError('whole header inverse differs')
    return changed, dict(class_edit_inverse_exact=True, whole_header_inverse_exact=True,
                        original_bvh_sha256=hashlib.sha256(original.encode()).hexdigest(),
                        optimized_bvh_sha256=hashlib.sha256(revised.encode()).hexdigest(),
                        slab_entry_arithmetic_copy=True,
                        changes=[dict(old=a, new=b) for a, b in edits])


def main():
    if WORK.exists() or OUTPUT.exists():
        raise ValueError('refuse existing near-first prototype')
    require_no_other_research_worker()
    os.sched_setaffinity(0, {max(os.sched_getaffinity(0))})
    os.nice(15)
    resource.setrlimit(resource.RLIMIT_AS, (4 * 1024**3,) * 2)
    for p in (Path(__file__).resolve(), PLAN, Path(D.__file__),
              D.HERE / 'run_primary_direction_sequence.py'):
        D.checked(p)
    build = json.loads(D.checked(D.RESULTS / '224-all-split-exporter-build.json'))
    prototype = json.loads(D.checked(D.RESULTS / '223-all-split-general-transport-equivalence.json'))
    cost = json.loads(D.checked(D.RESULTS / '236-all-split-remaining-controls-cpu-cost.json'))
    if (not build['complete'] or not build['all_pass'] or not prototype['complete']
            or not cost['complete'] or len(cost['rows']) != 6
            or not all(r['pass_cost_integrity'] for r in cost['rows'])):
        raise ValueError('actual retained exporter/prototype/six cost prerequisites required')
    for proof in (build, prototype, cost):
        for p, digest in proof['payload_sha256'].items():
            D.checked(Path(p), digest)
    base = D.OUT / 'all-split-exporter-v1'
    header, inverses = optimize(D.checked(base / 'n010_rqmc_oracle.hpp').decode())
    old_header = D.checked(D.ROOT / 'src/research/n008_hdr_oracle/n008_oracle.hpp').decode()
    first = old_header.index('class Bvh {')
    last = old_header.index('// ---------------------------------------------------------------- integrator', first)
    if hashlib.sha256(old_header[first:last].encode()).hexdigest() != inverses['original_bvh_sha256']:
        raise ValueError('retained BVH differs from original physical source')
    old_main = next(Path(p) for p in prototype['payload_sha256'] if p.endswith('/main.cpp'))
    old_data = next(Path(p) for p in prototype['payload_sha256'] if p.endswith('/data.json'))
    main_source = D.checked(old_main).decode()
    tail = '    out<<"]\\n";return out?0:5;'
    new_tail = '''    out<<"]\\n";
    std::cout<<"{\\"paired_closest\\":"<<oracle.bvh().paired_closest_count
             <<",\\"paired_occluded\\":"<<oracle.bvh().paired_occluded_count<<"}\\n";
    return out?0:5;'''
    paired_main = D.once(main_source, tail, new_tail)
    if D.once(paired_main, new_tail, tail) != main_source:
        raise ValueError('paired main output-only inverse differs')
    net = D.OUT / 'sobol16x262144.bin'
    scene = D.OUT / 'references-recovery-sponza-v1/C1_T_B8/scene.n008'
    D.checked(net); D.checked(scene)
    WORK.mkdir()
    (WORK / 'n010_rqmc_oracle.hpp').write_text(header)
    (WORK / 'paired.cpp').write_text(paired_main)
    (WORK / 'exporter.cpp').write_bytes(D.checked(base / 'main.cpp'))
    pixels = WORK / 'pixels.txt'
    pixels.write_text(''.join(f'{x} {y}\n' for x, y in PIXELS))
    result = dict(schema='n010-near-first-cpu-bvh-prototype/1', complete=False, all_pass=False,
                  gpu_run=False, reference_admission=False,
                  classification='ISOLATED_EXECUTION_PROTOTYPE_ACQUIRING',
                  input_sha256=D.INPUTS, inverses=inverses, attempts=[],
                  source_commit=subprocess.check_output(['git', 'rev-parse', 'HEAD'], text=True).strip(),
                  tests='NOT_RUN; isolated exact-query scientific execution prototype',
                  scope='Fixed original C1 queries and A6a8 cost only; no all-rays/full-physical/reference proof')

    def hashes():
        return {str(p): sha(p) for p in sorted(WORK.rglob('*')) if p.is_file()}

    def save():
        OUTPUT.write_text(json.dumps(result, indent=2, allow_nan=False) + '\n')

    save()

    def run(command):
        require_no_other_research_worker()
        index = len(result['attempts'])
        receipt = WORK / f'step-{index}.resources.json'
        attempt = dict(command=command, cpu_limit_seconds=220, elapsed_limit_seconds=300)
        result['attempts'].append(attempt)
        save()

        def limits():
            resource.setrlimit(resource.RLIMIT_CPU, (220,) * 2)
            receipt.write_text(json.dumps(dict(pid=os.getpid(),
                start_ticks=int(Path('/proc/self/stat').read_text().rsplit(')', 1)[1].split()[19]),
                cpu=list(resource.getrlimit(resource.RLIMIT_CPU)),
                address_space=list(resource.getrlimit(resource.RLIMIT_AS)),
                affinity=sorted(os.sched_getaffinity(0)), nice=os.getpriority(os.PRIO_PROCESS, 0),
                command=command)) + '\n')

        before = resource.getrusage(resource.RUSAGE_CHILDREN)
        start = time.monotonic()
        try:
            proc = subprocess.run(command, capture_output=True, text=True, timeout=300, preexec_fn=limits)
        except subprocess.TimeoutExpired as error:
            (WORK / f'step-{index}.stdout').write_bytes(error.stdout or b'')
            (WORK / f'step-{index}.stderr').write_bytes(error.stderr or b'')
            after = resource.getrusage(resource.RUSAGE_CHILDREN)
            attempt.update(classification='TIMEOUT_PARTIALS_RETAINED', elapsed=time.monotonic() - start,
                           child_cpu_seconds=(after.ru_utime + after.ru_stime) - (before.ru_utime + before.ru_stime),
                           returncode='NOT_EXPOSED_BY_TIMEOUTEXPIRED')
            result['payload_sha256'] = hashes(); save()
            raise ValueError('elapsed guard; no retry') from error
        after = resource.getrusage(resource.RUSAGE_CHILDREN)
        (WORK / f'step-{index}.stdout').write_text(proc.stdout)
        (WORK / f'step-{index}.stderr').write_text(proc.stderr)
        attempt.update(returncode=proc.returncode, elapsed=time.monotonic() - start,
                       child_cpu_seconds=(after.ru_utime + after.ru_stime) - (before.ru_utime + before.ru_stime))
        result['payload_sha256'] = hashes(); save()
        actual = json.loads(D.checked(receipt))
        if (actual['cpu'] != [220] * 2 or actual['address_space'] != [4 * 1024**3] * 2
                or len(actual['affinity']) != 1 or actual['nice'] != 15):
            raise ValueError('actual native resources differ')
        if proc.returncode:
            raise ValueError('compile/native failure; no retry')
        return proc, attempt

    try:
        flags = ['c++', '-std=c++20', '-O3', '-fno-fast-math', '-ffp-contract=off', '-pthread',
                 '-I', str(D.ROOT / 'src/research/n008_hdr_oracle')]
        paired = WORK / 'n010_near_first_paired'
        exporter = WORK / 'n010_near_first_exporter'
        run(flags + ['-DN010_VERIFY_BVH=1', str(WORK / 'paired.cpp'), '-o', str(paired)])
        proc, pair_time = run([str(paired), str(net), str(scene), str(pixels), str(WORK / 'paired-data.json')])
        counts = json.loads(proc.stdout)
        if counts['paired_closest'] <= 0 or counts['paired_occluded'] <= 0:
            raise ValueError('original-query pairing did not execute')
        if (WORK / 'paired-data.json').read_bytes() != old_data.read_bytes():
            raise ValueError('entire retained223 data bytes differ')
        result.update(every_executed_query_identity_pass=True, paired_query_counts=counts,
                      original223_entire_payload_bytes_equal=True)
        save()
        run(flags + [str(WORK / 'exporter.cpp'), '-o', str(exporter)])
        a6a = next(r for r in cost['rows'] if r['name'] == 'A6a')
        old_command = a6a['command']
        command = list(old_command)
        command[0] = str(exporter)
        out_index = command.index('--out') + 1
        original_prefix = Path(command[out_index])
        directory = WORK / 'a6a-cost'
        directory.mkdir()
        command[out_index] = str(directory / 'A6a')
        proc, measurement = run(command)
        payloads = [Path(p) for p in cost['payload_sha256'] if Path(p).parent == original_prefix.parent
                    and Path(p).suffix in ('.f64', '.pfm', '.hits')]
        if len(payloads) != 21 or any(p.read_bytes() != (directory / p.name).read_bytes() for p in payloads):
            raise ValueError('original236 A6a full payload bytes differ')
        fresh = json.loads(proc.stdout)
        if len(fresh['runs']) != 4:
            raise ValueError('optimized exporter run count differs')
        for key in ('scene_sha256', 'geometry_sha256', 'width', 'height', 'spp', 'seeds'):
            if fresh[key] != a6a['native_metadata'][key]:
                raise ValueError('optimized exporter identity differs')
        for new, old in zip(fresh['runs'], a6a['native_metadata']['runs']):
            for key in ('seed', 'primary_hits', 'shadow_tests', 'shadow_blocked', 'backface_absorbed', 'all_split'):
                if new[key] != old[key]:
                    raise ValueError('optimized exporter integer/proposal audits differ')
        for p, digest in list(D.INPUTS.items()):
            D.checked(Path(p), digest)
        ratio = measurement['child_cpu_seconds'] / a6a['child_cpu_seconds']
        result.update(complete=True, all_pass=ratio <= .75, classification='EXECUTION_PROTOTYPE_COMPLETE_NO_ADMISSION',
                      semantic_equivalence_checks_pass=True,
                      original236_a6a_all21_payloads_bytes_equal=True, original236_metadata_audits_equal=True,
                      original_a6a_cpu_seconds=a6a['child_cpu_seconds'],
                      optimized_a6a_cpu_seconds=measurement['child_cpu_seconds'],
                      optimized_over_retained_a6a_cpu_ratio=ratio, execution_promising=ratio <= .75,
                      cost_scope='Uncontrolled retained single-run sizing comparison, not a GI speedup claim',
                      full_physical_state_prefix_reference_proof='NOT_RUN_NOT_QUEUED')
    except (ValueError, OSError, KeyError, AssertionError, subprocess.SubprocessError) as error:
        result.update(classification='EXECUTION_PROTOTYPE_FAILURE_PARTIALS_RETAINED', failure=str(error))
    result['payload_sha256'] = hashes()
    save()
    print(json.dumps({k: result.get(k) for k in ('complete', 'all_pass', 'classification', 'failure',
                                              'paired_query_counts', 'execution_promising',
                                              'optimized_a6a_cpu_seconds', 'optimized_over_retained_a6a_cpu_ratio')}, indent=2))
    raise SystemExit(0 if result['all_pass'] else 2)


if __name__ == '__main__':
    main()
