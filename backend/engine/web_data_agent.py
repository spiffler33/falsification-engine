"""web_data_agent.py — Fetches indicators from web sources not available via FRED/Yahoo APIs.

Depends on: schemas/briefing.py (WebSourcedData), httpx, fredapi, yfinance
Depended on by: data_agent.py (build_briefing orchestration), activation.py (via web_sourced)

Populates BriefingPacket.web_sourced with 16 fields that the WEB_FIELD_MAP
in activation.py maps to theory-module indicators marked as 'web search' sources.

Fields produced:
  shiller_cape, ism_pmi, sp500_net_margin, insider_sell_buy_ratio,
  consumer_confidence, total_debt_to_gdp, top10_wealth_share, deficit_pct_gdp,
  finra_margin_debt, passive_fund_share, weighted_avg_interest_rate,
  cb_gold_purchases, em_dm_pe_gap, china_credit_impulse, usdcny, rmb_swift_share
"""

import logging
import os
import re
from datetime import datetime, timezone
from typing import Any, Callable, Optional

import httpx

from backend.schemas.briefing import WebSourcedData

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_TIMEOUT = 15  # seconds per HTTP request
_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/json,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}


# ---------------------------------------------------------------------------
# Utility functions
# ---------------------------------------------------------------------------


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _entry(value: float, source: str, confidence: str = "medium") -> WebSourcedData:
    return WebSourcedData(
        value=round(value, 4),
        source=source,
        fetched_at=_now_iso(),
        confidence=confidence,
    )


def _get(url: str, timeout: int = _TIMEOUT, **kwargs) -> httpx.Response:
    return httpx.get(
        url, headers=_HEADERS, timeout=timeout, follow_redirects=True, **kwargs
    )


def _get_json(url: str, timeout: int = _TIMEOUT, **kwargs) -> Any:
    resp = _get(url, timeout=timeout, **kwargs)
    resp.raise_for_status()
    return resp.json()


def _parse_soup(html: str):
    """Parse HTML with BeautifulSoup. Returns None if bs4/lxml not installed."""
    try:
        from bs4 import BeautifulSoup
    except ImportError:
        logger.warning("beautifulsoup4 not installed -- HTML scraping unavailable")
        return None
    try:
        return BeautifulSoup(html, "lxml")
    except Exception:
        return BeautifulSoup(html, "html.parser")


def _multpl_current(url_path: str) -> Optional[float]:
    """Extract the current numeric value from a multpl.com page.

    multpl.com displays the current value in ``<div id="current">``
    as ``Current <title>: <value>``. We search after the colon to
    avoid grabbing numbers from the title (e.g. "500" from "S&P 500").
    """
    try:
        resp = _get(f"https://www.multpl.com/{url_path}")
        resp.raise_for_status()
        soup = _parse_soup(resp.text)
        if soup:
            current = soup.find("div", id="current")
            if current:
                text = current.get_text()
                colon_pos = text.find(":")
                search_text = text[colon_pos + 1 :] if colon_pos >= 0 else text
                match = re.search(r"([\d,]+\.?\d*)", search_text)
                if match:
                    return float(match.group(1).replace(",", ""))
    except Exception as e:
        logger.debug("multpl.com/%s: %s", url_path, e)
    return None


# ---------------------------------------------------------------------------
# FRED helpers (for fields derivable from FRED series)
# ---------------------------------------------------------------------------

_fred_client_singleton = None


def _get_fred():
    """Get or create a FRED API client. Returns None if unavailable."""
    global _fred_client_singleton
    if _fred_client_singleton is not None:
        return _fred_client_singleton
    try:
        from fredapi import Fred
    except ImportError:
        logger.warning("fredapi not installed")
        return None
    # Load .env if FRED_API_KEY not already in environment
    api_key = os.environ.get("FRED_API_KEY")
    if not api_key:
        try:
            from dotenv import load_dotenv

            load_dotenv()
            api_key = os.environ.get("FRED_API_KEY")
        except ImportError:
            pass
    if not api_key:
        logger.warning("FRED_API_KEY not set -- FRED-derived web fields skipped")
        return None
    _fred_client_singleton = Fred(api_key=api_key)
    return _fred_client_singleton


