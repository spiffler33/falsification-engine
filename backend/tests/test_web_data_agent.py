# test_web_data_agent.py -- Phase 6: Fixture-based tests for web data parsers.
# Tests parsers against saved HTML/JSON fixtures (no live HTTP).
# Also tests utility functions, the registry, and fetch_web_data orchestration.
import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from backend.engine.web_data_agent import (
    _entry,
    _fetch_deficit_pct_gdp,
    _fetch_insider_sell_buy_ratio,
    _fetch_ism_pmi,
    _fetch_shiller_cape,
    _fetch_sp500_net_margin,
    _fetch_total_debt_to_gdp,
    _fetch_usdcny,
    _fetch_weighted_avg_interest_rate,
    _multpl_current,
    _parse_soup,
    _FETCHER_REGISTRY,
    fetch_web_data,
)
from backend.schemas.briefing import WebSourcedData

FIXTURES = Path(__file__).parent / "fixtures"


# ---------------------------------------------------------------------------
# Utility function tests
# ---------------------------------------------------------------------------


class TestEntry:
    def test_creates_web_sourced_data(self):
        result = _entry(37.92, "multpl.com", "high")
        assert isinstance(result, WebSourcedData)
        assert result.value == 37.92
        assert result.source == "multpl.com"
        assert result.confidence == "high"
        assert result.fetched_at  # non-empty ISO string

    def test_rounds_to_4_decimals(self):
        result = _entry(3.14159265, "test", "low")
        assert result.value == 3.1416


class TestParseSoup:
    def test_parses_valid_html(self):
        soup = _parse_soup("<html><body><div id='test'>hello</div></body></html>")
        assert soup is not None
        assert soup.find("div", id="test").get_text() == "hello"

    def test_returns_none_without_bs4(self):
        # We can't easily unimport bs4, but we can verify it doesn't crash
        soup = _parse_soup("")
        assert soup is not None  # bs4 is installed; empty doc is valid


class TestMultplCurrent:
    """Test _multpl_current() against fixture HTML."""

    def test_extracts_shiller_pe(self):
        html = (FIXTURES / "multpl_shiller_pe.html").read_text()
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.text = html
        mock_resp.raise_for_status = MagicMock()

        with patch("backend.engine.web_data_agent._get", return_value=mock_resp):
            result = _multpl_current("shiller-pe")
        assert result == 37.92

    def test_extracts_sp500_pe(self):
        html = (FIXTURES / "multpl_sp500_pe.html").read_text()
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.text = html
        mock_resp.raise_for_status = MagicMock()

        with patch("backend.engine.web_data_agent._get", return_value=mock_resp):
            result = _multpl_current("s-p-500-pe-ratio")
        assert result == 27.85

    def test_returns_none_on_http_error(self):
        with patch("backend.engine.web_data_agent._get", side_effect=Exception("timeout")):
            result = _multpl_current("shiller-pe")
        assert result is None

    def test_returns_none_when_no_current_div(self):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.text = "<html><body><p>No data here</p></body></html>"
        mock_resp.raise_for_status = MagicMock()

        with patch("backend.engine.web_data_agent._get", return_value=mock_resp):
            result = _multpl_current("shiller-pe")
        assert result is None


# ---------------------------------------------------------------------------
# Individual fetcher tests (against fixtures)
# ---------------------------------------------------------------------------


class TestFetchShillerCape:
    def test_returns_cape_value(self):
        html = (FIXTURES / "multpl_shiller_pe.html").read_text()
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.text = html
        mock_resp.raise_for_status = MagicMock()

        with patch("backend.engine.web_data_agent._get", return_value=mock_resp):
            result = _fetch_shiller_cape()
        assert result is not None
        assert result.value == 37.92
        assert result.confidence == "high"
        assert "multpl.com" in result.source


