#!/bin/bash
#SBATCH --job-name=devbrain_pca_umap
#SBATCH --account=pi-imoskowitz
#SBATCH --partition=caslake
#SBATCH --output=/project/imoskowitz/yubin/Trajectory_inference/logs/inference_nb_%j.out
#SBATCH --error=/project/imoskowitz/yubin/Trajectory_inference/logs/inference_nb_%j.err
#SBATCH --cpus-per-task=8
#SBATCH --mem=64G
#SBATCH --time=04:00:00

# Execute notebooks/inference.ipynb in place on a compute node.  The login nodes
# cap each user at 8 GB, which is not enough for 68k x 24k: normalization alone
# holds the counts layer plus a float32 copy of a 216M-nnz matrix.

set -euo pipefail

PROJ=/project/imoskowitz/yubin/Trajectory_inference
PYBIN=/home/yubin/.conda/envs/scRNAseq_python/bin

export OMP_NUM_THREADS=${SLURM_CPUS_PER_TASK:-8}
export OPENBLAS_NUM_THREADS=$OMP_NUM_THREADS
export MKL_NUM_THREADS=$OMP_NUM_THREADS
export NUMBA_NUM_THREADS=$OMP_NUM_THREADS

cd "$PROJ"
"$PYBIN/jupyter" nbconvert \
    --to notebook --execute --inplace \
    --ExecutePreprocessor.timeout=10800 \
    --ExecutePreprocessor.kernel_name=python3 \
    notebooks/inference.ipynb

echo "done: $(date)"
