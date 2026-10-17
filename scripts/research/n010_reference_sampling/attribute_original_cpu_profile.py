#!/usr/bin/env python3
"""Plan093: post-hoc old CPU IP attribution, byte-exact unexecuted debug companion."""
import hashlib
import json
import os
from pathlib import Path
import re
import resource
import struct
import subprocess
import time
import diagnose_selected_bounce_paths as D
from run_primary_direction_sequence import require_no_other_research_worker

WORK = D.OUT / 'cpu-profile-inline-attribution-v1'
OUTPUT = D.RESULTS / '241-posthoc-cpu-profile-inline-attribution.json'
PLAN = D.RESULTS.parent / 'experiments/093-profile-debug-companion-attribution.md'
PERF = '/nix/store/r9yzbjkiz71ig7g26jdd9cc4pp8ymdph-perf-linux-7.2.10/bin/perf'

def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()

def text_section(path):
    data = path.read_bytes()
    if data[:6] != b'\x7fELF\x02\x01':
        raise ValueError('expected little-endian ELF64')
    header = struct.unpack_from('<16sHHIQQQIHHHHHH', data)
    offset, entrysize, count, stringindex = header[6], header[11], header[12], header[13]
    sections = [struct.unpack_from('<IIQQQQIIQQ', data, offset+i*entrysize) for i in range(count)]
    names = sections[stringindex]
    names = data[names[4]:names[4]+names[5]]
    for s in sections:
        if names[s[0]:].split(b'\0', 1)[0] == b'.text':
            return s[3], data[s[4]:s[4]+s[5]]
    raise ValueError('no text section')

