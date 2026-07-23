# 2 — Water Chemical Data Transformation

Transforms validated Excel templates into analysis-ready tab-separated CSV
files. Each template type requires a different transformation, and the
component **handles each type independently** — if only ALKALINITY files are
present, only the alkalinity transformation runs; if only pH/conductivity
files are present, only the weighted averages are computed. This makes the
component reusable for any subset of subprograms.

---

## Workflow position

```
InputDataFormatValidation  →  WaterChemicalDataTransformation  →  LoqApplication
```

---

## Inputs

| Name | Type | Path | Description |
|------|------|------|-------------|
| input-data | Zip | `/mnt/inputs/allData_templates_format_validated.zip` | ZIP of validated Excel files from component 1. Each file must have a sheet named `data`. |

## Outputs

| Name | Type | Path | Description |
|------|------|------|-------------|
| output-data | Zip | `/mnt/outputs/water_chemical_data_transformed.zip` | ZIP of tab-separated CSV files, one per SiteCode per subprogram. |

## Parameters

None.

---

## Local execution (Windows PowerShell)

```powershell
cd "C:\path\to\2-water-chemical-data-transformation"

docker build -t water-chemical-data-transformation:0.0.1 .

docker run --rm `
  -v "${PWD}/resources/example/data/inputs:/mnt/inputs:ro" `
  -v "${PWD}/resources/example/data/outputs:/mnt/outputs" `
  water-chemical-data-transformation:0.0.1
