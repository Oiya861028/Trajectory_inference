# Methods

Trajectory inference for mouse early-embryo brain development, PRJNA637987
(La Manno et al. 2021, E7.0–E10.0), with a joint integration against Brooks 2025
(GSE273804, E7.5–E8.75).

Each section states what was done, the parameters used, and why. Where a step
corrects or integrates data, it is paired with a test that could have shown the
correction failed — those tests and their outcomes are recorded here too,
including the one that failed.

---

## 1. Input

`data/devbrain_E7-E10.h5ad` — 68,177 cells × 24,191 genes, raw UMI counts,
19 libraries spanning E7.0, E8.0, E8.5, E9.0, E10.0.

Produced by `scripts/fetch_count.sbatch` → `scripts/bam_to_h5ad.py` (stream
`CB`/`UB`/`GX` tags from the original CellRanger BAMs) → `scripts/combine_h5ad.py`
(concatenate, call cells with the CellRanger v2 ordmag heuristic, floor 500 UMI).

Reference: `refdata-cellranger-mm10-3.0.0` (Ensembl 93). Chemistry is 10x **v1**
— barcodes are 14 bp — which matters later: a FASTQ-level requantification with
`kb`/`alevin-fry` is impractical, so spliced/unspliced counts must come off the BAMs.

---

## 2. Gene-symbol repair

**What.** Rebuild the Ensembl→symbol map from the union of all 19 per-sample
files, cache to `data/metadata/gene_symbols.csv`, set `var_names` to symbols and
keep Ensembl IDs in `var["gene_ids"]`.

**Why.** 5,334 of 24,191 symbols were `NaN`. `combine_h5ad.py` concatenates with
`merge="first"`, which copies the whole `gene_symbol` column from the *first*
sample; genes that library never detected are reindexed to `NaN`. The symbols
survive in the other per-sample files, so all 5,334 are recoverable.

**Verified.** Counts were unaffected — `join="outer"` aligns `X` independently of
the `merge` policy. Checked directly on the matrix: `Tbx4` carried `NaN` as its
symbol but 30 UMIs across 10 samples; `Fgf23` 14 UMIs across 9. Only labels were
lost.

**Note for future concatenations.** `merge="first"` is column-level, not
element-level. `merge="unique"` or rebuilding `var` explicitly avoids this.

---

## 3. QC and filtering

`sc.pp.calculate_qc_metrics` with `mt` (`mt-` prefix) and `ribo` (`Rps`/`Rpl`)
flags, then:

| step | parameter | cells/genes removed |
|---|---|---|
| `filter_cells` | `min_genes=500` | 11 cells |
| mito filter | `pct_counts_mt < 15` | 0 cells |
| `filter_genes` | `min_cells=3` | 2,448 genes |

Result: 68,166 × 21,743.

**Why so permissive.** Cells were already ordmag-called at ≥500 UMI upstream;
filtering hard again would be double-dipping on the same signal. The mito
threshold never bound — median 0.56%, max 6.93% — so it is reported as
non-binding rather than described as if it had worked.

---

## 4. Normalization

```
adata.layers["counts"] = adata.X.copy()      # raw counts retained
sc.pp.normalize_total(adata, target_sum=1e4) # CP10K
sc.pp.log1p(adata)
```

No `.raw`, no second `lognorm` layer.

**Why.** Scaling happens on a separate HVG copy, so `adata.X` remains the
log-normalized matrix. `.raw` plus a `lognorm` layer would be two further copies
of a 216M-nonzero matrix (~1.7 GB each); dropping them cut ~3.5 GB of peak
memory with no information lost. Plots therefore pass `use_raw=False`.

---

## 5. HVG → PCA → UMAP → Leiden

```
sc.pp.highly_variable_genes(n_top_genes=2000, flavor="seurat", batch_key="sample")
sc.pp.scale(hvg_subset, max_value=10)
sc.tl.pca(n_comps=50, svd_solver="arpack")
sc.pp.neighbors(n_neighbors=15, n_pcs=30)
sc.tl.umap(min_dist=0.3)
sc.tl.leiden(resolution=1.0, flavor="igraph", n_iterations=2)   # 35 clusters
```

PCA runs on a scaled copy of the HVG subset and the embedding is carried back
onto the full object, so `X` keeps real expression values for feature plots.

