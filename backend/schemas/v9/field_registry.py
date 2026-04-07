"""v9 canonical field registry contract.

Every field the compiler can reference must be registered here.
Unknown field references are compilation errors, not runtime surprises.

The registry serves three purposes:
  1. Compilation gate: the compiler can only emit field_ids that exist here
  2. Unit contract: declares the unit of each field so comparisons can be
     unit-normalized at runtime
  3. Semantic typing: declares what kind of economic quantity each field
     represents, so category errors (rate vs level) are caught at validation

Design decisions:
  - FieldEntry is the schema contract. The actual field inventory is populated
    in Phase 1 from the data agent's FRED/Yahoo/web registry.
  - The registry is a flat dict[str, FieldEntry] keyed by canonical field_id.
  - Computed fields declare their dependencies so the validator can check
    whether upstream fields are available.
  - comparison_class is derived from semantic_type via the units module,
    not stored redundantly.
"""
from __future__ import annotations

from enum import Enum
from typing import Optional

from pydantic import BaseModel

from backend.schemas.v9.units import ComparisonClass, SemanticType, ValueUnit, get_comparison_class


# ---------------------------------------------------------------------------
# Field metadata
# ---------------------------------------------------------------------------

class FieldKind(str, Enum):
    """Whether a field is a single value or a time series."""
    SCALAR = "scalar"       # single point-in-time value
    SERIES = "series"       # historical time series available


class FieldSource(str, Enum):
    """Where the field's data comes from."""
    FRED = "fred"                   # FRED API
    YAHOO = "yahoo"                 # Yahoo Finance
    WEB = "web"                     # web scraping / manual entry
    COMPUTED = "computed"           # derived from other fields
    EXTERNAL = "external"           # external data provider


class DataFrequency(str, Enum):
    """How often the underlying data is updated."""
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"
    ANNUAL = "annual"
    IRREGULAR = "irregular"         # updated on no fixed schedule


class AllowedOperators(str, Enum):
    """Families of comparison operators allowed for this field."""
    NUMERIC = "numeric"             # gt, gte, lt, lte, eq — the standard set
    THRESHOLD_ONLY = "threshold_only"  # only gt/lt comparisons (not eq)
    CATEGORICAL = "categorical"     # eq only (for encoded states)


# ---------------------------------------------------------------------------
# Field entry — one field in the registry
# ---------------------------------------------------------------------------

class FieldEntry(BaseModel):
    """A single field in the canonical field registry.

    Every field the compiler can reference must have an entry.
    Fields not in the registry cannot appear in compiled artifacts.
    """
    # Identity
    field_id: str                               # canonical ID, e.g., "growth.initial_claims"
    display_name: str                           # human-readable, e.g., "Initial Jobless Claims"
    description: str = ""                       # what this field measures

    # Data shape
    kind: FieldKind = FieldKind.SCALAR          # scalar or series
    unit: ValueUnit = ValueUnit.UNKNOWN         # the unit of the value in the briefing
    semantic_type: SemanticType = SemanticType.LEVEL  # what kind of economic quantity

    # Data source
    source: FieldSource = FieldSource.FRED
    frequency: DataFrequency = DataFrequency.MONTHLY
    is_mechanical: bool = True                  # True = directly from data source, no human judgment

    # For computed fields
    is_computed: bool = False
    dependencies: list[str] = []                # field_ids this is derived from
    computation_description: str = ""           # how it's computed

    # Comparison constraints
    allowed_operators: AllowedOperators = AllowedOperators.NUMERIC

    # Briefing packet path (may differ from field_id for web-sourced/computed)
    briefing_path: str = ""                     # if different from field_id

    @property
    def comparison_class(self) -> ComparisonClass:
        """Derived from semantic_type — not stored redundantly."""
        return get_comparison_class(self.semantic_type)


# ---------------------------------------------------------------------------
# Field registry — the contract
# ---------------------------------------------------------------------------

