#!/usr/bin/env python3
"""Continue only verified complete own prefixes under the prospective CPU guard."""
import ctypes
from pathlib import Path
from generate_rqmc_oracle import once
from replayed_point_guided_adapter import adapt
from reference_provenance import ROOT, sha

ctypes.CDLL(None).prctl(15, b'n010_budget_q', 0, 0, 0)


def program():
    original, source = adapt('qualify_point_guided_references.py',
        'cb9ce1e58a612cd66e6f2af1492e575b49e8ff3f003b6bef38d6e2112d77cc2e', [
            ('import point_guided_reference_provenance as P', 'import budget_reference_provenance as P', 1)])
    source = once(source, '    resource.setrlimit(resource.RLIMIT_AS, (4*1024**3, 4*1024**3))\n    resource.setrlimit(resource.RLIMIT_CPU, (172800, 172800))',
        '    P.set_limits(prefix, spp, previous)')
    source = once(source, "'cpu_seconds': 172800", "'cpu_seconds': 691200")
    source = once(source, 'Separate ladders for all nine prospectively selected unfinished slots; no view transition or whole-corpus admission',
        'Operational continuation of the same nine ladders; imported complete own prefixes and new resource receipts; no whole-corpus admission')
    source = once(source, "    if a.work.exists() or a.output.exists() or (a.audit_archive and a.audit_archive.exists()):", "    if a.output.exists() or (a.audit_archive and a.audit_archive.exists()):")
    source = once(source, '    a.work.mkdir(parents=True)',
        "    if a.work != P.WORK or not a.work.is_dir():\n        raise ValueError('explicit existing operational root required')\n"
        "    imported_qualifications = P.imported(inputs)\n"
        "    result['operational_transition_sha256'] = sha(P.TRANSITION)\n"
        "    result['imported_qualification_names'] = list(imported_qualifications)")
    source = once(source, '            directory.mkdir()',
        "            if directory.exists():\n"
        "                if selected not in imported_qualifications:\n                    raise ValueError('unexpected existing directory')\n"
        "                if json.loads((directory/'qualification.json').read_text()) != imported_qualifications[selected]:\n                    raise ValueError('imported qualification changed before continuation')\n"
        "                P.verify_reference(directory,cell,vertices,lock['cells'][cell],{},require_eligible=False)\n"
        "            else:\n                directory.mkdir()")
    source = once(source, '            scene_path.write_text(scene.text())',
        "            if scene_path.exists():\n"
        "                if scene_path.read_text() != scene.text():\n                    raise ValueError('imported canonical scene changed')\n"
        "            else:\n                scene_path.write_text(scene.text())")
    source = once(source, "            result['cells'].append(q)",
        "            if selected in imported_qualifications:\n"
        "                q = imported_qualifications[selected]\n"
        "                levels = q['levels']\n"
        "                previous = read(directory/f'n{levels[-1][\"spp\"]}.meta.json', inputs)\n"
        "                manifests = read(directory/f'screen-n{levels[-1][\"spp\"]}.json', inputs)['levels']\n"
        "            result['cells'].append(q)")
    source = once(source, '            for spp in Q.LEVELS:',
        "            remaining = () if q['classification']=='STATISTICALLY_ELIGIBLE' else Q.LEVELS[len(levels):]\n"
        "            for spp in remaining:")
    source = once(source, '                prefix = directory/f\'o.n{spp}\'',
        "                if list(directory.glob(f'o.n{spp}.*')) or list(directory.glob(f'n{spp}.*')):\n"
        "                    raise ValueError('refuse overwriting an unexpected complete or partial level')\n"
        "                prefix = directory/f'o.n{spp}'")
    source = once(source, "                    wall_seconds_diagnostic=time.monotonic()-started)\n                attempt_path.write_text",
        "                    wall_seconds_diagnostic=time.monotonic()-started)\n"
        "                attempt['resource_limits_sha256'] = sha(directory/f'n{spp}.resource-limits.json')\n"
        "                attempt_path.write_text")
    source = once(source, "                    source_commit=result['source_commit'], wall_seconds_diagnostic=attempt['wall_seconds_diagnostic'])",
        "                    source_commit=result['source_commit'], wall_seconds_diagnostic=attempt['wall_seconds_diagnostic'],\n"
        "                    resource_limits_sha256=sha(directory/f'n{spp}.resource-limits.json'))")
    source = once(source, "    inputs = {str(Path(__file__).resolve()): sha(Path(__file__)),",
        "    inputs = {str(Path(__file__).resolve()): sha(Path(__file__)),\n"
        "        " + repr(str(original)) + ': ' + repr(sha(original)) + ',\n'
        "        str(P.PLAN):sha(P.PLAN),")
    return original, source


if __name__ == '__main__':
    original, source = program()
    exec(compile(source, str(original)+'#plan039', 'exec'), {'__name__': '__main__', '__file__': __file__})
