# 5 — Water Chemistry Validation

Merges per-subprogram CSV files by SiteCode, fills replicate sample metadata,
and computes a full set of chemical quality indicators following ICP-Forest
protocols. Produces a `FINAL_VALIDATION` flag (SI/NO) per sample.

## Workflow position

```
UnitTransformation  →  WaterChemistryValidation  →  WaterChemistryValidationReport
```

## Inputs

| Name | Type | Path | Description |
|------|------|------|-------------|
| input-data | Zip | `/mnt/inputs/water_chemical_data_level1_units.zip` | ZIP of unit-transformed CSVs from component 4. |
| input-samples | Text | `/mnt/inputs/samplesInfo.xlsx` | Excel file mapping SampleID → SamplingTypology. Required columns: `SampleID`, `SamplingTypology`. If absent, typology-dependent checks are skipped. |

## Outputs

| Name | Type | Path | Description |
|------|------|------|-------------|
| output-alldata | Zip | `/mnt/outputs/water_chemical_data_level2_alldata.zip` | Merged pre-validation CSV per SiteCode. |
| output-validated | Zip | `/mnt/outputs/water_chemical_data_level2_validated.zip` | Validated CSV per SiteCode with all quality indicator columns and `FINAL_VALIDATION` flag. |

## Parameters

| Name | Type | Default | Description |
|------|------|---------|-------------|
| param_ionsdiff_low_k | Float | `20.0` | Max IonsDiff% for WeightedConductivity ≤ 20 µS/cm |
| param_ionsdiff_high_k | Float | `10.0` | Max IonsDiff% for WeightedConductivity > 20 µS/cm |
| param_conddiff_low_1 | Float | `30.0` | Max CondDiff% for WeightedConductivity ≤ 10 µS/cm |
| param_conddiff_low_2 | Float | `20.0` | Max CondDiff% for WeightedConductivity 10–20 µS/cm |
| param_conddiff_high | Float | `10.0` | Max CondDiff% for WeightedConductivity > 20 µS/cm |
| param_ratio_nacl_low | Float | `0.5` | Lower bound of acceptable Na/Cl ratio |
| param_ratio_nacl_high | Float | `1.5` | Upper bound of acceptable Na/Cl ratio |

## Local execution

```bash
cp water_chemical_data_level1_units.zip data/inputs/
cp samplesInfo.xlsx                      data/inputs/
./bin/build-image
./bin/execute
```

## Quality indicators computed

| Column | Description |
|--------|-------------|
| `Metals_SW(µeq/l)` | Sum of Al+Fe+Mn for SW samples |
| `NDON(mg/l)` | TN - (NO3-N + NH4-N) |
| `Org-(µeq/l)` | Estimated organic anion from DOC (typology-dependent) |
| `SumAnions(µeq/l)` | Alkalinity + Cl + SO4S + NO3N |
| `SumCations(µeq/l)` | H + NH4N + Ca + Mg + Na + K + metals (SW) |
| `sC - sA IonsDiff.%` | Ionic balance without organic correction |
| `sC - sA - Org- IonsDiff.%` | Ionic balance with organic correction |
| `RatioNa/Cl` | Na/Cl molar ratio |
| `ConductivityCalculatedCorrected(µS/cm)` | Theoretical conductivity with ionic activity correction |
| `Cond. Diff.%Cc-Xm` | % difference between calculated and measured conductivity |
| `IonicStrenght(mol/l)` | Ionic strength (semi-empirical) |
| `FINAL_VALIDATION` | SI = passes all checks; NO = fails at least one |

## FINAL_VALIDATION logic

A sample is flagged NO when any of:
- BOF/WET typology AND organic-corrected ion balance fails
- Conductivity check fails
- OrgN check fails (TN < NO3-N + NH4-N)
- BOF/WET/THR/STF typology AND Na/Cl ratio fails
