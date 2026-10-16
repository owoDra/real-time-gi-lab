#!/usr/bin/env python3
"""Plan 052: full original calibration under a reversible IDE visibility policy."""
from hidden_ide_bulk_pfm_program import program

if __name__=='__main__':
    source, scope, proof = program()
    exec(compile(source, __file__+'#plan052', 'exec'), scope)
