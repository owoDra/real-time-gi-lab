"""Plan 052 source assembly; never dispatch GPU work at import/assembly time."""
import hashlib
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
RESULTS = ROOT/'research/lanes/n010-comparison-readiness/results'


def digest(source):
    return hashlib.sha256(source.encode()).hexdigest()


def original_program():
    wrapper = HERE/'calibrate_bulk_pfm_capture.py'
    if digest(wrapper.read_text())!='ed76b932d42b5cb13d41159602d287be5b09cf880e808bf0d51980a2841473bc':
        raise ValueError('frozen plan-048 wrapper changed')
    captured = []
    scope = {'__name__':'__main__', '__file__':str(wrapper),
             'exec':lambda code, namespace:captured.append(namespace)}
    exec(compile(wrapper.read_text(), str(wrapper)+'#source-only', 'exec'), scope)
    if len(captured)!=1:
        raise ValueError('plan-048 assembly shape changed')
    minimal_source = scope['source']
    minimal_scope = dict(captured[0])
    captured.clear()
    minimal_scope['exec'] = lambda code, namespace:captured.append(namespace)
    exec(compile(minimal_source, str(wrapper)+'#minimal-source-only', 'exec'), minimal_scope)
    if len(captured)!=1:
        raise ValueError('minimal program assembly shape changed')
    return minimal_scope['source'], captured[0]


def program():
    original, scope = original_program()
    source = original
    changes = []

    def replace(old, new, unique=False):
        nonlocal source
        count = source.count(old)
        if count<1 or (unique and count!=1) or new in source:
            raise ValueError('plan-052 source guard differs: '+old[:80])
        source = source.replace(old, new)
        changes.append((old, new, count))

    for old, new in (
        ('168-bulk-pfm-calibration-quiet-sizing.json', '177-hidden-ide-bulk-pfm-calibration-sizing.json'),
        ('169-bulk-pfm-calibration-full-renderer.json', '178-hidden-ide-bulk-pfm-calibration-full-renderer.json'),
        ('bulk-pfm-calibration-sizing-v1', 'hidden-ide-bulk-pfm-sizing-v1'),
        ('bulk-pfm-calibration-accepted-v1', 'hidden-ide-bulk-pfm-accepted-v1'),
        ('n010-bulk-pfm-renderer-calibration/1', 'n010-hidden-ide-bulk-pfm-renderer-calibration/1'),
        ('actual sizing 168', 'actual sizing 177'),
        ('full PASS 168 required', 'full PASS 177 required')):
        replace(old, new)
    replace(' _inputs={}', ' _inputs={}\n _visibility.prerequisites(_inputs)', unique=True)
    anchor = ' for boundary in cohort:\n'
    if source.count(anchor)!=1:
        raise ValueError('acquisition loop anchor differs')
    head, tail = source.split(anchor)
    hook = (' _visibility.bind(result,a,_inputs,_assembly_proof)\n'
            ' execute=_visibility.wrap_execute(execute)\n'
            ' with _visibility:\n')
    unwrapped = anchor+tail
    wrapped = ''.join(' '+line if line.strip() else line
                      for line in unwrapped.splitlines(keepends=True))
    source = head+hook+wrapped
    restored = head+unwrapped
    for old, new, count in reversed(changes):
        if restored.count(new)!=count:
            raise ValueError('plan-052 inverse dispatch count differs')
        restored = restored.replace(new, old)
    if restored!=original:
        raise ValueError('whole plan-048 program inverse differs')
    if source.split("if __name__=='__main__':")[0]!=original.split("if __name__=='__main__':")[0]:
        raise ValueError('scientific function body changed')
    proof = {'whole_generated_program_inverse_exact':True,
             'all_original_function_definitions_byte_identical':True,
             'original_generated_source_sha256':digest(original),
             'generated_source_sha256':digest(source),
             'restored_generated_source_sha256':digest(restored),
             'dispatch_changes':[{'old':a,'new':b,'count':n} for a,b,n in changes],
             'environment_hook':'single-PID context around complete acquisition; before/after native guards'}
    from hidden_ide_calibration_policy import VisibilityPolicy
    scope.update(_visibility=VisibilityPolicy(), _assembly_proof=proof)
    return source, scope, proof
