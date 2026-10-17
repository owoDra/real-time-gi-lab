#!/usr/bin/env python3
"""Plan079: scope-only repair of isolated generic prefix helper."""
import hashlib
import json
from pathlib import Path
import diagnose_selected_bounce_paths as D

original=Path(__file__).with_name('build_all_split_general_transport.py')
if hashlib.sha256(original.read_bytes()).hexdigest()!='f859ced1322b37bea27c01a705c3a26ac405207c84e319d6a571ffea7647041e':raise ValueError('original078 driver differs')
D.checked(original);D.checked(D.RESULTS.parent/'experiments/078-all-split-general-transport-and-prefix-reuse.md')
failed=json.loads(D.checked(D.RESULTS/'222-all-split-general-transport-equivalence.json'))
if failed['complete'] or len(failed['attempts'])!=1 or failed['attempts'][0]['returncode']==0:raise ValueError('actual222 compile failure required')
for p,h in failed['payload_sha256'].items():D.checked(Path(p),h)
base=D.checked(D.HERE/'all_split_general_transport.inc').decode()
revised=D.checked(D.HERE/'all_split_general_transport_repaired.inc').decode()
for a,b in [('        return log_density;\n\n    void whole_density_prefixes(', '        return log_density;\n    }\n\n    void whole_density_prefixes('), ('        if(endpoint)*endpoint=current;\n\n    }\n    }\n\n    static void whole_check_density', '        if(endpoint)*endpoint=current;\n\n    }\n\n    static void whole_check_density')]:base=D.once(base,a,b)
if base!=revised:raise ValueError('scope repair has other edits')
source=original.read_text()
for a,b in (
 ('all-split-general-transport-v1','all-split-general-transport-v2'),
 ('222-all-split-general-transport-equivalence.json','223-all-split-general-transport-equivalence.json'),
 ('078-all-split-general-transport-and-prefix-reuse.md','079-general-prefix-helper-scope-repair.md'),
 ('all_split_general_transport.inc','all_split_general_transport_repaired.inc')):
 source=D.once(source,a,b) if a!='all_split_general_transport.inc' else source.replace(a,b)
exec(compile(source,str(original)+'#plan079','exec'),{'__name__':'__main__','__file__':__file__})
