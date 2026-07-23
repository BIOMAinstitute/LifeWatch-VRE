# 3 — LOQ Application

Applies the Limit of Quantification (LOQ) to water chemistry CSV files.
Values below the LOQ for a given element or compound are replaced by **LOQ / 2**,
which is the standard half-LOQ substitution method for left-censored analytical
data in environmental chemistry. Every substitution is recorded in a
traceability log.

---

## Workflow position

```
WaterChemicalDataTransformation  →  LoqApplication  →  UnitTransformation
```

---

## Inputs

| Name | Type | Path | Description |
|------|------|------|-------------|
| input-data | Zip | `/mnt/inputs/water_chemical_data_transformed.zip` | ZIP of tab-separated CSV files from component 2. |

## Outputs

| Name | Type | Path | Description |
|------|------|------|-------------|
| output-data | Zip | `/mnt/outputs/water_chemical_data_transformed_loq.zip` | Same CSV files with LOQ substitutions applied. |
| output-log | Text | `/mnt/outputs/level1_loq/loq_substitutions.log` | Tab-separated traceability log: FILE, ROW, COLUMN, ORIGINAL_VALUE, LOQ, REPLACED_BY. |

---

## Parameters

All 24 parameters are the LOQ values for each measurable element or compound.
The defaults correspond to the detection limits of the ICP laboratory
equipment at BIOMA – University of Navarra. **They can be changed if your
laboratory uses different instruments with different detection limits.**

Column matching is **case-insensitive** — `NH4N(mg/l)`, `nh4n(mg/l)` and
`Nh4N(Mg/L)` all map to the same LOQ. Original column casing is preserved
in the output files.

| Parameter | Default | Unit | Element / compound |
|-----------|---------|------|--------------------|
| `param_WeightedConductivity` | `3.0` | µS/cm | Weighted electrical conductivity |
| `param_NH4N` | `0.04` | mg/L | Ammonium-nitrogen (NH₄-N) |
| `param_NO3` | `0.05` | mg/L | Nitrate (NO₃) |
| `param_SO4` | `0.1` | mg/L | Sulphate (SO₄) |
| `param_CL` | `0.05` | mg/L | Chloride (Cl) |
| `param_AS` | `0.000025` | mg/L | Arsenic (As) |
| `param_CD` | `0.000008` | mg/L | Cadmium (Cd) |
| `param_CR` | `0.000037` | mg/L | Chromium (Cr) |
| `param_CU` | `0.000062` | mg/L | Copper (Cu) |
| `param_CO` | `0.00001` | mg/L | Cobalt (Co) |
| `param_NI` | `0.000073` | mg/L | Nickel (Ni) |
| `param_PB` | `0.000011` | mg/L | Lead (Pb) |
| `param_ZN` | `0.000049` | mg/L | Zinc (Zn) |
| `param_P` | `0.016603` | mg/L | Phosphorus (P) |
| `param_S` | `0.5` | mg/L | Sulphur (S) |
| `param_CA` | `0.15` | mg/L | Calcium (Ca) |
| `param_K` | `0.15` | mg/L | Potassium (K) |
| `param_MG` | `0.03` | mg/L | Magnesium (Mg) |
| `param_NA` | `0.04` | mg/L | Sodium (Na) |
| `param_AL` | `0.01` | mg/L | Aluminium (Al) |
| `param_FE` | `0.005` | mg/L | Iron (Fe) |
| `param_MN` | `0.005` | mg/L | Manganese (Mn) |
| `param_DOC` | `0.5` | mg/L | Dissolved organic carbon (DOC) |
| `param_TN` | `0.1` | mg/L | Total nitrogen (TN) |

---

## Local execution (Windows PowerShell)

```powershell
cd "C:\path\to\3-laboratory-quantification-limit-application"

docker build -t laboratory-quantification-limit-application:0.0.1 .

docker run --rm `
  -v "${PWD}/resources/example/data/inputs:/mnt/inputs:ro" `
  -v "${PWD}/resources/example/data/outputs:/mnt/outputs" `
  laboratory-quantification-limit-application:0.0.1 `
```

## resources/example/data/execution-parameters.json

