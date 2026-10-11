#!/usr/bin/env bash
# Pre-publication secret audit. Run locally against an authenticated git clone.
# Intentionally not a GitHub Actions/CI workflow. Raw findings remain git-ignored.
set -euo pipefail
umask 077

root="$(git rev-parse --show-toplevel)"
cd "$root"
if ! git remote get-url origin >/dev/null 2>&1; then
  echo "ERROR: missing origin remote" >&2
  exit 2
fi

if command -v gitleaks >/dev/null 2>&1; then
  runner=(gitleaks)
elif command -v nix >/dev/null 2>&1; then
  runner=(nix run nixpkgs#gitleaks --)
else
  echo "ERROR: install gitleaks or use Nix with flakes enabled" >&2
  exit 2
fi

# Cover all advertised heads and tags, not merely local main.
git fetch origin --prune '+refs/heads/*:refs/remotes/origin/*' '+refs/tags/*:refs/tags/*'
report_dir="$root/out/security"
mkdir -p "$report_dir"

# Pull-request head refs may contain changes not present on any named branch.
pr_list="$report_dir/pull-head-refs.txt"
git ls-remote --refs origin 'refs/pull/*/head' > "$pr_list"
if [[ -s "$pr_list" ]]; then
  git fetch origin '+refs/pull/*/head:refs/remotes/origin/gh-pr/*'
fi

echo "Auditing $(git rev-list --count --all) reachable commits across all fetched refs."
echo "Refs: $(git for-each-ref --format='%(refname)' refs/heads refs/remotes/origin refs/tags | wc -l)"
report="$report_dir/gitleaks-all-history.json"
set +e
"${runner[@]}" git --log-opts='--all --full-history' --redact=100 \
  --report-format=json --report-path="$report" "$root"
result=$?
set -e

if [[ "$result" -eq 0 ]]; then
  echo "PASS: gitleaks reported no findings in the fetched Git history."
  echo "Note: this is pattern-based, not a guarantee of zero secrets."
elif [[ "$result" -eq 1 ]]; then
  echo "FAIL: possible secrets detected. Keep repository PRIVATE." >&2
  echo "Redacted, git-ignored report: $report" >&2
else
  echo "ERROR: gitleaks could not complete (exit $result). Keep repository PRIVATE." >&2
fi
echo "Also review commit author emails, third-party licenses, and untracked artifacts before publication."
exit "$result"
