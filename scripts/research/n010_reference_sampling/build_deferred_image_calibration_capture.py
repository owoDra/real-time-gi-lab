#!/usr/bin/env python3
"""Plan 054: build isolated bounded CPU image-spooling fixture; no GPU dispatch."""
from pathlib import Path
from deferred_image_capture_programs import build_program

if __name__=='__main__':
    source,scope = build_program()
    scope.update(__name__='__main__',__file__=str(Path(__file__).resolve()))
    exec(compile(source,__file__+'#plan054','exec'),scope)
