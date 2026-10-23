#!/usr/bin/env python3
"""CPU-only immutable-report consolidation; no sampling, GPU, or metric recomputation."""
from pathlib import Path
import hashlib, json, math, subprocess
base = Path('research/lanes/lane-m-gi-competitiveness')
results = base / 'results'
commit = subprocess.check_output(['git', 'rev-parse', 'HEAD'], text=True).strip()
source = Path(__file__).resolve().relative_to(Path.cwd().resolve())
assert subprocess.check_output(['git', 'show', commit + ':' + str(source)]) == Path(__file__).read_bytes(), 'Commit this read-only consolidator before execution'
inputs = {}

def read(name):
    p = results / name
    raw = p.read_bytes()
    assert subprocess.check_output(['git', 'show', commit + ':' + str(p)]) == raw, 'Commit accepted input before consolidation'
    inputs[str(p)] = hashlib.sha256(raw).hexdigest()
    d = json.loads(raw)
    if 'source_commit' in d:
        assert subprocess.run(['git', 'merge-base', '--is-ancestor', d['source_commit'], 'HEAD'], capture_output=True).returncode == 0
    return d
refs = read('016-six-original-references-and-retained-rc-raw-replay.json')
pt = read('022-six-pt-ladders-raw-replay.json')
dense = read('025-dense-fixed-control-replay.json')
fixed = read('027-fixed-traversal-controls-raw-replay.json')
ddgi = read('079-ddgi-corrected-six-targets-quality-raw-replay.json')
assert ddgi['cohort_complete'] and ddgi['all_existing_evidence_valid'] and (ddgi['next_named_case'] is None)
assert refs['reference_qualified_slot_count'] == refs['reference_total_slot_count'] == 6 and pt['complete'] and dense['complete'] and fixed['complete']
for name in ['028-fixed-control-quality-outcome.md', '050-ddgi-quality-screen-border-integrity-supersession.md', '067-ddgi-separated-border-twenty-controls-raw-replay.json', '068-ddgi-separated-border-requalification-outcome.md', '080-ddgi-corrected-six-targets-quality-outcome.md', '081-ddgi-corrected-six-targets-checkpoint-verification.json']:
    p = results / name
    raw = p.read_bytes()
    assert subprocess.check_output(['git', 'show', commit + ':' + str(p)]) == raw
    inputs[str(p)] = hashlib.sha256(raw).hexdigest()

def decision(c):
    v = [c['total']['nrmse'], c['indirect']['nrmse'], c['indirect']['signed_sum_bias']]
    assert all((x is not None and math.isfinite(x) for x in v)) and v[0] >= 0 and (v[1] >= 0)
    assert all((c[x]['scoring_exclusions'] == 0 and c[x]['pixels'] == 57600 for x in ('direct', 'indirect', 'total')))
    return 'PASS' if v[0] <= 0.05 and v[1] <= 0.1 and (abs(v[2]) <= 0.05) else 'QUALITY_FAIL'
