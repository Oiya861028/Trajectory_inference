#!/usr/bin/env python
"""Write one CellRanger-style barcodes.tsv per library from the combined h5ad.

velocyto needs the called-cell barcode whitelist for each BAM.  The combined
file already holds exactly the cells we kept, so export them per library using
the BAM basename as the library id -- that way velocyto's cell names come out as
``<library>:<barcode>x``, which matches both our own join key and the cell names
in the published dev_all.loom.
"""

import argparse
import os

import h5py
import numpy as np


def decode(g):
    """Read an h5ad string column, whether it is categorical or a plain array."""
    if isinstance(g, h5py.Group):
        cats = g["categories"].asstr()[:]
        codes = g["codes"][:]
        return np.where(codes >= 0, cats[np.clip(codes, 0, None)], "")
    return g.asstr()[:]


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--h5ad", required=True)
    p.add_argument("--manifest", required=True)
    p.add_argument("--outdir", required=True)
    args = p.parse_args()

    # sample -> library id (the BAM basename, e.g. 10X37_2 -> 10X37_2_A_1)
    lib = {}
    with open(args.manifest) as fh:
        for line in fh.read().splitlines()[1:]:
            f = line.split(",")
            lib[f[1]] = f[9].replace(".bam", "")

    with h5py.File(args.h5ad, "r") as h:
        barcode = decode(h["obs/barcode"])
        sample = decode(h["obs/sample"])

    os.makedirs(args.outdir, exist_ok=True)
    for s in sorted(set(sample.tolist())):
        bcs = barcode[sample == s]
        out = os.path.join(args.outdir, f"{lib[s]}.tsv")
        with open(out, "w") as fh:
            fh.write("\n".join(bcs) + "\n")
        print(f"{lib[s]:16s} {len(bcs):6d} barcodes -> {out}")


if __name__ == "__main__":
    main()
