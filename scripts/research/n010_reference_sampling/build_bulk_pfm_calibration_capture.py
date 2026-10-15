#!/usr/bin/env python3
"""Plan 048: isolated row-bulk PFM fixture, no GPU dispatch."""
from pathlib import Path
from bulk_pfm_capture_programs import build_program

if __name__ == '__main__':
    source, scope = build_program()
    scope.update(__name__='__main__', __file__=str(Path(__file__).resolve()))
    exec(compile(source, __file__+'#plan048', 'exec'), scope)
