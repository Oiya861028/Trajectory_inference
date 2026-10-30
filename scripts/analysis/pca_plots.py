#!/usr/bin/env python
"""PCA figures for the devbrain and joint objects, drawn by one code path.

The two sets were previously drawn differently - devbrain through scanpy's
sc.pl.pca / sc.pl.pca_variance_ratio, the joint object through bespoke
matplotlib - so they could not be compared side by side. This script replaces
both with the same grammar:

  pca_variance.png     scree + cumulative, with the 30-PC graph cutoff marked
  pca_scatter_<key>.png   rows = representation (uncorrected / Harmony),
                          cols = PC1-PC2 and PC2-PC3, coloured by <key>

Only obs/obsm/uns are read, so this runs without loading any expression matrix.

Outputs
  results/figures/02_pca_hvg/            devbrain
  results/figures/09_joint_pca_features/ joint
"""

import os

import anndata as ad
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

BASE = "/project/imoskowitz/yubin/Trajectory_inference/"
FIG = BASE + "results/figures/"

# number of PCs the exploratory kNN graph actually consumes:
# sc.pp.neighbors(n_neighbors=15, n_pcs=30) in both notebooks
N_PCS_GRAPH = 30

BLUE, RED = "#4878A6", "#C23B22"
GREY = "#8A8A8A"
STAGE_ORDER = ["e7.0", "e8.0", "e8.5", "e9.0", "e10.0",
               "E7.0", "E7.5", "E7.75", "E8.0", "E8.25", "E8.5", "E8.75",
               "E9.0", "E10.0"]


def tidy(ax):
    ax.set_xticks([]); ax.set_yticks([])
    for s in ax.spines.values():
        s.set_visible(False)


def variance_figure(adata, out, label):
    vr = np.asarray(adata.uns["pca"]["variance_ratio"]) * 100
    n = len(vr)
    x = np.arange(1, n + 1)
    cum = np.cumsum(vr)

    fig, axes = plt.subplots(1, 2, figsize=(11, 3.8))
    cols = [BLUE if i < N_PCS_GRAPH else GREY for i in range(n)]
    axes[0].bar(x, vr, color=cols, width=0.85)
    axes[0].axvline(N_PCS_GRAPH + 0.5, color=RED, lw=1.2, ls="--")
    axes[0].annotate(f"graph uses first {N_PCS_GRAPH}",
                     xy=(N_PCS_GRAPH + 0.5, vr.max() * 0.92),
                     xytext=(N_PCS_GRAPH + 3, vr.max() * 0.92),
                     color=RED, fontsize=9, va="center")
    axes[0].set_xlabel("principal component")
    axes[0].set_ylabel("variance explained (%)")
    axes[0].set_title(f"{label} — PC1 {vr[0]:.1f}%, PC2 {vr[1]:.1f}%", fontsize=10)

    axes[1].plot(x, cum, "-", color=BLUE, lw=1.6)
    axes[1].plot(x[:N_PCS_GRAPH], cum[:N_PCS_GRAPH], "o", color=BLUE, ms=3)
    axes[1].plot(x[N_PCS_GRAPH:], cum[N_PCS_GRAPH:], "o", color=GREY, ms=3)
    axes[1].axvline(N_PCS_GRAPH + 0.5, color=RED, lw=1.2, ls="--")
    axes[1].annotate(f"{cum[N_PCS_GRAPH-1]:.1f}% at PC{N_PCS_GRAPH}\n"
                     f"{cum[-1]:.1f}% at PC{n}",
                     xy=(N_PCS_GRAPH + 2, cum[N_PCS_GRAPH - 1] * 0.55),
                     color=RED, fontsize=9)
    axes[1].set_xlabel("principal component")
    axes[1].set_ylabel("cumulative variance (%)")
    axes[1].set_title("Cumulative", fontsize=10)

    for ax in axes:
        ax.spines[["top", "right"]].set_visible(False)
        ax.set_xlim(0, n + 1)
    fig.tight_layout()
    fig.savefig(out + "pca_variance.png", dpi=200, bbox_inches="tight")
    plt.close(fig)
    print(f"  pca_variance.png   PC1 {vr[0]:.2f}%  PC1-{N_PCS_GRAPH} "
          f"{cum[N_PCS_GRAPH-1]:.1f}%  PC1-{n} {cum[-1]:.1f}%", flush=True)


def scatter_figure(adata, out, label, key, reps, size=1.1, order=None):
    vals = adata.obs[key].astype(str).values
    cats = [c for c in (order or sorted(set(vals))) if c in set(vals)]
    if order is None and key in ("age", "stage"):
        cats = [c for c in STAGE_ORDER if c in set(vals)]
    cmap = plt.get_cmap("viridis" if len(cats) > 10 else "tab10")
    colours = {c: (cmap(i / max(len(cats) - 1, 1)) if len(cats) > 10 else cmap(i))
               for i, c in enumerate(cats)}

    nrow, pairs = len(reps), [(0, 1), (1, 2)]
    fig, axes = plt.subplots(nrow, 2, figsize=(11.5, 5.0 * nrow), squeeze=False)
    for r, (rep, rep_label) in enumerate(reps):
        xy = np.asarray(adata.obsm[rep])
        for c, (i, j) in enumerate(pairs):
            ax = axes[r][c]
            for cat in cats:
                m = vals == cat
                ax.scatter(xy[m, i], xy[m, j], s=size, color=colours[cat],
                           linewidths=0, rasterized=True,
                           label=f"{cat} ({int(m.sum()):,})")
            tidy(ax)
            ax.set_title(f"{rep_label}   PC{i+1} vs PC{j+1}", fontsize=10)
            if c == 1:
                ax.legend(markerscale=9, fontsize=7.5, frameon=False,
                          loc="center left", bbox_to_anchor=(1.01, 0.5))
    fig.suptitle(f"{label} — PCA coloured by {key}", fontsize=12)
    fig.tight_layout()
    fig.savefig(out + f"pca_scatter_{key}.png", dpi=200, bbox_inches="tight")
    plt.close(fig)
    print(f"  pca_scatter_{key}.png  {len(cats)} levels, {nrow} representation(s)",
          flush=True)


def main():
    jobs = [
        dict(path=BASE + "data/interim/devbrain_E7-E10_processed.h5ad",
             out=FIG + "02_pca_hvg/", label="devbrain E7–E10",
             reps=[("X_pca", "uncorrected"),
                   ("X_pca_harmony", "Harmony on chip (rejected)")],
             keys=["age", "tissue", "sample"]),
        dict(path=BASE + "data/processed/devbrain_brooks_integrated.h5ad",
             out=FIG + "09_joint_pca_features/", label="devbrain + Brooks",
             reps=[("X_pca", "uncorrected"),
                   ("X_pca_harmony", "Harmony on dataset")],
             keys=["stage", "dataset"]),
    ]
    for j in jobs:
        print(f"\n=== {j['label']} ===", flush=True)
        os.makedirs(j["out"], exist_ok=True)
        a = ad.read_h5ad(j["path"], backed="r")
        if "stage" in j["keys"] and "stage" not in a.obs:
            a.obs["stage"] = a.obs["age"].astype(str)
        print(f"  {a.shape}", flush=True)
        variance_figure(a, j["out"], j["label"])
        for key in j["keys"]:
            if key in a.obs:
                scatter_figure(a, j["out"], j["label"], key, j["reps"])
            else:
                print(f"  skip {key}: not in obs")
        a.file.close()
    print("\ndone")


if __name__ == "__main__":
    main()
