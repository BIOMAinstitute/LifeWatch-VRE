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

---

## Template structure — the `data` sheet

Every Excel file in the ZIP must contain a sheet named **`data`** (case-sensitive).
The component reads only this sheet. Any other sheets (e.g. `Readme`, `metadata`)
are ignored.

Each row in the `data` sheet represents one analytical sample.
Below are the six template types used in the ICP-Forest workflow, with their
columns and the values researchers record in each one.

---

### AMMONIUM template
**File naming:** `YYYY_MM_PARAMETER_AMMONIUM(_REP).xlsx`
**Example:** `2025_01_FOREST_AMMONIUM.xlsx`

| Column | Type | Required | Unit | Description |
|--------|------|----------|------|-------------|
| `SampleID` | text | ✅ | — | Unique sample identifier (e.g. `05PS INT`, `22PN EXT NIEVE`) |
| `SiteCode` | text | ✅ | — | Numeric plot code (e.g. `05`, `22`) |
| `SiteName` | text | ✅ | — | Plot name (e.g. `Valsain`, `Mora de Rubielos`) |
| `StartDate` | date | ⚠️ optional | DD/MM/YYYY | Sample collection start date |
| `EndDate` | date | ✅ | DD/MM/YYYY | Sample collection end date |
| `year` | integer | ✅ | — | Year of collection (e.g. `2025`) |
| `month` | integer | ✅ | — | Month of collection (1–12) |
| `NH4N(mg/l)` | float | ⚠️ optional | mg/L | Ammonium-nitrogen concentration |
| `Comments` | text | ⚠️ optional | — | Free-text observations |

---

### ANIONS template
**File naming:** `YYYY_MM_PARAMETER_ANIONS(_REP).xlsx`
**Example:** `2025_01_FOREST_ANIONS.xlsx`

| Column | Type | Required | Unit | Description |
|--------|------|----------|------|-------------|
| `SampleID` | text | ✅ | — | Unique sample identifier |
| `SiteCode` | text | ✅ | — | Numeric plot code |
| `SiteName` | text | ✅ | — | Plot name |
| `StartDate` | date | ⚠️ optional | DD/MM/YYYY | Collection start date |
| `EndDate` | date | ✅ | DD/MM/YYYY | Collection end date |
| `year` | integer | ✅ | — | Year |
| `month` | integer | ✅ | — | Month (1–12) |
| `CL(mg/l)` | float | ⚠️ optional | mg/L | Chloride concentration |
| `NO3(mg/l)` | float | ⚠️ optional | mg/L | Nitrate concentration |
| `SO4(mg/l)` | float | ⚠️ optional | mg/L | Sulphate concentration |
| `PO4(mg/l)` | float | ⚠️ optional | mg/L | Phosphate concentration |
| `Comments` | text | ⚠️ optional | — | Free-text observations |

---

### CATIONS template
**File naming:** `YYYY_MM_PARAMETER_CATIONS(_REP).xlsx`
**Example:** `2025_01_FOREST_CATIONS.xlsx`

| Column | Type | Required | Unit | Description |
|--------|------|----------|------|-------------|
| `SampleID` | text | ✅ | — | Unique sample identifier |
| `SiteCode` | text | ✅ | — | Numeric plot code |
| `SiteName` | text | ✅ | — | Plot name |
| `StartDate` | date | ⚠️ optional | DD/MM/YYYY | Collection start date |
| `EndDate` | date | ✅ | DD/MM/YYYY | Collection end date |
| `year` | integer | ✅ | — | Year |
| `month` | integer | ✅ | — | Month (1–12) |
| `CA(mg/l)` | float | ⚠️ optional | mg/L | Calcium |
| `MG(mg/l)` | float | ⚠️ optional | mg/L | Magnesium |
| `NA(mg/l)` | float | ⚠️ optional | mg/L | Sodium |
| `K(mg/l)` | float | ⚠️ optional | mg/L | Potassium |
| `AL(mg/l)` | float | ⚠️ optional | mg/L | Aluminium |
| `FE(mg/l)` | float | ⚠️ optional | mg/L | Iron |
| `MN(mg/l)` | float | ⚠️ optional | mg/L | Manganese |
| `AS(mg/l)` | float | ⚠️ optional | mg/L | Arsenic |
| `CD(mg/l)` | float | ⚠️ optional | mg/L | Cadmium |
| `CR(mg/l)` | float | ⚠️ optional | mg/L | Chromium |
| `CU(mg/l)` | float | ⚠️ optional | mg/L | Copper |
| `CO(mg/l)` | float | ⚠️ optional | mg/L | Cobalt |
| `NI(mg/l)` | float | ⚠️ optional | mg/L | Nickel |
| `PB(mg/l)` | float | ⚠️ optional | mg/L | Lead |
| `ZN(mg/l)` | float | ⚠️ optional | mg/L | Zinc |
| `P(mg/l)` | float | ⚠️ optional | mg/L | Phosphorus |
| `S(mg/l)` | float | ⚠️ optional | mg/L | Sulphur |
| `Comments` | text | ⚠️ optional | — | Free-text observations |