Variance explained: PC1 4.5%, PC2 3.3%, first 10 PCs 19.9%, first 30 PCs 28.3%,
all 50 PCs 32.0%. Elbow at PC8–10, flat past ~PC15, so 30 PCs for the graph is
adequate-to-generous.

**Caveat.** `batch_key="sample"` selects genes variable *within* libraries, which
can suppress genes that change monotonically with age — a real concern in a
developmental timecourse. A no-batch-key comparison has not been run.

**Plotting note.** `sc.pl.pca_variance_ratio(log=True)` plots the **natural** log
of a fraction, so every point is negative; replaced with a linear-scale scree
plot (`output_fig/02_pca_hvg/pca_scree.png`).

---

## 6. Diagnosing graph connectivity

Two diagnostics, because the second answers what the first cannot.

**Per-stage facets** (`facet_umap`, shared axis limits, non-members in grey) —
shows *where* each stage sits, which an overlaid UMAP cannot.

**kNN mixing matrix** — for each cell, the fraction of its neighbours drawn from
each stage, averaged within stage. Quantifies overlap.

Result on the devbrain-only graph:

| cell's age | e7.0 | e8.0 | e8.5 | e9.0 | e10.0 | cells in >90% own-age nbhd |
|---|---|---|---|---|---|---|
| e7.0 | **98.6** | 1.4 | 0.0 | 0.0 | 0.0 | 95.4% |
| e8.0 | 2.7 | **88.9** | 5.4 | 2.2 | 0.7 | 69.4% |
| e8.5 | 0.0 | 11.6 | **56.0** | 22.3 | 10.0 | 15.2% |
| e9.0 | 0.0 | 0.9 | 4.5 | **54.7** | 39.9 | 3.3% |
| e10.0 | 0.0 | 0.1 | 1.0 | 19.9 | **79.0** | 40.9% |

**e7.0 is effectively a separate component.** No pseudotime or velocity method
can traverse into it. Every subsequent decision follows from this table.

---

## 7. Harmony on `chip` — tested and rejected

**What.** `sc.external.pp.harmony_integrate(adata, "chip", max_iter_harmony=20)`,
where `chip` is the 10x Chromium run (`10X25` in `10X25_2`). Both embeddings
retained (`X_umap` / `X_umap_harmony`, `leiden_harmony`).

**Why `chip` and not `sample`.** Every library is exactly one timepoint, so
`sample` is perfectly nested inside `age`: Harmony could not distinguish "library
effect" from "developmental stage" and would delete the time axis by
construction. `chip` is partially crossed — `10X23` spans e8.0+e9.0, `10X25`
spans e9.0+e10.0 — though 7 of 10 chips remain single-age.

**The falsification test.** No chip contains both an e7.0 and an e9.0/e10.0
sample (e7.0 is only on `10X37`/`10X39`). Any new e7.0↔late edges therefore
cannot be a removed batch effect.

**Outcome — failed.**

| e7.0 neighbours from | before | after |
|---|---|---|
| e9.0 | 0.00% | 1.94% |
| e10.0 | 0.01% | **6.22%** |

Own-age share also collapsed (e8.0 88.9→45.8%, e8.5 56.0→20.3%) and clusters
dropped 35→29. Harmony forced distributions to match across clusters and
manufactured a continuum between gastrulation-stage and e10.0 brain cells.

**Conclusion.** Not used for trajectory inference. Retained in the object only
for comparison. If revisited, `theta` (default 2, converged in 3 iterations
here) is the lever; a sweep reporting e7.0→e10.0 leakage per theta would let a
value be chosen on evidence.

---

## 8. Spliced/unspliced counts

**Why regenerated rather than downloaded.** The published per-cell
`dev_all.loom` (19 GB) was hosted in the `linnarsson-lab-loom` GCS bucket, which
now 404s entirely — including `l5_all.loom`. Surviving mirrors are inadequate:

| source | contents | verdict |
|---|---|---|
| CELLxGENE `developing_mouse_nervous_system.h5ad` (9.97 GB) | layers `expected`, `pooled` | no spliced/unspliced |
| `dev_all.agg.loom` (260 MB) | per-cluster aggregate | not per-cell |
| CaltechDATA `dev_gfilt.loom` (672 MB) | real spliced/unspliced, 3,686 genes | **excludes Gli1, Hhip, Shh** |

The 10 GB CELLxGENE file was ruled out by reading its HDF5 header over HTTP
range requests (~9 requests) rather than downloading it.

