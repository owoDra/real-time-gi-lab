#!/usr/bin/env python3
"""Post-hoc whole-image and separately stratified interpretation of 193."""
import itertools
import json
import os
from pathlib import Path
import resource
import subprocess
import sys

import numpy as np

import diagnose_readiness_bottlenecks as D


def moment_diagnostics(mean, second, spp):
    # This corpus is grey. Verify it before using a single channel's second
    # moment as a luminance second moment (no RGB cross moments are stored).
    if not np.array_equal(mean[...,0],mean[...,1]) or not np.array_equal(mean[...,0],mean[...,2]):
        raise ValueError('grey-channel assumption failed')
    if not np.array_equal(second[...,0],second[...,1]) or not np.array_equal(second[...,0],second[...,2]):
        raise ValueError('grey second-moment assumption failed')
    x=mean[...,0];m2=second[...,0]
    path_variance=np.maximum(m2-x*x,0)
    observed=float(np.var(x,axis=0,ddof=1).sum())
    mc_proxy=float(path_variance.mean(0).sum()/spp)
    return {'replicate_variance_sum':observed,
            'mean_path_variance_sum':float(path_variance.mean(0).sum()),
            'iid_variance_of_mean_proxy_sum':mc_proxy,
            'observed_replicate_variance_to_iid_proxy':observed/mc_proxy,
            'scope':'Descriptive comparison to an iid proxy only. RQMC moments are not '
                    'standard errors; pixels are not asserted independent; no confidence or adoption claim.'}


def main():
    target=D.RESULTS/'194-posthoc-depth-weight-and-rqmc-interpretation.json'
    if target.exists():raise ValueError('refuse existing interpretation')
    os.sched_setaffinity(0,{max(os.sched_getaffinity(0))});os.nice(15)
    resource.setrlimit(resource.RLIMIT_CPU,(120,120))
    D.read_bytes(Path(__file__).resolve())
    source=D.read_json(D.RESULTS/'193-selected-bounce-path-diagnosis.json')
    if not source['complete']:raise ValueError('actual terminal selected-path diagnosis missing')
    paths={}
    for name in ('original','guided','nested'):
        variant=next(v for v in source['variants'] if v['variant']==name)
        for p,h in variant['payload_sha256'].items():D.read_bytes(Path(p),h)
        p=next(Path(p) for p in variant['payload_sha256'] if p.endswith('data.json'))
        paths[name]=json.loads(p.read_bytes())
    selected=[]
    for name,rows in paths.items():
        strata=[]
        for label,pixels in (('original_selected_tail',source['selected_pixels'][:8]),
                             ('fixed_grid',source['selected_pixels'][8:])):
            data=[r for r in rows if [r['x'],r['y']] in pixels]
            covariance=np.array([np.array(r['bounce_cross']).reshape(8,8)-np.outer(r['bounce_mean'],r['bounce_mean']) for r in data])
            means=np.array([[next(r['bounce_mean'] for r in data if [r['x'],r['y']]==p and r['seed']==seed)
                             for seed in D.SEEDS] for p in pixels])
            centered=means-means.mean(1,keepdims=True)
            energy=np.einsum('psb,psc->bc',centered,centered)
            strata.append({'stratum':label,'pixel_count':len(pixels),
                'indirect_replicate_energy':float(energy[1:,1:].sum()),
                'first_indirect_path_variance_sum':float(covariance[:,1,1].sum()),
                'later_indirect_path_variance_sum':float(covariance[:,2:,2:].sum()),
                'indirect_path_variance_sum':float(covariance[:,1:,1:].sum()),
                'first_later_path_covariance_sum':float(covariance[:,1,2:].sum()),
                'per_bounce_path_variance_sum':covariance.diagonal(axis1=1,axis2=2).sum(0).tolist(),
                'importance_weight_mean':float(np.mean([r['weight_mean'] for r in data])),
                'importance_weight_second':float(np.mean([r['weight_second'] for r in data]))})
        selected.append({'variant':name,'strata':strata})
    whole=[]
    dirs={'original':D.OUT/'references-recovery-sponza-v1/C1_T_B8',
          'first_bounce':D.OUT/'references-v1/C1_T_B2'}
    for name,directory in dirs.items():
        qualification=D.read_json(directory/'qualification.json')
        for spp in (8192,16384,32768):
            means,second=D.load_level(directory,qualification,spp)
            whole.append({'variant':name,'spp':spp,
                          **moment_diagnostics(means[...,2,:],second[...,2,:],spp)})
    campaign=D.read_json(D.RESULTS/'180-primary-direction-second-stop-bounded-feasibility.json')
    for level in campaign['levels']:
        spp=level['spp'];means=[];seconds=[]
        for i,seed in enumerate(D.SEEDS):
            p=D.OUT/f'primary-direction-feasibility-recovery-v3/o.n{spp}.s{i}.f64'
            m,s=D.sidecar(p,level['payload_sha256'][f'.s{i}.f64'],spp,seed)
            means.append(m);seconds.append(s)
        whole.append({'variant':'guided','spp':spp,
                      **moment_diagnostics(np.stack(means)[...,2,:],np.stack(seconds)[...,2,:],spp)})
    comparisons=[]
    for spp in (8192,16384):
        a=next(r for r in whole if r['variant']=='original' and r['spp']==spp)
        b=next(r for r in whole if r['variant']=='guided' and r['spp']==spp)
        comparisons.append({'spp':spp,
            'guided_to_original_path_variance_ratio':b['mean_path_variance_sum']/a['mean_path_variance_sum'],
            'guided_to_original_replicate_variance_ratio':b['replicate_variance_sum']/a['replicate_variance_sum'],
            'guided_to_original_iid_proxy_efficiency_ratio':b['observed_replicate_variance_to_iid_proxy']/a['observed_replicate_variance_to_iid_proxy']})
    result={'schema':'n010-posthoc-depth-weight-and-rqmc-interpretation/1',
        'complete':True,'gpu_run':False,'new_transport_samples':False,
        'classification':'POST_HOC_DIAGNOSTIC_NO_ADMISSION',
        'source_commit':subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),
        'input_sha256':D.INPUTS,'selected_path_strata':selected,
        'whole_image_moment_diagnostics':whole,'whole_image_comparisons':comparisons,
        'selection_warning':'Tail pixels were selected for large ORIGINAL replicate energy. '
            'Regression to the mean prevents interpreting their improvement under any new seed mapping '
            'as a fair global improvement. Fixed grid is separately reported but only eight pixels.',
        'scope':'C1 retained image moments plus all sixteen plan-057 path diagnostics. '
            'No other state, full image nested-scramble result, reference qualification or timing proof.',
        'tests':'NOT_RUN; post-hoc scientific analysis',
        'readiness':'NOT_ESTABLISHED; original six gates unchanged'}
    target.write_text(json.dumps(result,indent=2,allow_nan=False)+'\n')
    print(json.dumps({'whole_image_moment_diagnostics':whole,'comparisons':comparisons},indent=2))


if __name__=='__main__':main()
