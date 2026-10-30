#!/usr/bin/env python
"""Merge the 19 velocyto looms onto the devbrain cells of the joint object.

Output: data/devbrain_velocity.h5ad -- devbrain cells only (Brooks has no
spliced/unspliced), but carrying the *joint* Harmony embedding so the graph
still benefits from the Brooks bridge when picking a root cell.

Joins on
  cells : loom '<library>:<barcode>x'  ->  devbrain '<sample>:<barcode>-1'
  genes : loom row Accession (Ensembl)  ->  devbrain var['gene_ids']

Looms store layers as dense gene x cell arrays (54,232 x ~3.5k), so each layer
is read in gene blocks and converted to sparse rather than materialised whole.
"""

import glob
import os

import anndata as ad
import h5py
import numpy as np
import pandas as pd
from scipy.sparse import csr_matrix, lil_matrix, vstack

BASE = "/project/imoskowitz/yubin/Trajectory_inference/"
PROCESSED = BASE + "data/devbrain_E7-E10_processed.h5ad"
INTEGRATED = BASE + "data/devbrain_brooks_integrated.h5ad"
LOOMS = sorted(glob.glob(BASE + "data/velocyto/loom/*.loom"))
MANIFEST = BASE + "data/metadata/samples_E7-E10.csv"
OUT = BASE + "data/devbrain_velocity.h5ad"
GENE_BLOCK = 6000
LAYERS = ("spliced", "unspliced", "ambiguous")


def main():
    print(f"{len(LOOMS)} looms", flush=True)

    # library id -> sample id, from the manifest
    man = pd.read_csv(MANIFEST)
    lib2sample = {r.bam_name.replace(".bad", "").replace(".bam", ""): r.sample
                  for r in man.itertuples()}

    dev = ad.read_h5ad(PROCESSED)
    print(f"devbrain: {dev.shape}", flush=True)
    ens = dev.var["gene_ids"].astype(str).values
    ens_pos = {e: i for i, e in enumerate(ens)}
    cell_pos = {c: i for i, c in enumerate(dev.obs_names)}

    mats = {L: lil_matrix((dev.n_obs, dev.n_vars), dtype=np.float32) for L in LAYERS}
    found_total = 0

    for path in LOOMS:
        lib = os.path.basename(path).replace(".loom", "")
        sample = lib2sample[lib]
        with h5py.File(path, "r") as f:
            cell_ids = f["col_attrs/CellID"].asstr()[:]
            acc = f["row_attrs/Accession"].asstr()[:]

            # map loom cells onto devbrain rows
            keys = [f"{sample}:{c.split(':')[1][:-1]}-1" for c in cell_ids]
            col_take, row_put = [], []
            for j, k in enumerate(keys):
                i = cell_pos.get(k)
                if i is not None:
                    col_take.append(j); row_put.append(i)
            col_take = np.asarray(col_take); row_put = np.asarray(row_put)

            # map loom genes onto devbrain columns
            g_take, g_put = [], []
            for j, a in enumerate(acc):
                i = ens_pos.get(a)
                if i is not None:
                    g_take.append(j); g_put.append(i)
            g_take = np.asarray(g_take); g_put = np.asarray(g_put)

            print(f"  {lib:16s} cells {len(col_take):5d}/{len(cell_ids):5d}  "
                  f"genes {len(g_take):6d}/{len(acc)}", flush=True)
            found_total += len(col_take)
            if len(col_take) == 0:
                continue

            order = np.argsort(col_take)
            col_sorted = col_take[order]; row_sorted = row_put[order]

            for L in LAYERS:
                dset = f["layers"][L]
                blocks = []
                for start in range(0, len(g_take), GENE_BLOCK):
                    gi = g_take[start:start + GENE_BLOCK]
                    lo, hi = gi.min(), gi.max() + 1
                    chunk = dset[lo:hi, :][:, col_sorted]        # genes x cells
                    keep = np.isin(np.arange(lo, hi), gi)
                    blocks.append(csr_matrix(chunk[keep].astype(np.float32)))
                sub = vstack(blocks).T.tocsr()                   # cells x genes
                mats[L][np.ix_(row_sorted, g_put)] = sub

    print(f"\nmatched {found_total} / {dev.n_obs} devbrain cells", flush=True)
    for L in LAYERS:
        dev.layers[L] = mats[L].tocsr()
        print(f"  {L:10s} nnz={dev.layers[L].nnz:,} total={int(dev.layers[L].sum()):,}")

    cov = np.asarray((dev.layers["spliced"] + dev.layers["unspliced"]).sum(1)).ravel()
    dev.obs["velocyto_covered"] = cov > 0
    print(f"cells with any spliced/unspliced signal: {int((cov > 0).sum())}")

    # bring across the joint Harmony embedding (devbrain rows of the joint object)
    with h5py.File(INTEGRATED, "r") as f:
        jidx = f["obs/_index"].asstr()[:]
        is_dev = np.array([s.endswith("-devbrain") for s in jidx])
        jnames = np.array([s[: -len("-devbrain")] for s in jidx[is_dev]])
        pos = {c: i for i, c in enumerate(jnames)}
        take = np.array([pos[c] for c in dev.obs_names])
        for key, newkey in (("X_pca_harmony", "X_pca_harmony_joint"),
                            ("X_umap_post", "X_umap_joint")):
            arr = f["obsm"][key][:][is_dev][take]
            dev.obsm[newkey] = arr
            print(f"  carried {key} -> obsm['{newkey}'] {arr.shape}")
        lj = f["obs/leiden_joint"]
        cats = lj["categories"].asstr()[:]; codes = lj["codes"][:]
        vals = np.where(codes >= 0, cats[np.clip(codes, 0, None)], "")
        dev.obs["leiden_joint"] = pd.Categorical(vals[is_dev][take])

    stage_num = {"e7.0": 7.0, "e8.0": 8.0, "e8.5": 8.5, "e9.0": 9.0, "e10.0": 10.0}
    dev.obs["stage_num"] = dev.obs["age"].astype(str).map(stage_num).astype(float)

    dev.write_h5ad(OUT, compression="gzip")
    print(f"\nwrote {OUT}: {dev.shape}")
    print(dev)


if __name__ == "__main__":
    main()
