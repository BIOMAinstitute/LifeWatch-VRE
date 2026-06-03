# Tesseract Wrapper Creation Guide
## Internal reference — LifeWatch ERIC ICP-Forest workflow

This document captures everything needed to create new Tesseract wrappers
for the LifeWatch ERIC platform, based on the ICP water chemistry workflow.
Read this before generating any new component.

---

## 1. What a Tesseract wrapper is

A wrapper is a self-contained Docker container that represents one operation
unit in a Tesseract Workflow. Wrappers are chained: the output of one is the
input of the next. Every wrapper in this workflow has:

- A **Python script** (the logic)
- A **Dockerfile** (the environment)
- An **annotation.json** (metadata for the platform UI)
- An **execution-parameters.json** (parameter values for local testing)
- A **README.md** (documentation for users)
- **Input and output** folders in `resources/example/data/`
- A **requirements.txt** with dependencies (documentation only — pip install is in the Dockerfile)

---

## 2. Folder structure (mandatory)

```
COMPONENT-NAME/
├── resources/example/data/
│   ├── inputs/              # test input files go here
│   ├── outputs/             # results appear here after local execution
│   └── execution-parameters.json
├── annotation.json
├── <script>.py
├── Dockerfile
├── requirements.txt         # documentation only — pip install is in Dockerfile
├── .dockerignore
├── .gitignore               # important for GitLab uploads
└── README.md
```

The `execute` script mounts:
- `$(pwd)/data/inputs`  → `/mnt/inputs`  (read-only)
- `$(pwd)/data/outputs` → `/mnt/outputs` (writable)

All paths in the Python script must use `/mnt/inputs/` and `/mnt/outputs/`.

---

## 3. annotation.json — rules and constraints

Every field is required (except `citation`, which may be null).

### Top-level required fields
```json
{
  "name":               "PascalCase, unique across the system",
  "label":              "Human-readable name",
  "description":        "Non-empty string",
  "type":               "One of: DataAnalysing | DataCollection | DataProcessing | DataSink | DataFlow | Core",
  "dockerImage":        "image name without registry prefix or version suffix",
  "parameters":         [],
  "inputs":             [],
  "outputs":            [],
  "resources":          {},
  "tags":               [],
  "license":            "SPDX id, e.g. GPL v3",
  "version":            "semver x.y.z (each part 0-999)",
  "dependencies":       [],
  "publicationDate":    "ISO 8601 date: 2025-05-27",
  "author":             "LifeWatch ERIC",
  "citation":           null,
  "bugs":               { "email": "...", "url": "..." },
  "testPath":           "unitTest.sh",
  "metaDataCatalogueUrl": "https://metadatacatalogue.lifewatch.eu/..."
}
```

### parameters — each item requires exactly these 5 keys
```json
{
  "name":         "camelCase — must match --argName in Python argparse",
  "label":        "Human-readable label",
  "description":  "Non-empty description",
  "defaultValue": "Always a string, even for numbers: \"3.0\", \"TRUE\"",
  "type":         "One of: List | Boolean | Date | Double | Float | Integer | String | Timestamp"
}
```
Optional keys: `min`, `max`, `step`, `validationMessage`, `required`,
`readOnly`, `optionList`, `secret`.
When `type = "List"`, populate `optionList` with `[{ "value": "...", "label": "..." }]`.

### inputs and outputs — each item requires exactly these 5 keys
```json
{
  "name":        "kebab-case unique identifier",
  "label":       "Human-readable label",
  "description": "Non-empty description",
  "type":        "One of: Bin | Fastq | Image | Json | Map | Rar | TempFile | Text | DataSetClass | TabularDataSet | ClassificationMetric | RDF | Zip | Directory | File",
  "path":        "/mnt/inputs/<filename>  or  /mnt/outputs/<filename>"
}
```
Excel files (.xlsx) use type `"Text"`. ZIP archives use `"Zip"`.
No extra keys allowed — the validator will reject them.

### resources — all 5 keys required
```json
{
  "cores":         2,
  "memory":        1024,
  "gpuNeeded":     false,
  "gpuMemory":     0,
  "estimatedTime": 5
}
```
`memory` and `gpuMemory` are in MB. `estimatedTime` is in seconds.

### dependencies — each item requires exactly these 5 keys
```json
{
  "name":    "library name",
  "license": "SPDX id",
  "version": "x.y.z",
  "author":  "Author name",
  "citation": null
}
```

