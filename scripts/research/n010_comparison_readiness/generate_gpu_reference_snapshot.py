#!/usr/bin/env python3
"""Create read-only export accessors and a separate Float64 Vulkan context."""
import argparse
import json
from pathlib import Path
from reference_provenance import ROOT,RESULTS,sha

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out',type=Path,required=True)
    args=parser.parse_args()
    if args.out.exists():raise ValueError('refuse existing source snapshot')
    proof_path=RESULTS/'022-cached-oracle-equivalence.json'
    proof=json.loads(proof_path.read_text())
    if not proof['complete'] or not proof['all_pass']:raise ValueError('complete CPU cache proof required')
    base=ROOT/'out/research/n010-comparison-readiness/cached-oracle-source'
    for name,digest in proof['generated_source_sha256'].items():
        if sha(base/name)!=digest:raise ValueError('proved CPU source changed')
    args.out.mkdir(parents=True)
    header=(base/'n010_rqmc_oracle.hpp').read_text()
    needle='    std::vector<Node> nodes_;\n};'
    if header.count(needle)!=1:raise ValueError('BVH snapshot anchor changed')
    header=header.replace(needle,'    std::vector<Node> nodes_;\npublic:\n    const auto& n010_nodes() const {return nodes_;}\n    const auto& n010_order() const {return order_;}\n};')
    needle='    const Bvh& bvh() const { return bvh_; }'
    if header.count(needle)!=1:raise ValueError('oracle snapshot anchor changed')
    header=header.replace(needle,needle+'\n    double n010_edge_inset() const {return edge_inset_;}')
    (args.out/'n010_reference_snapshot.hpp').write_text(header)
    context_source=ROOT/'src/research/n010_comparison_readiness/ddgi_volume_bringup.cpp'
    context=context_source.read_text().split('static void run(')[0]
    needle='        VkPhysicalDeviceFeatures enabled{};'
    if context.count(needle)!=1:raise ValueError('context feature anchor changed')
    context=context.replace(needle,'        if(!features.shaderFloat64 || !features.shaderInt64)throw std::runtime_error("Float64/Int64 unavailable");\n'+needle)
    context=context.replace('enabled.shaderStorageImageExtendedFormats=VK_TRUE;', 'enabled.shaderStorageImageExtendedFormats=VK_TRUE;enabled.shaderFloat64=VK_TRUE;enabled.shaderInt64=VK_TRUE;')
    context=context.replace('buffers.reserve(8)','buffers.reserve(16)')
    (args.out/'n010_reference_context.hpp').write_text(context)
    meta={'schema':'n010-gpu-reference-source-snapshot/1','cpu_equivalence_sha256':sha(proof_path),
          'input_sha256':{'CPU header':sha(base/'n010_rqmc_oracle.hpp'),'Vulkan context':sha(context_source)},
          'generated_sha256':{p.name:sha(p) for p in sorted(args.out.glob('*.hpp'))},
          'scope':'Read-only BVH/order/edge-inset exports and separate FP64/Int64 context. Original sources/binaries unchanged; no GPU reference eligibility.'}
    (args.out/'snapshot.json').write_text(json.dumps(meta,indent=2)+'\n')
