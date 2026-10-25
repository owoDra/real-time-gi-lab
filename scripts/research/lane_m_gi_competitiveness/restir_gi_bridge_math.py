"""033 independent analytic fixture math, not an SDK shader implementation."""
import math


def dot(a, b): return math.fsum(x*y for x, y in zip(a, b))
def sub(a, b): return tuple(x-y for x, y in zip(a, b))


def direction(a, b):
    delta = sub(b, a); norm = math.sqrt(dot(delta, delta))
    if not math.isfinite(norm) or norm <= 0: raise ValueError('invalid segment')
    return tuple(x/norm for x in delta)


def target(position, normal, endpoint, radiance):
    if not math.isfinite(radiance) or radiance < 0: raise ValueError('physical radiance')
    return max(0., dot(normal, direction(position, endpoint)))*radiance/math.pi


def raw_weight(pdf):
    if not math.isfinite(pdf) or pdf < 0: raise ValueError('physical PDF')
    return 1/pdf if pdf else 0.


def no_resampling(position, normal, endpoint, radiance, pdf):
    return target(position, normal, endpoint, radiance)*raw_weight(pdf)


def ris_exact_expectation(radiances, pdfs, targets):
    """Enumerate final sample probabilities, including black candidates in M."""
    if not (len(radiances) == len(pdfs) == len(targets) > 0): raise ValueError('coverage')
    weights = [t*raw_weight(p) for p, t in zip(pdfs, targets)]
    if any(not math.isfinite(x) or x < 0 for x in [*radiances, *targets]): raise ValueError('physical values')
    total = math.fsum(weights)
    if total == 0: return 0.
    return math.fsum(w/total*(r*total/(len(weights)*t)) for r, w, t in zip(radiances, weights, targets) if t > 0)


def jacobian(receiver, original_receiver, endpoint, endpoint_normal):
    def partial(p):
        v = sub(p, endpoint); squared = dot(v, v)
        if squared <= 0 or not math.isfinite(squared): return 0., squared
        return min(1., max(0., dot(endpoint_normal, tuple(x/math.sqrt(squared) for x in v)))), squared
    new_cos, new_d2 = partial(receiver); old_cos, old_d2 = partial(original_receiver)
    if old_cos <= 0 or new_d2 <= 0: return 0.
    j = new_cos*old_d2/(old_cos*new_d2)
    return j if math.isfinite(j) else 0.


def validate_jacobian(j):
    if not math.isfinite(j) or j < .1 or j > 10: return False, j
    return True, min(3., max(1/3, j))


def visible_plane(start, end):
    """Only033 synthetic bounded z=.5 square; never a production BVH bridge."""
    dz = end[2]-start[2]
    if abs(dz) < 1e-12: return True
    t = (.5-start[2])/dz
    p = tuple(a+t*(b-a) for a, b in zip(start, end))
    return not (1e-6 < t < 1-1e-6 and abs(p[0]) < .25 and abs(p[1]) < .25)


def oriented_support(receiver, endpoint, endpoint_normal):
    return dot(sub(receiver, endpoint), endpoint_normal) > 0


def remaining_vertices(depth):
    if depth not in (2, 8): raise ValueError('unregistered finite boundary')
    return tuple(range(1, depth))


def similar(a, b, normal_threshold=.6, depth_threshold=.1):
    return a['valid'] and b['valid'] and a['material'] == b['material'] and dot(a['normal'], b['normal']) >= normal_threshold and abs(a['depth']-b['depth']) <= depth_threshold*max(a['depth'], b['depth'])
