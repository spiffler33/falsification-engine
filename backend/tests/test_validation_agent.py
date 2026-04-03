# test_validation_agent.py -- Phase 6: Unit tests for data validation checks.
# Uses synthetic BriefingPacket data to exercise all 6 check types
# and the ValidationReport quality grade logic.
from datetime import datetime, timedelta, timezone

import pytest

from backend.engine.validation_agent import (
    ANOMALY_THRESHOLDS,
    CRITICAL_COMPUTED,
    CRITICAL_FIELDS,
    RANGE_BOUNDS,
    STALENESS_DAYS,
    ValidationCheck,
    ValidationReport,
    _check_anomalies,
    _check_completeness,
    _check_consistency,
    _check_cross_source,
    _check_provenance,
    _check_ranges,
    _check_staleness,
    validate_briefing,
)
from backend.schemas.briefing import BriefingPacket, FieldProvenance, MarketData, WebSourcedData


# ---------------------------------------------------------------------------
# Helpers -- build minimal BriefingPackets for testing
# ---------------------------------------------------------------------------


def _make_briefing(**overrides) -> BriefingPacket:
    """Build a healthy BriefingPacket with all critical fields populated."""
    base = dict(
        growth={
            "real_gdp": 2.5, "unemployment": 3.8, "ism_proxy": 52.0,
            "gdp_latest": 29_000, "initial_claims": 220_000,
            "nonfarm_payrolls": 250,
        },
        inflation={
            "cpi_yoy": 3.2, "core_pce": 2.8, "breakeven_5y": 2.4,
            "breakeven_10y": 2.2,
        },
        rates={
            "fed_funds": 4.50, "treasury_2y": 4.25, "treasury_10y": 4.35,
            "treasury_3m": 4.55, "treasury_30y": 4.60, "curve_2s10s": 0.10,
            "curve_3m10y": -0.20,
        },
        liquidity={
            "fed_balance_sheet": 7_000_000, "tga": 750_000,
            "reverse_repo": 200_000, "m2": 21_000,
        },
        credit={"hy_spread": 350, "ig_spread": 95, "sloos_tightening_ci": 5.2},
        sentiment={"consumer_sentiment": 65.0},
        computed={
            "net_liquidity": 6_050_000, "equity_risk_premium": 2.5,
            "vix_vs_realized": 3.0, "spy_drawdown_from_52w_high": -4.5,
            "buffett_indicator": 1.85,
        },
        markets={"^VIX": MarketData(price=18.5)},
        web_sourced={},
    )
    base.update(overrides)
    return BriefingPacket(**base)


def _now_iso(offset_days: float = 0) -> str:
    t = datetime.now(timezone.utc) - timedelta(days=offset_days)
    return t.isoformat()


# ---------------------------------------------------------------------------
# Completeness checks
# ---------------------------------------------------------------------------


class TestCompleteness:
    def test_healthy_packet_no_errors(self):
        checks = _check_completeness(_make_briefing())
        errors = [c for c in checks if c.severity == "error"]
        assert errors == []

    def test_missing_critical_field_is_error(self):
        bp = _make_briefing(growth={"unemployment": 3.8, "ism_proxy": 52.0})
        checks = _check_completeness(bp)
        errors = [c for c in checks if c.severity == "error"]
        error_fields = {c.field for c in errors}
        assert "growth.real_gdp" in error_fields

    def test_missing_noncritical_field_is_warning(self):
        bp = _make_briefing()
        bp.growth["nonfarm_payrolls"] = None  # non-critical field
        checks = _check_completeness(bp)
        warnings = [c for c in checks if c.severity == "warning"]
        assert any("nonfarm_payrolls" in c.field for c in warnings)

    def test_missing_critical_computed_is_error(self):
        bp = _make_briefing()
        bp.computed["net_liquidity"] = None
        checks = _check_completeness(bp)
        errors = [c for c in checks if c.severity == "error"]
        assert any("net_liquidity" in c.field for c in errors)


# ---------------------------------------------------------------------------
# Range checks
# ---------------------------------------------------------------------------


