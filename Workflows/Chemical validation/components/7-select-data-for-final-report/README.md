# 7 — Data to Final Report

Selects the best available measurement per sample per month and produces
the final clean dataset ready for ICP programme reporting and database
ingestion. This is the last step of the workflow — it applies a priority
rule to resolve the NOREP/REP choice for each sample, keeps only the
chemistry columns needed for reporting, and discards samples that failed
validation and were never repeated.

---

## Workflow position

```
WaterChemistryValidationReport  →  Data2FinalReport
```

---

## Inputs

| Name | Type | Path | Description |
|------|------|------|-------------|
| input-data | Text | `/mnt/inputs/allFinalData.xlsx` | All validated samples from component 6. Must contain at minimum the `SampleID`, `year`, `month` and `VAL` columns. |
| input-samples | Text | `/mnt/inputs/samplesInfo.xlsx` | SampleID metadata file. Used to bring in `ICP_Program`, `SamplingTypology`, `Instrument` and `ID_PostgreSQL`. |

### allFinalData.xlsx — required columns

The input Excel file must contain the following columns. All are present
in the `allFinalData.xlsx` produced by component 6 — no manual preparation
is needed if the data comes from that component.

**Identity and validation columns** (mandatory):

| Column | Description |
|--------|-------------|
| `SampleID` | Sample identifier (may include REP suffix) |
| `SiteCode` | Plot code |
| `SiteName` | Plot name |
| `year` | Year of collection |
| `month` | Month of collection (1–12) |
| `VAL` | Final validation flag: `SI` (passed) or `NO` (failed) |

**Chemistry columns** (included in the output if present):

| Column | Unit | Subprogram |
|--------|------|------------|
| `CL(mg/l)` | mg/L | ANIONS |
| `SO4S(mg/l)` | mg/L | ANIONS |
| `NO3N(mg/l)` | mg/L | ANIONS |
| `PO4P(mg/l)` | mg/L | ANIONS |
| `CA(mg/l)` | mg/L | CATIONS |
| `MG(mg/l)` | mg/L | CATIONS |
| `NA(mg/l)` | mg/L | CATIONS |
| `K(mg/l)` | mg/L | CATIONS |
| `AL(mg/l)` | mg/L | CATIONS |
| `FE(mg/l)` | mg/L | CATIONS |
| `MN(mg/l)` | mg/L | CATIONS |
| `AS(mg/l)` | mg/L | CATIONS |
| `CD(mg/l)` | mg/L | CATIONS |
| `CR(mg/l)` | mg/L | CATIONS |
| `CU(mg/l)` | mg/L | CATIONS |
| `CO(mg/l)` | mg/L | CATIONS |
| `MO(mg/l)` | mg/L | CATIONS |
| `NI(mg/l)` | mg/L | CATIONS |
| `PB(mg/l)` | mg/L | CATIONS |
| `ZN(mg/l)` | mg/L | CATIONS |
| `P(mg/l)` | mg/L | CATIONS |
| `S(mg/l)` | mg/L | CATIONS |
| `NH4N(mg/l)` | mg/L | AMMONIUM |
| `TN(mg/l)` | mg/L | DOC_TN |
| `DOC(mg/l)` | mg/L | DOC_TN |
| `H(µeq/l)` | µeq/L | pH/COND |
| `WeightedConductivity(µS/cm)` | µS/cm | pH/COND |
| `Volume(ml)` | mL | pH/COND |
| `Precip(l/m2)` | l/m² | pH/COND |
| `WeightedpH` | — | pH/COND |
| `AlkalinityICPForests(µeq/l)` | µeq/L | ALKALINITY |

If a column is absent from the input (e.g. the ALKALINITY subprogram was
not measured), it will appear as an empty column in the output — the output
always has the full fixed column set.

### samplesInfo.xlsx — required columns

