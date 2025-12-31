#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

echo "Configuring git to use repo-local hooks: $ROOT/.githooks"
git config core.hooksPath "$ROOT/.githooks"

echo "Done."
echo "Verify with: git config core.hooksPath"
