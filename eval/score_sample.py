"""Score the completed manual review and publish the results.

Results are calculated only from the reviewer's Y/N answers. The script stops if
any answer is missing, so a partly reviewed sample can never produce a score.
"""

import csv
import math
import re
import sys
from collections import defaultdict
from pathlib import Path

from openpyxl import load_workbook

from make_sample import CHECK_FIELDS, ROOT, SHEET_PATH, STATUS_REPORTED

RESULTS_MD = ROOT / "eval" / "eval_results.md"
RESULTS_CSV = ROOT / "eval" / "column_accuracy.csv"
README_PATH = ROOT / "README.md"
README_BLOCK = re.compile(
    r"(<!-- EVAL_RESULTS_START -->\n).*?(\n<!-- EVAL_RESULTS_END -->)", re.DOTALL
)
Z_95 = 1.96


def wilson_interval(correct: int, total: int) -> tuple[float, float]:
    """95% Wilson score interval, which stays meaningful for small samples."""
    share = correct / total
    denominator = 1 + Z_95**2 / total
    centre = (share + Z_95**2 / (2 * total)) / denominator
    margin = Z_95 * math.sqrt(share * (1 - share) / total + Z_95**2 / (4 * total**2)) / denominator
    return max(0.0, centre - margin), min(1.0, centre + margin)


def read_sheet(sheet) -> list[dict]:
    """Return the sheet rows as dictionaries keyed by the header."""
    records = list(sheet.iter_rows(values_only=True))
    header = records[0]
    return [dict(zip(header, record)) for record in records[1:] if record[0] is not None]


def find_incomplete(rows: list[dict], documents: list[dict]) -> list[str]:
    """List every answer that is missing or inconsistent."""
    problems = []
    for row in rows:
        sample_id = row["sample_id"]
        answers = [row[f"{field}_ok"] for field in CHECK_FIELDS]
        problems += [
            f"sample {sample_id}: {field}_ok must be Y or N"
            for field, answer in zip(CHECK_FIELDS, answers)
            if answer not in ("Y", "N")
        ]
        if "N" in answers and row["error_type"] in (None, "none"):
            problems.append(f"sample {sample_id}: choose an error_type for the N answer")
    problems += [
        f"document_check: {doc['field']} must be Y or N"
        for doc in documents
        if doc["ok"] not in ("Y", "N")
    ]
    return problems


def score_columns(rows: list[dict]) -> list[dict]:
    """Score each column separately for the two sampling groups."""
    reported = [row for row in rows if row["amount_status"] == STATUS_REPORTED]
    other = [row for row in rows if row["amount_status"] != STATUS_REPORTED]

    results = []
    for field in CHECK_FIELDS:
        reported_correct = sum(row[f"{field}_ok"] == "Y" for row in reported)
        other_correct = sum(row[f"{field}_ok"] == "Y" for row in other)
        all_correct = reported_correct + other_correct
        low, high = wilson_interval(reported_correct, len(reported))
        results.append(
            {
                "column": field,
                "reported_correct": reported_correct,
                "reported_checked": len(reported),
                "other_correct": other_correct,
                "other_checked": len(other),
                "sample_correct": all_correct,
                "sample_checked": len(rows),
                "sample_accuracy": all_correct / len(rows),
                "reported_ci_low": low,
                "reported_ci_high": high,
            }
        )
    return results


def summarise_errors(rows: list[dict]) -> list[tuple]:
    """Group wrong cells by error type and column."""
    groups = defaultdict(list)
    for row in rows:
        for field in CHECK_FIELDS:
            if row[f"{field}_ok"] == "N":
                groups[(row["error_type"], field)].append(row["correct_value_or_note"] or "")
    ordered = sorted(groups.items(), key=lambda item: -len(item[1]))
    return [(kind, field, len(notes), notes[0]) for (kind, field), notes in ordered]


def build_markdown(rows: list[dict], documents: list[dict], results: list[dict]) -> str:
    cells = sum(item["sample_checked"] for item in results)
    correct_cells = sum(item["sample_correct"] for item in results)
    clean_rows = sum(all(r[f"{f}_ok"] == "Y" for f in CHECK_FIELDS) for r in rows)
    reported_rows = results[0]["reported_checked"]
    other_rows = results[0]["other_checked"]

    lines = [
        f"Manual check of **{len(rows)} rows** against the source PDF, drawn by stratified "
        f"random sampling: {reported_rows} rows with a numeric amount and {other_rows} rows without one.",
        "",
        f"- Cells correct: **{correct_cells} of {cells}** ({correct_cells / cells:.1%})",
        f"- Rows with every checked column correct: **{clean_rows} of {len(rows)}**",
        "",
        "| Column | Numeric rows correct | Other rows correct | Sample accuracy | 95% Wilson interval, numeric rows |",
        "|---|---:|---:|---:|---:|",
    ]
    lines += [
        f"| {r['column']} | {r['reported_correct']}/{r['reported_checked']} "
        f"| {r['other_correct']}/{r['other_checked']} | {r['sample_accuracy']:.1%} "
        f"| {r['reported_ci_low']:.1%} to {r['reported_ci_high']:.1%} |"
        for r in results
    ]

    lines += ["", "Report-level values, checked once:", "", "| Field | Value | Correct |", "|---|---|---|"]
    lines += [
        f"| {d['field']} | {d['value']} | {'Yes' if d['ok'] == 'Y' else 'No'} |" for d in documents
    ]

    lines += ["", "**Typical errors**", ""]
    errors = summarise_errors(rows)
    if errors:
        lines += ["| Error type | Column | Cells | Example |", "|---|---|---:|---|"]
        lines += [f"| {kind} | {field} | {count} | {note} |" for kind, field, count, note in errors]
    else:
        lines.append("No errors were found in this sample.")

    lines += [
        "",
        "Sample accuracy is unweighted and describes these sampled rows only. Numeric rows are "
        "deliberately over-represented, so it is not an estimate for the full dataset. The "
        "interval applies to rows with a numeric amount.",
    ]
    return "\n".join(lines)


def main() -> int:
    if not SHEET_PATH.exists():
        print("eval/sample_check.xlsx not found. Run eval/make_sample.py first.")
        return 1

    workbook = load_workbook(SHEET_PATH, data_only=True)
    rows = read_sheet(workbook["row_check"])
    documents = read_sheet(workbook["document_check"])

    problems = find_incomplete(rows, documents)
    if problems:
        print(f"Review is not complete ({len(problems)} open item(s)). No results were written.")
        for problem in problems[:10]:
            print(f"- {problem}")
        return 1

    results = score_columns(rows)
    with RESULTS_CSV.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=list(results[0]))
        writer.writeheader()
        writer.writerows(results)

    markdown = build_markdown(rows, documents, results)
    RESULTS_MD.write_text(f"# Evaluation results\n\n{markdown}\n", encoding="utf-8")

    readme = README_PATH.read_text(encoding="utf-8")
    README_PATH.write_text(
        README_BLOCK.sub(lambda m: m.group(1) + markdown + m.group(2), readme), encoding="utf-8"
    )
    print(f"Wrote {RESULTS_MD.name}, {RESULTS_CSV.name} and updated README.md.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
