#!/usr/bin/env python
"""Quantify how far apart devbrain (E7-E10) and Brooks 2025 (E7.5-E8.75) really are.

Everything streams over the CSR matrices in cell blocks, so this runs inside the
8 GB login-node cap instead of needing a compute node.

Reports
  1. per-cell sequencing depth / complexity / mito / ribo, per dataset and stage
  2. gene-space overlap and detection-rate differences
  3. pseudobulk expression correlation between the datasets, stage by stage --
     with the shared stages (E8.0, E8.5) as the like-for-like comparison
  4. how much of each PC's variance the dataset label alone explains
"""

import os

import h5py
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

BASE = "/project/imoskowitz/yubin/Trajectory_inference/"
DEV = BASE + "data/interim/devbrain_E7-E10_processed.h5ad"
BROOKS = ("/project/imoskowitz/kdreyer/public_datasets/"
          "001_Brooks2025_GSE273804/WT_timeseries/GSE273804_FVB_All.h5ad")
OUT = BASE + "results/figures/06_integration_brooks/"
os.makedirs(OUT, exist_ok=True)
BLOCK = 4000


def decode(obj):
    if isinstance(obj, h5py.Group):
        cats = obj["categories"].asstr()[:]
        codes = obj["codes"][:]
        return np.where(codes >= 0, cats[np.clip(codes, 0, None)], "")
    return obj.asstr()[:] if obj.dtype.kind in "OS" else obj[:]


def scan(path, counts_key, stage_col, stage_map):
    """One pass: per-cell QC plus per-stage pseudobulk sums."""
    with h5py.File(path, "r") as f:
        var_names = np.array([str(v) for v in f["var/_index"].asstr()[:]])
        n_obs, n_var = tuple(f["X"].attrs["shape"])
        stage = np.array([stage_map.get(str(s), str(s))
                          for s in decode(f["obs"][stage_col])])
        g = f[counts_key]
        indptr = g["indptr"][:]
        data, indices = g["data"], g["indices"]

        is_mt = np.array([v.startswith("mt-") for v in var_names])
        is_ribo = np.array([v.startswith(("Rps", "Rpl")) for v in var_names])

        stages = sorted(set(stage.tolist()))
        s_idx = {s: i for i, s in enumerate(stages)}
        pseudo = np.zeros((len(stages), n_var), dtype=np.float64)
        n_per_stage = np.zeros(len(stages), dtype=np.int64)
        detected = np.zeros((len(stages), n_var), dtype=np.int64)

        total = np.zeros(n_obs); ngene = np.zeros(n_obs)
        mt_frac = np.zeros(n_obs); ribo_frac = np.zeros(n_obs)

        for start in range(0, n_obs, BLOCK):
            stop = min(start + BLOCK, n_obs)
            lo, hi = indptr[start], indptr[stop]
            d = data[lo:hi]; idx = indices[lo:hi]
            rel = indptr[start:stop + 1] - lo
            for r in range(stop - start):
                a, b = rel[r], rel[r + 1]
                dd, ii = d[a:b], idx[a:b]
                tot = dd.sum()
                total[start + r] = tot
                ngene[start + r] = len(ii)
                if tot > 0:
                    mt_frac[start + r] = dd[is_mt[ii]].sum() / tot
                    ribo_frac[start + r] = dd[is_ribo[ii]].sum() / tot
                si = s_idx[stage[start + r]]
                np.add.at(pseudo[si], ii, dd)
                np.add.at(detected[si], ii, 1)
                n_per_stage[si] += 1

    qc = pd.DataFrame({"stage": stage, "total_counts": total, "n_genes": ngene,
                       "pct_mt": 100 * mt_frac, "pct_ribo": 100 * ribo_frac})
    return {"var_names": var_names, "qc": qc, "stages": stages, "pseudo": pseudo,
            "n_per_stage": n_per_stage, "detected": detected, "n_obs": n_obs}


DEV_MAP = {"e7.0": "E7.0", "e8.0": "E8.0", "e8.5": "E8.5", "e9.0": "E9.0",
           "e10.0": "E10.0"}
print("scanning devbrain ...", flush=True)
dev = scan(DEV, "layers/counts", "age", DEV_MAP)
print("scanning brooks ...", flush=True)
bro = scan(BROOKS, "layers/raw_counts", "stage", {})

