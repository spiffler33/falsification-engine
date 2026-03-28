export default function AboutView() {
  return (
    <div className="about-view">
      <h1 className="about-view__title">How the Pipeline Works</h1>

      <p className="about-view__premise">
        LLMs are distributional reasoners trained on symmetric loss. They spread
        probability mass across plausible continuations — useful for hypothesis
        generation, structurally unsuited to conviction formation. This system
        uses LLMs where they are strong (generation, adversarial attack) and
        replaces them with mechanical computation where they are weak (scoring,
        conviction, risk assessment). The model is a falsification engine, not
        an oracle.
      </p>

      <section className="about-view__section">
        <h2 className="about-view__section-label">Data Layer</h2>
        <ol className="about-view__list">
          <li>
            <strong>Theory parsing.</strong> 8 economic theory modules parsed
            into structured activation conditions (indicator, threshold, weight,
            direction), predictions, and pre-registered falsifier sets with
            severity. Two-phase theories scored per-phase with resolving phase
            checked first.
          </li>
          <li>
            <strong>Data briefing.</strong> 22+ macro series from FRED and Yahoo
            Finance assembled into a structured packet: growth, inflation, rates,
            liquidity, credit, sentiment, computed metrics, and full ETF universe
            market data. 24-hour cache with staleness tracking.
          </li>
        </ol>
      </section>

      <section className="about-view__section">
        <h2 className="about-view__section-label">Mechanical Passes — Zero LLM</h2>
        <ol className="about-view__list">
          <li>
            <strong>Activation scoring.</strong> Each theory's indicators checked
            against the briefing packet. Weighted sum of triggered indicators
            normalized by total mechanical weight. Output: Active (&ge;0.60) /
            Adjacent (0.30-0.59) / Inactive (&lt;0.30). Pure Python, no model
            calls.
          </li>
        </ol>
      </section>

      <section className="about-view__section">
        <h2 className="about-view__section-label">LLM Passes — Generation and Attack</h2>
        <ol className="about-view__list">
          <li>
            <strong>Hypothesis generation.</strong> Active theories + data
            briefing fed to Claude via copy-paste. Produces 2-4 hypotheses per
            Active theory with causal mechanism, testable prediction, assets,
            and timeframe. Consolidation check kills redundant hypotheses. The
            generator does not rank or recommend.
          </li>
          <li>
            <strong>Adversarial elimination.</strong> Separate prompt, separate
            instructions. Every pre-registered hard and soft falsifier checked
            against current data. Each falsifier classified TRIGGERED (data
            contradicts), CLEAR (data confirms safe, must cite evidence), or
            UNTESTABLE (cannot verify mechanically — the default, not CLEAR).
            Cross-theory attacks and evidence quality grading. The evaluator does
            not assign conviction.
          </li>
        </ol>
      </section>

      <section className="about-view__section">
        <h2 className="about-view__section-label">
          Conviction Scoring — Three Stages, Zero LLM
        </h2>
        <ol className="about-view__list">
          <li>
            <strong>Mechanical kill rules.</strong> Hard falsifier TRIGGERED =
            killed. 2+ major soft falsifiers = killed. 3+ any soft falsifiers =
            killed. No narrative, no judgment calls.
          </li>
          <li>
            <strong>Stage 1: Raw conviction.</strong> Four dimensions, weighted
            sum scaled to 0-10. Support strength (0.30) from theory activation
            score. Evidence quality (0.30) from mechanical data coverage ratio —
            indicators with data divided by mechanical indicators only; skipped
            qualitative/web-search indicators excluded from the denominator.
            Convergence (0.25) from fraction of predicted assets aligned with
            30-day price action. Falsifier clarity (0.15) from the share of
            falsifiers that are verifiable (CLEAR or TRIGGERED vs UNTESTABLE).
          </li>
          <li>
            <strong>Stage 2: Discounts.</strong> Soft falsifier severity discount
            — multiplicative compounding per triggered falsifier (minor 0.10,
            medium 0.25, major 0.45). UNTESTABLE uncertainty discount —
            multiplicative compounding at reduced weights (minor 0.05, medium
            0.10, major 0.15) because absence of data is not absence of risk.
            Theory-aware overlap: same-theory redundancy penalized (-0.50),
            cross-theory convergence bonused (+0.10, cap +0.20).
          </li>
          <li>
            <strong>Stage 3: Gates.</strong> Horizon alignment scored from
            timeframe parsing against 30-90 day ideal window — hard caps at 1,
            2, or 4/10 for misaligned horizons. Expression efficiency scored
            from ETF universe coverage, liquidity tier, and instrument
            directness — hard caps at 1 or 3/10 for poorly expressible
            hypotheses. Conviction floor: below 5/10 = killed.
          </li>
        </ol>
      </section>

      <section className="about-view__section">
        <h2 className="about-view__section-label">Audit Trail</h2>
        <ol className="about-view__list">
          <li>
            <strong>Lossless conviction math.</strong> Every intermediate value
            stored with each hypothesis: Stage 1 dimension scores and weights,
            Stage 2 discount factors with the input lists that produced them
            (triggered falsifier severities, UNTESTABLE falsifier severities,
            overlap counts by type), Stage 3 gate scores and caps applied.
            Conviction scores can be reconstructed exactly from stored JSON —
            zero discrepancy verified across all hypotheses.
          </li>
          <li>
            <strong>LLM audit comparison.</strong> The LLM's self-assessed
            conviction inputs are preserved alongside the mechanical values.
            Typical divergence: LLM clusters all inputs at 0.78-0.93 (0.50
            spread); mechanical scores spread 5.42-7.69 (2.27 spread, 4.5x
            wider differentiation). The LLM's numbers are kept for audit, never
            used for scoring.
          </li>
          <li>
            <strong>Decision surface.</strong> Surviving hypotheses presented
            ranked by conviction with every score, every falsifier status, every
            discount visible and traceable. The system takes positions through
            conviction scores. The human decides what to do.
          </li>
        </ol>
      </section>
    </div>
  )
}
