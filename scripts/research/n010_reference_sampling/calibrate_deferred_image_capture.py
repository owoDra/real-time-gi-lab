#!/usr/bin/env python3
"""Plan 054: original full calibration with CPU PFM writes after each sequence."""
from pathlib import Path
from deferred_image_calibration_program import program

if __name__=='__main__':
    source,scope,proof = program(Path(__file__).resolve())
    exec(compile(source,__file__+'#plan054','exec'),scope)