---

## 4. Python script — mandatory conventions

### CLI argument parsing
Every parameter declared in `annotation.json` must be received via argparse:
```python
parser = argparse.ArgumentParser(description="<wrapper name> wrapper")
parser.add_argument("--paramName", type=float, default=3.0, help="...")
args = parser.parse_args()
```
The `execute` script passes parameters as `--paramName=value`.
Components with no parameters still need the parser:
```python
parser = argparse.ArgumentParser(description="...")
args = parser.parse_args()
```

### Paths
```python
input_zip_path  = "/mnt/inputs/<filename>"
output_zip_path = "/mnt/outputs/<filename>"
```
Create output subdirectories with `os.makedirs(..., exist_ok=True)`.
Use `/tmp/` for intermediate extraction (`/tmp/input/`, `/tmp/output/`).

### ZIP handling pattern
```python
import zipfile
extract_dir = "/tmp/input/level0"
os.makedirs(extract_dir, exist_ok=True)
with zipfile.ZipFile(input_zip_path, "r") as z:
    z.extractall(extract_dir)

# ... process files in extract_dir ...

with zipfile.ZipFile(output_zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zout:
    for fpath in Path(output_dir).glob("*"):
        zout.write(fpath, fpath.name)
```

### Guard inputs at the start
```python
for p in (input_zip_path, input_config_path):
    if not os.path.exists(p):
        raise RuntimeError(f"Required input file not found: {p}")
```

---

## 5. Dockerfile — rules

```dockerfile
FROM python:3.11-slim          # always slim, never alpine (numpy/pandas compile issues)

WORKDIR /code

RUN pip install --no-cache-dir \
    pandas==2.2.2 \
    numpy==1.26.4 \
    openpyxl==3.1.2

COPY <script>.py ./
ENTRYPOINT ["python", "./<script>.py"]
```

Key rules:
- `zipfile`, `os`, `re`, `json`, `argparse`, `pathlib` are stdlib — never pip-install these.
- `openpyxl` is needed whenever `pd.read_excel()` or `pd.to_excel()` is called, even if not imported directly.
- `matplotlib` — always add `matplotlib.use("Agg")` immediately after the import (no display inside Docker).
- `fpdf2` (not `fpdf`) — use `Helvetica` not `Arial`; use `new_x=XPos.LMARGIN, new_y=YPos.NEXT` instead of `ln=True`.
- Never use Alpine base image with scientific Python libraries.

---

## 6. execution-parameters.json format

```json
{
  "parameters": [
    { "name": "paramName", "defaultValue": "3.0", "value": "3.0" }
  ]
}
```
- All values as strings, even floats and booleans.
- Every parameter in `annotation.json` must have a matching entry here.
- If no parameters: `{ "parameters": [] }`.
- This file goes in `resources/example/data/execution-parameters.json`.

---

## 7. Scientific context — ICP-Forest water chemistry workflow

### 7.1 Background

Since the 1980s, European forests have been continuously monitored under two
international programmes coordinated by the UN Economic Commission for Europe
(UNECE) under the Convention on Long-range Transboundary Air Pollution (CLRTAP):

- **ICP Forests** — monitors forest condition across Europe. Level II plots (640
  across Europe, 14 in Spain) provide detailed cause-effect data on atmospheric
  pollution impacts. Each plot collects water, soil, organic matter, air and
  biodiversity samples.
- **ICP Integrated Monitoring (ICP IM)** — assesses ecological effects of air
  pollutants through long-term integrated observations. 48 active stations across
  15 countries, including one Spanish site (ES02, BIOMA – University of Navarra).

This workflow focuses on **water-related subprogrammes**, which share identical
laboratory analyses and validation procedures across all sampling types.

### 7.2 Water subprogrammes

| Subprogram | Code | Description |
|------------|------|-------------|
| Precipitation Chemistry | PC | Bulk deposition in open areas — quantifies wet deposition inputs |
| Throughfall | TF | Water passing through the forest canopy — reflects canopy interactions |
| Stemflow | SF | Water flowing down tree stems — localised flux insights |
| Soil Water | SW | Soil solution chemistry — acidification and nitrogen dynamics |
| Runoff Water | RW | Catchment outflows — estimates element export via hydrology |

