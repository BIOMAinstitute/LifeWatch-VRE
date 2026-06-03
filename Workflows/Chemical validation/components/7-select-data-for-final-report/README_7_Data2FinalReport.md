# 7 — Data to Final Report

Selects the best available measurement per sample per month for ICP
programme reporting and database ingestion, applying a priority rule
to choose between original (NOREP) and replicate (REP) samples.

## Workflow position

```
WaterChemistryValidationReport  →  Data2FinalReport
```

## Inputs

| Name | Type | Path | Description |
|------|------|------|-------------|
| input-data | Text | `/mnt/inputs/allFinalData.xlsx` | All validated samples from component 6. Must include `VAL` (SI/NO) and `SampleID` columns. |
| input-samples | Text | `/mnt/inputs/samplesInfo.xlsx` | SampleID → ICP_Program / SamplingTypology / Instrument / ID_PostgreSQL mapping. |

## Outputs

| Name | Type | Path | Description |
|------|------|------|-------------|
| output-data | Text | `/mnt/outputs/data2report.xlsx` | One row per sample per month with the final chemistry columns, ready for ICP reporting and database ingestion. |

## Parameters

None.

## Local execution

```bash
cp allFinalData.xlsx data/inputs/
cp samplesInfo.xlsx  data/inputs/
./bin/build-image
./bin/execute
```

## data/execution-parameters.json

```json
{ "parameters": [] }
```

## Selection logic

For each unique combination of (base SampleID / year / month):

| Rule | Condition | Action |
|------|-----------|--------|
| 1 | NOREP passes (VAL = SI) | Keep NOREP |
| 2 | NOREP fails, REP passes | Keep REP |
| 3 | NOREP fails AND REP fails | Keep NOREP (both were attempted) |
| 4 | NOREP fails, no REP exists | Discard |

## Output columns

```
SampleID, SiteCode, SiteName, year, month,
CL(mg/l), SO4S(mg/l), NO3N(mg/l), PO4P(mg/l),
CA(mg/l), MG(mg/l), NA(mg/l), K(mg/l), AL(mg/l), FE(mg/l), MN(mg/l),
AS(mg/l), CD(mg/l), CR(mg/l), CU(mg/l), CO(mg/l), MO(mg/l), NI(mg/l),
PB(mg/l), ZN(mg/l), P(mg/l), S(mg/l),
NH4N(mg/l), TN(mg/l), DOC(mg/l),
H(µeq/l), WeightedConductivity(µS/cm), Volume(ml), Precip(l/m2),
WeightedpH, AlkalinityICPForests(µeq/l)
```

## Notes

- SampleID normalisation (`clean_id`): uppercase, remove spaces/hyphens/
  underscores. Applied consistently to both `allFinalData.xlsx` and
  `samplesInfo.xlsx` before merging.
- Columns from `samplesInfo.xlsx` that are added to the merged data:
  `ICP_Program`, `SamplingTypology`, `Instrument`, `ID_PostgreSQL`.
  Only columns actually present in `samplesInfo.xlsx` are merged.
- Columns missing from the input data are included as empty columns
  in the output (via `reindex`), so the output always has the full
  column set regardless of which subprograms were present.
