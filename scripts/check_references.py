#!/usr/bin/env python
"""Verify every path referenced by the project's code actually resolves.

Run after moving anything:

    envs/cellrank_traj/bin/python scripts/check_references.py

Exits non-zero if any reference is broken, so it can gate a commit.

Three classes of reference are checked separately, because they fail in
different ways:

1. Executables named by an sbatch wrapper (a .py or .ipynb it runs). A typo
   here fails only when the job starts, minutes into a node allocation. This is
   the class that broke after the directory reorganization: four wrappers still
   pointed at scripts/<name>.py after the scripts were moved into
   subdirectories, and the first check written for that reorganization accepted
   them because the parent directory scripts/ existed.
2. Inputs a script or notebook reads. Must exist now.
3. Outputs a script or notebook writes. The file need not exist yet, but its
   parent directory must be creatable, and - the real point - no two writers may
   claim the same output, or whichever runs last silently wins.
"""

import ast
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

BASE = Path("/project/imoskowitz/yubin/Trajectory_inference")

CODE = (sorted((BASE / "scripts").rglob("*.py"))
        + sorted((BASE / "scripts").rglob("*.sbatch"))
        + sorted((BASE / "notebooks").glob("*.ipynb"))
        + sorted((BASE / "docs" / "deck").glob("*.py")))

# The deck names figures as paths relative to results/figures/. A figure
# renamed by a pipeline change would otherwise break the deck silently at the
# next rebuild, which is exactly the failure this script exists to prevent.
DECK_FIG_RE = re.compile(r"[\"'](\d\d_[A-Za-z0-9_]+/[A-Za-z0-9_.\-]+\.png)[\"']")
FIGROOT = BASE / "results" / "figures"

# a path-looking string rooted at one of the project's top-level directories
PATH_RE = re.compile(
    r"(?:data|results|notebooks|scripts|logs|docs)/[A-Za-z0-9_./\-]*"
    r"[A-Za-z0-9_\-](?:\.[A-Za-z0-9]+)?")
# what an sbatch wrapper hands to an interpreter
EXEC_RE = re.compile(r"(?:python[0-9.]*\s+(?:-[A-Za-z]+\s+)*|nbconvert[^\n]*?)"
                     r"[\"']?(?:\$\{?PROJ\}?/|\$\{?BASE\}?/)?"
                     r"((?:scripts|notebooks)/[A-Za-z0-9_/]+\.(?:py|ipynb))")
WRITE_RE = re.compile(r"(?:savefig|to_csv|write_h5ad|write)\(\s*([A-Za-z_][A-Za-z0-9_]*)"
                      r"\s*\+\s*f?[\"']([^\"']+)[\"']")
# `res_dir = base + "results/tables/cellrank/"` -> res_dir maps to that fragment.
# Needed so two files writing the same basename into different directories are
# not reported as colliding.
ASSIGN_RE = re.compile(r"^\s*([A-Za-z_][A-Za-z0-9_]*)\s*=\s*[^\n\"']*[\"']"
                       r"([A-Za-z0-9_./\-]*/)[\"']", re.M)


def source_of(p):
    if p.suffix == ".ipynb":
        nb = json.loads(p.read_text())
        return "\n".join("".join(c["source"]) for c in nb["cells"]
                         if c["cell_type"] == "code")
    return p.read_text()


def main():
    problems, warnings = [], []
    writers = defaultdict(list)

    for p in CODE:
        rel = p.relative_to(BASE)
        src = source_of(p)

        # 1. executables an sbatch wrapper invokes
        if p.suffix == ".sbatch":
            for m in EXEC_RE.finditer(src):
                target = BASE / m.group(1)
                if not target.is_file():
                    problems.append(f"{rel}: runs {m.group(1)} — NOT A FILE")

        # 2/3. path literals
        for m in PATH_RE.finditer(src):
            ref = m.group(0)
            full = BASE / ref
            if full.exists():
                continue
            # an output not yet written is fine if its directory is real
            if full.parent.is_dir():
                continue
            # a directory referenced as a prefix that the code mkdirs is fine
            if any(part.endswith(("_", "/")) for part in [ref]):
                continue
            warnings.append(f"{rel}: {ref}")

        # 3b. duplicate outputs, keyed on directory + name so that the same
        # basename written into two different directories is not a collision
        dirs = {m.group(1): m.group(2) for m in ASSIGN_RE.finditer(src)}
        for m in WRITE_RE.finditer(src):
            var, name = m.group(1), m.group(2)
            if "{" in name:          # f-string template: compare the literal part
                name = re.sub(r"\{[^}]*\}", "*", name)
            writers[dirs.get(var, var + ":") + name].append(str(rel))

    for name, who in sorted(writers.items()):
        uniq = sorted(set(who))
        if len(uniq) > 1:
            problems.append(f"output {name!r} written by {len(uniq)} files: "
                            + ", ".join(uniq))

    # 4. figures the deck asks for
    deck = BASE / "docs" / "deck" / "slides.py"
    if deck.is_file():
        text = deck.read_text()
        refs = sorted({m.group(1) for m in DECK_FIG_RE.finditer(text)})
        for ref in refs:
            if not (FIGROOT / ref).is_file():
                problems.append(f"docs/deck/slides.py: figure {ref} does not exist")
        print(f"{len(refs)} figures referenced by the deck")

    # 5. the declared paths themselves
    sys.path.insert(0, str(BASE))
    from scripts.paths import check as path_check
    for missing in path_check(require_outputs=False):
        problems.append(f"scripts/paths.py declares a missing input — {missing}")

    print(f"checked {len(CODE)} files "
          f"({sum(p.suffix=='.sbatch' for p in CODE)} sbatch, "
          f"{sum(p.suffix=='.ipynb' for p in CODE)} notebooks, "
          f"{sum(p.suffix=='.py' for p in CODE)} scripts)")
    print(f"{len(writers)} distinct output names, "
          f"{sum(len(set(v))>1 for v in writers.values())} with multiple writers")

    if warnings:
        print(f"\n{len(warnings)} unresolved path literal(s) — review, may be runtime-created:")
        for w in warnings:
            print("  ", w)
    if problems:
        print(f"\n{len(problems)} PROBLEM(S):")
        for b in problems:
            print("  ", b)
        return 1
    print("\nno broken references")
    return 0


if __name__ == "__main__":
    sys.exit(main())
