#!/usr/bin/env python3
"""Repository consistency check: relative Markdown links resolve and every
file listed in legacy/README.md exists. Not a build or runtime validation."""
from pathlib import Path
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
LINK = re.compile(r'\[[^\]]*\]\(([^)\s]+)\)')
MANIFEST = re.compile(r'`([\w./-]+)`')


def tracked_markdown():
    out = subprocess.run(['git', 'ls-files', '-co', '--exclude-standard', '*.md'],
                         cwd=ROOT, capture_output=True, text=True, check=True).stdout
    return [ROOT / p for p in out.splitlines() if (ROOT / p).exists() and not p.startswith('.claude/')]


def check_links(errors):
    count = 0
    for md in tracked_markdown():
        text = re.sub(r'```.*?```', '', md.read_text(encoding='utf-8'), flags=re.S)
        for target in LINK.findall(text):
            if re.match(r'[a-z]+:', target) or target.startswith('#'):
                continue
            count += 1
            path = (md.parent / target.split('#', 1)[0]).resolve()
            if not path.exists():
                errors.append(f'{md.relative_to(ROOT)}: broken link {target}')
    return count


def check_legacy(errors):
    count = 0
    legacy = ROOT / 'legacy'
    first_columns = [line.split('|')[1] for line in (legacy / 'README.md').read_text(encoding='utf-8').splitlines()
                     if line.startswith('| `')]
    for cell in first_columns:
        directory = legacy
        for name in MANIFEST.findall(cell):
            # A bare file name continues in the directory of the previous entry in the same cell.
            path = legacy / name if '/' in name else directory / name
            if '/' in name:
                directory = path if name.endswith('/') else path.parent
            count += 1
            if not path.exists():
                errors.append(f'legacy/README.md: missing {path.relative_to(ROOT)}')
    return count


def main():
    errors = []
    links = check_links(errors)
    entries = check_legacy(errors)
    for error in errors:
        print(error)
    print(f'check: {"FAIL" if errors else "OK"} ({links} relative links, {entries} legacy entries; not a build or runtime validation)')
    return 1 if errors else 0


if __name__ == '__main__':
    sys.exit(main())
