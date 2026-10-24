"""029 fixed surface incident-direction control variate; CPU only."""
import numpy as np

TRAIN = 8
FRAMES = 64
RIDGE = 1e-3


def need(ok, message):
    if not ok:
        raise ValueError(message)


def unit_vectors(v):
    v = np.asarray(v, dtype=np.float64)
    need(v.ndim >= 2 and v.shape[-1] == 3 and np.isfinite(v).all(), '029 invalid vector array')
    length = np.linalg.norm(v, axis=-1, keepdims=True)
    need((length > 0).all(), '029 zero direction')
    return v / length


def basis(direction):
    w = unit_vectors(direction)
    x, y, z = np.moveaxis(w, -1, 0)
    return np.stack((np.ones_like(x), x, y, z, x*y, y*z, z*x, x*x-y*y, 3*z*z-1), axis=-1)


def moments(normal):
    n = unit_vectors(normal)
    x, y, z = np.moveaxis(n, -1, 0)
    return np.stack((np.ones_like(x), 2*x/3, 2*y/3, 2*z/3, x*y/4, y*z/4,
                     z*x/4, (x*x-y*y)/4, (3*z*z-1)/4), axis=-1)


def partition(origin, normal, active, owner, material, vertices, metadata):
    origin = np.asarray(origin, dtype=np.float64)
    normal = np.asarray(normal, dtype=np.float64)
    need(active.ndim == 1 and active.dtype == np.bool_ and active.any(), '029 invalid active domain')
    size = len(active)
    need(origin.shape == normal.shape == (size, 3) and np.isfinite(origin).all()
         and np.isfinite(normal).all(), '029 invalid primary geometry')
    need(owner.shape == material.shape == (size,) and owner.dtype.kind == material.dtype.kind == 'u',
         '029 invalid opaque ownership')
    need(vertices.ndim == 3 and vertices.shape[1:] == (3, 3) and np.isfinite(vertices).all()
         and metadata.shape == (len(vertices), 4) and metadata.dtype.kind == 'u', '029 invalid full geometry')
    ids = np.flatnonzero(active)
    normals = unit_vectors(normal[active])
    cells = np.zeros((len(ids), 3), dtype=np.int64)
    bounds = []
    for value in np.unique(owner[active]):
        triangles = vertices[metadata[:, 2] == value]
        need(len(triangles) > 0, '029 owner absent from full geometry')
        lo = triangles.min(axis=(0, 1)); hi = triangles.max(axis=(0, 1))
        extent = np.where(hi > lo, hi-lo, 1.)
        mask = owner[active] == value
        cells[mask] = np.clip(np.floor(8*(origin[active][mask]-lo)/extent), 0, 7).astype(np.int64)
        bounds.append(np.r_[float(value), lo, hi])
    keys = np.column_stack((owner[active].astype(np.int64), material[active].astype(np.int64),
                            np.rint(1024*normals).astype(np.int64), cells))
    unique, inverse = np.unique(keys, axis=0, return_inverse=True)
    groups = np.full(size, -1, dtype=np.int64); groups[ids] = inverse
    safe_normal = np.zeros((size, 3)); safe_normal[:, 2] = 1.; safe_normal[active] = normals
    return dict(keys=unique, groups=groups, normal=safe_normal, active=active.copy(), bounds=np.array(bounds))


def train(features, values, groups, count):
    need(features.ndim == 3 and features.shape[0] == TRAIN and features.shape[2] == 9
         and values.shape == features.shape[:2] and groups.shape == (features.shape[1],), '029 training split/shape')
    need(np.isfinite(features).all() and np.isfinite(values).all() and (values >= 0).all(), '029 invalid training values')
    need(groups.dtype.kind in 'iu' and (groups >= -1).all() and count > 0
         and set(groups[groups >= 0]) == set(range(count)), '029 missing training group')
    coefficients = np.empty((count, 9)); grams = np.empty((count, 9, 9))
    rhs = np.empty((count, 9)); lambdas = np.empty(count); samples = np.empty(count, dtype=np.int64)
    for group in range(count):
        mask = groups == group
        x = features[:, mask].reshape(-1, 9); y = values[:, mask].ravel()
        gram = x.T @ x; b = x.T @ y; lam = RIDGE * np.trace(gram)/9
        need(np.isfinite(lam) and lam > 0, '029 invalid ridge scale')
        coefficients[group] = np.linalg.solve(gram+lam*np.eye(9), b)
        grams[group] = gram; rhs[group] = b; lambdas[group] = lam; samples[group] = len(y)
    need(np.isfinite(coefficients).all(), '029 nonfinite fitted field')
    return dict(coefficients=coefficients, gram=grams, rhs=rhs, lambdas=lambdas, training_samples=samples)


def correction(features, mu, coefficients, groups):
    need(features.ndim == 3 and features.shape[2] == 9 and mu.shape == features.shape[1:]
         and groups.shape == (features.shape[1],) and coefficients.ndim == 2
         and coefficients.shape[1] == 9, '029 invalid correction shape')
    need(np.isfinite(features).all() and np.isfinite(mu).all() and np.isfinite(coefficients).all()
         and ((groups >= -1) & (groups < len(coefficients))).all(), '029 invalid correction field')
    c = coefficients[np.maximum(groups, 0)].copy(); c[groups < 0] = 0
    result = np.einsum('fpk,pk->fp', mu[None]-features, c)
    need(np.isfinite(result).all(), '029 nonfinite signed correction')
    return result


def aggregate(raw, corrected):
    need(raw.ndim == 2 and raw.shape[0] == FRAMES and corrected.shape == raw[TRAIN:].shape,
         '029 complete64/8/56 split required')
    need(np.isfinite(raw).all() and (raw >= 0).all() and np.isfinite(corrected).all(), '029 nonfinite samples')
    baseline = raw.sum(axis=0)/FRAMES
    signed = (raw[:TRAIN].sum(axis=0)+corrected.sum(axis=0))/FRAMES
    t = float(raw[:TRAIN].var(axis=0, ddof=1).sum())
    r = float(raw[TRAIN:].var(axis=0, ddof=1).sum())
    s = float(corrected.var(axis=0, ddof=1).sum())
    numerator = TRAIN*t+(FRAMES-TRAIN)*r; denominator = TRAIN*t+(FRAMES-TRAIN)*s
    need(np.isfinite([t, r, s, numerator, denominator]).all() and min(t, r, s, numerator, denominator) > 0,
         '029 undefined empirical variance ratio')
    return dict(baseline=baseline, signed=signed, clipped=np.maximum(signed, 0)), dict(
        training_variance=t, raw_evaluation_variance=r, corrected_evaluation_variance=s,
        ratio=numerator/denominator, variance_pass=bool(numerator/denominator >= 1.20))