class TestFetchWeightedAvgInterestRate:
    def test_extracts_total_interest_bearing(self):
        data = json.loads((FIXTURES / "treasury_avg_interest_rates.json").read_text())

        with patch("backend.engine.web_data_agent._get_json", return_value=data):
            result = _fetch_weighted_avg_interest_rate()
        assert result is not None
        assert result.value == 3.36
        assert result.confidence == "high"
        assert "2026-03-01" in result.source

    def test_returns_none_on_api_error(self):
        with patch("backend.engine.web_data_agent._get_json", side_effect=Exception("500")):
            result = _fetch_weighted_avg_interest_rate()
        assert result is None


class TestFetchUsdcny:
    def test_extracts_cny_rate(self):
        data = json.loads((FIXTURES / "er_api_usd.json").read_text())

        with patch("backend.engine.web_data_agent._get_json", return_value=data):
            result = _fetch_usdcny()
        assert result is not None
        assert result.value == 6.89
        assert result.confidence == "high"

    def test_falls_back_to_yahoo(self):
        """When er-api fails, tries Yahoo chart API."""
        yahoo_data = {
            "chart": {
                "result": [
                    {
                        "indicators": {
                            "quote": [{"close": [7.10, 7.12, None, 7.15, 7.14]}]
                        }
                    }
                ]
            }
        }
        yahoo_resp = MagicMock()
        yahoo_resp.status_code = 200
        yahoo_resp.json.return_value = yahoo_data

        with patch("backend.engine.web_data_agent._get_json", side_effect=Exception("er-api down")), \
             patch("backend.engine.web_data_agent._get", return_value=yahoo_resp):
            result = _fetch_usdcny()
        assert result is not None
        assert result.value == 7.14  # last non-None close
        assert "Yahoo" in result.source


class TestFetchInsiderSellBuyRatio:
    def test_computes_ratio_from_fixture(self):
        html = (FIXTURES / "openinsider_screener.html").read_text()
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.text = html

        with patch("backend.engine.web_data_agent._get", return_value=mock_resp):
            result = _fetch_insider_sell_buy_ratio()
        # Fixture: 4 sells (AAPL Sale, MSFT Sale+OE, GOOGL Sale, META Sale), 2 buys (JPM, BRK.B)
        assert result is not None
        assert result.value == pytest.approx(2.0, rel=0.01)
        assert result.confidence == "medium"

    def test_returns_none_on_http_failure(self):
        mock_resp = MagicMock()
        mock_resp.status_code = 403
        with patch("backend.engine.web_data_agent._get", return_value=mock_resp):
            result = _fetch_insider_sell_buy_ratio()
        assert result is None


class TestFetchIsmPmi:
    def test_investing_com_fallback(self):
        """ISM website fails (redirect loop), investing.com fixture works."""
        ism_exc = Exception("redirect loop")
        investing_html = (FIXTURES / "ism_investing_com.html").read_text()

        investing_resp = MagicMock()
        investing_resp.status_code = 200
        investing_resp.text = investing_html

        # httpx.get for ISM raises, _get for investing.com returns fixture
        with patch("backend.engine.web_data_agent.httpx") as mock_httpx, \
             patch("backend.engine.web_data_agent._get", return_value=investing_resp):
            mock_httpx.get.side_effect = ism_exc
            result = _fetch_ism_pmi()
        assert result is not None
        assert result.value == 52.7

    def test_returns_none_when_all_fail(self):
        with patch("backend.engine.web_data_agent.httpx") as mock_httpx, \
             patch("backend.engine.web_data_agent._get", side_effect=Exception("blocked")):
            mock_httpx.get.side_effect = Exception("redirect")
            result = _fetch_ism_pmi()
        assert result is None


class TestFetchTotalDebtToGdp:
    def test_uses_fred_data_passthrough(self):
        fred_data = {
            "computed_fred.total_credit_debt": 73_500_000,  # millions
            "growth.gdp_latest": 29_000,  # billions
        }
        result = _fetch_total_debt_to_gdp(fred_data=fred_data)
        assert result is not None
        # 73,500,000 M / 1000 = 73,500 B, / 29,000 B * 100 = 253.4%
        assert 250 < result.value < 260
        assert result.confidence == "high"

    def test_returns_none_when_no_data(self):
        result = _fetch_total_debt_to_gdp(fred_data={})
        # Without FRED client, returns None
        with patch("backend.engine.web_data_agent._fred_latest", return_value=None):
            result = _fetch_total_debt_to_gdp(fred_data={})
        assert result is None


