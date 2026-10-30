#!/usr/bin/env python
"""Progress deck: one generated figure per slide, a title and a single line.

Every figure is read from results/figures/ as produced by the pipeline — none
are regenerated or restyled for the deck, so what is on the slide is what the
analysis actually output.
"""

from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN
from pptx.util import Inches, Pt

from build_deck import (  # noqa
    new_deck, blank, title, textbox, card, stat, bullets, table, footer, banner,
    fig_slide, fig_row, divider, place_fig,
    INK, DARK, CHERRY, EMBER, PEACH, SAND, NAVY, STEEL, GREY, MIDGREY, WHITE,
    TINT, TINT2, HEAD, BODY, W, H, TITLE_Y, CAP_Y, FIG_TOP, FIG_BOTTOM,
)

OUT = "progress_trajectory_inference.pptx"
prs = new_deck()

# ------------------------------------------------------------------ title
s = blank(prs, dark=True)
textbox(s, 0.9, 2.15, 11.5, 1.5,
        "Trajectory inference in the\nE7.0–E10.0 mouse embryonic brain",
        size=40, font=HEAD, bold=True, color=WHITE, line=1.1)
textbox(s, 0.9, 3.85, 10.6, 0.4,
        "La Manno E7–E10, joint integration with Brooks 2025, preliminary CellRank", size=15, color=SAND)
for i, (val, lab) in enumerate([("68,166", "cells, 19 libraries"),
                                ("107,629", "cells once Brooks is joined"),
                                ("8", "CellRank kernel weightings")]):
    x = 0.9 + i * 3.9
    textbox(s, x, 5.0, 3.6, 0.5, val, size=26, font=HEAD, bold=True, color=EMBER,
            space_after=0)
    textbox(s, x, 5.55, 3.6, 0.3, lab, size=11.5, color=MIDGREY, space_after=0)
textbox(s, 0.9, 6.55, 11.5, 0.3, "Yubin  ·  Moskowitz Lab  ·  30 October 2026",
        size=11, color=GREY, space_after=0)

# ================================================================== PART 1
divider(prs, "1", "The La Manno dataset on its own",
        "Quality control, feature selection, PCA, UMAP and hedgehog expression — "
        "before any integration.")

fig_slide(prs, "01_qc/violin_qc_by_age.png",
          "Quality control by stage",
          "Comparable across all five stages — no stage needed special handling.",
          note="Median 3,188 genes and 11,692 UMIs per cell. Mitochondrial "
               "fraction is under 1% everywhere, which is unusually clean. "
               "Filtering removed only 11 cells and 2,448 genes.")

fig_slide(prs, "01_qc/umap_qc.png",
          "Quality metrics on the UMAP",
          "No cluster is defined by depth or mitochondrial content — structure is not an artifact.")

fig_slide(prs, "02_pca_hvg/filter_genes_dispersion_hvg.png",
          "Highly variable gene selection",
          "2,000 genes per batch; hedgehog genes retained explicitly, being too sparse to survive.")

fig_slide(prs, "02_pca_hvg/pca_variance.png",
          "PCA variance is spread thin",
          "PC1 carries 4.5%; 50 components computed, the first 30 feed the neighbour graph.",
          note="sc.tl.pca(n_comps=50) then sc.pp.neighbors(n_neighbors=15, "
               "n_pcs=30) - 50 computed, 30 used. Elbow at PC8-10 and flat past "
               "PC15, so 30 is adequate-to-generous. Variance: PC1 4.5%, PC2 "
               "3.3%, first 10 19.9%, first 30 28.3%, all 50 32.0%. The flatness "
               "means the graph rests on many weak directions, which is part of "
               "why E7.0 separates so completely. Note the CellRank notebook "
               "rebuilds its graph as n_neighbors=30 over the full 50-component "
               "Harmony representation, so the PC count differs there.")

fig_slide(prs, "02_pca_hvg/pca_scatter_age.png",
          "PCA by stage",
          "E7.0 sits apart already in PCA space, before any graph is built.",
          note="Harmony-on-chip is shown as the second row for comparison only; it was rejected. The same figure exists for tissue and sample.")

fig_slide(prs, "03_umap_unintegrated/umap_age_tissue_sample.png",
          "Unintegrated UMAP",
          "By stage, region and library — hard to tell apart, because they covary by design.")

fig_slide(prs, "03_umap_unintegrated/umap_facet_age.png",
          "One panel per stage",
          "E7.0 touches nothing else: 98.6% self-neighbours, 0.0% reaching E9.0 or E10.0.",
          note="This is the central problem of the project. The graph has no path "
               "from E7.0 to the later stages, so a trajectory rooted there is "
               "unsupported by the graph it runs on.")

fig_slide(prs, "03_umap_unintegrated/umap_facet_tissue.png",
          "One panel per dissected region",
          "Dissection widens with stage, so region and stage cannot be separated.",
          note="Quantified: library pairs matching region across different stages "
               "correlate 0.9576, and pairs matching stage across different "
               "regions 0.9579. Indistinguishable. One region is worth about one "
               "stage step.")

