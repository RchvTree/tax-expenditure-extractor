"""Draw a stratified random sample of output rows and create the manual review workbook.

Rows with a numeric amount are sampled separately so that amount extraction is
tested on enough real numbers. The seed is fixed so that anyone can reproduce the
same sample. An existing workbook is never overwritten, because it may contain
finished manual checks.
"""

import csv
import random
import sys
from pathlib import Path

from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.datavalidation import DataValidation

ROOT = Path(__file__).resolve().parent.parent
CSV_PATH = ROOT / "data" / "output" / "tax_expenditures.csv"
SHEET_PATH = ROOT / "eval" / "sample_check.xlsx"

SEED = 42
STATUS_REPORTED = "reported"
REPORTED_SAMPLE_SIZE = 10
OTHER_SAMPLE_SIZE = 5

# Columns reviewed on every sampled row.
CHECK_FIELDS = [
    "measure_id",
    "measure_name",
    "measure_type_raw",
    "measure_type",
    "fiscal_year",
    "revenue_forgone_amount",
    "amount_status",
    "source_page",
]
# Columns that hold one value for the whole report, so they are reviewed once.
DOCUMENT_FIELDS = ["country", "report_year", "currency", "amount_unit"]
ERROR_TYPES = "none,wrong_value,wrong_year,truncated_text,wrong_mapping,wrong_page,other"
INTEGER_FIELDS = {"revenue_forgone_amount", "source_page"}

INSTRUCTIONS = [
    "Manual review of a random sample against the source PDF",
    "",
    "1. Open data/input/australia_teis_2025-26.pdf and go to source_page (the PDF viewer's page number).",
    "2. Find the measure_id on that page and read the column for fiscal_year.",
    "3. In row_check, set every yellow *_ok cell to Y if the value matches the PDF, otherwise N.",
    "4. revenue_forgone_amount: when the PDF shows a symbol (*, .., -, nfp) or 'Included in', an empty cell is correct.",
    "5. amount_status: * = unquantifiable, .. = rounded_to_zero, - = nil, nfp = not_published,",
    "   'Included in' = included_elsewhere, a number = reported.",
    "6. measure_type: Exemption = exemption, Deduction = deduction, Concessional rate = reduced rate,",
    "   Offset or Rebate = credit, every other label = other.",
    "7. If any cell in a row is N, choose an error_type and write the correct value in correct_value_or_note.",
    "8. In document_check, confirm the four report-level values once.",
    "9. Save the workbook and run: python eval/score_sample.py",
]

HEADER_FILL = PatternFill("solid", fgColor="1F3864")
HEADER_FONT = Font(bold=True, color="FFFFFF")
INPUT_FILL = PatternFill("solid", fgColor="FFF2CC")
WRAP = Alignment(wrap_text=True, vertical="top")


def typed(field: str, value: str):
    """Show numeric fields as numbers and keep empty amounts empty."""
    if field in INTEGER_FIELDS and value != "":
        return int(value)
    return value if value != "" else None


def style_header(sheet) -> None:
    for cell in sheet[1]:
        cell.fill = HEADER_FILL
        cell.font = HEADER_FONT
        cell.alignment = WRAP
    sheet.freeze_panes = "B2"


def add_dropdown(sheet, options: str, cell_range: str) -> None:
    validation = DataValidation(type="list", formula1=f'"{options}"', allow_blank=True)
    sheet.add_data_validation(validation)
    validation.add(cell_range)


def build_row_sheet(workbook: Workbook, sample: list[dict]) -> None:
    sheet = workbook.create_sheet("row_check")
    header = ["sample_id"]
    for field in CHECK_FIELDS:
        header += [field, f"{field}_ok"]
    header += ["error_type", "correct_value_or_note"]
    sheet.append(header)

    for number, row in enumerate(sample, start=1):
        record = [number]
        for field in CHECK_FIELDS:
            record += [typed(field, row[field]), None]
        record += [None, None]
        sheet.append(record)

    last_row = len(sample) + 1
    for index, name in enumerate(header, start=1):
        letter = get_column_letter(index)
        sheet.column_dimensions[letter].width = 42 if name == "measure_name" else 16
        if name.endswith("_ok") or name in ("error_type", "correct_value_or_note"):
            for row_number in range(2, last_row + 1):
                sheet.cell(row=row_number, column=index).fill = INPUT_FILL
        if name.endswith("_ok"):
            add_dropdown(sheet, "Y,N", f"{letter}2:{letter}{last_row}")
        if name == "error_type":
            add_dropdown(sheet, ERROR_TYPES, f"{letter}2:{letter}{last_row}")
    sheet.column_dimensions[get_column_letter(len(header))].width = 40

    for row_cells in sheet.iter_rows(min_row=2):
        for cell in row_cells:
            cell.alignment = WRAP
    style_header(sheet)


def build_document_sheet(workbook: Workbook, first_row: dict) -> None:
    sheet = workbook.create_sheet("document_check")
    sheet.append(["field", "value", "ok", "note"])
    for field in DOCUMENT_FIELDS:
        sheet.append([field, first_row[field], None, None])
    last_row = len(DOCUMENT_FIELDS) + 1
    for row_number in range(2, last_row + 1):
        sheet.cell(row=row_number, column=3).fill = INPUT_FILL
    add_dropdown(sheet, "Y,N", f"C2:C{last_row}")
    for letter, width in zip("ABCD", (18, 18, 8, 40)):
        sheet.column_dimensions[letter].width = width
    style_header(sheet)


def main() -> int:
    if SHEET_PATH.exists():
        print(f"{SHEET_PATH.name} already exists. Move it first to draw a new sample.")
        return 1

    with CSV_PATH.open(encoding="utf-8-sig", newline="") as file:
        rows = list(csv.DictReader(file))

    reported = [row for row in rows if row["amount_status"] == STATUS_REPORTED]
    other = [row for row in rows if row["amount_status"] != STATUS_REPORTED]
    generator = random.Random(SEED)
    sample = generator.sample(reported, REPORTED_SAMPLE_SIZE) + generator.sample(other, OTHER_SAMPLE_SIZE)
    # Page order makes the manual review quicker and does not change the sample.
    sample.sort(key=lambda row: (int(row["source_page"]), row["measure_id"], row["fiscal_year"]))

    workbook = Workbook()
    guide = workbook.active
    guide.title = "instructions"
    for line in INSTRUCTIONS:
        guide.append([line])
    guide["A1"].font = Font(bold=True, size=13)
    guide.column_dimensions["A"].width = 115

    build_row_sheet(workbook, sample)
    build_document_sheet(workbook, rows[0])
    workbook.save(SHEET_PATH)
    print(f"Created {SHEET_PATH.name} with {len(sample)} rows (seed {SEED}).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
