# AI Tool Usage Report

Team SWBMCM2613050, Problem B, 2026 ShuWei Cup Fall Contest.

This report accompanies the 24-page team review candidate. The manuscript includes a report after the references. The chronological log lists the prompts, outputs, adoption and review status in 11 columns.

## ChatGPT (Codex) [16]

OpenAI, GPT-6 series, 20–21 November 2026. Earlier entries identify GPT-6.2 Sol. The exact deployment version for this revision and public release dates were unverified.

The team requested parameter transcription, solver prototypes, independent technical checks, replay and visualization, and LaTeX and archive preparation. In the latest request, the team specified a six-stage audit of commit dd5dd39, the four comparison designs, 24-page layout requirements, and reproducibility gates.

The candidate incorporates Codex's code and test changes, corrections to the P1–P3 analysis and its wording, exact dispatch and local route comparisons, deterministic P4 threshold results, figure edits, provenance records and layout. Automated checks reran these outputs. The record for this revision contains no completed independent team verification or documented human rewriting of the adopted changes.

## Antigravity (Gemini) [17]

Google DeepMind, Gemini (version not publicly disclosed), 21 November 2026.

The earlier prompts requested the offline 3D replay, figure production, a full discrete dispatch audit, actual solver sensitivity and Pareto studies, expansion and deduplication of the P4 suite, and an English manuscript. The candidate retains parts of the generated code, evidence, visualizations and manuscript text, including earlier drafting of formal derivations. This revision corrected specific errors and clarified the scope of the numerical evidence. Independent team verification and rewriting of the candidate are pending.

## WorkBuddy Agent

DeepSeek, DeepSeek-V4.1-Flash, 17 November 2026. The pre-contest log records research on submission and AI disclosure requirements. The model record and prior review status are preserved in the log.

## Locations and verification

- P1–P4 analysis and the sensitivity section of the manuscript contain the AI-assisted mathematical and numerical material described above.
- The accompanying Python code, tests, figures, and source tables support reproduction of the recorded outputs. The numerical provenance table links typeset values to source records. The full comparison precision is retained in the result CSV and JSON files.
- The complete prompt and output summaries, adoption decisions and current human-review status are recorded in AI_USAGE_LOG.csv. The latest entry covers the current revision.

In the follow-up review of d0f82c3, Codex drafted the revised monotonicity argument and implemented and ran supplemental synthetic stress and clearance checks. The team has yet to independently verify and rewrite this follow-up.