```json
{
  "parameters": [
    { "name": "param_WeightedConductivity", "defaultValue": "3.0",      "value": "3.0"      },
    { "name": "param_NH4N",                 "defaultValue": "0.04",     "value": "0.04"     },
    { "name": "param_NO3",                  "defaultValue": "0.05",     "value": "0.05"     },
    { "name": "param_SO4",                  "defaultValue": "0.1",      "value": "0.1"      },
    { "name": "param_CL",                   "defaultValue": "0.05",     "value": "0.05"     },
    { "name": "param_AS",                   "defaultValue": "0.000025", "value": "0.000025" },
    { "name": "param_CD",                   "defaultValue": "0.000008", "value": "0.000008" },
    { "name": "param_CR",                   "defaultValue": "0.000037", "value": "0.000037" },
    { "name": "param_CU",                   "defaultValue": "0.000062", "value": "0.000062" },
    { "name": "param_CO",                   "defaultValue": "0.00001",  "value": "0.00001"  },
    { "name": "param_NI",                   "defaultValue": "0.000073", "value": "0.000073" },
    { "name": "param_PB",                   "defaultValue": "0.000011", "value": "0.000011" },
    { "name": "param_ZN",                   "defaultValue": "0.000049", "value": "0.000049" },
    { "name": "param_P",                    "defaultValue": "0.016603", "value": "0.016603" },
    { "name": "param_S",                    "defaultValue": "0.5",      "value": "0.5"      },
    { "name": "param_CA",                   "defaultValue": "0.15",     "value": "0.15"     },
    { "name": "param_K",                    "defaultValue": "0.15",     "value": "0.15"     },
    { "name": "param_MG",                   "defaultValue": "0.03",     "value": "0.03"     },
    { "name": "param_NA",                   "defaultValue": "0.04",     "value": "0.04"     },
    { "name": "param_AL",                   "defaultValue": "0.01",     "value": "0.01"     },
    { "name": "param_FE",                   "defaultValue": "0.005",    "value": "0.005"    },
    { "name": "param_MN",                   "defaultValue": "0.005",    "value": "0.005"    },
    { "name": "param_DOC",                  "defaultValue": "0.5",      "value": "0.5"      },
    { "name": "param_TN",                   "defaultValue": "0.1",      "value": "0.1"      }
  ]
}
```

---

## What this component does

For each CSV file in the input ZIP and for each column whose name matches one
of the 24 known elements/compounds:

1. Compares each value against the corresponding LOQ.
2. If the value is **below the LOQ** → replaces it with **LOQ / 2**.
3. Logs the substitution (file, row, column, original value, LOQ, replacement).
4. Writes the corrected CSV to the output ZIP.

Values equal to or above the LOQ are left unchanged. NaN (missing) values are
ignored. Non-numeric values in a numeric column are coerced to NaN before the
comparison.

### Why LOQ / 2?

The LOQ is the minimum concentration that the laboratory instrument can reliably
quantify. Values reported below the LOQ exist but are too close to the noise
floor to be trustworthy as exact measurements — they are **left-censored data**.

Setting them to zero would underestimate the true concentration. Keeping the
original sub-LOQ value would overstate analytical precision. The standard
convention in environmental chemistry (and the one recommended by ICP-Forest)
is to substitute with **LOQ / 2**, which acknowledges that the concentration
is low while contributing a reasonable non-zero estimate to aggregate
calculations such as ionic balance and weighted means.

---

## Input CSV format

The component accepts any ZIP containing tab-separated (``\t``) CSV files where
column names follow the ``{ELEMENT}(unit)`` convention. This is exactly the
format produced by Component 2. Below is the structure of each CSV type with
the columns that will be checked against the LOQ.

### AMMONIUM CSV
```
SampleID  SiteCode  SiteName  StartDate  EndDate  year  month  NH4N(mg/l)  Comments
05PS INT  5         Valsain              2025-01-24  2025  1  0.151
```
**LOQ-checked column:** `NH4N(mg/l)`

---

### ANIONS CSV
```
SampleID  SiteCode  SiteName  StartDate  EndDate  year  month  CL(mg/l)  NO3(mg/l)  SO4(mg/l)  PO4(mg/l)  Comments
05PS INT  5         Valsain              2025-01-24  2025  1  1.4493    0.578      0.3809
```
**LOQ-checked columns:** `CL(mg/l)`, `NO3(mg/l)`, `SO4(mg/l)`
> Note: `PO4(mg/l)` is not in the LOQ parameter list and will be left unchanged.

---

### CATIONS CSV
```
SampleID  SiteCode  SiteName  StartDate  EndDate  year  month  CA(mg/l)  MG(mg/l)  NA(mg/l)  K(mg/l)  AL(mg/l)  FE(mg/l)  MN(mg/l)  AS(mg/l)  CD(mg/l)  CR(mg/l)  CU(mg/l)  CO(mg/l)  NI(mg/l)  PB(mg/l)  ZN(mg/l)  P(mg/l)  S(mg/l)  Comments
05PS INT  5         Valsain              2025-01-24  2025  1  0.664781  0.141924  0.853     0.89     0.01753   0.006429  0.028052
```
**LOQ-checked columns:** `CA(mg/l)`, `MG(mg/l)`, `NA(mg/l)`, `K(mg/l)`, `AL(mg/l)`, `FE(mg/l)`, `MN(mg/l)`, `AS(mg/l)`, `CD(mg/l)`, `CR(mg/l)`, `CU(mg/l)`, `CO(mg/l)`, `NI(mg/l)`, `PB(mg/l)`, `ZN(mg/l)`, `P(mg/l)`, `S(mg/l)`

