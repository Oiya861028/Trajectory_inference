#!/usr/bin/env python
"""Slide content for the trajectory-inference progress deck."""

from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN
from pptx.util import Inches, Pt

from build_deck import (  # noqa
    new_deck, blank, title, textbox, card, stat, bullets, table, bar, footer,
    banner, INK, DARK, CHERRY, EMBER, PEACH, SAND, NAVY, STEEL, GREY, MIDGREY,
    WHITE, TINT, TINT2, HEAD, BODY, W, H,
)

OUT = "progress_trajectory_inference.pptx"
prs = new_deck()


# ---------------------------------------------------------------- 1. title
s = blank(prs, dark=True)
textbox(s, 0.9, 2.05, 11.5, 1.5,
        "Trajectory inference in the\nE7.0–E10.0 mouse embryonic brain",
        size=40, font=HEAD, bold=True, color=WHITE, line=1.1)
textbox(s, 0.9, 3.75, 10.6, 0.9,
        "Pipeline status, the E7.0 connectivity problem, and one result that "
        "changes the plan", size=16, color=SAND, line=1.25)
for i, (lab, val) in enumerate([("cells, 19 libraries", "68,166"),
                                ("cells after joining Brooks", "107,629"),
                                ("kernel weightings compared", "8")]):
    x = 0.9 + i * 3.9
    textbox(s, x, 5.1, 3.6, 0.55, val, size=26, font=HEAD, bold=True, color=EMBER)
    textbox(s, x, 5.68, 3.6, 0.35, lab, size=11.5, color=MIDGREY)
textbox(s, 0.9, 6.6, 11.5, 0.4, "Yubin  ·  Moskowitz Lab  ·  30 October 2026",
        size=11, color=GREY)
s.notes_slide.notes_text_frame.text = (
    "Progress on ordering E7-E10 brain cells along developmental time to read out "
    "hedgehog pathway dynamics. Three things to cover: the pipeline works, the "
    "Brooks integration fixed the graph, and CellRank surfaced a problem that "
    "needs a decision before we spend more compute. Jobs: 61852174 devbrain 2h42m, 61852175 joint 1h03m, 61841763 CellTypist 4h26m.")


# ------------------------------------------------- 2. executive summary
s = blank(prs)
title(s, "Where this stands", sub="Pipeline is complete end to end; one finding blocks the biology")
stat(s, 0.7, 1.95, 2.85, "68,166", "cells pass QC",
     "19 libraries, E7.0–E10.0\n11 cells, 2,448 genes cut", color=STEEL)
stat(s, 3.75, 1.95, 2.85, "1", "connected component",
     "100% of 107,629 cells\nacross all 9 stages", color=STEEL)
stat(s, 6.80, 1.95, 2.85, "7 / 8", "CellRank kernels ran",
     "Velocity-only failed at\nthe fate-probability solve", color=STEEL)
stat(s, 9.85, 1.95, 2.85, "0", "macrostates at E7.0",
     "Under every kernel using\nmoscot optimal transport", color=CHERRY)
bullets(s, 0.7, 4.30, 11.9, [
    ("Works. ", "QC, gene-symbol repair, velocity regeneration, the Brooks bridge, "
     "CellTypist annotation, and 7 of 8 CellRank runs."),
    ("Blocks. ", "No metastable state is placed at E7.0 by any optimal-transport "
     "kernel, so the root cell cannot be identified — which was the whole point of "
     "adding the bridge."),
    ("Confounded. ", "The single run that does put a root at E7.0 picks cells that "
     "are also 100% from the one undissected sample, so stage and dissection cannot "
     "be told apart."),
], size=14.5, gap=11)
banner(s, text="Decision needed: test a less absorbing transport kernel, or "
                "restrict the analysis to one dissected region")


# ------------------------------------------------------- 3. data + question
s = blank(prs)
title(s, "The data and the question",
      sub="Mouse embryonic brain, 10x v1 chemistry, five timepoints")
