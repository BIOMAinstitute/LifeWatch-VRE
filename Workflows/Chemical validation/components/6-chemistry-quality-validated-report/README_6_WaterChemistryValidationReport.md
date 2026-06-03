# 6 — Water Chemistry Validation Report

Generates a validation report from the validated CSV files produced by
component 5. Produces a PDF report, an Excel file with failing samples
and an Excel file with all samples.

## Workflow position

```
WaterChemistryValidation  →  WaterChemistryValidationReport  →  Data2FinalReport
```

## Inputs

| Name | Type | Path | Description |
|------|------|------|-------------|
| input-data | Zip | `/mnt/inputs/water_chemical_data_level2_validated.zip` | Validated CSVs from component 5. |
| input-samples | Text | `/mnt/inputs/samplesInfo.xlsx` | SampleID → SamplingTypology mapping. Used to fill typology for REP samples and to define sample sort order in tables. |

## Outputs

| Name | Type | Path | Description |
|------|------|------|-------------|
| output-pdf | Text | `/mnt/outputs/validation_report.pdf` | Multi-page PDF with key indicators, 6 charts (3×2 grid on page 1) and a colour-coded validation table. |
| output-repeat | Text | `/mnt/outputs/Samples2Repeat.xlsx` | Excel with only the samples that failed (VAL = NO). Empty cells highlighted red. |
| output-all | Text | `/mnt/outputs/allFinalData.xlsx` | Excel with all samples. Empty cells highlighted red. |

## Parameters

None.

## Local execution

```bash
cp water_chemical_data_level2_validated.zip data/inputs/
cp samplesInfo.xlsx                          data/inputs/
./bin/build-image
./bin/execute
```

## data/execution-parameters.json

```json
{ "parameters": [] }
```

## PDF structure

| Page | Content |
|------|---------|
| 1 | Key indicators + 3×2 chart grid |
| 2 | Failure rate by sample — non-repeated (colour gradient, all samples) |
| 3 | Failure rate by sample — repeated (if REP samples exist) |
| 4+ | Colour-coded validation table per sample |

## Chart grid (page 1)

| | Left | Right |
|-|------|-------|
| Row 1 | Failed validations by month (NOREP vs REP) | Failure type breakdown |
| Row 2 | Validation outcome by sampling typology (stacked) | Heatmap: failure rate by typology × month |
| Row 3 | Failure rate by SiteCode (NOREP vs REP) | REP improvement rate by typology |

Charts comparing NOREP vs REP are only shown when REP samples exist.
Charts using typology data are only shown when `samplesInfo.xlsx` contains typology information.

## Notes

- The report compares two scenarios: **NOREP original** (base samples) and
  **NOREP replaced by REP** (same base samples but REP validation results
  substituted where a REP exists). This keeps sample counts identical.
- The REP improvement chart shows, for each typology, how many failed NOREP
  samples improved (NO → SI) vs stayed failed (NO → NO) when repeated.
  SI → NO transitions are impossible by design (passing samples are not repeated).
