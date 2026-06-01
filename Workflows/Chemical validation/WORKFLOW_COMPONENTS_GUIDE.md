# Tesseract Wrapper Creation Guide
## (Internal reference for Claude — LifeWatch ERIC ICP-Forest workflow)

This document captures everything needed to create new Tesseract wrappers
for the LifeWatch ERIC platform, based on the ICP-Forest water chemistry
workflow built in this session. Read this before generating any new component.

---

## 1. What a Tesseract wrapper is

A wrapper is a self-contained Docker container that represents one operation
unit in a Tesseract Workflow. Wrappers are chained: the output of one is the
input of the next. Every wrapper has:

- A **Python script** (the logic)
- A **Dockerfile** (the environment)
- An **annotation.json** (metadata for the platform UI)
- An **execution-parameters.json** (parameter values for local testing)
- A **README.md** (documentation for users)

---

## 2. Folder structure (mandatory)

```
COMPONENT-NAME/
├── bin/
│   ├── build-image          # runs: docker build -t <image>:<version> .
│   └── execute              # validates annotation + runs docker with params
├── data/
│   ├── inputs/              # test input files go here
│   ├── outputs/             # results appear here after local execution
│   └── execution-parameters.json
├── annotation.json
├── <script>.py
├── Dockerfile
├── requirements.txt         # documentation only — pip install is in Dockerfile
└── README.md
```

The `execute` script mounts:
- `$(pwd)/data/inputs`  → `/mnt/inputs`  (read-only)
- `$(pwd)/data/outputs` → `/mnt/outputs` (writable)

All paths in the Python script must use `/mnt/inputs/` and `/mnt/outputs/`.

---

## 3. annotation.json — rules and constraints

The `execute` script validates this file strictly. Every field is required
(except `citation`, which may be null).

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
  "name":         "camelCase identifier — must match --argName in Python argparse",
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
  "cores":        2,
  "memory":       1024,
  "gpuNeeded":    false,
  "gpuMemory":    0,
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
Parameters with no CLI args (empty `parameters: []`) still need the parser:
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

RUN pip install --no-cache-dir \
    pandas==2.2.2 \
    numpy==1.26.4 \
    openpyxl==3.1.2

COPY <script>.py ./
ENTRYPOINT ["python", "./<script>.py"]
```

- `zipfile`, `os`, `re`, `json`, `argparse`, `pathlib` — stdlib, never pip-install these.
- `openpyxl` — needed whenever `pd.read_excel()` or `pd.to_excel()` is called,
  even if not imported directly.
- `matplotlib` — needed for chart generation; always add `matplotlib.use("Agg")`
  immediately after the import (no display inside Docker).
- `fpdf2` (not `fpdf`) — the maintained fork; use `Helvetica` not `Arial`;
  use `new_x=XPos.LMARGIN, new_y=YPos.NEXT` instead of `ln=True`.
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
- If no parameters, use `{ "parameters": [] }`.
- This file goes in `data/execution-parameters.json`.

---

## 7. The ICP-Forest water chemistry workflow

This workflow processes raw ICP-Forest water chemistry Excel templates
through 7 sequential components:

```
1. InputDataFormatValidation
        ↓ allData_templates_format_validated.zip
2. WaterChemicalDataTransformation
        ↓ water_chemical_data_level1.zip
3. LoqApplication
        ↓ water_chemical_data_level1_loq.zip
4. UnitTransformation
        ↓ water_chemical_data_level1_units.zip
5. WaterChemistryValidation
        ↓ water_chemical_data_level2_validated.zip
           water_chemical_data_level2_alldata.zip
6. WaterChemistryValidationReport
        ↓ validation_report.pdf
           Samples2Repeat.xlsx
           allFinalData.xlsx
7. Data2FinalReport
        ↓ data2report.xlsx
```

External inputs used by multiple components:
- `allData.zip` — ZIP of validated .xlsx templates (component 1)
- `config_tables.txt` — JSON validation rules for Excel columns (component 1)
- `samplesInfo.xlsx` — SampleID → SamplingTypology / ICP_Program / Instrument
  / ID_PostgreSQL mapping (components 5, 6, 7)

---

## 8. Key domain knowledge

### SamplingTypology codes
Used in validation and report generation:
- `BOF` — bulk open field (wet deposition)
- `WET` — wet-only deposition
- `THR` — throughfall
- `THR BL` — throughfall bulk/litterfall
- `STF` — stemflow
- `SW` — soil water

### Organic anion (Org-) estimation coefficients by typology
These are ICP-Forest empirical calibrations used in `WaterChemistryValidation`:
- STF:      `Org- = 5.04·DOC - 6.67`
- THR BL:   `Org- = 6.80·DOC - 12.32`
- THR other:`Org- = 4.17·DOC - 5.01`
- SW:       `Org- = 9.80·DOC`

### Quality thresholds (configurable parameters in component 5)
- IonsDiff% limit: 20% (conductivity ≤ 20 µS/cm), 10% (> 20 µS/cm)
- CondDiff% limits: 30% (≤ 10), 20% (10–20), 10% (> 20 µS/cm)
- Na/Cl ratio: [0.5, 1.5]

### LOQ substitution (component 3)
Values below the Limit of Quantification are replaced by LOQ/2.
This is the standard half-LOQ method for left-censored analytical data.

### REP (replicate) samples
- Identified by SampleID ending in `REP` after `clean_id()` normalisation.
- `clean_id()`: uppercase, remove spaces/underscores/hyphens/dots/commas.
- A sample is only repeated when it failed validation (VAL = NO).
- SI → NO transition is impossible by definition (passing samples are not repeated).

### SiteCode extraction
SiteCode is a column inside each Excel file — it is NOT in the filename.
Always group by SiteCode from data content, never from filename parsing.

---

## 9. Common pitfalls

| Problem | Cause | Fix |
|---------|-------|-----|
| `AttributeError: Can only use .str accessor with string values` | SiteCode column has mixed types (NaN + str) | Add `df["SiteCode"] = df["SiteCode"].astype(str)` after reading |
| `UnicodeEncodeError` in fpdf2 | Em dash `—` or other non-latin-1 chars in PDF text | Replace `—` with `-`; use `Helvetica` not `Arial` |
| `DeprecationWarning: ln=True` in fpdf2 | Old fpdf API | Use `new_x=XPos.LMARGIN, new_y=YPos.NEXT` |
| `ModuleNotFoundError` in Docker | Library not in Dockerfile | Add to `pip install` block; remember `openpyxl` for any Excel I/O |
| Chart backend error in Docker | matplotlib trying to use GUI backend | Add `matplotlib.use("Agg")` immediately after `import matplotlib` |
| `plot_cols is not defined` | Variable used outside its scope | Derive flags (`has_rep`, `has_typology`) once at function top level |
| Alpine + numpy/pandas | Missing C build tools | Use `python:3.11-slim` not `python:3.11-alpine` |
| `FutureWarning` on `.fillna()` | Pandas downcasting deprecation | Chain `.infer_objects(copy=False)` after `.fillna()` |

---

## 10. README template for each component

Each component folder must contain a `README.md` with:
1. Component name and one-line description
2. Where it fits in the workflow (previous → this → next)
3. Inputs table (name, type, path, description)
4. Outputs table (name, type, path, description)
5. Parameters table (name, type, default, description)
6. Local execution instructions (`build-image` + `execute`)
7. What to put in `data/inputs/` for local testing

See the 7 component READMEs in this session for concrete examples.
