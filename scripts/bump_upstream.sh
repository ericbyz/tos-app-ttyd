#!/usr/bin/env bash
# Bump the pinned upstream version: UPSTREAM + config.ini + control in lockstep.
# Usage: ./scripts/bump_upstream.sh 1.7.8
# After bumping, fill the new asset SHA256s into UPSTREAM, then run ./build.sh
set -euo pipefail

NEW_VERSION="${1:?usage: bump_upstream.sh <version>}"
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${REPO_ROOT}"

# UPSTREAM
sed -i "s/^UPSTREAM_TAG=.*/UPSTREAM_TAG=${NEW_VERSION}/" UPSTREAM
sed -i "s/^UPSTREAM_VERSION=.*/UPSTREAM_VERSION=${NEW_VERSION}/" UPSTREAM
sed -i "s/^SHA256_x86_64=.*/SHA256_x86_64=REPLACE_WITH_UPSTREAM_SHA256/" UPSTREAM
sed -i "s/^SHA256_aarch64=.*/SHA256_aarch64=REPLACE_WITH_UPSTREAM_SHA256/" UPSTREAM

# config.ini
python3 - "$NEW_VERSION" <<'PYEOF'
import json, sys
cfg = json.load(open("config.ini", encoding="utf-8"))
cfg["version"] = sys.argv[1]
with open("config.ini", "w", encoding="utf-8", newline="\n") as f:
    json.dump(cfg, f, ensure_ascii=False, indent=2)
    f.write("\n")
PYEOF

# DEBIAN/control version
sed -i "s/^Version:.*/Version: ${NEW_VERSION}/" DEBIAN/control

echo "bumped to ${NEW_VERSION}"
echo "NEXT STEPS:"
echo "  1. pin the new release binary SHA256s in UPSTREAM (SHA256_x86_64 / SHA256_aarch64)"
echo "  2. review upstream release notes (html asset changes / flag changes)"
echo "  3. run ./build.sh && ./scripts/validate.py"
echo "  4. commit, tag v${NEW_VERSION} and push to trigger CI"
