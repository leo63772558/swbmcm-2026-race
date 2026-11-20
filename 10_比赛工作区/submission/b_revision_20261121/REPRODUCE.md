# Problem B engineering review package

This package contains the team's technical handoff, marked review manuscript, independently checked diagnostic files, and the offline simulator. The independent competition solution and final prose are team deliverables. The archived solver is included as a reproducibility reference.

## Open or rebuild

1. Extract the support ZIP. Open `artifacts/simulator/B_Simulator.html` with its adjacent `assets/` folder intact. The 3D field uses the bundled Plotly.js GL3D runtime and a WebGL-capable browser. The separate vectors and PNGs remain available if WebGL is unavailable.
2. From the extracted directory, install the pinned Python requirements for a compatible Python environment. The diagnostic pipeline also needs Poppler `pdftoppm`, Node.js, and Times New Roman. Use `B_TNR_REGULAR` and `B_TNR_BOLD` to set other local paths to those fonts.
3. Run one command from the extracted root.

   ```text
   python -B src/reproduce_b_revision.py --out _b_rerun
   ```

   Have Tectonic and its resources cached locally if you also want the source build.

   ```text
   python -B src/reproduce_b_revision.py --out _b_tex_rerun --tex-bundle path/to/tectonic/bundle
   ```

   In a regular XeLaTeX installation, compile `artifacts/paper/B_submission.tex` from its directory, running XeLaTeX repeatedly until the contents and page totals settle. It uses `B_review_metrics.tex` and sibling figures. The same instructions apply to `P1_ERRATA.tex`.

The pipeline runs boundary checks, then area/route/probability diagnostics, then matched experiments, then figures and replay. Providing a TeX bundle adds compilation and full PDF checks afterward. It creates a new output tree and checks the produced evidence against the bundled reference on the same platform. The core data directory and archived CSV inputs stay outside the output tree.

## Files

- `data/` holds read-only statement transcriptions. `results/` holds the archived CSV references consumed by the checks.
- `src/` contains the archived solver and the revision workflow.
- `artifacts/results/` includes all calculated revision evidence, executed intervals and the stable plan ID.
- `artifacts/figures/` includes seven 300 dpi PNG and vector PDF pairs, plus three paired-frame drawings. The caption inputs are in the accompanying CSV source files.
- `artifacts/paper/` contains the TeX and PDFs, as well as the number provenance table.
- `TEAM_HANDOFF_CHECKLIST.md` maps the team's remaining independent work to sections, proof obligations and data.
- The official naming convention, size and copy status are checked separately. The signed commitment is handled independently by the team.
