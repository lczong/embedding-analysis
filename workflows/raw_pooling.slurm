#!/usr/bin/env bash
#SBATCH --job-name=cazy-raw-pooling
#SBATCH --partition=standard
#SBATCH --cpus-per-task=4
#SBATCH --mem=16G
#SBATCH --time=02:00:00
#SBATCH --output=outputs/cazy/logs/raw-pooling-20261109/%x-%A_%a.log
set -euo pipefail
cd "${SLURM_SUBMIT_DIR:?Submit from the project root}"
export OPENBLAS_NUM_THREADS="${SLURM_CPUS_PER_TASK:-4}"
export OMP_NUM_THREADS="$OPENBLAS_NUM_THREADS"
export MKL_NUM_THREADS="$OPENBLAS_NUM_THREADS"
export MPLBACKEND=Agg
export PYTHONUNBUFFERED=1
export MPLCONFIGDIR="$PWD/.cache/matplotlib-${SLURM_JOB_ID}"
ROUTES=(esm1b__pool-cls esm1b__pool-residue_mean esm2-650m__pool-cls esm2-650m__pool-residue_mean)
TASK="${SLURM_ARRAY_TASK_ID:?Use array 0-3}"
case "$TASK" in 0|1|2|3) ;; *) exit 2;; esac
ROUTE="${ROUTES[TASK]}"
for STEP in pca tsne visualization-tsne; do
    printf '[%s] %s %s\n' "$(date -Is)" "$ROUTE" "$STEP"
    bash workflows/overview.sh configs/cazy_raw_pooling.json "$ROUTE" "$STEP" raw-pooling-20261109
 done
