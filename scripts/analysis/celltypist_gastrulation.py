#!/usr/bin/env python
"""Train CellTypist models on Pijuan-Sala 2019 and annotate the devbrain cells.

No mouse-gastrulation model exists in the CellTypist zoo (60 models checked);
the nearest, Developing_Mouse_Brain.pkl, is trained on La Manno 2021 - the
dataset being annotated here - so it is circular.

Two models, because one stage range cannot answer both questions:

  A  E6.5-E7.5, `celltype_PijuanSala2019`
     At E7.0 Pijuan-Sala holds 13 neurectoderm cells out of 14,749; the neural
     plate has not formed. So this model cannot label "brain" - what it can do
     is separate the neural-COMPETENT epiblast from extraembryonic, mesodermal
     and endodermal cells, which is the useful operation at E7.0.

  B  E7.5-E8.5, `celltype_extended_atlas`
     Brain-region labels (fore/mid/hindbrain progenitors, neural tube, spinal
     cord) first appear at E7.75-E8.5. This model can call brain identity, and
     is applied to devbrain E8.0 onward.

Outputs
  results/models/celltypist/*.pkl
  data/processed/devbrain_celltypist.h5ad        all cells + predictions from both models
  data/processed/devbrain_neural_lineage.h5ad    the isolated neural/brain subset
  results/tables/metadata/celltypist_*.csv       composition tables
"""

import os
import re

import anndata as ad
import celltypist
import numpy as np
import pandas as pd
import scanpy as sc
from celltypist import models as ct_models

BASE = "/project/imoskowitz/yubin/Trajectory_inference/"
PIJUAN = ("/project/imoskowitz/kdreyer/public_datasets/002_PijuanSala2019/"
          "gastrulation_ps2019.h5ad")
DEVBRAIN = BASE + "data/interim/devbrain_E7-E10_processed.h5ad"
MODEL_DIR = BASE + "results/models/celltypist/"
META = BASE + "results/tables/metadata/"
N_JOBS = int(os.environ.get("SLURM_CPUS_PER_TASK", 8))
MIN_CELLS_PER_LABEL = 20

os.makedirs(MODEL_DIR, exist_ok=True)

# ---------------------------------------------------------------------------
# Marker panels from the literature. Sources:
#   - Mahadevan et al. 2024/2025, eLife 102819 "A single-cell atlas of spatial and
#     temporal gene expression in the mouse cranial neural plate" (E8.5-E9.0):
#     forebrain Otx2/Six3/Otx1, telencephalon Foxg1/Lhx2, diencephalon Barhl2,
#     midbrain+r1 En1/Fgf8/Pax2/Pax5/Wnt1, MHB Fgf8, hindbrain Egr2/Gbx2/Hoxa2/
#     Hoxb2/Hoxb3, posterior rhombomeres Hoxb1/Egr2.
#   - Martinez-Barbera et al. 2001, Development 128:4789 - Otx2/Gbx2 mutual
#     antagonism fixes the midbrain-hindbrain border, already at ~E7.5.
#   - Thomas & Beddington 1996, Curr Biol 6:1487 - Hesx1 in AVE then anterior
#     ectoderm (prospective forebrain).
#   - Peng et al. 2012, Development 139:4847 - Six3 and Sox1 in anterior
#     neuroectoderm from ~E7.0-E7.5, earlier than previously reported; Dlx5/
#     Hesx1/Sox1/Sox2 as anterior non-neural vs neural markers.
#   - Lagutin et al. 2003, Genes Dev 17:368 - Six3 represses Wnt in anterior
#     neuroectoderm; required for forebrain.
# Panels are scored with sc.tl.score_genes, independently of CellTypist, so the
# label transfer and the marker evidence can disagree visibly.
MARKER_PANELS = {
    "anterior_neuroectoderm": ["Six3", "Hesx1", "Otx2", "Sox1", "Sox2", "Otx1"],
    "forebrain":              ["Six3", "Otx2", "Otx1", "Foxg1", "Lhx2", "Barhl2", "Hesx1"],
    "midbrain_r1":            ["En1", "En2", "Pax2", "Pax5", "Wnt1", "Fgf8", "Otx2"],
    "hindbrain":              ["Gbx2", "Egr2", "Hoxa2", "Hoxb1", "Hoxb2", "Hoxb3", "Mafb"],
    "spinal_caudal":          ["Cdx1", "Cdx2", "Cdx4", "Hoxb9", "Nkx1-2"],
    "floor_plate":            ["Shh", "Foxa2", "Arx"],
    "neural_crest":           ["Sox10", "Foxd3", "Pax3", "Tfap2a"],
    "non_neural_ectoderm":    ["Dlx5", "Tfap2a", "Krt8", "Krt18", "Grhl3"],
    "epiblast_pluripotent":   ["Pou5f1", "Nanog", "Utf1", "Sox2"],
    "primitive_streak_meso":  ["T", "Mesp1", "Mixl1", "Eomes"],
    "endoderm":               ["Sox17", "Foxa2", "Ttr", "Afp"],
    "extraembryonic":         ["Elf5", "Tfap2c", "Rhox5", "Ttr"],
    "blood":                  ["Hba-x", "Hbb-bh1", "Runx1"],
}

