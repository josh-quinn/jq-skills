#!/bin/sh
# Run the planted leaky package (jq-privacy-sandbox/tests/fixtures/leaky-pkg) in a real sandbox
# and check that every planted leak was caught and blocked. Needs Docker. Uses a throwaway
# config and data folder, never the real ones.
set -eu
repo=$(cd "$(dirname "$0")/.." && pwd -P)
tmp=$(mktemp -d)
trap 'rm -rf "$tmp"' EXIT
unset TOOLS_CONFIG
export JQ_TOOLS_CONFIG="$tmp/config"
mkdir -p "$JQ_TOOLS_CONFIG/privacy-audit"
printf 'data_dir: %s/audits\nprofile: personal\n' "$tmp" > "$JQ_TOOLS_CONFIG/privacy-audit/config.yaml"
py="uv run -q --no-project --with pyyaml python -I"
work=$($py "$repo/jq-privacy-common/scripts/privacy.py" init --target leaky-pkg | sed -n 's/.*"work_dir": "\(.*\)".*/\1/p')
box=$($py "$repo/jq-privacy-sandbox/scripts/sandbox.py" prepare --work "$work" \
  --target "$repo/jq-privacy-sandbox/tests/fixtures/leaky-pkg" --run "node leak.js" --timeout 60 --linger 2 \
  | sed -n 's/.*"sandbox": "\(.*\)".*/\1/p')
$py "$repo/jq-privacy-sandbox/scripts/sandbox.py" run "$box" > "$tmp/out.txt" 2>&1 || true
report="$box/sandbox-report.md"
fail=0
for want in 'Planted data tried to leave the machine' 'file:ssh-key' 'file:meeting-notes' 'file:git-email' \
            'collect.leaky-example.xyz' 'backup.leaky-example.xyz' 'us.i.posthog.com'; do
  grep -q "$want" "$report" || { echo "missing from report: $want"; fail=1; }
done
grep -q '| registry.npmjs.org | trusted | ok | [0-9]* | [1-9]' "$report" || { echo "registry was not forwarded"; fail=1; }
if [ "$fail" -ne 0 ]; then cat "$report"; tail -40 "$tmp/out.txt"; exit 1; fi
$py "$repo/jq-privacy-sandbox/scripts/sandbox.py" clean "$box" >/dev/null 2>&1 || true
echo "sandbox smoke test passed"
