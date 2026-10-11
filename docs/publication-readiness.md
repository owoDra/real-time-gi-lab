# Publication readiness — manual security gate

## What was checked through the connected GitHub API (2026-10-11)

- The repository remains **private**. Apache-2.0 license text was added from GitHub Choose a License's standard Apache-2.0 template.
- Audited the **file paths in the current trees of 26 remote branches** (the 25 original research heads plus the consolidation head, including main/research). No files named like private keys, `.env`, credential exports or token stores were found by the filename-pattern check.
- Read the main branch commit list: **859 reachable commits**; this inspected commit **metadata and subjects only**, not the contents of every historical patch.
- Read the advertised remote refs: **26 branch refs, four pull request head refs, no tags**.
- Inspected root paths for a checked-in LICENSE/NOTICE and obvious bundled third-party binary/test scene asset; external Sponza is fetched under ignored `assets/`.
- GitHub's connected **code search returned no results even for known code terms**, so empty search hits are **not** accepted as negative evidence.
- The GitHub connector cannot run Git/GLSL or Gitleaks locally and the sandbox cannot resolve GitHub's private clone host. **No exhaustive all-commit/all-blob secret-content scan has been completed in this session.**

## Reviewed historical false positive

The owner's local Gitleaks scan (2026-10-11) enumerated 1,881 reachable commits and reported **one** `generic-api-key` finding, on commit `8f5491bb5f5a94e8f9f607c8b0180cbaf6c723fc`, file `research/lanes/n006-interval-aware-allocation/001-literature-and-architecture.md`, line 38. Inspection of the exact historical Git blob confirmed this line discusses the GI storage process `update/invalidation/resolve` and does not contain a real authentication secret.

The root [.gitleaksignore](../.gitleaksignore) exempts **only that exact commit, path, rule and line**, preserving the generic detector for other files and findings. This is not a path-wide ignore or history rewrite. **The local scan must be rerun and must return exit code 0**; until the new run is confirmed, the repository is still not cleared for public release.

## Mandatory before changing visibility to public

On a workstation that can clone or fetch the private repository, run:

```bash
git clone git@github.com:owoDra/phos-gi-lab.git
cd phos-gi-lab
bash scripts/audit_public_release.sh
```

This script fetches **all remote heads and tags, plus pull-request heads**, then runs [Gitleaks](https://github.com/gitleaks/gitleaks) on the full locally reachable history (`git log -p --all --full-history`). Requires Gitleaks or Nix with flakes. The redacted report stays under ignored `out/security/`.

The check must finish with **exit status 0** and no unresolved findings. A nonzero status does **not** authorize publication. Also review all distinct commit author emails (they become visible), code comments/internal URLs or personal path names, and any third-party copyright or NOTICE obligations. Gitleaks is signature-based: no findings does not prove no credentials.

**Current publication decision: NOT CLEARED.** The all-history content scan has been prepared but cannot be represented as having run or passed. Remain private until local execution and review are confirmed.