# ---------------------------------------------------------------- 1. depth ---
print("\n" + "=" * 78)
print("1. SEQUENCING DEPTH AND COMPLEXITY")
print("=" * 78)
rows = []
for name, d in (("devbrain", dev), ("brooks", bro)):
    q = d["qc"]
    rows.append({
        "dataset": name, "cells": d["n_obs"],
        "median_UMI": int(np.median(q["total_counts"])),
        "median_genes": int(np.median(q["n_genes"])),
        "genes_per_10k_UMI": round(float(np.median(
            q["n_genes"] / q["total_counts"] * 1e4)), 1),
        "median_pct_mt": round(float(np.median(q["pct_mt"])), 2),
        "median_pct_ribo": round(float(np.median(q["pct_ribo"])), 1),
    })
summary = pd.DataFrame(rows).set_index("dataset")
print(summary.to_string())
print(f"\ndepth ratio (brooks / devbrain): "
      f"{summary.loc['brooks','median_UMI']/summary.loc['devbrain','median_UMI']:.2f}x UMI, "
      f"{summary.loc['brooks','median_genes']/summary.loc['devbrain','median_genes']:.2f}x genes")

print("\nby stage:")
per_stage = []
for name, d in (("devbrain", dev), ("brooks", bro)):
    g = d["qc"].groupby("stage")
    t = pd.DataFrame({"cells": g.size(),
                      "median_UMI": g["total_counts"].median().astype(int),
                      "median_genes": g["n_genes"].median().astype(int),
                      "median_pct_mt": g["pct_mt"].median().round(2)})
    t["dataset"] = name
    per_stage.append(t.reset_index())
per_stage = pd.concat(per_stage)
print(per_stage.set_index(["dataset", "stage"]).to_string())

# ----------------------------------------------------------- 2. gene space ---
print("\n" + "=" * 78)
print("2. GENE SPACE")
print("=" * 78)
dset, bset = set(dev["var_names"].tolist()), set(bro["var_names"].tolist())
shared = sorted(dset & bset)
print(f"devbrain {len(dset):,} genes | brooks {len(bset):,} | shared {len(shared):,}")
print(f"  devbrain-only {len(dset - bset):,}   brooks-only {len(bset - dset):,}")
print(f"  shared covers {100*len(shared)/len(dset):.1f}% of devbrain, "
      f"{100*len(shared)/len(bset):.1f}% of brooks")

d_pos = {g: i for i, g in enumerate(dev["var_names"])}
b_pos = {g: i for i, g in enumerate(bro["var_names"])}
di = np.array([d_pos[g] for g in shared]); bi = np.array([b_pos[g] for g in shared])

d_det = dev["detected"].sum(0)[di] / dev["n_obs"]
b_det = bro["detected"].sum(0)[bi] / bro["n_obs"]
print(f"\nmean detection rate per shared gene: devbrain {100*d_det.mean():.1f}%, "
      f"brooks {100*b_det.mean():.1f}%")
print(f"genes detected in >10% of cells: devbrain {(d_det>0.1).sum():,}, "
      f"brooks {(b_det>0.1).sum():,}")

# -------------------------------------------------- 3. pseudobulk agreement ---
print("\n" + "=" * 78)
print("3. PSEUDOBULK EXPRESSION AGREEMENT")
print("=" * 78)


def cp10k_log(mat, idx):
    sub = mat[:, idx]
    tot = sub.sum(1, keepdims=True)
    return np.log1p(sub / np.maximum(tot, 1) * 1e4)


dev_pb = cp10k_log(dev["pseudo"], di)
bro_pb = cp10k_log(bro["pseudo"], bi)
dev_stages, bro_stages = dev["stages"], bro["stages"]

corr = pd.DataFrame(index=dev_stages, columns=bro_stages, dtype=float)
for i, ds in enumerate(dev_stages):
    for j, bs in enumerate(bro_stages):
        corr.loc[ds, bs] = float(np.corrcoef(dev_pb[i], bro_pb[j])[0, 1])
print("Pearson r of log pseudobulk, devbrain (rows) vs brooks (cols):")
print(corr.round(3).to_string())

print("\nwithin-dataset, consecutive stages (the scale of real biological change):")
for name, pb, st in (("devbrain", dev_pb, dev_stages), ("brooks", bro_pb, bro_stages)):
    for a in range(len(st) - 1):
        r = float(np.corrcoef(pb[a], pb[a + 1])[0, 1])
        print(f"  {name:9s} {st[a]:6s} vs {st[a+1]:6s}  r = {r:.3f}")

print("\nSHARED STAGES - same nominal timepoint, different dataset:")
for s in sorted(set(dev_stages) & set(bro_stages)):
    r = corr.loc[s, s]
    print(f"  {s:6s} devbrain vs brooks  r = {r:.3f}")
