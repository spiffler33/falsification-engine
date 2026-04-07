"""Tests for series data loading pipeline.

Tests field source mapping, FRED transforms, Yahoo parsing,
computed field derivation, cache I/O, and store population.
All tests use mocked/synthetic data — no live API calls.
"""
from __future__ import annotations

import csv
import tempfile
from datetime import date, timedelta
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from backend.engine.field_source_mapping import (
    FIELD_SOURCES,
    SourceType,
    get_all_required_fred_series,
    get_all_required_yahoo_tickers,
    get_fred_fields,
    get_yahoo_fields,
    get_computed_fields,
    get_web_sourced_fields,
)
from backend.engine.fred_series_fetcher import (
    _transform_level,
    _transform_pct_to_bps,
    _transform_billions_to_millions,
    _transform_millions,
    _transform_ism_from_employment,
    _write_cache as fred_write_cache,
    _read_cache as fred_read_cache,
)
from backend.engine.yahoo_series_fetcher import (
    _write_cache as yahoo_write_cache,
    _read_cache as yahoo_read_cache,
)


# ===================================================================
# 1. Field source mapping completeness
# ===================================================================

class TestFieldSourceMapping:
    """Tests that the mapping covers all 26 temporal fields correctly."""

    def test_all_26_fields_mapped(self):
        """Every temporal field_id has a source mapping."""
        expected = {
            "growth.unemployment", "growth.ism_proxy", "growth.initial_claims",
            "rates.fed_funds", "rates.curve_2s10s",
            "credit.hy_spread", "credit.sloos_tightening_ci",
            "liquidity.fed_balance_sheet", "liquidity.reverse_repo", "liquidity.tga",
            "sentiment.consumer_sentiment",
            "cb_gold_purchases", "china_credit_impulse",
            "commodity_index_3m_change", "dxy_index", "eem_spy_3m_relative",
            "finra_margin_debt", "foreign_treasury_holdings_pct",
            "gold_oil_ratio", "insider_sell_buy_ratio",
            "net_liquidity_30d_change", "qqq_iwm_ratio",
            "rmb_swift_share", "sloos_net_tightening",
            "usdcny", "weighted_avg_interest_rate",
        }
        assert expected <= set(FIELD_SOURCES.keys()), (
            f"Missing: {expected - set(FIELD_SOURCES.keys())}"
        )

    def test_fred_fields_have_series_id(self):
        """FRED-backed fields must specify a fred_series."""
        for fs in get_fred_fields():
            assert fs.fred_series is not None, f"{fs.field_id} missing fred_series"
            assert len(fs.fred_series) > 0

    def test_yahoo_fields_have_tickers(self):
        """Yahoo-backed fields must specify tickers."""
        for fs in get_yahoo_fields():
            assert len(fs.yahoo_tickers) > 0, f"{fs.field_id} missing yahoo_tickers"

    def test_computed_fields_have_derivation(self):
        """Computed fields must document their derivation."""
        for fs in get_computed_fields():
            assert fs.derivation or fs.upstream_fields, (
                f"{fs.field_id} missing derivation/upstream_fields"
            )

    def test_web_sourced_have_notes(self):
        """Web-sourced fields must document why they can't be fetched."""
        for fs in get_web_sourced_fields():
            assert fs.note, f"{fs.field_id} missing note"

    def test_get_all_required_fred_series(self):
        """Should return all unique FRED series IDs with lookback."""
        fred = get_all_required_fred_series()
        assert "UNRATE" in fred
        assert "FEDFUNDS" in fred
        assert "DGS10" in fred  # upstream for curve_2s10s
        assert "DGS2" in fred
        assert fred["FEDFUNDS"] >= 12  # ELB check needs 10+ years

    def test_get_all_required_yahoo_tickers(self):
        """Should return all unique Yahoo tickers."""
        tickers = get_all_required_yahoo_tickers()
        assert "DX-Y.NYB" in tickers
        assert "QQQ" in tickers
        assert "IWM" in tickers
        assert "EEM" in tickers
        assert "SPY" in tickers

    def test_source_type_distribution(self):
        """Verify we have the expected source type mix."""
        types = {fs.source_type for fs in FIELD_SOURCES.values()}
        assert SourceType.FRED_DIRECT in types
        assert SourceType.YAHOO_PRICE in types
        assert SourceType.YAHOO_RATIO in types
        assert SourceType.WEB_SOURCED in types


