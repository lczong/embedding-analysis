#!/usr/bin/env bash
# No embedding/PCA dependency; trailing arguments select individual plots.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
CONFIG="${1:-configs/cazy.json}"
STEP="${2:-help}"
if (( $# >= 2 )); then shift 2; else set --; fi
PYTHON="$ROOT/.venv/bin/python"
case "$STEP" in
    tables|plots) "$PYTHON" workflows/performance.py "$STEP" --config "$CONFIG" "$@" ;;
    all)
        # --version belongs to both stages; --plots only to the plotting stage.
        TABLE_ARGS=(--config "$CONFIG")
        ARGS=("$@")
        for (( i=0; i<${#ARGS[@]}; i++ )); do
            if [[ "${ARGS[i]}" == --version ]]; then
                TABLE_ARGS+=(--version "${ARGS[i+1]:?--version requires a value}")
            elif [[ "${ARGS[i]}" == --version=* ]]; then
                TABLE_ARGS+=("${ARGS[i]}")
            fi
        done
        "$PYTHON" workflows/performance.py tables "${TABLE_ARGS[@]}"
        "$PYTHON" workflows/performance.py plots --config "$CONFIG" "$@"
        ;;
    help) echo 'Usage: bash workflows/performance.sh CONFIG tables|plots|all [--version NAME] [--plots NAME ...]' ;;
    *) echo "Unknown step: $STEP" >&2; exit 2 ;;
esac
