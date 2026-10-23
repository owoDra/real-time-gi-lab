#!/usr/bin/env python3
"""013 reversible private shader overlay; historical sources stay immutable."""
from pathlib import Path
import hashlib

ROOT = Path(__file__).resolve().parents[3]
SOURCE = ROOT / 'shaders/research/lane_n_end_to_end_renderer'
PINS = {
    'n001_primary.comp.glsl': '90c995c5d56ef7754b22905955b545b210f28eaf37a22fe136b115fdac216fda',
    'n003_primary_software.comp.glsl': 'a85abf20fdf4a6c21538da2fb344178cde34f1ab935b1facc981a7769490779e',
}
CONSTANTS = 'const float HIT_ABS_TOL = 2.0e-4;\nconst float HIT_REL_TOL = 2.0e-5;\n'
OLD_ORDER = '''    float tolerance = max(HIT_ABS_TOL, abs(best_t) * HIT_REL_TOL);
    return t < best_t - tolerance ||
        (abs(t - best_t) <= tolerance && primitive < best_primitive);'''
NEW_ORDER = '''    return t < best_t || (t == best_t && primitive < best_primitive);'''
OLD_BOUND = '''    float tolerance = max(HIT_ABS_TOL, abs(best_t) * HIT_REL_TOL);
    if (t < RAY_T_MIN || t > ray_tmax || t > best_t + tolerance) return false;'''
NEW_BOUND = '''    if (t < RAY_T_MIN || t > ray_tmax || t > best_t) return false;'''


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def once(text, old, new):
    if text.count(old) != 1:
        raise ValueError('Pinned primary source drift: ' + old[:60])
    return text.replace(old, new)


def overlay(raw):
    if hashlib.sha256(raw).hexdigest() not in PINS.values():
        raise ValueError('Unregistered original primary source')
    text = raw.decode()
    for old, new in ((CONSTANTS, ''), (OLD_ORDER, NEW_ORDER), (OLD_BOUND, NEW_BOUND)):
        text = once(text, old, new)
    # Inverse reconstructs the constants at their original unambiguous anchor.
    restored = once(text, NEW_BOUND, OLD_BOUND)
    restored = once(restored, NEW_ORDER, OLD_ORDER)
    restored = once(restored, 'const float RAY_T_MIN = 1.0e-4;\n',
                    'const float RAY_T_MIN = 1.0e-4;\n' + CONSTANTS)
    if restored.encode() != raw or 'HIT_ABS_TOL' in text or 'HIT_REL_TOL' in text:
        raise ValueError('Primary overlay inverse is not exact')
    return text.encode()


def selection_function(raw):
    text = raw.decode()
    start = text.index('bool prefer_hit(')
    return text[start:text.index('\n}', start) + 2]
