"""020 reversible loader overlay and exact canonical metadata admission."""
from pathlib import Path
import subprocess
import numpy as np
import surface_quadratic_replay as OLD
R,C,F,G=OLD.R,OLD.C,OLD.F,OLD.G
ROOT,BASE,RESULTS=OLD.ROOT,OLD.BASE,OLD.RESULTS
PROTOCOL=RESULTS.parent/'experiments/020-surface-quadratic-material-abi-repair.md'
BUILD=BASE/'m001-q020-host-cpu-build-v1/result.json'
SOURCE=ROOT/'src/research/lane_m_gi_competitiveness'
BEFORE='for(q::uint a=4;a<7;a++)require(s.hits[p*8+a]!=0xffffffffu,"hit metadata invalid");'
AFTER='require(s.hits[p*8+4]!=0xffffffffu && s.hits[p*8+6]!=0xffffffffu,"hit primitive/instance metadata invalid");'
OWN=[Path(__file__).with_name(n) for n in ('surface_quadratic_material_abi.py','build_surface_quadratic_material_abi.py','test_surface_quadratic_material_abi.py','surface_quadratic_material_replay.py','surface_quadratic_material_audit.py')]+[PROTOCOL]


def committed():
    for p in OWN:
        R.require(subprocess.check_output(['git','show',G.head()+':'+str(p.relative_to(ROOT))],cwd=ROOT)==p.read_bytes(),'Commit all020code before execution')


def repaired(source):
    R.require(source.count(BEFORE)==1 and AFTER not in source,'020 overlay source/predicate differs')
    result=source.replace(BEFORE,AFTER)
    R.require(result.replace(AFTER,BEFORE)==source,'020 inverse overlay differs')
    return result


def canonical_metadata(raw,meta):
    R.require(raw.ndim==2 and raw.shape[1]==8 and raw.dtype==np.uint32 and meta.ndim==2 and meta.shape[1]>=3,'020 metadata ABI differs')
    R.require(np.isin(raw[:,7],(0,1)).all(),'020 primary flag invalid')
    hit=raw[:,7]==1;ids=raw[hit,4];order=np.argsort(meta[:,0]);keys=meta[order,0]
    R.require(len(keys)>0 and len(np.unique(keys))==len(keys),'020 canonical primitive keys invalid')
    where=np.searchsorted(keys,ids);R.require((where<len(keys)).all(),'020 unknown hit primitive')
    matched=meta[order[where],:3]
    R.require((raw[hit,4]!=0xffffffff).all() and (raw[hit,6]!=0xffffffff).all(),'020 invalid primitive/instance')
    R.require(np.array_equal(raw[hit,4:7],matched),'020 canonical primitive/material/instance mismatch')
    R.require((raw[~hit,4:7]==0xffffffff).all(),'020 miss metadata invalid')
    return dict(hit_pixels=int(hit.sum()),material_uint32_max_hits=int((raw[hit,5]==0xffffffff).sum()),exact_canonical_metadata=True)


def build_gate(inputs):
    b=OLD.pin_inventory(BUILD,inputs)
    R.require(b['complete'] and b['all_pass'] and not b['gpu_executed'],'020 repaired build incomplete')
    F.rehash(b['input_sha256']);F.rehash(b['compiled_dependency_sha256']);inputs.update(b['input_sha256']);inputs.update(b['compiled_dependency_sha256'])
    for p in OWN:OLD.P.pin(p,inputs)
    for key in ('executable','shader'):OLD.P.pin(Path(b[key]),inputs,b[key+'_sha256'])
    return b
