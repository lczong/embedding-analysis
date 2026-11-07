#!/usr/bin/env bash
# unseen owns its step order. Output paths are system-scoped.
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
        visualization-tsne|visualization-umap)
            "$PYTHON" workflows/unseen.py visualization "${COMMON[@]}" --route "$ROUTE" --method "${1#visualization-}" ;;
        metrics|tsne|umap|metric-plots) "$PYTHON" workflows/unseen.py "$1" "${COMMON[@]}" --route "$ROUTE" ;;
        *) echo "Unknown step: $1" >&2; exit 2 ;;
    esac
}
if [[ "$STEP" == help ]]; then
    echo "Usage: bash workflows/unseen.sh CONFIG ROUTE STEP [VERSION]"
    echo "Steps: pca; metrics; tsne; umap; visualization-tsne; visualization-umap; metric-plots; all"
    exit 0
fi
if [[ "$STEP" != all ]]; then run_step "$STEP"; exit; fi
run_step pca
run_step metrics
run_step tsne
run_step umap
run_step visualization-tsne
run_step visualization-umap
run_step metric-plots
