# G001 — Memory ownership and lifetime census

Status: **complete**

## Frozen question

Explain the F007 transient-LBVH sparse peak-memory failures before making any
memory optimization:

- sparse-stress: 3.0836x run-local vanilla;
- sparse-moving: 3.2025x run-local vanilla.

## Outcome

Accepted target-GPU evidence at
`0fcd6bce9576be5fdc708e434991b811e88cc74c` reproduces both anchors
byte-accurately.

The dominant cause is static HWRT ownership/lifetime, not the transient LBVH.
The complete moving-set LBVH allocation is only 232,960 B. Static HWRT retains
approximately 46 MiB of setup-only build input/scratch across runtime lifetime.

No G001 memory optimization was performed.

See `results/001-memory-ownership-lifetime-census.md` for the byte ownership
and lifetime breakdown.

G002 may now begin. G003 remains blocked until G002 freezes a decision-valid
timing protocol.