rows = []
for cell in ('H01', 'H02', 'H03'):
    for depth in (2, 8):
        target = f'T_B{depth}'
        reference = next((x for x in refs['rows'] if (x['cell'], x['transport']) == (cell, target)))
        proof = reference['verification']
        assert reference['reference_eligible'] and reference['accepted_spp'] == 16384 and proof['pass'] and (proof['levels'] == [8192, 16384])
        qual = Path(proof['directory']) / 'qualification.json'
        assert hashlib.sha256(qual.read_bytes()).hexdigest() == proof['qualification_sha256']
        role_rows = []

        def add(role, c, classification, verification, budget, finite, levels=None):
            assert verification == proof, 'Different physical reference/provenance between families'
            assert decision(c) == classification, 'Classifier differs from unchanged inclusive original gates'
            for name in ('direct', 'indirect', 'total'):
                assert c[name]['reference_rms'] == reference['retained_incumbent']['quality']['components'][name]['reference_rms'], 'Normalization differs between families'
            role_rows.append(dict(role=role, classification=classification, budget=budget, finite_depth_semantics_qualified=finite, scoring_exclusions=0, components={k: {m: c[k][m] for m in ('nrmse', 'signed_sum_bias', 'reference_rms', 'whole_image_max_absolute')} for k in ('direct', 'indirect', 'total')}, **{'observed_levels': levels} if levels is not None else {}))
        p = next((x for x in pt['rows'] if (x['cell'], x['transport']) == (cell, target)))
        assert p['selected_spp'] is not None
        assert [x['spp'] for x in p['levels']] == [1, 4, 16, 64, 256, 1024][:len(p['levels'])]
        assert all((x['audit']['quality_evidence_valid'] and x['audit']['classification'] == 'QUALITY_FAIL' for x in p['levels'][:-1]))
        z = p['levels'][-1]['audit']
        assert z['quality_evidence_valid'] and z['classification'] == 'PASS' and (p['selected_spp'] == p['levels'][-1]['spp'])
        add('pixel-pt', z['components'], p['classification'], z['reference_verification'], dict(selected_spp=p['selected_spp']), True, [dict(spp=x['spp'], classification=x['audit']['classification']) for x in p['levels']])
        z = reference['retained_incumbent']
        assert z['quality']['state_bytes_equal'] and z['quality']['complete_physical_scene_bytes_equal']
        add('retained-hwrt-rc', z['quality']['components'], z['classification'], proof, 'Original fixed RC budget; one scene image scored against B2/B8, not PT-equivalent', False)
        for role in ('vanilla', 'software'):
            native = next((x for x in fixed['native_audits'] if x['cell'] == cell and x['role'] == role))
            assert native['audit']['quality_evidence_valid']
            z = next((x for x in native['audit']['rows'] if x['transport'] == target))
            assert z['finite_depth_equivalent'] is False
            add(role + '-rc', z['components'], z['classification'], native['audit']['references'][str(depth)], 'Original fixed RC budget; one scene image scored against B2/B8, not PT-equivalent', False)
        z = next((x['report'] for x in dense['rows'] if (x['report']['cell'], x['report']['transport']) == (cell, target)))
        assert z['independent_metric_replay'] and z['source_raw_inventory_replayed'] and (z['finite_depth_equivalent'] is False)
        add('dense-rc', z['quality']['components'], z['classification'], z['reference_verification'], 'Original fixed dense RC budget; ignores finite-depth/sample pushes, same image for B2/B8', False)
        levels = [x for x in ddgi['rows'] if (x['scope']['cell'], x['scope']['vertices']) == (cell, depth)]
        assert levels and [x['scope']['rung'] for x in levels] == list(range(len(levels))) and all((x['quality_evidence_valid'] for x in levels))
        assert all((x['classification'] == 'QUALITY_FAIL' for x in levels[:-1]))
        z = levels[-1]
        assert z['classification'] == 'PASS' or z['scope']['rung'] == 2
        add('corrected-ddgi', z['components'], z['classification'], z['reference_verification'], dict(rung=z['scope']['rung'], grid_side=z['scope']['grid_side'], rays_per_probe=z['scope']['rays'], stages=depth - 1, reset_all=True, temporal_history=False), True, [dict(rung=x['scope']['rung'], classification=x['classification']) for x in levels])
        rows.append(dict(cell=cell, transport=target, reference=proof, roles=role_rows))
counts = {role: dict(quality_pass=sum((z['classification'] == 'PASS' for row in rows for z in row['roles'] if z['role'] == role)), quality_fail=sum((z['classification'] == 'QUALITY_FAIL' for row in rows for z in row['roles'] if z['role'] == role))) for role in [z['role'] for z in rows[0]['roles']]}
matched = [f"{r['cell']}_{r['transport']}" for r in rows if all((next((z for z in r['roles'] if z['role'] == role))['classification'] == 'PASS' for role in ('pixel-pt', 'corrected-ddgi')))]
report = dict(schema='m001-static-screen-immutable-report-consolidation/1', source_commit=commit, consolidator_path=str(source), consolidator_matches_committed_bytes=True, consolidator_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(), input_report_sha256=inputs, all_inputs_match_committed_bytes=True, all_source_ancestry_pass=True, reference_qualification_files_rehashed=6, reference_provenance_identical_across_all_roles=True, reference_rms_normalization_identical_across_all_roles=True, inclusive_classifications_recomputed_from_reported_metrics=True, old_pt_rc_raw_metrics_recomputed=False, new_ddgi_complete_raw_replay='079-ddgi-corrected-six-targets-quality-raw-replay.json', old_raw_replay_provenance='Immutable prior016/022/025/027 records; no new sampling, acquisition, old error-map replay or old raw-byte validation claimed by this consolidation', terminal_role_target_decisions=sum((v['quality_pass'] + v['quality_fail'] for v in counts.values())), quality_pass_fail_by_role=counts, quality_matched_supported_pt_ddgi_targets=matched, accepted_timing=False, speed_comparison_eligible_for_fixed_rc=False, architecture_promoted=False, lane_m_complete=False, gpu_executed=False, cpu_reference_sampling_executed=False, rows=rows, limitations=['Original DDGI010scores remain superseded; corrected012is explicitly unblinded, not a fresh unseen cohort', 'Fixed RC shared-image observations are diagnostic targets and not PT-equivalent finite budgets', 'One Radeon8060S only; new dynamic/Sponza/representative-device strata and historical direct/timing issues remain open', 'Prior builds/tests and default Renderer runtime not rerun; no active build graph change'])
with (results / '082-m001-static-screen-family-summary.json').open('x') as f:
    json.dump(report, f, indent=2, allow_nan=False)
    f.write('\n')
