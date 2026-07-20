# 6 — Water Chemistry Validation Report

Generates a validation report from the validated CSV files produced by
component 5. The report summarises which samples passed or failed validation,
compares original samples against their replicates, and identifies patterns
by typology, site and month. No new scientific analysis is performed here —
this component reads the quality flags computed in component 5 and presents
them visually and in tabular form.

---

## Workflow position

```
WaterChemistryValidation  →  WaterChemistryValidationReport  →  Data2FinalReport
```

---

## Inputs

| Name | Type | Path | Description |
|------|------|------|-------------|
| input-data | Zip | `/mnt/inputs/water_chemical_data_level2_validated.zip` | ZIP of validated tab-separated CSV files from component 5. One CSV per SiteCode. |
| input-samples | Text | `/mnt/inputs/samplesInfo.xlsx` | SampleID → SamplingTypology mapping. Used to fill typology for REP samples and to define the sample sort order in report tables. |

### Required columns in the validated CSVs

The component reads the following columns from each validated CSV. All are
produced by component 5 — no manual preparation is needed if the data comes
from that component.

**Identity columns** (always required):

| Column | Description |
|--------|-------------|
| `SampleID` | Sample identifier |
| `SiteCode` | Plot code |
| `SiteName` | Plot name |
| `year` | Year of collection |
| `month` | Month of collection (1–12) |

**Quality flag columns** (required for the report):

| Column | Values | Used for |
|--------|--------|----------|
| `FINAL_VALIDATION` | `SI` / `NO` | All charts, tables and indicators |
| `sC - sA - Org- QualityIonsBalance` | `ok` / `NO` | Failure type chart, table |
| `QualityConductivity` | `ok` / `NO` | Failure type chart, table |
| `QualityOrgN` | `ok` / `NO TN` | Failure type chart, table |
| `QualityRatioNa/Cl` | `ok` / `NO` | Failure type chart, table |
| `SamplingTypology` | text | Typology charts (if available) |

**Optional columns** (used when available, ignored if absent):

| Column | Used for |
|--------|----------|
| `WeightedConductivity(µS/cm)` | Key indicators |
| `WeightedpH` | Key indicators |

---

## Outputs

| Name | Type | Path | Description |
|------|------|------|-------------|
| output-pdf | Text | `/mnt/outputs/validation_report.pdf` | Multi-page PDF report (see structure below). |
| output-repeat | Text | `/mnt/outputs/Samples2Repeat.xlsx` | Excel with only the samples that failed validation (FINAL_VALIDATION = NO). Empty cells highlighted red. |
| output-all | Text | `/mnt/outputs/allFinalData.xlsx` | Excel with all samples regardless of outcome. Empty cells highlighted red. |

---

## Parameters

None.

---

## Local execution (Windows PowerShell)

```powershell
cd "C:\path\to\6-chemistry-quality-validated-report"

docker build -t chemistry-quality-validated-report:0.0.1 .

docker run --rm `
  -v "${PWD}/resources/example/data/inputs:/mnt/inputs:ro" `
  -v "${PWD}/resources/example/data/outputs:/mnt/outputs" `
  chemistry-quality-validated-report:0.0.1