class FieldRegistry(BaseModel):
    """The canonical field registry.

    Keyed by field_id. The compiler and validator both reference this
    to check field existence, units, and semantic types.
    """
    schema_version: int = 1
    fields: dict[str, FieldEntry] = {}

    def has_field(self, field_id: str) -> bool:
        """Check whether a field_id is registered."""
        return field_id in self.fields

    def get_field(self, field_id: str) -> Optional[FieldEntry]:
        """Look up a field entry by ID. Returns None if not found."""
        return self.fields.get(field_id)

    def get_unit(self, field_id: str) -> Optional[ValueUnit]:
        """Get the declared unit for a field. Returns None if not found."""
        entry = self.fields.get(field_id)
        return entry.unit if entry else None

    def get_semantic_type(self, field_id: str) -> Optional[SemanticType]:
        """Get the declared semantic type for a field."""
        entry = self.fields.get(field_id)
        return entry.semantic_type if entry else None

    def get_comparison_class(self, field_id: str) -> Optional[ComparisonClass]:
        """Get the comparison class for a field (derived from semantic type)."""
        entry = self.fields.get(field_id)
        return entry.comparison_class if entry else None

    def check_comparison_legality(
        self, field_a_id: str, field_b_id: str,
    ) -> tuple[bool, str]:
        """Check whether two fields can legally be compared.

        Returns (is_legal, reason).
        """
        entry_a = self.fields.get(field_a_id)
        entry_b = self.fields.get(field_b_id)

        if entry_a is None:
            return False, f"Unknown field: {field_a_id}"
        if entry_b is None:
            return False, f"Unknown field: {field_b_id}"

        class_a = entry_a.comparison_class
        class_b = entry_b.comparison_class

        if class_a != class_b:
            return False, (
                f"Comparison class mismatch: "
                f"{field_a_id} is {class_a.value} ({entry_a.semantic_type.value}), "
                f"{field_b_id} is {class_b.value} ({entry_b.semantic_type.value})"
            )

        return True, "ok"

    def check_unit_compatibility(
        self, field_id: str, literal_unit: ValueUnit,
    ) -> tuple[bool, str]:
        """Check whether a field can be compared to a literal with the given unit.

        Returns (is_compatible, reason).
        """
        entry = self.fields.get(field_id)
        if entry is None:
            return False, f"Unknown field: {field_id}"

        from backend.schemas.v9.units import can_convert
        if entry.unit == ValueUnit.UNKNOWN or literal_unit == ValueUnit.UNKNOWN:
            return True, "unknown unit — cannot verify (warning)"

        if entry.unit == literal_unit:
            return True, "ok"

        if can_convert(literal_unit, entry.unit):
            return True, f"convertible: {literal_unit.value} -> {entry.unit.value}"

        return False, (
            f"Unit mismatch: field {field_id} is {entry.unit.value}, "
            f"literal is {literal_unit.value}, no conversion exists"
        )

    def validate_dependencies(self, field_id: str) -> list[str]:
        """Check that all dependencies of a computed field exist.

        Returns list of missing dependency field_ids (empty = ok).
        """
        entry = self.fields.get(field_id)
        if entry is None:
            return [field_id]
        if not entry.is_computed:
            return []
        return [dep for dep in entry.dependencies if dep not in self.fields]

    def register(self, entry: FieldEntry) -> None:
        """Register a field entry. Overwrites if field_id already exists."""
        self.fields[entry.field_id] = entry

    def field_count(self) -> int:
        """Total number of registered fields."""
        return len(self.fields)


# ---------------------------------------------------------------------------
# Seed registry builder — used in Phase 1 to populate from data agent
# ---------------------------------------------------------------------------

