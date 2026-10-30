#!/bin/bash
#SBATCH --job-name=merge_velocyto
#SBATCH --account=pi-imoskowitz
#SBATCH --partition=caslake
#SBATCH --output=/project/imoskowitz/yubin/Trajectory_inference/logs/merge_velocyto_%j.out
#SBATCH --error=/project/imoskowitz/yubin/Trajectory_inference/logs/merge_velocyto_%j.err
#SBATCH --cpus-per-task=4
#SBATCH --mem=48G
#SBATCH --time=02:00:00
set -euo pipefail
cd /project/imoskowitz/yubin/Trajectory_inference
/home/yubin/.conda/envs/scRNAseq_python/bin/python -u scripts/merge_velocyto.py
echo "done: $(date)"
