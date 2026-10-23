"""011 CPU expected full output from immutable pre-copy captures."""
import numpy as np
from ddgi_border_audit import border_map, check_atlas


def expected_copy(before, tile, side):
    check_atlas(before, tile, side)  # Reject shape, type and nonfinite inputs.
    out = before.copy()
    m = border_map(tile)
    ys = np.arange(side)[:, None, None] * tile
    xs = np.arange(side)[None, :, None] * tile
    out[:, ys + m[:, 0], xs + m[:, 1], :] = before[:, ys + m[:, 2], xs + m[:, 3], :]
    return out


def check_copy(before, after, tile, side):
    """Raise on any invalid copy, interior change or uncleared pre-copy border."""
    post = check_atlas(after, tile, side)
    expected = expected_copy(before, tile, side)
    m = border_map(tile)
    ys = np.arange(side)[:, None, None] * tile
    xs = np.arange(side)[None, :, None] * tile
    if np.any(before[:, ys + m[:, 0], xs + m[:, 1], :].view('<u4') != 0):
        raise ValueError('Pre-copy border was not freshly cleared +0')
    if not np.array_equal(after.view('<u4'), expected.view('<u4')):
        raise ValueError('Full post-copy atlas differs: corrupt border or altered interior')
    if not post['exact_copy_pass']:
        raise ValueError('Post-copy atlas violates exact SDK border rule')
    return dict(full_copy_exact=True, interior_unchanged=True, pre_border_zero=True,
                complete_components=int(after.size), **post)
