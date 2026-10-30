#!/bin/bash
#SBATCH --job-name=devbrain_sra
#SBATCH --account=pi-imoskowitz
#SBATCH --partition=caslake
#SBATCH --output=/project/imoskowitz/yubin/Trajectory_inference/logs/fetch_count_%A_%a.out
#SBATCH --error=/project/imoskowitz/yubin/Trajectory_inference/logs/fetch_count_%A_%a.err
#SBATCH --array=1-19%10
#SBATCH --cpus-per-task=8
#SBATCH --mem=16G
#SBATCH --time=02:00:00

# One array task per PRJNA637987 sample (E7.0-E10.0): download the original
# CellRanger BAM from the SRA source bucket, count UMIs straight off the
# CB/UB/GX tags, write a raw .h5ad, then delete the BAM again.
#
# BAMs are staged on node-local scratch and discarded; set BAM_DIR=/some/path
# plus KEEP_BAM=1 to retain them.

set -euo pipefail

PROJ=/project/imoskowitz/yubin/Trajectory_inference
# Stage BAMs on the node-local SSD: per-job, auto-cleaned, and immune to the
# shared /scratch quota. Override with BAM_DIR to keep them somewhere durable.
SCRATCH=${BAM_DIR:-${SLURM_TMPDIR:-/tmp}}
MANIFEST=$PROJ/results/tables/metadata/samples_E7-E10.csv
OUTDIR=$PROJ/data/raw/h5ad
PYTHON=/home/yubin/.conda/envs/scRNAseq_python/bin/python
export SAMTOOLS=/software/samtools-1.22.1-el8-x86_64/bin/samtools

mkdir -p "$SCRATCH" "$OUTDIR"

# manifest columns: run,sample,age,age_num,tissue,strain,biosample,experiment,
#                   library_name,bam_name,bam_size,bam_md5,bam_url
# tr -d '\r' guards against the manifest being rewritten with CRLF endings.
row=$(awk -v n="$((SLURM_ARRAY_TASK_ID + 1))" 'NR==n' "$MANIFEST" | tr -d '\r')
IFS=, read -r RUN SAMPLE AGE AGE_NUM TISSUE STRAIN BIOSAMPLE EXPERIMENT LIBNAME BAM_NAME BAM_SIZE BAM_MD5 BAM_URL <<<"$row"

OUT=$OUTDIR/${SAMPLE}_${AGE}_raw.h5ad
BAM=$SCRATCH/${RUN}_${SAMPLE}.bam

echo "=== task $SLURM_ARRAY_TASK_ID: $RUN / $SAMPLE / $AGE / $TISSUE ==="
echo "host=$(hostname) started=$(date -Is)"

if [[ -s "$OUT" ]]; then
    echo "$OUT already exists, nothing to do"
    exit 0
fi

# --- download (resumable) -------------------------------------------------
ok=0
for attempt in 1 2 3; do
    echo "download attempt $attempt -> $BAM"
    rc=0
    curl -fsSL -C - --retry 5 --retry-delay 10 --retry-connrefused \
         --speed-limit 102400 --speed-time 300 \
         -o "$BAM" "$BAM_URL" || rc=$?
    if [[ $rc -eq 0 ]]; then ok=1; break; fi
    echo "attempt $attempt failed (curl exit $rc)"
    sleep 30
done
[[ $ok -eq 1 ]] || { echo "ERROR: download failed for $RUN"; exit 1; }

actual_size=$(stat -c %s "$BAM")
if [[ "$actual_size" != "$BAM_SIZE" ]]; then
    echo "ERROR: size mismatch for $RUN: got $actual_size, expected $BAM_SIZE"
    exit 1
fi
echo "downloaded $actual_size bytes, verifying BGZF integrity"
"$SAMTOOLS" quickcheck -v "$BAM"

# --- count ----------------------------------------------------------------
"$PYTHON" -u "$PROJ/scripts/bam_to_h5ad.py" \
    --bam "$BAM" \
    --out "$OUT" \
    --sample "$SAMPLE" \
    --run "$RUN" \
    --age "$AGE" \
    --tissue "$TISSUE" \
    --threads "$SLURM_CPUS_PER_TASK"

if [[ "${KEEP_BAM:-0}" != "1" ]]; then
    rm -f "$BAM"
    echo "removed $BAM"
fi

echo "finished=$(date -Is)"
