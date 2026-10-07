#!/usr/bin/env bash
# unseen owns the execution order and input/output paths.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
EXPERIMENT="unseen"
CONFIG="${1:-configs/cazy.json}"
ROUTE="${2:-esm2__l2-frozen-nca}"
STEP="${3:-help}"
SYSTEM="$(basename "$CONFIG" .json)"
BASE="${4:-outputs/steps/$SYSTEM/$ROUTE}"
PYTHON="$ROOT/.venv/bin/python"
run_step() {
    case "$1" in
        pca) "$PYTHON" workflows/pca.py prepare --config "$CONFIG" --route "$ROUTE" --output "$BASE/pca" ;;
        metrics|tsne|umap)
            local command=("$PYTHON" "workflows/$EXPERIMENT.py" "$1" --config "$CONFIG" --route "$ROUTE" --input "$BASE/pca" --output "$BASE/$EXPERIMENT/$1")

            "${command[@]}" ;;
        visualization-tsne|visualization-umap)
            local method="${1#visualization-}"
            "$PYTHON" "workflows/$EXPERIMENT.py" visualization --config "$CONFIG" --input "$BASE/$EXPERIMENT/$method" --output "$BASE/$EXPERIMENT/$1" ;;
        metric-plots)
            "$PYTHON" "workflows/$EXPERIMENT.py" metric-plots --config "$CONFIG" --input "$BASE/$EXPERIMENT/metrics" --output "$BASE/$EXPERIMENT/metric-plots" ;;
        *) echo "Unknown step: $1" >&2; exit 2 ;;
    esac
}
if [[ "$STEP" == help ]]; then
    echo "Usage: bash workflows/$EXPERIMENT.sh CONFIG ROUTE STEP [OUTPUT_BASE]"
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
