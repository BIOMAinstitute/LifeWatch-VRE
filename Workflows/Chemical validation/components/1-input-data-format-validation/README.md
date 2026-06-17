# 1 — Input Data Format Validation

Validates multiple Excel templates contained in a ZIP against a JSON
configuration file. Produces a plain-text validation log and a ZIP
with the same files renamed with a `validated_` prefix.

**This is a general-purpose component.** It can validate any set of Excel
files as long as:
1. The data to validate is in a sheet named exactly **`data`** (lowercase).
2. A `tables_config.txt` file is provided that describes the expected structure.

---

## Workflow position

```
[allData.zip + tables_config.txt]  →  InputDataFormatValidation  →  WaterChemicalDataTransformation
```

---

## Inputs

| Name | Type | Path | Description |
|------|------|------|-------------|
| input-data | Zip | `/mnt/inputs/allData.zip` | ZIP of Excel workbooks (.xlsx). Each must have a sheet named `data`. |
| input-config | Text | `/mnt/inputs/tables_config.txt` | JSON array defining validation rules per template type. |

## Outputs

| Name | Type | Path | Description |
|------|------|------|-------------|
| output-log | Text | `/mnt/outputs/validation_log.txt` | Plain-text report: ❌ critical errors, ⚠️ warnings, ✅ ok per file. |
| output-data | Zip | `/mnt/outputs/allData_templates_format_validated.zip` | Same Excel files renamed with `validated_` prefix. |

## Parameters

| Name | Type | Default | Description |
|------|------|---------|-------------|
| stopOnErrors | String | `TRUE` | When `TRUE`, exits with code 1 if any critical error is found, halting the workflow. Set to `FALSE` to always continue and only inspect the log. |

---

## Local execution (Windows PowerShell)

```powershell
cd "C:\path\to\1-input-data-format-validation"

docker build -t input-data-format-validation:0.0.1 .

docker run --rm `
  -v "${PWD}/resources/example/data/inputs:/mnt/inputs:ro" `
  -v "${PWD}/resources/example/data/outputs:/mnt/outputs" `
  input-data-format-validation:0.0.1
