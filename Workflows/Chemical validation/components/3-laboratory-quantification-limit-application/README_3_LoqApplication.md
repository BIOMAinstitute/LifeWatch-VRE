# 3 — LOQ Application

Applies the Limit of Quantification (LOQ) to water chemistry CSV files.
Values below the LOQ for a given element are replaced by **LOQ / 2**,
which is the standard half-LOQ substitution for left-censored analytical data.
Every substitution is recorded in a traceability log.

## Workflow position

```
WaterChemicalDataTransformation  →  LoqApplication  →  UnitTransformation
```

## Inputs

| Name | Type | Path | Description |
|------|------|------|-------------|
| input-data | Zip | `/mnt/inputs/water_chemical_data_level1.zip` | ZIP of tab-separated CSVs from component 2. Compatible with any CSV set using the same `{ANALYTE}(mg/l)` column naming convention. |

## Outputs

| Name | Type | Path | Description |
|------|------|------|-------------|
| output-data | Zip | `/mnt/outputs/water_chemical_data_level1_loq.zip` | Same CSVs with LOQ substitutions applied. |
| output-log | Text | `/mnt/outputs/level1_loq/loq_substitutions.log` | Tab-separated log: FILE, ROW, COLUMN, ORIGINAL_VALUE, LOQ, REPLACED_BY. |

## Parameters

Column names are matched **case-insensitively** — `NH4N(mg/l)`, `nh4n(mg/l)` and
`Nh4N(Mg/L)` all match. Original column casing is preserved in the output.

| Name | Type | Default | Description |
|------|------|---------|-------------|
| param_WeightedConductivity | Float | `3.0` | LOQ for weighted conductivity (µS/cm) |
| param_NH4N | Float | `0.04` | LOQ for NH4-N (mg/L) |
| param_NO3 | Float | `0.05` | LOQ for NO3 (mg/L) |
| param_SO4 | Float | `0.1` | LOQ for SO4 (mg/L) |
| param_CL | Float | `0.05` | LOQ for Cl (mg/L) |
| param_AS | Float | `0.000025` | LOQ for As (mg/L) |
| param_CD | Float | `0.000008` | LOQ for Cd (mg/L) |
| param_CR | Float | `0.000037` | LOQ for Cr (mg/L) |
| param_CU | Float | `0.000062` | LOQ for Cu (mg/L) |
| param_CO | Float | `0.00001` | LOQ for Co (mg/L) |
| param_NI | Float | `0.000073` | LOQ for Ni (mg/L) |
| param_PB | Float | `0.000011` | LOQ for Pb (mg/L) |
| param_ZN | Float | `0.000049` | LOQ for Zn (mg/L) |
| param_P | Float | `0.016603` | LOQ for P (mg/L) |
| param_S | Float | `0.5` | LOQ for S (mg/L) |
| param_CA | Float | `0.15` | LOQ for Ca (mg/L) |
| param_K | Float | `0.15` | LOQ for K (mg/L) |
| param_MG | Float | `0.03` | LOQ for Mg (mg/L) |
| param_NA | Float | `0.04` | LOQ for Na (mg/L) |
| param_AL | Float | `0.01` | LOQ for Al (mg/L) |
| param_FE | Float | `0.005` | LOQ for Fe (mg/L) |
| param_MN | Float | `0.005` | LOQ for Mn (mg/L) |
| param_DOC | Float | `0.5` | LOQ for DOC (mg/L) |
| param_TN | Float | `0.1` | LOQ for TN (mg/L) |

## Local execution

```bash
cp water_chemical_data_level1.zip data/inputs/
./bin/build-image
./bin/execute
```

## Notes

- LOQ values correspond to the detection limits of the ICP-Forest laboratory equipment.
- Columns not present in a given CSV are silently skipped.
- NaN values are ignored during the LOQ comparison.
