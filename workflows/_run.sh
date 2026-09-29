#!/usr/bin/env bash
# Shared shell plumbing only; each experiment has its own entrypoint.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
EXPERIMENT="$1"; shift
CONFIG="${1:-configs/cazy.json}"
ROUTE="${2:-esm2__l2-frozen-nca}"
STEP="${3:-help}"
SYSTEM="$(basename "$CONFIG" .json)"
BASE="${4:-outputs/steps/$SYSTEM/$ROUTE}"
PYTHON="$ROOT/.venv/bin/python"
run_step() {
    case "$1" in
        pca) "$PYTHON" workflows/pca.py prepare --config "$CONFIG" --route "$ROUTE" --output "$BASE/pca" ;;
        sample) "$PYTHON" workflows/ood.py sample --config "$CONFIG" --output "$BASE/ood/sample" ;;
        metrics|tsne|umap)
            local extra=()
            if [[ "$EXPERIMENT" == ood ]]; then extra=(--sampling "$BASE/ood/sample"); fi
            "$PYTHON" "workflows/$EXPERIMENT.py" "$1" --config "$CONFIG" --route "$ROUTE" --input "$BASE/pca" --output "$BASE/$EXPERIMENT/$1" "${extra[@]}" ;;
        visualization-tsne|visualization-umap)
            local method="${1#visualization-}"
            "$PYTHON" "workflows/$EXPERIMENT.py" visualization --config "$CONFIG" --input "$BASE/$EXPERIMENT/$method" --output "$BASE/$EXPERIMENT/$1" ;;
        visualization)
            "$PYTHON" "workflows/$EXPERIMENT.py" visualization --config "$CONFIG" --input "$BASE/$EXPERIMENT/metrics" --output "$BASE/$EXPERIMENT/visualization" ;;
        metric-plots)
            "$PYTHON" "workflows/$EXPERIMENT.py" metric-plots --config "$CONFIG" --input "$BASE/$EXPERIMENT/metrics" --output "$BASE/$EXPERIMENT/metric-plots" ;;
        *) echo "Unknown step: $1" >&2; exit 2 ;;
    esac
}
if [[ "$STEP" == help ]]; then
    echo "Usage: bash workflows/$EXPERIMENT.sh CONFIG ROUTE STEP [OUTPUT_BASE]"
    echo "Steps: pca; sample (OOD); metrics; tsne; umap; visualization-tsne; visualization-umap; metric-plots; all"
    echo "overview: no metrics; structure: metrics, visualization, metric-plots (no tsne/umap)"
    exit 0
fi
if [[ "$STEP" != all ]]; then run_step "$STEP"; exit; fi
run_step pca
if [[ "$EXPERIMENT" == ood ]]; then run_step sample; fi
if [[ "$EXPERIMENT" != overview ]]; then run_step metrics; fi
if [[ "$EXPERIMENT" == structure ]]; then
    run_step visualization
else
    run_step tsne
    run_step umap
    run_step visualization-tsne
    run_step visualization-umap
fi
if [[ "$EXPERIMENT" != overview ]]; then run_step metric-plots; fi
