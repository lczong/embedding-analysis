#!/usr/bin/env bash
#SBATCH --job-name=backbone-analysis
#SBATCH --partition=standard
#SBATCH --cpus-per-task=4
#SBATCH --mem=32G
#SBATCH --time=24:00:00
#SBATCH --output=outputs/cazy/logs/%x-%A_%a.log

# Submit from the project root: MODE MODEL; route mode uses array 0-2.
# MODEL also names the isolated output version and must appear in job/log names.
set -euo pipefail
cd "${SLURM_SUBMIT_DIR:?Submit from the project root}"
export PYTHONUNBUFFERED=1
export MPLBACKEND=Agg
export OPENBLAS_NUM_THREADS="${SLURM_CPUS_PER_TASK:-4}"
export MKL_NUM_THREADS="$OPENBLAS_NUM_THREADS"
export OMP_NUM_THREADS="$OPENBLAS_NUM_THREADS"
export NUMBA_NUM_THREADS="$OPENBLAS_NUM_THREADS"
export MPLCONFIGDIR="$PWD/.cache/matplotlib-${SLURM_JOB_ID}"
export NUMBA_CACHE_DIR="$PWD/.cache/numba-${SLURM_JOB_ID}"
mkdir -p "$MPLCONFIGDIR" "$NUMBA_CACHE_DIR"
MODEL="${2:-}"
case "$MODEL" in esm2-150m|esm2-35m) ;; *) echo 'Expected model esm2-150m or esm2-35m' >&2; exit 2;; esac
VERSION="$MODEL"
CONFIG=configs/cazy_backbones.json
PYTHON="$PWD/.venv/bin/python"
run() {
    printf '\n[%s] START' "$(date -Is)"
    printf ' %q' "$@"
    printf '\n'
    "$@"
    printf '[%s] DONE\n' "$(date -Is)"
}
trap 'printf "[%s] FAILED line %s exit %s\n" "$(date -Is)" "$LINENO" "$?" >&2' ERR
case "${1:-}" in
    sample)
        run "$PYTHON" workflows/boundary.py sample --config "$CONFIG" --version "$VERSION"
        ;;
    route)
        case "${SLURM_ARRAY_TASK_ID:-}" in 0|1|2) ;; *) echo 'Expected array task 0, 1, or 2' >&2; exit 2;; esac
        ROUTE="${MODEL}__l${SLURM_ARRAY_TASK_ID}-ft-ce"
        run "$PYTHON" workflows/pca.py prepare --config "$CONFIG" --version "$VERSION" --route "$ROUTE"
        for workflow in boundary multilabel; do
            run bash "workflows/${workflow}.sh" "$CONFIG" "$ROUTE" metrics "$VERSION"
            run bash "workflows/${workflow}.sh" "$CONFIG" "$ROUTE" metric-plots "$VERSION"
        done
        for workflow in overview boundary multilabel binary; do
            if [[ "$workflow" == binary ]]; then
                run bash workflows/binary.sh "$CONFIG" "$ROUTE" pca "$VERSION"
            fi
            for method in tsne umap; do
                run bash "workflows/${workflow}.sh" "$CONFIG" "$ROUTE" "$method" "$VERSION"
                run bash "workflows/${workflow}.sh" "$CONFIG" "$ROUTE" "visualization-$method" "$VERSION"
            done
        done
        ;;
    summary)
        for workflow in boundary multilabel; do
            run "$PYTHON" "workflows/${workflow}_summary.py" tables --config "$CONFIG" --version "$VERSION" --routes "${MODEL}__l0-ft-ce" "${MODEL}__l1-ft-ce" "${MODEL}__l2-ft-ce"
            run "$PYTHON" "workflows/${workflow}_summary.py" plots --config "$CONFIG" --version "$VERSION"
        done
        ;;
    *) echo 'Usage: sbatch workflows/backbone.slurm sample|route|summary esm2-150m|esm2-35m' >&2; exit 2 ;;
esac
