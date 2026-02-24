#!/usr/bin/env bash
set -euo pipefail
echo "== RLM-Lens verification =="
make clean
make check
make e2e
echo "OK"
