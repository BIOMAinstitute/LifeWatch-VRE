# Water Chemistry Quality Validation and Reporting

This component receives the preprocessed chemical data produced by the previous workflow component, calculates and applies the chemical quality criteria, generates the review report and selects the final monthly dataset for ICP reporting.

## Internal sequence

```text
water_chemical_data_preprocessed.zip
        ↓
1. chemical_quality_validation.py
        ├── water_chemical_alldata_calculated.zip
        └── water_chemical_alldata_validated.zip
                    ↓
2. validation_report.py
        ├── validation_report.pdf
        ├── Samples2Repeat.xlsx
        └── All_Validated_Data.xlsx
                    ↓
3. data2final_report.py
                    ↓
              Final_Data.xlsx
```

`run_pipeline.py` only coordinates inputs, outputs, parameters and execution order. The scientific calculations and selection rules remain in the original scripts under `scripts/`.

## Inputs

- `/mnt/inputs/water_chemical_data_preprocessed.zip`: output ZIP from the combined preprocessing component (steps 2–4).
- `/mnt/inputs/samplesInfo.xlsx`: sample metadata reused by the three stages.

The original filename outside Docker does not matter when Tesseract mounts the selected input at the declared path. During manual testing, either mount the ZIP explicitly at `/mnt/inputs/water_chemical_data_preprocessed.zip` or mount an input directory containing a single `.zip`; the coordinator will also recognise the older `water_chemical_data_level1_units.zip` name for backward compatibility.

## Parameters

These parameters define the acceptance limits used by the chemical validation workflow. The ionic balance and conductivity-difference thresholds are applied according to the measured conductivity (WeightedConductivity), while the Na/Cl ratio thresholds define the acceptable interval for the sodium-to-chloride equivalent ratio. Samples exceeding these limits are flagged as failing the corresponding quality check.

The original seven quality thresholds are preserved:

| Parameter | Description | Default |
|-----------|-------------|--------:|
| `param_ionsdiff_low_k` | Maximum allowed absolute ionic balance difference (`IonsDiff.%`) for samples with measured conductivity ≤ 20 µS/cm. | 20.0 |
| `param_ionsdiff_high_k` | Maximum allowed absolute ionic balance difference (`IonsDiff.%`) for samples with measured conductivity > 20 µS/cm. | 10.0 |
| `param_conddiff_low_1` | Maximum allowed absolute difference between calculated and measured conductivity (`Cond. Diff.%Cc-Xm`) for samples with measured conductivity ≤ 10 µS/cm. | 30.0 |
| `param_conddiff_low_2` | Maximum allowed absolute difference between calculated and measured conductivity (`Cond. Diff.%Cc-Xm`) for samples with measured conductivity > 10 and ≤ 20 µS/cm. | 20.0 |
| `param_conddiff_high` | Maximum allowed absolute difference between calculated and measured conductivity (`Cond. Diff.%Cc-Xm`) for samples with measured conductivity > 20 µS/cm. | 10.0 |
| `param_ratio_nacl_low` | Lower acceptable limit of the Na/Cl equivalent ratio. | 0.5 |
| `param_ratio_nacl_high` | Upper acceptable limit of the Na/Cl equivalent ratio. | 1.5 |

All thresholds must be non-negative, and the lower Na/Cl ratio limit cannot exceed the upper limit.

## Outputs

All outputs are written directly under `/mnt/outputs`:

- `water_chemical_alldata_calculated.zip`: merged calculated data before quality-indicator columns are appended.
- `water_chemical_alldata_validated.zip`: calculated data with chemical quality indicators and `FINAL_VALIDATION`.
- `validation_report.pdf`: summary and detailed chemical validation report.
- `Samples2Repeat.xlsx`: samples whose final validation result requires review or repetition.
- `All_Validated_Data.xlsx`: consolidated sample-level data and validation results.
- `Final_Data.xlsx`: selected and monthly aggregated data prepared for ICP reporting.
- `pipeline_execution.log`: execution messages grouped by stage.

Existing public outputs are removed at the beginning of each run so that a failed stage cannot be mistaken for a successful run because of stale files from a previous execution.

## Code organisation

```text
scripts/
├── chemical_quality_validation.py
├── validation_report.py
└── data2final_report.py
```

## The detailed original documentation for each processing stage is preserved unchanged under `docs/`.

