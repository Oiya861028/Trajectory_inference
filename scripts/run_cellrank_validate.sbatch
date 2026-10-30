#!/bin/bash
#SBATCH --job-name=cr_validate
#SBATCH --account=pi-imoskowitz
#SBATCH --partition=caslake
#SBATCH --output=/project/imoskowitz/yubin/Trajectory_inference/logs/cr_validate_%j.out
#SBATCH --error=/project/imoskowitz/yubin/Trajectory_inference/logs/cr_validate_%j.err
#SBATCH --cpus-per-task=8
#SBATCH --mem=48G
#SBATCH --time=01:00:00
set -euo pipefail
cd /project/imoskowitz/yubin/Trajectory_inference
export OMP_NUM_THREADS=${SLURM_CPUS_PER_TASK:-8} JAX_PLATFORMS=cpu
export OPENBLAS_NUM_THREADS=$OMP_NUM_THREADS MKL_NUM_THREADS=$OMP_NUM_THREADS NUMBA_NUM_THREADS=$OMP_NUM_THREADS
/project/imoskowitz/yubin/envs/cellrank_traj/bin/python -u \
  /home/yubin/claude-90309882/-project-imoskowitz-yubin-Trajectory-inference/aca6db75-a33d-4b4b-b40c-664de22bfd79/scratchpad/validate_cellrank.py
echo "done: $(date)"
