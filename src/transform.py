"""Step 3: turn raw measures into template rows, one row per measure and fiscal year."""

import re

import config
from extract import RawMeasure

# Whole numbers with optional thousands separators, for example 4, -560 or 11,200.
NUMBER = re.compile(r"^-?\d{1,3}(?:,\d{3})*$")


def parse_amount(raw_value: str) -> tuple[int | None, str]:
    """Return (amount, status) for one printed value.

    Symbols such as "*" stay empty. Converting them to 0 would claim a cost
    of zero for measures the report says it cannot quantify.
    """
    if raw_value in config.STATUS_BY_SYMBOL:
        return None, config.STATUS_BY_SYMBOL[raw_value]
    if raw_value.startswith("Included in "):
        return None, config.STATUS_INCLUDED
    if NUMBER.match(raw_value):
        return int(raw_value.replace(",", "")), config.STATUS_REPORTED
    raise ValueError(f"Unrecognised value: {raw_value!r}")


def standardise_type(type_label: str) -> str:
    """Map a printed type label to one of the five template categories."""
    return config.TYPE_MAPPING.get(type_label, "other")


def resolve_included_targets(measures: list[RawMeasure]) -> dict[str, str | None]:
    """Find which current measure holds the estimate of each "Included in" measure.

    The printed "Included in X" cannot be trusted as a current ID: X is sometimes
    a 2024-25 code that now belongs to a different measure. The "estimates include"
    note on the receiving measure is unambiguous, so it decides the target.
    """
    owner_by_code = {
        code: measure.measure_id for measure in measures for code in measure.included_codes
    }
    targets = {}
    for measure in measures:
        if measure.values[0].startswith("Included in "):
            owners = [owner_by_code[c] for c in measure.prior_codes if c in owner_by_code]
            targets[measure.measure_id] = owners[0] if owners else None
    return targets


def build_rows(measures: list[RawMeasure]) -> list[dict]:
    """Expand each measure into one row per fiscal year."""
    targets = resolve_included_targets(measures)
    rows = []
    for measure in measures:
        for fiscal_year, raw_value in zip(config.FISCAL_YEARS, measure.values):
            amount, status = parse_amount(raw_value)
            rows.append(
                {
                    "country": config.COUNTRY,
                    "report_year": config.REPORT_YEAR,
                    "measure_id": measure.measure_id,
                    "measure_name": measure.measure_name,
                    "measure_type": standardise_type(measure.type_label),
                    "measure_type_raw": measure.type_label,
                    "fiscal_year": fiscal_year,
                    "revenue_forgone_amount": amount,
                    "amount_status": status,
                    "amount_raw": raw_value,
                    "included_in_measure_id": targets.get(measure.measure_id),
                    "amount_unit": config.AMOUNT_UNIT,
                    "currency": config.CURRENCY,
                    "source_page": measure.source_page,
                }
            )
    return rows
