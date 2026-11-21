# AI Tool Usage Report (Standalone Compliance Addendum)

- **Team Control Number:** `SWBMCM2613050`
- **Problem Chosen:** Problem B — *Rapid UAV Localization via Coordinated Mobile Vehicles*
- **Competition:** 2026 ShuWei Cup International Mathematical Modeling Contest (Fall)
- **Policy Reference:** *2026 ShuWei Cup Regulations on the Use of Artificial Intelligence Tools (2026 Revision)* (effective 2026-11-11)
- **Page Quota Notice:** Also included as `Appendix B` of `BSWBMCM2613050.pdf` and archived separately in `BSWBMCM2613050fj.zip`; exempt from the 25-page main paper limit per Article 6.

---

## 1. Summary of AI Tools Used (Article 6 Nine-Field Table)

The in-contest tools are listed in References as [15]–[17]. The paper’s AI Usage Disclosure and Appendix B summarize all three tools. The complete 11-column chronology is in AI_USAGE_LOG.csv.

| Ref # | Tool Name | Version / Model | Developer / Organization | Dates Used | Usage Stage | Prompt / Operation Summary | Adoption Status | Verification & Location |
|---|---|---|---|---|---|---|---|---|
| `[15]` | ChatGPT (Codex) | GPT-5.4 / GPT-6.2 Sol / GPT-6 | OpenAI | 2026-11-20 to 2026-11-21 | Code, Verification, Replay, Figures, Typesetting | Parameter transcription checks, initial P1–P4 solver scaffolding, quadrature/MC validation, replay engine, Matplotlib visualization, LaTeX macro binding, final typography and disclosure alignment, package checks, and WP1 terminology and reference-order verification | Adapted & integrated into active pipeline | Cross-checked via exact B&B, Wilson CIs, and `pytest`; `src/*.py`, `paper/` |
| `[16]` | Antigravity (Gemini) | Gemini 3.1 Pro | Google DeepMind | 2026-11-21 | Audit, 3D Twin, Sensitivity, Pareto, Figures, Editing | Offline 3D digital twin UI & Chromium QA, 1,000-pair exact B&B audit, real-solver perturbation & 3D Pareto, 115-case P4 expansion + hysteresis sweep, 11-figure publication suite, LaTeX/proof/English remediation | Adapted & integrated into active pipeline | Verified via 6/6 hardcore audits, offline Chromium QA, and 9-file `pytest`; `src/*.py`, `figures/`, `simulator/B_Simulator.html`, `paper/` |
| `[17]` | WorkBuddy Agent | DeepSeek-V4.1-Flash | DeepSeek / Tencent | 2026-11-17; 2026-11-21 | Rule verification; precision-aware dispatch and keep-append studies | Checked the submission workflow and AI disclosure rules; implemented the crossing-angle guard sweep (`b_revision_precision_dispatch.py`) and the keep-append baseline (`b_revision_p4_append.py`), re-ran the exact B&B and the 115-case suite, and typeset the resulting tables | Adapted & integrated into `src/` and Tables 6 & 8 | Re-verified by the team against `results/P2_precision_tradeoff.csv` and `results/P4_keep_append_summary.csv`; the team led model design, interpretation, and derivation of conclusions |

---

## 2. Detailed Breakdown of AI Assistance vs. Verification Safeguards

