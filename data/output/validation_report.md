# Validation report

Automatic format and completeness checks. These do not measure accuracy against the PDF.

| Check | Result | Detail |
|---|---|---|
| Measure counts match Table A1.1 | PASS | 304 of 304 measures found |
| Each measure has one row per year | PASS | 2432 rows |
| No duplicate measure-year rows | PASS | All keys are unique |
| Required fields are filled | PASS | No missing values |
| Formats and categories are valid | PASS | All values are in range |
| Amount agrees with amount_status | PASS | All rows agree |
| 'Included in' references resolve | PASS | All references resolve |

## Rows by amount_status

| amount_status | Rows | Share |
|---|---:|---:|
| unquantifiable | 1175 | 48.3% |
| reported | 1039 | 42.7% |
| rounded_to_zero | 91 | 3.7% |
| nil | 75 | 3.1% |
| included_elsewhere | 48 | 2.0% |
| not_published | 4 | 0.2% |

## Measures by measure_type

| measure_type | Measures |
|---|---:|
| exemption | 138 |
| other | 101 |
| deduction | 28 |
| reduced rate | 22 |
| credit | 15 |
