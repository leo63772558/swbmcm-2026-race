# Reproducing the Problem B draft

From the directory containing `src/`, `data/` and `paper/`, run these commands in order.

    python src/solve_problem_b.py
    python src/check_problem_b.py
    python src/check_b_p2_fairness.py
    python src/check_b_p3_margin.py
    python src/check_b_p4_cross.py
    python src/check_b_p4_replay.py
    python src/render_problem_b.py

The solver uses the Python standard library and loads the transcribed input from the data directory. The renderer uses ReportLab, pypdf, Pillow, Poppler pdftoppm and Windows Times New Roman fonts. It produces vector PDF figures, 300 dpi PNG copies, a figure overview, B_prototype.tex and B_prototype_preview.pdf. To regenerate the editable TeX alone from recorded results, run the renderer with `--tex-only`.

Compile B_prototype.tex from the paper directory using Tectonic or XeLaTeX. This handoff was compiled with Tectonic's XeTeX engine using local TeX resources. Tectonic updates the references automatically. With XeLaTeX, rerun until the table of contents and page count stabilize.

    Push-Location paper
    tectonic --untrusted --keep-logs --keep-intermediates B_prototype.tex
    Pop-Location
    python src/package_problem_b.py --prototype --out submission/rebuilt
    python src/verify_handoff.py --bundle submission/rebuilt --tex-log paper/B_prototype.log --tex-toc paper/B_prototype.toc

The prototype command stages the compiled manuscript and its source archive in a new directory for internal use. To replay a trusted internal ZIP without recompiling the PDF, run `python src/verify_handoff.py --reproduce-zip <support.zip>`. For the team version, use the workspace copy of the packager so it can access the PDF checker. From `10_比赛工作区`, stage the completed team manuscript PDF and its matching support ZIP in a new directory.

    python src/package_problem_b.py --paper '<team-paper.pdf>' --support '<team-support.zip>'

The team command runs strict PDF QA before publishing the pair under `submission/final`. Add `--counted-pages N` when the report or appendices start after physical page N and do not count toward the main page limit. The signed commitment is a separate local file.

B_P2_schedules.csv contains all nominal scheduling events. B_P4.csv reports paired metrics and case parameters. B_timelines.json contains the nominal routes, issued plan before replanning, recovery state, locked observations, and revised routes with timestamps.

B_validation.csv contains fixed-seed Monte Carlo cross-checks, an independent replay of the scenario scores, and a search-budget comparison for the nominal schedule.

The audit outputs include B_P2_fairness.csv for paired station-pool and search-width probes, B_P3_margin.csv for the five coverage checkpoints, B_P4_cross.csv and its timeline JSON for the fully crossed existing inputs, and B_P4_replay.csv for the instruction-cache and clock-boundary probes. These checks retain the recorded nominal plan and original case scores.

## Working comparison and outage settings

For the main P2 fairness check, select the row with `probe=common_dynamic`, `screen=arrival` and `per_vehicle_k=8` in B_P2_fairness.csv. At each state, both policies sort reachable stations by arrival, ready time, point and path before keeping eight per vehicle. Fixed-order nearest assignment retains one continuation and sorts by the later vehicle arrival, then observation start. Beam search considers different alert orders with width 20. Both policies use the same route, visibility, pairing, synchronization and reset checks. Keep the matching `k=3` row as the sensitivity check. P4 uses the archived nominal plan in B_timelines.json.

The P4 replays assume the full nominal itinerary is cached before the outage. Surviving vehicles follow the nominal phase clock until communication recovers. A failed vehicle is removed. Its observation pair is preserved only if it started strictly before failure. Valid observations starting strictly before recovery are locked. A vehicle in transit is located by route interpolation. A vehicle in an already-started valid observation keeps its scheduled availability. For a vehicle that is still at the station for an unstarted observation, cancellation requires return to the parked heading. The extra reset time is elapsed time since arrival clipped to the interval from zero to nominal slew duration. The engine uses beam width three and two candidate stations per vehicle. A valid start must be strictly before the evaluation-window end. The alternate 35-second recovery, ongoing-only instructions and the single held-aim reset case are tracked separately in the audit files.

The beam schedule is a feasible incumbent. The rectangular road buffers and finite station candidates limit its optimality claims. For P4, the fixed policy retains instructions, counts a failed pair as unsuccessful after failure, and makes no assignment for newly arrived alerts. The listed scenarios are deterministic test cases, so their counts are descriptive.
