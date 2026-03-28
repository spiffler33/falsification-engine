export default function AboutView() {
  return (
    <div className="about-view">
      <h1 className="about-view__title">What This System Does</h1>

      <ol className="about-view__list">
        <li>
          Parses 8 economic theory modules into structured activation
          conditions, predictions, and falsifier sets.
        </li>
        <li>
          Fetches 22+ macro data series (FRED, Yahoo Finance) and computes
          derived metrics (net liquidity, ERP, yield curves, relative performance).
        </li>
        <li>
          Scores theory activation mechanically: weighted indicator sum against
          current data, producing Active / Adjacent / Inactive per theory.
        </li>
        <li>
          Generates candidate hypotheses via LLM using only Active theory
          mechanisms and current data. Consolidates redundant hypotheses.
        </li>
        <li>
          Attacks each hypothesis via LLM falsifier audit: every pre-registered
          hard and soft falsifier checked against data. Status: CLEAR, TRIGGERED,
          or UNTESTABLE.
        </li>
        <li>
          Applies mechanical kill rules: hard falsifier trigger = killed,
          2+ major soft falsifiers = killed, 3+ any soft falsifiers = killed.
        </li>
        <li>
          Scores conviction mechanically (zero LLM): support strength from
          activation score, evidence quality from data coverage ratio, convergence
          from 30-day price alignment, falsifier clarity from verification ratio.
        </li>
        <li>
          Applies Stage 2 discounts: soft falsifier severity discount (multiplicative),
          UNTESTABLE uncertainty discount, theory-aware overlap penalty (same-theory
          penalized, cross-theory convergence bonused).
        </li>
        <li>
          Applies Stage 3 gates: horizon alignment from timeframe parsing,
          expression efficiency from ETF universe coverage and liquidity tier.
          Conviction floor at 5/10.
        </li>
        <li>
          Presents surviving hypotheses ranked by conviction with full audit trail:
          every score, every falsifier, every discount visible and traceable.
        </li>
      </ol>
    </div>
  )
}
