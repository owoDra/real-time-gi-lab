#!/usr/bin/env python3
"""Plan092: strict inverse environment-only dispatch of original091 CPU profile."""
import hashlib
from pathlib import Path

BASE = Path(__file__).with_name('profile_original_all_split_cpu.py')
EXPECTED = '39388ab12b7cae67b05bf41bc2e1576cab53aaf153e1e6691cdc876a0c7c9b33'
source = BASE.read_text()
if hashlib.sha256(BASE.read_bytes()).hexdigest() != EXPECTED:
    raise ValueError('sealed091 driver changed')
edits = [
    ("original-all-split-cpu-profile-v1", "original-all-split-cpu-profile-local-linker-v1"),
    ("239-original-all-split-cpu-profile.json", "240-original-all-split-cpu-profile-local-linker.json"),
    ("091-original-all-split-cpu-profile.md", "092-cpu-profile-local-linker-dispatch.md"),
    ("(Path(__file__).resolve(), PLAN, Path(D.__file__), PERF,", "(Path(__file__).resolve(), BASE, PLAN, Path(D.__file__), PERF,"),
    ("perf_version=subprocess.check_output([str(PERF), '--version'], text=True).strip(),",
     "perf_version=subprocess.check_output([str(PERF), '--version'], text=True, env={k:v for k,v in os.environ.items() if k != 'LD_LIBRARY_PATH'}).strip(),"),
    ("env = dict(os.environ, DEBUGINFOD_URLS='', PERF_PAGER='cat')",
     "env = dict(os.environ, DEBUGINFOD_URLS='', PERF_PAGER='cat')\n    env.pop('LD_LIBRARY_PATH', None)"),
]
revised = source
for old, new in edits:
    if revised.count(old) != 1:
        raise ValueError('nonunique dispatch edit')
    revised = revised.replace(old, new)
inverse = revised
for old, new in reversed(edits):
    if inverse.count(new) != 1:
        raise ValueError('nonunique inverse edit')
    inverse = inverse.replace(new, old)
if inverse != source:
    raise ValueError('dispatch inverse differs')
exec(compile(revised, str(BASE), 'exec'), globals())