**Why velocyto and not the existing tag-streaming code.** The BAMs do carry
`RE:A:{E,N,I}` region tags, so tag-only counting was tested first. CellRanger 3.0
assigns `GX` only to exonic reads: of 25,407 intronic (`RE:A:N`) reads probed,
**zero** had a gene tag. Intronic counts require annotation-based interval
assignment, which is velocyto's job.

**Pipeline.** `scripts/export_barcodes.py` (per-library whitelists from the
called cells) → `scripts/velocyto_run.sbatch`:

```
velocyto run --bcfile <library>.tsv --sampleid <library> \
             --mask mm10_rmsk.ensembl.gtf \
             --samtools-threads 8 --samtools-memory 2048 -vv \
             <bam> Mus_musculus.GRCm38.93.gtf
```

References in `data/external/refs/`: Ensembl 93 GTF (all 24,191 of our gene IDs
present — exact match to the CellRanger reference) and UCSC mm10 `rmsk`
converted to Ensembl chromosome naming (`chr1`→`1`, `chrM`→`MT`, alt contigs
dropped; 5,138,236 intervals).

`--sampleid` is set to the library name so cell IDs emerge as
`<library>:<barcode>x`, matching both our join key and the published loom
convention.

**Pilot before fan-out.** One sample (`--array=1`) measured runtime (2h05) and
peak RSS (19.8 GB), which retuned the array from a guessed 48 GB/16 h to
32 GB/6 h. Then `--array=2-19%6`.

**Validated against the authors' own run.** On identical cells and genes
(3,928 cells, 3,686 genes shared with `dev_gfilt.loom`):

| | spliced | unspliced | U/(S+U) |
|---|---|---|---|
| ours | 4,605,058 | 1,086,684 | **19.1%** |
| published | 4,614,149 | 1,104,588 | **19.3%** |

Output: `data/velocyto/loom/`, 19 files, 68,177 cells — exactly the input cell
count. Note the *global* unspliced fraction is 5.2%; the published 3,686-gene
subset is intron-rich by construction, which is why it reads higher. Ribosomal
genes illustrate the dilution: `Rps2` has 347,315 spliced against 562 unspliced.

---

## 9. Joint integration with Brooks 2025

**Source.** `/project/imoskowitz/kdreyer/public_datasets/001_Brooks2025_GSE273804/WT_timeseries/GSE273804_FVB_All.h5ad`
— 39,463 cells × 23,063 genes, stages E7.5/E7.75/E8.0/E8.25/E8.5/E8.75, 30
replicates, `raw_counts` available, with cell-type and neural-plate annotations.

(The file in `Zallen_Celltypist_Annotation/` is an **E8.75-only** 5,903-cell
CellTypist training subset derived from it, not the timeseries.)

**Why it can bridge.** The combined timeline interleaves, with genuine overlap:

| 7.0 | 7.5 | 7.75 | 8.0 | 8.25 | 8.5 | 8.75 | 9.0 | 10.0 |
|---|---|---|---|---|---|---|---|---|
| devbrain | Brooks | Brooks | **both** | Brooks | **both** | Brooks | devbrain | devbrain |

**Procedure.** 15,200 shared genes → concatenate raw counts → CP10K + log1p →
`highly_variable_genes(n_top_genes=3000, batch_key="dataset")` → scale → PCA(50)
→ baseline graph → `harmony_integrate` on **`dataset`** → graph/UMAP/Leiden on
`X_pca_harmony`. Both embeddings kept (`X_umap_pre` / `X_umap_post`).

**Why `dataset` (2 levels) and not replicate.** Same nesting argument as §7:
Brooks replicates are nested in stage, devbrain libraries in age. The dominant
batch effect is cross-platform regardless (see §10).

**The falsification test.** Correction should produce overlap *at the shared
stages specifically*. Uniform mixing would mean the time axis was flattened.

**Outcome — passed.**

| stage | shared by both? | % neighbours from other dataset |
|---|---|---|
| E8.75 | no (adjacent to E9.0) | 35.4 |
| E8.0 devbrain | **yes** | 31.5 |
| E8.5 devbrain | **yes** | 29.9 |
| E8.5 Brooks | **yes** | 23.3 |
| E8.0 Brooks | **yes** | 19.2 |
| E9.0 | no | 14.3 |
| E10.0 | no | **8.4** |