bullets(s, 0.7, 1.95, 6.0, [
    ("Goal. ", "Order cells along developmental time, then read hedgehog pathway "
     "dynamics (Shh, Ptch1, Smo, Gli1–3, Hhip) along that ordering."),
    ("Source. ", "PRJNA637987 — 19 libraries re-counted from the original "
     "CellRanger BAMs, because the published loom is no longer downloadable."),
    ("Dissection widens with stage. ", "Whole embryo at E7.0, head at E8.0–E8.5, "
     "then forebrain / midbrain / hindbrain separately at E9.0–E10.0."),
], size=13.5, gap=10)
card(s, 0.7, 4.6, 6.0, 2.1, fill=TINT2)
textbox(s, 0.95, 4.78, 5.5, 0.3, "Why this is hard", size=12, bold=True, color=NAVY)
textbox(s, 0.95, 5.12, 5.5, 1.45,
        "E7.0 is three days and one gastrulation event away from E10.0, and was "
        "dissected differently. Any method that assumes a continuum has to bridge "
        "a real biological and technical gap.", size=12, color=INK, line=1.2)
bar(s, 7.0, 2.05, 5.6, 4.6, ["E7.0", "E8.0", "E8.5", "E9.0", "E10.0"],
    [("cells", [11195, 6813, 3241, 14781, 32136])],
    [STEEL, STEEL, STEEL], val_fmt='#,##0', font_size=11)
textbox(s, 7.0, 6.72, 5.6, 0.26, "Cells per stage — E10.0 is 47% of the object",
        size=10.5, color=GREY, align=PP_ALIGN.CENTER)
s.notes_slide.notes_text_frame.text = (
    "Note the stage imbalance: E10.0 has 32k cells, E8.5 only 3.2k. This matters "
    "later - metastable states follow where the cells are.")


# ----------------------------------------------------------------- 4. QC
s = blank(prs)
title(s, "Quality control", sub="Both datasets, same pipeline, very different chemistry")
table(s, 0.7, 2.0, 7.0, [
    ["", "devbrain", "Brooks 2025"],
    ["Cells", "68,166", "39,463"],
    ["Median UMI / cell", "11,692", "42,461"],
    ["Median genes / cell", "3,188", "5,923"],
    ["Genes per 10k UMI", "2,742", "1,393"],
    ["Median % mitochondrial", "0.56", "0.00"],
    ["Median % ribosomal", "25.5", "25.9"],
], col_w=[3.2, 1.9, 1.9], row_h=0.38, size=12.5)
bullets(s, 8.0, 2.0, 4.6, [
    ("Filtering was light. ", "68,177 → 68,166 cells (11 below 500 genes); "
     "24,191 → 21,743 genes (2,448 in fewer than 3 cells)."),
    ("5,334 var entries had no gene symbol. ", "Caused by merge=\"first\" taking "
     "the column from one sample only. Rebuilt from all 19 files; counts were "
     "never affected."),
    ("Brooks reports 0% mitochondrial ", "at every stage — it arrives "
     "pre-filtered, so its QC is not directly comparable."),
], size=12.5, gap=10)
banner(s, text="Brooks is 3.6× deeper per cell. That asymmetry, not biology, "
               "dominates any raw cross-dataset comparison", color=NAVY)


# ------------------------------------------------ 5. the blocker: E7.0 island
s = blank(prs)
title(s, "The blocker: E7.0 is an island in the kNN graph",
      sub="Mean share of each cell's 30 nearest neighbours, by stage (devbrain alone)")
hot = {(1, 1): CHERRY, (2, 2): PEACH, (3, 3): SAND, (4, 4): SAND, (5, 5): PEACH}
tbl = table(s, 0.7, 2.05, 7.3, [
    ["own stage →", "E7.0", "E8.0", "E8.5", "E9.0", "E10.0"],
    ["E7.0",  "98.6", "1.4",  "0.0",  "0.0",  "0.0"],
    ["E8.0",  "2.7",  "88.9", "5.4",  "2.2",  "0.7"],
    ["E8.5",  "0.0",  "11.6", "56.0", "22.3", "10.0"],
    ["E9.0",  "0.0",  "0.9",  "4.5",  "54.7", "39.9"],
    ["E10.0", "0.0",  "0.1",  "1.0",  "19.9", "79.0"],
], col_w=[2.0, 1.06, 1.06, 1.06, 1.06, 1.06], row_h=0.42, size=12.5)
for r in (1,):
    for c in (1,):
        tbl.cell(r, c).text_frame.paragraphs[0].runs[0].font.color.rgb = WHITE
