#!/bin/bash
#SBATCH --job-name=celltypist_gastru
#SBATCH --account=pi-imoskowitz
#SBATCH --partition=caslake
#SBATCH --output=/project/imoskowitz/yubin/Trajectory_inference/logs/celltypist_%j.out
#SBATCH --error=/project/imoskowitz/yubin/Trajectory_inference/logs/celltypist_%j.err
#SBATCH --cpus-per-task=16
#SBATCH --mem=128G
#SBATCH --time=08:00:00

# Train CellTypist models on Pijuan-Sala 2019 (116k cells) and annotate devbrain.
# No gastrulation model exists in the CellTypist zoo; the nearest is trained on
# La Manno 2021, which is the dataset being annotated.
set -euo pipefail
cd /project/imoskowitz/yubin/Trajectory_inference
export OMP_NUM_THREADS=${SLURM_CPUS_PER_TASK:-16}
export OPENBLAS_NUM_THREADS=$OMP_NUM_THREADS
export MKL_NUM_THREADS=$OMP_NUM_THREADS
/home/yubin/.conda/envs/scRNAseq_python/bin/python -u scripts/analysis/celltypist_gastrulation.py
echo "done: $(date)"
