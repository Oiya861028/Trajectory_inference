# Progress deck

`../progress_trajectory_inference.pptx`, 16 slides, built from source rather
than edited by hand so the numbers on the slides can be traced to the run that
produced them.

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
- `fig_*.png` — crops of `results/figures/09_joint_pca_features/` sized for
  slides. Regenerate them if those figures change.

The palette is the expression colormap used in every figure in the project
(`#FCC9B4 → #99000D`), so the deck and the figures read as one piece of work.