bullets(s, 8.3, 2.1, 4.35, [
    "98.6% of an E7.0 cell's neighbours are also E7.0.",
    "0.0% reach E9.0 or E10.0 — not rounding, zero edges.",
    "95.4% of E7.0 cells sit in neighbourhoods that are >90% their own age.",
], size=13, gap=12)
banner(s, text="No path exists from E7.0 to later stages, so any trajectory "
               "rooted at E7.0 is unsupported by the graph it runs on")
textbox(s, 0.7, 5.62, 11.9, 0.55,
        "Rows sum to 100%. The E8.5 and E9.0 rows mix freely in both directions — "
        "what a continuous series should look like. E7.0 does not.",
        size=11.5, color=GREY, line=1.2)


# -------------------------------------------- 6. Harmony on chip, rejected
s = blank(prs)
title(s, "First attempt: Harmony on chip — tested, then rejected",
      sub="The only within-dataset batch key not nested inside age")
bar(s, 0.7, 2.05, 5.9, 3.35, ["E7.0 → E7.0", "E7.0 → E10.0"],
    [("before Harmony", [98.56, 0.01]), ("after Harmony", [88.40, 6.22])],
    [STEEL, CHERRY], legend=True, val_fmt='0.00"%"', font_size=11)
textbox(s, 0.7, 5.45, 5.9, 0.26, "Neighbour share from E7.0 cells",
        size=10.5, color=GREY, align=PP_ALIGN.CENTER)
bullets(s, 7.0, 2.1, 5.6, [
    ("It looked like it worked. ", "E7.0→E10.0 neighbour share rose from 0.01% "
     "to 6.22%, and the UMAP stopped showing a detached island."),
    ("But no chip contains both ", "an E7.0 library and a late library. Harmony "
     "removes variation shared between batches; with no overlap there is nothing "
     "to remove."),
    ("So the mixing is manufactured, ", "not corrected — Harmony pulled the "
     "clouds together because the key told it they were the same batch."),
], size=13, gap=11)
banner(s, text="Rejected. A correction that cannot be distinguished from "
                "fabrication is worse than no correction")
s.notes_slide.notes_text_frame.text = (
    "This is the key methodological point of the first half. The diagnostic that "
    "caught it was checking the chip-by-stage crosstab before trusting the mixing "
    "improvement.")


# ----------------------------------------------- 7. the bridge: Brooks design
s = blank(prs)
title(s, "The bridge: Brooks 2025 fills the window devbrain skips",
      sub="GSE273804, FVB wild-type timeseries, E7.5–E8.75, 39,463 cells")
rows = [["Stage", "E7.0", "E7.5", "E7.75", "E8.0", "E8.25", "E8.5", "E8.75", "E9.0", "E10.0"],
        ["devbrain", "11,195", "—", "—", "6,813", "—", "3,241", "—", "14,781", "32,136"],
        ["Brooks", "—", "9,533", "7,101", "3,444", "3,397", "10,085", "5,903", "—", "—"]]
cc = {}
for c in (2, 3, 5, 7):
    cc[(2, c)] = SAND
for c in (1, 8, 9):
    cc[(1, c)] = TINT2
tbl = table(s, 0.7, 2.1, 11.9, rows,
            col_w=[1.5] + [1.16] * 9, row_h=0.42, size=11.5, cell_colors=cc)
bullets(s, 0.7, 3.55, 11.9, [
    ("The gap was E7.0 → E8.0. ", "Brooks supplies E7.5 and E7.75 inside it, so "
     "the series becomes a chain of small steps rather than one three-day jump."),
    ("Harmony on dataset, not on sample. ", "Every Brooks replicate is a single "
     "stage, so correcting on replicate would delete the developmental signal "
     "along with the batch effect."),
    ("Accepted cost: ", "the two datasets are cross-platform, so some of what "
     "Harmony removes is real biology. Quantified on the next slide."),
], size=13.5, gap=11)
banner(s, text="The bridge is a chain, not a shortcut — it adds intermediate "
               "stages rather than forcing distant ones together", color=NAVY)