---

### DOC/TN template
**File naming:** `YYYY_MM_PARAMETER_DOC_TN(_REP).xlsx`
**Example:** `2025_01_FOREST_DOC_TN.xlsx`

| Column | Type | Required | Unit | Description |
|--------|------|----------|------|-------------|
| `SampleID` | text | ✅ | — | Unique sample identifier |
| `SiteCode` | text | ✅ | — | Numeric plot code |
| `SiteName` | text | ✅ | — | Plot name |
| `StartDate` | date | ⚠️ optional | DD/MM/YYYY | Collection start date |
| `EndDate` | date | ✅ | DD/MM/YYYY | Collection end date |
| `year` | integer | ✅ | — | Year |
| `month` | integer | ✅ | — | Month (1–12) |
| `DOC(mg/l)` | float | ⚠️ optional | mg/L | Dissolved organic carbon |
| `TN(mg/l)` | float | ⚠️ optional | mg/L | Total nitrogen |
| `Comments` | text | ⚠️ optional | — | Free-text observations |

---

### pH / Conductivity template  ⚠️ Special case
**File naming:** `YYYY_MM_PARAMETER_pH_COND_WEIGHTED_RAW(_REP).xlsx`
**Example:** `2025_01_FOREST_pH_COND_WEIGHTED_RAW.xlsx`

This template is different from the others: **measurements are recorded per
individual collector** (one row per bottle/collector), not per composite sample.
Multiple collectors that belong to the same composite sample share the same
`SampleID` and `Group` value. The transformation step (Component 2) computes
the volume-weighted average across collectors to produce one row per sample.

| Column | Type | Required | Unit | Description |
|--------|------|----------|------|-------------|
| `SampleID` | text | ✅ | — | Sample identifier (shared by all collectors in the same group) |
| `StartDate` | date | ⚠️ optional | DD/MM/YYYY | Collection start date |
| `EndDate` | date | ⚠️ optional | DD/MM/YYYY | Collection end date |
| `year` | integer | ✅ | — | Year |
| `month` | integer | ✅ | — | Month (1–12) |
| `SiteCode` | text | ✅ | — | Numeric plot code |
| `SiteName` | text | ✅ | — | Plot name |
| `CollectorID` | text | ⚠️ optional | — | Individual collector identifier (e.g. `1231`, `A-04`) |
| `Group` | integer | ✅ | — | Group index that defines which collectors belong to the same composite sample |
| `Tare(g)` | float | ⚠️ optional | g | Weight of empty collector |
| `Tare+Sample(g)` | float | ⚠️ optional | g | Weight of collector + collected water |
| `VolumeCollector(ml)` | float | ✅ | mL | Volume of water collected by this collector — used for weighting |
| `sampler_radius` | float | ⚠️ optional | m | Radius of the collector mouth — used to compute precipitation (l/m²) |
| `Saturated(Y/N)` | text | ⚠️ optional | Y/N | Whether the collector overflowed |
| `Conductivity(µS/cm)` | float | ⚠️ optional | µS/cm | Electrical conductivity of this collector's sample |
| `Temperature(ºC)` | float | ⚠️ optional | °C | Temperature at measurement |
| `pH` | float | ⚠️ optional | — | pH of this collector's sample |
| `DO(%)` | float | ⚠️ optional | % | Dissolved oxygen saturation |
| `DO(ppm)` | float | ⚠️ optional | mg/L | Dissolved oxygen concentration |
| `Comments` | text | ⚠️ optional | — | Free-text observations |

---

### ALKALINITY template  ⚠️ Special case
**File naming:** `YYYY_ALKALINITY_MM(_REP).xlsx`
**Example:** `2025_ALKALINITY_05.xlsx`

This template is also different: **each sample has multiple rows**, one per
titration step. Successive small volumes of HCl are added to the sample while
recording pH. These rows are later used together to compute alkalinity via the
Gran method (Component 2). All rows belonging to the same sample share the
same `SampleID`.

| Column | Type | Required | Unit | Description |
|--------|------|----------|------|-------------|
| `SampleID` | text | ✅ | — | Sample identifier (same value for all titration rows of a sample) |
| `SiteCode` | text | ✅ | — | Numeric plot code |
| `SiteName` | text | ✅ | — | Plot name |
| `year` | integer | ✅ | — | Year |
| `month` | integer | ✅ | — | Month (1–12, or `01`–`12` as text) |
| `HCLVolume(ml)` | float | ✅ | mL | Cumulative volume of HCl added at this titration step |
| `pH` | float | ✅ | — | pH measured at this titration step |
| `HCL(mol/l)` | float | ✅ | mol/L | Concentration of the HCl solution used (same for all rows of the same sample) |
| `SamplingVolume(ml)` | float | ✅ | mL | Total volume of the water sample being titrated (same for all rows) |
| `Comments` | text | ⚠️ optional | — | Free-text observations |

---

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
