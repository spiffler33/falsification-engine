#!/usr/bin/env python
"""regression_check.py -- Canonical post-v8 regression entrypoint.

Runs the semantic regression surface in two explicit stages:

  Stage 1: Correctness harness  (test_activation_correctness.py)
           Frozen expected-output gate for all 8 theories against the
           Task 0 briefing packet. Catches any semantic drift in field
           resolution, threshold parsing, trigger states, or scoring.

  Stage 2: Broader backend suite  (backend/tests/)
           Full pytest run covering parser, activation, lifecycle,
           prompt builder, pipeline, and all other backend tests.

Usage:
    python -m scripts.regression_check

Exit codes:
    0  -- all stages passed
    1  -- one or more stages failed

Offline and deterministic. Does not fetch live data, regenerate fixtures,
or mutate frozen artifacts.
"""
from __future__ import annotations

import subprocess
import sys
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent

# -----------------------------------------------------------------------
# Stage definitions
# -----------------------------------------------------------------------

STAGES: list[dict] = [
    {
        "name": "Correctness harness",
        "description": "Frozen expected-output gate (all 8 theories)",
        "cmd": [
            sys.executable, "-m", "pytest",
            "backend/tests/test_activation_correctness.py",
            "-v", "--tb=short", "--no-header",
        ],
    },
    {
        "name": "Broader backend suite",
        "description": "Full backend test suite",
        "cmd": [
            sys.executable, "-m", "pytest",
            "backend/tests/",
            "-v", "--tb=short", "--no-header",
        ],
    },
]

# -----------------------------------------------------------------------
# Runner
# -----------------------------------------------------------------------

DIVIDER = "-" * 60


def run_stage(index: int, stage: dict) -> bool:
    """Run a single stage. Returns True on success, False on failure."""
    label = f"Stage {index + 1}: {stage['name']}"
    print(f"\n{DIVIDER}")
    print(f"  {label}")
    print(f"  {stage['description']}")
    print(DIVIDER)

    t0 = time.monotonic()
    result = subprocess.run(
        stage["cmd"],
        cwd=PROJECT_ROOT,
    )
    elapsed = time.monotonic() - t0

    passed = result.returncode == 0
    status = "PASS" if passed else "FAIL"
    print(f"\n  {label} ... {status}  ({elapsed:.1f}s)")
    return passed


def main() -> int:
    print("=" * 60)
    print("  REGRESSION CHECK")
    print(f"  Stages: {len(STAGES)}")
    print("=" * 60)

    results: list[tuple[str, bool]] = []
    any_failed = False

    for i, stage in enumerate(STAGES):
        passed = run_stage(i, stage)
        results.append((stage["name"], passed))
        if not passed:
            any_failed = True

    # Summary
    print(f"\n{'=' * 60}")
    print("  RESULTS")
    print("=" * 60)
    for i, (name, passed) in enumerate(results):
        status = "PASS" if passed else "FAIL"
        print(f"  Stage {i + 1}: {name} ... {status}")

    print(DIVIDER)
    if any_failed:
        print("  REGRESSION CHECK FAILED")
    else:
        print("  REGRESSION CHECK PASSED")
    print("=" * 60)

    return 1 if any_failed else 0


if __name__ == "__main__":
    sys.exit(main())
