# Trajectory_inference

Trajectory / RNA-velocity analysis of mouse early-embryo brain development
(PRJNA637987, E7.0–E10.0), with a joint integration against Brooks 2025
(E7.5–E8.75).

## Layout

```
scripts/      pipeline scripts + SLURM submission wrappers
Notebooks/    analysis notebooks (executed on compute nodes via sbatch)
data/         inputs and intermediates (large files are gitignored)
  metadata/     small sample / QC tables (tracked)
  external/     reference genomes + annotations (not tracked)
  velocyto/     spliced/unspliced intermediates (not tracked)
output_fig/   figures, one subdirectory per analysis stage
logs/         SLURM stdout/stderr (not tracked)
```

## Pipeline

1. `scripts/fetch_count.sbatch` — per-sample array job: pull the original
   CellRanger BAM from SRA and count UMIs with `scripts/bam_to_h5ad.py`.
2. `scripts/combine_h5ad.py` — concatenate per-sample raw matrices and call
   cells with the CellRanger v2 ordmag heuristic →
   `data/devbrain_E7-E10.h5ad`.
3. `scripts/run_inference_nb.sbatch` — execute `Notebooks/inference.ipynb`
   in place (QC → HVG/PCA → UMAP → Harmony → hedgehog markers).
4. `scripts/export_barcodes.py` + `scripts/velocyto_run.sbatch` — per-library
   spliced/unspliced counts for velocity.
5. `scripts/run_integration_nb.sbatch` — execute
   `Notebooks/integration_devbrain_brooks.ipynb`; see also
   `scripts/compare_datasets.py` for the streaming dataset comparison.

## Data

The `.h5ad`/`.loom` matrices and reference annotations are deliberately not in
git (~6 GB). Regenerate them with the pipeline above, or copy them from the
project directory on the cluster.
