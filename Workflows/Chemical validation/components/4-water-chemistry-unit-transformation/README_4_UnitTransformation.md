# 4 — Unit Transformation

Converts water chemistry measurements to a standardised set of three units
per analyte: **mg/l**, **µg/l** and **µeq/l**. The transformation is
unit-agnostic: the input unit is detected from the column name
(e.g. `NH4N(µg/l)`) and converted accordingly.

Also handles paired cross-conversions:
- NH4 ↔ NH4N (ammonium / ammonium-nitrogen)
- NO3 ↔ NO3N (nitrate / nitrate-nitrogen)
- SO4 ↔ SO4S (sulphate / sulphate-sulphur)
- PO4 ↔ PO4P (phosphate / phosphate-phosphorus)

## Workflow position

```
LoqApplication  →  UnitTransformation  →  WaterChemistryValidation
```

## Inputs

| Name | Type | Path | Description |
|------|------|------|-------------|
| input-data | Zip | `/mnt/inputs/water_chemical_data_level1_loq.zip` | ZIP of LOQ-corrected CSVs from component 3. Compatible with any CSV set following the `{ANALYTE}({unit})` column naming convention. |

## Outputs

| Name | Type | Path | Description |
|------|------|------|-------------|
| output-data | Zip | `/mnt/outputs/water_chemical_data_level1_units.zip` | Same CSVs with three unit columns added per analyte. |

## Parameters

None. The transformation is fully deterministic from the column names and
built-in chemical constants (atomic weights, molecular weights, valences).

## Local execution

```bash
cp water_chemical_data_level1_loq.zip data/inputs/
./bin/build-image
./bin/execute
```

## data/execution-parameters.json

```json
{ "parameters": [] }
```

## Notes

- Supported input units: `mg/l`, `µg/l`, `ug/l`, `µeq/l`, `ueq/l`.
  Both `μ` (Greek mu, U+03BC) and `µ` (micro sign, U+00B5) are normalised.
- Column names are matched case-insensitively (`NH4N(mg/l)` = `nh4n(mg/l)`).
- If a column already exists in the output (e.g. `NH4(mg/l)` is already present
  and `NH4N(mg/l)` is also present), the existing column is preserved and not
  overwritten (`overwrite=False`).
- Columns that do not match any known analyte are left unchanged.
