#!/usr/bin/env python3
"""Plan 056: bounded two-level feasibility; no corpus reference admission."""
from pathlib import Path
from nested_scramble_programs import program

if __name__=='__main__':
    source,scope,proof = program('feasibility',Path(__file__).resolve())
    exec(compile(source,__file__+'#plan056','exec'),scope)
