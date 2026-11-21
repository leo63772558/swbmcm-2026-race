# AI Tool Usage Report (Standalone Compliance Addendum)

- **Team Control Number:** `SWBMCM2613050`
- **Problem Chosen:** Problem B — *Rapid UAV Localization via Coordinated Mobile Vehicles*
- **Competition:** 2026 ShuWei Cup International Mathematical Modeling Contest (Fall)
- **Policy Reference:** *2026 ShuWei Cup Regulations on the Use of Artificial Intelligence Tools (2026 Revision)* (effective 2026-11-11)
- **Page Quota Notice:** Submitted as a standalone compliance document; does not count toward the 25-page main paper limit.

---

## 1. Summary of AI Tools Used

In strict compliance with the 2026 ShuWei Cup AI Tool Usage Policy, our team fully and transparently discloses all artificial intelligence tools utilized during the competition. Every entry below is cross-referenced in the main paper's `References` section (`[14]` and `[15]`), the `AI Usage Disclosure` section of `B_submission.pdf`, and the complete 11-column chronological log `AI_USAGE_LOG.csv`.

| Ref # | Tool Name | Version / Model | Developer / Organization | Dates Used | Primary Roles |
|---|---|---|---|---|---|
| `[14]` | ChatGPT (Codex) | GPT-6 series / GPT-6.2 Sol | OpenAI | 2026-11-20 to 2026-11-21 | Initial parameter transcription checks, early solver prototyping, independent verification scripts, replay plumbing, archival packaging |
| `[15]` | Antigravity (Gemini) | Gemini | Google DeepMind | 2026-11-21 | Dark 3D digital twin UI & Chromium offline verification, 1,000-pairing exact Branch-and-Bound audit, real-solver parameter perturbation & 3D Pareto scripts, deduplicated/expanded 115-case P4 audit, 11-figure Matplotlib suite, 9-file `pytest` suite, LaTeX typesetting & editorial drafting/polishing |
| Log-only | WorkBuddy Agent | DeepSeek-V4.1-Flash | DeepSeek | 2026-11-17 (pre-contest) | Pre-contest official rules verification (submission steps & AI disclosure policy) |

---

## 2. Detailed Breakdown of AI Assistance vs. Human Decisions & Verification

To prevent any understatement or contradiction between the paper, code headers, and chronological logs, the table below specifies the exact scope of AI assistance across all competition stages:

| Work Stage | AI Assistance Used | Verification & Accountability Safeguards | Affected Files / Sections |
|---|---|---|---|
| **Problem Formulation & Modeling Decisions** | Parameter extraction checks, mathematical formulation review, errata consolidation, formal proof drafting (`Proposition 1`, `Theorem 1`) | All physical constraints, tie-breaking rules (readiness-first vs. arrival-first), closed-disk vs. closed-prism boundary semantics, and discrete/continuous optimality caveats were explicitly set and reviewed against official Problem B data (`B题题面参数.csv`). | `paper/B_submission.tex`, `paper/team/*.tex` |
| **Algorithm Implementation & Audits** | Solver prototyping (Codex), full-space 1,000-pairing / 4,200-order zero-truncation exact Branch-and-Bound audit (Antigravity), real P1–P4 solver sensitivity & 3D Pareto scripts, P4 deduplication/expansion & search-budget stability scripts | Every numerical result in the paper (72 bound LaTeX macros) is deterministically generated from Python scripts and stored in `results/*.csv` and `results/*.json`. Independent unseeded B&B (`initial_ub = inf`), central finite-difference Jacobian verification (`<1e-10`), $3\times 2\times 10^6$ Bonferroni–Wilson Monte Carlo CIs, 6 automated hardcore audits (`b_hardcore_audit.py`), and 9 `pytest` test modules (`tests/`) verify all math and geometry invariants. | `10_比赛工作区/src/*.py`, `03_code/run_all.py`, `tests/test_*.py` |
| **Visualization & 3D Digital Twin** | 11 publication-grade Matplotlib figures (`fig01`–`fig11`, PDF + PNG), zero-CDN dark 3D Plotly WebGL + Canvas 2.5D dashboard (`B_Simulator.html`) with one-click `Auto-Tour` demo | Visually inspected rendered PNGs and PDF pages; verified offline in Headless Chromium with network disabled (0 external requests, 0 page errors, 770/770 assertions, 0 collisions across 892 travel segments and 4,503 stationary states). | `10_比赛工作区/src/b_revision_figures.py`, `10_比赛工作区/src/b_revision_simulator.py`, `figures/*`, `interactive/B_Simulator.html` |
| **Paper Typesetting & Editorial Completion** | LaTeX layout (`12 pt Times New Roman`, A4, ≤25 pages, `tcolorbox` boxes, `Algorithm 1–2`), English prose completion and editorial polishing under explicit team instruction, IEEE reference DOI verification | Zero fabricated data or citations; all 15 references verified; all negative findings (V5 `+1.893 s` myopic penalty, `pan_speed=36°/s` greedy beam shift, weight-dependent sensitivity rank swaps) preserved transparently. Team members are responsible for final human sign-off and AIGC/similarity screening prior to official portal submission. | `paper/B_submission.tex`, `paper/team/*.tex`, `paper/B_submission.pdf` |
| **Packaging, Anonymity & Reproducibility** | Clean-room ZIP packaging (`BSWBMCM2613050fj.zip`), hash verification, strict anonymity scrubbing | Automated `tests/test_submission_package.py` verifies zero personal names or university identifiers across `B_submission.pdf` and all members of `BSWBMCM2613050fj.zip`, strict 11-column schema in `AI_USAGE_LOG.csv`, and clean-room rerun via `python 03_code/run_all.py`. | `10_比赛工作区/src/package_b_revision.py`, `VERIFY_REPORT.md`, `AI_USAGE_LOG.csv` |

---

## 3. Compliance Confirmation & Anonymity Statement

1. **No Fabricated Data or References:** Every numerical value, table, figure, and statistical interval is deterministically traced to executable code and verified outputs in `results/`.
2. **Code Attribution:** AI-assisted modules carry file-header notices documenting AI tool involvement.
3. **Strict Anonymity:** Neither this report, the main paper (`B_submission.pdf`), nor any source file or log inside `BSWBMCM2613050fj.zip` contains participant names, university names, or advisor information.
4. **Full Log Reference:** The complete line-by-line chronological ledger (11-column standard schema) is archived in `AI_USAGE_LOG.csv`.