def _fred_latest(series_id: str) -> Optional[float]:
    """Most recent non-null value from a FRED series."""
    fred = _get_fred()
    if fred is None:
        return None
    try:
        s = fred.get_series(series_id)
        if s is not None and len(s) > 0:
            return float(s.dropna().iloc[-1])
    except Exception as e:
        logger.warning("FRED %s: %s", series_id, e)
    return None


# ===================================================================
# FETCHERS -- one per field, grouped by data source
# ===================================================================


# -------------------------------------------------------------------
# Group 1: FRED-derived (high confidence)
# -------------------------------------------------------------------


def _fetch_total_debt_to_gdp(
    fred_data: Optional[dict] = None,
) -> Optional[WebSourcedData]:
    """Total credit to domestic non-financial sectors / GDP (%).

    FRED Z.1 Financial Accounts: TCMDODNS / GDP.
    """
    tcmd = None
    gdp = None

    if fred_data:
        tcmd = fred_data.get("computed_fred.total_credit_debt")
        gdp = fred_data.get("growth.gdp_latest")

    if tcmd is None:
        tcmd = _fred_latest("TCMDODNS")
    if gdp is None:
        gdp = _fred_latest("GDP")

    if tcmd is None or gdp is None or gdp <= 0:
        return None

    # TCMDODNS is in Millions of USD, GDP is in Billions of USD.
    # If raw ratio > 1000%, we have the expected unit mismatch.
    ratio = tcmd / gdp * 100
    if ratio > 1000:
        ratio = (tcmd / 1000) / gdp * 100
    if 50 < ratio < 500:
        return _entry(ratio, "FRED: TCMDODNS/GDP (Z.1 Financial Accounts)", "high")
    logger.warning("total_debt_to_gdp: ratio %.1f%% outside sanity range", ratio)
    return None


def _fetch_top10_wealth_share() -> Optional[WebSourcedData]:
    """Top 10% share of total household net worth (%).

    FRED Distributional Financial Accounts:
      WFRBST01134 (top 1% net worth share)
      + WFRBSN09161 (90th-99th percentile net worth share).
    """
    top1 = _fred_latest("WFRBST01134")
    next9 = _fred_latest("WFRBSN09161")
    if top1 is not None and next9 is not None:
        total = top1 + next9
        if 40 < total < 90:
            return _entry(total, "FRED: DFA (WFRBST01134 + WFRBSN09161)", "high")
    return None


def _fetch_deficit_pct_gdp(
    fred_data: Optional[dict] = None,
) -> Optional[WebSourcedData]:
    """Federal deficit as % of GDP (annualized, positive = deficit).

    FRED: MTSDS133FMS (monthly, millions, negative=deficit) annualized / GDP.
    """
    deficit_monthly = None
    gdp = None

    if fred_data:
        deficit_monthly = fred_data.get("computed_fred.monthly_treasury_deficit")
        gdp = fred_data.get("growth.gdp_latest")

    if deficit_monthly is None:
        deficit_monthly = _fred_latest("MTSDS133FMS")
    if gdp is None:
        gdp = _fred_latest("GDP")

    if deficit_monthly is None or gdp is None or gdp <= 0:
        return None

    annual_deficit_B = abs(deficit_monthly) * 12 / 1000  # millions -> billions
    pct = annual_deficit_B / gdp * 100
    if 0 < pct < 30:
        return _entry(pct, "FRED: MTSDS133FMS annualized / GDP", "high")
    return None


# -------------------------------------------------------------------
# Group 2: Yahoo Finance (high confidence)
# -------------------------------------------------------------------


