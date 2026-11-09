#!/usr/bin/env bash
#SBATCH --job-name=workflow-pdf
#SBATCH --partition=standard
#SBATCH --cpus-per-task=2
#SBATCH --mem=8G
#SBATCH --time=00:30:00
#SBATCH --output=outputs/paper/reports/logs/%x-%j.log

# Submit from the project root after creating outputs/paper/reports/logs.
# Pass --system, --model, and optionally --version/--panels/--dpi.
set -euo pipefail
cd "${SLURM_SUBMIT_DIR:?Submit from the project root}"
export MPLBACKEND=Agg
export PYTHONUNBUFFERED=1
export OPENBLAS_NUM_THREADS="${SLURM_CPUS_PER_TASK:-2}"
export OMP_NUM_THREADS="$OPENBLAS_NUM_THREADS"
exec .venv/bin/python paper/report.py render "$@"