text = '# M001 static quality screen: PT passes; no accepted competitiveness result\n\n2026-10-24. The original controlled static screen and explicitly unblinded\ncorrected-DDGI continuation now have terminal outcomes for all six H01/H02/H03\nB2/B8targets. [Immutable-report consolidation082](082-m001-static-screen-family-summary.json)\nchecks committed report identities, Git ancestry, identical physical reference\nprovenance/normalization across families and inclusive classifications. It does\nnot rerun old acquisitions, old raw metrics, references or source. New corrected\nDDGI raw/copy/error-map replay079 is independently complete; original PT/RC\nraw replay remains016/022/025/027. Old010scores stay superseded050/051.\n\n|Target|PT first PASS spp|Retained HWRT RC|Vanilla RC|Software RC|Dense RC|Corrected DDGI terminal rung / outcome|\n|---|---:|---|---|---|---|---|\n'
for row in rows:
    z = {x['role']: x for x in row['roles']}
    text += f"|{row['cell']}/{row['transport']}|{z['pixel-pt']['budget']['selected_spp']}|{z['retained-hwrt-rc']['classification']}|{z['vanilla-rc']['classification']}|{z['software-rc']['classification']}|{z['dense-rc']['classification']}|q{z['corrected-ddgi']['budget']['rung']} / {z['corrected-ddgi']['classification']}|\n"
text += "\nAll families use the original admitted16384spp four-seed physical means and\nunchanged inclusive total NRMSE≤5%, indirect NRMSE≤10%, absolute indirect signed\nbias≤5%, with every57,600pixel retained. PT selects the first passing frozen\nlevel, retaining33cases/27losses. Its near10%B2single-seed passes are literal\nthreshold decisions, not robust margins or real-time competitiveness.\n\nFour fixed RC roles retain24losses. Their B2/B8scores share each role's original\nscene image and are not independent native acquisitions or PT-equivalent finite\nbudgets. Vanilla/software/HWRT PFMs are byte-identical; independent cache-free\ndense evaluation also fails. Corrected DDGI retains its complete012ladder\noutcomes at the qualified finite-stage/reset-all boundary, with no retuning on\nold/new quality images. No universal failure mechanism is inferred.\n\n"
text += f"Supported same-quality PT/DDGI targets: {', '.join(matched) or 'none'}. "
text += 'Quality-mismatched branches stop; diagnostic native times and owned allocation\nsizes cannot establish a speed or memory advantage. No accepted statistical\nGPU timing campaign or architecture promotion. An actual same-quality pair would\nstill require a prospectively fixed complete boundary family, process order/count,\nmultiplicity-aware calibration, practical ratio1.20, full costs and owned≤8GiB/\nzero teardown before a speed decision.\n\n**This bounded static screen is complete; Lane M remains active and incomplete.**\nThe incumbent is not promoted on this outcome. Broader prospective dynamic/Sponza/\nrepresentative-device strata, temporal limitations, historical Sponza direct\nrelative-error1.0 and timing uncertainty remain open. Future development must\nkeep this observed cohort as development/diagnostic data and use new preregistered\nheldouts, without changing these outcomes. No more012quality acquisition is selected.\n\nThis consolidation is CPU evidence-only, with exact committed source/evidence\nidentities and unchanged executable/default build graph. Prior tests/builds and\ndefault Renderer runtime regression were not rerun; no runtime regression PASS\nis claimed. No GPU, power/clock/desktop changes, overwrite/retry, CI or promotion.\nRaw data/error maps/tars remain repository/out, with original human/assistant\nattribution preserved. Verification084 records applicable checks.\n'
with (results / '083-m001-static-screen-outcome.md').open('x') as f:
    f.write(text)
print(json.dumps(dict(terminal_role_target_decisions=sum((v['quality_pass'] + v['quality_fail'] for v in counts.values())), quality_pass_fail_by_role=counts, quality_matched_supported_pt_ddgi_targets=matched, input_reports=len(inputs), rows=len(rows), gpu_executed=False, old_raw_metrics_recomputed=False), indent=2))
