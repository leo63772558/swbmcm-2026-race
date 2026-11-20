# Problem B engineering review package

The checked numerical baseline is commit `9c2fef8`. The simulator, figures, and review PDF use its parameter table, experiment tables and event records. Consult `TEAM_HANDOFF_CHECKLIST.md` for the derivations, interpretations, and English manuscript that the team must complete independently.

## Open the offline replay

Double-click `artifacts/simulator/B_Simulator.html` in a browser. The HTML alone contains the renderer and scenario data. WebGL uses the embedded Plotly distribution. If WebGL is unavailable, Canvas renders the same scene with an orthographic 2.5D view. The files under `simulator/assets/` are inputs for rebuilding and include the Plotly license.

`artifacts/figures/` contains the eight PDF and PNG pairs. `artifacts/figures/replay_frames/` contains the three standalone keyframes. `FIGURE_SOURCES.csv` links figures to the frozen data and identifies illustrative calculations.

The optional browser check uses Python Playwright and a Chromium installation. From the extracted archive, run `python -B src/b_replay_browser_check.py artifacts/simulator/B_Simulator.html --proof _browser_checks.json --screenshots _browser_frames`. Supply `--chromium path/to/chrome` to select an installed browser. The check copies only the HTML to an empty directory and exercises both renderers offline.

## Reproduce from the support archive

Extract `BSWBMCM2613050fj.zip` into an empty directory. Install the pinned Python requirements from that directory. Node.js checks the replay states. The optional PDF stage also requires Tectonic, a cached resource bundle with the required fonts, and Poppler `pdftoppm`.

```text
python -m pip install -r requirements-review.txt
python -B src/reproduce_b_revision.py --out _b_rerun
python -B src/reproduce_b_revision.py --out _b_tex_rerun --tex-bundle path/to/local-bundle.zip
```

Choose a fresh output directory for each run. The scripts regenerate the checks, numeric results, eight paired figures, keyframes, HTML, and optional PDFs in the output directory. `REPRODUCTION_CHECK.json` records matching artifact hashes and, for the PDF stage, page-by-page text matches. CSV and JSON hashes normalize Windows line endings to the Git convention. Exact image hashes assume the pinned versions and the same fonts and rendering platform.

To compile in XeLaTeX, open `artifacts/paper/B_submission.tex` or `P1_ERRATA.tex` from that paper directory. Compile repeatedly until the table of contents, references, and page totals settle. The manuscript uses the bound macros in `B_review_metrics.tex` and figures in the sibling directory.

## Build the review archives from the repository

```text
python -B 10_比赛工作区/src/package_b_revision.py --bundle path/to/local-bundle.zip
```

The packager reruns from a fresh extraction, checks the ZIP paths, CRCs and member hashes, and writes `RELEASE_ACCEPTANCE.json`. The two ZIPs and review PDF are internal handoff artifacts. The team handles the signed commitment and official submission separately.
