# 2 — Water Chemical Data Transformation

Transforms validated Excel templates into analysis-ready tab-separated CSV
files grouped by SiteCode. Handles three transformation types:

- **ALKALINITY** — computes alkalinity via linear regression on 4 pH reference points.
- **pH_COND_WEIGHTED_RAW** — computes volume-weighted pH, conductivity, hydron and precipitation.
- **AMMONIUM / ANIONS / CATIONS / DOC_TN** — consolidates and deduplicates rows.

## Workflow position

```
InputDataFormatValidation  →  WaterChemicalDataTransformation  →  LoqApplication
```

## Inputs

| Name | Type | Path | Description |
|------|------|------|-------------|
| input-data | Zip | `/mnt/inputs/allData_templates_format_validated.zip` | Validated Excel ZIP from component 1. |

## Outputs

| Name | Type | Path | Description |
|------|------|------|-------------|
| output-data | Zip | `/mnt/outputs/water_chemical_data_level1.zip` | ZIP of tab-separated CSVs, one per SiteCode per subprogram. |

## Parameters

None.

## Local execution

```bash
cp allData_templates_format_validated.zip data/inputs/
./bin/build-image
./bin/execute
```

## data/execution-parameters.json

```json
{ "parameters": [] }
```

## Notes

- SiteCode is read from the **content** of each Excel file (column `SiteCode`),
  not from the filename. Each file may contain multiple SiteCodes.
- Files are identified by subprogram keyword in their name:
  `ALKALINITY`, `PH_COND_WEIGHTED_RAW`, `AMMONIUM`, `ANIONS`, `CATIONS`, `DOC_TN`.
- Replicate files (containing `_REP_` in the name) have `_REP` appended to
  all SampleIDs in that file.
- Output filenames follow the pattern `<SiteCode>_WATER_<SUBPROGRAM>.csv`.
- The alkalinity regression uses reference pH points `[4, 4.2, 4.3, 4.5]`.