# --------------------------------------------------- 8. integration result
s = blank(prs)
title(s, "Integration worked", sub="One connected component holding 100% of 107,629 cells, all nine stages")
s.shapes.add_picture("fig_integration.png", Inches(0.7), Inches(1.98),
                     height=Inches(4.64))
textbox(s, 0.7, 6.72, 3.6, 0.26, "devbrain (blue) vs Brooks (orange)",
        size=10.5, color=GREY, align=PP_ALIGN.CENTER)
bullets(s, 4.6, 2.0, 8.0, [
    ("Before: ", "the two datasets occupy separate territory — 99.6% of a Brooks "
     "cell's neighbours are Brooks, 99.8% of a devbrain cell's are devbrain."),
    ("After: ", "80.3% / 86.3% self — they interdigitate, and stage forms a clean "
     "E7.0 → E10.0 gradient across the manifold."),
    ("E7.0 reconnected: ", "neighbour share to E7.5 went 0.05% → 8.75% and to "
     "E7.75 0.03% → 3.33%, through added intermediate cells rather than forcing."),
    ("Not over-mixed: ", "cross-dataset mixing peaks exactly at the shared stages "
     "(E8.0 31.5%, E8.5 29.9%) and is lowest where only one dataset has cells "
     "(E10.0 8.4%) — the correct behaviour."),
    ("Still honest about distance: ", "E7.0 → E9.0/E10.0 stayed at 0.01%. The "
     "bridge did not invent a shortcut across three days."),
], size=12.5, gap=9)


# ---------------------------------------- 9. how different are the datasets
s = blank(prs)
title(s, "How different are the two datasets?",
      sub="Pseudobulk correlation, and why the headline number misleads")
bar(s, 0.7, 2.05, 6.3, 3.8,
    ["all genes", "expressed\nonly", "stage-variable\ngenes", "Spearman"],
    [("devbrain E7.0 vs E10.0", [0.963, 0.935, 0.913, 0.870]),
     ("devbrain vs Brooks, both E8.5", [0.936, 0.855, 0.907, 0.674])],
    [STEEL, CHERRY], legend=True, val_fmt='0.000', font_size=10.5)
textbox(s, 0.7, 5.95, 6.3, 0.26, "Pearson r unless noted; higher = more similar",
        size=10.5, color=GREY, align=PP_ALIGN.CENTER)
bullets(s, 7.4, 2.05, 5.2, [
    ("The ceiling is 0.9999. ", "Two random halves of the same stage, differing "
     "only by sampling noise, correlate that highly — so 0.963 is not close to "
     "identical, it is far from the ceiling."),
    ("88.7% of the 15,200 shared genes ", "are near-zero in both, and only 34 "
     "genes (0.2%) move more than one log1p unit from E7.0 to E10.0."),
    ("Platform beats biology here. ", "Same-stage across datasets (Spearman "
     "0.674) is less similar than three days of development within one dataset "
     "(0.870)."),
], size=12.5, gap=10)
banner(s, text="Pearson over all genes is dominated by the shared "
               "mean-expression axis. Use Spearman on expressed genes")


# ------------------------------------------- 10. dissection confound
s = blank(prs)
title(s, "Dissection is confounded with stage",
      sub="Mean Spearman between library pairs, split by whether stage and region match")
table(s, 0.7, 2.1, 7.6, [
    ["Library pair", "Same region", "Different region"],
    ["Same stage", "0.9717", "0.9579"],
    ["Different stage", "0.9576", "0.8869"],
], col_w=[2.9, 2.35, 2.35], row_h=0.52, head_h=0.44, size=14,
   cell_colors={(1, 1): SAND, (1, 2): TINT2, (2, 1): TINT2})
textbox(s, 0.7, 4.0, 7.6, 0.9,
        "Matching region across different stages (0.9576) is indistinguishable "
        "from matching stage across different regions (0.9579).",
        size=13, color=INK, bold=True, line=1.2)
