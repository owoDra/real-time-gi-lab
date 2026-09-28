# Experiment B001 — traversal contract and comparable controls

Status: planned

## Question

Can StrataBrick, a simple software traversal baseline, and hardware RT/TLAS
(where available) be compared under one semantic ray contract without hiding
their maintenance costs?

## Hypothesis

StrataBrick may reduce dynamic maintenance or practical GI-range traversal cost
in some scene regimes, but this must be demonstrated against simpler and
hardware baselines rather than assumed.

## Protocol

- Define one `traceRay(origin, direction, tMax) -> Hit` semantic contract.
- Establish a shared correctness/reference path.
- Bring up the simplest software baseline first.
- Bring up StrataBrick/derived traversal second.
- Add hardware RT/TLAS when supported and semantically comparable.
- Use clearly labeled GI-like control rays for bring-up only.
- Measure build/refit/rebuild/update, trace time, and memory separately and
  end-to-end.
- Cover static/dynamic, sparse/dense, vertical, and practical 50m/200m-style
  ranges where appropriate.

## Correctness gate

Hit/miss, distance, identity/material information required by the contract must
match the reference within explicit tolerances.

## Decision gate

Do not promote a traversal architecture from control rays alone. A provisional
candidate may advance, but the final decision must be repeated on Lane A's
representative producer stream.