print("  (compare against the within-dataset numbers above: if cross-dataset r at the")
print("   same stage is well below within-dataset r across adjacent stages, the batch")
print("   effect is larger than one timepoint of development)")

# --------------------------------------------------------- 4. PC attribution --
print("\n" + "=" * 78)
print("4. HOW MUCH PC VARIANCE IS THE DATASET LABEL?  (pre-integration)")
print("=" * 78)
print("computed in the integration notebook on the joint PCA; here we report the")
print("pseudobulk distance instead, which needs no joint embedding:")
d_mean = dev_pb.mean(0); b_mean = bro_pb.mean(0)
print(f"  overall pseudobulk r (all stages pooled): {np.corrcoef(d_mean, b_mean)[0,1]:.3f}")
diff = d_mean - b_mean
top = np.argsort(-np.abs(diff))[:15]
print("\n  genes most discordant between datasets (log CP10K difference):")
for i in top:
    print(f"    {shared[i]:14s} devbrain {d_mean[i]:6.2f}  brooks {b_mean[i]:6.2f}  "
          f"delta {diff[i]:+.2f}")

# ------------------------------------------------------------------- plots ---
fig, axes = plt.subplots(2, 2, figsize=(13, 10))

ax = axes[0, 0]
for name, d, c in (("devbrain", dev, "#1f77b4"), ("brooks", bro, "#E32F27")):
    ax.hist(np.log10(d["qc"]["total_counts"] + 1), bins=80, alpha=0.55, color=c,
            label=f"{name} (median {int(np.median(d['qc']['total_counts'])):,})",
            density=True)
ax.set_xlabel("log10 UMI per cell"); ax.set_ylabel("density")
ax.set_title("Sequencing depth", fontsize=11); ax.legend(fontsize=9, frameon=False)

ax = axes[0, 1]
for name, d, c in (("devbrain", dev, "#1f77b4"), ("brooks", bro, "#E32F27")):
    ax.hist(d["qc"]["n_genes"], bins=80, alpha=0.55, color=c, density=True,
            label=f"{name} (median {int(np.median(d['qc']['n_genes'])):,})")
ax.set_xlabel("genes detected per cell"); ax.set_ylabel("density")
ax.set_title("Library complexity", fontsize=11); ax.legend(fontsize=9, frameon=False)

ax = axes[1, 0]
im = ax.imshow(corr.values.astype(float), cmap="RdYlBu_r", vmin=float(corr.values.min()),
               vmax=1.0)
ax.set_xticks(range(len(bro_stages))); ax.set_xticklabels(bro_stages, rotation=45, fontsize=8)
ax.set_yticks(range(len(dev_stages))); ax.set_yticklabels(dev_stages, fontsize=8)
ax.set_xlabel("Brooks stage"); ax.set_ylabel("devbrain stage")
ax.set_title("Pseudobulk correlation across datasets", fontsize=11)
for i in range(len(dev_stages)):
    for j in range(len(bro_stages)):
        ax.text(j, i, f"{corr.values[i, j]:.2f}", ha="center", va="center", fontsize=7)
plt.colorbar(im, ax=ax, fraction=0.04)

ax = axes[1, 1]
ax.scatter(d_mean, b_mean, s=2, c="#777777", alpha=0.4, rasterized=True)
lim = [min(d_mean.min(), b_mean.min()), max(d_mean.max(), b_mean.max())]
ax.plot(lim, lim, color="#E32F27", lw=1, ls="--")
ax.set_xlabel("devbrain, mean log CP10K"); ax.set_ylabel("brooks, mean log CP10K")
ax.set_title(f"Shared genes (n={len(shared):,}), r = "
             f"{np.corrcoef(d_mean, b_mean)[0,1]:.3f}", fontsize=11)

for a in axes.ravel():
    for s in ("top", "right"):
        a.spines[s].set_visible(False)
fig.tight_layout()
fig.savefig(OUT + "dataset_comparison.png", dpi=200, bbox_inches="tight")
print(f"\nwrote {OUT}dataset_comparison.png")

summary.to_csv(BASE + "results/tables/metadata/dataset_comparison_summary.csv")
per_stage.to_csv(BASE + "results/tables/metadata/dataset_comparison_by_stage.csv", index=False)
corr.to_csv(BASE + "results/tables/metadata/dataset_pseudobulk_correlation.csv")
print("wrote comparison tables to results/tables/metadata/")
