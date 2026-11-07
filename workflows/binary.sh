#!/usr/bin/env bash
# binary owns its step order. Output paths are system-scoped.
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
        pca) "$PYTHON" workflows/binary.py pca "${COMMON[@]}" --route "$ROUTE" ;;
        visualization-tsne|visualization-umap)
            "$PYTHON" workflows/binary.py visualization "${COMMON[@]}" --route "$ROUTE" --method "${1#visualization-}" ;;
        tsne|umap) "$PYTHON" workflows/binary.py "$1" "${COMMON[@]}" --route "$ROUTE" ;;
        *) echo "Unknown step: $1" >&2; exit 2 ;;
    esac
}
if [[ "$STEP" == help ]]; then
    echo "Usage: bash workflows/binary.sh CONFIG ROUTE STEP [VERSION]"
    echo "Steps: pca; tsne; umap; visualization-tsne; visualization-umap; all"
    exit 0
fi
if [[ "$STEP" != all ]]; then run_step "$STEP"; exit; fi
run_step pca
run_step tsne
run_step umap
run_step visualization-tsne
run_step visualization-umap
