#!/bin/bash
#SBATCH --job-name=devbrain_brooks_int
#SBATCH --account=pi-imoskowitz
#SBATCH --partition=caslake
#SBATCH --output=/project/imoskowitz/yubin/Trajectory_inference/logs/integration_nb_%j.out
#SBATCH --error=/project/imoskowitz/yubin/Trajectory_inference/logs/integration_nb_%j.err
#SBATCH --cpus-per-task=8
#SBATCH --mem=96G
#SBATCH --time=06:00:00

# Joint integration of devbrain (E7-E10) with Brooks 2025 (E7.5-E8.75).
# 107k cells x 15.2k shared genes, two kNN graphs and two UMAPs, so this needs
# more headroom than the devbrain-only notebook (which peaked at 9.1 GB).

set -euo pipefail
PROJ=/project/imoskowitz/yubin/Trajectory_inference
PYBIN=/home/yubin/.conda/envs/scRNAseq_python/bin
export OMP_NUM_THREADS=${SLURM_CPUS_PER_TASK:-8}
export OPENBLAS_NUM_THREADS=$OMP_NUM_THREADS
export MKL_NUM_THREADS=$OMP_NUM_THREADS
export NUMBA_NUM_THREADS=$OMP_NUM_THREADS

cd "$PROJ"
"$PYBIN/jupyter" nbconvert --to notebook --execute --inplace \
    --ExecutePreprocessor.timeout=18000 \
    --ExecutePreprocessor.kernel_name=python3 \
    notebooks/integration_devbrain_brooks.ipynb
echo "done: $(date)"
