"""Independent numerical checks of the existing Problem 3 uncertainty model.

AI assistance: ChatGPT (Codex, GPT-6.2 Sol), OpenAI, used 2026-11-21.
Public model release date was not verified. This is numerical review evidence.
"""
from functools import cache
from math import atan2, degrees, erf, erfc, exp, pi, radians, sqrt, tan
from random import Random
from statistics import NormalDist

from problem_b_geometry import number, read_values
from b_revision_data import SOURCE_RESULTS, read_csv, write_csv, write_json


DISTANCE = number("p3", "target", "horizontal_range")
A, B = read_values("p3", "position", "coordinate_std_intercept", "coordinate_std_slope")
OFFSET, CONTROL = read_values("p3", "gimbal", "zero_offset_std", "control_error_std")
MARGIN, REQUIRED = read_values("p3", "error", "absolute_error_max", "coverage_min")
CHECK = number("p3", "vehicle", "parameter_check_distance")
GIMBAL = sqrt(OFFSET**2 + CONTROL**2)
SEED = 261305031
SAMPLES = 2_000_000
Z_WINDOW = 10  # integration truncation in independent standard deviations
ROOT_HALF_WIDTH = 0.0001  # m; verification bracket, not the reported experimental precision


@cache
def nodes(n, lo=-Z_WINDOW, hi=Z_WINDOW):
    h = (hi-lo)/n
    return tuple((z, (1 if i in (0, n) else 4 if i % 2 else 2)
                  * h * exp(-z*z/2) / (3 * sqrt(2*pi)))
                 for i in range(n+1) for z in (lo + h*i,))


def coverage(sigma, n=96, gimbal=GIMBAL):
    """Condition on longitudinal error and gimbal error, integrate lateral CDF."""
    if sigma == 0:
        return erf(MARGIN/ (sqrt(2)*gimbal)) if gimbal else 1.0
    if MARGIN + Z_WINDOW * gimbal >= 90:
        raise ValueError("Forward wedge only verified inside the stated gimbal window")
    lo = max(-Z_WINDOW, -DISTANCE/sigma)
    longitudinal = nodes(n, lo, Z_WINDOW)
    turns = nodes(n) if gimbal else ((0.0, 1.0),)
    total = 0.0
    for g, outer_weight in turns:
        lower = tan(radians(-MARGIN-g*gimbal)) / sqrt(2)
        upper = tan(radians(MARGIN-g*gimbal)) / sqrt(2)
        total += outer_weight * sum(
            weight * (erf(upper*(DISTANCE/sigma+x)) - erf(lower*(DISTANCE/sigma+x))) / 2
            for x, weight in longitudinal
        )
    return total


def find_crossing(n):
    lo, hi = 0.0, CHECK
    assert coverage(A+B*lo, n) >= REQUIRED > coverage(A+B*hi, n)
    for _ in range(35):
        mid = (lo+hi)/2
        if coverage(A+B*mid, n) >= REQUIRED:
            lo = mid
        else:
            hi = mid
    return (lo+hi)/2


def wilson(k, n, z):
    p = k/n
    scale = 1+z*z/n
    center = (p+z*z/(2*n))/scale
    width = z*sqrt(p*(1-p)/n+z*z/(4*n*n))/scale
    return center-width, center+width


def monte_carlo(probes):
    rng = Random(SEED)
    counts = [0] * len(probes)
    sigma = [(A+B*s) for s in probes]
    gauss = rng.gauss
    for _ in range(SAMPLES):
        zx, zy = gauss(0, 1), gauss(0, 1)
        error = gauss(0, OFFSET) + gauss(0, CONTROL)
        for i, spread in enumerate(sigma):
            angle = degrees(atan2(spread*zy, DISTANCE+spread*zx))
            if abs((angle+error+180) % 360 - 180) <= MARGIN:
                counts[i] += 1
    z = NormalDist().inv_cdf(1-.05 / (2*len(probes)))
    return [{"distance_m": s, "samples": SAMPLES, "hits": k, "estimate": k/SAMPLES,
             "simultaneous_95_lower": lo, "simultaneous_95_upper": hi,
             "required": REQUIRED, "seed": SEED,
             "assessment": "above" if lo > REQUIRED else "below" if hi < REQUIRED else "indeterminate"}
            for s, k in zip(probes, counts) for lo, hi in (wilson(k, SAMPLES, z),)]


