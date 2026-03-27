# conviction.py — Pass 4: Three-stage mechanical conviction scoring pipeline.
# Depends on: schemas/scoring.py
# Depended on by: api/pipeline.py, api/hypotheses.py
#
# Pure math. No LLM. No narrative.
# Stage 1: Raw conviction from epistemic quality (weighted sum)
# Stage 2: Multiplicative discounts (soft falsifier health + overlap penalty)
# Stage 3: Hard caps (horizon alignment + expression efficiency gates)
from __future__ import annotations

from backend.schemas.scoring import (
    ConvictionInput,
    ConvictionMath,
    Stage1Raw,
    Stage2Discounts,
    Stage3Gates,
)

# Stage 1 weights from CLAUDE.md
WEIGHT_SUPPORT = 0.30
WEIGHT_QUALITY = 0.30
WEIGHT_CONVERGENCE = 0.25
WEIGHT_FALSIFIER_CLARITY = 0.15

# Stage 2 severity discount weights from interface contract
SEVERITY_WEIGHTS = {
    "minor": 0.10,
    "medium": 0.25,
    "major": 0.45,
}

# Stage 3 gate caps from CLAUDE.md
HORIZON_CAPS = [
    (0.10, 1),   # H < 0.10 → capped at 1/10
    (0.25, 2),   # H < 0.25 → capped at 2/10
    (0.40, 4),   # H < 0.40 → capped at 4/10
]

EXPRESSION_CAPS = [
    (0.15, 1),   # E < 0.15 → capped at 1/10
    (0.30, 3),   # E < 0.30 → capped at 3/10
]


def score_conviction(inp: ConvictionInput) -> ConvictionMath:
    """Run the full three-stage conviction scoring pipeline.

    Returns a ConvictionMath object with full transparency into each stage.
    """
    s1 = _stage1_raw(inp)
    s2 = _stage2_discounts(inp, s1.raw)
    s3 = _stage3_gates(inp, s2.adjusted)

    return ConvictionMath(stage1=s1, stage2=s2, stage3=s3)


def score_batch(inputs: list[ConvictionInput]) -> list[ConvictionMath]:
    """Score a batch of hypotheses. Overlap counts should be pre-computed."""
    return [score_conviction(inp) for inp in inputs]


# ---------------------------------------------------------------------------
# Stage 1: Raw conviction
# ---------------------------------------------------------------------------

def _stage1_raw(inp: ConvictionInput) -> Stage1Raw:
    """Compute raw conviction from epistemic quality dimensions.

    RAW = S(0.30) + Q(0.30) + C(0.25) + F(0.15)
    Range: 0.0 to 1.0, then scaled to 0-10.
    """
    raw_01 = (
        inp.support_strength * WEIGHT_SUPPORT
        + inp.evidence_quality * WEIGHT_QUALITY
        + inp.convergence * WEIGHT_CONVERGENCE
        + inp.falsifier_clarity * WEIGHT_FALSIFIER_CLARITY
    )
    # Clamp to [0, 1]
    raw_01 = max(0.0, min(1.0, raw_01))
    raw_10 = raw_01 * 10.0

    return Stage1Raw(
        support_strength=inp.support_strength,
        evidence_quality=inp.evidence_quality,
        convergence=inp.convergence,
        falsifier_clarity=inp.falsifier_clarity,
        raw=raw_10,
    )


# ---------------------------------------------------------------------------
# Stage 2: Discounts
# ---------------------------------------------------------------------------

def _stage2_discounts(inp: ConvictionInput, raw_score: float) -> Stage2Discounts:
    """Apply multiplicative discounts for soft falsifier health and overlap.

    D_f = max(0.05, 1 - sum(severity_weight_i))
    D_o = 1 / (1 + overlap_count * 0.25)
    DISCOUNTED = RAW * D_f * D_o
    """
    # Soft falsifier health discount
    total_severity = sum(
        SEVERITY_WEIGHTS.get(f.get("severity", "minor"), 0.10)
        for f in inp.triggered_soft_falsifiers
    )
    d_f = max(0.05, 1.0 - total_severity)

    # Exposure overlap penalty
    d_o = 1.0 / (1.0 + inp.overlap_count * 0.25)

    adjusted = raw_score * d_f * d_o

    return Stage2Discounts(
        soft_falsifier_discount=d_f,
        overlap_penalty=d_o,
        adjusted=adjusted,
    )


# ---------------------------------------------------------------------------
# Stage 3: Gates
# ---------------------------------------------------------------------------

def _stage3_gates(inp: ConvictionInput, adjusted_score: float) -> Stage3Gates:
    """Apply hard caps from horizon alignment and expression efficiency.

    FINAL = min(SCORE, horizon_cap, expression_cap)
    Round to nearest integer. Output: 0-10.
    """
    # Horizon cap
    horizon_cap = None
    for threshold, cap in HORIZON_CAPS:
        if inp.horizon_alignment < threshold:
            horizon_cap = cap
            break

    # Expression cap
    expression_cap = None
    for threshold, cap in EXPRESSION_CAPS:
        if inp.expression_efficiency < threshold:
            expression_cap = cap
            break

    # Apply caps
    final = adjusted_score
    if horizon_cap is not None:
        final = min(final, horizon_cap)
    if expression_cap is not None:
        final = min(final, expression_cap)

    # Round to nearest integer
    final = round(final)
    # Clamp to 0-10
    final = max(0, min(10, final))

    return Stage3Gates(
        horizon_score=inp.horizon_alignment,
        horizon_cap=horizon_cap,
        expression_score=inp.expression_efficiency,
        expression_cap=expression_cap,
        final=float(final),
    )
