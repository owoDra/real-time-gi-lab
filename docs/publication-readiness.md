# Publication readiness — manual security gate

## What was checked through the connected GitHub API (2026-10-11)

- The repository remains **private**. Apache-2.0 license text was added from GitHub Choose a License's standard Apache-2.0 template.
- Audited the **file paths in the current trees of 26 remote branches** (the 25 original research heads plus the consolidation head, including main/research). No files named like private keys, `.env`, credential exports or token stores were found by the filename-pattern check.
- Read the main branch commit list: **859 reachable commits**; this inspected commit **metadata and subjects only**, not the contents of every historical patch.
- Read the advertised remote refs: **26 branch refs, four pull request head refs, no tags**.
- Inspected root paths for a checked-in LICENSE/NOTICE and obvious bundled third-party binary/test scene asset; external Sponza is fetched under ignored `assets/`.
- GitHub's connected **code search returned no results even for known code terms**, so empty search hits are **not** accepted as negative evidence.
- The GitHub connector cannot run Git/GLSL or Gitleaks locally and the sandbox cannot resolve GitHub's private clone host. **The connected GitHub API could not independently run Gitleaks. A subsequent complete local history scan is reported as PASS by the repository owner (see below).**

## Reviewed historical false positive

The owner's local Gitleaks scan (2026-10-11) enumerated 1,881 reachable commits and reported **one** `generic-api-key` finding, on commit `8f5491bb5f5a94e8f9f607c8b0180cbaf6c723fc`, file `research/lanes/n006-interval-aware-allocation/001-literature-and-architecture.md`, line 38. Inspection of the exact historical Git blob confirmed this line discusses the GI storage process `update/invalidation/resolve` and does not contain a real authentication secret.

The root [.gitleaksignore](../.gitleaksignore) exempts **only that exact commit, path, rule and line**, preserving the generic detector for other files and findings. This is not a path-wide ignore or history rewrite. **The owner reports that the local scan was rerun and returned PASS after this exact-fingerprint allowlist was added.** This confirms the Gitleaks check by user report, not independent remote execution. The repository remains private.

## Owner-reported history scan PASS and remaining privacy review

- On 2026-10-11 the owner reported **PASS** for `bash scripts/audit_public_release.sh` after the single reviewed false-positive fingerprint was allowlisted. The full-history Gitleaks gate is therefore marked **PASS (owner-reported)**, with no unreviewed detector findings reported.
- A separate audit of **all 862 main-reachable commit metadata entries** found **one distinct personal `gmail.com` email address recorded as author/committer in two historical commits** (`2620d102830fa5c23ae725bc7a4b58bc89655ab5` and `a17b9769fcd9…`). No address is reproduced here. Once published, those Git commit metadata records become visible. This is **not a credential leak** and does not invalidate Gitleaks PASS, but warrants an explicit privacy decision before changing repository visibility.
- The commit-author email audit above covers the **main-reachable commit list**, not every distinct commit on all divergent branch refs. Other old branches and refs will also become publicly visible. Third-party NOTICE/copyright checks are not yet a verified complete audit.

**Current readiness:** Gitleaks history scan **PASS (owner-reported)**; public visibility **NOT YET APPROVED** pending owner decision about historical email exposure and third-party material review. No repository visibility change has been made.

## Mandatory before changing visibility to public

On a workstation that can clone or fetch the private repository, run:

```bash
git clone git@github.com:owoDra/phos-gi-lab.git
cd phos-gi-lab
bash scripts/audit_public_release.sh
```

This script fetches **all remote heads and tags, plus pull-request heads**, then runs [Gitleaks](https://github.com/gitleaks/gitleaks) on the full locally reachable history (`git log -p --all --full-history`). Requires Gitleaks or Nix with flakes. The redacted report stays under ignored `out/security/`.

The check must finish with **exit status 0** and no unresolved findings. A nonzero status does **not** authorize publication. Also review all distinct commit author emails (they become visible), code comments/internal URLs or personal path names, and any third-party copyright or NOTICE obligations. Gitleaks is signature-based: no findings does not prove no credentials.

**Current publication decision: NOT YET CLEARED FOR PUBLIC VISIBILITY.** Gitleaks PASS is recorded from the owner's local execution; the separate historical email privacy and third-party license decisions remain open. Keep the repository private until those are addressed.
