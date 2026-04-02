# briefing.py — Pydantic models for the data briefing packet.
# Depends on: nothing
# Depended on by: engine/data_agent.py, engine/activation.py, engine/web_data_agent.py
from __future__ import annotations

from typing import Any, Optional

from pydantic import BaseModel


class BriefingSection(BaseModel):
    """A section of the briefing packet (growth, inflation, etc.)."""
    # Fields are dynamic — each section has different metrics.
    # Using dict for flexibility since field names vary by section.
    pass


class MarketData(BaseModel):
    price: Optional[float] = None
    return_1m: Optional[float] = None
    return_3m: Optional[float] = None
    return_12m: Optional[float] = None


class WebSourcedData(BaseModel):
    """A single data point fetched from a web source (not FRED/Yahoo)."""
    value: float
    source: str = ""        # URL or description of data source
    fetched_at: str = ""    # ISO timestamp of when fetched
    confidence: str = ""    # "high", "medium", "low"


# Web-sourced fields that replace FRED-derived proxies when available.
# Key = original field path (what theory modules reference)
# Value = web_sourced field name (better data)
_FIELD_OVERRIDES: dict[str, str] = {
    "growth.ism_proxy": "ism_pmi",  # Actual ISM PMI replaces MANEMP-derived proxy
}


class BriefingPacket(BaseModel):
    """Structured data briefing from FRED + Yahoo Finance + web sources.

    Field names here must match the metric_source references in theory
    module activation conditions.
    """
    timestamp: str = ""
    staleness_hours: float = 0.0

    # Macro sections — flat dicts for easy field-name lookup
    growth: dict[str, Optional[float]] = {}
    inflation: dict[str, Optional[float]] = {}
    rates: dict[str, Optional[float]] = {}
    liquidity: dict[str, Optional[float]] = {}
    credit: dict[str, Optional[float]] = {}
    sentiment: dict[str, Optional[float]] = {}

    # Computed metrics — derived from raw data
    computed: dict[str, Optional[float]] = {}

    # Market data — ETF prices and returns
    markets: dict[str, MarketData] = {}

    # Web-sourced data — fields not available from FRED/Yahoo
    # Populated by web_data_agent.py (Phase 2)
    web_sourced: dict[str, WebSourcedData] = {}

    # Data quality report from validation agent (Phase 4)
    data_quality: dict[str, Any] = {}

    def get_field(self, field_path: str) -> Optional[float]:
        """Resolve a dotted field path like 'credit.hy_spread' or a ticker like '^VIX'.

        Resolution order:
        0. Priority overrides (web-sourced data replacing FRED proxies)
        1. Direct ticker (^VIX, $DXY)
        2. Dotted section path (credit.hy_spread)
        3. Computed metrics (qqq_iwm_ratio)
        4. Web-sourced data (shiller_cape, china_credit_impulse)
        5. Fallback scan across all macro sections
        """
        # Priority overrides: web-sourced data replacing FRED proxies
        override_key = _FIELD_OVERRIDES.get(field_path)
        if override_key and override_key in self.web_sourced:
            return self.web_sourced[override_key].value

        # Direct ticker reference (e.g. ^VIX)
        if field_path.startswith("^") or field_path.startswith("$"):
            ticker = field_path
            if ticker in self.markets:
                return self.markets[ticker].price
            return None

        # Dotted section path (e.g. credit.hy_spread)
        if "." in field_path:
            parts = field_path.split(".", 1)
            section_name, field_name = parts[0], parts[1]
            section = getattr(self, section_name, None)
            if isinstance(section, dict):
                val = section.get(field_name)
                if val is not None:
                    # web_sourced values are WebSourcedData objects — extract .value
                    if isinstance(val, WebSourcedData):
                        return val.value
                    return val
            return None

        # Try computed metrics
        if field_path in self.computed:
            return self.computed[field_path]

        # Try web-sourced data
        if field_path in self.web_sourced:
            return self.web_sourced[field_path].value

        # Try all sections as fallback
        for section_name in ("growth", "inflation", "rates", "liquidity",
                             "credit", "sentiment", "computed"):
            section = getattr(self, section_name, {})
            if isinstance(section, dict) and field_path in section:
                return section[field_path]

        return None
