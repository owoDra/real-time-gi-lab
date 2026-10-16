#!/usr/bin/env python3
"""Plan 056: all 24 original state and exact own-prefix controls."""
from pathlib import Path
from nested_scramble_programs import program

if __name__=='__main__':
    source,scope,proof = program('prefix',Path(__file__).resolve())
    exec(compile(source,__file__+'#plan056','exec'),scope)
