# Lane N — end-to-end renderer integration

Issue: #26  
Canonical branch: `research-lane-n-end-to-end-renderer`  
Base: `research@a75cf7857761cfbc783c9f1f847dc1380359481e`

Status: **N001 in progress — GPU-independent renderer/reference contract prepared**.

Lane N is the first image-producing end-to-end lane. It preserves the accepted
A–M architecture decisions from `research/status.md` and measures the complete
renderer boundary before any new transport feature is added.

Current work is N001 renderer/reference bring-up. No architecture performance
winner is selected in N001. Temporal reuse, leak mitigation, multi-bounce
extensions, glossy/specular transport, and denoising are explicitly out of
scope until the weakness atlas is measured.

The N001 GPU-independent contract lives in
`experiments/001-n001-config.json` and
`scripts/research/lane_n_end_to_end_renderer/n001_contract.py`.
Raw target artifacts must remain under `out/research/`.