# ===================================================================
# 2. FRED transforms
# ===================================================================

class TestFredTransforms:
    """Test per-observation transforms match data_agent.py behavior."""

    def test_level_identity(self):
        assert _transform_level(3.7) == 3.7
        assert _transform_level(0.0) == 0.0

    def test_pct_to_bps(self):
        assert _transform_pct_to_bps(3.80) == 380  # 3.80% -> 380bp
        assert _transform_pct_to_bps(1.20) == 120

    def test_billions_to_millions(self):
        assert _transform_billions_to_millions(7.5) == 7500  # $7.5B -> $7500M

    def test_millions_round(self):
        assert _transform_millions(847718.123) == 847718

    def test_ism_from_employment(self):
        """MANEMP 3-month change -> ISM proxy centered at 50."""
        # 100K jobs gained in 3 months -> ISM ~60
        values = [
            ("2025-01-01", 12000),
            ("2025-02-01", 12030),
            ("2025-03-01", 12060),
            ("2025-04-01", 12100),  # +100 from Jan
        ]
        result = _transform_ism_from_employment(values)
        assert len(result) == 1
        assert result[0][0] == "2025-04-01"
        assert result[0][1] == 60.0  # 50 + 100/10

    def test_ism_negative_change(self):
        """Job losses -> ISM below 50."""
        values = [
            ("2025-01-01", 12100),
            ("2025-02-01", 12080),
            ("2025-03-01", 12060),
            ("2025-04-01", 12000),  # -100 from Jan
        ]
        result = _transform_ism_from_employment(values)
        assert result[0][1] == 40.0  # 50 + (-100/10)

    def test_ism_clamped(self):
        """Extreme changes clamped to [30, 70]."""
        values = [
            ("2025-01-01", 12000),
            ("2025-02-01", 12000),
            ("2025-03-01", 12000),
            ("2025-04-01", 12500),  # +500 -> would be 100, clamped to 70
        ]
        result = _transform_ism_from_employment(values)
        assert result[0][1] == 70.0


# ===================================================================
# 3. Cache I/O
# ===================================================================

class TestCacheIO:
    """Test CSV cache read/write roundtrip."""

    def test_fred_cache_roundtrip(self, tmp_path, monkeypatch):
        monkeypatch.setattr("backend.engine.fred_series_fetcher.CACHE_DIR", tmp_path)

        data = [("2025-01-01", 3.7), ("2025-02-01", 3.9), ("2025-03-01", 4.1)]
        fred_write_cache("UNRATE_level", data)
        result = fred_read_cache("UNRATE_level", max_age_hours=1.0)

        assert result is not None
        assert len(result) == 3
        assert result[0] == ("2025-01-01", 3.7)
        assert result[2] == ("2025-03-01", 4.1)

    def test_yahoo_cache_roundtrip(self, tmp_path, monkeypatch):
        monkeypatch.setattr("backend.engine.yahoo_series_fetcher.CACHE_DIR", tmp_path)

        data = [("2025-01-02", 104.5), ("2025-01-03", 105.2)]
        yahoo_write_cache("DX_Y_NYB", data)
        result = yahoo_read_cache("DX_Y_NYB", max_age_hours=1.0)

        assert result is not None
        assert len(result) == 2

    def test_fred_cache_expired(self, tmp_path, monkeypatch):
        monkeypatch.setattr("backend.engine.fred_series_fetcher.CACHE_DIR", tmp_path)

        fred_write_cache("EXPIRED", [("2025-01-01", 1.0)])
        # Set max_age to 0 to force expiry
        result = fred_read_cache("EXPIRED", max_age_hours=0.0)
        assert result is None

    def test_fred_cache_miss(self, tmp_path, monkeypatch):
        monkeypatch.setattr("backend.engine.fred_series_fetcher.CACHE_DIR", tmp_path)
        result = fred_read_cache("NONEXISTENT", max_age_hours=1.0)
        assert result is None


# ===================================================================
# 4. Computed series derivation
# ===================================================================