Although these subprogrammes differ in collection method, all resulting samples
undergo **identical laboratory analyses and validation procedures**. The
distinction is captured in the `samplesInfo.xlsx` file via the `SamplingTypology`
column, which is essential for several validation rules.

### 7.3 Template structure and sample representation

Researchers fill standardised Excel templates with laboratory results.
These are the **Level 0** entry point of the workflow.

**Naming convention:** `YYYY_MM_PARAMETER(_REP).xlsx`
Examples: `2025_02_ANIONS.xlsx`, `2025_02_FOREST_ALKALINITY_REP.xlsx`

Each row in a template = one analytical sample. Multiple subprogrammes can
coexist in the same template. The number of rows depends on how samples were
processed in the lab (individual vs composite), not on the subprogramme itself.

**Template types and their columns:**

| Template | Key columns |
|----------|-------------|
| AMMONIUM | SampleID, SiteCode, SiteName, EndDate, NH4N, Comments |
| CATIONS | SampleID, SiteCode, SiteName, EndDate, Ca, Mg, Na, K, Al, Fe, Mn, As, Cd, Co, Cr, Cu, Ni, Pb, Zn, P, S, Comments |
| ANIONS | SampleID, SiteCode, SiteName, EndDate, Cl, NO3, SO4, PO4, Comments |
| DOC/TN | SampleID, SiteCode, SiteName, EndDate, DOC, TN, Comments |
| pH/Conductivity | StartDate, EndDate, SiteCode, SiteName, SampleID, Collector, Volume, pH, Conductivity, Temperature, DO(%), DO(ppm), Comments |
| Alkalinity | SampleID, SiteCode, SiteName, Year, Month, HCl Volume, pH, HCl(mol/L), Sampling Volume, Comments |

**Special case — pH/Conductivity:** Measurements are made on each individual
collector before mixing, resulting in multiple rows per final sample. A
volume-weighted average must be computed to produce one value per composite
sample (matching the row count of the other templates).

**Special case — Alkalinity:** Each sample has multiple titration rows (successive
HCl additions while recording pH). These rows are used together to compute
alkalinity via the Gran method (linear regression to find the equivalence point).
Each sample has a unique SampleID across all its titration rows.

### 7.4 The four data levels

| Level | Name | Description |
|-------|------|-------------|
| **Level 0** | Raw data | Laboratory results recorded directly into templates. No processing applied. Entry point of the workflow. |
| **Level 1** | Pre-processed | Passed format validation + basic transformations: LOQ substitution, unit conversion, alkalinity calculation (Gran method), volume-weighted pH and conductivity. |
| **Level 2** | Chemically validated | Advanced physicochemical quality checks per sample: ion balance, conductivity consistency, Na/Cl ratio, organic nitrogen check, ionic strength. Each sample carries a `FINAL_VALIDATION` flag (SI/NO). |
| **Level 3** | Reporting-ready | Best measurement selected per sample per month (NOREP/REP priority logic). One row per sample per month, ready for ICP programme submission and database ingestion. |

### 7.5 Replicate (REP) samples

When a sample fails chemical validation, ICP guidelines recommend repeating the
laboratory analysis. The repeated file uses the same naming convention with `_REP`
appended: `2025_02_ANIONS_REP.xlsx`.

**Important rules:**
- REP files must always be accompanied by their original NOREP files.
- REP and NOREP samples are initially processed independently (different rows).
- If a REP file only contains some parameters, missing values are filled from the NOREP data.
- A sample is only ever repeated when it **failed** (VAL = NO). Therefore:
  - SI → NO transition is **impossible** — passing samples are never repeated.
  - The only meaningful transitions are NO → SI (REP improved) or NO → NO (REP still fails).

**Final reporting selection logic (component 7):**
1. NOREP passes (VAL = SI) → keep NOREP
2. NOREP fails, REP passes → keep REP
3. Both NOREP and REP fail → keep NOREP (both were attempted; result must be reported)
4. NOREP fails, no REP → discard the sample

### 7.6 SamplingTypology codes

The `SamplingTypology` column in `samplesInfo.xlsx` drives several
typology-specific calculations in the chemical validation step:

| Code | Meaning | Used for |
|------|---------|---------|
| `BOF` | Bulk open field (wet deposition) | Ion balance and Na/Cl filter |
| `WET` | Wet-only deposition | Ion balance and Na/Cl filter |
| `THR` | Throughfall | Na/Cl filter; Org- coefficient |
| `THR BL` | Throughfall bulk/litterfall | Na/Cl filter; specific Org- coefficient |
| `STF` | Stemflow | Na/Cl filter; specific Org- coefficient |
| `SW` | Soil water | Metals sum; specific Org- coefficient |

