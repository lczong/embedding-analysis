#!/usr/bin/env bash
#SBATCH --job-name=esm1b-analysis
#SBATCH --partition=standard
#SBATCH --cpus-per-task=4
#SBATCH --mem=32G
#SBATCH --time=24:00:00
#SBATCH --output=outputs/cazy/logs/esm1b/%x-%A_%a.log

# Submit from the project root. Modes: sample, route (array 0-2), summary.
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
        run "$PYTHON" workflows/boundary.py sample --config "$CONFIG"
        ;;
    route)
        case "${SLURM_ARRAY_TASK_ID:-}" in 0|1|2) ;; *) echo 'Expected array task 0, 1, or 2' >&2; exit 2;; esac
        ROUTE="esm1b__l${SLURM_ARRAY_TASK_ID}-ft-ce"
        run "$PYTHON" workflows/pca.py prepare --config "$CONFIG" --route "$ROUTE"
        for workflow in boundary multilabel; do
            run bash "workflows/${workflow}.sh" "$CONFIG" "$ROUTE" metrics
            run bash "workflows/${workflow}.sh" "$CONFIG" "$ROUTE" metric-plots
        done
        for workflow in overview boundary multilabel binary; do
            if [[ "$workflow" == binary ]]; then
                run bash workflows/binary.sh "$CONFIG" "$ROUTE" pca
            fi
            for method in tsne umap; do
                run bash "workflows/${workflow}.sh" "$CONFIG" "$ROUTE" "$method"
                run bash "workflows/${workflow}.sh" "$CONFIG" "$ROUTE" "visualization-$method"
            done
        done
        ;;
    summary)
        for workflow in boundary multilabel; do
            run "$PYTHON" "workflows/${workflow}_summary.py" tables --config "$CONFIG" --routes esm1b__l0-ft-ce esm1b__l1-ft-ce esm1b__l2-ft-ce
            run "$PYTHON" "workflows/${workflow}_summary.py" plots --config "$CONFIG"
        done
        ;;
    *) echo 'Usage: sbatch workflows/esm1b.slurm sample|route|summary' >&2; exit 2 ;;
esac
