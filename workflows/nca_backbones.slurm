#!/usr/bin/env bash
#SBATCH --job-name=cazy-nca-tsne
#SBATCH --partition=standard
#SBATCH --cpus-per-task=4
#SBATCH --mem=16G
#SBATCH --time=02:00:00
#SBATCH --output=outputs/cazy/logs/nca-20261109/%x-%A_%a.log
set -euo pipefail
cd "${SLURM_SUBMIT_DIR:?Submit from the project root}"
export OPENBLAS_NUM_THREADS="${SLURM_CPUS_PER_TASK:-4}"
export OMP_NUM_THREADS="$OPENBLAS_NUM_THREADS"
export MKL_NUM_THREADS="$OPENBLAS_NUM_THREADS"
export MPLBACKEND=Agg
export PYTHONUNBUFFERED=1
export MPLCONFIGDIR="$PWD/.cache/matplotlib-${SLURM_JOB_ID}"
CONFIG=configs/cazy_nca_backbones.json
VERSION=nca-20261109
MODELS=(esm1b esm2-150m esm2-35m)
case "${1:-}" in
  route)
    TASK="${SLURM_ARRAY_TASK_ID:?Use array 0-5}"
    case "$TASK" in 0|1|2|3|4|5) ;; *) exit 2;; esac
    MODEL="${MODELS[TASK / 2]}"
    ROUTE="${MODEL}__l2-frozen-nca"
    if (( TASK % 2 )); then ROUTE="${MODEL}__l1-ft-ce__l2-frozen-nca"; fi
    for STEP in pca tsne visualization-tsne; do
      printf '[%s] %s %s\n' "$(date -Is)" "$ROUTE" "$STEP"
      bash workflows/overview.sh "$CONFIG" "$ROUTE" "$STEP" "$VERSION"
    done
    ;;
  report)
    for MODEL in "${MODELS[@]}"; do
      .venv/bin/python paper/report.py render --system cazy --model "$MODEL" --version "$VERSION" --preset nca --dpi 300
    done
    ;;
  *) echo 'Usage: sbatch workflows/nca_backbones.slurm route|report' >&2; exit 2;;
esac