def _fetch_usdcny() -> Optional[WebSourcedData]:
    """USD/CNY exchange rate (how many CNY per 1 USD).

    Uses open.er-api.com (free, no key required) since yfinance
    forex tickers are unreliable.
    """
    try:
        data = _get_json("https://open.er-api.com/v6/latest/USD", timeout=10)
        if data.get("result") == "success":
            cny = data.get("rates", {}).get("CNY")
            if cny and 5 < cny < 10:
                return _entry(float(cny), "open.er-api.com/v6/latest/USD", "high")
    except Exception as e:
        logger.debug("usdcny er-api: %s", e)

    # Fallback: Yahoo Finance chart API (direct JSON, bypasses yfinance lib)
    try:
        resp = _get(
            "https://query1.finance.yahoo.com/v8/finance/chart/CNY=X"
            "?interval=1d&range=5d",
            timeout=10,
        )
        if resp.status_code == 200:
            data = resp.json()
            closes = data["chart"]["result"][0]["indicators"]["quote"][0]["close"]
            latest = [x for x in closes if x is not None][-1]
            if 5 < latest < 10:
                return _entry(float(latest), "Yahoo Finance chart API: CNY=X", "high")
    except Exception as e:
        logger.debug("usdcny yahoo chart: %s", e)

    return None


# -------------------------------------------------------------------
# Group 3: Government APIs (high confidence)
# -------------------------------------------------------------------


def _fetch_weighted_avg_interest_rate() -> Optional[WebSourcedData]:
    """Weighted average interest rate on total federal debt (%).

    Treasury Fiscal Data API: Average Interest Rates on U.S. Treasury Securities.
    """
    try:
        url = (
            "https://api.fiscaldata.treasury.gov/services/api/fiscal_service/"
            "v2/accounting/od/avg_interest_rates"
            "?sort=-record_date"
            "&page[size]=100"
            "&fields=record_date,security_desc,avg_interest_rate_amt"
        )
        data = _get_json(url)
        for record in data.get("data", []):
            desc = record.get("security_desc", "").lower()
            if "total" in desc and ("interest" in desc or "marketable" in desc):
                rate = float(record["avg_interest_rate_amt"])
                date = record.get("record_date", "")
                if 0 < rate < 15:
                    return _entry(
                        rate,
                        f"fiscaldata.treasury.gov ({date})",
                        "high",
                    )
    except Exception as e:
        logger.warning("weighted_avg_interest_rate: %s", e)
    return None


# -------------------------------------------------------------------
# Group 4: Web scraping -- well-structured sites (medium-high)
# -------------------------------------------------------------------


def _fetch_shiller_cape() -> Optional[WebSourcedData]:
    """Shiller Cyclically Adjusted PE Ratio from multpl.com."""
    val = _multpl_current("shiller-pe")
    if val is not None and 5 < val < 80:
        return _entry(val, "multpl.com/shiller-pe", "high")
    return None


def _fetch_sp500_net_margin() -> Optional[WebSourcedData]:
    """S&P 500 net profit margin (%).

    Tries multpl.com for earnings-related data. If net margin isn't
    directly available, attempts the PE ratio page to derive a proxy.
    """
    # Attempt 1: direct net profit margin page (may not exist)
    val = _multpl_current("s-p-500-net-income")
    if val is not None:
        # This would be income, not margin. Skip.
        pass

    # Attempt 2: S&P 500 earnings yield -> approximate margin
    # Earnings yield = 1/PE. Not exactly net margin, but directionally useful.
    # Actual net margin requires revenue data we don't have.
    # Instead, try macrotrends data embedded in script tags.
    try:
        resp = _get(
            "https://www.macrotrends.net/stocks/charts/SPY/spdr-s-p-500-etf/net-profit-margin",
            timeout=10,
        )
        if resp.status_code == 200:
            # macrotrends embeds chart data in JavaScript arrays
            match = re.search(
                r'charting.*?\[.*?"v":\s*([\d.]+)\s*\}[^\]]*\]',
                resp.text,
                re.S,
            )
            if not match:
                # Try simpler pattern: last percentage value in a data context
                matches = re.findall(
                    r'<td[^>]*>\s*([\d.]+)%?\s*</td>', resp.text
                )
                if matches:
                    val = float(matches[-1])
                    if 3 < val < 20:
                        return _entry(
                            val, "macrotrends.net/spy-net-profit-margin", "medium"
                        )
    except Exception as e:
        logger.debug("sp500_net_margin macrotrends: %s", e)

    # Attempt 3: Estimate from S&P 500 PE ratio (rough proxy)
    pe = _multpl_current("s-p-500-pe-ratio")
    if pe and 10 < pe < 40:
        # Historical relationship: net margin ~ (1/PE) * price/sales * 100
        # Very rough: if PE=20, earnings yield=5%, typical P/S~2.5 -> margin~12.5%
        # Simplified: margin_estimate = 250 / PE (works for PE 15-30 range)
        margin_est = 250 / pe
        if 5 < margin_est < 20:
            return _entry(
                margin_est,
                f"estimated from S&P 500 PE ({pe:.1f}) via multpl.com",
                "low",
            )

    return None


