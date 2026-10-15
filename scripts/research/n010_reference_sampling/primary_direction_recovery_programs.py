"""Guarded plan-047 control programs; no acquisition during source assembly."""
import hashlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
RESULTS = ROOT/'research/lanes/n010-comparison-readiness/results'
PLAN = RESULTS.parent/'experiments/047-prospective-directional-control-recovery.md'
FROZEN = {
    'validate_primary_direction.py': '70f02a4f63c2be0b851730c6c7af769248bf51fe60597bc410cb3f40ffacfb87',
    'validate_primary_direction_prefix.py': '2c93ffdb497dd2dd9850d6a105c74b2e73341962f101decfc9122b47ba27ebc9',
    'acquire_primary_direction_feasibility.py': 'e2a7cf3335c863278c0084d148b4a16e0c6d4be8212c1abe04be3244f9a8f588',
}


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def once(source, before, after):
    if source.count(before) != 1:
        raise ValueError('recovery source guard differs: '+before[:90])
    return source.replace(before, after, 1)


def identities(entry, original):
    return {str(p): sha(p) for p in (Path(entry).resolve(), Path(__file__).resolve(), PLAN, original)}


def require_paths(work, output, leaf, filename):
    if (work.resolve() != ROOT/'out/research/n010-comparison-readiness'/leaf
        or output.resolve() != RESULTS/filename):
        raise ValueError('recovery work/output must use the registered fresh paths')


def generated(original_name):
    """Capture the frozen wrapper's generated source without executing it."""
    original = HERE/original_name
    if sha(original) != FROZEN[original_name]:
        raise ValueError('frozen primary-direction wrapper changed')
    source = original.read_text()
    if original_name == 'acquire_primary_direction_feasibility.py':
        return original, source
    # Both frozen wrappers transform source, then invoke exec once. Intercept
    # only that final exec; the generated argparse/native program is not run.
    captured = []
    namespace = {'__name__': '__main__', '__file__': str(original),
                 'exec': lambda code, scope: captured.append(code)}
    exec(compile(source, str(original)+'#capture-only', 'exec'), namespace)
    if len(captured) != 1 or 'source' not in namespace:
        raise ValueError('frozen wrapper assembly shape differs')
    return original, namespace['source']


def physical_program():
    original, source = generated('validate_primary_direction.py')
    source = once(source, '    a = ap.parse_args()',
        "    a = ap.parse_args()\n"
        "    _require_paths(a.work, a.output, 'primary-direction-physical-recovery-v1',\n"
        "                   '163-primary-direction-recovered-physical-controls.json')")
    source = once(source, "    ctypes.CDLL(None).prctl(15, b'n010_guide_phys', 0, 0, 0)",
        "    _require_quiet()\n    ctypes.CDLL(None).prctl(15, b'n010_guide_phys', 0, 0, 0)")
    source = once(source, '    a.work.mkdir(parents=True)',
        '    _retained = _prepare_recovery(inputs)\n'
        '    inputs.update(_program_inputs)\n    a.work.mkdir(parents=True)')
    source = once(source, '    def save():',
        "    result['recovery_provenance'] = _retained['provenance']\n    def save():")
    source = once(source, "            row = {'name': name, 'command': command, 'spp': meta['spp'], 'pass': False}",
        "            imported = _retained['rows'].get(name)\n"
        "            if imported:\n"
        "                command = _copy_import(name, imported, command, a.work)\n"
        "            row = {'name': name, 'command': command, 'spp': meta['spp'], 'pass': False,\n"
        "                'execution_origin': 'retained-152-byte-copy' if imported else 'new-native-invocation',\n"
        "                'payload_directory': str(a.work.resolve())}\n")
    before = '''            try:
                proc = subprocess.run(command, cwd=ROOT, text=True, capture_output=True,
                                      timeout=3600, preexec_fn=limits)
            except subprocess.TimeoutExpired:
                raise ValueError('guided control elapsed guard; partial output retained')
            (a.work/(name+'.stdout')).write_text(proc.stdout)
            (a.work/(name+'.stderr')).write_text(proc.stderr)'''
    source = once(source, before, '''            if imported:
                proc = _import_process(a.work, name, imported)
            else:
                try:
                    proc = subprocess.run(command, cwd=ROOT, text=True, capture_output=True,
                                          timeout=3600, preexec_fn=limits)
                except subprocess.TimeoutExpired:
                    raise ValueError('guided control elapsed guard; partial output retained')
                (a.work/(name+'.stdout')).write_text(proc.stdout)
                (a.work/(name+'.stderr')).write_text(proc.stderr)''')
    source = once(source,
        "            (a.work/(name+'.meta.json')).write_text(json.dumps(fresh, indent=2)+'\\n')",
        "            if not imported:\n"
        "                (a.work/(name+'.meta.json')).write_text(json.dumps(fresh, indent=2)+'\\n')")
    # Every row numerical check, analytic control and iid comparison stays
    # byte-identical; only execution/import and proof identities above differ.
    for start, end in (("            if fresh['seeds']", "        def replay_control"),
                       ('        def replay_control', '    except (ValueError')):
        old = generated('validate_primary_direction.py')[1]
        if old[old.index(start):old.index(end)] != source[source.index(start):source.index(end)]:
            raise ValueError('physical scientific checks changed')
    return original, source


def prefix_program():
    original, source = generated('validate_primary_direction_prefix.py')
    before = '152-primary-direction-physical-controls.json'
    if source.count(before) != 3:
        raise ValueError('physical proof dispatch count differs')
    source = source.replace(before, '163-primary-direction-recovered-physical-controls.json')
    source = once(source, '    a = ap.parse_args()',
        "    a = ap.parse_args()\n"
        "    _require_paths(a.work, a.output, 'primary-direction-prefix-proof-recovery-v1',\n"
        "                   '164-primary-direction-recovered-all-state-and-prefix.json')\n"
        "    if a.wait_for_physical_proof: raise ValueError('recovery does not install a waiting worker')")
    source = once(source, "    ctypes.CDLL(None).prctl(15, b'n010_dir_pfx', 0, 0, 0)",
        "    _require_quiet()\n    ctypes.CDLL(None).prctl(15, b'n010_dir_pfx', 0, 0, 0)")
    source = once(source, '    proofs = {name:',
        '    inputs.update(_program_inputs)\n    proofs = {name:')
    return original, source


def feasibility_program():
    original, source = generated('acquire_primary_direction_feasibility.py')
    for before, after in (
        ('152-primary-direction-physical-controls.json', '163-primary-direction-recovered-physical-controls.json'),
        ('153-primary-direction-all-state-and-prefix.json', '164-primary-direction-recovered-all-state-and-prefix.json')):
        source = once(source, before, after)
    # Internal dictionary keys must follow actual result numbers; this does not
    # alias a partial 152 to PASS or manufacture files at old proof paths.
    source = once(source, "(proofs[k] for k in ('151', '152', '153'))",
        "(proofs[k] for k in ('151', '163', '164'))")
    source = once(source, '    args = ap.parse_args()',
        "    args = ap.parse_args()\n"
        "    _require_paths(args.work, args.output, 'primary-direction-feasibility-recovery-v1',\n"
        "                   '165-primary-direction-recovered-bounded-feasibility.json')")
    source = once(source, "    ctypes.CDLL(None).prctl(15, b'n010_dir_feas', 0, 0, 0)",
        "    _require_quiet()\n    ctypes.CDLL(None).prctl(15, b'n010_dir_feas', 0, 0, 0)")
    source = once(source, "    result = {'schema':",
        "    inputs.update(_program_inputs)\n    result = {'schema':")
    return original, source
