#!/bin/bash
#SBATCH --job-name=joint_plots
#SBATCH --account=pi-imoskowitz
#SBATCH --partition=caslake
#SBATCH --output=/project/imoskowitz/yubin/Trajectory_inference/logs/joint_plots_%j.out
#SBATCH --error=/project/imoskowitz/yubin/Trajectory_inference/logs/joint_plots_%j.err
#SBATCH --cpus-per-task=4
#SBATCH --mem=64G
#SBATCH --time=01:00:00
set -euo pipefail
cd /project/imoskowitz/yubin/Trajectory_inference
export OMP_NUM_THREADS=${SLURM_CPUS_PER_TASK:-4}
/project/imoskowitz/yubin/envs/cellrank_traj/bin/python -u scripts/joint_pca_feature_plots.py
echo "done: $(date)"
