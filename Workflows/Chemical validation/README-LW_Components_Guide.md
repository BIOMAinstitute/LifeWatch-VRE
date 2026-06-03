# Tesseract Wrapper Creation Guide
## Internal reference — LifeWatch ERIC ICP workflow

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

## 7. README template for each component

Each component folder must contain a `README.md` with:
1. Component name and one-line description
2. Where it fits in the workflow (previous → this → next)
3. Inputs table (name, type, path, description)
4. Outputs table (name, type, path, description)
5. Parameters table (name, type, default, description)
6. Local execution instructions (`build-image` + `execute`)
7. What to put in `resources/example/data/inputs/` for local testing

See the 7 component READMEs for concrete examples.