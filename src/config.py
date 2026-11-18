"""Shared settings for the pipeline: source report, paths and the output template."""

from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# Source report. The checksum makes sure every run reads the exact same file.
PDF_URL = "https://treasury.gov.au/sites/default/files/2025-12/p2025-721342.pdf"
PDF_SHA256 = "f1b870f03776566c6303fe07b7588ebc2df925a8c285996a439632d2fc16050d"

# File locations.
PDF_PATH = ROOT / "data" / "input" / "australia_teis_2025-26.pdf"
OUTPUT_DIR = ROOT / "data" / "output"
CSV_PATH = OUTPUT_DIR / "tax_expenditures.csv"
XLSX_PATH = OUTPUT_DIR / "tax_expenditures.xlsx"
VALIDATION_REPORT_PATH = OUTPUT_DIR / "validation_report.md"

# Values that are the same for every row of this report.
COUNTRY = "Australia"
REPORT_YEAR = "2025-26"
CURRENCY = "AUD"
AMOUNT_UNIT = "million"

# PDF page numbers as shown by a PDF viewer (printed page number + 4).
CONTROL_TOTAL_PAGE = 61
FIRST_MEASURE_PAGE = 63
LAST_MEASURE_PAGE = 207

FISCAL_YEARS = [
    "2021-22", "2022-23", "2023-24", "2024-25",
    "2025-26", "2026-27", "2027-28", "2028-29",
]

# Table A1.1 category names and the letter that starts their measure IDs.
CATEGORY_PREFIXES = {
    "Personal income tax": "A",
    "Business income tax": "B",
    "Superannuation tax": "C",
    "Fringe benefits tax": "D",
    "Capital gains tax": "E",
    "Indirect taxes excluding GST": "F",
    "Natural resource taxes": "G",
    "Goods and services tax": "H",
}

# Labels with a direct match in the template. Every other known label becomes "other".
TYPE_MAPPING = {
    "Exemption": "exemption",
    "Deduction": "deduction",
    "Concessional rate": "reduced rate",
    "Offset": "credit",
    "Rebate": "credit",
}

# All labels used in this report. A label outside this list fails validation,
# which catches garbled text instead of silently calling it "other".
KNOWN_TYPE_LABELS = {
    "Exemption",
    "Deduction",
    "Concessional rate",
    "Deferral",
    "Accelerated write-off",
    "Increased rate",
    "Offset",
    "Reduction in taxable value",
    "Denial of deduction",
    "Exemption, Concessional rate",
    "Discounted valuation",
    "Rebate",
    "Exemption, Deferral",
    "Exemption, Reduction in taxable value",
    "Exemption, Offset, Concessional rate",
    "Record keeping exemption",
    "Exemption, Accelerated write-off, Deferral",
    "Exemption, Offset",
    "Deduction, Discounted valuation",
    "Exemption, Denial of deduction",
    "Deduction, Concessional rate",
    "Concessional rate, Increased rate",
    "Denial of deduction, Deferral of deduction",
    "Denial of refund",
}

MEASURE_TYPES = {"deduction", "exemption", "reduced rate", "credit", "other"}

# Symbols the report uses instead of a number (see PDF page 61).
# They are kept as statuses because none of them means a confirmed amount.
STATUS_BY_SYMBOL = {
    "*": "unquantifiable",
    "..": "rounded_to_zero",
    "-": "nil",
    "nfp": "not_published",
}
STATUS_REPORTED = "reported"
STATUS_INCLUDED = "included_elsewhere"
AMOUNT_STATUSES = {STATUS_REPORTED, STATUS_INCLUDED, *STATUS_BY_SYMBOL.values()}

# The output template: (column, type, description).
TEMPLATE = [
    ("country", "text", "Country that published the report."),
    ("report_year", "text", "Edition of the report."),
    ("measure_id", "text", "Identifier of the measure in the report, for example A1."),
    ("measure_name", "text", "Name of the measure as printed in the report."),
    ("measure_type", "category", "Standardised type: deduction, exemption, reduced rate, credit or other."),
    ("measure_type_raw", "text", "Type label exactly as printed in the report."),
    ("fiscal_year", "text", "Fiscal year of the estimate, from 2021-22 to 2028-29."),
    ("revenue_forgone_amount", "integer", "Published estimate in amount_unit. Empty unless amount_status is reported. Can be negative."),
    ("amount_status", "category", "reported, unquantifiable, rounded_to_zero, nil, not_published or included_elsewhere."),
    ("amount_raw", "text", "Value exactly as printed in the report."),
    ("included_in_measure_id", "text", "Current ID of the measure holding this estimate. Filled only when amount_status is included_elsewhere."),
    ("amount_unit", "text", "Unit of revenue_forgone_amount."),
    ("currency", "text", "ISO 4217 currency code."),
    ("source_page", "integer", "PDF page holding the estimate, as numbered by a PDF viewer (printed page + 4)."),
]
COLUMNS = [column for column, _, _ in TEMPLATE]
