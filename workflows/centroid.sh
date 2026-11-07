#!/usr/bin/env bash
# centroid owns its step order. Output paths are system-scoped.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
CONFIG="${1:-configs/cazy.json}"
ROUTE="${2:-esm2__l2-frozen-nca}"
STEP="${3:-help}"
VERSION="${4:-}"
PYTHON="$ROOT/.venv/bin/python"
COMMON=(--config "$CONFIG")
if [[ -n "$VERSION" ]]; then COMMON+=(--version "$VERSION"); fi
run_step() {
    case "$1" in
        pca) "$PYTHON" workflows/pca.py prepare "${COMMON[@]}" --route "$ROUTE" ;;
        metrics|visualization|metric-plots) "$PYTHON" workflows/centroid.py "$1" "${COMMON[@]}" --route "$ROUTE" ;;
        *) echo "Unknown step: $1" >&2; exit 2 ;;
    esac
}
if [[ "$STEP" == help ]]; then
    echo "Usage: bash workflows/centroid.sh CONFIG ROUTE STEP [VERSION]"
    echo "Steps: pca; metrics; visualization; metric-plots; all"
    exit 0
fi
if [[ "$STEP" != all ]]; then run_step "$STEP"; exit; fi
run_step pca
run_step metrics
run_step visualization
run_step metric-plots