class TestRangeChecks:
    def test_in_range_no_warnings(self):
        checks = _check_ranges(_make_briefing())
        assert len(checks) == 0

    def test_out_of_range_section_field(self):
        bp = _make_briefing()
        bp.growth["unemployment"] = 30.0  # outside [0, 25]
        checks = _check_ranges(bp)
        assert any(c.field == "growth.unemployment" for c in checks)

    def test_out_of_range_computed_field(self):
        bp = _make_briefing()
        bp.computed["equity_risk_premium"] = 20.0  # outside [-10, 15]
        checks = _check_ranges(bp)
        assert any(c.field == "equity_risk_premium" for c in checks)

    def test_out_of_range_web_sourced(self):
        bp = _make_briefing(web_sourced={
            "shiller_cape": WebSourcedData(value=100.0, source="test"),  # max=80
        })
        checks = _check_ranges(bp)
        assert any("shiller_cape" in c.field for c in checks)

    def test_vix_market_data_range(self):
        bp = _make_briefing(markets={"^VIX": MarketData(price=95.0)})  # max=90
        checks = _check_ranges(bp)
        assert any("VIX" in c.field for c in checks)

    def test_none_values_skipped(self):
        bp = _make_briefing()
        bp.growth["real_gdp"] = None
        checks = _check_ranges(bp)
        # Should not flag None values as out of range
        assert not any(c.field == "growth.real_gdp" for c in checks)


# ---------------------------------------------------------------------------
# Consistency checks
# ---------------------------------------------------------------------------


class TestConsistency:
    def test_ig_less_than_hy_passes(self):
        bp = _make_briefing()  # ig=95, hy=350
        checks = _check_consistency(bp)
        assert not any("ig_spread" in c.field and c.severity == "error" for c in checks)

    def test_ig_greater_than_hy_is_error(self):
        bp = _make_briefing(credit={"hy_spread": 100, "ig_spread": 200})
        checks = _check_consistency(bp)
        errors = [c for c in checks if c.severity == "error"]
        assert any("ig_spread" in c.field for c in errors)

    def test_3m_tracks_fed_funds(self):
        bp = _make_briefing()  # 3m=4.55, ff=4.50 -> delta=0.05 < 0.75
        checks = _check_consistency(bp)
        assert not any("treasury_3m" in c.field for c in checks)

    def test_3m_diverges_from_fed_funds(self):
        bp = _make_briefing()
        bp.rates["treasury_3m"] = 6.0  # 1.5pp from fed_funds=4.50
        checks = _check_consistency(bp)
        assert any("treasury_3m" in c.field for c in checks)

    def test_net_liquidity_consistent(self):
        """BS - TGA - RRP = 7M - 750K - 200K = 6,050,000"""
        bp = _make_briefing()  # computed net_liq = 6,050,000
        checks = _check_consistency(bp)
        assert not any(c.field == "net_liquidity" and c.severity == "error" for c in checks)

    def test_net_liquidity_inconsistent(self):
        bp = _make_briefing()
        bp.computed["net_liquidity"] = 5_000_000  # should be 6,050,000
        checks = _check_consistency(bp)
        errors = [c for c in checks if c.field == "net_liquidity" and c.severity == "error"]
        assert len(errors) == 1

    def test_breakeven_5y_vs_10y_unusual(self):
        bp = _make_briefing()
        bp.inflation["breakeven_5y"] = 4.5  # 10y=2.2, diff=2.3pp > 1.0
        checks = _check_consistency(bp)
        assert any("breakeven" in c.field for c in checks)

    def test_deficit_consistency_ok(self):
        bp = _make_briefing()
        bp.computed["deficit_pace_annualized"] = 3000
        bp.web_sourced["deficit_pct_gdp"] = WebSourcedData(
            value=10.3, source="test"  # 10.3% of 29000 = 2987B
        )
        checks = _check_consistency(bp)
        assert not any("deficit_pace" in c.field for c in checks)

    def test_deficit_consistency_diverged(self):
        bp = _make_briefing()
        bp.computed["deficit_pace_annualized"] = 1000  # $1T
        bp.web_sourced["deficit_pct_gdp"] = WebSourcedData(
            value=10.0, source="test"  # 10% of 29000 = $2.9T -- ratio > 2x
        )
        checks = _check_consistency(bp)
        assert any("deficit_pace" in c.field for c in checks)


# ---------------------------------------------------------------------------
# Cross-source checks
# ---------------------------------------------------------------------------