```

## resources/example/data/execution-parameters.json

```json
{ "parameters": [] }
```

---

## What this component does — transformation by template type

The component scans the input ZIP and identifies each file by keywords in its
name. It then applies the appropriate transformation. **Each transformation
is fully independent** — the component skips any type for which no files are
found and prints a message. The three transformation types are:

---

### 1. ALKALINITY — Gran method linear regression

**Triggered by:** files with `ALKALINITY` in the filename.
**Output:** `<SiteCode>_WATER_ALKALINITY.csv`

**What it does:**

The alkalinity template contains multiple titration rows per sample (see
Component 1 README for the template structure). Each row records the pH
measured after adding a cumulative volume of HCl to the sample. The
transformation uses these rows to compute alkalinity in µeq/l following
the **Gran method** (Gran, 1952), which is the recommended approach for
low-alkalinity waters.

**Step-by-step:**

1. **Select 4 reference points per sample.** From all the titration rows for
   a given sample, the 4 rows whose pH values are closest to the reference
   points `[4.0, 4.2, 4.3, 4.5]` are selected. One row per reference point,
   without replacement (each row can only be used once).

2. **Transform the selected rows.** For each selected row, a Gran function
   value is computed:

   ```
   F = 10^(-pH) × (V_HCl + V_sample) / 1000 × 10
   ```
   where `V_HCl` is the cumulative HCl volume (ml) and `V_sample` is the
   sample volume (ml).

3. **Linear regression.** A linear regression is fitted with `V_HCl` on the
   x-axis and the Gran function value `F` on the y-axis. The x-axis intercept
   (where `F = 0`) gives the equivalence point of the titration.

4. **Compute alkalinity.** From the x-intercept and the HCl concentration:

   ```
   Alkalinity (µeq/l) = (((-intercept / slope) / 1000) × C_HCl
                        / V_sample / 1000 × 100 × 10 × 1000) × 1,000,000
   ```
   where `C_HCl` is in mol/l and `V_sample` is in ml.
   Negative alkalinity values are set to 0.

**Output columns:** `SampleID`, `SiteCode`, `SiteName`, `year`, `month`,
`AlkalinityICPForests(µeq/l)`

**Reuse note:** This transformation can be used standalone for any dataset
that follows the ALKALINITY template structure described in Component 1.
If your ZIP contains only ALKALINITY files, only this transformation will
run and you will get one CSV per SiteCode with the computed alkalinity values.

---

### 2. pH / Conductivity — volume-weighted averages

**Triggered by:** files with `PH_COND_WEIGHTED_RAW` in the filename.
**Output:** `<SiteCode>_WATER_pH_COND_WEIGHTED_RAW.csv`

**What it does:**

The pH/conductivity template has multiple rows per composite sample — one row
per individual collector (bottle) before mixing (see Component 1 README).
Collectors belonging to the same composite sample share the same `SampleID`.
The transformation aggregates these individual measurements into a single
representative value per sample per month.

**Computed values per sample:**

| Output column | Computation | Formula |
|---------------|-------------|---------|
| `Volume(ml)` | Total volume | Sum of `VolumeCollector(ml)` across all collectors of the sample |
| `Temperature(ºC)` | Simple average | Mean of `Temperature(ºC)` across collectors (NaN-safe) |
| `DO(%)` | Simple average | Mean of `DO(%)` across collectors (NaN-safe) |
| `DO(ppm)` | Simple average | Mean of `DO(ppm)` across collectors (NaN-safe) |
| `Precip(l/m2)` | Estimated precipitation | `(TotalVolume_L) / (n_collectors × sampler_radius)` — only computed when `sampler_radius` is provided |
| `WeightedConductivity(µS/cm)` | Volume-weighted mean | `Σ(V_i × EC_i) / Σ(V_i)` where `V_i` is the collector volume and `EC_i` is its conductivity |
| `WeightedHydron(µeq/l)` | Volume-weighted H⁺ | `Σ(V_i × 10^(pH_i)) / Σ(V_i)` |
| `WeightedpH` | pH from weighted H⁺ | `log10(WeightedHydron)` |
| `H(µeq/l)` | H⁺ concentration | `10^(-WeightedpH) × 10^6` |

**Why volume-weighted pH?**

Averaging pH values directly is mathematically incorrect because pH is a
logarithmic scale. The correct approach is to convert each pH measurement to
its hydrogen ion concentration `[H⁺] = 10^(-pH)`, compute the volume-weighted
mean of `[H⁺]`, and then convert back to pH. This correctly weights the
contribution of each collector according to the volume of water it captured.

**Handling single-collector samples:** If a sample has only one collector
(no mixing needed), the transformation still runs correctly — the weighted
average of a single value equals that value.

**Output columns:** `SampleID`, `SiteCode`, `SiteName`, `StartDate`, `EndDate`,
`year`, `month`, `Temperature(ºC)`, `DO(%)`, `DO(ppm)`, `Volume(ml)`,
`Precip(l/m2)`, `WeightedConductivity(µS/cm)`, `WeightedHydron(µeq/l)`,
`WeightedpH`, `H(µeq/l)`, `Comments`

**Reuse note:** This transformation can be used standalone for any dataset
where individual collector measurements need to be aggregated into
volume-weighted composite values. The only requirement is the template
structure described in Component 1 (columns `SampleID`, `VolumeCollector(ml)`,
`pH`, `Conductivity(µS/cm)`, optionally `sampler_radius`).

---

### 3. AMMONIUM / ANIONS / CATIONS / DOC_TN — consolidation

**Triggered by:** files with `AMMONIUM`, `ANIONS`, `CATIONS`, or `DOC_TN`
in the filename. Each keyword is processed independently.
**Output:** `<SiteCode>_WATER_<SUBPROGRAM>.csv`

**What it does:**

These templates already contain one row per composite sample — no mathematical
transformation is needed. The component:

1. Reads all files for the subprogram (across all months).
2. Groups rows by `SiteCode`.
3. Concatenates all monthly data for each SiteCode into a single dataset.
4. Deduplicates by `SampleID`, `SiteCode`, `SiteName`, `EndDate` — keeping
   the first occurrence if the same sample appears more than once.

**Output columns:** same as the input template columns.

**Reuse note:** These four subprograms are independent of each other. If your
ZIP contains only CATIONS files, for example, only the CATIONS output CSV
will be produced. The component prints a message for each subprogram for which
no files are found.

---

## How files are identified

The component scans filenames for the following keywords (case-insensitive):

| Keyword | Template type |
|---------|---------------|
| `ALKALINITY` | Alkalinity titration data |
| `PH_COND_WEIGHTED_RAW` | pH and conductivity per collector |
| `AMMONIUM` | Ammonium concentration |
| `ANIONS` | Anion concentrations (Cl, NO3, SO4, PO4) |
| `CATIONS` | Cation and heavy metal concentrations |
| `DOC_TN` | Dissolved organic carbon and total nitrogen |

Files not matching any keyword are silently ignored.

---

## How SiteCode is determined

SiteCode is read from the **`SiteCode` column inside each Excel file** — never
from the filename. A single file may contain rows belonging to multiple
SiteCodes. The component groups all rows by SiteCode and produces one output
CSV per SiteCode per subprogram.

---

## How replicate (REP) files are handled

If a filename contains `_REP` (case-insensitive), the string `_REP` is
appended to every `SampleID` in that file. This distinguishes replicate
measurements from originals in the output CSVs, while keeping them in the
same dataset for subsequent steps.

Example: a sample `05PS INT` in file `2025_01_FOREST_AMMONIUM_REP.xlsx`
becomes `05PS INT_REP` in the output CSV.

---

## Output file naming

```
<SiteCode>_WATER_ALKALINITY.csv
<SiteCode>_WATER_pH_COND_WEIGHTED_RAW.csv
<SiteCode>_WATER_AMMONIUM.csv
<SiteCode>_WATER_ANIONS.csv
<SiteCode>_WATER_CATIONS.csv
<SiteCode>_WATER_DOC_TN.csv
```

All CSVs are tab-separated (`\t`) and include a header row.
They are bundled into `water_chemical_data_transformed.zip`.

---

## Notes

- All output CSVs use tab (`\t`) as the column separator.
- The strings `"n.a"` and `"n.a."` are treated as missing values (NaN) throughout.
- Deduplication for AMMONIUM/ANIONS/CATIONS/DOC_TN is done on
  `(SampleID, SiteCode, SiteName, EndDate)` — the first occurrence is kept
  when duplicates are found.
- Deduplication for pH/conductivity is done on
  `(SiteCode, SampleID, EndDate, month)`.
- If a SiteCode value is NaN or missing, that row is excluded from all outputs.
