# G002b — paired counterbalanced repeatability validation

Status: **pending target-GPU evidence**

This remains part of G002. It is not a G003 optimization or decision run.

The first G002 campaign rejected the F007 one-shot timing protocol and showed
that longer warmup alone does not remove the instability. G002b tests adjacent
candidate/comparator measurements in counterbalanced blocks, retaining every
measurement.

See `002b-paired-counterbalanced-config.json` for the frozen matrix and
repeatability criteria.
