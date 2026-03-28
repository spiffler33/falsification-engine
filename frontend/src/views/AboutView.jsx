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
            <strong>Theory parsing.</strong> The system runs on eight theory
            modules covering structural fragility, fiscal dominance, debt
            cycles, valuations, capital flows, and monetary architecture. Each
            one defines what activates it, what it predicts, and what would
            kill it — all explicit, all auditable. If you think something's
            missing, write a new module.
          </li>
          <li>
            <strong>Data briefing.</strong> FRED macro series and the full ETF
            universe from Yahoo Finance, organized the way a desk would want
            it: growth, inflation, rates, liquidity, credit, sentiment,
            computed cross-metrics, and price action across every asset class.
            Cached daily with staleness flags.
          </li>
        </ol>
      </section>

      <section className="about-view__section">
        <h2 className="about-view__section-label">Mechanical Passes — No LLM</h2>
        <ol className="about-view__list">
          <li>
            <strong>Activation scoring.</strong> Each theory's conditions
            checked against the briefing. Either the data supports the theory
            right now or it doesn't. Output: Active, Adjacent, or Inactive.
            Pure computation.
          </li>
        </ol>
      </section>

      <section className="about-view__section">
        <h2 className="about-view__section-label">LLM Passes — Generation and Attack</h2>
        <ol className="about-view__list">
          <li>
            <strong>Hypothesis generation.</strong> Active theories and the
            briefing fed to the model. It produces a handful of hypotheses per
            theory — mechanism, prediction, assets, timeframe. Redundancies
            killed. The model proposes. It never ranks.
          </li>
          <li>
            <strong>Adversarial elimination.</strong> Separate prompt, separate
            job: destroy. Every pre-registered falsifier checked against
            current data. Either the data contradicts the hypothesis, confirms
            it's safe, or can't be verified right now — and can't-verify is
            the default, not safe. The evaluator runs cross-theory attacks and
            grades evidence quality. It never assigns conviction.
          </li>
        </ol>
      </section>

      <section className="about-view__section">
        <h2 className="about-view__section-label">
          Conviction Scoring — No LLM
        </h2>
        <ol className="about-view__list">
          <li>
            <strong>Kill rules.</strong> If the data contradicts a core
            assumption, the hypothesis is dead. Stack enough warning signs and
            it's dead. No stories, no "but if you squint."
          </li>
          <li>
            <strong>Raw conviction.</strong> Scored on four things: how
            strongly the underlying theory activated, how much hard data backs
            the hypothesis, whether the predicted assets are actually moving
            the right way, and how many of the kill criteria are actually
            testable right now versus sitting in limbo.
          </li>
          <li>
            <strong>Discounts.</strong> Warning signs that aren't fatal still
            cost you — the more there are and the worse they are, the deeper
            the haircut. Not knowing isn't the same as being safe, so
            untestable conditions discount too. Same theory producing multiple
            hypotheses gets penalized for double-counting. Different theories
            pointing at the same trade gets a small convergence bonus.
          </li>
          <li>
            <strong>Gates.</strong> Two hard reality checks. Horizon: if the
            timeframe doesn't fit your holding period, conviction gets
            capped — being right on the wrong timeline is the same as being
            wrong. Expression: if you can't put it on cleanly through liquid
            ETFs, conviction gets capped. Below the floor after gates, it's
            killed.
          </li>
        </ol>
      </section>

      <section className="about-view__section">
        <h2 className="about-view__section-label">Audit Trail</h2>
        <ol className="about-view__list">
          <li>
            <strong>Every number is stored.</strong> Every intermediate score,
            every discount, every cap. Any conviction number can be
            reconstructed exactly from stored data.
          </li>
          <li>
            <strong>LLM vs. mechanical.</strong> The model's self-assessed
            scores are kept alongside the mechanical ones. The model always
            clusters everything together — barely differentiates. The
            mechanical pipeline spreads conviction several times wider. The
            model's numbers are kept for audit. They're never used.
          </li>
          <li>
            <strong>Decision surface.</strong> Survivors ranked by conviction.
            Every score, every falsifier, every discount visible and
            traceable. The system produces conviction. You decide what to do
            with it.
          </li>
        </ol>
      </section>
    </div>
  )
}