| Column | Required | Description |
|--------|----------|-------------|
| `SampleID` | ✅ | Must match the SampleIDs in `allFinalData.xlsx` |
| `ICP_Program` | ⚠️ optional | Programme name (e.g. `ICP-Forest`, `ICP-IM`) |
| `SamplingTypology` | ⚠️ optional | Sampling type code |
| `Instrument` | ⚠️ optional | Instrument identifier |
| `ID_PostgreSQL` | ⚠️ optional | Database record identifier |

Only columns actually present in the file are merged. If a column is missing
from `samplesInfo.xlsx`, it is simply not added to the output.

---

## Outputs

| Name | Type | Path | Description |
|------|------|------|-------------|
| output-data | Text | `/mnt/outputs/data2report.xlsx` | One row per sample per month with the final chemistry columns, ready for ICP reporting and database ingestion. Sheet name: `Datos`. |

---

## Parameters

None. The selection logic is fixed and deterministic.

---

## Local execution (Windows PowerShell)

```powershell
cd "C:\path\to\7-data2final-report"

docker build -t data2final-report:0.0.1 .

docker run --rm `
  -v "${PWD}/resources/example/data/inputs:/mnt/inputs:ro" `
  -v "${PWD}/resources/example/data/outputs:/mnt/outputs" `
  data2final-report:0.0.1
```

## resources/example/data/execution-parameters.json

```json
{ "parameters": [] }
```

---

## Selection logic — choosing between NOREP and REP

The component groups all rows by `(base SampleID / year / month)` and applies
four rules in priority order. Only the first matching rule is applied.

The **base SampleID** is the SampleID with the `REP` suffix removed
(e.g. `05PSINT` for both `05PSINT` and `05PSINT_REP`).

| Rule | Condition | Action | Reason |
|------|-----------|--------|--------|
| 1 | NOREP exists AND `VAL = SI` | Keep NOREP | The original measurement passed — use it. |
| 2 | NOREP failed AND REP exists AND REP `VAL = SI` | Keep REP | The repetition improved the result — use the better measurement. |
| 3 | NOREP failed AND REP exists AND REP `VAL = NO` | Keep NOREP | Both failed — the sample was deliberately repeated and must be reported, but use the original. |
| 4 | NOREP failed AND no REP exists | Discard | Unvalidated data with no chance of recovery — not included in the final dataset. |

### Worked example

| SampleID | year | month | VAL | Selected? | Rule |
|----------|------|-------|-----|-----------|------|
| 05PSINT | 2025 | 1 | SI | ✅ Yes (as NOREP) | 1 |
| 05PSINT | 2025 | 2 | NO | — | — |
| 05PSINT_REP | 2025 | 2 | SI | ✅ Yes (as REP) | 2 |
| 05PSINT | 2025 | 3 | NO | ✅ Yes (as NOREP) | 3 |
| 05PSINT_REP | 2025 | 3 | NO | — | — |
| 05PSINT | 2025 | 4 | NO | ❌ Discarded | 4 |

In the output, month 2 is represented by the REP row, month 3 by the NOREP
row (both failed), and month 4 is absent.

### SampleID normalisation

Before the grouping, all SampleIDs are normalised:
- Converted to uppercase
- Spaces, hyphens and underscores removed

This ensures that `05PS INT`, `05PS-INT` and `05PSINT` are treated as the same
sample, and that `05PSINT_REP`, `05PS INT REP` and `05PSINT REP` are all
correctly identified as REP samples of the same base.

---

## Notes

- The output always contains the full fixed set of 36 chemistry columns
  regardless of which subprograms were measured. Missing subprogram columns
  appear as empty cells in the output Excel file.
- Metadata columns from `samplesInfo.xlsx` (`ICP_Program`, `SamplingTypology`,
  `Instrument`, `ID_PostgreSQL`) are not included in the final output column
  set — they are only used internally during the merge step and then dropped.
  If you need these columns in the output, the script would need to be modified.
- The output file has a single sheet named `Datos`.
