"""Plan 056: declared dispatch/provenance overlays on frozen scientific drivers."""
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
PLAN = ROOT/'research/lanes/n010-comparison-readiness/experiments/056-prospective-nested-scramble-reference-sampling.md'

PARENTS = {
    'physical':('validate_primary_direction.py','70f02a4f63c2be0b851730c6c7af769248bf51fe60597bc410cb3f40ffacfb87'),
    'prefix':('validate_primary_direction_prefix.py','2c93ffdb497dd2dd9850d6a105c74b2e73341962f101decfc9122b47ba27ebc9'),
    'feasibility':('acquire_primary_direction_feasibility.py','e2a7cf3335c863278c0084d148b4a16e0c6d4be8212c1abe04be3244f9a8f588')}


def digest(path): return hashlib.sha256(path.read_bytes()).hexdigest()


def execution_gate():
    from run_primary_direction_sequence import require_no_other_research_worker
    require_no_other_research_worker()
    results = ROOT/'research/lanes/n010-comparison-readiness/results'
    p = results/'180-primary-direction-second-stop-bounded-feasibility.json'
    feasibility = json.loads(p.read_bytes())
    if not feasibility.get('complete'):
        raise ValueError('180 must actually terminate before plan-056 scientific acquisition')
    checked = {str(p):digest(p)}
    for name in ('185-deferred-image-calibration-sizing.json',
                 '186-deferred-image-calibration-full-renderer.json'):
        p = results/name
        record = json.loads(p.read_bytes())
        terminal = bool(record.get('complete') or (record.get('failure') and
            record.get('classification')=='OPERATIONAL_FAILURE_PARTIALS_RETAINED_NOT_ACCEPTED'))
        if not terminal: raise ValueError('prior GPU acquisition must be terminal: '+name)
        checked[str(p)] = digest(p)
        if not record.get('all_pass'): break
    require_no_other_research_worker()
    return {'terminal_input_sha256':checked,'other_research_workers_absent':True,
        'boot_id':Path('/proc/sys/kernel/random/boot_id').read_text().strip(),
        'scope':'Terminal/exclusion gate only; no acceptance of negative GPU calibration or reference evidence'}


def program(kind,entry):
    name,expected = PARENTS[kind]
    parent = HERE/name
    if digest(parent)!=expected: raise ValueError('frozen scientific parent changed')
    original = parent.read_text(); source = original; edits = []
    pairs = [
        ('151-primary-direction-proposal-build.json','187-nested-scramble-oracle-build.json'),
        ('152-primary-direction-physical-controls.json','188-nested-scramble-physical-controls.json'),
        ('153-primary-direction-all-state-and-prefix.json','189-nested-scramble-all-state-and-prefix.json'),
        ('primary-direction-build-v1','owen-reference-build-v1'),
        ('n010_primary_direction_oracle','n010_owen_oracle'),
        ('n010_primary_direction_prefix','n010_owen_prefix'),
        ('n010-primary-direction-physical-controls/1','n010-nested-scramble-physical-controls/1'),
        ('n010-primary-direction-all-state-and-prefix/1','n010-nested-scramble-all-state-and-prefix/1'),
        ('n010-primary-direction-bounded-feasibility/1','n010-nested-scramble-bounded-feasibility/1'),
        ('043-prospective-primary-direction-reference-sampling.md',PLAN.name),
        ("('151', '152', '153')","('187', '188', '189')"),
        ("b'n010_dir_feas'","b'n010_owen_feas'"),
        ("b'n010_dir_pfx'","b'n010_owen_pfx'"),
        ('PRIMARY-DIRECTION STATE/PREFIX','NESTED-SCRAMBLE STATE/PREFIX')]
    for old,new in pairs:
        count = source.count(old)
        if count:
            if new in source: raise ValueError('unexpected existing dispatch value')
            source = source.replace(old,new); edits.append((old,new,count))
    restored = source
    for old,new,count in reversed(edits):
        if restored.count(new)!=count: raise ValueError('dispatch inverse count differs')
        restored = restored.replace(new,old)
    if restored!=original: raise ValueError('whole scientific dispatch inverse differs')
    proof = {'whole_parent_inverse_exact':True,'parent_path':str(parent),
        'parent_sha256':expected,'restored_parent_sha256':hashlib.sha256(restored.encode()).hexdigest(),
        'declared_dispatch_source_sha256':hashlib.sha256(source.encode()).hexdigest(),
        'scope':'Only result/work/binary/plan/schema/process identities and provenance; original statistical/physical/prefix rules retained',
        'dispatch_edits':[{'old':old,'new':new,'count':count} for old,new,count in edits]}
    extra = {str(p.resolve()):digest(p) for p in (entry,Path(__file__),parent,PLAN,
        HERE/'run_primary_direction_sequence.py')}
    anchor = '    result = {'
    addition = ('    inputs.update('+repr(extra)+')\n'
        "    inputs.update(_owen_execution_proof['terminal_input_sha256'])\n"
        "    result = {'execution_exclusion_proof':_owen_execution_proof,"
        "'nested_scramble_dispatch_proof':"+repr(proof)+',')
    work_guard = '    if '+('args' if kind=='feasibility' else 'a')+'.work.exists()'
    gate = ('    from nested_scramble_programs import execution_gate\n'
        '    _owen_execution_proof = execution_gate()\n')
    if kind=='prefix':
        gate += ("    if a.wait_for_physical_proof:\n"
            "        raise ValueError('plan 056 refuses waiting queues; invoke only after actual physical termination')\n")
    if kind=='feasibility':
        if source.count(anchor)!=1 or source.count(work_guard)!=1:
            raise ValueError('feasibility provenance/exclusion anchor differs')
        executable = source.replace(anchor,addition).replace(work_guard,gate+work_guard)
        if executable.replace(addition,anchor).replace(gate,'')!=source:
            raise ValueError('provenance/exclusion inverse differs')
    else:
        # Parent wrappers assemble the original point-guided control programs.
        # Add evidence identities to that inner program, before its result exists.
        needle = '    exec(compile(source,'
        if source.count(needle)!=1:raise ValueError('control assembly anchor differs')
        hook = ('    source = once(source, '+repr(anchor)+', '+repr(addition)+')\n'
            '    source = once(source, '+repr(work_guard)+', '+repr(gate+work_guard)+')\n')
        executable = source.replace(needle,hook+needle)
        if executable.replace(hook,'')!=source:raise ValueError('provenance assembly inverse differs')
    compile(executable,str(entry)+'#plan056','exec')
    return executable,{'__name__':'__main__','__file__':str(entry)},proof
