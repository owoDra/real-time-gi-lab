#!/usr/bin/env bash
# Prepare a complete history email rewrite in an isolated mirror. Does not push.
set -euo pipefail
umask 077

if (( $# != 2 )); then
  echo "Usage: $0 OLD_EMAIL GITHUB_NOREPLY_EMAIL" >&2
  exit 2
fi
old_email="$1"
new_email="$2"
pattern='^[A-Za-z0-9._+%-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$'
if [[ ! "$old_email" =~ $pattern || ! "$new_email" =~ $pattern || "$old_email" == "$new_email" || "$new_email" != *@users.noreply.github.com ]]; then
  echo "ERROR: provide old email and a different GitHub noreply address" >&2
  exit 2
fi

root="$(git rev-parse --show-toplevel)"
remote="$(git -C "$root" remote get-url origin)"
case "$remote" in
  *github.com:owoDra/phos-gi-lab.git|*github.com/owoDra/phos-gi-lab.git) ;;
  *) echo "ERROR: unexpected origin: $remote" >&2; exit 2;;
esac

if command -v git-filter-repo >/dev/null 2>&1; then
  filter=(git-filter-repo)
elif git filter-repo -h >/dev/null 2>&1; then
  filter=(git filter-repo)
elif command -v nix >/dev/null 2>&1; then
  filter=(nix run 'nixpkgs#git-filter-repo' --)
else
  echo "ERROR: install git-filter-repo (or Nix with flakes enabled)" >&2
  exit 2
fi

mkdir -p "$root/out/security"
work="$(mktemp -d "$root/out/security/email-redaction.XXXXXXXX")"
mirror="$work/rewritten.git"
echo "Private local workspace: $work"
git clone --mirror "$remote" "$mirror"
git --git-dir="$mirror" for-each-ref --format='%(refname) %(objectname)' > "$work/refs-before.txt"
git --git-dir="$mirror" bundle create "$work/original-history.bundle" --all
printf '%s==>%s\n' "$old_email" "$new_email" > "$work/email-replacements.txt"
callback="return b'${new_email}' if email.lower() == b'${old_email}'.lower() else email"
(
  cd "$mirror"
  "${filter[@]}" --force --email-callback "$callback" \
    --replace-text "$work/email-replacements.txt" \
    --replace-message "$work/email-replacements.txt"
)

if git --git-dir="$mirror" log --all --format='%ae%n%ce' | grep -Fxi -- "$old_email"; then
  echo "ERROR: old address remains in the rewritten author/committer metadata" >&2
  exit 1
fi
mapfile="$mirror/filter-repo/commit-map"
if [[ ! -s "$mapfile" ]]; then
  echo "ERROR: commit-map missing" >&2
  exit 1
fi
git --git-dir="$mirror" for-each-ref --format='%(refname) %(objectname)' > "$work/refs-after.txt"

echo "Prepared an isolated rewritten mirror without changing GitHub."
echo "Original history backup: $work/original-history.bundle"
echo "Old-to-new SHA mapping: $mapfile"
echo "Original refs: $work/refs-before.txt"
echo "Rewritten refs: $work/refs-after.txt"
echo "IMPORTANT: All descendant SHAs change. Recorded research source-SHA references require migration."
echo "GitHub pull-request refs and cached old commits may still expose the original address."
echo "Update the N006 Gitleaks fingerprint for the rewritten commit and rerun the audit."
echo "Do not force-push the mirror until provenance and PR-reference impacts are resolved."
