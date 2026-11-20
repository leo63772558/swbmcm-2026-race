"""Versioned output and provenance helpers for the B review workflow.

AI assistance: ChatGPT (Codex, GPT-6.2 Sol), OpenAI, used 2026-11-21.
Public model release date was not verified. Assistance: data export and QA.
"""
import csv
from hashlib import sha256
import json
from pathlib import Path

from problem_b_geometry import ROOT


DEFAULT_OUTPUT = ROOT / "submission" / "b_revision_20261121"
SOURCE_RESULTS = ROOT / "results"


def read_csv(path):
    with path.open(encoding="utf-8-sig", newline="") as file:
        return list(csv.DictReader(file))


def write_csv(path, rows):
    rows = list(rows)
    if not rows:
        raise ValueError(f"Empty evidence table: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=rows[0])
        writer.writeheader()
        writer.writerows(rows)


def read_json(path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + "\n",
                    encoding="utf-8")


def digest(value):
    data = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)
    return sha256(data.encode("utf-8")).hexdigest()


def file_hash(path):
    return sha256(Path(path).read_bytes()).hexdigest()


def case_parameters(case_id, spec, disturbance, horizon, rule):
    _, goal, failed, receivable = spec
    if receivable < disturbance or receivable > horizon:
        raise ValueError("Invalid absolute communication recovery time")
    return {
        "case": case_id, "disturbance_s": disturbance, "failure_s": disturbance if failed is not None else None,
        "absolute_recovery_s": receivable if receivable > disturbance else None,
        "dispatch_allowed_from_s": receivable, "outage_duration_s": receivable - disturbance,
        "horizon_s": horizon, "failed_vehicle": failed + 1 if failed is not None else None,
        "new_target": goal, "outage_rule": rule,
    }


def window_score(starts, requested, window_start, horizon, incomplete):
    valid = {alert: t for alert, t in starts.items() if window_start <= t < horizon}
    if not valid.keys() <= requested:
        raise ValueError("Unrequested alert in replay")
    count = len(valid)
    return count, count / len(requested), max(valid.values()) if count == len(requested) else incomplete