---

### DOC_TN CSV
```
SampleID  SiteCode  SiteName  StartDate  EndDate  year  month  DOC(mg/l)  TN(mg/l)  Comments
05PS INT  5         Valsain              2025-01-24  2025  1  4.266      0.2906
```
**LOQ-checked columns:** `DOC(mg/l)`, `TN(mg/l)`

---

### pH / Conductivity CSV
```
SampleID  SiteCode  SiteName  ...  WeightedConductivity(µS/cm)  WeightedpH  H(µeq/l)  ...
05PS INT  5         Valsain   ...  13.133                       6.127       0.747      ...
```
**LOQ-checked column:** `WeightedConductivity(µS/cm)`
> Note: pH, H(µeq/l) and other derived columns are not in the LOQ parameter list
> and will be left unchanged.

---

### ALKALINITY CSV
```
SampleID  SiteCode  SiteName  year  month  AlkalinityICPForests(µeq/l)
05PSINT   5         Valsain   2025  1      45.533
```
**LOQ-checked columns:** none — alkalinity in µeq/l does not have an
associated LOQ parameter in this component. The ALKALINITY CSV passes through
unchanged (it is still included in the output ZIP).

---

## Reusing this component with other datasets

This component can be applied to **any ZIP of tab-separated CSV files** as long
as the following conditions are met:

### ✅ Requirements

1. **Column naming convention:** analytical columns must follow the pattern
   `{ELEMENT}(mg/l)` (or `{ELEMENT}(µS/cm)` for conductivity). The component
   recognises columns by their exact lowercase name after stripping spaces
   (see the full list in the Parameters table above).

2. **Tab separator:** files must use `\t` as the column delimiter.

3. **Header row:** the first row must be the column names.

4. **Numeric values:** concentration columns must contain numbers (or be empty).
   Non-numeric text in a numeric column is coerced to NaN and ignored.

### ⚠️ Important constraint — only the 24 listed elements are checked

The component only applies LOQ substitution to the **24 elements and compounds**
listed in the Parameters table. If your dataset contains other analytes
(e.g. `HG(mg/l)`, `BR(mg/l)`, `F(mg/l)`), those columns will pass through the
component without any LOQ check. The component does not raise an error for
unrecognised columns — it simply ignores them.

This means the component is directly reusable for any water chemistry dataset
that measures a **subset** of these 24 analytes. If your dataset measures all
24, all will be checked. If it only measures 5, only those 5 will be checked.

### ⚠️ LOQ values are instrument-specific

The default LOQ values correspond to the specific laboratory equipment used in
the ICP-Forest workflow at BIOMA – University of Navarra. **If you use different
instruments, you must provide your own LOQ values as parameters.** Using the
defaults with a different instrument may result in incorrect substitutions
(too few or too many).

### Example: reusing with a different dataset

If you have a ZIP of CSV files from a different project measuring Ca, Mg, K and
Na in water samples with a different instrument, you would:

1. Ensure your CSVs are tab-separated with columns `CA(mg/l)`, `MG(mg/l)`,
   `K(mg/l)`, `NA(mg/l)`.
2. Set the four relevant parameters to your instrument's LOQ values.
3. Leave all other parameters at their defaults — they will simply be skipped
   because those column names are not present in your files.

---

## Traceability log format

The log file `loq_substitutions.log` is tab-separated with one row per
substitution:

```
FILE                    ROW  COLUMN      ORIGINAL_VALUE  LOQ     REPLACED_BY
5_WATER_AMMONIUM.csv    3    nh4n(mg/l)  0.017           0.04    0.02
5_WATER_CATIONS.csv     7    al(mg/l)    0.003           0.01    0.005
```

Column names in the log are lowercased (the internal working format).
The original column casing is preserved in the output CSV files.

---

## Notes

- Files in the input ZIP that are not `.csv` are silently ignored.
- A CSV file that contains none of the 24 recognised columns is copied to
  the output unchanged (ALKALINITY CSVs typically fall into this category).
- The output ZIP contains both the corrected CSVs **and** the log file,
  so the full audit trail is preserved in a single archive.
