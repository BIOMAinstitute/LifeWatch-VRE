# Water Chemistry Quality Validation and Reporting (steps 5–7)

This component combines the original workflow components 5, 6 and 7 while retaining each scientific stage in a separate Python script.

## Internal sequence

```text
water_chemical_data_level1_units.zip
        ↓
5. chemical_quality_validation.py
        ↓
water_chemical_data_level2_validated.zip
        ↓
6. validation_report.py
        ↓
All_Validated_Data.xlsx + report outputs
        ↓
7. data2final_report.py
        ↓
Final_Data.xlsx
```

`run_pipeline.py` only coordinates paths, parameters and execution order. The calculations and selection rules remain in the original scripts under `scripts/`.

## Inputs

- `/mnt/inputs/water_chemical_data_level1_units.zip`: output ZIP from the combined preprocessing component (steps 2–4).
- `/mnt/inputs/samplesInfo.xlsx`: sample metadata reused by all three stages.

The original file names outside Docker do not matter. Tesseract mounts each selected input at the paths above. During manual Docker testing, mount the files to those paths explicitly.

## Parameters

The seven quality thresholds from component 5 are preserved unchanged:

- `param_ionsdiff_low_k` = 20.0
- `param_ionsdiff_high_k` = 10.0
- `param_conddiff_low_1` = 30.0
- `param_conddiff_low_2` = 20.0
- `param_conddiff_high` = 10.0
- `param_ratio_nacl_low` = 0.5
- `param_ratio_nacl_high` = 1.5

Components 6 and 7 have no configurable parameters.

## Outputs

All outputs are written directly under `/mnt/outputs`:

- `water_chemical_data_level2_alldata.zip`
- `water_chemical_data_level2_validated.zip`
- `validation_report.pdf`
- `Samples2Repeat.xlsx`
- `All_Validated_Data.xlsx`
- `Final_Data.xlsx`
- `pipeline_execution.log`

## Code organization

```text
scripts/
├── chemical_quality_validation.py
├── validation_report.py
└── data2final_report.py
```

Only input/output paths were made configurable through environment variables so the coordinator can connect the stages internally. One metadata inconsistency was corrected: component 7's original annotation declared duplicated output entries, while its script actually writes `Final_Data.xlsx`; the combined component declares that real output once.

## Docker test

```bash
docker build -t water-chemistry-quality-report .
bash pipelineUnitTest.sh
```

The unit test builds the image, executes the full three-stage pipeline with the included example data, checks that all declared outputs exist and verifies that the ZIP and Excel files contain data.

The detailed original documentation is retained in `docs/`.

## Regression note

The combined execution was compared against the current standalone scripts from components 5, 6 and 7 and produced identical tabular results. Some historical example output files packaged in the original component ZIPs no longer match the current scripts (notably the number of repeat and final rows), so the current script behavior—not stale example snapshots—is used as the regression baseline.
