"""Step 2: read the measure blocks in Appendix A.1 of the PDF.

Every measure is printed as the same block of lines:

    A1 Deduction for expenses incurred by election candidates     <- ID and name (1-2 lines)
    General public services - Legislative and executive ($m)      <- budget function and unit
    2021-22 2022-23 2023-24 2024-25 2025-26 2026-27 2027-28 ...   <- year header (the anchor)
    3 4 4 4 4 4 4 4                                               <- values
    Tax expenditure type: Deduction 2024-25 code: A1              <- type label

The parser finds each year header, then reads the lines around it.
Any block that does not fit this layout raises an error instead of being guessed.
"""

import re
from dataclasses import dataclass

import pdfplumber

import config

YEAR_HEADER = " ".join(config.FISCAL_YEARS)
MEASURE_START = re.compile(r"^([A-H]\d{1,3})\s+(.+)$")
TYPE_LINE = re.compile(r"^Tax expenditure type:\s*(.+?)\s+2024-25\b")
INCLUDED_IN = re.compile(r"^Included in [A-H]\d{1,3}$")
PRIOR_CODE_LINE = re.compile(r"2024-25\s*(?:code:\s*)?(.+)$")
INCLUDES_NOTE = re.compile(r"^Note: estimates include tax expenditures (.+)$")
MEASURE_CODE = re.compile(r"[A-H]\d{1,3}")

# How many lines to search around the year header before giving up.
MAX_HEADING_LINES = 4
MAX_TYPE_LINE_OFFSET = 3


@dataclass
class RawMeasure:
    """One measure as printed in the report, before any standardisation."""

    measure_id: str
    measure_name: str
    type_label: str
    values: list[str]
    source_page: int
    # Codes this measure had in the 2024-25 edition.
    prior_codes: list[str]
    # 2024-25 codes listed in this measure's "estimates include" note, if any.
    included_codes: list[str]


def read_lines(pdf_path) -> list[tuple[int, str]]:
    """Return (page number, line) pairs for the appendix, without page headers and footers."""
    lines = []
    with pdfplumber.open(pdf_path) as pdf:
        for page_number in range(config.FIRST_MEASURE_PAGE, config.LAST_MEASURE_PAGE + 1):
            text = pdf.pages[page_number - 1].extract_text() or ""
            # The first line is the running title and the last line is the page footer.
            # Joining pages this way also repairs blocks that continue on the next page.
            for line in text.split("\n")[1:-1]:
                lines.append((page_number, line.strip()))
    return lines


def read_control_totals(pdf_path) -> dict[str, int]:
    """Read the published number of measures per ID letter from Table A1.1."""
    with pdfplumber.open(pdf_path) as pdf:
        text = pdf.pages[config.CONTROL_TOTAL_PAGE - 1].extract_text() or ""

    totals = {}
    for category, prefix in config.CATEGORY_PREFIXES.items():
        match = re.search(rf"^{re.escape(category)} (\d+)$", text, re.MULTILINE)
        if match is None:
            raise ValueError(f"Category not found in Table A1.1: {category}")
        totals[prefix] = int(match.group(1))
    return totals


def parse_heading(lines: list[tuple[int, str]], year_index: int) -> tuple[str, str]:
    """Walk upwards from the year header to find the measure ID and full name."""
    # year_index - 1 is the budget function line, so the name ends just above it.
    unit_index = year_index - 1
    if not lines[unit_index][1].endswith("($m)"):
        raise ValueError(f"Expected a ($m) line on page {lines[unit_index][0]}.")

    for start in range(unit_index - 1, unit_index - 1 - MAX_HEADING_LINES, -1):
        match = MEASURE_START.match(lines[start][1])
        if match:
            name_parts = [match.group(2)] + [text for _, text in lines[start + 1:unit_index]]
            return match.group(1), " ".join(name_parts)
    raise ValueError(f"No measure ID found above the table on page {lines[year_index][0]}.")


def parse_values(text: str, page: int) -> list[str]:
    """Split the value line into one printed value per fiscal year."""
    # "Included in A43" is printed once but applies to every year.
    if INCLUDED_IN.match(text):
        return [text] * len(config.FISCAL_YEARS)

    values = text.split()
    if len(values) != len(config.FISCAL_YEARS):
        raise ValueError(f"Expected {len(config.FISCAL_YEARS)} values on page {page}: {text!r}")
    return values


def parse_type_label(lines: list[tuple[int, str]], values_index: int) -> str:
    """Find the type label printed just below the values."""
    for _, text in lines[values_index + 1 : values_index + 1 + MAX_TYPE_LINE_OFFSET]:
        match = TYPE_LINE.match(text)
        if match:
            return match.group(1)
    raise ValueError(f"No type label found on page {lines[values_index][0]}.")


def parse_prior_codes(lines: list[tuple[int, str]], values_index: int) -> list[str]:
    """Read the measure's 2024-25 code(s) from the type line."""
    for _, text in lines[values_index + 1 : values_index + 1 + MAX_TYPE_LINE_OFFSET]:
        if TYPE_LINE.match(text):
            return MEASURE_CODE.findall(PRIOR_CODE_LINE.search(text).group(1))
    return []


def extract_measures(pdf_path) -> list[RawMeasure]:
    """Parse every measure block in the appendix."""
    lines = read_lines(pdf_path)
    measures = []
    for index, (_, text) in enumerate(lines):
        # A note belongs to the measure block that is currently open.
        note = INCLUDES_NOTE.match(text)
        if note and measures:
            measures[-1].included_codes = MEASURE_CODE.findall(note.group(1))
            continue
        if text != YEAR_HEADER:
            continue
        values_page, values_text = lines[index + 1]
        measure_id, measure_name = parse_heading(lines, index)
        measures.append(
            RawMeasure(
                measure_id=measure_id,
                measure_name=measure_name,
                type_label=parse_type_label(lines, index + 1),
                values=parse_values(values_text, values_page),
                source_page=values_page,
                prior_codes=parse_prior_codes(lines, index + 1),
                included_codes=[],
            )
        )
    return measures
