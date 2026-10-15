#!/usr/bin/env python3
"""Plan 044: original full calibration with isolated minimal-output executables."""
from pathlib import Path
import sys

SCRIPTS = Path(__file__).resolve().parents[1]/'n010_comparison_readiness'
sys.path.insert(0,str(SCRIPTS))
from generate_rqmc_oracle import once
from reference_provenance import ROOT, RESULTS, read, sha
from qualify_hybrid_references import check_files
from readiness_preflight import replay
from run_primary_direction_sequence import require_no_other_research_worker

if __name__ == '__main__':
    original = SCRIPTS/'calibrate_renderer.py'
    digest = '64deb4d3995eb40498ca2b454dacf6d97d5909115ef32a36e3c80c3a7683cb8d'
    if sha(original) != digest:
        raise ValueError('original scientific calibration changed')
    source = original.read_text()
    fixture = ROOT/'out/research/n010-comparison-readiness/minimal-calibration-build-v1'
    for name in ('phos-n010-capture','phos-n010-pixel-pt'):
        source = once(source,"ROOT/'build/n009/"+name+"'",repr(fixture/name).replace('PosixPath','Path'))
    source = once(source,' env=os.environ.copy();cell=',
        ' env=os.environ.copy();env["PHOS_N010_MINIMAL_CALIBRATION_READBACK"]="1";cell=')
    source = once(source," return result\ndef schedule",''' if not _replay(result['allocation_ledger']):
  raise ValueError('minimal capture ledger replay/peak/teardown failed')
 baseline=next(r['evidence'] for r in _baseline['rows'] if r['boundary']['id']==b['id'])
 expected=baseline['payloads'][0]['images']
 if any(p['images']!=expected for p in payloads):
  raise ValueError('minimal capture image differs from original quiet sizing 046')
 result['images_byte_equal_to_original_046']=True
 result['allocation_ledger_replay_pass']=True
 return result
def schedule''')
    source = once(source,"'schema':'n010-renderer-calibration/1'", "'schema':'n010-minimal-capture-renderer-calibration/1'")
    source = once(source," lock=json.loads(a.lock.read_text());cohort=boundaries(lock)",'''
 if a.output.exists():raise ValueError('refuse existing calibration output')
 if a.boundaries:raise ValueError('plan 044 requires all sixteen boundaries')
 _require_quiet()
 _inputs={}
 _build=_read(LANE/'results/156-minimal-calibration-fixture-build.json',_inputs)
 if not _build['complete'] or not _build['all_pass'] or not _build['source_inverse_proof'] or not _build['active_inputs_byte_unchanged']:
  raise ValueError('minimal fixture build proof incomplete/failed')
 _check_files(_build['input_sha256'],_inputs)
 _fixture=ROOT/'out/research/n010-comparison-readiness/minimal-calibration-build-v1'
 _check_files({str(_fixture/name):h for name,h in _build['generated_sha256'].items()},_inputs)
 _baseline=_read(LANE/'results/046-calibration-quiet-sizing.json',_inputs)
 if sha(LANE/'results/046-calibration-quiet-sizing.json')!='2ab654662ffdef9b873179d95a9142eea7e18ad0635cec37601c51f0f828d36d':
  raise ValueError('immutable original quiet sizing 046 changed')
 if not _baseline['complete'] or not _baseline['all_pass'] or len(_baseline['rows'])!=16:
  raise ValueError('original complete quiet sizing proof required')
 if _baseline['lock_sha256']!=sha(a.lock):raise ValueError('original quiet sizing lock differs')
 for _path in (Path(_wrapper),Path(_original),LANE/'experiments/044-prospective-minimal-calibration-capture.md',
  LANE/'experiments/001-comparison-readiness.md',LANE/'experiments/009-timing-calibration-execution.md',
  LANE/'experiments/012-amendment-5-sizing-probe-range.md',Path(_replay_file),Path(_quiet_file),
  ROOT/'build/n009/n010-neutral-work-verify',ROOT/'scripts/run_with_vulkan.sh'):
  _inputs[str(_path)]=sha(_path)
 lock=_read(a.lock,_inputs);cohort=boundaries(lock)
 for _spec in lock['cells'].values():
  for _path in (ROOT/_spec['state_directory']).iterdir():
   if _path.is_file():_inputs[str(_path)]=sha(_path)
 for _directory in (ROOT/'assets/Vulkan-Samples-Assets/scenes/sponza',
  ROOT/'out/research/n008-hdr-oracle/phase-b-states/n004-scenes'):
  for _path in _directory.rglob('*'):
   if _path.is_file():_inputs[str(_path)]=sha(_path)
 _path=ROOT/'out/research/n010-comparison-readiness/light-selection-v1/sponza-local-motion.n009contract'
 _inputs[str(_path)]=sha(_path)''')
    source = once(source," if a.plan:result['plan_sha256']=sha(a.plan)",
        " result['fixture_input_sha256']=_inputs\n"
        " result['capture_scope']='Every image/scratch/time and full GPU boundaries; bulk diagnostic/state file copies suppressed outside timing'\n"
        " if a.plan:result['plan_sha256']=sha(a.plan)")
    source = once(source,' result.update(complete=True,all_pass=',
        ' _check_files(_inputs,{})\n result.update(complete=True,all_pass=')
    # Full old 001/009 schedule and analysis functions remain verbatim.
    if (original.read_text().split('def schedule(')[1].split("if __name__")[0]
        != source.split('def schedule(')[1].split("if __name__")[0]):
        raise ValueError('scientific schedule/statistics/thresholds changed')
    import readiness_preflight
    import run_primary_direction_sequence
    namespace = {'__name__':'__main__','__file__':str(original),
        '_replay':replay,'_read':read,'_check_files':check_files,
        '_require_quiet':require_no_other_research_worker,
        '_wrapper':str(Path(__file__).resolve()),'_original':str(original),
        '_replay_file':str(Path(readiness_preflight.__file__).resolve()),
        '_quiet_file':str(Path(run_primary_direction_sequence.__file__).resolve())}
    exec(compile(source,str(original)+'#plan044','exec'),namespace)
