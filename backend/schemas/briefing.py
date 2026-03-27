# briefing.py — Pydantic models for the data briefing packet.
# Depends on: nothing
# Depended on by: engine/data_agent.py, engine/activation.py
from __future__ import annotations

from typing import Optional

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


class BriefingPacket(BaseModel):
    """Structured data briefing from FRED + Yahoo Finance.

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

    def get_field(self, field_path: str) -> Optional[float]:
        """Resolve a dotted field path like 'credit.hy_spread' or a ticker like '^VIX'.

        Also handles computed metrics like 'qqq_iwm_ratio'.
        """
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
                return section.get(field_name)
            return None

        # Try computed metrics
        if field_path in self.computed:
            return self.computed[field_path]

        # Try all sections as fallback
        for section_name in ("growth", "inflation", "rates", "liquidity",
                             "credit", "sentiment", "computed"):
            section = getattr(self, section_name, {})
            if isinstance(section, dict) and field_path in section:
                return section[field_path]

        return None
