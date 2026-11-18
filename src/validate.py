"""Step 4: automatic checks on formats, missing fields and completeness.

These checks show that the output is well formed and complete. They cannot show
that each value matches the PDF, which is what the manual evaluation in eval/ measures.
"""

import re
from collections import Counter
from dataclasses import dataclass

import config

MEASURE_ID = re.compile(r"^[A-H]\d{1,3}$")
OPTIONAL_COLUMNS = {"revenue_forgone_amount", "included_in_measure_id"}
REQUIRED_COLUMNS = [c for c in config.COLUMNS if c not in OPTIONAL_COLUMNS]


@dataclass
class Check:
    name: str
    passed: bool
    detail: str


def make_check(name: str, problems: list, success_detail: str) -> Check:
    """Build a check result, showing the first few problems when it fails."""
    if problems:
        return Check(name, False, f"{len(problems)} problem(s), first: {problems[:3]}")
    return Check(name, True, success_detail)


def check_control_totals(rows: list[dict], control_totals: dict[str, int]) -> Check:
    """Compare measures found per category with the counts published in Table A1.1."""
    measure_ids = {row["measure_id"] for row in rows}
    found = Counter(measure_id[0] for measure_id in measure_ids)
    problems = [
        f"{prefix}: found {found[prefix]}, report says {expected}"
        for prefix, expected in control_totals.items()
        if found[prefix] != expected
    ]
    total = sum(control_totals.values())
    return make_check(
        "Measure counts match Table A1.1", problems, f"{len(measure_ids)} of {total} measures found"
    )


def check_row_count(rows: list[dict]) -> Check:
    per_measure = Counter(row["measure_id"] for row in rows)
    expected = len(config.FISCAL_YEARS)
    problems = [m for m, count in per_measure.items() if count != expected]
    return make_check("Each measure has one row per year", problems, f"{len(rows)} rows")


def check_unique_keys(rows: list[dict]) -> Check:
    keys = Counter((row["measure_id"], row["fiscal_year"]) for row in rows)
    problems = [key for key, count in keys.items() if count > 1]
    return make_check("No duplicate measure-year rows", problems, "All keys are unique")


def check_required_fields(rows: list[dict]) -> Check:
    problems = [
        (row["measure_id"], row["fiscal_year"], column)
        for row in rows
        for column in REQUIRED_COLUMNS
        if row[column] in (None, "")
    ]
    return make_check("Required fields are filled", problems, "No missing values")


def check_formats(rows: list[dict]) -> Check:
    problems = []
    for row in rows:
        key = (row["measure_id"], row["fiscal_year"])
        if not MEASURE_ID.match(row["measure_id"]):
            problems.append((key, "measure_id"))
        if row["fiscal_year"] not in config.FISCAL_YEARS:
            problems.append((key, "fiscal_year"))
        if row["measure_type"] not in config.MEASURE_TYPES:
            problems.append((key, "measure_type"))
        if row["measure_type_raw"] not in config.KNOWN_TYPE_LABELS:
            problems.append((key, "measure_type_raw"))
        if row["amount_status"] not in config.AMOUNT_STATUSES:
            problems.append((key, "amount_status"))
        if row["currency"] != config.CURRENCY or row["amount_unit"] != config.AMOUNT_UNIT:
            problems.append((key, "currency or unit"))
        if not config.FIRST_MEASURE_PAGE <= row["source_page"] <= config.LAST_MEASURE_PAGE:
            problems.append((key, "source_page"))
    return make_check("Formats and categories are valid", problems, "All values are in range")


def check_amount_status(rows: list[dict]) -> Check:
    """An amount must exist for reported rows and be empty for all other rows."""
    problems = [
        (row["measure_id"], row["fiscal_year"])
        for row in rows
        if (row["amount_status"] == config.STATUS_REPORTED)
        != isinstance(row["revenue_forgone_amount"], int)
    ]
    return make_check("Amount agrees with amount_status", problems, "All rows agree")


def check_included_references(rows: list[dict]) -> Check:
    """Included rows must point to another existing measure, and only they may do so."""
    measure_ids = {row["measure_id"] for row in rows}
    problems = []
    for row in rows:
        target = row["included_in_measure_id"]
        if row["amount_status"] != config.STATUS_INCLUDED:
            if target is not None:
                problems.append((row["measure_id"], "unexpected target", target))
        elif target not in measure_ids or target == row["measure_id"]:
            problems.append((row["measure_id"], row["amount_raw"], target))
    return make_check("'Included in' references resolve", problems, "All references resolve")


def run_checks(rows: list[dict], control_totals: dict[str, int]) -> list[Check]:
    return [
        check_control_totals(rows, control_totals),
        check_row_count(rows),
        check_unique_keys(rows),
        check_required_fields(rows),
        check_formats(rows),
        check_amount_status(rows),
        check_included_references(rows),
    ]
