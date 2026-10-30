#!/bin/bash
#SBATCH --job-name=pca_plots
#SBATCH --account=pi-imoskowitz
#SBATCH --partition=caslake
#SBATCH --output=/project/imoskowitz/yubin/Trajectory_inference/logs/pca_plots_%j.out
#SBATCH --error=/project/imoskowitz/yubin/Trajectory_inference/logs/pca_plots_%j.err
#SBATCH --cpus-per-task=4
#SBATCH --mem=48G
#SBATCH --time=01:00:00
set -euo pipefail
cd /project/imoskowitz/yubin/Trajectory_inference
export OMP_NUM_THREADS=${SLURM_CPUS_PER_TASK:-4}
/project/imoskowitz/yubin/envs/cellrank_traj/bin/python -u scripts/analysis/pca_plots.py
echo "done: $(date)"
