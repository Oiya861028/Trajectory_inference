#!/usr/bin/env python
"""Build a raw cell x gene count matrix from a 10x CellRanger BAM.

The BAMs archived under PRJNA637987 are the original CellRanger (v2/v3) output
BAMs, so every read CellRanger counted carries ``xf`` bit 8 ("representative
read for a molecule") together with a corrected barcode (``CB``), a corrected
UMI (``UB``) and exactly one gene (``GX``/``GN``).  Counting those reads
reproduces the CellRanger UMI count matrix without re-aligning anything.

Writes a raw AnnData (all barcodes above --min-umi) to --out.
"""

import argparse
import os
import subprocess
import sys
import time
from array import array

import anndata as ad
import numpy as np
import pandas as pd
from scipy.sparse import coo_matrix

SAMTOOLS = os.environ.get("SAMTOOLS", "samtools")


def stream_counts(bam, threads, samtools=SAMTOOLS):
    """Yield (barcode_idx, gene_idx) for every CellRanger-counted read."""
    cmd = [
        samtools, "view",
        "-@", str(threads),
        "-e", "[xf] & 8",
        "--keep-tag", "CB,GX,GN",
        bam,
    ]
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, bufsize=1 << 20)

    cb_index, gene_index, gene_names = {}, {}, []
    # array('i') rather than a list: 4 bytes/entry instead of ~36, which keeps
    # peak memory in the hundreds of MB for ~40M counted reads per sample
    rows, cols = array("i"), array("i")
    n_reads = 0
    t0 = time.time()

    for line in proc.stdout:
        fields = line.rstrip("\n").split("\t")
        cb = gx = gn = None
        for f in fields[11:]:
            tag = f[:5]
            if tag == "CB:Z:":
                cb = f[5:]
            elif tag == "GX:Z:":
                gx = f[5:]
            elif tag == "GN:Z:":
                gn = f[5:]
        if cb is None or gx is None:
            continue

        r = cb_index.get(cb)
        if r is None:
            r = cb_index[cb] = len(cb_index)
        c = gene_index.get(gx)
        if c is None:
            c = gene_index[gx] = len(gene_index)
            gene_names.append(gn or gx)
        rows.append(r)
        cols.append(c)

        n_reads += 1
        if n_reads % 10_000_000 == 0:
            print(f"  {n_reads/1e6:.0f}M counted reads, "
                  f"{len(cb_index)/1e3:.0f}k barcodes, {time.time()-t0:.0f}s",
                  flush=True)

    proc.stdout.close()
    err = proc.stderr.read()
    if proc.wait() != 0:
        raise RuntimeError(f"samtools failed ({proc.returncode}):\n{err}")

    print(f"  done: {n_reads} counted reads in {time.time()-t0:.0f}s", flush=True)
    return rows, cols, cb_index, gene_index, gene_names


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--bam", required=True)
    p.add_argument("--out", required=True)
    p.add_argument("--sample", required=True)
    p.add_argument("--run", required=True)
    p.add_argument("--age", default="")
    p.add_argument("--tissue", default="")
    p.add_argument("--threads", type=int, default=4)
    p.add_argument("--min-umi", type=int, default=1,
                   help="drop barcodes with fewer total UMIs (1 keeps the full raw matrix)")
    args = p.parse_args()

    rows, cols, cb_index, gene_index, gene_names = stream_counts(args.bam, args.threads)
    if not rows:
        sys.exit(f"no counted reads found in {args.bam}")

    n_cells, n_genes = len(cb_index), len(gene_index)
    rows = np.frombuffer(rows, dtype=np.int32)
    cols = np.frombuffer(cols, dtype=np.int32)
    # duplicate (barcode, gene) entries are summed by tocsr(), giving UMIs per cell/gene
    X = coo_matrix((np.ones(len(rows), dtype=np.int32), (rows, cols)),
                   shape=(n_cells, n_genes)).tocsr()
    del rows, cols

    barcodes = np.empty(n_cells, dtype=object)
    for bc, i in cb_index.items():
        barcodes[i] = bc
    gene_ids = np.empty(n_genes, dtype=object)
    for g, i in gene_index.items():
        gene_ids[i] = g

    obs = pd.DataFrame(index=pd.Index([f"{args.sample}:{b}" for b in barcodes], name=None))
    obs["barcode"] = list(barcodes)
    obs["sample"] = args.sample
    obs["run"] = args.run
    obs["age"] = args.age
    obs["tissue"] = args.tissue

    var = pd.DataFrame(index=pd.Index(list(gene_ids), name=None))
    var["gene_ids"] = list(gene_ids)
    var["gene_symbol"] = gene_names

    adata = ad.AnnData(X=X, obs=obs, var=var)
    adata.obs["total_counts"] = np.asarray(adata.X.sum(axis=1)).ravel()
    adata.obs["n_genes"] = np.asarray((adata.X > 0).sum(axis=1)).ravel()

    if args.min_umi > 1:
        adata = adata[adata.obs["total_counts"] >= args.min_umi].copy()

    adata.uns["source"] = {
        "bioproject": "PRJNA637987",
        "study": "La Manno et al., developing mouse brain (Karolinska)",
        "run": args.run,
        "sample": args.sample,
        "reference": "refdata-cellranger-mm10-3.0.0",
        "counting": "unique UMIs from CellRanger BAM reads with xf bit 8 set",
    }

    os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
    adata.write_h5ad(args.out, compression="gzip")
    print(f"wrote {args.out}: {adata.n_obs} barcodes x {adata.n_vars} genes, "
          f"{int(adata.obs['total_counts'].sum())} UMIs", flush=True)


if __name__ == "__main__":
    main()