And the headline result — e7.0 reaches forward without long-range fabrication:

| E7.0 neighbours from | before | after |
|---|---|---|
| E7.5 | 0.05% | **8.75%** |
| E7.75 | 0.03% | **3.33%** |
| E9.0 | 0.00% | 0.01% |
| E10.0 | 0.02% | 0.01% |

**One connected component holding 100% of cells**, all nine stages, with every
consecutive stage pair sharing 5–35% of neighbours. Contrast §7, where
e7.0→e10.0 went to 6.22%.

Output: `data/devbrain_brooks_integrated.h5ad` (107,629 × 15,200).

**Caveats.** Only 1,618 of the 3,000 HVGs are variable in both datasets. The
E7.0↔E7.5 link (8.75%) is the thinnest in the chain and is the bottleneck for
any trajectory through gastrulation.

---

## 10. How different are the two datasets?

`scripts/compare_datasets.py` (streams both matrices in cell blocks).

| | devbrain | Brooks |
|---|---|---|
| cells | 68,166 | 39,463 |
| median UMI/cell | 11,692 | 42,461 (**3.6×**) |
| median genes/cell | 3,188 | 5,923 (1.9×) |
| genes per 10k UMI | 2,742 | 1,393 |
| median % mito | 0.56 | **0.00** |

Brooks has **exactly** 0.00% mitochondrial reads at every stage — mito genes were
stripped upstream — so mito-based QC cannot be compared across the two, and mito
genes should be excluded from joint HVG selection.

### Interpreting pseudobulk correlation

`scripts/pseudobulk_correlation_context.py` establishes the scale, because raw
Pearson values here are misleading. Splitting each stage into two random halves
(differing only by sampling noise) gives the ceiling:

| comparison | all genes | expressed only | stage-variable | Spearman |
|---|---|---|---|---|
| **ceiling** — E10.0 half A vs B | 1.0000 | 1.0000 | 1.0000 | 0.9999 |
| devbrain E9.0 vs E10.0 | 0.9973 | 0.9952 | 0.9944 | 0.9900 |
| devbrain E7.0 vs E8.0 | 0.9818 | 0.9685 | 0.9601 | 0.9352 |
| devbrain E7.0 vs E10.0 | 0.9626 | 0.9346 | 0.9134 | 0.8700 |
| dev E8.0 vs Brooks E8.0 | 0.9600 | 0.9051 | 0.9439 | 0.7732 |
| dev E8.5 vs Brooks E8.5 | 0.9360 | 0.8553 | 0.9070 | 0.6737 |

Technical replicates score 0.9999, so the whole usable range is ~0.93–1.00.
An r of 0.963 is therefore *far from ceiling*, not "high". It is propped up by:

- **88.7% of the 15,200 shared genes are near-zero in both** (only 1,720 exceed
  1 CP10K) — correlated noise around zero
- **pseudobulk averages away composition change**: only 34 genes (0.2%) move more
  than one log1p unit between E7.0 and E10.0; development changes *which cell
  types exist*, and summing over cells erases that
- **log1p compresses dynamic range**, so r tracks the shared mean-expression axis
  (ribosomal, housekeeping)

**Conclusion, which holds under every metric and widens as the metric sharpens:**
two datasets at the *same nominal stage* agree less well (Spearman 0.773 / 0.674)
than devbrain cells three days apart (0.870). The platform gap exceeds the
biological time axis — which is why §9's integration is necessary, and why its
falsification test was non-negotiable.

---

## 10b. Dissection is confounded with stage

Per-library pseudobulk correlation (`data/metadata/devbrain_library_correlation.csv`,
171 pairs, expressed genes) separates stage from dissected region:

| | n pairs | median r |
|---|---|---|
| same stage, same tissue | 14 | 0.9883 |
| different stage, same tissue | 14 | 0.9825 |
| same stage, different tissue | 28 | 0.9820 |
| different stage, different tissue | 115 | 0.9481 |

One dissected region costs about as much correlation as one stage step. The
lowest same-stage pairs are E10.0 Forebrain vs Midbrain/Hindbrain (0.968-0.972);
the highest cross-stage pairs are E9.0-E10.0 within one region (Midbrain-Midbrain,
0.9948). Cross-stage pairs can therefore exceed same-stage pairs, with no
labelling error involved.

The design offers no way to separate the two effects:

