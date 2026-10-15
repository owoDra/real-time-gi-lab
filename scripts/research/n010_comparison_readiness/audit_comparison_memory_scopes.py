#!/usr/bin/env python3
"""Separate current linked-source evidence from historical pilot identities."""
from pathlib import Path
from reference_provenance import sha
from generate_rqmc_oracle import once

original = Path(__file__).with_name('audit_comparison_memory_boundary.py').resolve()
if sha(original) != 'ebb8f4ae6386b503cb7c413576335b3dbbb84e12af58ee689c3b1becc8ea4b7c':
    raise ValueError('retained strict audit source changed')
source = original.read_text()
source = once(source, 'Path(__file__).with_name(\'generate_memory_hooks.py\')):',
    'Path(__file__).with_name(\'generate_memory_hooks.py\'), '+repr(original)+'):')
# repr(Path) is not a source literal without the concrete class import.
source = source.replace(repr(original), 'Path('+repr(str(original))+')')
source = once(source, "'classification': 'POST_HOC_LINKED_SOURCE_AND_RETAINED_LEDGER_AUDIT_ONLY'",
    "'classification': 'POST_HOC_DISTINCT_CURRENT_SOURCE_AND_RETAINED_LEDGER_SCOPES'")
source = once(source, "'inputs': inputs, 'linked_targets': [], 'pilot_rows': [], 'unsupported_rows': [],",
    "'inputs': inputs, 'linked_targets': [], 'pilot_rows': [], 'unsupported_rows': [], 'current_sizing_rows': [],")
source = once(source,
    "                if binary is None or row['binary_sha256'] != sha(binary):\n                    raise ValueError('retained pilot differs from frozen comparison executable')",
    "                if binary is None:\n                    raise ValueError('retained pilot executable not in declared comparison family')\n"
    "                binary_is_current = row['binary_sha256'] == sha(binary)")
source = once(source, "'ledger_sha256':sha(ledger_path),'event_count':len(raw['events']),",
    "'ledger_sha256':sha(ledger_path),'binary_matches_current':binary_is_current,'event_count':len(raw['events']),")
extra = '''        sizing = read(RESULTS/'035-calibration-observable-sizing.json',inputs)
        if not sizing['complete'] or not sizing['all_pass'] or len(sizing['rows']) != 16:
            raise ValueError('current-boundary diagnostic sizing incomplete')
        for row in sizing['rows']:
            e = row['evidence']
            command = e['command']
            binary = next((BUILD/t for t in TARGETS if str(BUILD/t) in command),None)
            if (binary is None or e['binary_sha256'] != sha(binary)
                    or e['shader_sha256'] != driver['shader_sha256'] or e['returncode']):
                raise ValueError('sizing evidence differs from current frozen executable/shaders')
            directory = Path(command[command.index('--out')+1])
            if not directory.is_absolute():
                directory = ROOT/directory
            raw = read(directory/'allocation-ledger.json',inputs)
            if raw != e['allocation_ledger'] or not replay(raw):
                raise ValueError('current-boundary retained memory mismatch/replay failure')
            result['current_sizing_rows'].append({'boundary':row['boundary'],
                'binary_sha256':e['binary_sha256'],'shader_sha256':e['shader_sha256'],
                'ledger_sha256':sha(directory/'allocation-ledger.json'),
                'event_count':len(raw['events']),
                'device_contexts':sorted({v['device_context'] for v in raw['events']}),
                'true_peak_owned_bytes':raw['true_peak_owned_bytes'],
                'teardown_zero':True,'pass':True,'accepted_timing':False})
        result['historical_pilot_rows_not_matching_current_binary'] = sum(
            not r['binary_matches_current'] for r in result['pilot_rows'])
        result['current_binary_pilot_rows'] = sum(r['binary_matches_current'] for r in result['pilot_rows'])
        result['historical_pilots_attested_as_current_binary'] = False
        result['accepted_calibration_claimed'] = False
        if len(result['pilot_rows']) != 76 or len(result['unsupported_rows']) != 1:'''
source = once(source, "        if len(result['pilot_rows']) != 76 or len(result['unsupported_rows']) != 1:",extra)
exec(compile(source,str(original)+'#separate-scopes','exec'),{'__name__':'__main__','__file__':__file__})
