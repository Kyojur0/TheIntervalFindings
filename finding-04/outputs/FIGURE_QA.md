# Finding 04 figure QA

**PASS — all eight requested PNG exports reviewed visually.** Checked 12 September 2026. This is the authoring/visual pass; the separate method and claim verification remains independent.

- Four figures each have light and dark variants in `../figures/`, all 2100 × 1270 pixels at 200 dpi. `../analysis/make_figures.py` exposes `make_figures(results_dir, figures_dir)` and ran successfully after the final wording changes.
- The copied `figure_spec.py` is byte-identical to Finding 03's supplied specification. Palette, serif headings, mono source lines, quiet axes and direct labels follow that specification. No legend boxes appear.
- Every figure states **reported England pathways; NONC excluded** and **submitted data; no estimates for missing providers**. Notes distinguish time waited so far from completed waiting times. First-release data caveats are visible.
- Text, endpoint labels, tick labels, notes and source lines are legible and contained within the exported canvas in both themes. No material overlaps or clipping remain. The parent separately inspected all four light figures.
- The median and p92 charts show the full 29-month sequence with first and latest dates visible. Their axes start at zero. The 18-week reference is explicitly distinguished from the median; the promise chart shows the latest 20.6-week gap, alongside p50 12.4 and p92 38.6 weeks.
- The composition chart accurately shows within-18-week pathways as the largest block. Latest labels are 4.690m / 65.6%, 2.362m / 33.0%, and 0.102m / 1.4%. Its title says the middle **has shrunk**, avoiding a claim of uninterrupted monthly decline.
- The distribution uses all 104 closed weekly bands plus the 177 pathways in the open 104+ band. The latter appears separately on an explicitly labelled count scale, with no invented finite upper endpoint or one-week width. The script checks that the 105 counts reconcile to the latest headline total.

The reviewed surface is the standalone PNG export. No website/mobile layout or colour-vision simulation is claimed in this pass.
