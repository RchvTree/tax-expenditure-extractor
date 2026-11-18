# Evaluation results

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