### 7.7 SiteCode

SiteCode identifies a monitoring plot. It is stored as a **column inside each
Excel file**, not in the filename. Always group data by SiteCode from file
content — never parse it from the filename. Each file may contain rows for
multiple SiteCodes.

---

## 8. The workflow step by step

See `ICP_Workflow_Lifewatch.docx` for the full scientific description of each step.

```
[allData.zip + config_tables.txt]
            │
            ▼
 ┌─────────────────────────────────────┐
 │  1. InputDataFormatValidation       │  Level 0 → validated Level 0
 │  Checks template format & content   │
 └─────────────────────────────────────┘
            │ allData_templates_format_validated.zip
            ▼
 ┌─────────────────────────────────────┐
 │  2. WaterChemicalDataTransformation │  validated Level 0 → Level 1 (raw)
 │  Alkalinity (Gran), weighted pH/EC, │
 │  consolidation per SiteCode         │
 └─────────────────────────────────────┘
            │ water_chemical_data_level1.zip
            ▼
 ┌─────────────────────────────────────┐
 │  3. LoqApplication                  │  Level 1 → Level 1 (LOQ-corrected)
 │  Replaces values < LOQ with LOQ/2   │
 └─────────────────────────────────────┘
            │ water_chemical_data_level1_loq.zip
            ▼
 ┌─────────────────────────────────────┐
 │  4. UnitTransformation              │  Level 1 → Level 1 (all units)
 │  Generates mg/l, µg/l, µeq/l       │
 │  for every analyte                  │
 └─────────────────────────────────────┘
            │ water_chemical_data_level1_units.zip
            ▼
 ┌─────────────────────────────────────┐  ← also needs samplesInfo.xlsx
 │  5. WaterChemistryValidation        │  Level 1 → Level 2
 │  Ion balance, conductivity check,   │
 │  Na/Cl ratio, OrgN check,           │
 │  FINAL_VALIDATION flag per sample   │
 └─────────────────────────────────────┘
            │ water_chemical_data_level2_validated.zip
            │ water_chemical_data_level2_alldata.zip
            ▼
 ┌─────────────────────────────────────┐  ← also needs samplesInfo.xlsx
 │  6. WaterChemistryValidationReport  │  Level 2 → report outputs
 │  PDF report, Samples2Repeat.xlsx,   │
 │  allFinalData.xlsx                  │
 └─────────────────────────────────────┘
            │ allFinalData.xlsx
            │ Samples2Repeat.xlsx
            │ validation_report.pdf
            ▼
 ┌─────────────────────────────────────┐  ← also needs samplesInfo.xlsx
 │  7. Data2FinalReport                │  Level 2 → Level 3
 │  NOREP/REP selection logic,         │
 │  one row per sample per month       │
 └─────────────────────────────────────┘
            │ data2report.xlsx (Level 3)
```

**External inputs shared across multiple components:**

| File | Used by | Description |
|------|---------|-------------|
| `allData.zip` | Component 1 | All filled Excel templates from researchers |
| `config_tables.txt` | Component 1 | JSON validation rules per template type |
| `samplesInfo.xlsx` | Components 5, 6, 7 | SampleID → SamplingTypology / ICP_Program / Instrument / ID_PostgreSQL mapping |

---

## 9. Key chemistry — what each validation checks and why

### 9.1 Ionic balance (components 5 & 6)

In a chemically consistent water sample, the sum of positive ions (cations)
should equal the sum of negative ions (anions). The IonsDiff% measures this:

```
IonsDiff% = 100 × (SumCations - SumAnions) / (0.5 × (SumCations + SumAnions))
```

Acceptable limits depend on conductivity (a proxy for ion concentration):
- WeightedConductivity ≤ 20 µS/cm → max ±20% (dilute samples, more analytical noise)
- WeightedConductivity > 20 µS/cm → max ±10%

A second version includes the estimated organic anion (Org-) in the anion sum,
which is important for samples with high dissolved organic carbon (DOC).

### 9.2 Organic anion estimation (Org-)

Dissolved organic matter carries a negative charge that contributes to the
anion balance but is not directly measured. It is estimated from DOC using
empirical relationships calibrated by sampling typology (ICP-Forest protocol):

