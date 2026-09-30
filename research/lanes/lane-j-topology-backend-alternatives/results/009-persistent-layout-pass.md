# J003 persistent physical-slot all-profile replay result

Status: **PASS — promote to persistent Vulkan buffers**

The frozen J002 topology profiles were replayed through the v1.3 persistent
physical-slot layout.

## Gate result

All five profiles completed without:

- logical/physical ownership leaks;
- physical-slot collisions;
- invalid persistent occupancy;
- upper-hierarchy structural failure;
- capacity-policy violation.

## Observed profile behavior

### small-global-high

- initial slot capacity: 4;
- active clusters: 3..4;
- resize count: 0;
- total dirty-slot updates: 27;
- upper refit path exercised: 5 nodes;
- total upper rebuild nodes: 41;
- persistent logical bytes: 41,296.

### medium-global-representative

- slot capacity: 32;
- active clusters: 15..25;
- resize count: 0;
- total dirty-slot updates: 158;
- upper refit nodes: 0;
- total upper rebuild nodes: 308;
- persistent logical bytes: 330,704.

### medium-local-high

- slot capacity: 32;
- active clusters: 15..25;
- resize count: 0;
- total dirty-slot updates: 149;
- clean-cluster retention is exercised: several transitions have
  dirty-slot count below active-cluster count;
- total upper rebuild nodes: 302;
- persistent logical bytes: 330,704.

### large-global-high

- initial slot capacity: 256;
- step 1 grows to 512 physical slots;
- resize count: 1;
- old persistent logical bytes: 2,645,968;
- new persistent logical bytes: 5,291,984;
- simultaneous old/new resize overlap: **7,937,952 bytes**;
- total dirty-slot updates: 1,586;
- total upper rebuild nodes: 3,164.

### large-local-high

- slot capacity remains 256;
- active clusters: 138..231;
- resize count: 0;
- total dirty-slot updates: 1,343;
- dirty-slot counts remain below active counts on multiple transitions,
  confirming locality preservation in the physical layout;
- total upper rebuild nodes: 3,010;
- persistent logical bytes: 2,645,968.

## Interpretation

The frozen slot policy behaves as intended on the complete topology campaign:

- global churn can force capacity growth;
- local churn preserves clean physical slots;
- resize overlap is explicitly representable;
- physical ownership returns to the active logical set after merge/retire;
- both upper rebuild and refit paths are reachable.

These are host-layout results only. They do not establish actual Vulkan
allocation sizes, actual device-resident true peak, GPU upload correctness, or
transition-time exact Hit correctness.

## Promotion

Proceed to persistent Vulkan buffers with the same fixed slot policy:

1. allocate triangle / micro-node / cluster / upper buffers from slot capacity;
2. upload only dirty triangle and micro-node slot ranges;
3. upload changed cluster metadata;
4. upload upper nodes according to rebuild/refit scope;
5. on capacity growth, retain old buffers through migration completion and
   report actual Vulkan allocation overlap;
6. replay exact GPU Hits after every frozen transition;
7. keep validation ray/hit buffers outside candidate persistent memory.

No J004 ranking is permitted.
