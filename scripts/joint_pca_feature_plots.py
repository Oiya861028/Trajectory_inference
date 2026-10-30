#!/usr/bin/env python
"""PCA and feature plots for the joint devbrain + Brooks object.

Mirrors what Notebooks/inference.ipynb produces for devbrain alone, so the two
can be read side by side: PCA variance ratio, PC scatters before and after
Harmony, stage/dataset facets, and hedgehog-pathway feature plots with the
same grey-background / brightest-last contrast treatment.

Output: output_fig/09_joint_pca_features/
"""

import os

import anndata as ad
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import scanpy as sc
from matplotlib.colors import LinearSegmentedColormap

BASE = "/project/imoskowitz/yubin/Trajectory_inference/"
OUT = BASE + "output_fig/09_joint_pca_features/"
os.makedirs(OUT, exist_ok=True)
sc.settings.verbosity = 2
sc.settings.set_figure_params(dpi=100, dpi_save=200, frameon=False, figsize=(5, 5))

# same palette as inference.ipynb: viridis puts its darkest end at zero, which on
# a mostly-zero matrix lets the non-expressing majority dominate the figure
EXPR_CMAP = LinearSegmentedColormap.from_list(
    "expr", ["#FCC9B4", "#FB8A6A", "#E32F27", "#99000D"])
BG_GREY = "#DDDDDD"

HH = ["Shh", "Ptch1", "Smo", "Gli1", "Gli2", "Gli3", "Hhip"]
REGIONAL = ["Six3", "Foxg1", "Otx2", "En1", "Gbx2", "Hoxb1", "Sox2", "T"]

STAGE_ORDER = ["E7.0", "E7.5", "E7.75", "E8.0", "E8.25", "E8.5", "E8.75",
               "E9.0", "E10.0"]


def feature_scatter(adata, gene, ax, basis, pct=99.0, bg_size=1.0, fg_size=4.0):
    """One gene on `basis`, non-expressing cells as flat grey, brightest last."""
    xy = adata.obsm[basis]
    v = adata[:, gene].X
    v = np.asarray(v.todense()).ravel() if hasattr(v, "todense") else np.ravel(v)
    on = v > 0
    vmax = np.percentile(v[on], pct) if on.any() else 1.0
    ax.scatter(xy[~on, 0], xy[~on, 1], s=bg_size, c=BG_GREY, linewidths=0, rasterized=True)
    o = np.argsort(v[on])                       # brightest painted last
    pts, vals = xy[on][o], v[on][o]
    h = ax.scatter(pts[:, 0], pts[:, 1], s=fg_size, c=vals, cmap=EXPR_CMAP,
                   vmin=0, vmax=max(vmax, 1e-9), linewidths=0, rasterized=True)
    ax.set_title(f"{gene}   {on.sum():,} / {adata.n_obs:,} cells", fontsize=10)
    ax.set_xticks([]); ax.set_yticks([])
    for s in ax.spines.values():
        s.set_visible(False)
    cb = plt.colorbar(h, ax=ax, fraction=0.035, pad=0.01)
    cb.ax.tick_params(labelsize=7, length=2)
    cb.outline.set_visible(False)
    return on.sum(), float(v.max())


def cat_scatter(adata, key, ax, basis, order=None, size=1.2, legend=True):
    xy = adata.obsm[basis]
    vals = adata.obs[key].astype(str)
    cats = order or sorted(vals.unique())
    cats = [c for c in cats if c in set(vals)]
    cmap = plt.get_cmap("viridis" if len(cats) > 8 else "tab10")
    for i, c in enumerate(cats):
        m = (vals == c).values
        ax.scatter(xy[m, 0], xy[m, 1], s=size,
                   color=cmap(i / max(len(cats) - 1, 1) if len(cats) > 8 else i),
                   label=f"{c} ({m.sum():,})", linewidths=0, rasterized=True)
    ax.set_xticks([]); ax.set_yticks([])
    for s in ax.spines.values():
        s.set_visible(False)
    if legend:
        ax.legend(markerscale=8, fontsize=7, frameon=False, loc="center left",
                  bbox_to_anchor=(1.0, 0.5))
    return ax


