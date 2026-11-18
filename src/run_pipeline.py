"""Run the full pipeline: download, extract, transform, validate, export."""

import sys

import config
from download import download_pdf
from export import write_csv, write_excel, write_validation_report
from extract import extract_measures, read_control_totals
from transform import build_rows
from validate import run_checks


def main() -> int:
    download_pdf()

    measures = extract_measures(config.PDF_PATH)
    print(f"Extracted measures: {len(measures)}")

    rows = build_rows(measures)
    print(f"Template rows: {len(rows)}")

    checks = run_checks(rows, read_control_totals(config.PDF_PATH))
    for check in checks:
        print(f"[{'PASS' if check.passed else 'FAIL'}] {check.name}: {check.detail}")

    # The report is always written so that a failed run can be inspected.
    config.OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    write_validation_report(rows, checks)

    if not all(check.passed for check in checks):
        print("Validation failed, so no data files were exported.")
        return 1

    write_csv(rows)
    write_excel(rows, checks)
    print(f"Exported: {config.CSV_PATH.name}, {config.XLSX_PATH.name}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
