# N007 CPU-only archive inspection

Previous N006 GPU/CPU run artifacts are retained **outside the public Git repo** under the sibling `../gi-lab-old-private/` directory. This is a private evidence location, not a dependency to commit.

From the current `real-time-gi-lab` repository root:

```bash
python3 -m unittest discover -s scripts/research/n007_reference_validity -p 'test_*.py' -v
python3 scripts/research/n007_reference_validity/inspect_archive.py \
  --archive ../gi-lab-old-private
```

The inspector searches for the **original N006 M3b** `p1m3b-moving-rigid-q8-signed/<timestamp>/Q8_control_reference/` capture under the archived repository. It reads the captured `n006-candidate-evidence.json` to locate the two independent CPU PFMs and Q8 GPU PFM. The original M3b failed-summary SHA is checked if its source JSON is present. Multiple candidate captures are **not selected automatically**; the tool lists them and requires `--capture /exact/discovered/Q8_control_reference`.

Default output is **only in the current repository**:
`out/research/n007-reference-validity/p0-m3b-archive-diagnostic.json`.
The private archive is never written to, and no GPU or CPU re-rendering is performed.

If the tool reports no M3b capture, this does **not** imply it never existed. Check whether any PFM was preserved in the archive:

```bash
find ../gi-lab-old-private -type f -name '*.pfm' -print | head -30
```

For other captures, `inspect_hdr.py` supports explicit actual `--reference` PFM paths; placeholder `path/to/reference-a.pfm` is **not** an executable example.

A two-reference historical inspection is a **diagnostic** and intentionally cannot satisfy the four-seed N007 statistical eligibility gate. `statistically_eligible=false` for only two references is expected, not a retrospective change to N006's `invalid-retained` decision. The original archive must remain private; upload only the resulting diagnostic JSON when asking for review.
