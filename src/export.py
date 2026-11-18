"""Step 5: write the validated rows to CSV, Excel and a validation report."""

import csv
from collections import Counter

from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill

import config
from validate import Check

HEADER_FILL = PatternFill("solid", fgColor="1F3864")
HEADER_FONT = Font(bold=True, color="FFFFFF")
COLUMN_WIDTHS = {"measure_name": 60, "measure_type_raw": 28, "amount_raw": 18}
DEFAULT_WIDTH = 16


def write_csv(rows: list[dict]) -> None:
    # utf-8-sig lets Excel display characters such as the en dash correctly.
    with config.CSV_PATH.open("w", newline="", encoding="utf-8-sig") as file:
        writer = csv.DictWriter(file, fieldnames=config.COLUMNS)
        writer.writeheader()
        writer.writerows(rows)


def add_sheet(workbook: Workbook, title: str, header: list[str], records: list[list]):
    """Add a sheet with a styled header row and return it."""
    sheet = workbook.create_sheet(title)
    sheet.append(header)
    for record in records:
        sheet.append(record)
    for cell in sheet[1]:
        cell.fill = HEADER_FILL
        cell.font = HEADER_FONT
        cell.alignment = Alignment(vertical="center")
    sheet.freeze_panes = "A2"
    sheet.auto_filter.ref = sheet.dimensions
    return sheet


def write_excel(rows: list[dict], checks: list[Check]) -> None:
    workbook = Workbook()
    workbook.remove(workbook.active)

    data = add_sheet(
        workbook,
        "tax_expenditures",
        config.COLUMNS,
        [[row[column] for column in config.COLUMNS] for row in rows],
    )
    for index, column in enumerate(config.COLUMNS):
        letter = data.cell(row=1, column=index + 1).column_letter
        data.column_dimensions[letter].width = COLUMN_WIDTHS.get(column, DEFAULT_WIDTH)

    definition = add_sheet(
        workbook, "template_definition", ["column", "type", "description"],
        [list(item) for item in config.TEMPLATE],
    )
    definition.column_dimensions["A"].width = 26
    definition.column_dimensions["B"].width = 12
    definition.column_dimensions["C"].width = 95

    validation = add_sheet(
        workbook, "validation", ["check", "result", "detail"],
        [[c.name, "PASS" if c.passed else "FAIL", c.detail] for c in checks],
    )
    validation.column_dimensions["A"].width = 42
    validation.column_dimensions["B"].width = 10
    validation.column_dimensions["C"].width = 70

    workbook.save(config.XLSX_PATH)


def write_validation_report(rows: list[dict], checks: list[Check]) -> None:
    lines = [
        "# Validation report",
        "",
        "Automatic format and completeness checks. These do not measure accuracy against the PDF.",
        "",
        "| Check | Result | Detail |",
        "|---|---|---|",
    ]
    lines += [f"| {c.name} | {'PASS' if c.passed else 'FAIL'} | {c.detail} |" for c in checks]

    lines += ["", "## Rows by amount_status", "", "| amount_status | Rows | Share |", "|---|---:|---:|"]
    for status, count in Counter(row["amount_status"] for row in rows).most_common():
        lines.append(f"| {status} | {count} | {count / len(rows):.1%} |")

    measures = {row["measure_id"]: row["measure_type"] for row in rows}
    lines += ["", "## Measures by measure_type", "", "| measure_type | Measures |", "|---|---:|"]
    for measure_type, count in Counter(measures.values()).most_common():
        lines.append(f"| {measure_type} | {count} |")

    config.VALIDATION_REPORT_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")