bullets(s, 0.7, 4.92, 7.6, [
    "One dissected region is worth about one stage step.",
    "The dissection scheme changes with stage by design — whole embryo, then "
    "head, then separate regions — so the two cannot be separated in this data.",
], size=12.5, gap=10)
card(s, 8.6, 2.1, 4.0, 4.3, fill=TINT)
textbox(s, 8.85, 2.3, 3.5, 0.35, "Consequence", size=12.5, bold=True, color=CHERRY)
textbox(s, 8.85, 2.72, 3.5, 3.5,
        "Any statement of the form “this state is early” is also a statement "
        "“this state came from the whole-embryo dissection.”\n\n"
        "The only clean fix is to analyse within a single region — which means "
        "E9.0–E10.0 only, where forebrain, midbrain and hindbrain were collected "
        "separately.", size=12, color=INK, line=1.22)


# ------------------------------------------------- 11. velocity data
s = blank(prs)
title(s, "Spliced / unspliced counts had to be regenerated",
      sub="The published loom is gone; velocyto rerun on all 19 libraries")
bullets(s, 0.7, 2.0, 7.3, [
    ("The authors' loom is unreachable. ", "The hosting bucket returns 404, and "
     "the surviving mirrors are inadequate — CELLxGENE carries only pooled or "
     "expected counts, and the filtered loom excludes Gli1, Hhip and Shh."),
    ("So it was rebuilt from the BAMs, ", "velocyto with the Ensembl 93 "
     "annotation and an mm10 repeat mask, as one SLURM array job over the 19 "
     "libraries."),
    ("Validated against the paper: ", "19.1% of reads unspliced here versus the "
     "authors' reported 19.3% — close enough to trust the regeneration."),
    ("One subtlety: ", "these are CellRanger 3.0 BAMs, where intronic reads carry "
     "no GX tag, so region assignment comes from the RE:A tag instead."),
], size=13.5, gap=11)
bar(s, 8.3, 2.05, 4.3, 3.3, ["this run", "published"],
    [("% reads unspliced", [19.1, 19.3])], [CHERRY, STEEL], val_fmt='0.0"%"',
    font_size=11)
textbox(s, 8.3, 5.45, 4.3, 0.26, "Unspliced fraction",
        size=10.5, color=GREY, align=PP_ALIGN.CENTER)
banner(s, text="All five hedgehog genes survive into the velocity object — "
                "they need explicit retention, or the shared-count filter drops them")


# ---------------------------------------------------- 12. CellRank setup
s = blank(prs)
title(s, "CellRank: eight kernel weightings, run identically",
      sub="So that differences between runs come from the kernel, not the settings")
table(s, 0.7, 2.0, 6.5, [
    ["Run", "Composition"],
    ["velocity", "RNA velocity alone"],
    ["realtime_moscot", "Optimal transport alone"],
    ["connectivity", "Graph connectivity alone"],
    ["vk0.8_ck0.2", "velocity + connectivity"],
    ["vk0.8_rtk0.2", "velocity-dominant + OT"],
    ["vk0.5_rtk0.5", "balanced velocity / OT"],
    ["vk0.2_rtk0.8", "OT-dominant"],
    ["vk0.6_rtk0.2_ck0.2", "three-way"],
], col_w=[2.7, 3.8], row_h=0.355, size=12)
bullets(s, 7.6, 2.0, 5.0, [
    ("Shared settings: ", "12 macrostates, Leiden clusters as the cluster key, "
     "Krylov Schur decomposition, 4 terminal states."),
    ("moscot converged ", "on all consecutive stage pairs, costs 0.11–0.16."),
    ("7 of 8 completed. ", "Velocity alone failed at the fate-probability solve — "
     "60,762 of 68,166 rows did not sum to 1, a GMRES convergence failure, fixable "
     "with a direct solver."),
    ("Terminal states agree: ", "all seven runs nominate cluster 0; pairwise "
     "fate-probability correlation runs 0.44 to 0.99."),
], size=12.5, gap=10)
footer(s, "Environment note: cellrank 2.0.7 on python 3.11 with four local "
          "site-packages patches, re-applied by scripts/env/patch_cellrank_env.py")


# =========================== 13. THE FINDING ===========================
s = blank(prs, dark=True)
title(s, "The finding: optimal transport removes E7.0 from the trajectory",
      dark=True, sub="Number of macrostates containing any E7.0 cell, per kernel")