```

## resources/example/data/execution-parameters.json

```json
{ "parameters": [] }
```

---

## PDF structure

### Page 1 — Summary dashboard

Contains two key indicator tables and a **3×2 chart grid**.

**Key indicator tables** show summary statistics for two scenarios
(see NOREP vs REP comparison below):
- Total records, unique samples, sites, validated periods
- Failed records, passed records, failure rate, unknown VAL

**3×2 chart grid:**

| Position | Chart | Shown when |
|----------|-------|------------|
| Row 1 left | Failed validations by month — bar chart (NOREP vs REP) | Always |
| Row 1 right | Failure type breakdown — bar chart (NOREP vs REP) | Always |
| Row 2 left | Validation outcome by sampling typology — stacked bars (NOREP vs REP) | Typology data available |
| Row 2 right | Heatmap: failure rate % by typology × month | Typology data available |
| Row 3 left | Failure rate by SiteCode — horizontal bars (NOREP vs REP) | SiteCode data available |
| Row 3 right | REP improvement rate by typology | REP samples exist + typology available |

When REP samples do not exist, all "vs REP" comparisons are replaced by
single-scenario charts with simplified titles. When typology data is absent,
the typology and heatmap charts show a placeholder.

### Page 2 — Failure rate by non-repeated sample

One horizontal bar per sample (all samples, not just top N), sorted by
failure rate % from highest to lowest. Bar colour is a red-to-green gradient
(red = 100% fail, green = 0% fail). Total record count shown per sample.
Labels include the SamplingTypology when available.

### Page 3 — Failure rate by repeated (REP) sample

Same chart as page 2 but showing only REP samples. Only included when
REP samples exist in the data.

### Page 4+ — Colour-coded validation table

One row per sample per month, sorted by year, month and SampleID order from
`samplesInfo.xlsx`. Columns: SampleID, month, Type (typology), Ions balance Org,
Conductivity, OrgN, Ratio Na/Cl, REP (whether the sample is a replicate),
VAL (FINAL_VALIDATION).

Colour coding per cell:
- 🔴 Red: `NO` or `NO TN` — failed check
- 🟢 Green: `ok` or `SI` — passed check
- 🟠 Orange: `Rep` — replicate sample marker
- White: all other values

The table continues across as many pages as needed.

---

## Excel output columns

Both `Samples2Repeat.xlsx` and `allFinalData.xlsx` contain the same column
set, drawn from the validated CSV. Key columns included:

```
SampleID, SiteCode, SiteName, Type (SamplingTypology), year, month,
CL(mg/l), SO4S(mg/l), NO3N(mg/l), CA(mg/l), MG(mg/l), NA(mg/l), K(mg/l),
AL(mg/l), FE(mg/l), MN(mg/l), NH4N(mg/l), TN(mg/l), DOC(mg/l),
WeightedpH, WeightedConductivity(µS/cm), Volume(ml), Precip(l/m2),
AlkalinityICPForests(µeq/l), Metals_SW(µeq/l), NDON(mg/l), Org-(µeq/l),
SumAnions(µeq/l), +Org(µeq/l), H(µeq/l), SumCations(µeq/l),
sC - sA IonsDiff.%, sC - sA QualityIonsBalance,
sC - sA - Org- IonsDiff.%, IonsDiffOrg.Limit(%), IonsDiffOrg.OverLimit.pp,
IonsDiffOrg.OverLimit.relative%, RatioNa/Cl,
ConductivityCalculatedWithoutCorrection(µS/cm), IonicStrenght(mol/l),
IonicActivityFactor, ConductivityCalculatedCorrected(µS/cm),
Cond. Diff.%Cc-Xm, Ions balance Org, Ratio Na/Cl, Conductivity, OrgN, VAL
```

`Samples2Repeat.xlsx` contains only the rows where `FINAL_VALIDATION = NO`.
`allFinalData.xlsx` contains all rows regardless of outcome.

Both files are sorted by year → month → SampleID (order from `samplesInfo.xlsx`).
Empty cells are highlighted in red in both files.

---

## NOREP vs REP comparison

The report compares two paired scenarios to assess whether repeating a
sample improves validation outcomes:

**NOREP original:** validation results from the original non-replicate samples.

**NOREP replaced by REP:** the same set of base samples, but for each sample
where a REP exists, the validation result (`FINAL_VALIDATION` and all quality
flags) is replaced by the REP result. The number of samples is identical in
both scenarios — only the validation results change.

This comparison answers: *"For the samples that were repeated, did the
repetition improve the result?"*

**REP improvement chart** (page 1, row 3 right): for each typology, shows
how many of the samples that failed as NOREP then:
- Improved when repeated: NO → SI
- Did not improve: NO → NO
- Had no REP available

Note: SI → NO transitions are impossible by design — if a sample already
passed validation it is never repeated.

---

## Notes

- `samplesInfo.xlsx` is optional but strongly recommended. Without it:
  typology-based charts are empty, and the sample sort order in tables falls
  back to alphabetical by SampleID.
- All CSV files in the input ZIP are merged into a single dataset before
  generating the report. Duplicate rows (same SampleID + month) are resolved
  by keeping the row with the fewest NaN values.
- Rows with empty, NaN or `"NA"` SampleID are excluded from all outputs.
