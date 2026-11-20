"""Render the audit results as a compact, print-ready vector figure."""

import csv

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from problem_b_geometry import ROOT


def read_rows(filename):
    with (ROOT / "results" / filename).open(newline="") as file:
        return list(csv.DictReader(file))


def main():
    bound_row = read_rows("B_P2_bound.csv")[-1]
    lower, candidate = (float(bound_row[key]) for key in ("lower_s", "incumbent_s"))
    raw = read_rows("B_P2_schedules.csv")
    original = max(float(row["start"]) for row in raw if row["policy"] == "beam")
    cases = read_rows("B_P4_policy_comparison.csv")
    v5 = next(row for row in cases if row["scenario"] == "failure_V5")
    keep, replan = (float(v5[key]) for key in ("keep_latest_s", "replan_latest_s"))

    ink, gray, blue, amber = "#17263A", "#526378", "#166777", "#A2481D"
    plt.rcParams.update({
        "font.family": "DejaVu Sans", "font.size": 9, "text.color": ink,
        "axes.labelcolor": gray, "xtick.color": gray, "ytick.color": ink,
        "pdf.fonttype": 42, "savefig.facecolor": "white",
    })
    fig, (left, right) = plt.subplots(1, 2, figsize=(8.8, 2.95))
    fig.subplots_adjust(left=.205, right=.98, top=.82, bottom=.22, wspace=.82)
    left.set_title("P2 · Nominal schedule", loc="left", fontsize=11, fontweight="bold", pad=12)
    left.axvspan(lower, candidate, color="#E4F0F0", zorder=0)
    left.set_yticks([2, 1, 0], ["Continuous bound", "Refined stations", "Original stations"])
    for y, value, color in zip((2, 1, 0), (lower, candidate, original), (gray, blue, ink)):
        left.scatter(value, y, s=32, color=color, zorder=3)
        left.annotate(f"{value:.3f}", (value, y), xytext=(7, 0), textcoords="offset points",
                      va="center", color=color, fontweight="bold")
    left.set_ylim(-.5, 2.5)
    left.set_xlim(lower - .22, original + .6)
    left.annotate(f"{candidate-lower:.3f} s gap", ((candidate + lower) / 2, 1.55),
                  ha="center", va="center", color=blue)

    right.set_title("P4 · V5 fails, no new alert", loc="left", fontsize=11,
                    fontweight="bold", pad=12)
    right.barh([1, 0], [keep, replan], color=[blue, amber], height=.36, zorder=3)
    right.set_yticks([1, 0], ["Keep plan", "Replan"])
    for y, value in ((1, keep), (0, replan)):
        right.annotate(f"{value:.3f}", (value, y), xytext=(5, 0), textcoords="offset points",
                       va="center", fontweight="bold")
    right.set_xlim(0, replan + 3.25)
    right.set_ylim(-.55, 1.55)
    right.text(.02, .52, f"+{replan-keep:.3f} s with replanning",
               transform=right.transAxes, va="center", color=amber)

    for ax in (left, right):
        ax.set_xlabel("Latest observation start (s)", labelpad=8)
        ax.grid(axis="x", color="#DEE6EB", linewidth=.65)
        ax.set_axisbelow(True)
        ax.tick_params(length=0, pad=6)
        for spine in ax.spines.values():
            spine.set_visible(False)
    fig.savefig(ROOT / "results" / "B_schedule_audit.pdf")
    plt.close(fig)


if __name__ == "__main__":
    main()
