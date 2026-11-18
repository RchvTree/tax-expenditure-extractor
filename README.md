# tax-expenditure-extractor

A small proof of concept that turns one public tax expenditure report from PDF into a standardised dataset, then measures the result against the source by hand.

**Input:** Australian Treasury, [2025–26 Tax Expenditures and Insights Statement](https://treasury.gov.au/sites/default/files/2025-12/p2025-721342.pdf), Appendix A.1 (PDF pages 63–207).

**Output:** 304 tax expenditure measures across 8 fiscal years (2,432 rows), as [CSV](data/output/tax_expenditures.csv) and [Excel](data/output/tax_expenditures.xlsx).

## How it works

```text
PDF download → text extraction → structured rows → validation → CSV + Excel export
                                                                       ↓
                                               random sample → manual check → accuracy report
```

| Step | File | What it does |
|---|---|---|
| Download | [src/download.py](src/download.py) | Downloads the PDF and verifies its SHA-256 checksum |
| Extract | [src/extract.py](src/extract.py) | Reads each measure block with layout rules |
| Transform | [src/transform.py](src/transform.py) | Standardises types and amounts, one row per measure and year |
| Validate | [src/validate.py](src/validate.py) | Checks completeness, formats and internal consistency |
| Export | [src/export.py](src/export.py) | Writes the CSV, Excel file and validation report |
| Evaluate | [eval/](eval/) | Samples rows for manual review and scores the answers |

Extraction is rule-based. The appendix uses one repeating layout, so no LLM is needed and every run gives the same output.

## How to run

Tested with Python 3.15.

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

python src/run_pipeline.py     # build the dataset
python eval/make_sample.py     # create eval/sample_check.xlsx
# complete the yellow cells in eval/sample_check.xlsx against the PDF
python eval/score_sample.py    # calculate accuracy and update this README
```

## Template definition

| Column | Type | Description |
|---|---|---|
| `country` | text | Country that published the report |
| `report_year` | text | Edition of the report |
| `measure_id` | text | Identifier of the measure in the report, for example `A1` |
| `measure_name` | text | Name of the measure as printed |
| `measure_type` | category | `deduction`, `exemption`, `reduced rate`, `credit` or `other` |
| `measure_type_raw` | text | Type label exactly as printed |
| `fiscal_year` | text | Fiscal year of the estimate, `2021-22` to `2028-29` |
| `revenue_forgone_amount` | integer | Published estimate in `amount_unit`. Empty unless `amount_status` is `reported`. Can be negative |
| `amount_status` | category | See the table below |
| `amount_raw` | text | Value exactly as printed |
| `included_in_measure_id` | text | Current ID of the measure holding this estimate, for `included_elsewhere` rows only |
| `amount_unit` | text | `million` |
| `currency` | text | `AUD` |
| `source_page` | integer | PDF page as numbered by a PDF viewer (printed page + 4) |

**`amount_status` values.** Symbols are never converted to 0, because most of them do not mean a cost of zero.

| Printed value | `amount_status` | Meaning in the report | Rows |
|---|---|---|---:|
| `*` | `unquantifiable` | Cannot be quantified | 1,175 |
| A number | `reported` | Point estimate | 1,039 |
| `..` | `rounded_to_zero` | Not zero but rounded to zero | 91 |
| `-` | `nil` | Nil | 75 |
| `Included in X` | `included_elsewhere` | Counted within another measure | 48 |
| `nfp` | `not_published` | Not for publication | 4 |

**`measure_type` mapping.** This mapping is a project decision and is not part of the report.

| Printed label | `measure_type` | Measures |
|---|---|---:|
| Exemption | `exemption` | 138 |
| Deduction | `deduction` | 28 |
| Concessional rate | `reduced rate` | 22 |
| Offset, Rebate | `credit` | 15 |
| All other labels, including combinations such as "Exemption, Deferral" | `other` | 101 |

## Validation results

All 7 automatic checks pass. The full output is in [data/output/validation_report.md](data/output/validation_report.md).

The measure count is compared with the counts published in the report's Table A1.1, for all 8 categories. These checks confirm that the output is complete and well formed. They do not confirm that each value matches the PDF, which is the purpose of the manual evaluation.

## Evaluation results

<!-- EVAL_RESULTS_START -->
Manual check of **15 rows** against the source PDF, drawn by stratified random sampling: 10 rows with a numeric amount and 5 rows without one.

- Cells correct: **120 of 120** (100.0%)
- Rows with every checked column correct: **15 of 15**

| Column | Numeric rows correct | Other rows correct | Sample accuracy | 95% Wilson interval, numeric rows |
|---|---:|---:|---:|---:|
| measure_id | 10/10 | 5/5 | 100.0% | 72.2% to 100.0% |
| measure_name | 10/10 | 5/5 | 100.0% | 72.2% to 100.0% |
| measure_type_raw | 10/10 | 5/5 | 100.0% | 72.2% to 100.0% |
| measure_type | 10/10 | 5/5 | 100.0% | 72.2% to 100.0% |
| fiscal_year | 10/10 | 5/5 | 100.0% | 72.2% to 100.0% |
| revenue_forgone_amount | 10/10 | 5/5 | 100.0% | 72.2% to 100.0% |
| amount_status | 10/10 | 5/5 | 100.0% | 72.2% to 100.0% |
| source_page | 10/10 | 5/5 | 100.0% | 72.2% to 100.0% |

Report-level values, checked once:

| Field | Value | Correct |
|---|---|---|
| country | Australia | Yes |
| report_year | 2025-26 | Yes |
| currency | AUD | Yes |
| amount_unit | million | Yes |

**Typical errors**

No errors were found in this sample.

Sample accuracy is unweighted and describes these sampled rows only. Numeric rows are deliberately over-represented, so it is not an estimate for the full dataset. The interval applies to rows with a numeric amount.
<!-- EVAL_RESULTS_END -->

**Method.** 15 rows are drawn by stratified random sampling with a fixed seed (42): 10 from the 1,039 rows with a numeric amount and 5 from the 1,393 rows without one. A person compares 8 columns of each row with the source PDF. The 4 report-level columns are checked once.

**Sampling decision.** The first design was a simple random sample of 15 rows from all 2,432 rows. That sample contained only 3 rows with a numeric amount (7 `unquantifiable`, 2 `rounded_to_zero`, 2 `nil` and 1 `included_elsewhere` made up the rest), which was too few to test amount extraction, the most important output of this project. The sample was therefore replaced with the stratified design above, keeping the review at 15 rows. The change was made after seeing the status mix of the first sample, but before any row had been compared with the PDF, so no accuracy result influenced it.

**Trade-offs of this design.** Numeric rows make up 67% of the sample and 43% of the dataset, so the overall sample accuracy is not an estimate for the full dataset. Results are therefore reported separately for numeric and other rows. All 5 other rows drawn are `unquantifiable`, so this sample does not test the `rounded_to_zero`, `nil`, `not_published` or `included_elsewhere` statuses.

## Known limitations

- The parser is written for this report's layout. Another country or edition needs new rules.
- Only Appendix A.1 is covered. Descriptions, reliability ratings, legislative references and the distributional tables in Chapter 2 are not extracted.
- 57% of rows (1,393 of 2,432) have no numeric amount, because the report gives a symbol or a reference. Summing the amount column does not give total revenue forgone.
- `measure_type` is a simplified mapping, and 101 of 304 measures fall into `other`.
- The report's "Included in X" references mix current IDs with 2024–25 codes. `included_in_measure_id` is resolved from the report's "estimates include" notes, which covers the 6 affected measures in this edition.
- The manual review covers only 15 of 2,432 rows and does not test every `amount_status` value.

## Data source and licence

Source: The Treasury, Commonwealth of Australia, *2025–26 Tax Expenditures and Insights Statement*, licensed under [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/).

The dataset in this repository is based on Commonwealth of Australia data. It has been restructured for this project and is not endorsed by the Commonwealth of Australia.
