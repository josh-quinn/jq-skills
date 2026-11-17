#!/bin/sh
# Pin every GitHub Action reference to a full commit SHA with a version comment.
#
#   pin-actions.sh [--update] [FILE_OR_DIR ...]     (default: .github/workflows)
#
#   uses: owner/repo@v1.2.3     -> uses: owner/repo@<sha> # v1.2.3
#   uses: owner/repo@PIN        -> latest release, pinned
#   --update                    -> also move SHA-pinned refs to the latest release
#
# Skips local actions (./), docker:// images, and slsa-framework/slsa-github-generator,
# which must stay tag-referenced for slsa-verifier. Needs jq, plus gh (authenticated) or curl.
# Does not pin container images: use `docker buildx imagetools inspect IMAGE:TAG` for the
# digest and write IMAGE:TAG@sha256:... (see assets/github/workflows/container.yml).
set -eu

update=0
if [ "${1:-}" = "--update" ]; then update=1; shift; fi
[ $# -gt 0 ] || set -- .github/workflows

files=$(for p in "$@"; do
  if [ -d "$p" ]; then find "$p" -type f \( -name '*.yml' -o -name '*.yaml' \); else echo "$p"; fi
done)

# Uses gh when it is authenticated, else the public REST API via curl (60 requests/hour
# unauthenticated; export GITHUB_TOKEN to raise it). jq is required either way.
if gh auth status >/dev/null 2>&1; then
  api() { gh api "$1" --jq "$2"; }
else
  api() { curl -fsS ${GITHUB_TOKEN:+-H "Authorization: Bearer $GITHUB_TOKEN"} "https://api.github.com/$1" | jq -r "$2"; }
fi
latest_tag() { api "repos/$1/releases/latest" .tag_name 2>/dev/null \
  || api "repos/$1/tags" '.[0].name'; }
tag_sha() { api "repos/$1/commits/$2" .sha; }

status=0
for f in $files; do
  refs=$(grep -oE 'uses:[[:space:]]+[A-Za-z0-9_.-]+/[A-Za-z0-9_./-]+@[A-Za-z0-9_.-]+' "$f" \
    | sed 's/uses:[[:space:]]*//' | sort -u) || continue
  for ref in $refs; do
    action=${ref%@*}; version=${ref#*@}
    repo=$(echo "$action" | cut -d/ -f1-2)
    case "$repo" in slsa-framework/slsa-github-generator) continue ;; esac
    if echo "$version" | grep -Eq '^[0-9a-f]{40}$'; then
      [ "$update" -eq 1 ] || continue
      tag=$(latest_tag "$repo")
    elif [ "$version" = PIN ]; then
      tag=$(latest_tag "$repo")
    else
      tag=$version
    fi
    if ! sha=$(tag_sha "$repo" "$tag"); then
      echo "pin-actions: cannot resolve $repo@$tag in $f" >&2; status=1; continue
    fi
    # Replace the ref and any old version comment after it.
    esc=$(printf '%s' "$ref" | sed 's/[.[\*^$/]/\\&/g')
    sed -i.bak -E "s/$esc([[:space:]]*#.*)?\$/$(printf '%s' "$action" | sed 's/[\/&]/\\&/g')@$sha # $tag/" "$f"
    rm -f "$f.bak"
    echo "$f: $action@$tag -> $sha"
  done
done
exit $status
