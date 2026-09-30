# Lane J scripts

GPU-independent preparation:

```bash
mise exec -- python -m unittest discover   -s scripts/research/lane_j_topology_backend_alternatives   -p 'test_*.py'

mise exec -- python   scripts/research/lane_j_topology_backend_alternatives/run_j002_prepare.py   --producer-stream /path/to/accepted/A001/stream-v1.bin

mise exec -- python   scripts/research/lane_j_topology_backend_alternatives/run_j002_materialize.py   --scene assets/Vulkan-Samples-Assets/scenes/sponza/Sponza01.gltf   --producer-stream /path/to/accepted/A001/stream-v1.bin   --artifact-dir out/research/lane-j-topology-backend-alternatives/002-deterministic-topology-contract/materialized

mise exec -- python   scripts/research/lane_j_topology_backend_alternatives/run_j003_cpu_gates.py   --j002-artifact-dir out/research/lane-j-topology-backend-alternatives/002-deterministic-topology-contract/materialized
```

The materializer deliberately requires the accepted A001 natural append stream;
it does not synthesize or reorder producer work. It reproduces B002 glTF
triangle ordering, requires the historical 796-triangle representative object,
and emits exact binary geometry snapshots for all frozen J002 transitions.

After the CPU structural gates pass, the next work is the target-GPU J003
backend implementation/validation. Formal timing remains blocked by Lane I.
