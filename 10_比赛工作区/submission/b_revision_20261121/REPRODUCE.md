# Problem B reproduction guide

Extract `BSWBMCM2613050fj.zip` into a new directory and run the following from that directory.

```text
python -m pip install -r requirements.txt
python 03_code/run_all.py --list
python 03_code/run_all.py --out _b_rerun
```

Use a fresh output path. Without `--out`, the entrypoint creates a temporary run directory. Add `--keep-temp` to retain it for inspection. The command also runs from the repository root with the same arguments. From the repository, install Python dependencies using the candidate directory's `requirements-review.txt`.

The release environment uses Python 3.14.7, Node.js 24.19.0, MiKTeX XeTeX 4.10, Poppler 26.07.0, and Times New Roman fonts. The Python packages are pinned in `requirements.txt`. For byte-level graphics matching, use the same operating system, fonts, and rendering versions. XeLaTeX is selected by default when present. To use Tectonic with a cached compatible bundle, pass `--tex-bundle path/to/local-bundle.zip`.

## Verification

The runner regenerates the numerical results, all 11 paired PDF/PNG figures, the offline replay, and both paper PDFs. It also executes the six audit checks, including seeded and unseeded discrete branch-and-bound, and tests replay state agreement with Node.js. Figure 11 uses the frozen browser captures packaged with the data.

`artifacts/REPRODUCIBILITY_MANIFEST.json` records the checksum of every mandatory regenerated artifact, the published PDF bytes, and the text of each PDF page. The compiler uses a fixed build timestamp. Both recompiled PDFs must match the published files by SHA-256 and page text. Byte-identical reproduction requires the pinned environment and compiler used to produce the reference files. The runner writes `REPRODUCTION_CHECK.json` after every required check passes. The packager runs the same entrypoint from a fresh extraction of the final ZIP and records the proof in `RELEASE_ACCEPTANCE.json` and the engineering handoff.

## Offline replay

Open `artifacts/simulator/B_Simulator.html` directly in a browser. Plotly WebGL and the Canvas fallback are bundled in the file. `artifacts/figures/FIGURE_SOURCES.csv` lists the evidence used for the plots.

## Rebuild the archive from the repository

```text
python -B 10_比赛工作区/src/package_b_revision.py
```

The packager checks the 24-page paper, creates the manifest and ZIP, and verifies the package by reproducing it in a fresh directory. Use `--work path/to/new-directory` to keep the extracted package and rebuilt files for inspection.