def main():
    print("loading joint object ...", flush=True)
    a = ad.read_h5ad(BASE + "data/devbrain_brooks_integrated.h5ad")
    print(a.shape, flush=True)
    a.obs["stage"] = a.obs["stage"].astype(str)

    # ---- 1. PCA variance ratio ------------------------------------------
    vr = a.uns["pca"]["variance_ratio"]
    fig, axes = plt.subplots(1, 2, figsize=(11, 4))
    axes[0].bar(np.arange(1, len(vr) + 1), vr * 100, color="#4878A6")
    axes[0].set_xlabel("principal component"); axes[0].set_ylabel("variance explained (%)")
    axes[0].set_title(f"Joint PCA: PC1 explains {vr[0]*100:.1f}%, "
                      f"top 50 explain {vr.sum()*100:.1f}%", fontsize=10)
    axes[1].plot(np.arange(1, len(vr) + 1), np.cumsum(vr) * 100, "o-", ms=3, color="#4878A6")
    axes[1].set_xlabel("principal component"); axes[1].set_ylabel("cumulative (%)")
    axes[1].set_title("Cumulative variance explained", fontsize=10)
    for ax in axes:
        ax.spines[["top", "right"]].set_visible(False)
    fig.tight_layout(); fig.savefig(OUT + "pca_variance_ratio.png", dpi=200, bbox_inches="tight")
    plt.close(fig)
    print(f"PC1 {vr[0]*100:.2f}%  PC1-10 {vr[:10].sum()*100:.1f}%  "
          f"PC1-50 {vr.sum()*100:.1f}%", flush=True)

    # ---- 2. PC scatters, uncorrected vs Harmony -------------------------
    # the point of the pair: if a PC separates the two datasets before Harmony
    # and not after, that PC was carrying batch rather than biology
    for key, order, fname in (("dataset", ["devbrain", "brooks"], "dataset"),
                              ("stage", STAGE_ORDER, "stage")):
        fig, axes = plt.subplots(2, 2, figsize=(13, 10))
        for row, (rep, label) in enumerate(((("X_pca"), "uncorrected"),
                                            (("X_pca_harmony"), "Harmony"))):
            for col, (i, j) in enumerate(((0, 1), (1, 2))):
                ax = axes[row, col]
                sub = ad.AnnData(obs=a.obs, obsm={"p": a.obsm[rep][:, [i, j]]})
                cat_scatter(sub, key, ax, "p", order=order,
                            legend=(col == 1))
                ax.set_title(f"{label}  PC{i+1} vs PC{j+1}", fontsize=10)
        fig.suptitle(f"Joint PCA coloured by {key}", fontsize=12)
        fig.tight_layout()
        fig.savefig(OUT + f"pca_scatter_{fname}.png", dpi=200, bbox_inches="tight")
        plt.close(fig)
        print(f"wrote pca_scatter_{fname}.png", flush=True)

    # ---- 3. UMAP, pre vs post Harmony -----------------------------------
    fig, axes = plt.subplots(2, 2, figsize=(13, 10))
    for row, (basis, label) in enumerate((("X_umap_pre", "before Harmony"),
                                          ("X_umap_post", "after Harmony"))):
        cat_scatter(a, "dataset", axes[row, 0], basis, order=["devbrain", "brooks"])
        axes[row, 0].set_title(f"{label} - dataset", fontsize=10)
        cat_scatter(a, "stage", axes[row, 1], basis, order=STAGE_ORDER)
        axes[row, 1].set_title(f"{label} - stage", fontsize=10)
    fig.tight_layout(); fig.savefig(OUT + "umap_pre_post_harmony.png", dpi=200, bbox_inches="tight")
    plt.close(fig)
    print("wrote umap_pre_post_harmony.png", flush=True)

    # ---- 4. stage facets ------------------------------------------------
    # one panel per stage: overlapping stages in a single UMAP are unreadable
    stages = [s for s in STAGE_ORDER if s in set(a.obs["stage"])]
    ncol = 5; nrow = int(np.ceil(len(stages) / ncol))
    fig, axes = plt.subplots(nrow, ncol, figsize=(3.1 * ncol, 3.1 * nrow))
    xy = a.obsm["X_umap_post"]
    for ax, s in zip(np.ravel(axes), stages):
        m = (a.obs["stage"] == s).values
        ax.scatter(xy[~m, 0], xy[~m, 1], s=0.6, c=BG_GREY, linewidths=0, rasterized=True)
        ds = a.obs.loc[m, "dataset"].astype(str)
        for d, col in (("devbrain", "#D62728"), ("brooks", "#1F77B4")):
            mm = np.where(m)[0][(ds == d).values]
            if len(mm):
                ax.scatter(xy[mm, 0], xy[mm, 1], s=1.4, c=col, linewidths=0,
                           rasterized=True, label=f"{d} ({len(mm):,})")
        ax.set_title(s, fontsize=10); ax.set_xticks([]); ax.set_yticks([])
        for sp in ax.spines.values():
            sp.set_visible(False)
        ax.legend(markerscale=6, fontsize=6, frameon=False, loc="lower left")
    for ax in np.ravel(axes)[len(stages):]:
        ax.axis("off")
    fig.suptitle("Joint UMAP (post-Harmony), one panel per stage", fontsize=12)
    fig.tight_layout(); fig.savefig(OUT + "umap_facet_stage.png", dpi=200, bbox_inches="tight")
    plt.close(fig)
    print("wrote umap_facet_stage.png", flush=True)

    # ---- 5. feature plots -----------------------------------------------
    for panel, genes in (("hedgehog", HH), ("regional", REGIONAL)):
        genes = [g for g in genes if g in a.var_names]
        for basis, tag in (("X_umap_post", "umap"), ("X_pca_harmony", "pca")):
            ncol = 4; nrow = int(np.ceil(len(genes) / ncol))
            fig, axes = plt.subplots(nrow, ncol, figsize=(4.6 * ncol, 4.0 * nrow))
            for ax, g in zip(np.ravel(axes), genes):
                n_on, mx = feature_scatter(a, g, ax, basis)
                if tag == "umap":
                    print(f"  {panel:9s} {g:6s} expressing {n_on:6,}  max {mx:.2f}", flush=True)
            for ax in np.ravel(axes)[len(genes):]:
                ax.axis("off")
            ttl = "post-Harmony UMAP" if tag == "umap" else "Harmony PC1 vs PC2"
            fig.suptitle(f"{panel.capitalize()} genes on the joint {ttl}", fontsize=12)
            fig.tight_layout()
            fig.savefig(OUT + f"features_{panel}_{tag}.png", dpi=200, bbox_inches="tight")
            plt.close(fig)
            print(f"wrote features_{panel}_{tag}.png", flush=True)

    print(f"\nall figures -> {OUT}")


if __name__ == "__main__":
    main()