| Work Stage | AI Assistance Used | Verification & Accountability Safeguards | Affected Files / Sections |
|---|---|---|---|
| **Problem Formulation & Mathematical Derivations** | Parameter verification against `B题题面参数.csv`, formulation cross-checks, formal proof editing (`Proposition 1`, `Theorem 1`, `Algorithm 1–2`) | Every sign, boundary condition ($a=0, b=0, \gamma\to 0^\circ/180^\circ, r=r_{\min}, \delta_{\mathrm{hyst}}\ge 0$), and locking clock (`t_start < t_rel`) was checked analytically and programmatically against official Problem B data. | `paper/B_submission.tex`, `paper/team/*.tex` |
| **Algorithm Implementation & Hardcore Audits** | Core solvers (`solve_problem_b.py`, `problem_b_geometry.py`), full-space 1,000-pairing / 4,200-order zero-truncation exact B&B (`b_hardcore_audit.py`), real P1–P4 solver sensitivity & raw-float 3D Pareto (`b_revision_sensitivity_pareto.py`), 115-case P4 deduplication/expansion & positive-threshold hysteresis sweep (`b_revision_p4_extended.py`), three batches of 2,000,000 independent NumPy Monte Carlo draws (`b_revision_probability.py`) | All 104 bound LaTeX macros are generated deterministically from `results/*.csv` and `results/*.json`. Independent seeded + unseeded B&B, finite-difference Jacobian checks (`<1e-10`), 6,000,000 independent Monte Carlo draws and three Bonferroni-adjusted 95% Wilson intervals, 6 automated hardcore audits, and 9 live-solver `pytest` suites verify all invariants. | `10_比赛工作区/src/*.py`, `03_code/run_all.py`, `tests/test_*.py` |
| **Visualization & Offline 3D Digital Twin** | 11 publication-grade Matplotlib figures (`fig01`–`fig11`, vector PDF + 320 dpi PNG, B&W hatching & colorblind-safe palettes), zero-CDN offline 3D Plotly WebGL + Canvas 2.5D dashboard (`simulator/B_Simulator.html`) with one-click `Auto-Tour` demo | All 11 rendered PNGs and compiled PDF pages visually inspected; `simulator/B_Simulator.html` verified offline in Headless Chromium (network disabled, WebGL + forced-context-loss Canvas, full Auto-Tour cycle, all 9 interactive controls, 0 external requests, 0 page errors, 770/770 Node.js assertions, 0 static building-obstacle collisions across 892 travel segments and 4,503 stationary states with continuous `r = 1.5 m` clearance). | `10_比赛工作区/src/b_revision_figures.py`, `10_比赛工作区/src/b_revision_replay.py`, `10_比赛工作区/src/b_replay*.js`, `figures/*`, `simulator/B_Simulator.html` |
| **Paper Typesetting & Editorial Verification** | XeLaTeX layout (`12 pt Times New Roman`, full A4, ≤25 main-body pages + exempt Appendices A & B, strict first-citation order `[1]`–`[17]`), academic English copy-editing, reference DOI verification | Zero fabricated data or citations; all 17 references verified in strict first-citation order; negative findings preserved transparently. Team members handle final human rewriting for AIGC reduction and official portal submission. | `paper/B_submission.tex`, `paper/team/*.tex`, `paper/B_submission.pdf` |
| **Packaging, Anonymity & Reproducibility** | Clean-room reproduction & packaging (`reproduce_b_revision.py`, `package_b_revision.py`), strict fail-fast PDF verification, SHA-256 hashed anonymity scanning | Automated `tests/test_submission_package.py` verifies zero identity leaks across `BSWBMCM2613050.pdf` and every member of `BSWBMCM2613050fj.zip`, excludes internal handoff/audit memos and duplicate PDFs from the official ZIP, enforces strict 11-column unified `AI_USAGE_LOG.csv`, and validates clean-room rerun via `python 03_code/run_all.py`. | `10_比赛工作区/src/package_b_revision.py`, `REPRODUCE.md`, `AI_USAGE_LOG.csv` |

---

## 3. Compliance Confirmation & Anonymity Statement

The team led model design, interpretation, and derivation of conclusions. AI provided implementation, numerical verification, visualization, and editorial and formatting assistance. The chronological entries record the adopted assistance and the items awaiting team review.

1. **No Fabricated Data or References:** Every numerical value, table, figure, and statistical interval is deterministically traced to executable code and verified outputs in `results/`.
2. **Code Attribution:** Every active AI-assisted script carries an Article 7 file-header disclosure documenting tool, version/provider, date, and scope.
3. **Strict Anonymity:** Neither this report, the main paper (`BSWBMCM2613050.pdf`), nor any source file, test file, or log inside `BSWBMCM2613050fj.zip` contains participant names, university names, or advisor information.
4. **Full Log Reference:** The complete line-by-line chronological ledger (unified 11-column schema) is archived in `AI_USAGE_LOG.csv`.