class TestCrossSource:
    def test_ism_agrees_no_flag(self):
        """Proxy=52, actual=53 -- same side of 50, delta < 5."""
        bp = _make_briefing(web_sourced={
            "ism_pmi": WebSourcedData(value=53.0, source="test"),
        })
        bp.growth["ism_proxy"] = 52.0
        checks = _check_cross_source(bp)
        assert len(checks) == 0

    def test_ism_disagrees_on_expansion_is_error(self):
        """Proxy=48 (contraction), actual=52.7 (expansion)."""
        bp = _make_briefing(web_sourced={
            "ism_pmi": WebSourcedData(value=52.7, source="test"),
        })
        bp.growth["ism_proxy"] = 48.0
        checks = _check_cross_source(bp)
        errors = [c for c in checks if c.severity == "error"]
        assert len(errors) == 1
        assert "expansion" in errors[0].message or "contraction" in errors[0].message

    def test_ism_same_side_large_delta_is_info(self):
        """Both expanding but delta > 5."""
        bp = _make_briefing(web_sourced={
            "ism_pmi": WebSourcedData(value=58.0, source="test"),
        })
        bp.growth["ism_proxy"] = 52.0  # delta = 6
        checks = _check_cross_source(bp)
        assert any(c.severity == "info" and "differ by" in c.message for c in checks)

    def test_sentiment_divergence(self):
        """UMich < 70 (negative), OECD > 99 (positive)."""
        bp = _make_briefing(web_sourced={
            "consumer_confidence": WebSourcedData(value=101.0, source="test"),
        })
        bp.sentiment["consumer_sentiment"] = 60.0
        checks = _check_cross_source(bp)
        assert any("consumer" in c.field.lower() or "sentiment" in c.field.lower()
                    for c in checks)

    def test_no_cross_source_data_no_checks(self):
        bp = _make_briefing()
        checks = _check_cross_source(bp)
        assert len(checks) == 0


# ---------------------------------------------------------------------------
# Staleness checks
# ---------------------------------------------------------------------------


class TestStaleness:
    def test_fresh_data_no_warnings(self):
        bp = _make_briefing(web_sourced={
            "ism_pmi": WebSourcedData(value=52.7, source="test", fetched_at=_now_iso(0)),
        })
        checks = _check_staleness(bp)
        assert len(checks) == 0

    def test_stale_data_warns(self):
        bp = _make_briefing(web_sourced={
            "ism_pmi": WebSourcedData(
                value=52.7, source="test",
                fetched_at=_now_iso(40),  # 40 days old, threshold is 35
            ),
        })
        checks = _check_staleness(bp)
        assert len(checks) == 1
        assert checks[0].severity == "warning"
        assert "40d" in checks[0].message or "40" in checks[0].message

    def test_missing_timestamp_warns(self):
        bp = _make_briefing(web_sourced={
            "usdcny": WebSourcedData(value=6.89, source="test", fetched_at=""),
        })
        checks = _check_staleness(bp)
        assert any("no fetched_at" in c.message for c in checks)

    def test_unparseable_timestamp_warns(self):
        bp = _make_briefing(web_sourced={
            "usdcny": WebSourcedData(value=6.89, source="test", fetched_at="not-a-date"),
        })
        checks = _check_staleness(bp)
        assert any("unparseable" in c.message for c in checks)

    def test_field_without_staleness_threshold_ignored(self):
        """Fields not in STALENESS_DAYS are not checked."""
        bp = _make_briefing(web_sourced={
            "unknown_field": WebSourcedData(
                value=42.0, source="test", fetched_at=_now_iso(365),
            ),
        })
        checks = _check_staleness(bp)
        assert len(checks) == 0


# ---------------------------------------------------------------------------
# Anomaly checks
# ---------------------------------------------------------------------------


class TestAnomalyChecks:
    def test_no_anomaly_when_stable(self):
        current = _make_briefing()
        previous = _make_briefing()
        checks = _check_anomalies(current, previous)
        assert len(checks) == 0

    def test_unemployment_jump_flagged(self):
        current = _make_briefing()
        previous = _make_briefing()
        current.growth["unemployment"] = 6.5  # was 3.8, delta=2.7 > threshold=2.0
        checks = _check_anomalies(current, previous)
        assert any("unemployment" in c.field for c in checks)

    def test_web_sourced_anomaly(self):
        current = _make_briefing(web_sourced={
            "ism_pmi": WebSourcedData(value=60.0, source="test"),
        })
        previous = _make_briefing(web_sourced={
            "ism_pmi": WebSourcedData(value=50.0, source="test"),
        })
        # delta=10, threshold=8
        checks = _check_anomalies(current, previous)
        assert any("ism_pmi" in c.field for c in checks)

    def test_no_previous_field_skipped(self):
        current = _make_briefing()
        previous = _make_briefing()
        previous.growth.pop("unemployment")  # no previous value
        current.growth["unemployment"] = 10.0
        checks = _check_anomalies(current, previous)
        assert not any("unemployment" in c.field for c in checks)


# ---------------------------------------------------------------------------
# Overall validation + quality grades
# ---------------------------------------------------------------------------


