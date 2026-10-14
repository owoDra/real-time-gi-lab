#!/usr/bin/env python3
"""Retire the original C7/C1/C2/C4/C5/C6 runner only after C1 T_B8 ends."""
import argparse
import json
import os
from pathlib import Path
import signal
import time
import subprocess
from qualify_incremental_references import dependencies
from qualify_references import ROOT, LEVELS
from reference_provenance import sha

def command(pid):
    return [w.decode() for w in (Path('/proc')/str(pid)/'cmdline').read_bytes().split(b'\0') if w]

def original(pid,work):
    path=Path('/proc')/str(pid)
    if path.stat().st_uid!=os.getuid():raise ValueError('refuse another user process')
    words=command(pid)
    if not any(Path(w).name=='qualify_references.py' for w in words):raise ValueError('unexpected parent process')
    if Path(words[words.index('--work')+1]).resolve()!=work.resolve():raise ValueError('original runner work differs')
    start=words.index('--cells')+1
    stop=next((i for i in range(start,len(words)) if words[i].startswith('--')),len(words))
    if words[start:stop]!=['C7','C1','C2','C4','C5','C6']:raise ValueError('unexpected original selection')
    return words

def children(parent,work):
    found=[]
    for path in Path('/proc').iterdir():
        if not path.name.isdigit():continue
        try:
            stat=(path/'stat').read_text().rsplit(')',1)[1].split()
            if int(stat[1])!=parent:continue
            words=command(int(path.name))
            if not words:continue
            if Path(words[0]).name!='n010_rqmc_oracle':raise ValueError('unexpected child; resume parent without killing child')
            prefix=Path(words[words.index('--out')+1]).resolve()
            if not prefix.is_relative_to(work.resolve()):raise ValueError('child output differs from original acquisition')
            found.append({'pid':int(path.name),'output_prefix':str(prefix)})
        except (FileNotFoundError,ProcessLookupError):pass
    return found

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--pid',type=int,required=True)
    parser.add_argument('--references',type=Path,required=True)
    parser.add_argument('--work',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    if args.work.exists() or args.output.exists():raise ValueError('refuse existing retirement record')
    proof=dependencies()
    original_command=original(args.pid,args.references)
    args.work.mkdir(parents=True)
    status={'schema':'n010-original-qualifier-retirement/1','complete':False,
            'phase':'WAITING_FOR_COMPLETED_C1_T_B8_TRANSPORT','parent_pid':args.pid,
            'proof_sha256':proof,'source_commit':subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),
            'script_sha256':sha(Path(__file__)),'parent_command':original_command,
            'rule':'First completed eligible pair or full frozen cap; no threshold/outcome change. New C2/C4/C5/C6 view selected before incremental images, all original and any subsequent partial files retained.'}
    (args.work/'status.json').write_text(json.dumps(status,indent=2)+'\n')
    boundary=args.references/'C1_T_B8/qualification.json'
    while True:
        if original(args.pid,args.references)!=original_command or proof!={name:sha(ROOT/'research/lanes/n010-comparison-readiness/results'/name) for name in proof}:raise ValueError('parent or proof identity changed')
        try:q=json.loads(boundary.read_text())
        except (OSError,json.JSONDecodeError):q={}
        levels=q.get('levels',[])
        eligible=q.get('classification')=='STATISTICALLY_ELIGIBLE' and len(levels)>=2 and levels[-1]['screen']['status']=='statistical-screen-pass'
        capped=bool(levels) and levels[-1]['spp']==LEVELS[-1] and levels[-1]['screen']['status']=='statistical-screen-fail'
        if eligible or capped:break
        time.sleep(1)
    # Stop only the known qualification parent so it cannot launch another
    # original transport during inspection. Preserve any child already started
    # after this completed transport boundary, as allowed by Amendment 6.
    if dependencies()!=proof:raise ValueError('binary/sampler proof changed before retirement')
    os.kill(args.pid,signal.SIGSTOP)
    try:active=children(args.pid,args.references)
    except Exception:
        os.kill(args.pid,signal.SIGCONT)
        raise
    try:
        for child in active:
            try:os.kill(child['pid'],signal.SIGTERM)
            except ProcessLookupError:pass
        os.kill(args.pid,signal.SIGTERM)
    finally:
        try:os.kill(args.pid,signal.SIGCONT)
        except ProcessLookupError:pass
    deadline=time.monotonic()+60
    while any((Path('/proc')/str(pid)).exists() for pid in [args.pid]+[c['pid'] for c in active]):
        if time.monotonic()>deadline:raise ValueError('process termination not confirmed; inspect retained state')
        time.sleep(.2)
    raw=boundary.read_bytes();(args.work/'boundary-qualification.json').write_bytes(raw)
    inventory={}
    for cell in ('C7','C1','C2','C4','C5','C6'):
        for vertices in (2,8):
            directory=args.references/f'{cell}_T_B{vertices}'
            if not directory.exists():continue
            for path in sorted(directory.glob('*')):
                if path.is_file():inventory[str(path.resolve())]={'bytes':path.stat().st_size,'sha256':sha(path)}
    status.update(complete=True,phase='RETIRED_AT_COMPLETED_TRANSPORT_BOUNDARY',
                  boundary_classification=q['classification'],boundary_levels=[level['spp'] for level in levels],
                  boundary_qualification_sha256=sha(boundary),subsequent_partial_children=active,
                  retained_file_inventory=inventory,utc=time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()))
    (args.work/'status.json').write_text(json.dumps(status,indent=2)+'\n')
    args.output.write_text(json.dumps(status,indent=2)+'\n')
    print(status['phase'])
