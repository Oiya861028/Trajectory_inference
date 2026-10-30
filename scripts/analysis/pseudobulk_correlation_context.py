#!/usr/bin/env python
"""Why is pseudobulk r between E7.0 and E10.0 as high as 0.963?

Computes a *ceiling* (two random halves of the same stage, where the only
difference is sampling noise) and a *floor*, then re-measures the same
comparisons under metrics that are not dominated by the mean-expression axis:
genes expressed above a floor, stage-variable genes only, Spearman, and the
count of genes that actually move.

Streams in cell blocks so it fits the login-node cap.
"""

import os

import h5py
import numpy as np
import pandas as pd

BASE = "/project/imoskowitz/yubin/Trajectory_inference/"
DEV = BASE + "data/interim/devbrain_E7-E10_processed.h5ad"
BROOKS = ("/project/imoskowitz/kdreyer/public_datasets/"
          "001_Brooks2025_GSE273804/WT_timeseries/GSE273804_FVB_All.h5ad")
OUT = BASE + "results/tables/metadata/"
BLOCK = 4000
rng = np.random.default_rng(0)


def decode(obj):
    if isinstance(obj, h5py.Group):
        cats = obj["categories"].asstr()[:]
        codes = obj["codes"][:]
        return np.where(codes >= 0, cats[np.clip(codes, 0, None)], "")
    return obj.asstr()[:] if obj.dtype.kind in "OS" else obj[:]


def pseudobulk(path, counts_key, stage_col, stage_map, split_halves=True):
    """Sum counts per gene per stage; optionally per random half of each stage."""
    with h5py.File(path, "r") as f:
        var_names = np.array([str(v) for v in f["var/_index"].asstr()[:]])
        n_obs, n_var = tuple(f["X"].attrs["shape"])
        stage = np.array([stage_map.get(str(s), str(s))
                          for s in decode(f["obs"][stage_col])])
        half = rng.integers(0, 2, size=n_obs) if split_halves else np.zeros(n_obs, int)

        stages = sorted(set(stage.tolist()))
        keys = [(s, h) for s in stages for h in (0, 1)]
        kpos = {k: i for i, k in enumerate(keys)}
        acc = np.zeros((len(keys), n_var), dtype=np.float64)

        g = f[counts_key]
        indptr = g["indptr"][:]
        data, indices = g["data"], g["indices"]
        for start in range(0, n_obs, BLOCK):
            stop = min(start + BLOCK, n_obs)
            lo, hi = indptr[start], indptr[stop]
            d, idx = data[lo:hi], indices[lo:hi]
            rel = indptr[start:stop + 1] - lo
            for r in range(stop - start):
                a, b = rel[r], rel[r + 1]
                np.add.at(acc[kpos[(stage[start + r], int(half[start + r]))]],
                          idx[a:b], d[a:b])
    return var_names, stages, keys, acc


def cp10k_log(mat):
    tot = mat.sum(1, keepdims=True)
    return np.log1p(mat / np.maximum(tot, 1) * 1e4)


DEV_MAP = {"e7.0": "E7.0", "e8.0": "E8.0", "e8.5": "E8.5", "e9.0": "E9.0",
           "e10.0": "E10.0"}
print("scanning devbrain ...", flush=True)
d_var, d_stages, d_keys, d_acc = pseudobulk(DEV, "layers/counts", "age", DEV_MAP)
print("scanning brooks ...", flush=True)
b_var, b_stages, b_keys, b_acc = pseudobulk(BROOKS, "layers/raw_counts", "stage", {})

shared = sorted(set(d_var) & set(b_var))
di = np.array([{g: i for i, g in enumerate(d_var)}[g] for g in shared])
bi = np.array([{g: i for i, g in enumerate(b_var)}[g] for g in shared])

d_log = cp10k_log(d_acc[:, di])
b_log = cp10k_log(b_acc[:, bi])
d_kp = {k: i for i, k in enumerate(d_keys)}
b_kp = {k: i for i, k in enumerate(b_keys)}


def dev_full(stage):
    return cp10k_log((d_acc[d_kp[(stage, 0)]] + d_acc[d_kp[(stage, 1)]])[None, di])[0]