rows = [["Kernel", "Contains OT?", "Macrostates at E7.0"],
        ["connectivity", "no", "4"],
        ["vk0.8_ck0.2", "no", "3"],
        ["realtime_moscot", "yes", "0"],
        ["vk0.8_rtk0.2", "yes", "0"],
        ["vk0.5_rtk0.5", "yes", "0"],
        ["vk0.2_rtk0.8", "yes", "0"],
        ["vk0.6_rtk0.2_ck0.2", "yes", "0"],
        ["both joint runs", "yes", "0"]]
cc = {(1, 2): SAND, (2, 2): SAND}
for r in range(3, 9):
    cc[(r, 2)] = CHERRY
tbl = table(s, 0.7, 2.15, 7.0, rows, col_w=[2.9, 1.8, 2.3], row_h=0.375,
            size=12, head_fill=RGBColor(0x3A, 0x30, 0x33), cell_colors=cc)
for r in range(3, 9):
    tbl.cell(r, 2).text_frame.paragraphs[0].runs[0].font.color.rgb = WHITE
textbox(s, 7.9, 2.2, 4.7, 0.4, "Why this happens", size=14, bold=True,
        font=HEAD, color=SAND)
textbox(s, 7.9, 2.72, 4.7, 2.5,
        "GPCCA macrostates are metastable regions, and metastability requires "
        "stationary probability mass.\n\n"
        "A strongly directed transport kernel gives early stages almost no "
        "stationary probability — so they cannot be macrostates, by construction.",
        size=12.5, color=WHITE, line=1.25)
textbox(s, 7.9, 5.22, 4.7, 0.95,
        "The connectivity kernel finds E7.0 states for the mirror reason: the "
        "isolation we diagnosed as the problem reads as metastability to an "
        "undirected kernel.",
        size=11.5, color=MIDGREY, line=1.2)
banner(s, text="Consequence: the three runs reporting an initial state at E10.0 "
               "are artifacts, not biology")
s.notes_slide.notes_text_frame.text = (
    "This is the slide that matters. Moscot was added specifically to carry early "
    "cells forward by optimal transport. It does the opposite: it removes them "
    "from the metastable structure entirely. In the joint object it is worse - "
    "nothing before E8.0, so all of E7.0, E7.5 and E7.75 are unrepresented, 26% "
    "of the cells, Brooks bridge notwithstanding.")


# --------------------------------------- 14. the one root is confounded
s = blank(prs)
title(s, "And the one run that does find an E7.0 root is confounded",
      sub="vk0.8_ck0.2 nominates macrostate 21 as the initial state")
table(s, 0.7, 2.1, 7.4, [
    ["Macrostate", "% E7.0", "% tissue “All”", "Role"],
    ["21", "100.0", "100.0", "nominated initial state"],
    ["19", "96.7", "96.7", "E7.0 macrostate"],
    ["16", "100.0", "100.0", "E7.0 macrostate"],
], col_w=[2.0, 1.8, 2.0, 2.6], row_h=0.46, head_h=0.42, size=13,
   cell_colors={(1, 1): SAND, (1, 2): SAND})
textbox(s, 0.7, 4.0, 7.4, 0.85,
        "Every E7.0 macrostate is also entirely from the whole-embryo dissection, "
        "because “All” is used at E7.0 and nowhere else.",
        size=13, bold=True, color=INK, line=1.2)
bullets(s, 0.7, 5.0, 7.4, [
    "“The root is at E7.0” and “the root is in the undissected sample” predict "
    "exactly the same cells.",
    "This is the §10b confound landing precisely where it was predicted to.",
], size=12.5, gap=10)
card(s, 8.7, 2.1, 3.9, 4.2, fill=TINT)
textbox(s, 8.95, 2.3, 3.4, 0.35, "What would break the tie", size=12.5,
        bold=True, color=CHERRY)
textbox(s, 8.95, 2.75, 3.4, 3.3,
        "A sample dissected the same way at two stages, or a stage sampled two "
        "ways.\n\nThis design has neither — dissection was widened as the embryo "
        "grew, which is biologically sensible and statistically unfortunate.\n\n"
        "Brooks does not help: it is whole-embryo throughout.",
        size=12, color=INK, line=1.22)


