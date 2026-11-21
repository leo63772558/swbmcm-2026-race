# Problem B Supporting Package — Deterministic Reproduction Guide

Team Control Number: `SWBMCM2613050`  
Problem Chosen: **Problem B — Rapid UAV Localization via Coordinated Mobile Vehicles**

## 1. Open the Offline 3D Digital Twin

Open `artifacts/simulator/B_Simulator.html` directly in any modern browser (no internet connection or CDN required). The single HTML file embeds the complete scenario dataset, Plotly WebGL 3D renderer, and an automatic Canvas 2.5D orthographic fallback, including a one-click **Auto-Tour: V5 Fault & Dual-Strategy Demo** and 9 interactive inspection controls.

`artifacts/figures/` contains all **11 publication-grade analytical figures (`fig01`–`fig11`)** as both vector PDF and 320 dpi PNG, plus 3 replay keyframe panels under `artifacts/figures/replay_frames/`. `FIGURE_SOURCES.csv` maps every figure to its source CSV/JSON files.

Optional headless browser verification (requires Python `playwright` and a local Chromium binary):

```text
python -B src/b_replay_browser_check.py artifacts/simulator/B_Simulator.html --chromium <path/to/chrome> --proof _browser_checks.json --screenshots _browser_frames
```

## 2. Deterministic Full-Pipeline Reproduction

Extract `BSWBMCM2613050fj.zip` into an empty directory and install the pinned Python dependencies (Node.js is required for replay state assertions; XeLaTeX or Tectonic + `pdftoppm` is required for PDF compilation):

```text
python -m pip install -r requirements-review.txt
python 03_code/run_all.py --out _b_rerun
```

To use the lower-level runner for only the numerical, figure, and simulator stages, pass `--skip-pdf` explicitly (the runner refuses to silently skip PDF compilation).

From the full repository root, the strict fail-fast entry point is:

```text
python 03_code/run_all.py
python -m pytest tests/ -v
```

`reproduce_b_revision.py` regenerates all P1–P4 correctness checks, independent 3×2,000,000 Monte Carlo validation, matched P2 dispatch & 73-case P4 experiments, real-solver parameter perturbation & 3D Pareto analysis, 115-case deduplicated/expanded P4 resilience & positive-threshold hysteresis sweeps, all 11 vector PDF + 320 dpi PNG figures, the offline 3D simulator HTML, the 3-pass XeLaTeX paper (`B_submission.pdf`), and all 6 hardcore automated audits (including full 1,000-pairing / 4,200-order seeded and unseeded exact Branch-and-Bound).