def build_seed_registry() -> FieldRegistry:
    """Build a minimal seed registry from the known fields in the spike.

    This is a Phase 0 placeholder. Phase 1 will build the full registry
    from the data agent's FRED/Yahoo/web registries with complete metadata.

    The seed registry has enough entries to validate the Phase 0 contracts
    and test the comparison legality logic.
    """
    registry = FieldRegistry()

    # A representative sample — enough to test contracts, not exhaustive.
    # Phase 1 will populate the complete registry from data_agent.py's
    # FRED_SERIES, YAHOO_TICKERS, and web-sourced field configs.
    _SEED_FIELDS: list[dict] = [
        # Growth
        {"field_id": "growth.gdp_latest", "display_name": "GDP (nominal, latest)",
         "unit": ValueUnit.USD_BILLIONS, "semantic_type": SemanticType.LEVEL,
         "source": FieldSource.FRED, "frequency": DataFrequency.QUARTERLY},
        {"field_id": "growth.real_gdp", "display_name": "Real GDP Growth Rate",
         "unit": ValueUnit.PERCENT, "semantic_type": SemanticType.GROWTH_RATE,
         "source": FieldSource.FRED, "frequency": DataFrequency.QUARTERLY},
        {"field_id": "growth.unemployment", "display_name": "Unemployment Rate",
         "unit": ValueUnit.PERCENT, "semantic_type": SemanticType.RATE,
         "source": FieldSource.FRED, "frequency": DataFrequency.MONTHLY},
        {"field_id": "growth.initial_claims", "display_name": "Initial Jobless Claims",
         "unit": ValueUnit.COUNT, "semantic_type": SemanticType.COUNT,
         "source": FieldSource.FRED, "frequency": DataFrequency.WEEKLY,
         "kind": FieldKind.SERIES},
        {"field_id": "growth.ism_proxy", "display_name": "ISM Manufacturing PMI (proxy)",
         "unit": ValueUnit.INDEX_POINTS, "semantic_type": SemanticType.INDEX,
         "source": FieldSource.FRED, "frequency": DataFrequency.MONTHLY},

        # Rates
        {"field_id": "rates.fed_funds", "display_name": "Federal Funds Rate",
         "unit": ValueUnit.PERCENT, "semantic_type": SemanticType.RATE,
         "source": FieldSource.FRED, "frequency": DataFrequency.DAILY},
        {"field_id": "rates.treasury_10y", "display_name": "10-Year Treasury Yield",
         "unit": ValueUnit.PERCENT, "semantic_type": SemanticType.RATE,
         "source": FieldSource.FRED, "frequency": DataFrequency.DAILY},
        {"field_id": "rates.curve_2s10s", "display_name": "2s10s Yield Curve Spread",
         "unit": ValueUnit.PERCENT, "semantic_type": SemanticType.SPREAD,
         "source": FieldSource.FRED, "frequency": DataFrequency.DAILY},

        # Credit
        {"field_id": "credit.hy_spread", "display_name": "High-Yield Credit Spread",
         "unit": ValueUnit.BASIS_POINTS, "semantic_type": SemanticType.SPREAD,
         "source": FieldSource.FRED, "frequency": DataFrequency.DAILY},

        # Liquidity
        {"field_id": "liquidity.tga", "display_name": "Treasury General Account Balance",
         "unit": ValueUnit.USD_BILLIONS, "semantic_type": SemanticType.BALANCE,
         "source": FieldSource.FRED, "frequency": DataFrequency.WEEKLY},
        {"field_id": "liquidity.reverse_repo", "display_name": "Reverse Repo Facility Balance",
         "unit": ValueUnit.USD_BILLIONS, "semantic_type": SemanticType.BALANCE,
         "source": FieldSource.FRED, "frequency": DataFrequency.DAILY},

        # Computed
        {"field_id": "equity_risk_premium", "display_name": "Equity Risk Premium",
         "unit": ValueUnit.PERCENT, "semantic_type": SemanticType.SPREAD,
         "source": FieldSource.COMPUTED, "is_computed": True,
         "dependencies": ["rates.treasury_10y"],
         "computation_description": "S&P 500 earnings yield minus 10Y Treasury yield"},
        {"field_id": "shiller_cape", "display_name": "Shiller CAPE Ratio",
         "unit": ValueUnit.RATIO, "semantic_type": SemanticType.RATIO,
         "source": FieldSource.WEB, "frequency": DataFrequency.MONTHLY},
        {"field_id": "gold_oil_ratio", "display_name": "Gold/Oil Price Ratio",
         "unit": ValueUnit.RATIO, "semantic_type": SemanticType.RATIO,
         "source": FieldSource.COMPUTED, "is_computed": True},
        {"field_id": "deficit_pace_annualized", "display_name": "Annualized Fiscal Deficit Pace",
         "unit": ValueUnit.USD_BILLIONS, "semantic_type": SemanticType.FLOW,
         "source": FieldSource.COMPUTED, "is_computed": True},
        {"field_id": "net_liquidity", "display_name": "Net Liquidity",
         "unit": ValueUnit.USD_BILLIONS, "semantic_type": SemanticType.BALANCE,
         "source": FieldSource.COMPUTED, "is_computed": True,
         "dependencies": ["liquidity.fed_balance_sheet", "liquidity.tga", "liquidity.reverse_repo"]},
        {"field_id": "real_fed_funds_rate", "display_name": "Real Federal Funds Rate",
         "unit": ValueUnit.PERCENT, "semantic_type": SemanticType.RATE,
         "source": FieldSource.COMPUTED, "is_computed": True,
         "dependencies": ["rates.fed_funds", "inflation.cpi_yoy"]},
        {"field_id": "qqq_iwm_ratio", "display_name": "QQQ/IWM Large-Cap/Small-Cap Ratio",
         "unit": ValueUnit.RATIO, "semantic_type": SemanticType.RATIO,
         "source": FieldSource.COMPUTED, "is_computed": True},
        {"field_id": "consumer_confidence", "display_name": "Conference Board Consumer Confidence",
         "unit": ValueUnit.INDEX_POINTS, "semantic_type": SemanticType.INDEX,
         "source": FieldSource.WEB, "frequency": DataFrequency.MONTHLY},
        {"field_id": "cb_gold_purchases", "display_name": "Central Bank Gold Purchases",
         "unit": ValueUnit.TONS, "semantic_type": SemanticType.FLOW,
         "source": FieldSource.WEB, "frequency": DataFrequency.ANNUAL},
    ]

    for fd in _SEED_FIELDS:
        entry = FieldEntry(
            field_id=fd["field_id"],
            display_name=fd["display_name"],
            unit=fd.get("unit", ValueUnit.UNKNOWN),
            semantic_type=fd.get("semantic_type", SemanticType.LEVEL),
            source=fd.get("source", FieldSource.FRED),
            frequency=fd.get("frequency", DataFrequency.MONTHLY),
            kind=fd.get("kind", FieldKind.SCALAR),
            is_computed=fd.get("is_computed", False),
            dependencies=fd.get("dependencies", []),
            computation_description=fd.get("computation_description", ""),
        )
        registry.register(entry)

    return registry