# -------------------------------------------------- 15. CellTypist
s = blank(prs)
title(s, "Annotation: no brain exists yet at E7.0",
      sub="Two CellTypist models trained on Pijuan-Sala, because no gastrulation model exists")
bullets(s, 0.7, 2.0, 6.5, [
    ("The zoo has no gastrulation model. ", "All 60 were checked; the closest is "
     "trained on this very dataset, which would be circular."),
    ("So two were trained: ", "E6.5–E7.5 to separate neural-competent epiblast "
     "from extraembryonic and mesodermal cells, and E7.5–E8.5 to call actual "
     "brain regions."),
    ("E7.0 has no neural plate. ", "Pijuan-Sala holds 13 neurectoderm cells out "
     "of 14,749 there — so the filter excludes non-neural lineages rather than "
     "requiring a positive neural call."),
], size=13, gap=10)
table(s, 0.7, 5.0, 6.5, [
    ["devbrain E7.0, top labels", "Cells"],
    ["Epiblast", "4,208"],
    ["Nascent mesoderm", "3,670"],
    ["ExE endoderm", "1,908"],
], col_w=[4.3, 2.2], row_h=0.36, head_h=0.38, size=12)
bar(s, 7.6, 2.05, 5.0, 3.2, ["Forebrain", "Midbrain", "Hindbrain"],
    [("forebrain panel", [0.076, 0.018, -0.089]),
     ("hindbrain panel", [-0.051, -0.054, 0.064])],
    [CHERRY, STEEL], legend=True, val_fmt='0.000', font_size=10.5)
textbox(s, 7.6, 5.35, 5.0, 0.6,
        "Marker-panel score by region at E10.0 — each panel peaks in its own "
        "region, so the panels work.",
        size=10.5, color=GREY, align=PP_ALIGN.CENTER, line=1.2)
banner(s, text="38,167 cells (56%) retained as neural lineage — but averaged "
               "over age instead of region, every brain panel reads as zero",
       color=NAVY)


# ------------------------------------------------------- 16. next steps
s = blank(prs, dark=True)
title(s, "Where this leaves us", dark=True,
      sub="Three options, in the order I would try them")
opts = [
    ("1", "Make the transport kernel less absorbing",
     "The final stage is currently treated as fully self-transitioning, which is "
     "what concentrates all probability mass there. Switching to connectivity-based "
     "self-transitions is a one-line change.",
     "Cheap. Test on a 6,000-cell subsample first — about 4 minutes."),
    ("2", "Restrict to one dissected region",
     "Forebrain alone at E9.0–E10.0 breaks the dissection confound, because region "
     "is then held constant while stage varies.",
     "Costs the early timepoints entirely — no E7.0, so no root."),
    ("3", "Report the connectivity-kernel root, confound stated",
     "Macrostate 21 is a defensible root if the write-up says plainly that stage "
     "and dissection are not separable in this design.",
     "Honest but weak; reviewers will ask the same question."),
]
y = 2.02
for num, head, body, cost in opts:
    card(s, 0.7, y, 11.9, 1.36, fill=RGBColor(0x2A, 0x23, 0x26))
    textbox(s, 0.95, y + 0.16, 0.5, 0.5, num, size=24, font=HEAD, bold=True,
            color=EMBER, space_after=0)
    textbox(s, 1.6, y + 0.14, 10.8, 0.32, head, size=14.5, bold=True, color=WHITE,
            space_after=0)
    textbox(s, 1.6, y + 0.52, 7.4, 0.8, body, size=11.5, color=RGBColor(0xD8,0xD2,0xD4),
            line=1.18)
    textbox(s, 9.3, y + 0.52, 3.1, 0.8, cost, size=11, color=SAND, italic=True,
            line=1.18)
    y += 1.48
banner(s, text="Recommendation: option 1, validated on a subsample before "
                "committing another eight-kernel run")


prs.save(OUT)
print(f"wrote {OUT}: {len(prs.slides.__iter__.__self__._sldIdLst)} slides")
