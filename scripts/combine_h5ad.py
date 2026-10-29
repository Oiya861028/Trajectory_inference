#!/usr/bin/env python
"""Concatenate the per-sample raw matrices into one AnnData and call cells.

The per-sample files written by bam_to_h5ad.py are *raw* -- every barcode seen
in the BAM, empty droplets included.  CellRanger's own cell calls were not
archived with the BAMs, so we redo the call here with the CellRanger v2
ordmag heuristic: threshold = (99th percentile of the top `expected_cells`
barcode counts) / 10.

Writes:
  data/devbrain_E7-E10.h5ad      cells only, concatenated
  data/devbrain_E7-E10_raw.h5ad  all barcodes >= --raw-min-umi (with --write-raw)
"""

import argparse
import glob
import os

import anndata as ad
import numpy as np
import pandas as pd

AGE_NUM = lambda a: float(a.lstrip("e"))


def call_cells(counts, expected_cells=3000, min_umi=500):
    """CellRanger v2 'ordmag' cell calling on a vector of per-barcode UMI totals."""
    if counts.size == 0:
        return np.zeros(0, dtype=bool)
    top = np.sort(counts)[::-1][:expected_cells]
    thresh = max(np.percentile(top, 99) / 10.0, min_umi)
    return counts >= thresh


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--indir", required=True)
    p.add_argument("--out", required=True)
    p.add_argument("--raw-out", default=None)
    p.add_argument("--expected-cells", type=int, default=3000)
    p.add_argument("--min-umi", type=int, default=500)
    p.add_argument("--raw-min-umi", type=int, default=100)
    p.add_argument("--write-raw", action="store_true")
    args = p.parse_args()

    files = sorted(glob.glob(os.path.join(args.indir, "*_raw.h5ad")))
    if not files:
        raise SystemExit(f"no *_raw.h5ad under {args.indir}")
    print(f"found {len(files)} per-sample files")

    cells, raws = [], []
    summary = []
    for f in files:
        a = ad.read_h5ad(f)
        counts = a.obs["total_counts"].to_numpy()
        is_cell = call_cells(counts, args.expected_cells, args.min_umi)
        a.obs["is_cell"] = is_cell
        sample = a.obs["sample"].iloc[0]
        summary.append({
            "sample": sample,
            "age": a.obs["age"].iloc[0],
            "tissue": a.obs["tissue"].iloc[0],
            "barcodes_total": a.n_obs,
            "cells_called": int(is_cell.sum()),
            "median_umi_per_cell": float(np.median(counts[is_cell])) if is_cell.any() else 0.0,
            "median_genes_per_cell": float(np.median(a.obs["n_genes"].to_numpy()[is_cell])) if is_cell.any() else 0.0,
            "umis_total": int(counts.sum()),
        })
        print(f"  {sample:10s} {a.obs['age'].iloc[0]:6s} "
              f"{a.n_obs:8d} barcodes -> {int(is_cell.sum()):6d} cells "
              f"(median {summary[-1]['median_umi_per_cell']:.0f} UMI)", flush=True)

        if args.write_raw:
            raws.append(a[counts >= args.raw_min_umi].copy())
        cells.append(a[is_cell].copy())
        del a

    def finish(parts, path):
        comb = ad.concat(parts, join="outer", merge="first", index_unique=None)
        comb.var = comb.var.copy()
        comb.obs["age_num"] = comb.obs["age"].map(AGE_NUM).astype(float)
        for c in ("sample", "run", "age", "tissue"):
            comb.obs[c] = comb.obs[c].astype("category")
        comb.obs["age"] = comb.obs["age"].cat.reorder_categories(
            sorted(comb.obs["age"].cat.categories, key=AGE_NUM), ordered=True)
        comb.uns["source"] = {
            "bioproject": "PRJNA637987",
            "study": "La Manno et al. 2021, molecular architecture of the developing mouse brain",
            "reference": "refdata-cellranger-mm10-3.0.0",
            "counting": "unique UMIs from CellRanger BAM reads with xf bit 8 set",
            "cell_calling": f"CellRanger v2 ordmag, expected_cells={args.expected_cells}, floor={args.min_umi} UMI",
        }
        comb.write_h5ad(path, compression="gzip")
        print(f"wrote {path}: {comb.n_obs} x {comb.n_vars}")
        return comb

    comb = finish(cells, args.out)
    if args.write_raw and args.raw_out:
        finish(raws, args.raw_out)

    df = pd.DataFrame(summary)
    csv = os.path.join(os.path.dirname(os.path.abspath(args.out)), "metadata", "per_sample_summary.csv")
    os.makedirs(os.path.dirname(csv), exist_ok=True)
    df.to_csv(csv, index=False)
    print(f"\n{df.to_string(index=False)}")
    print(f"\nsummary -> {csv}")
    print(f"\ncells per age:\n{comb.obs.groupby('age', observed=True).size().to_string()}")


if __name__ == "__main__":
    main()
