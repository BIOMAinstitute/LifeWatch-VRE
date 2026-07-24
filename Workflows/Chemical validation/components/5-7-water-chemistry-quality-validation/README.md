# Water Chemistry Quality Validation and Reporting (steps 5–7)

This component executes the original water-chemistry components **5, 6 and 7** sequentially while keeping their scientific logic in three separate scripts. It receives the preprocessed chemical data produced by the previous workflow component, calculates and applies the chemical quality criteria, generates the review report and selects the final monthly dataset for ICP reporting.

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


### Canonical fields in `Final_Data.xlsx`

To avoid duplicate representations, the final file retains only `StartDate` and
`EndDate` for dates, `Precip(l/m2)` for precipitation, and
`AlkalinityICPForests(µeq/l)` for alkalinity. Database-specific names such as
`date_1`, `date_2` and `Precipitation (mm)` should be assigned during database
loading. `Alkalinity (mg/l)` and `Deposition Alkalinity (kg/ha)` are not generated.

## Parameters

The original seven quality thresholds are preserved:

- `param_ionsdiff_low_k` = `20.0`
- `param_ionsdiff_high_k` = `10.0`
- `param_conddiff_low_1` = `30.0`
- `param_conddiff_low_2` = `20.0`
- `param_conddiff_high` = `10.0`
- `param_ratio_nacl_low` = `0.5`
- `param_ratio_nacl_high` = `1.5`

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

## Docker test

```bash
bash pipelineUnitTest.sh
```

The unit test builds the image, executes the full pipeline with the included example data, checks every declared output, verifies ZIP and PDF integrity and confirms the expected dimensions of the example Excel outputs.

The detailed documentation inherited from the original components is retained in `docs/`.