```
tissue       E7.0  E8.0  E8.5  E9.0  E10.0
All             3     0     0     0      0
Head            0     2     1     0      0
Forebrain       0     0     0     1      4
Hindbrain       0     0     0     2      2
Midbrain        0     0     0     2      2
```

Consequences:

1. The e7.0 isolation in §6 is partly compositional, not purely temporal: e7.0 is
   whole embryo (mesoderm, endoderm, blood) while E9.0/E10.0 are microdissected
   brain. The Brooks bridge addresses the time gap; it addresses the tissue gap
   only insofar as Brooks is itself whole-embryo at E7.5-E8.75.
2. CellRank terminal states at E9.0/E10.0 will tend to recover dissection regions,
   because that is the dominant axis there. Macrostate composition is therefore
   reported by `tissue` as well as by stage, so a state that is merely a
   dissection label is identifiable as one.
3. A within-region trajectory (Forebrain has E9.0 + 4x E10.0) would pose a cleaner
   lineage question, at the cost of the early timepoints, which carry no region
   label.

Chip-sharing contributes a smaller effect with tissue held fixed (median r 0.9917
same-chip vs 0.9832 different-chip), but on only 4 same-chip pairs.

---

## 11. Velocity object

`scripts/merge_velocyto.py` → `data/devbrain_velocity.h5ad` (68,166 × 21,743).

Joins: loom `<library>:<barcode>x` → devbrain `<sample>:<barcode>-1`; loom row
`Accession` → `var["gene_ids"]`. Looms store layers as dense gene × cell arrays,
so each is read in 6,000-gene blocks and converted to sparse rather than
materialised whole.

Adds `spliced`/`unspliced`/`ambiguous` layers (all 68,166 cells covered) and
carries the joint embedding across as `X_pca_harmony_joint` / `X_umap_joint`.

**Why devbrain-only.** Brooks has no spliced/unspliced, and CellRank requires
every kernel in a combination to be defined over the same cells. Carrying the
joint embedding preserves the bridge's benefit for root-cell selection even
though Brooks cells are not in the kernel.

---

## 12. CellRank

### Environment

`/project/imoskowitz/yubin/envs/cellrank_traj` — python 3.11, cellrank 2.0.7,
moscot 0.5.2, scvelo 0.3.4, scanpy 1.11.5, numpy 2.4.6, scipy 1.17.1,
petsc4py/slepc4py 3.26.

**Why 2.0.7 and not 2.3.3.** cellrank ≥2.1 requires python ≥3.12; every
conda-forge `petsc4py`/`slepc4py` build is python 3.11 (`np2py311`). They are
mutually exclusive. SLEPc is load-bearing — without it pyGPCCA falls back to a
dense Schur decomposition, and at 68k cells that matrix is ~37 TB — so three
minor cellrank versions were traded for the ability to compute macrostates at all.

Your existing `envs/cellrank` (python 3.12, cellrank 2.3.3) was left untouched; a
dry-run showed adding petsc4py there would pull a py311-tagged build and
downgrade python.

### Local patches — **these do not survive an env rebuild**

Both have `.orig` backups beside them.

1. `scvelo/tools/optimization.py` — `leastsq_generalized` assigns a size-1 array
   into a scalar slot, which numpy ≥2 rejects, breaking `mode="stochastic"`.
   Fixed with `np.ravel(...)[0]`. (`mode="deterministic"` works unpatched and is
   the fallback.)
2. `cellrank/kernels/_velocity_kernel.py` — calls
   `np.testing.assert_array_equal(x=…, y=…)`; numpy 2 renamed those parameters to
   `actual`/`desired`. Fixed by passing positionally.

A grep of the whole cellrank package found only four numpy-2-suspect sites; the
other three are `.A1` calls guarded by `issparse`, safe as long as matrices stay
`csr_matrix` — which the notebook's `as_sparse_matrices()` helper guarantees.

### In-notebook compatibility shims

- **`getnnz` on sparse arrays** — scanpy 1.11.5 calls `.getnnz()` on the kNN
  distance matrix, but scipy ≥1.16 returns a `csr_array`, where the method was
  removed. Restored on `csr_array`/`csc_array`. Pinning scipy down was rejected:
  petsc4py here is built against numpy 2, so moving scipy backwards risked the
  ABI the entire Krylov path depends on.