```

## resources/example/data/execution-parameters.json

```json
{
  "parameters": [
    { "name": "stopOnErrors", "defaultValue": "TRUE", "value": "TRUE" }
  ]
}
```

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

## The `tables_config.txt` configuration file

This is a **JSON array** (`[...]`), where each element (`{...}`) describes one
table type and its validation rules. One config entry covers all files whose
name matches the given `path` glob pattern.

```
[
  { ...rules for AMMONIUM files... },
  { ...rules for ANIONS files... },
  { ...rules for ALKALINITY files... },
  ...
]
```

### Full reference of every field

---

#### `type` — table identifier
- **What:** A short label to identify this entry (used only for readability).
- **Required:** No (but recommended for clarity).
- **Accepted values:** Any string, e.g. `"Ammonium"`, `"phWeighted"`, `"Alkalinity"`.
- **Example:**
```json
"type": "Ammonium"
```

---

#### `path` — file matching pattern
- **What:** A glob pattern that selects which files this entry applies to.
  The pattern is matched against filenames relative to the ZIP extraction folder.
- **Required:** Yes.
- **Accepted values:** Any glob string. Use `*` as wildcard.
- **Examples:**
```json
"path": "*_AMMONIUM*"       ← matches any file with AMMONIUM in the name
"path": "*_ANIONS*"
"path": "*_pH_COND*"
"path": "*_ALKALINITY*"
```

---

#### `schema` — column definitions
- **What:** An object where each key is a column name and each value defines
  the expected data type. Only columns listed here are type-checked.
  Columns not listed are ignored (not validated).
- **Required:** Yes.
- **Accepted type values:**

| Value | Meaning |
|-------|---------|
| `"float"` | Numeric value (integer or decimal). Non-numeric values trigger a critical error. |
| `"object"` | Text / string. No type check applied — any value is accepted. |
| `{"type": "datetime", "format": "..."}` | Date. The `format` follows Python `strptime` notation (e.g. `"%d/%m/%Y"`). Invalid dates trigger a critical error. |

- **Example:**
```json
"schema": {
  "SampleID":          "object",
  "SiteCode":          "object",
  "SiteName":          "object",
  "EndDate":           {"type": "datetime", "format": "%d/%m/%Y"},
  "year":              "float",
  "month":             "float",
  "NH4N(mg/l)":        "float",
  "Comments":          "object"
}
```

---

#### `critical_columns` — columns that must not be empty
- **What:** List of column names that must exist AND must not have any empty
  (NaN) values. If a critical column is completely empty → critical error.
  If it has at least one empty value → critical error.
- **Required:** No (defaults to no critical checks if omitted).
- **Accepted values:** Array of column name strings. Columns must also be in `schema`.
- **Example:**
```json
"critical_columns": ["SampleID", "SiteCode", "SiteName", "EndDate", "year", "month"]
```

---

#### `optional_columns` — columns that generate warnings when empty
- **What:** List of column names whose emptiness is reported as a warning (⚠️)
  rather than a critical error. Useful for parameters that are measured most
  of the time but occasionally absent.
- **Required:** No.
- **Accepted values:** Array of column name strings.
- **Example:**
```json
"optional_columns": ["NH4N(mg/l)", "Comments", "Volume(ml)", "DOC(mg/l)"]
```

---

#### `no_negatives` — columns that must not contain negative values
- **What:** List of column names where negative values are physically
  impossible (concentrations, volumes, pH). Any negative value triggers a
  critical error. Non-numeric values in these columns are ignored (already
  caught by the type check).
- **Required:** No.
- **Accepted values:** Array of column name strings (must be numeric columns).
- **Example:**
```json
"no_negatives": ["NH4N(mg/l)", "CA(mg/l)", "Volume(ml)", "pH", "Conductivity(µS/cm)"]
```

---

#### `expected_ranges` — soft bounds that generate warnings
- **What:** An object where each key is a column name and the value is a
  `[min, max]` array defining the expected range. Values outside the range
  generate a warning (⚠️), not a critical error — they may be valid but
  unusual.
- **Required:** No.
- **Accepted values:** Object where values are two-element arrays `[number, number]`.
- **Example:**
```json
"expected_ranges": {
  "pH":                  [0, 14],
  "Conductivity(µS/cm)": [0, 500],
  "AbsO3":               [0, 200]
}
```

---

#### `formats` — regex pattern validation
- **What:** An object where each key is a column name and the value is a
  regular expression string. Each non-empty value in the column is matched
  against the regex. Values that do not match trigger a critical error.
- **Required:** No.
- **Accepted values:** Object where values are regex strings (Python `re` syntax).
- **Example:**
```json
"formats": {
  "Saturated(Y/N)": "^(Y|N)?$"
}
```
  This accepts `Y`, `N`, or empty (the `?` makes the whole group optional).

---

### Complete config example — AMMONIUM entry

```json
{
  "type": "Ammonium",
  "path": "*_AMMONIUM*",
  "schema": {
    "SampleID":   "object",
    "SiteCode":   "object",
    "SiteName":   "object",
    "EndDate":    {"type": "datetime", "format": "%d/%m/%Y"},
    "year":       "float",
    "month":      "float",
    "NH4N(mg/l)": "float",
    "Comments":   "object"
  },
  "critical_columns": ["SampleID", "SiteCode", "SiteName", "EndDate", "year", "month"],
  "optional_columns": ["NH4N(mg/l)", "Comments"],
  "no_negatives":     ["NH4N(mg/l)"],
  "formats":          {},
  "expected_ranges":  {}
}
```

### Complete config example — pH/Conductivity entry

```json
{
  "type": "phWeighted",
  "path": "*_pH_COND*",
  "schema": {
    "SampleID":              "object",
    "SiteCode":              "object",
    "SiteName":              "object",
    "StartDate":             {"type": "datetime", "format": "%d/%m/%Y"},
    "EndDate":               {"type": "datetime", "format": "%d/%m/%Y"},
    "year":                  "float",
    "month":                 "float",
    "VolumeCollector(ml)":   "float",
    "Conductivity(µS/cm)":   "float",
    "Temperature(ºC)":       "float",
    "pH":                    "float",
    "DO(%)":                 "float",
    "DO(ppm)":               "float",
    "Comments":              "object"
  },
  "critical_columns": ["SampleID", "SiteCode", "SiteName", "year", "month"],
  "optional_columns": ["VolumeCollector(ml)", "Conductivity(µS/cm)", "Temperature(ºC)",
                       "pH", "DO(%)", "DO(ppm)", "Comments"],
  "no_negatives":     ["VolumeCollector(ml)", "Conductivity(µS/cm)", "pH",
                       "DO(%)", "DO(ppm)"],
  "formats":          {"Saturated(Y/N)": "^(Y|N)?$"},
  "expected_ranges":  {}
}
```

### Complete config example — ALKALINITY entry

```json
{
  "type": "Alkalinity",
  "path": "*_ALKALINITY*",
  "schema": {
    "SampleID":            "object",
    "SiteCode":            "object",
    "SiteName":            "object",
    "year":                "float",
    "month":               "object",
    "HCLVolume(ml)":       "float",
    "pH":                  "float",
    "HCL(mol/l)":          "float",
    "SamplingVolume(ml)":  "float",
    "Comments":            "object"
  },
  "critical_columns": ["SampleID", "SiteCode", "SiteName", "year", "month",
                       "HCLVolume(ml)", "pH", "HCL(mol/l)", "SamplingVolume(ml)"],
  "optional_columns": ["Comments"],
  "no_negatives":     ["HCLVolume(ml)", "pH", "HCL(mol/l)", "SamplingVolume(ml)"],
  "formats":          {},
  "expected_ranges":  {}
}
```

---

## Adapting this component to other Excel files

To use this component with a completely different set of Excel files:

1. Make sure every Excel file has a sheet named **`data`**.
2. Create a `tables_config.txt` following the format above, with one entry
   per file type.
3. For each entry:
   - Set `path` to a glob pattern that matches your filenames.
   - In `schema`, list all columns with their expected types.
   - In `critical_columns`, list columns that must always have values.
   - In `optional_columns`, list columns where empty values are acceptable.
   - In `no_negatives`, list numeric columns where negatives are invalid.
   - In `expected_ranges`, add soft bounds for any numeric column.
   - In `formats`, add regex constraints for any text column with a fixed format.
4. Put all Excel files in a ZIP named `allData.zip`, place it in
   `resources/example/data/inputs/` together with `tables_config.txt`, and run
   the component.

---

## Notes

- Non-numeric values in numeric columns are coerced to NaN before range/negative
  checks. Type errors and range errors are reported independently.
- The string `"n.a"` and `"n.a."` are treated as missing values (NaN) throughout.
- The `path` patterns in the config are matched against absolute paths after
  extraction, so the glob only needs to match the filename portion.
- If `stopOnErrors = FALSE`, the validation log is still written but the
  wrapper exits with code 0 even when critical errors are found. This allows
  inspecting all errors before deciding whether to proceed.
