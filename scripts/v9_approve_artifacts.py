#!/usr/bin/env python
"""v9 Phase 3: Approve compiled artifacts for scalar-evaluable theories.

Promotes artifact_status from DRAFT to APPROVED for theories where the
Phase 2 semantic diff shows zero unexplained mismatches and all evaluable
indicators either match or are justified improvements.

Approved theories:
  - valuation_mean_reversion
  - fiscal_dominance_arithmetic
  - debt_cycle_long

Each artifact gets:
  - artifact_status = "approved"
  - approval_timestamp (ISO 8601)
  - approval_justification (references semantic diff classification)
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

ARTIFACTS_DIR = Path(__file__).resolve().parent.parent / "artifacts" / "v9"

APPROVALS: dict[str, str] = {
    "valuation_mean_reversion": (
        "Phase 2 semantic diff: 2 expected_parity matches, 1 justified_improvement "
        "(profit_margins OR condition), 4 data_infra_limitation (time-series/missing). "
        "Zero unexplained mismatches, zero compiler issues. Tier: active/active MATCH. "
        "See V9_PHASE2_SEMANTIC_DIFF.md."
    ),
    "debt_cycle_long": (
        "Phase 2 semantic diff: 3 expected_parity matches, 1 justified_improvement "
        "(wealth_inequality correct 70% threshold), 1 coincidental_parity "
        "(fiscal_deficit_primary_driver — compiled fixes wrong-field resolution), "
        "1 data_infra_limitation. Zero unexplained mismatches, zero compiler issues. "
        "Tier: active/active MATCH. See V9_PHASE2_SEMANTIC_DIFF.md."
    ),
    "fiscal_dominance_arithmetic": (
        "Phase 2 semantic diff: 2 expected_parity matches, 4 data_infra_limitation "
        "(time-series/missing). Score parity at 1.000. Zero mismatches, zero "
        "coincidental parity, zero compiler issues. Tier: active/active MATCH. "
        "See V9_PHASE2_SEMANTIC_DIFF.md."
    ),
}


def approve_artifacts() -> None:
    ts = datetime.now(timezone.utc).isoformat()

    for theory_id, justification in APPROVALS.items():
        path = ARTIFACTS_DIR / f"{theory_id}.compiled.json"
        data = json.loads(path.read_text())

        old_status = data["artifact_status"]
        data["artifact_status"] = "approved"
        data["approval_timestamp"] = ts
        data["approval_justification"] = justification

        path.write_text(json.dumps(data, indent=2))
        print(f"  {theory_id}: {old_status} -> approved")

    print(f"\nApproval timestamp: {ts}")
    print(f"Artifacts approved: {len(APPROVALS)}")


if __name__ == "__main__":
    approve_artifacts()