# Label groups, matched case-insensitively against predicted labels.
#
# At E7.0 there is no brain to find: Pijuan-Sala has 13 neurectoderm cells out of
# 14,749 there, and the neural plate forms ~E7.5. The filter is therefore
# deliberately general - it EXCLUDES the clearly non-neural lineages rather than
# requiring a positive neural call, so neural-competent epiblast is retained.
EXCLUDE_LINEAGE = (
    r"^exe |extraembryonic|visceral endoderm|parietal endoderm|def\. endoderm|"
    r"\bgut\b|blood|erythroid|haematoendothelial|\bpgc\b|mesenchyme|"
    r"somitic|paraxial|pharyngeal|nascent mesoderm|mixed mesoderm|intermediate mesoderm|"
    r"lateral plate|cardiomyocyte|endothelium|allantois|amnio|chorion|"
    r"primitive streak|notochord|node\b"
)
# positive neural evidence, used for reporting rather than for the filter itself
NEURAL_POSITIVE = (r"epiblast|neurectoderm|neuroectoderm|^ectoderm$|neural|"
                   r"forebrain|midbrain|hindbrain|spinal|floor plate|brain")


def log_norm(a):
    """CellTypist expects log1p of CP10K."""
    sc.pp.normalize_total(a, target_sum=1e4)
    sc.pp.log1p(a)
    return a


def train(adata, label_key, stages, name, top_genes=500):
    sub = adata[adata.obs["stage"].isin(stages)].copy()
    counts = sub.obs[label_key].value_counts()
    keep = counts[counts >= MIN_CELLS_PER_LABEL].index
    dropped = counts[counts < MIN_CELLS_PER_LABEL]
    sub = sub[sub.obs[label_key].isin(keep)].copy()
    sub.obs[label_key] = sub.obs[label_key].astype(str)

    print(f"\n=== training {name} ===", flush=True)
    print(f"  stages {stages}  ->  {sub.n_obs:,} cells x {sub.n_vars:,} genes")
    print(f"  {len(keep)} labels kept (>= {MIN_CELLS_PER_LABEL} cells); "
          f"{len(dropped)} dropped: {list(dropped.index)[:6]}")
    print(sub.obs[label_key].value_counts().to_string())

    model = celltypist.train(
        sub, labels=label_key, n_jobs=N_JOBS,
        feature_selection=True, top_genes=top_genes,
        check_expression=False,          # already log1p CP10K
    )
    path = MODEL_DIR + f"{name}.pkl"
    model.write(path)
    print(f"  wrote {path}  ({len(model.cell_types)} classes, "
          f"{len(model.features):,} features)")
    del sub
    return path


def annotate(dev, model_path, prefix, over_clustering="leiden"):
    print(f"\n=== annotating with {os.path.basename(model_path)} ===", flush=True)
    res = celltypist.annotate(dev, model=model_path, majority_voting=True,
                              over_clustering=over_clustering)
    lab = res.predicted_labels
    dev.obs[f"{prefix}_raw"] = lab["predicted_labels"].values
    dev.obs[f"{prefix}"] = lab["majority_voting"].values
    conf = res.probability_matrix.max(axis=1)
    dev.obs[f"{prefix}_conf"] = np.asarray(conf).ravel()
    print(dev.obs[f"{prefix}"].value_counts().head(20).to_string())
    return dev


