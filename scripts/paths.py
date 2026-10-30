"""Single source of truth for every path in this project.

Import this instead of writing a path literal. Adding a file means adding a
constant here, so a future move needs one edit rather than a grep across four
notebooks, nine sbatch wrappers and ten scripts — which is how the
post-reorganization run of run_joint_plots.sbatch came to point at a script
that no longer existed.

Usage from a script:

    import sys; sys.path.insert(0, "/project/imoskowitz/yubin/Trajectory_inference")
    from scripts.paths import DEVBRAIN_PROCESSED, fig, table

Usage from a notebook in notebooks/ (cwd is that directory):

    import sys, os
    sys.path.insert(0, os.path.abspath(".."))
    from scripts.paths import *

Depends on nothing outside the standard library, so it cannot fail to import on
a compute node.
"""

from pathlib import Path

# ---------------------------------------------------------------- roots
BASE = Path("/project/imoskowitz/yubin/Trajectory_inference")

DOCS      = BASE / "docs"
NOTEBOOKS = BASE / "notebooks"
SCRIPTS   = BASE / "scripts"
LOGS      = BASE / "logs"

DATA          = BASE / "data"
DATA_RAW      = DATA / "raw"
DATA_INTERIM  = DATA / "interim"
DATA_PROCESSED = DATA / "processed"

RESULTS = BASE / "results"
FIGURES = RESULTS / "figures"
TABLES  = RESULTS / "tables"
MODELS  = RESULTS / "models"

# ---------------------------------------------------------------- inputs
# per-sample matrices from bam_to_h5ad.py, and the reference annotation
RAW_H5AD   = DATA_RAW / "h5ad"
EXTERNAL   = DATA_RAW / "external"
REFS       = EXTERNAL / "refs"
GTF        = REFS / "Mus_musculus.GRCm38.93.gtf"
REPEAT_MASK = REFS / "mm10_rmsk.ensembl.gtf"

# external datasets, read-only, outside this project
PIJUAN = Path("/project/imoskowitz/kdreyer/public_datasets/002_PijuanSala2019/"
              "gastrulation_ps2019.h5ad")
BROOKS = Path("/project/imoskowitz/kdreyer/public_datasets/"
              "001_Brooks2025_GSE273804/WT_timeseries/GSE273804_FVB_All.h5ad")

# ---------------------------------------------------------------- interim
# written once by an early stage, read by later ones
DEVBRAIN_RAW       = DATA_INTERIM / "devbrain_E7-E10.h5ad"
DEVBRAIN_PROCESSED = DATA_INTERIM / "devbrain_E7-E10_processed.h5ad"
DEVBRAIN_VELOCITY  = DATA_INTERIM / "devbrain_velocity.h5ad"
VELOCYTO           = DATA_INTERIM / "velocyto"
VELOCYTO_LOOM      = VELOCYTO / "loom"

# ---------------------------------------------------------------- processed
# each of these backs a figure or a table
JOINT              = DATA_PROCESSED / "devbrain_brooks_integrated.h5ad"
DEVBRAIN_CELLRANK  = DATA_PROCESSED / "devbrain_cellrank.h5ad"
DEVBRAIN_CELLTYPIST = DATA_PROCESSED / "devbrain_celltypist.h5ad"
NEURAL_LINEAGE     = DATA_PROCESSED / "devbrain_neural_lineage.h5ad"

# ---------------------------------------------------------------- results
TABLES_METADATA = TABLES / "metadata"
TABLES_CELLRANK = TABLES / "cellrank"
# the joint CellRank run writes the same basenames (fate_*.csv,
# composition_*.csv) as the devbrain run, so it gets its own directory rather
# than relying on a "joint_" prefix in the kernel names to keep them apart
TABLES_CELLRANK_JOINT = TABLES / "cellrank_joint"
MODELS_CELLTYPIST = MODELS / "celltypist"

# Figure directories are numbered by analysis stage. Register a new stage here
# and `fig()` will create it on demand; nothing else needs to change.
FIGURE_STAGES = {
    "qc":                "01_qc",
    "pca_hvg":           "02_pca_hvg",
    "umap_unintegrated": "03_umap_unintegrated",
    "harmony_chip":      "04_harmony_chip",
    "hedgehog":          "05_hedgehog",
    "integration":       "06_integration_brooks",
    "cellrank":          "07_cellrank",
    "cellrank_joint":    "08_cellrank_joint",
    "joint_features":    "09_joint_pca_features",
}


def fig(stage, create=True):
    """Directory for one analysis stage's figures, as a trailing-slash string.

    `stage` is a key of FIGURE_STAGES, or a literal directory name for a stage
    not yet registered.
    """
    name = FIGURE_STAGES.get(stage, stage)
    d = FIGURES / name
    if create:
        d.mkdir(parents=True, exist_ok=True)
    return str(d) + "/"


def table(name="", kind="metadata", create=True):
    """Path under results/tables/<kind>/, optionally to a named file."""
    d = TABLES / kind
    if create:
        d.mkdir(parents=True, exist_ok=True)
    return str(d / name) if name else str(d) + "/"


def model(name="", kind="celltypist", create=True):
    d = MODELS / kind
    if create:
        d.mkdir(parents=True, exist_ok=True)
    return str(d / name) if name else str(d) + "/"


def check(require_outputs=False):
    """Verify the inputs exist. Returns a list of problems, empty if clean."""
    problems = []
    always = {
        "RAW_H5AD": RAW_H5AD, "GTF": GTF, "REPEAT_MASK": REPEAT_MASK,
        "DEVBRAIN_RAW": DEVBRAIN_RAW, "DEVBRAIN_PROCESSED": DEVBRAIN_PROCESSED,
        "DEVBRAIN_VELOCITY": DEVBRAIN_VELOCITY, "VELOCYTO_LOOM": VELOCYTO_LOOM,
        "JOINT": JOINT, "BROOKS": BROOKS, "PIJUAN": PIJUAN,
    }
    outputs = {
        "DEVBRAIN_CELLRANK": DEVBRAIN_CELLRANK,
        "DEVBRAIN_CELLTYPIST": DEVBRAIN_CELLTYPIST,
        "NEURAL_LINEAGE": NEURAL_LINEAGE,
    }
    for name, p in {**always, **(outputs if require_outputs else {})}.items():
        if not p.exists():
            problems.append(f"{name}: {p}")
    return problems


if __name__ == "__main__":
    bad = check(require_outputs=True)
    print(f"BASE = {BASE}")
    print(f"{len(FIGURE_STAGES)} figure stages registered")
    if bad:
        print(f"\n{len(bad)} missing:")
        for b in bad:
            print("  ", b)
        raise SystemExit(1)
    print("all declared paths exist")