| Typology | Formula |
|----------|---------|
| STF (stemflow) | Org- = 5.04 × DOC - 6.67 |
| THR BL (throughfall bulk) | Org- = 6.80 × DOC - 12.32 |
| THR (other throughfall) | Org- = 4.17 × DOC - 5.01 |
| SW (soil water) | Org- = 9.80 × DOC |

### 9.3 Conductivity check (component 5)

A theoretical conductivity is calculated from the measured ion concentrations
using their equivalent conductances (Kohlrausch's law), then corrected for
ionic activity using the Davies equation. The difference between this
theoretical value and the measured WeightedConductivity should be small:

- WeightedConductivity ≤ 10 µS/cm → max ±30%
- WeightedConductivity 10–20 µS/cm → max ±20%
- WeightedConductivity > 20 µS/cm → max ±10%

A large discrepancy indicates a missing or incorrectly measured ion.

### 9.4 Na/Cl ratio (component 5)

The ratio of sodium to chloride (in µeq/l) reflects the marine origin of
these ions. In most European forest monitoring contexts, Na/Cl should be
close to the seawater ratio (~1.0). Acceptable range: [0.5, 1.5].
Values outside this range suggest sea-salt influence, Na contamination,
or analytical errors. Only checked for BOF, WET, THR and STF samples.

### 9.5 OrgN check (component 5)

Total Nitrogen (TN) must always be greater than or equal to the sum of its
inorganic fractions: TN ≥ NO3-N + NH4-N. If this is violated it means TN
was measured lower than the sum of its known components, which is chemically
impossible and indicates a measurement error.

### 9.6 LOQ substitution (component 3)

The Limit of Quantification (LOQ) is the minimum concentration a laboratory
instrument can reliably measure. Values below the LOQ are not zero — they are
simply below the detection threshold. The standard method in environmental
chemistry is to replace them with LOQ/2, which preserves the information that
the value is low without treating it as absent. Every substitution is logged
for traceability.

### 9.7 Unit conventions

Three unit representations are generated for every analyte:
- **mg/l** — mass concentration (most common in templates)
- **µg/l** — mass concentration at micro scale (trace metals)
- **µeq/l** — equivalent concentration, charge-based (required for ion balance)

Conversion from µeq/l to mg/l: `mg/l = µeq/l × (atomic or molecular weight / valence) / 1000`

---

## 10. Common pitfalls

| Problem | Cause | Fix |
|---------|-------|-----|
| `AttributeError: Can only use .str accessor with string values` | SiteCode column has mixed types (NaN + str) | `df["SiteCode"] = df["SiteCode"].astype(str)` after reading |
| `UnicodeEncodeError` in fpdf2 | Em dash `—` or other non-latin-1 chars in PDF text | Replace `—` with `-`; use `Helvetica` not `Arial` |
| `DeprecationWarning: ln=True` in fpdf2 | Old fpdf API | Use `new_x=XPos.LMARGIN, new_y=YPos.NEXT` |
| `ModuleNotFoundError` in Docker | Library not in Dockerfile | Add to `pip install`; remember `openpyxl` for any Excel I/O |
| Chart backend error in Docker | matplotlib trying to use GUI | Add `matplotlib.use("Agg")` after `import matplotlib` |
| `plot_cols is not defined` | Variable used outside its scope | Derive flags (`has_rep`, `has_typology`) once at function top |
| Alpine + numpy/pandas build error | Missing C build tools | Use `python:3.11-slim` not `python:3.11-alpine` |
| `FutureWarning` on `.fillna()` | Pandas downcasting deprecation | Chain `.infer_objects(copy=False)` after `.fillna()` |
| REP samples missing typology | REP SampleID doesn't match samplesInfo | Join on base ID (strip `REP$`) not full SampleID |
| SiteCode parsed from filename | Old approach, no longer valid | Read SiteCode from file content column only |

---

## 11. README template for each component

Each component folder must contain a `README.md` with:
1. Component name and one-line description
2. Where it fits in the workflow (previous → this → next)
3. Inputs table (name, type, path, description)
4. Outputs table (name, type, path, description)
5. Parameters table (name, type, default, description)
6. Local execution instructions (`build-image` + `execute`)
7. What to put in `resources/example/data/inputs/` for local testing

See the 7 component READMEs for concrete examples.