def _fetch_consumer_confidence() -> Optional[WebSourcedData]:
    """Consumer confidence indicator.

    Primary: Conference Board Consumer Confidence (paywalled).
    Fallback: OECD Consumer Confidence from FRED (CSCICP03USM665S).
    Not identical but serves the same analytical purpose.
    """
    val = _fred_latest("CSCICP03USM665S")
    if val is not None:
        return _entry(
            val, "FRED: OECD Consumer Confidence (CSCICP03USM665S)", "medium"
        )
    return None


# -------------------------------------------------------------------
# Group 5: Web scraping -- moderate difficulty
# -------------------------------------------------------------------


def _fetch_ism_pmi() -> Optional[WebSourcedData]:
    """ISM Manufacturing PMI.

    ISM licenses their data, so free programmatic access is limited.
    Tries the ISM website and financial data pages.
    If all fail, the MANEMP-derived proxy remains active in the briefing.
    """
    # Attempt 1: ISM website press release page
    try:
        resp = httpx.get(
            "https://www.ismworld.org/supply-management-news-and-reports/"
            "reports/ism-report-on-business/pmi/pmi-at-a-glance/",
            headers=_HEADERS,
            timeout=10,
            follow_redirects=False,  # ISM site has redirect loops
        )
        if resp.status_code == 200:
            # Look for the PMI headline number in page text
            match = re.search(
                r"(?:PMI|index|composite)[^0-9]{0,40}?([\d]{2}\.?\d?)\s*(?:%|percent)?",
                resp.text,
                re.I,
            )
            if match:
                val = float(match.group(1))
                if 30 < val < 70:
                    return _entry(val, "ismworld.org/pmi-at-a-glance", "high")
    except Exception as e:
        logger.debug("ism_pmi ismworld.org: %s", e)

    # Attempt 2: investing.com economic calendar (may block bots)
    try:
        resp = _get(
            "https://www.investing.com/economic-calendar/ism-manufacturing-pmi-173",
            timeout=10,
        )
        if resp.status_code == 200:
            # Look for "Actual" value patterns
            for pattern in [
                r'"actualValue"["\s:]*(\d+\.?\d*)',
                r'id="releaseInfo"[^>]*>[^<]*?([\d.]+)',
                r"Actual.*?<[^>]*>([\d.]+)",
            ]:
                match = re.search(pattern, resp.text, re.I)
                if match:
                    val = float(match.group(1))
                    if 30 < val < 70:
                        return _entry(
                            val, "investing.com/ism-manufacturing-pmi", "medium"
                        )
    except Exception as e:
        logger.debug("ism_pmi investing.com: %s", e)

    logger.warning("ism_pmi: all sources failed -- MANEMP proxy remains active")
    return None


def _fetch_insider_sell_buy_ratio() -> Optional[WebSourcedData]:
    """Aggregate insider sell/buy transaction ratio (recent filings).

    Source: openinsider.com -- counts recent SEC Form 4 filings
    for large-cap stocks, computes sell/buy ratio.
    """
    try:
        # Large-cap insider transactions (market cap > $10B)
        resp = _get(
            "http://openinsider.com/screener"
            "?s=&o=&pl=&ph=&ll=&lh=&fd=30&fdr=&td=0&tdr="
            "&feession=&lac=&lbc=&mc=7&mic=&ric="
            "&isc=1&isc=2&isc=3&isc=4&cnt=100&page=1",
            timeout=10,
        )
        if resp.status_code != 200:
            return None

        soup = _parse_soup(resp.text)
        if not soup:
            return None

        table = soup.find("table", class_="tinytable")
        if not table:
            return None

        rows = table.find_all("tr")
        sells, buys = 0, 0
        for row in rows[1:]:
            cells = row.find_all("td")
            # Column 7 is "Trade Type": "P - Purchase", "S - Sale", "S - Sale+OE"
            if len(cells) >= 8:
                tx = cells[7].get_text(strip=True).lower()
                if tx.startswith("s"):
                    sells += 1
                elif tx.startswith("p"):
                    buys += 1

        if buys > 0:
            ratio = sells / buys
            return _entry(
                ratio,
                f"openinsider.com (30d large-cap: {sells}S/{buys}B)",
                "medium",
            )
    except Exception as e:
        logger.warning("insider_sell_buy_ratio: %s", e)
    return None