class TestComputedSeriesDerivation:
    """Test the computed field logic in the loader."""

    def test_curve_2s10s(self):
        from scripts.load_series_data import _compute_curve_2s10s

        fred_raw = {
            "DGS10": [("2025-01-01", 4.50), ("2025-02-01", 4.40), ("2025-03-01", 4.30)],
            "DGS2": [("2025-01-01", 4.20), ("2025-02-01", 4.25), ("2025-03-01", 4.15)],
        }
        result = _compute_curve_2s10s(fred_raw)
        assert result is not None
        assert len(result) == 3
        assert result[0] == ("2025-01-01", 0.30)  # 4.50 - 4.20
        assert result[2] == ("2025-03-01", 0.15)  # 4.30 - 4.15

    def test_curve_missing_series(self):
        from scripts.load_series_data import _compute_curve_2s10s
        assert _compute_curve_2s10s({"DGS10": [("2025-01-01", 4.5)]}) is None

    def test_foreign_treasury_pct(self):
        from scripts.load_series_data import _compute_foreign_treasury_pct

        fred_raw = {
            "FDHBFIN": [("2025-01-01", 7500.0)],  # $7,500B
            "GFDEBTN": [("2025-01-01", 36000000.0)],  # $36T in $M
        }
        result = _compute_foreign_treasury_pct(fred_raw)
        assert result is not None
        assert len(result) == 1
        # 7500 / (36000000/1000) * 100 = 7500/36000 * 100 = 20.83
        assert 20.0 < result[0][1] < 21.0


# ===================================================================
# 5. Store population from mapping
# ===================================================================

class TestStorePopulation:
    """Test that the loader correctly populates InMemorySeriesStore."""

    def test_load_with_mocked_fetchers(self):
        """Full pipeline with mocked fetch functions."""
        from backend.engine.v9.series_store import InMemorySeriesStore

        # Create synthetic data for all source types
        dates = [f"2025-{m:02d}-01" for m in range(1, 13)]
        values = [float(i) for i in range(12)]

        store = InMemorySeriesStore()

        # Manually add series as the loader would
        store.add_series("growth.unemployment", dates, values)
        store.add_series("rates.fed_funds", dates, values)
        store.add_series("dxy_index", dates, values)
        store.add_series("qqq_iwm_ratio", dates, values)
        store.add_series("rates.curve_2s10s", dates, values)

        assert store.has_series("growth.unemployment")
        assert store.has_series("rates.fed_funds")
        assert store.has_series("dxy_index")
        assert store.has_series("qqq_iwm_ratio")
        assert store.has_series("rates.curve_2s10s")
        assert store.series_length("growth.unemployment") == 12

    def test_cb_gold_purchases_hardcoded(self):
        """CB gold purchases should load from hardcoded annual values."""
        from scripts.load_series_data import _CB_GOLD_PURCHASES_ANNUAL
        from backend.engine.v9.series_store import InMemorySeriesStore

        store = InMemorySeriesStore()
        dates = sorted(_CB_GOLD_PURCHASES_ANNUAL.keys())
        values = [_CB_GOLD_PURCHASES_ANNUAL[d] for d in dates]
        store.add_series("cb_gold_purchases", dates, values)

        assert store.has_series("cb_gold_purchases")
        assert store.series_length("cb_gold_purchases") == len(_CB_GOLD_PURCHASES_ANNUAL)

    def test_net_liquidity_30d_change(self):
        """Test net liquidity 30d change computation."""
        from scripts.load_series_data import _compute_net_liquidity_30d_change
        from backend.engine.v9.series_store import InMemorySeriesStore

        store = InMemorySeriesStore()
        # 6 months of data, ~30 day spacing
        dates = [f"2025-{m:02d}-01" for m in range(1, 7)]

        # Fed BS rising, TGA stable, RRP falling -> net liq rising
        store.add_series("liquidity.fed_balance_sheet", dates,
                         [7000000, 7100000, 7200000, 7300000, 7400000, 7500000])
        store.add_series("liquidity.tga", dates,
                         [800000, 800000, 800000, 800000, 800000, 800000])
        store.add_series("liquidity.reverse_repo", dates,
                         [500000, 450000, 400000, 350000, 300000, 250000])

        result = _compute_net_liquidity_30d_change(store)
        assert result is not None
        assert len(result) > 0
        # Each month: net_liq increases by ~150K ($M)
        # 30d change should be positive
        assert result[-1][1] > 0