fig_row(prs, ["03_umap_unintegrated/umap_leiden.png",
              "05_hedgehog/dotplot__hedgehog_by_leiden.png"],
        "Leiden clusters and hedgehog expression per cluster",
        "Expression is cluster-restricted rather than uniform — what a readout needs.",
        labels=["Leiden clusters", "Hh by cluster"])

fig_slide(prs, "05_hedgehog/umap_hedgehog_genes.png",
          "Hedgehog pathway on the UMAP",
          "Shh and Gli1 sparse and localised, Smo and Ptch1 broad; non-expressors in grey.",
          note="Scanpy's default viridis puts its darkest end at zero, which on a "
               "mostly-zero matrix buries the expressing cells under the "
               "majority. These plots paint non-expressors flat grey and the "
               "brightest cells last.")

fig_slide(prs, "05_hedgehog/violin_hedgehog_by_age.png",
          "Hedgehog expression by stage",
          "Activity rises after E8.0, as Shh signalling begins once the neural tube forms.")

fig_slide(prs, "04_harmony_chip/before_after_chip.png",
          "Harmony on chip — tested, then rejected",
          "Mixing rose 0.01% → 6.22%, but no chip spans both ends, so there was nothing to correct.",
          note="Harmony removes variation shared between batches. With no chip "
               "spanning both ends, the mixing it produced cannot be a corrected "
               "batch effect — it was manufactured because the key asserted the "
               "clouds were the same batch. Rejected, and we went looking for a "
               "real bridge instead.")

# ================================================================== PART 2
divider(prs, "2", "Joining Brooks 2025, and a first CellRank run",
        "A second dataset to bridge the E7.0–E8.0 gap, then velocity and optimal "
        "transport on the result.")

fig_slide(prs, "06_integration_brooks/dataset_comparison.png",
          "The two datasets are not technically alike",
          "3.6× deeper per cell, yet every cross-dataset stage pair sits at r = 0.93–0.96.",
          note="The flat heatmap is the point. If pseudobulk correlation cannot "
               "tell E7.0-vs-E8.5 apart from E8.0-vs-E8.0, it is not measuring "
               "developmental distance - it is measuring the shared "
               "mean-expression axis. The ceiling from two random halves of one "
               "stage is 0.9999, so 0.95 is far from identical.")

fig_slide(prs, "06_integration_brooks/before_after_dataset.png",
          "Integration by dataset, before and after Harmony",
          "Self-neighbour share falls from 99.6% / 99.8% to 80.3% / 86.3% — they interdigitate.")

fig_slide(prs, "06_integration_brooks/before_after_stage.png",
          "Integration by stage, before and after Harmony",
          "Nine stages form one gradient; the graph is now a single component, 100% of cells.",
          note="E7.0 to E7.5 neighbour share went from 0.05% to 8.75%, and to "
               "E7.75 from 0.03% to 3.33%. Critically, E7.0 to E9.0/E10.0 stayed "
               "at 0.01% - the bridge added intermediate stages rather than "
               "inventing a shortcut across three days.")

fig_slide(prs, "06_integration_brooks/umap_facet_stage.png",
          "Joint object, one panel per stage",
          "Brooks supplies E7.5 to E8.75 — exactly the window the La Manno series skips.")

fig_slide(prs, "09_joint_pca_features/pca_variance.png",
          "Joint PCA variance",
          "Same axes as slide 6: PC1 3.6% here versus 4.5% alone — two platforms spread it thinner.")

fig_slide(prs, "09_joint_pca_features/pca_scatter_dataset.png",
          "Joint PCA, uncorrected versus Harmony",
          "Components that separated the datasets no longer do — the intended behaviour.")

fig_slide(prs, "09_joint_pca_features/features_hedgehog_umap.png",
          "Hedgehog pathway on the joint UMAP",
          "All seven genes survive the 15,200-gene intersection; Shh in 3,578 of 107,629 cells.",
          top=1.85, bottom=5.6)

fig_slide(prs, "09_joint_pca_features/features_regional_umap.png",
          "Regional markers on the joint UMAP",
          "Six3, Otx2, En1, Gbx2 and Hoxb1 occupy distinct territory along the A–P axis.",
          top=1.85, bottom=5.6)

fig_slide(prs, "07_cellrank/scvelo_velocity_stream_age.png",
          "RNA velocity stream",
          "Regenerated with velocyto: 19.1% of reads unspliced vs the authors' 19.3%.",
          note="The published loom is no longer downloadable - the bucket 404s, "
               "and surviving mirrors either hold only pooled counts or exclude "
               "Gli1, Hhip and Shh. So it was rebuilt from the original BAMs.")

