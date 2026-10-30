#!/bin/bash
#SBATCH --job-name=devbrain_velocyto
#SBATCH --account=pi-imoskowitz
#SBATCH --partition=caslake
#SBATCH --output=/project/imoskowitz/yubin/Trajectory_inference/logs/velocyto_%A_%a.out
#SBATCH --error=/project/imoskowitz/yubin/Trajectory_inference/logs/velocyto_%A_%a.err
#SBATCH --array=1
#SBATCH --cpus-per-task=8
#SBATCH --mem=32G
#SBATCH --time=06:00:00

# Spliced/unspliced counts for one PRJNA637987 sample.
#
# Why we regenerate instead of downloading: the published per-cell loom
# (dev_all.loom, 19 GB) was hosted in the linnarsson-lab-loom GCS bucket, which
# now 404s entirely.  The surviving mirrors are no substitute -- the CELLxGENE
# h5ad has only 'expected'/'pooled' layers, and CaltechDATA's dev_gfilt.loom is
# filtered to 3,686 genes that exclude Gli1, Hhip and Shh.
#
# Why velocyto and not the tag-streaming trick in bam_to_h5ad.py: these BAMs do
# carry RE:A:{E,N,I} region tags, but CellRanger 3.0 assigns GX only to exonic
# reads -- every intronic read has no gene tag, so unspliced counts need
# annotation-based interval assignment, which is what velocyto does.
#
# Run the pilot with:   sbatch --array=1 scripts/velocyto_run.sbatch
# then fan out with:    sbatch --array=2-19 scripts/velocyto_run.sbatch

set -euo pipefail

PROJ=/project/imoskowitz/yubin/Trajectory_inference
MANIFEST=$PROJ/results/tables/metadata/samples_E7-E10.csv
BCDIR=$PROJ/data/interim/velocyto/barcodes
OUTDIR=$PROJ/data/interim/velocyto/loom
REFS=$PROJ/data/raw/external/refs
GTF=$REFS/Mus_musculus.GRCm38.93.gtf
RMSK=$REFS/mm10_rmsk.ensembl.gtf
VELOCYTO=/project/imoskowitz/yubin/envs/velocyto/bin/velocyto

export PATH=/software/samtools-1.22.1-el8-x86_64/bin:$PATH
SCRATCH=${BAM_DIR:-${SLURM_TMPDIR:-/tmp}}/velocyto_${SLURM_ARRAY_TASK_ID:-0}
THREADS=${SLURM_CPUS_PER_TASK:-8}

mkdir -p "$OUTDIR" "$SCRATCH"

# manifest columns: run,sample,age,age_num,tissue,strain,biosample,experiment,
#                   library_name,bam_name,bam_size,bam_md5,bam_url
row=$(awk -v n="$((SLURM_ARRAY_TASK_ID + 1))" 'NR==n' "$MANIFEST" | tr -d '\r')
IFS=, read -r RUN SAMPLE AGE AGE_NUM TISSUE STRAIN BIOSAMPLE EXPERIMENT LIBNAME BAM_NAME BAM_SIZE BAM_MD5 BAM_URL <<<"$row"

LIB=${BAM_NAME%.bam}
BAM=$SCRATCH/${LIB}.bam
BARCODES=$BCDIR/${LIB}.tsv
LOOM=$OUTDIR/${LIB}.loom

echo "sample=$SAMPLE age=$AGE library=$LIB"
echo "scratch=$SCRATCH threads=$THREADS"

if [[ -s "$LOOM" ]]; then
    echo "$LOOM already exists, nothing to do"
    exit 0
fi
[[ -s "$BARCODES" ]] || { echo "missing barcode whitelist $BARCODES" >&2; exit 1; }

# velocyto writes a cell-barcode-sorted copy next to the BAM, so budget 2x.
need=$(( (BAM_SIZE / 1000000000 + 1) * 2 + 5 ))
avail=$(df -BG --output=avail "$SCRATCH" | tail -1 | tr -dc '0-9')
echo "scratch needs ~${need}G, has ${avail}G"
[[ "$avail" -ge "$need" ]] || { echo "not enough scratch on $SCRATCH" >&2; exit 1; }

# The GTF ships gzipped; velocyto wants it plain. Decompress once, shared.
if [[ ! -s "$GTF" ]]; then
    echo "decompressing GTF"
    zcat "$GTF.gz" > "$GTF.tmp.$$" && mv -n "$GTF.tmp.$$" "$GTF"
    rm -f "$GTF.tmp.$$"
fi

echo "downloading $BAM_NAME ($(( BAM_SIZE / 1000000000 ))G)"
curl -sS --retry 3 --retry-delay 10 -o "$BAM" "$BAM_URL"
echo "md5 check"
echo "$BAM_MD5  $BAM" | md5sum -c - || { echo "md5 mismatch" >&2; exit 1; }

echo "velocyto run starting: $(date)"
"$VELOCYTO" run \
    --bcfile "$BARCODES" \
    --outputfolder "$SCRATCH/out" \
    --sampleid "$LIB" \
    --mask "$RMSK" \
    --samtools-threads "$THREADS" \
    --samtools-memory 2048 \
    -vv \
    "$BAM" "$GTF"

cp "$SCRATCH/out/${LIB}.loom" "$LOOM"
rm -rf "$SCRATCH"
echo "wrote $LOOM"
echo "done: $(date)"