def _fetch_finra_margin_debt() -> Optional[WebSourcedData]:
    """FINRA margin debt outstanding ($B).

    Downloads FINRA's margin-statistics.xlsx spreadsheet directly.
    Column "Debit Balances in Customers' Securities Margin Accounts"
    is margin debt in millions of USD. First row = most recent month.
    """
    try:
        import io

        import pandas as pd

        resp = _get(
            "https://www.finra.org/sites/default/files/2021-03/margin-statistics.xlsx",
            timeout=20,
        )
        resp.raise_for_status()

        df = pd.read_excel(io.BytesIO(resp.content))
        if df.empty:
            return None

        # First row is most recent. Debit balances column = margin debt.
        debit_col = [c for c in df.columns if "debit" in c.lower()]
        if not debit_col:
            return None

        latest_millions = float(df[debit_col[0]].iloc[0])
        latest_date = str(df.iloc[0, 0])  # Year-Month column
        val_billions = latest_millions / 1000

        if 100 < val_billions < 3000:
            return _entry(
                val_billions,
                f"finra.org/margin-statistics.xlsx ({latest_date})",
                "high",
            )
    except Exception as e:
        logger.warning("finra_margin_debt: %s", e)
    return None


# -------------------------------------------------------------------
# Group 6: Web scraping -- hard / slow-moving (best-effort)
# -------------------------------------------------------------------


def _fetch_em_dm_pe_gap() -> Optional[WebSourcedData]:
    """Emerging vs. Developed markets PE gap (S&P 500 PE - EEM PE).

    Gets S&P 500 trailing PE from multpl.com. For EM PE, tries
    yfinance EEM info; falls back to a historical-ratio estimate.
    """
    sp500_pe = _multpl_current("s-p-500-pe-ratio")
    if not sp500_pe or not (10 < sp500_pe < 50):
        return None

    # Try EEM trailing PE from yfinance
    try:
        import yfinance as yf

        eem = yf.Ticker("EEM")
        eem_info = eem.info
        eem_pe = eem_info.get("trailingPE")
        if eem_pe and 5 < eem_pe < 30:
            gap = sp500_pe - eem_pe
            return _entry(
                gap,
                f"multpl.com S&P PE ({sp500_pe:.1f}) - yfinance EEM PE ({eem_pe:.1f})",
                "medium",
            )
    except Exception as e:
        logger.debug("em_dm_pe_gap yfinance: %s", e)

    # Fallback: EM historically trades at ~60% of DM PE
    est_em_pe = sp500_pe * 0.6
    gap = sp500_pe - est_em_pe
    return _entry(
        gap,
        f"multpl.com S&P PE ({sp500_pe:.1f}) - estimated EM PE ({est_em_pe:.1f})",
        "low",
    )


