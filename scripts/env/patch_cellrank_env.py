#!/usr/bin/env python
"""Re-apply the four source patches envs/cellrank_traj needs.

cellrank 2.3.3 requires python >= 3.12, but every conda-forge petsc4py/slepc4py
build is python 3.11, and without SLEPc pyGPCCA falls back to a dense Schur
decomposition - 68,166^2 x 8 bytes is ~37 TB. So the environment is pinned at
python 3.11 + cellrank 2.0.7, which predates numpy 2 and petsc4py 3.19. Four
call sites broke as a result; each is patched in place with a .orig backup.

Run with the environment's own interpreter:
    envs/cellrank_traj/bin/python scripts/patch_cellrank_env.py [--check]

--check reports status without writing. The script is idempotent.
"""
import argparse
import pathlib
import shutil
import sys
import sysconfig

SP = pathlib.Path(sysconfig.get_paths()["purelib"])

# (file, what broke, old text, new text)
PATCHES = [
    (
        "scvelo/tools/optimization.py",
        "numpy >= 2 refuses to assign a size-1 array into a scalar slot, so "
        "scv.tl.velocity(mode='stochastic') raised in leastsq_generalized",
        "            gamma[i] = np.linalg.pinv(A.T.dot(A)).dot(A.T.dot(y[:, i]))\n",
        "            # numpy>=2 rejects assigning a size-1 array into a scalar slot;\n"
        "            # ravel first (patched locally for scvelo 0.3.4 + numpy 2.x)\n"
        "            gamma[i] = np.ravel(np.linalg.pinv(A.T.dot(A)).dot(A.T.dot(y[:, i])))[0]\n",
    ),
    (
        "cellrank/kernels/_velocity_kernel.py",
        "numpy >= 2 renamed assert_array_equal's x/y parameters to "
        "actual/desired, so building a VelocityKernel raised TypeError",
        "        np.testing.assert_array_equal(\n"
        "            x=self._xdata.shape,\n"
        "            y=self._vdata.shape,\n",
        "        # numpy>=2 renamed assert_array_equal's parameters x/y -> actual/desired;\n"
        "        # pass positionally (patched locally for cellrank 2.0.7 + numpy 2.x)\n"
        "        np.testing.assert_array_equal(\n"
        "            self._xdata.shape,\n"
        "            self._vdata.shape,\n",
    ),
    (
        "cellrank/_utils/_linear_solver.py",
        "petsc4py >= 3.19 renamed Mat.getVecs to Mat.createVecs, so "
        "compute_fate_probabilities raised AttributeError",
        "    x, b = A.getVecs()",
        "    x, b = A.createVecs()  # petsc4py >= 3.19 renamed Mat.getVecs -> Mat.createVecs",
    ),
    (
        "pygpcca/utils/_utils.py",
        "the same getVecs rename made _eigs_slepc raise AttributeError rather "
        "than be merely unavailable, and the handler only caught ImportError, "
        "so the stationary distribution failed and predict_initial_states raised "
        "'No coarse-grained stationary distribution found'",
        '    try:\n'
        '        vals, vecs = _eigs_slepc(P.T, k=2, which="LR")\n'
        '    except ImportError:\n'
        '        vals, vecs = eigs(P.T, k=2, which="LR", ncv=None)',
        '    try:\n'
        '        vals, vecs = _eigs_slepc(P.T, k=2, which="LR")\n'
        '    except (ImportError, AttributeError):\n'
        '        # petsc4py >= 3.19 renamed Mat.getVecs -> Mat.createVecs, so _eigs_slepc\n'
        '        # raises AttributeError instead of being merely unavailable. ARPACK is\n'
        '        # adequate here: only k=2 eigenpairs are needed.\n'
        '        vals, vecs = eigs(P.T, k=2, which="LR", ncv=None)',
    ),
]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true", help="report status, write nothing")
    args = ap.parse_args()

    print(f"site-packages: {SP}\n")
    missing = 0
    for rel, why, old, new in PATCHES:
        path = SP / rel
        if not path.exists():
            print(f"[ABSENT ] {rel}\n           file not found"); missing += 1; continue
        text = path.read_text()
        if new in text:
            print(f"[ok     ] {rel}"); continue
        if old not in text:
            # neither form present: the upstream source changed, so the patch
            # must be re-derived rather than silently skipped
            print(f"[STALE  ] {rel}\n           neither patched nor original text found; "
                  f"re-derive this patch\n           ({why})")
            missing += 1
            continue
        if args.check:
            print(f"[NEEDED ] {rel}\n           {why}"); missing += 1; continue
        if not (bak := path.with_suffix(path.suffix + ".orig")).exists():
            shutil.copy2(path, bak)
        path.write_text(text.replace(old, new, 1))
        print(f"[patched] {rel}\n           {why}")

    print(f"\n{len(PATCHES) - missing}/{len(PATCHES)} patches in place")
    return 1 if missing else 0


if __name__ == "__main__":
    sys.exit(main())
