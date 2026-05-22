"""
Step 4: Build 30-point metric time series for each incident.

For AIOpsArena incidents: extracts real CSV values around the fault window.
For GAIA incidents: synthesizes realistic time series using real peak/baseline.

Adds "timeseries" field to each incident in incidents_with_fixes.json.
Output: data/incidents_with_fixes.json (updated in-place)
"""

import json
import math
import os
import random
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
DATA_DIR = ROOT / "data"
AIOPS_DIR = DATA_DIR / "aiopsarena"
INPUT_FILE = DATA_DIR / "incidents_with_fixes.json"

POINTS = 30          # total time-series points
PRE_FAULT = 10       # points before fault (normal baseline)
FAULT_WINDOW = 12    # points during fault (spike)
POST_FAULT = 8       # points after (recovery)

random.seed(42)


def gaussian_noise(val: float, pct: float = 0.05) -> float:
    """Add ±pct gaussian noise to a value."""
    noise = random.gauss(0, val * pct)
    return max(0.0, val + noise)


def exponential_decay(start: float, end: float, steps: int, k: float = 0.4) -> list[float]:
    """Smooth exponential decay from start to end over steps."""
    result = []
    for i in range(steps):
        t = i / max(steps - 1, 1)
        val = end + (start - end) * math.exp(-k * i)
        result.append(val)
    return result


def synthesize_timeseries(baseline: float, peak: float, duration_s: int) -> list[dict]:
    """Build a 30-point synthetic time series with realistic spike shape."""
    points = []

    # Pre-fault baseline (t = -10min to -1min)
    for i in range(PRE_FAULT):
        t = -(PRE_FAULT - i)
        points.append({"t": t, "v": round(gaussian_noise(baseline, 0.04), 2)})

    # Fault ramp-up (first 2 points)
    ramp = [(baseline + (peak - baseline) * (j + 1) / 3) for j in range(2)]
    for i, v in enumerate(ramp):
        points.append({"t": i, "v": round(gaussian_noise(v, 0.02), 2)})

    # Peak plateau
    plateau_len = FAULT_WINDOW - 2 - 2
    for i in range(plateau_len):
        points.append({"t": i + 2, "v": round(gaussian_noise(peak, 0.03), 2)})

    # Fault ramp-down (last 2 points of fault window)
    mid = (peak + baseline) / 2
    for i, v in enumerate([peak * 0.85, mid]):
        points.append({"t": FAULT_WINDOW - 2 + i, "v": round(gaussian_noise(v, 0.02), 2)})

    # Recovery (exponential decay back to baseline)
    decay_vals = exponential_decay(mid, baseline, POST_FAULT)
    for i, v in enumerate(decay_vals):
        points.append({"t": FAULT_WINDOW + i, "v": round(gaussian_noise(v, 0.04), 2)})

    assert len(points) == POINTS, f"Expected {POINTS} points, got {len(points)}"
    return points


def extract_aiopsarena_timeseries(inc: dict) -> list[dict] | None:
    """Try to extract real time-series values from AIOpsArena CSVs."""
    if not AIOPS_DIR.exists():
        return None

    service = inc.get("service", "")
    atype = inc.get("anomaly_type", "")
    target_metric = "cpu" if "cpu" in atype else "mem" if "mem" in atype else None
    if not target_metric:
        return None

    # Find relevant CSV
    candidates = []
    for csv_path in AIOPS_DIR.rglob("*.csv"):
        if target_metric in csv_path.stem.lower() or service.lower() in csv_path.stem.lower():
            candidates.append(csv_path)

    if not candidates:
        return None

    import csv as csv_mod
    csv_path = candidates[0]
    try:
        with csv_path.open(newline="", errors="replace") as fh:
            reader = csv_mod.DictReader(fh)
            rows = list(reader)
    except Exception:
        return None

    val_col = next((h for h in (rows[0].keys() if rows else [])
                   if any(k in h.lower() for k in ["value", "cpu", "mem", "usage"])), None)
    label_col = next((h for h in (rows[0].keys() if rows else [])
                     if any(k in h.lower() for k in ["fault", "label", "type", "anomaly"])), None)

    if not val_col or not rows:
        return None

    try:
        values = [float(r.get(val_col, 0) or 0) for r in rows]
    except Exception:
        return None

    if len(values) < POINTS:
        return None

    # Find fault window
    if label_col:
        fault_indices = [i for i, r in enumerate(rows)
                        if r.get(label_col, "normal").lower() not in ("normal", "0", "false", "")]
    else:
        baseline = sum(values[:20]) / 20
        fault_indices = [i for i, v in enumerate(values) if v > baseline * 1.5]

    if not fault_indices:
        return None

    fault_start = max(0, fault_indices[0] - PRE_FAULT)
    end = min(len(values), fault_start + POINTS)
    start = max(0, end - POINTS)
    window = values[start:end]

    if len(window) < POINTS:
        window += [values[-1]] * (POINTS - len(window))

    fault_offset = (fault_indices[0] - start) if fault_indices else PRE_FAULT
    return [{"t": i - fault_offset, "v": round(v, 2)} for i, v in enumerate(window)]


def main() -> None:
    print("=" * 60)
    print("STEP 4 — BUILDING METRIC TIME SERIES")
    print("=" * 60)

    if not INPUT_FILE.exists():
        print(f"✗ {INPUT_FILE} not found — run generate_fixes.py first", file=sys.stderr)
        sys.exit(1)

    incidents = json.loads(INPUT_FILE.read_text())
    print(f"  Processing {len(incidents)} incidents...")

    real_count = 0
    synth_count = 0

    for inc in incidents:
        ts = None

        # Try real CSV extraction for AIOpsArena
        if inc.get("source") == "aiopsarena":
            ts = extract_aiopsarena_timeseries(inc)
            if ts:
                real_count += 1

        # Synthesize if no real data available
        if ts is None:
            baseline = inc.get("metric_baseline") or 40.0
            peak = inc.get("metric_peak") or baseline * 2
            duration = inc.get("duration_seconds", 300)
            ts = synthesize_timeseries(float(baseline), float(peak), duration)
            synth_count += 1

        inc["timeseries"] = ts

    INPUT_FILE.write_text(json.dumps(incidents, indent=2))

    print(f"\n✓ Added timeseries to {len(incidents)} incidents → {INPUT_FILE}")
    print(f"  Real (from CSV): {real_count}")
    print(f"  Synthesized:     {synth_count}")
    print(f"\n  Sample (first 5 points of incident 0):")
    for pt in incidents[0]["timeseries"][:5]:
        print(f"    t={pt['t']:+3d}min  v={pt['v']:6.2f}%")


if __name__ == "__main__":
    main()