def _fetch_passive_fund_share() -> Optional[WebSourcedData]:
    """Passive (index) fund share of US equity fund assets (%).

    Primary: ICI Combined Active/Index XLS (flow data, for direction).
    Fallback: Compute from ICI monthly index vs active flow ratio.
    Last resort: documented latest value from ICI/Morningstar reports.

    This is a slow-moving metric (~2-3pp annual increase).
    """
    # Attempt 1: ICI Combined Active/Index XLS — use flow ratio as proxy
    try:
        import io

        import pandas as pd

        resp = _get(
            "https://www.ici.org/statistical-report/combinedactiveindexdataxls",
            timeout=20,
        )
        if resp.status_code == 200 and len(resp.content) > 1000:
            df = pd.read_excel(io.BytesIO(resp.content))
            # The XLS has header rows 0-8, data starts at row 9.
            # Col 2 = Active total flows, Col 8 = Index total flows.
            # Use YTD or trailing 12M cumulative flows.
            # Rows with "YTD" in date column give year-to-date flows.
            active_col = 2  # "Active Funds: Total"
            index_col = 8  # "Index Funds: Total" (column H after header)
            # Use last 12 monthly rows (skip YTD/summary rows)
            data_rows = df.iloc[9:]  # skip header rows
            monthly = data_rows[
                ~data_rows.iloc[:, 1].astype(str).str.contains("YTD|Note", na=False)
            ].tail(12)
            if len(monthly) >= 6:
                active_flows = pd.to_numeric(monthly.iloc[:, active_col], errors="coerce")
                index_flows = pd.to_numeric(monthly.iloc[:, index_col], errors="coerce")
                total_a = active_flows.sum()
                total_i = index_flows.sum()
                if total_a + total_i != 0:
                    # Flow share isn't the same as asset share, but it indicates
                    # direction and magnitude. Index fund flows dominate.
                    idx_flow_share = total_i / (abs(total_a) + abs(total_i)) * 100
                    logger.debug(
                        "passive_fund_share: 12M flow share=%.1f%% (A=%.0fM, I=%.0fM)",
                        idx_flow_share, total_a, total_i,
                    )
    except Exception as e:
        logger.debug("passive_fund_share ICI XLS: %s", e)

    # Attempt 2: Scrape from Morningstar or ETF.com public pages
    try:
        resp = _get("https://www.etf.com/sections/etf-basics", timeout=10)
        if resp.status_code == 200:
            match = re.search(
                r"(?:passive|index)\s+(?:fund|investing)[^%]{0,80}([\d.]+)\s*%",
                resp.text,
                re.I,
            )
            if match:
                val = float(match.group(1))
                if 30 < val < 80:
                    return _entry(val, "etf.com", "medium")
    except Exception as e:
        logger.debug("passive_fund_share etf.com: %s", e)

    # Attempt 3: Documented fallback from Morningstar/ICI public reports.
    # Morningstar reported passive overtook active in US equity in Sept 2024
    # at ~50%. S&P Global SPIVA confirmed ~57% by end of 2024.
    # Growth rate ~2-3pp/year. Conservative estimate for early 2026: ~59%.
    return _entry(
        59.0,
        "Morningstar/S&P SPIVA estimate (~57% end-2024, +2pp/yr trend)",
        "low",
    )


def _fetch_cb_gold_purchases() -> Optional[WebSourcedData]:
    """Central bank net gold purchases (tonnes, trailing 12M).

    Primary: WGC Goldhub (JS-rendered, may fail).
    Secondary: Wikipedia gold reserve article.
    Last resort: documented WGC quarterly report figure.
    """
    # Attempt 1: WGC Goldhub — look for JSON-LD structured data
    try:
        resp = _get("https://www.gold.org/goldhub/data/gold-demand-by-country", timeout=10)
        if resp.status_code == 200:
            # Check JSON-LD for any demand data
            soup = _parse_soup(resp.text)
            if soup:
                for script in soup.find_all("script", type="application/ld+json"):
                    text = script.get_text()
                    if "demand" in text.lower() or "purchase" in text.lower():
                        import json as _json
                        try:
                            data = _json.loads(text)
                            # Look for numeric values in structured data
                            text_repr = str(data)
                            match = re.search(r"(\d[\d,]*)\s*(?:tonnes|t\b)", text_repr, re.I)
                            if match:
                                val = float(match.group(1).replace(",", ""))
                                if 100 < val < 3000:
                                    return _entry(val, "gold.org/goldhub (structured data)", "medium")
                        except Exception:
                            pass
    except Exception as e:
        logger.debug("cb_gold_purchases WGC: %s", e)

    # Attempt 2: Wikipedia — Gold reserve article
    try:
        resp = _get("https://en.wikipedia.org/wiki/Gold_reserve", timeout=10)
        if resp.status_code == 200:
            # Look for recent central bank purchase figures
            for pattern in [
                r"(?:central\s+bank|official\s+sector)[^0-9]{0,100}([\d,]+)\s*(?:tonnes|metric\s+ton)",
                r"(?:purchas|bought|added|acquir)[^0-9]{0,60}([\d,]+)\s*(?:tonnes|t\b)",
                r"(?:202[3-6])[^0-9]{0,40}([\d,]+)\s*(?:tonnes|metric)",
            ]:
                match = re.search(pattern, resp.text, re.I)
                if match:
                    val = float(match.group(1).replace(",", ""))
                    if 100 < val < 3000:
                        return _entry(val, "en.wikipedia.org/wiki/Gold_reserve", "medium")
    except Exception as e:
        logger.debug("cb_gold_purchases Wikipedia: %s", e)

    # Attempt 3: Documented fallback from WGC reports.
    # WGC reported 1,037 tonnes of central bank purchases in 2024,
    # following 1,049 tonnes in 2023. Trend: sustained buying >1000t/yr.
    return _entry(
        1037.0,
        "WGC 2024 annual report: 1,037 tonnes net central bank purchases",
        "low",
    )