def bro_full(stage):
    return cp10k_log((b_acc[b_kp[(stage, 0)]] + b_acc[b_kp[(stage, 1)]])[None, bi])[0]


def pear(a, b, mask=None):
    if mask is not None:
        a, b = a[mask], b[mask]
    return float(np.corrcoef(a, b)[0, 1])


def spear(a, b, mask=None):
    from scipy.stats import spearmanr
    if mask is not None:
        a, b = a[mask], b[mask]
    return float(spearmanr(a, b).statistic)


# ---- gene masks -----------------------------------------------------------
dev_mean = np.mean([dev_full(s) for s in d_stages], axis=0)
bro_mean = np.mean([bro_full(s) for s in b_stages], axis=0)
expressed = (dev_mean > np.log1p(1.0)) | (bro_mean > np.log1p(1.0))   # >1 CP10K
stage_var = np.var(np.vstack([dev_full(s) for s in d_stages]), axis=0)
top_var = np.zeros(len(shared), bool)
top_var[np.argsort(-stage_var)[:2000]] = True

print("\n" + "=" * 86)
print("CEILING: two random halves of the SAME stage (differ only by sampling noise)")
print("=" * 86)
print(f"{'comparison':34s} {'all genes':>10s} {'expressed':>10s} {'stage-var':>10s} {'spearman':>10s}")
for s in d_stages:
    a = cp10k_log(d_acc[d_kp[(s, 0)]][None, di])[0]
    b = cp10k_log(d_acc[d_kp[(s, 1)]][None, di])[0]
    print(f"  devbrain {s:6s} half A vs B     {pear(a,b):10.4f} {pear(a,b,expressed):10.4f} "
          f"{pear(a,b,top_var):10.4f} {spear(a,b,expressed):10.4f}")

print("\n" + "=" * 86)
print("THE COMPARISONS OF INTEREST")
print("=" * 86)
print(f"{'comparison':34s} {'all genes':>10s} {'expressed':>10s} {'stage-var':>10s} {'spearman':>10s}")
pairs = [
    ("devbrain E7.0 vs E10.0", dev_full("E7.0"), dev_full("E10.0")),
    ("devbrain E7.0 vs E8.0", dev_full("E7.0"), dev_full("E8.0")),
    ("devbrain E9.0 vs E10.0", dev_full("E9.0"), dev_full("E10.0")),
    ("dev E8.0 vs brooks E8.0", dev_full("E8.0"), bro_full("E8.0")),
    ("dev E8.5 vs brooks E8.5", dev_full("E8.5"), bro_full("E8.5")),
    ("dev E7.0 vs brooks E8.75", dev_full("E7.0"), bro_full("E8.75")),
]
rows = []
for name, a, b in pairs:
    r = dict(comparison=name, all_genes=pear(a, b), expressed=pear(a, b, expressed),
             stage_variable=pear(a, b, top_var), spearman=spear(a, b, expressed))
    rows.append(r)
    print(f"  {name:32s} {r['all_genes']:10.4f} {r['expressed']:10.4f} "
          f"{r['stage_variable']:10.4f} {r['spearman']:10.4f}")

print("\n" + "=" * 86)
print("WHY 'all genes' IS INFLATED")
print("=" * 86)
print(f"shared genes: {len(shared):,}")
print(f"  expressed above 1 CP10K in either dataset : {int(expressed.sum()):,} "
      f"({100*expressed.mean():.1f}%)")
print(f"  so {100*(1-expressed.mean()):.1f}% of the genes in the 'all genes' column are "
      f"near-zero in both\n  and contribute correlated noise around zero")

a7, a10 = dev_full("E7.0"), dev_full("E10.0")
lfc = a7 - a10
for thr in (1, 2):
    n = int((np.abs(lfc) > thr).sum())
    print(f"  genes moving >{thr} log1p unit between E7.0 and E10.0: {n:,} "
          f"({100*n/len(shared):.1f}%)")
print("  -> development changes a minority of genes; Pearson over all of them is")
print("     dominated by the shared mean-expression axis (ribosomal, housekeeping)")

pd.DataFrame(rows).to_csv(OUT + "pseudobulk_correlation_context.csv", index=False)
print(f"\nwrote {OUT}pseudobulk_correlation_context.csv")
