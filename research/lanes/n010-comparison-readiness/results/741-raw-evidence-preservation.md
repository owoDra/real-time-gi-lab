# Raw evidence preservation during project pause (2026-10-19)

## User request and scope

The user asked what happens if raw data is lost and whether it can be recorded.
The project remains **PAUSED; N010 NOT_READY / INCOMPLETE**. This operation only
inventories existing files and preserves an existing archive; it performs no
scientific acquisition, diagnosis or change to accepted evidence.

Committed summaries, source/configuration and hashes survive a local disk loss
when pushed, but **hashes cannot reconstruct file contents**. Losing the only
copy of raw captures, per-sample measurements or reference payloads prevents
their original independent re-scoring/re-auditing. Source may permit a future
recomputation, at its original cost and hardware requirements; that would be
new evidence and must not be substituted silently for lost historical bytes.
The written finding does not automatically disappear, but its raw evidence
would no longer be available for verification. Record any such loss explicitly.

## Independent remote copy of the latest failed attempt

The exact 16-member archive described in
[740 suspension checkpoint](740-project-suspension-checkpoint.md) now has an
independent remote copy in a **GitHub Releases draft**:

[N010 suspension evidence backup (partial)](https://github.com/owoDra/real-time-gi-lab/releases/tag/untagged-3f01f518a9ca3cbc8dd0)

- Requested release tag/name: `n010-suspension-20261019`.
- Target commit: `cb4504a71129188d9bf72e443c15714943dacc48`.
- Archive: `n010-737-failed-native-evidence.tar`, **80578560 bytes**.
- Archive SHA256: `407c8f446eeb125b41ef14762236314990142f55f80a323627af039ab1c50590`.
- Other assets: original `manifest.json` and `741-local-raw-inventory.json.gz`.
- All three uploaded assets were **downloaded back from GitHub**; their complete
  byte SHA256 values and sizes match the original local files and server digests.
- [Backup receipt](evidence/741-github-backup-receipt.json) records remote asset
  IDs/API URLs, digests, sizes and completed readback verification.

The draft requires authenticated repository access with suitable permissions;
it is not an anonymously accessible public release. This is an evidence backup,
not a Renderer release, study completion or promotion to main. Git pushes and
clones alone do not transfer release assets. Do not delete this draft or its
assets while they are the independent copy.

To retrieve the preserved files using the repository owner's existing access:

```bash
gh release download n010-suspension-20261019 \
  --repo owoDra/real-time-gi-lab --dir /path/to/new-empty-restore-directory
```

Verify the archive against the SHA256 above, then verify extracted members
against `manifest.json` before use. The JSON result for failed737 and its source
bindings remain in Git. The remote archive protects the failed scene/attempt,
logs/resource receipt/six partial payloads, exact prefix binary/generated
sources and sampling net. It grants no reference admission or scientific PASS.

## Current local raw inventory — metadata only

[Compressed inventory](evidence/741-local-raw-inventory.json.gz) records existing
regular files under `out/research/`, across the locally present N007–N010 trees:

| Property | Snapshot |
| --- | --- |
| Regular files |183258 |
| Sum of logical sizes |249720385351 bytes (about233 GiB) |
| Sum of allocated regular-file blocks |249921499136 bytes |
| Symlinks listed, targets not followed |100 |
| Inventory errors |0 |
| Uncompressed inventory bytes |37176863 |
| Uncompressed inventory SHA256 |`64229a707344a047bb804d4ca1944b11811e3621c57ebc2beadb682f92eb8bc7` |
| Gzip inventory bytes |1871032 |
| Gzip inventory SHA256 |`745022ae7dac83cfb02d3264b350ace1c38d65af36d0c01ccca0235280921195` |

This is a path/size/mtime snapshot, **not file contents, a content-integrity
validation, or a full backup**. No content hashes of the entire233 GiB were
computed. Assets, build trees, external symlink targets and historical raw files
not currently present under `out/research/` are outside this inventory. A backup
of this tree alone cannot be claimed to include every research prerequisite.

## Remaining protection gap

The original `out/` tree and the local archive are on the same SSD. A second
directory there protects against some accidental deletions, not SSD loss. Only
the latest failed737 archive has been copied off that device here. The rest of
the approximately233 GiB remains **NOT independently backed up by this operation**.

The user was asked for a separate disk/NAS/server/cloud destination for the full
data. No destination has yet been supplied and no bulk transfer is running.
Once supplied, preserve exact files and failures with a complete transfer
manifest and content-hash/readback verification; include required assets and
external dependencies or state their exclusions. Preserve originals until that
backup is verified. Do not delete bulky diagnostics or deduplicate away original
paths without retaining their exact content and provenance.

No new scientific conclusions or thresholds were introduced. Tests, builds,
runtime checks, GPU measurements and root-cause diagnosis were **NOT RUN**.
Only filesystem metadata, compression of the new inventory, existing-archive
transfer, byte/hash readback and documentation/index checks were performed.
Source/build graph, N001–N009 results, host settings and the paused research goal
are unchanged.