def _fetch_china_credit_impulse() -> Optional[WebSourcedData]:
    """China credit impulse (YoY change in credit-to-GDP ratio, pp).

    Uses FRED series QCNPAM770A: BIS total credit to private
    non-financial sector for China (% of GDP, quarterly).
    Credit impulse = current value minus value 4 quarters ago.
    """
    fred = _get_fred()
    if fred is None:
        return None
    try:
        s = fred.get_series("QCNPAM770A")
        if s is None or len(s) < 5:
            return None
        recent = s.dropna().tail(8)
        vals = list(recent.values)
        if len(vals) >= 5:
            curr = float(vals[-1])
            prev_yr = float(vals[-4])
            impulse = curr - prev_yr  # YoY change in pp
            if -30 < impulse < 30:
                return _entry(
                    impulse,
                    f"FRED: QCNPAM770A BIS China credit/GDP ({curr:.1f}% - {prev_yr:.1f}%)",
                    "high",
                )
    except Exception as e:
        logger.warning("china_credit_impulse FRED: %s", e)
    return None


def _fetch_rmb_swift_share() -> Optional[WebSourcedData]:
    """RMB share of global SWIFT payments (%).

    Primary: SWIFT RMB Tracker (monthly publication, JS-rendered).
    Secondary: Wikipedia — Internationalisation of the renminbi.
    Last resort: documented SWIFT tracker figure.
    """
    # Attempt 1: SWIFT RMB Tracker page
    try:
        resp = _get(
            "https://www.swift.com/our-solutions/compliance-and-shared-services/"
            "business-intelligence/renminbi/rmb-tracker",
            timeout=10,
        )
        if resp.status_code == 200:
            for pattern in [
                r"(?:rmb|renminbi|yuan)\s+(?:share|proportion|rank)[^%]{0,80}([\d.]+)\s*%",
                r"([\d.]+)\s*%[^.]{0,60}(?:rmb|renminbi|yuan|global\s+payment)",
                r"(?:share|proportion)\s+of\s+(?:global|world)[^%]{0,80}([\d.]+)\s*%",
            ]:
                match = re.search(pattern, resp.text, re.I)
                if match:
                    val = float(match.group(1))
                    if 1.0 < val < 15:
                        return _entry(val, "swift.com/rmb-tracker", "medium")
    except Exception as e:
        logger.debug("rmb_swift_share SWIFT: %s", e)

    # Attempt 2: Wikipedia — Internationalisation of the renminbi
    try:
        resp = _get(
            "https://en.wikipedia.org/wiki/Internationalisation_of_the_renminbi",
            timeout=10,
        )
        if resp.status_code == 200:
            for pattern in [
                r"SWIFT[^%]{0,100}([\d.]+)\s*%",
                r"([\d.]+)\s*%[^.]{0,60}SWIFT",
                r"(?:payment|transaction)[^%]{0,80}([\d.]+)\s*%[^.]{0,40}(?:renminbi|RMB|yuan)",
            ]:
                matches = re.findall(pattern, resp.text, re.I)
                for m in matches:
                    val = float(m)
                    if 1.0 < val < 15:
                        return _entry(
                            val,
                            "en.wikipedia.org/Internationalisation_of_the_renminbi",
                            "medium",
                        )
    except Exception as e:
        logger.debug("rmb_swift_share Wikipedia: %s", e)

    # Attempt 3: Documented fallback from SWIFT RMB Tracker.
    # SWIFT reported RMB share at 4.69% of global payments in Nov 2024,
    # 3.89% in Feb 2025. Range 3.5-4.7% in recent months.
    return _entry(
        3.89,
        "SWIFT RMB Tracker Feb 2025: 3.89% of global payments",
        "low",
    )