fig_row(prs, ["07_cellrank/scvelo_vk0.8_ck0.2_macrostates.png",
              "07_cellrank/scvelo_vk0.8_ck0.2_terminal.png",
              "07_cellrank/scvelo_vk0.8_ck0.2_initial.png"],
        "CellRank macrostates, terminal and initial states",
        "velocity 0.8 + connectivity 0.2, the only weighting placing a root in E7.0.",
        labels=["12 macrostates", "4 terminal states", "initial state"],
        note="Macrostate 21 is nominated as the root and is 100% E7.0 - but also "
             "100% from the one whole-embryo dissection, so the two readings "
             "cannot be told apart.")

fig_slide(prs, "07_cellrank/kernel_agreement.png",
          "Do the kernel weightings agree?",
          "Pairwise fate-probability correlation across the seven completed runs, 0.44 to 0.99.",
          note="This figure was empty on the first attempt. All eight runs had "
               "raised and the loop caught each exception while printing only its "
               "message, so the matrix was 0x0 and imshow produced a blank panel "
               "with no error anywhere.")

fig_row(prs, ["07_cellrank/scvelo_realtime_moscot_macrostates.png",
              "08_cellrank_joint/scvelo_joint_rtk0.5_ck0.5_macrostates.png"],
        "Optimal transport places no state in the early stages",
        "Neither run puts a macrostate in E7.0 — every state sits at E9.0 or later.",
        labels=["devbrain, moscot only", "joint, moscot + connectivity"],
        note="This is the finding that matters. Moscot was added specifically to "
             "carry early cells forward. In the joint object nothing lands before "
             "E8.0, so E7.0, E7.5 and E7.75 - 26% of the cells - are entirely "
             "unrepresented, Brooks bridge notwithstanding.")

# ================================================================== PART 3
divider(prs, "3", "Assumptions and open problems",
        "What the analysis currently takes for granted, and where that could "
        "bite.")

s = blank(prs)
title(s, "What this analysis assumes", size=26,
      sub="Each of these is load-bearing — if one is wrong, the conclusions move")
rows = [
    ["Assumption", "Why we need it", "How safe"],
    ["Harmony on dataset removes platform,\nnot biology",
     "Only way to put two chemistries\nin one graph", "Weakest link"],
    ["Brooks E7.5 is a valid intermediate\nbetween La Manno E7.0 and E8.0",
     "The bridge depends on it", "Untested"],
    ["Splicing ratios from our velocyto run\nmatch the authors'",
     "Velocity kernel depends on it", "Checked: 19.1 vs 19.3%"],
    ["30-cell macrostate anchors represent\ntheir surrounding region",
     "CellRank's default", "Unexamined"],
    ["Stage, not dissection, drives the\ntransitions we recover",
     "The whole trajectory reading", "Known to be false"],
]
cc = {(1, 2): SAND, (2, 2): SAND, (4, 2): SAND, (5, 2): CHERRY}
tbl = table(s, 0.7, 2.05, 11.9, rows, col_w=[4.9, 3.6, 3.4], row_h=0.78,
            head_h=0.42, size=12, cell_colors=cc)
tbl.cell(5, 2).text_frame.paragraphs[0].runs[0].font.color.rgb = WHITE

s = blank(prs, dark=True)
title(s, "Open problems, in the order they matter", dark=True, size=26,
      sub="Three of the four are structural rather than bugs")
items = [
    ("1", "No metastable state at E7.0 under any transport kernel",
     "Macrostates need stationary probability mass; a directed OT kernel gives "
     "early stages almost none, so they cannot be macrostates by construction. "
     "Root cell therefore unidentifiable."),
    ("2", "Stage and dissection are confounded, irreparably in this design",
     "Matching region across stages scores 0.9576; matching stage across regions "
     "0.9579. Every E7.0 macrostate is also 100% whole-embryo. No sample breaks "
     "the tie."),
    ("3", "Cross-platform integration may be removing real biology",
     "Same-stage across datasets (Spearman 0.674) is less similar than three days "
     "of development within one dataset (0.870). Harmony cannot tell which part "
     "is chemistry."),
    ("4", "Velocity alone fails to solve, and is the least trustworthy kernel",
     "60,762 of 68,166 rows did not sum to 1 — a solver failure, fixable. But 10x "
     "v1 chemistry and 3' bias make unspliced estimates weak here regardless."),
]
y = 1.92
for num, head, body in items:
    card(s, 0.7, y, 11.9, 1.02, fill=RGBColor(0x2A, 0x23, 0x26))
    textbox(s, 0.95, y + 0.12, 0.45, 0.45, num, size=22, font=HEAD, bold=True,
            color=EMBER, space_after=0)
    textbox(s, 1.5, y + 0.11, 10.9, 0.3, head, size=13.5, bold=True, color=WHITE,
            space_after=0)
    textbox(s, 1.5, y + 0.42, 10.9, 0.56, body, size=10.5,
            color=RGBColor(0xD0, 0xC9, 0xCB), line=1.18, space_after=0)
    y += 1.08
banner(s, text="Next: test a less absorbing transport kernel on a subsample "
                "before committing another eight-kernel run")

prs.save(OUT)
print(f"wrote {OUT}: {len(prs.slides._sldIdLst)} slides")
