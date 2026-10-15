#!/usr/bin/env python3
"""Plan 048: original sixteen-boundary calibration with bulk PFM writers."""
from pathlib import Path
from bulk_pfm_capture_programs import HERE, sha, once

if __name__ == '__main__':
    original = HERE/'calibrate_minimal_capture.py'
    if sha(original) != '7fd9b4d46c1529e7563eecc25ca9c0943818e75669ef3c74300143a103206bc4':
        raise ValueError('frozen minimal calibration wrapper changed')
    source = original.read_text()
    for old, new in (
        ('159-minimal-calibration-directory-fix-build.json', '167-bulk-pfm-calibration-fixture-build.json'),
        ('n010-minimal-calibration-fixture-build/2', 'n010-minimal-calibration-fixture-build/3'),
        ('n010-minimal-capture-renderer-calibration/1', 'n010-bulk-pfm-renderer-calibration/1')):
        source = once(source, old, new)
    if source.count('minimal-calibration-build-v2') != 2:
        raise ValueError('fixture dispatch count differs')
    source = source.replace('minimal-calibration-build-v2', 'minimal-calibration-build-v3')
    source = once(source, " if a.output.exists():raise ValueError('refuse existing calibration output')",
        " _expected_result='168-bulk-pfm-calibration-quiet-sizing.json' if a.mode=='sizing' else '169-bulk-pfm-calibration-full-renderer.json'\n"
        " _expected_work='bulk-pfm-calibration-sizing-v1' if a.mode=='sizing' else 'bulk-pfm-calibration-accepted-v1'\n"
        " if a.output.resolve()!=LANE/'results'/_expected_result or a.work.resolve()!=ROOT/'out/research/n010-comparison-readiness'/_expected_work:\n"
        "  raise ValueError('bulk PFM calibration requires registered fresh work/results')\n"
        " if a.output.exists():raise ValueError('refuse existing calibration output')")
    source = once(source, 'Path(_replay_file),Path(_quiet_file),',
        'Path(_replay_file),Path(_quiet_file),Path('+repr(str(original))+'),\n'
        "  LANE/'experiments/048-prospective-bulk-pfm-calibration-output.md',")
    source = once(source, ' _inputs={}', ''' _inputs={}
 if a.mode=='accepted':
  if not a.plan or a.plan.resolve()!=LANE/'results/168-bulk-pfm-calibration-quiet-sizing.json':
   raise ValueError('accepted bulk PFM calibration requires actual sizing 168')
  _sizing=_read(a.plan,_inputs)
  if (_sizing['schema']!='n010-bulk-pfm-renderer-calibration/1' or _sizing['mode']!='sizing'
   or not _sizing['complete'] or not _sizing['all_pass'] or len(_sizing['rows'])!=16):
   raise ValueError('complete full PASS 168 required')
  _check_files(_sizing['fixture_input_sha256'],_inputs)''')
    exec(compile(source, str(original)+'#plan048', 'exec'),
        {'__name__': '__main__', '__file__': __file__})