def main():
    print("loading Pijuan-Sala ...", flush=True)
    pij = ad.read_h5ad(PIJUAN)
    pij.var_names_make_unique()
    print(f"  {pij.shape}")
    pij = log_norm(pij)

    model_a = train(pij, "celltype_PijuanSala2019",
                    ["E6.5", "E6.75", "E7.0", "E7.25", "E7.5"],
                    "Pijuan2019_gastrulation_E65-E75")
    model_b = train(pij, "celltype_extended_atlas",
                    ["E7.5", "E7.75", "E8.0", "E8.25", "E8.5"],
                    "Pijuan2019_extended_E75-E85")
    del pij

    print("\nloading devbrain ...", flush=True)
    dev = ad.read_h5ad(DEVBRAIN)          # X is already log1p CP10K
    print(f"  {dev.shape}")

    dev = annotate(dev, model_a, "ct_gastrulation")
    dev = annotate(dev, model_b, "ct_extended")

    # ---- marker scores (independent of CellTypist) -------------------------
    print("\n=== marker panel scores ===", flush=True)
    for panel, genes in MARKER_PANELS.items():
        present = [g for g in genes if g in dev.var_names]
        missing = [g for g in genes if g not in dev.var_names]
        if not present:
            print(f"  {panel:24s} SKIPPED - no genes present")
            continue
        sc.tl.score_genes(dev, present, score_name=f"score_{panel}")
        print(f"  {panel:24s} {len(present)}/{len(genes)} genes"
              + (f"  missing: {missing}" if missing else ""))

    # ---- lineage calls ----------------------------------------------------
    g = dev.obs["ct_gastrulation"].astype(str)
    e = dev.obs["ct_extended"].astype(str)
    excluded = (g.str.contains(EXCLUDE_LINEAGE, case=False, regex=True) |
                e.str.contains(EXCLUDE_LINEAGE, case=False, regex=True))
    dev.obs["excluded_lineage"] = excluded
    dev.obs["neural_positive"] = (g.str.contains(NEURAL_POSITIVE, case=False, regex=True) |
                                  e.str.contains(NEURAL_POSITIVE, case=False, regex=True))
    # the general filter: keep anything not confidently assigned to a non-neural
    # lineage by either model
    dev.obs["is_neural"] = ~excluded

    print("\n=== what the exclusion removed (top labels) ===")
    for col, series in (("ct_gastrulation", g), ("ct_extended", e)):
        rm = series[excluded].value_counts().head(8)
        print(f"  {col}:")
        print("    " + rm.to_string().replace("\n", "\n    "))

    print("\n=== lineage calls by stage ===")
    tab = pd.crosstab(dev.obs["age"], dev.obs["is_neural"])
    tab["pct_neural"] = (100 * tab[True] / tab.sum(1)).round(1) if True in tab else np.nan
    print(tab.to_string())
    tab.to_csv(META + "celltypist_neural_by_stage.csv")

    for col in ("ct_gastrulation", "ct_extended"):
        ct = pd.crosstab(dev.obs[col], dev.obs["age"])
        ct.to_csv(META + f"celltypist_{col}_by_stage.csv")
        print(f"\n=== {col} x stage (top 15) ===")
        print(ct.sort_values(ct.columns[0], ascending=False).head(15).to_string())

    print("\n=== mean confidence by model ===")
    print(dev.obs[["ct_gastrulation_conf", "ct_extended_conf"]].describe().round(3).to_string())

    dev.write_h5ad(BASE + "data/processed/devbrain_celltypist.h5ad", compression="gzip")
    print(f"\nwrote data/processed/devbrain_celltypist.h5ad: {dev.shape}")

    neural = dev[dev.obs["is_neural"]].copy()
    neural.write_h5ad(BASE + "data/processed/devbrain_neural_lineage.h5ad", compression="gzip")
    print(f"wrote data/processed/devbrain_neural_lineage.h5ad: {neural.shape} "
          f"({100*neural.n_obs/dev.n_obs:.1f}% of cells)")
    print(neural.obs["age"].value_counts().sort_index().to_string())


if __name__ == "__main__":
    main()