- **`as_sparse_matrices()`** — anndata ≥0.12 returns sparse *arrays*, while scvelo
  0.3.4 still uses matrix-only APIs (`.A1`, `.getnnz`). Converts `obsp` and
  `layers` back to `csr_matrix`, called after `sc.pp.neighbors`, after the gene
  subset, and before `velocity_graph` — i.e. at each point anndata rebuilds them.

### Preprocessing (scvelo 0.3.4 API)

0.3.4 removed `n_top_genes`, `log` and `subset_highly_variable` from
`filter_and_normalize`; log and HVG now come from scanpy:

```
adata.X = adata.layers["counts"].copy()        # scvelo expects counts
scv.pp.filter_and_normalize(min_shared_counts=20, retain_genes=HH_GENES)
sc.pp.log1p(adata)
sc.pp.highly_variable_genes(n_top_genes=2000)
keep = highly_variable | var_names.isin(HH_GENES)
scv.pp.moments(n_pcs=None, n_neighbors=None)   # reuse the Harmony graph
scv.tl.velocity(mode="stochastic")
scv.tl.velocity_graph()
```

**`retain_genes` is required.** Gli1 and Shh are too sparse to survive either the
shared-count filter or HVG selection and were silently dropped in a first pass;
they are now retained through both, so all five Hh genes (Gli1, Hhip, Smo, Shh,
Ptch1) reach the velocity object.

### Kernels and weightings

| run | composition |
|---|---|
| `velocity` | VelocityKernel alone |
| `realtime_moscot` | RealTimeKernel alone (moscot OT, consecutive stages) |
| `connectivity` | ConnectivityKernel alone |
| `vk0.8_ck0.2` | velocity + connectivity (CellRank's usual default) |
| `vk0.8_rtk0.2` | velocity-dominant |
| `vk0.5_rtk0.5` | balanced |
| `vk0.2_rtk0.8` | OT-dominant |
| `vk0.6_rtk0.2_ck0.2` | three-way |

moscot: `TemporalProblem.prepare(time_key="stage_num", joint_attr=X_pca_harmony_joint)`
then `solve(epsilon=1e-2, tau_a=0.95, tau_b=0.95, scale_cost="mean")`.
`RealTimeKernel.from_moscot(...).compute_transition_matrix(self_transitions="all", conn_weight=0.2)`.

Every run uses identical settings (`n_states=12`, `cluster_key="leiden_joint"`,
Krylov Schur) so the comparison is like-for-like. Each reports macrostates,
terminal states, **initial** states, and the stage each state falls in —
root-cell identification being the motivation for the bridge in the first place.
Cross-run comparisons: fate-probability correlation matrix and terminal-state
overlap table.

A moscot-only run on the full nine-stage joint object is in
`Notebooks/cellrank_joint_moscot.ipynb`; velocity cannot participate there.

### Status

**Not yet complete.** Four failures so far, every one a version incompatibility
rather than an analysis error (§12 patches and shims above). Job `61837986` is
running at time of writing. The preprocessing chain, the numpy-2 stochastic
patch, and `scv.tl.velocity_graph` are all confirmed working on the full 68k
cells; the failures have been strictly downstream of those.

---

## Figure layout

```
output_fig/
├── 01_qc/                  QC violins, UMAP by QC metric
├── 02_pca_hvg/             HVG dispersion, scree, PCA scatter
├── 03_umap_unintegrated/   leiden, age/tissue/sample, per-age + per-tissue facets
├── 04_harmony_chip/        before/after, facets, hedgehog (REJECTED — see §7)
├── 05_hedgehog/            feature panels, dotplot, violin
├── 06_integration_brooks/  dataset comparison, before/after, per-stage facets
├── 07_cellrank/            velocity stream, macrostates, fate probabilities
└── 08_cellrank_joint/      moscot-only runs on the 9-stage object
```

Each notebook section re-points `sc.settings.figdir`, so the layout survives
re-runs rather than needing a manual tidy.

## Plotting conventions

Sparse gene expression uses grey for non-expressing cells and a single hue
light→dark for expressing cells, drawn last in ascending order, with the scale
clipped at the 99th percentile of expressing cells. scanpy's default `viridis`
puts its darkest end at *zero*, so on a 95%-zero gene the non-expressing majority
dominates the image and a few outliers compress everything else. Panels state how
many cells express the gene, so sparsity is explicit rather than inferred.
