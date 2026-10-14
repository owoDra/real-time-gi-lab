# Post-hoc replay of the retained point-guided physical controls

Result 113 is terminal FAIL: after all seventeen native acquisitions and export
checks passed, the analytic replay adapter accessed `geometry_hash_match`, which
its metadata wrapper had not supplied. No analytic or independent iid gate ran.
Keep 113, its runner, logs and every acquired payload unchanged.

Perform a new CPU-only analysis of those exact retained outputs. Recheck all
113 frozen inputs and native payload hashes, all four seed/sidecar headers,
finite nonnegative means/moments, exact direct/emission and primary records,
and null-sample bounds. Derive the missing `name` and `geometry_hash_match`
fields exactly as the original `validate_sampler.render` wrapper does, by
comparing actual geometry metadata with the independently constructed scene.
Do not assign an unconditional geometry PASS.

Replay the exact existing eight physical controls and two 16384-spp iid
comparisons from the pinned 113 runner. No rendering, altered counts, masks,
threshold changes, selected successes, or discarded failed checks are allowed.
Record original acquisition commands as historical commands, never as commands
executed by this replay. Record the analysis source, adapter, original result,
all read bytes and their unchanged hashes after analysis. Refuse existing
outputs. A complete replay PASS could replace the failed analysis dependency
only in a separately identified future proof chain; 113 must remain FAIL.
No reference or N010 readiness follows from physical replay alone.