def main():
    if WORK.exists() or OUTPUT.exists():
        raise ValueError('refuse existing attribution')
    require_no_other_research_worker()
    os.sched_setaffinity(0, {max(os.sched_getaffinity(0))}); os.nice(15)
    resource.setrlimit(resource.RLIMIT_AS, (4*1024**3,)*2)
    for p in (Path(__file__).resolve(), PLAN, Path(D.__file__), Path(PERF)):
        D.checked(p)
    build = json.loads(D.checked(D.RESULTS/'224-all-split-exporter-build.json'))
    profile = json.loads(D.checked(D.RESULTS/'240-original-all-split-cpu-profile-local-linker.json'))
    if not build['all_pass'] or not profile['complete']:
        raise ValueError('actual original build/complete profiles required')
    for record in (build, profile):
        for p, h in record['payload_sha256'].items(): D.checked(Path(p), h)
    WORK.mkdir()
    result = dict(schema='n010-posthoc-cpu-inline-attribution/1', complete=False,
        posthoc=True, gpu_run=False, native_runs=0, reference_admission=False,
        source_commit=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),
        classification='OFFLINE_ATTRIBUTION_ACQUIRING',input_sha256=D.INPUTS,attempts=[],rows=[],
        tests='NOT_RUN; offline attribution and unexecuted standalone debug companion')
    def save(): OUTPUT.write_text(json.dumps(result,indent=2,allow_nan=False)+'\n')
    env=dict(os.environ,DEBUGINFOD_URLS='',PERF_PAGER='cat');env.pop('LD_LIBRARY_PATH',None)
    def execute(command, tag, cpu=30, elapsed=45):
        def limits():
            resource.setrlimit(resource.RLIMIT_CPU,(cpu,)*2)
            resource.setrlimit(resource.RLIMIT_FSIZE,(32*1024**2,)*2)
            (WORK/(tag+'.resources.json')).write_text(json.dumps(dict(pid=os.getpid(),
                start_ticks=int(Path('/proc/self/stat').read_text().rsplit(')',1)[1].split()[19]),
                cpu=list(resource.getrlimit(resource.RLIMIT_CPU)),address_space=list(resource.getrlimit(resource.RLIMIT_AS)),
                affinity=sorted(os.sched_getaffinity(0)),nice=os.getpriority(os.PRIO_PROCESS,0),command=command))+'\n')
        attempt=dict(command=command,tag=tag);result['attempts'].append(attempt);save()
        before=resource.getrusage(resource.RUSAGE_CHILDREN);start=time.monotonic()
        with (WORK/(tag+'.stdout')).open('w') as out,(WORK/(tag+'.stderr')).open('w') as err:
            proc=subprocess.run(command,env=env,stdout=out,stderr=err,timeout=elapsed,preexec_fn=limits)
        after=resource.getrusage(resource.RUSAGE_CHILDREN)
        attempt.update(returncode=proc.returncode,elapsed=time.monotonic()-start,
            cpu_seconds=after.ru_utime+after.ru_stime-before.ru_utime-before.ru_stime);save()
        if proc.returncode:raise ValueError(tag+' failed')
        return (WORK/(tag+'.stdout')).read_text()
    save()
    try:
        original=Path(build['command'][-1]);debug=WORK/'oracle-debug-unexecuted'
        command=list(build['command']);command[-1]=str(debug);command.insert(1,'-g')
        execute(command,'compile',140,180)
        oldtext,newtext=text_section(original),text_section(debug)
        if oldtext!=newtext:raise ValueError('debug/original text bytes or address differ')
        def symbols(p,tag):
            data=execute(['nm','--defined-only',str(p)],tag)
            return [(f[0],f[2]) for line in data.splitlines() if len(f:=line.split())==3 and f[1] in ('t','T')]
        if symbols(original,'original-symbols')!=symbols(debug,'debug-symbols'):
            raise ValueError('debug/original text symbol identities differ')
        result.update(debug_text_and_addresses_exact=True,debug_binary_never_executed=True,
            text_address=oldtext[0],text_sha256=hashlib.sha256(oldtext[1]).hexdigest())
        for row in profile['rows']:
            case=row['name'];data=row['attempts'][0]['command'][row['attempts'][0]['command'].index('-o')+1]
            annotation=execute([PERF,'annotate','--stdio','--stdio-color','never','--no-source',
                '--show-nr-samples','--dsos',original.name,'-i',data],case+'-annotation')
            counts={}
            for line in annotation.splitlines():
                m=re.match(r'\s*(\d+)\s*:\s*([0-9a-f]+):',line)
                if m and int(m[1]):
                    address=int(m[2],16);counts[address]=counts.get(address,0)+int(m[1])
            if not counts:raise ValueError('no instruction counts decoded')
            addresses=sorted(counts)
            frames=execute(['addr2line','-a','-f','-i','-C','-e',str(debug)]+[hex(a) for a in addresses],case+'-frames')
            blocks={};address=None
            for line in frames.splitlines():
                if re.fullmatch(r'0x[0-9a-fA-F]+',line):
                    address=int(line,16);blocks[address]=[]
                elif address is not None:blocks[address].append(line)
            categories={};mapped=[]
            for address in addresses:
                stack=blocks.get(address,[]);joined='\n'.join(stack)
                category='other_or_unresolved'
                for fragment,label in [('Bvh::slab','bvh_box_slab'),('WatertightRay::intersect','triangle_intersection'),
                    ('WatertightRay::WatertightRay','watertight_ray_setup'),('Bvh::traverse','remaining_bvh_traversal'),
                    ('Bvh::closest','remaining_bvh_closest'),('Bvh::occluded','remaining_bvh_occluded')]:
                    if fragment in joined:category=label;break
                categories[category]=categories.get(category,0)+counts[address]
                mapped.append(dict(address=hex(address),samples=counts[address],category=category,inline_frames=stack))
            total=row['decoded_ip_sample_count'];covered=sum(counts.values())
            if covered>total:raise ValueError('annotation sample count exceeds original decoded samples')
            result['rows'].append(dict(name=case,total_original_ip_samples=total,
                annotated_executable_samples=covered,unannotated_samples=total-covered,
                category_samples=categories,category_fraction_of_all_original_samples={k:v/total for k,v in categories.items()},
                address_samples=mapped,lost_record_lines=row['lost_record_lines']))
            save()
        for p,h in list(D.INPUTS.items()):D.checked(Path(p),h)
        if sum(p.stat().st_size for p in WORK.iterdir() if p.is_file())>128*1024**2:raise ValueError('spool cap')
        result.update(complete=True,classification='POSTHOC_INLINE_ATTRIBUTION_COMPLETE_NO_ADMISSION')
    except (ValueError,OSError,KeyError,AssertionError,subprocess.SubprocessError) as e:
        result.update(classification='OFFLINE_ATTRIBUTION_FAILURE_PARTIALS_RETAINED',failure=str(e))
    result['payload_sha256']={str(p):sha(p) for p in WORK.iterdir() if p.is_file()};save()
    print(json.dumps({k:result.get(k) for k in ('complete','classification','failure')},indent=2))
    raise SystemExit(0 if result['complete'] else 2)

if __name__=='__main__':main()