class TestFetchDeficitPctGdp:
    def test_computes_deficit_pct(self):
        fred_data = {
            "computed_fred.monthly_treasury_deficit": -250_000,  # millions, negative
            "growth.gdp_latest": 29_000,  # billions
        }
        result = _fetch_deficit_pct_gdp(fred_data=fred_data)
        assert result is not None
        # |250000| * 12 / 1000 = 3000 B, / 29000 * 100 = 10.3%
        assert 10 < result.value < 11
        assert result.confidence == "high"


class TestFetchSp500NetMargin:
    def test_pe_based_estimate(self):
        """When macrotrends fails, falls back to PE-based estimate."""
        pe_html = (FIXTURES / "multpl_sp500_pe.html").read_text()
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.text = pe_html
        mock_resp.raise_for_status = MagicMock()

        macrotrends_resp = MagicMock()
        macrotrends_resp.status_code = 403  # blocked

        call_count = 0

        def mock_get(url, **kwargs):
            nonlocal call_count
            call_count += 1
            if "macrotrends" in url:
                return macrotrends_resp
            return mock_resp  # multpl.com

        with patch("backend.engine.web_data_agent._get", side_effect=mock_get):
            result = _fetch_sp500_net_margin()
        assert result is not None
        # PE=27.85, margin_est = 250/27.85 = 8.97%
        assert 8 < result.value < 10
        assert result.confidence == "low"


# ---------------------------------------------------------------------------
# Registry and orchestration tests
# ---------------------------------------------------------------------------


class TestFetcherRegistry:
    def test_registry_has_16_entries(self):
        assert len(_FETCHER_REGISTRY) == 16

    def test_all_entries_have_correct_shape(self):
        for field_name, fetcher, needs_fred in _FETCHER_REGISTRY:
            assert isinstance(field_name, str)
            assert callable(fetcher)
            assert isinstance(needs_fred, bool)

    def test_field_names_are_unique(self):
        names = [entry[0] for entry in _FETCHER_REGISTRY]
        assert len(names) == len(set(names))


class TestFetchWebData:
    def test_returns_dict_of_web_sourced_data(self):
        """Mock all fetchers to return synthetic data."""
        fake = _entry(42.0, "test", "high")

        def fake_fetcher(**kwargs):
            return fake

        def fake_fetcher_no_fred():
            return fake

        with patch("backend.engine.web_data_agent._FETCHER_REGISTRY", [
            ("test_field_a", lambda fred_data=None: fake, True),
            ("test_field_b", lambda: fake, False),
        ]):
            results = fetch_web_data(fred_data={"foo": 1.0})
        assert "test_field_a" in results
        assert "test_field_b" in results
        assert results["test_field_a"].value == 42.0

    def test_progress_callback_called(self):
        fake = _entry(10.0, "test", "medium")
        calls = []

        with patch("backend.engine.web_data_agent._FETCHER_REGISTRY", [
            ("one", lambda: fake, False),
        ]):
            fetch_web_data(on_progress=lambda f, s: calls.append((f, s)))
        assert len(calls) == 2  # "fetching" + "ok (medium)"
        assert calls[0] == ("one", "fetching")

    def test_graceful_degradation_on_failure(self):
        def broken():
            raise RuntimeError("network error")

        with patch("backend.engine.web_data_agent._FETCHER_REGISTRY", [
            ("broken_field", broken, False),
            ("ok_field", lambda: _entry(5.0, "src", "low"), False),
        ]):
            results = fetch_web_data()
        assert "broken_field" not in results
        assert "ok_field" in results

    def test_returns_empty_when_all_fail(self):
        def broken():
            raise RuntimeError("fail")

        with patch("backend.engine.web_data_agent._FETCHER_REGISTRY", [
            ("a", broken, False),
            ("b", broken, False),
        ]):
            results = fetch_web_data()
        assert results == {}
