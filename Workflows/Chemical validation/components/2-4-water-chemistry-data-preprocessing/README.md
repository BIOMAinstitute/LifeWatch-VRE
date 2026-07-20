# Water Chemistry Preprocessing — combined components 2, 3 and 4

This component executes the original water-chemistry components **2, 3 and 4** sequentially while keeping their scientific logic in three separate scripts.

```text
Validated Excel templates
        │
        ▼
2. Water chemical data transformation
        │  water_chemical_data_level1.zip
        ▼
3. Laboratory LOQ application
        │  water_chemical_data_level1_loq.zip
        ▼
4. Water chemistry unit transformation
        │
        ▼
water_chemical_data_level1_units.zip
```

## Internal structure

```text
2-4-water-chemistry-preprocessing/
├── annotation.json
├── Dockerfile
├── requirements.txt
├── run_pipeline.py
├── pipelineUnitTest.sh
├── scripts/
│   ├── data_transformation.py
│   ├── laboratory_loq_application.py
│   └── unit_transformation.py
├── docs/
│   ├── README_step2_data_transformation.md
│   ├── README_step3_loq_application.md
│   └── README_step4_unit_transformation.md
└── resources/example/data/
    ├── execution-parameters.json
    ├── inputs/validated_data.zip
    └── outputs/expected_water_chemical_data_level1_units.zip
```

`run_pipeline.py` is only an orchestrator. It creates temporary directories, runs each original script, passes the intermediate ZIP to the next stage, forwards the LOQ parameters and publishes the final outputs.

## Changes made to the original scripts

The processing formulas and dataframe transformations were not reorganised or rewritten. Only these integration changes were made:

1. Input, output and extraction paths may be supplied through environment variables. Their original paths remain the defaults, so each script can still be used independently.
2. Component 2 now searches recursively within the extracted ZIP. This is required because the format-validation component stores the workbooks under an `input_data/` directory.
3. Intermediate files are written under `/tmp/water_chemistry_preprocessing` and are not exposed as component outputs.

## Input

| Name | Type | Path |
|---|---|---|
| `input-data` | Zip | `/mnt/inputs/validated_data.zip` |

The ZIP may contain the validated workbooks directly or under `input_data/`. File identification continues to use the original keywords: `ALKALINITY`, `PH_COND_WEIGHTED_RAW`, `AMMONIUM`, `ANIONS`, `CATIONS` and `DOC_TN`.

## Outputs

| Name | Type | Path |
|---|---|---|
| Final preprocessed data | Zip | `/mnt/outputs/water_chemical_data_level1_units.zip` |
| LOQ substitution log | Text | `/mnt/outputs/loq_substitutions.log` |
| Pipeline execution log | Text | `/mnt/outputs/pipeline_execution.log` |

The final ZIP contains the same tab-separated CSV files that were produced by the former component 4.

## Parameters

The component exposes the same 24 LOQ parameters as the former component 3. Their names and default values have been preserved exactly. Components 2 and 4 did not have user parameters.

For every configured analyte, values below its LOQ are replaced with `LOQ / 2`. Every replacement is recorded in `loq_substitutions.log`.

## Docker execution

```bash
docker build -t lw-water-chemistry-preprocessing .

docker run --rm \
  -v "$(pwd)/resources/example/data/inputs/validated_data.zip:/mnt/inputs/validated_data.zip:ro" \
  -v "$(pwd)/resources/example/data/outputs/test-run:/mnt/outputs" \
  lw-water-chemistry-preprocessing
```

Parameters can be overridden after the image name:

```bash
docker run --rm \
  -v "$(pwd)/resources/example/data/inputs/validated_data.zip:/mnt/inputs/validated_data.zip:ro" \
  -v "$(pwd)/resources/example/data/outputs/test-run:/mnt/outputs" \
  lw-water-chemistry-preprocessing \
  --param_NH4N 0.04 \
  --param_NO3 0.05
```

## Unit test

```bash
bash pipelineUnitTest.sh
```

The test:

1. builds the Docker image;
2. runs the full three-stage chain using the original example workbooks;
3. checks that the final ZIP, LOQ log and pipeline log exist and are non-empty;
4. verifies ZIP integrity;
5. verifies that the expected 84 CSV files were generated.

The detailed original documentation for each processing stage is preserved unchanged under `docs/`.
