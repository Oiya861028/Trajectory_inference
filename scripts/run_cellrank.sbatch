#!/bin/bash
#SBATCH --job-name=cellrank_traj
#SBATCH --account=pi-imoskowitz
#SBATCH --partition=caslake
#SBATCH --output=/project/imoskowitz/yubin/Trajectory_inference/logs/cellrank_%j.out
#SBATCH --error=/project/imoskowitz/yubin/Trajectory_inference/logs/cellrank_%j.err
#SBATCH --cpus-per-task=16
#SBATCH --mem=96G
#SBATCH --time=12:00:00

# CellRank on the devbrain cells: velocity + moscot + connectivity kernels,
# individually and at five weightings.  Uses envs/cellrank_traj (cellrank 2.0.7,
# moscot 0.5.2, PETSc/SLEPc for the Krylov Schur decomposition - without SLEPc,
# pyGPCCA would need a dense 68k x 68k Schur form).
#
# Usage: sbatch scripts/run_cellrank.sbatch [notebook]
set -euo pipefail
PROJ=/project/imoskowitz/yubin/Trajectory_inference
PYBIN=/project/imoskowitz/yubin/envs/cellrank_traj/bin
NB=${1:-Notebooks/cellrank_trajectory.ipynb}

export OMP_NUM_THREADS=${SLURM_CPUS_PER_TASK:-16}
export OPENBLAS_NUM_THREADS=$OMP_NUM_THREADS
export MKL_NUM_THREADS=$OMP_NUM_THREADS
export NUMBA_NUM_THREADS=$OMP_NUM_THREADS
export XLA_FLAGS="--xla_force_host_platform_device_count=${SLURM_CPUS_PER_TASK:-16}"
export JAX_PLATFORMS=cpu

cd "$PROJ"
"$PYBIN/jupyter" nbconvert --to notebook --execute --inplace \
    --ExecutePreprocessor.timeout=36000 \
    --ExecutePreprocessor.kernel_name=python3 \
    "$NB"
echo "done: $(date)"
