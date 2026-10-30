# Progress deck

`../progress_trajectory_inference.pptx`, 30 slides, built from source rather
than edited by hand so every slide traces to the run that produced it.

One generated figure per slide, with a title and a single line. The figures are
read straight out of `results/figures/` — none are regenerated or restyled for
the deck, so what is on the slide is what the analysis actually output. Detail
that does not fit in one line goes into the speaker notes rather than onto the
slide.

Structure: part 1 is the La Manno dataset alone (QC → HVG → PCA → UMAP →
hedgehog), part 2 adds Brooks and the first CellRank run, part 3 is assumptions
and open problems.

## Rebuild

```
cd docs/deck
/project/imoskowitz/yubin/envs/cellrank_traj/bin/python slides.py
/project/imoskowitz/yubin/envs/cellrank_traj/bin/python geomqa.py      # layout QA
cp progress_trajectory_inference.pptx ..
```

- `build_deck.py` — theme, layout grid and the drawing helpers. All geometry is
  derived from one set of constants (`TITLE_Y`, `BODY_Y`, `BANNER_Y`, `FOOTER_Y`)
  and one pair of text metrics (`CHAR_W`, `LINE_H`).
- `slides.py` — the content, one block per slide.
- `geomqa.py` — estimates wrapped text height against each box, and reports
  overlaps and margin violations. This cluster has no LibreOffice, so the usual
  render-and-look visual check is not available; `geomqa.py` stands in for it.
  It shares its text metrics with `build_deck.py`, so a box sized by the builder
  is measured the same way by the checker.
- Figures are referenced by path under `FIGROOT` in `build_deck.py`, scaled to
  fit each slide's figure band by `place_fig` / `fig_row`. Nothing is copied, so
  re-running the pipeline updates the deck on the next build.

The palette is the expression colormap used in every figure in the project
(`#FCC9B4 → #99000D`), so the deck and the figures read as one piece of work.
