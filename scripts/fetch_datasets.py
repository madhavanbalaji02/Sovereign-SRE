"""
Step 1: Clone real AIOps datasets for Sovereign-SRE.

Downloads:
  - GAIA-DataSet (CloudWise-OpenSource): anomaly injection logs
  - AIOpsArena (MicroServo): CPU/memory CSVs with fault labels

Usage:
    python3 scripts/fetch_datasets.py
"""

import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
DATA_DIR = ROOT / "data"
DATA_DIR.mkdir(exist_ok=True)


def run(cmd: list[str], cwd: Path | None = None) -> int:
    print(f"  $ {' '.join(cmd)}")
    result = subprocess.run(cmd, cwd=cwd, capture_output=False)
    return result.returncode


def clone_or_skip(url: str, dest: Path, label: str) -> None:
    if dest.exists() and any(dest.iterdir()):
        print(f"  ✓ {label} already cloned → {dest}")
        return
    print(f"\n→ Cloning {label}...")
    code = run(["git", "clone", "--depth", "1", url, str(dest)])
    if code != 0:
        print(f"  ✗ Clone failed for {label}", file=sys.stderr)
        sys.exit(1)
    print(f"  ✓ {label} cloned → {dest}")


def list_files(path: Path, pattern: str = "*", depth: int = 3) -> list[Path]:
    results = []
    for p in sorted(path.rglob(pattern)):
        if p.is_file() and ".git" not in p.parts:
            rel = p.relative_to(path)
            if len(rel.parts) <= depth:
                results.append(p)
    return results


def main() -> None:
    print("=" * 60)
    print("STEP 1 — FETCHING REAL AIOPS DATASETS")
    print("=" * 60)

    # ── 1. GAIA Dataset ────────────────────────────────────────────
    gaia_dir = DATA_DIR / "gaia"
    clone_or_skip(
        "https://github.com/CloudWise-OpenSource/GAIA-DataSet",
        gaia_dir,
        "GAIA-DataSet",
    )

    print("\n── GAIA files (depth ≤ 3):")
    gaia_files = list_files(gaia_dir, "*", depth=3)
    for f in gaia_files[:30]:
        print(f"    {f.relative_to(DATA_DIR)}")
    if len(gaia_files) > 30:
        print(f"    ... and {len(gaia_files) - 30} more")

    # ── 2. AIOpsArena Dataset ──────────────────────────────────────
    aiops_dir = DATA_DIR / "aiopsarena"
    clone_or_skip(
        "https://github.com/MicroServo/dataset",
        aiops_dir,
        "AIOpsArena",
    )

    print("\n── AIOpsArena CSV files:")
    csv_files = list_files(aiops_dir, "*.csv", depth=5)
    for f in csv_files[:20]:
        print(f"    {f.relative_to(DATA_DIR)}")
    if len(csv_files) > 20:
        print(f"    ... and {len(csv_files) - 20} more CSVs")

    # ── Sample 5 rows from each ────────────────────────────────────
    print("\n── Sample: GAIA anomaly logs")
    log_files = [f for f in gaia_files if f.suffix in (".log", ".txt", "")]
    if not log_files:
        log_files = [f for f in gaia_files if f.is_file()]
    for lf in log_files[:3]:
        try:
            lines = lf.read_text(errors="replace").splitlines()
            anomaly_lines = [l for l in lines if "anomal" in l.lower() or "WARNING" in l or "inject" in l.lower()]
            sample = anomaly_lines[:5] if anomaly_lines else lines[:5]
            if sample:
                print(f"\n  [{lf.relative_to(DATA_DIR)}]")
                for line in sample:
                    print(f"    {line[:120]}")
        except Exception:
            pass

    print("\n── Sample: AIOpsArena CSVs")
    for cf in csv_files[:3]:
        try:
            lines = cf.read_text(errors="replace").splitlines()
            print(f"\n  [{cf.relative_to(DATA_DIR)}]")
            for line in lines[:6]:
                print(f"    {line[:120]}")
        except Exception:
            pass

    print("\n✓ Datasets ready in data/")


if __name__ == "__main__":
    main()