def run(out):
    baseline, = read_csv(SOURCE_RESULTS / "B_P3.csv")
    original = float(baseline["path_cap_m"])
    thresholds = {n: find_crossing(n) for n in (96, 192)}
    crossing = thresholds[192]
    assert abs(crossing - original) < 0.001
    cuts = crossing - ROOT_HALF_WIDTH, crossing + ROOT_HALF_WIDTH
    bracket = [{"nodes": n, "s_lower_m": cuts[0], "s_upper_m": cuts[1],
                "p_lower_s": coverage(A+B*cuts[0], n),
                "p_upper_s": coverage(A+B*cuts[1], n)}
               for n in (96, 192, 384)]
    assert all(row["p_lower_s"] > REQUIRED > row["p_upper_s"] for row in bracket)
    spread = A+B*crossing
    sigma_cut = A+B*(3*CHECK)
    z_error, z_position = 3, 3
    # Union bound for the tail in s, using the upper bound on the longitudinal
    # displacement on its retained event and the circular angular triangle bound.
    max_cross_track = (DISTANCE/sigma_cut+z_position) * tan(radians(MARGIN+z_error*GIMBAL))
    far_bound = erf(max_cross_track/sqrt(2)) + erfc(z_error/sqrt(2)) + erfc(z_position/sqrt(2))/2
    assert far_bound < REQUIRED
    scan_spots = sorted(set([i*0.5 for i in range(int(6*CHECK)+1)] + [*cuts, crossing, CHECK]))
    scan = []
    for s in scan_spots:
        sig = A+B*s
        variance = degrees(sig/DISTANCE)**2 + GIMBAL**2
        p_linear = erf(MARGIN/sqrt(2*variance))
        scan.append({"distance_m": s, "nonlinear_coverage": coverage(sig),
                     "linear_coverage": p_linear, "linear_variance_deg2": variance,
                     "required": REQUIRED})
    assert all(a["nonlinear_coverage"] >= b["nonlinear_coverage"]-1e-12 for a,b in zip(scan, scan[1:]))

    mc = monte_carlo([crossing-0.5, crossing+0.5, CHECK])
    assert [row["assessment"] for row in mc] == ["above", "below", "below"]
    ablations = []
    for s in (0.0, crossing, CHECK):
        sig = A+B*s
        contributions = (degrees(sig/DISTANCE)**2, OFFSET**2, CONTROL**2)
        for label, loc, gim in (("all", sig, GIMBAL), ("without_position", 0, GIMBAL),
                                ("without_zero_offset", sig, CONTROL),
                                ("without_control", sig, OFFSET)):
            ablations.append({"distance_m": s, "variant": label, "coverage": coverage(loc, gimbal=gim),
                              "position_variance_share": contributions[0]/sum(contributions),
                              "zero_offset_variance_share": contributions[1]/sum(contributions),
                              "control_variance_share": contributions[2]/sum(contributions)})
    parameter_probes = []
    for label, fraction in (("inside", .99), ("on_crossing", 1), ("outside", 1.01)):
        for share in (0, .5, 1):
            a, b = spread*fraction*share, spread*fraction*(1-share)/CHECK
            parameter_probes.append({"case": label, "a_m": a, "b_m_per_m": b, "distance_m": CHECK,
                                     "sigma_m": a+CHECK*b, "coverage": coverage(a+CHECK*b)})
    assert all((p["coverage"] >= REQUIRED if p["case"] == "inside" else
                p["coverage"] < REQUIRED if p["case"] == "outside" else
                abs(p["coverage"]-REQUIRED) < 1e-9) for p in parameter_probes)

    write_csv(out / "P3_curve.csv", scan)
    write_csv(out / "P3_bracket.csv", bracket)
    write_csv(out / "P3_MC.csv", mc)
    write_csv(out / "P3_ablation.csv", ablations)
    write_csv(out / "P3_parameters.csv", parameter_probes)
    summary = {
        "archived_distance_m": original, "independent_crossing_m": crossing,
        "linearized_distance_m": float(baseline["linear_path_cap_m"]),
        "sigma_at_crossing_m": spread, "bracket_m": cuts,
        "quadrature_node_crossing_m": thresholds, "monotone_scan_points": len(scan),
        "tail_start_m": 3*CHECK, "tail_probability_upper_bound": far_bound,
        "omitted_standard_normal_tail_by_union_bound": 2*erfc(Z_WINDOW/sqrt(2)),
        "mc_samples_per_probe": SAMPLES, "mc_seed": SEED,
        "note": "Deterministic quadrature bracket and scan; the team supplies the continuous proof.",
    }
    write_json(out / "P3_verification.json", summary)
    print(f"P3 independent crossing {crossing:.9f} m; 3x{SAMPLES:,} MC classifications passed")
    return summary
