#!/usr/bin/env python3
"""Plan146: terminal-control scheduling for the unchanged private PT fixture."""
from pathlib import Path

import build_history_known_work as B

PARENT_SHA = '3b68aadf903825fef9336337f4039480b992f61cc4f3a5190da48791b4ba9274'
PLAN = B.RESULTS.parent/'experiments/146-known-work-build-terminal-scheduling.md'


def program():
    original = B.checked(Path(B.__file__).resolve(), PARENT_SHA).decode()
    source, edits = original, []

    def change(before, after):
        nonlocal source
        if source.count(before) != 1 or after in source:
            raise ValueError('nonunique terminal-scheduling source edit')
        source = source.replace(before, after, 1)
        edits.append((before, after))

    change("PLAN=RESULTS.parent/'experiments/135-bounded-history-known-work.md'",
           "PLAN=RESULTS.parent/'experiments/146-known-work-build-terminal-scheduling.md'")
    change("OUTPUT=RESULTS/'431-history-known-work-build.json'",
           "OUTPUT=RESULTS/'502-history-known-work-build-terminal-control.json'")
    change("    if not control['complete'] or not control['seed_integrity_pass']:\n"
           "        raise ValueError('terminal integrity-PASS261 required; no waiting or compiler queue')",
           """    if (control['classification'] != 'ORIGINAL_FULL_SPHERE_SEED_FAILURE_PARTIALS_RETAINED'
            or control['returncode'] != -6 or control['complete'] or control['seed_integrity_pass']):
        raise ValueError('exact retained terminal261 failure required; no reclassification')
    for group in ('input_sha256', 'payload_sha256'):
        for name, digest in control[group].items():checked(name, digest)
    for filename in ('483-compensated-sealed-dark-full-control.json',
                     '484-compensated-sealed-lit-full-control.json'):
        terminal = json.loads(checked(RESULTS/filename))
        if not (terminal['complete'] and terminal['all_pass'] and terminal['terminal_identity_verified']):
            raise ValueError('both candidate sealed natives must terminate and pass before compilation')
        for group in ('input_sha256', 'payload_sha256'):
            for name, digest in terminal[group].items():checked(name, digest)
    if (RESULTS/'431-history-known-work-build.json').exists():
        raise ValueError('old431 must remain unexecuted; separate502 only')
    B.quiet()  # Actual /proc quiescence, not merely a saved terminal flag.
""")
    restored = source
    for before, after in reversed(edits):
        if restored.count(after) != 1:
            raise ValueError('terminal-scheduling source inverse count differs')
        restored = restored.replace(after, before, 1)
    if restored != original:
        raise ValueError('complete original builder source inverse differs')
    return source, dict(parent_sha256=PARENT_SHA, whole_original_builder_inverse_exact=True,
                       edits=[dict(before=a, after=b) for a, b in edits])


def main():
    source, inverse = program()
    scope = dict(__name__='n010_terminal_scheduling_builder', __file__=str(Path(__file__).resolve()))
    exec(compile(source, str(Path(B.__file__).resolve())+'#plan146', 'exec'), scope)
    return scope['main']()


if __name__ == '__main__':
    raise SystemExit(main())
