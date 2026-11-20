# Reproducing the Problem B draft

From the repository root, run these commands in order.

    python '10_比赛工作区/src/solve_problem_b.py'
    python '10_比赛工作区/src/check_problem_b.py'
    python '10_比赛工作区/src/render_problem_b.py'

The solver uses the Python standard library and loads the transcribed input from the data directory. The renderer uses ReportLab, pypdf, Poppler pdftoppm and Windows Times New Roman fonts. It produces the vector figures, B_prototype.tex and B_prototype_preview.pdf.

Compile B_prototype.tex from the paper directory using Tectonic or XeLaTeX. This handoff was compiled with Tectonic's XeTeX engine using local TeX resources. Tectonic updates the references automatically. With XeLaTeX, rerun until the table of contents and page count stabilize.

    Push-Location '10_比赛工作区/paper'
    tectonic --untrusted B_prototype.tex
    Pop-Location
    python '10_比赛工作区/src/package_problem_b.py'

The packaging step uses the compiled B_prototype.pdf and checks its structure and embedded fonts before staging the numbered paper and source archive. The signed commitment is a separate local file.

B_P2_schedules.csv contains all nominal scheduling events. B_P4.csv reports paired metrics and case parameters. B_timelines.json contains the nominal routes, issued plan before replanning, recovery state, locked observations, and revised routes with timestamps.

B_validation.csv contains fixed-seed Monte Carlo cross-checks, an independent replay of the scenario scores, and a search-budget comparison for the nominal schedule.

The beam schedule is a feasible incumbent. The rectangular road buffers and finite station candidates limit its optimality claims. For P4, the fixed policy retains instructions, counts a failed pair as unsuccessful after failure, and makes no assignment for newly arrived alerts. The listed scenarios are deterministic test cases, so their counts are descriptive.