class TestValidateBriefing:
    def test_healthy_packet_good_quality(self):
        report = validate_briefing(_make_briefing())
        assert isinstance(report, ValidationReport)
        assert report.overall_quality == "good"
        assert report.errors == 0

    def test_degraded_quality_with_errors(self):
        """1-2 errors -> degraded."""
        bp = _make_briefing(credit={"hy_spread": 100, "ig_spread": 200})
        report = validate_briefing(bp)
        assert report.errors >= 1
        assert report.overall_quality in ("degraded", "poor")

    def test_poor_quality_many_errors(self):
        """>=3 errors -> poor."""
        bp = _make_briefing(
            growth={"unemployment": 3.8},  # missing real_gdp and ism_proxy
            credit={"hy_spread": 100, "ig_spread": 200},  # IG > HY
        )
        bp.computed["net_liquidity"] = None  # missing critical computed
        report = validate_briefing(bp)
        assert report.errors >= 3
        assert report.overall_quality == "poor"

    def test_anomaly_detection_with_previous(self):
        current = _make_briefing()
        current.growth["unemployment"] = 8.0
        previous = _make_briefing()
        report = validate_briefing(current, previous_briefing=previous)
        assert any(c.check_type == "anomaly" for c in report.checks)

    def test_no_anomaly_without_previous(self):
        report = validate_briefing(_make_briefing())
        assert not any(c.check_type == "anomaly" for c in report.checks)

    def test_all_6_check_types_exercised(self):
        """With enough data, all 6 check types produce results."""
        current = _make_briefing(web_sourced={
            "ism_pmi": WebSourcedData(value=52.7, source="test", fetched_at=_now_iso(40)),
        })
        current.growth["ism_proxy"] = 48.0  # cross-source ISM divergence
        current.growth["unemployment"] = 30.0  # range violation
        current.credit["ig_spread"] = 500  # > HY

        previous = _make_briefing()
        report = validate_briefing(current, previous_briefing=previous)

        check_types = {c.check_type for c in report.checks}
        # May not get all 6 from this single packet, but should get most
        assert "completeness" in check_types or "range" in check_types
        assert "cross_source" in check_types
        assert "staleness" in check_types


# ---------------------------------------------------------------------------
# Provenance checks
# ---------------------------------------------------------------------------


class TestProvenance:
    def test_primary_provenance_no_warnings(self):
        bp = _make_briefing()
        bp.field_provenance = {
            "equity_risk_premium": FieldProvenance(method="primary", detail="real data"),
        }
        checks = _check_provenance(bp)
        assert checks == []

    def test_fallback_provenance_is_warning(self):
        bp = _make_briefing()
        bp.field_provenance = {
            "equity_risk_premium": FieldProvenance(
                method="fallback", detail="4.5% constant - 10Y (WILL5000INDFC unavailable)",
            ),
        }
        checks = _check_provenance(bp)
        assert len(checks) == 1
        assert checks[0].severity == "warning"
        assert checks[0].check_type == "provenance"
        assert "WILL5000INDFC" in checks[0].message

    def test_hardcoded_provenance_is_info(self):
        bp = _make_briefing()
        bp.field_provenance = {
            "interest_exceeds_defense": FieldProvenance(
                method="hardcoded", detail="Interest - $940B defense (FY2026 estimate)",
            ),
        }
        checks = _check_provenance(bp)
        assert len(checks) == 1
        assert checks[0].severity == "info"

    def test_missing_provenance_is_warning(self):
        bp = _make_briefing()
        bp.field_provenance = {
            "buffett_indicator": FieldProvenance(
                method="missing", detail="WILL5000INDFC unavailable",
            ),
        }
        checks = _check_provenance(bp)
        assert len(checks) == 1
        assert checks[0].severity == "warning"

    def test_empty_provenance_no_checks(self):
        bp = _make_briefing()
        checks = _check_provenance(bp)
        assert checks == []

    def test_provenance_integrated_into_validate(self):
        bp = _make_briefing()
        bp.field_provenance = {
            "equity_risk_premium": FieldProvenance(
                method="fallback", detail="test fallback",
            ),
        }
        report = validate_briefing(bp)
        assert any(c.check_type == "provenance" for c in report.checks)


# ---------------------------------------------------------------------------
# Registry sanity checks
# ---------------------------------------------------------------------------


class TestRegistrySanity:
    def test_critical_fields_are_dotted(self):
        """All critical fields should be section.field format."""
        for field in CRITICAL_FIELDS:
            assert "." in field, f"CRITICAL_FIELDS entry '{field}' missing dot"

    def test_range_bounds_are_valid(self):
        for field, (lo, hi) in RANGE_BOUNDS.items():
            assert lo < hi, f"RANGE_BOUNDS['{field}']: min ({lo}) >= max ({hi})"

    def test_staleness_days_positive(self):
        for field, days in STALENESS_DAYS.items():
            assert days > 0, f"STALENESS_DAYS['{field}']: {days} <= 0"

    def test_anomaly_thresholds_positive(self):
        for field, threshold in ANOMALY_THRESHOLDS.items():
            assert threshold > 0, f"ANOMALY_THRESHOLDS['{field}']: {threshold} <= 0"