# ===================================================================
# Registry and main entry point
# ===================================================================

# (field_name, fetcher_function, needs_fred_data)
_FETCHER_REGISTRY: list[tuple[str, Callable, bool]] = [
    # FRED-derived (high confidence)
    ("total_debt_to_gdp", _fetch_total_debt_to_gdp, True),
    ("top10_wealth_share", _fetch_top10_wealth_share, False),
    ("deficit_pct_gdp", _fetch_deficit_pct_gdp, True),
    # Yahoo Finance (high confidence)
    ("usdcny", _fetch_usdcny, False),
    # Government API (high confidence)
    ("weighted_avg_interest_rate", _fetch_weighted_avg_interest_rate, False),
    # Web scraping -- reliable
    ("shiller_cape", _fetch_shiller_cape, False),
    ("consumer_confidence", _fetch_consumer_confidence, False),
    # Web scraping -- moderate
    ("sp500_net_margin", _fetch_sp500_net_margin, False),
    ("ism_pmi", _fetch_ism_pmi, False),
    ("insider_sell_buy_ratio", _fetch_insider_sell_buy_ratio, False),
    ("finra_margin_debt", _fetch_finra_margin_debt, False),
    ("em_dm_pe_gap", _fetch_em_dm_pe_gap, False),
    # Web scraping -- hard (best-effort)
    ("passive_fund_share", _fetch_passive_fund_share, False),
    ("cb_gold_purchases", _fetch_cb_gold_purchases, False),
    ("china_credit_impulse", _fetch_china_credit_impulse, False),
    ("rmb_swift_share", _fetch_rmb_swift_share, False),
]


def fetch_web_data(
    fred_data: Optional[dict[str, Optional[float]]] = None,
    on_progress: Optional[Callable[[str, str], None]] = None,
) -> dict[str, WebSourcedData]:
    """Fetch all web-sourced data fields.

    Args:
        fred_data: Pre-fetched FRED data from data_agent (optional).
            If provided, FRED-derived fields use these values instead
            of making separate API calls.
        on_progress: Optional callback(field_name, status) for progress.

    Returns:
        Dict of field_name -> WebSourcedData for successfully fetched fields.
        Fields that fail return no entry -- activation layer handles gaps.
    """
    results: dict[str, WebSourcedData] = {}

    def emit(field: str, status: str) -> None:
        if on_progress:
            on_progress(field, status)

    for field_name, fetcher, needs_fred in _FETCHER_REGISTRY:
        emit(field_name, "fetching")
        try:
            if needs_fred:
                result = fetcher(fred_data=fred_data)
            else:
                result = fetcher()

            if result is not None:
                results[field_name] = result
                emit(field_name, f"ok ({result.confidence})")
                logger.info(
                    "web [%s] = %.4f  (%s, %s)",
                    field_name,
                    result.value,
                    result.confidence,
                    result.source,
                )
            else:
                emit(field_name, "no data")
                logger.info("web [%s]: no data", field_name)
        except Exception as e:
            emit(field_name, f"error: {e}")
            logger.warning("web [%s] unexpected: %s", field_name, e)

    # Summary
    total = len(_FETCHER_REGISTRY)
    ok = len(results)
    high = sum(1 for r in results.values() if r.confidence == "high")
    med = sum(1 for r in results.values() if r.confidence == "medium")
    low = sum(1 for r in results.values() if r.confidence == "low")
    logger.info(
        "Web data complete: %d/%d fields (%d high, %d medium, %d low)",
        ok,
        total,
        high,
        med,
        low,
    )

    return results
