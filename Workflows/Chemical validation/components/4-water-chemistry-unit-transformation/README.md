# 4 — Unit Transformation

Converts water chemistry measurements to a standardised set of three units
per analyte: **mg/l**, **µg/l** and **µeq/l**. The transformation is
**unit-agnostic**: the input unit is automatically detected from the column
name (e.g. `NH4N(µg/l)`) and the three output columns are generated regardless
of which unit was originally used. If only one unit representation exists in
the input, all three will exist in the output.

Also handles four paired cross-conversions between molecular and elemental
forms, generating both representations simultaneously:
- NH4 ↔ NH4N (ammonium / ammonium-nitrogen)
- NO3 ↔ NO3N (nitrate / nitrate-nitrogen)
- SO4 ↔ SO4S (sulphate / sulphate-sulphur)
- PO4 ↔ PO4P (phosphate / phosphate-phosphorus)

---

## Workflow position

```
LoqApplication  →  UnitTransformation  →  WaterChemistryValidation
```

---

## Inputs

| Name | Type | Path | Description |
|------|------|------|-------------|
| input-data | Zip | `/mnt/inputs/water_chemical_data_level1_loq.zip` | ZIP of tab-separated CSV files from component 3. |

## Outputs

| Name | Type | Path | Description |
|------|------|------|-------------|
| output-data | Zip | `/mnt/outputs/water_chemical_data_level1_units.zip` | Same CSV files with three unit columns added per recognised analyte. |

## Parameters

None. The transformation is fully deterministic from the column names and
the built-in chemical constants (atomic weights, molecular weights, valences).

---

## Local execution (Windows PowerShell)

```powershell
cd "C:\path\to\4-unit-transformation"

docker build -t unit-transformation:0.0.1 .

docker run --rm `
  -v "${PWD}/resources/example/data/inputs:/mnt/inputs:ro" `
  -v "${PWD}/resources/example/data/outputs:/mnt/outputs" `
  unit-transformation:0.0.1
```

## resources/example/data/execution-parameters.json

```json
{ "parameters": [] }
```

---

## Understanding the three units

For each analyte, the component generates three columns covering the two
most common measurement conventions in water chemistry:

### mg/l — mass concentration
The mass of the element or compound dissolved per litre of water.
This is the unit typically reported by laboratory instruments and
recorded in the original templates.

```
Example: CA(mg/l) = 0.665
→ 0.665 mg of calcium per litre of water
```

### µg/l — micro mass concentration
The same as mg/l but expressed at the micro scale. Useful for trace
elements whose concentrations are very small as mg/l values.

```
Conversion: µg/l = mg/l × 1000

Example: CA(mg/l) = 0.665  →  CA(µg/l) = 665
         AS(mg/l) = 0.000025  →  AS(µg/l) = 0.025
```

### µeq/l — microequivalent concentration (charge-based)
This is the electrochemical unit used for **ion balance calculations**.
It expresses the number of electric charges (equivalents) per litre,
scaled to the micro level. Unlike mg/l, it accounts for both the
molecular weight and the ionic charge (valence) of the element.

This unit is essential for checking whether the sum of positive ions
(cations) equals the sum of negative ions (anions) in a water sample —
a fundamental physicochemical constraint used in Component 5.

```
Conversion: µeq/l = mg/l × valence / molecular_weight × 1000

Example: CA(mg/l) = 0.665
         Ca atomic weight = 40.08 g/mol, valence = 2
         CA(µeq/l) = 0.665 × 2 / 40.08 × 1000 = 33.18 µeq/l

Example: SO4(mg/l) = 0.381
         SO4 molecular weight = 95.996 g/mol, valence = 2
         SO4S(µeq/l) = 0.381 × 2 / 95.996 × 1000 = 7.94 µeq/l
```

**Why does valence matter?** A calcium ion (Ca²⁺) carries 2 positive
charges, so 1 mg/l of calcium contributes twice as many charge equivalents
as 1 mg/l of sodium (Na⁺, valence 1). The µeq/l unit normalises for this,
making concentrations of different ions directly comparable for charge balance.

---

## Elements and compounds supported

The component recognises analytes by their name in the column header
(case-insensitive). Below is the complete list of supported analytes with
the chemical constants used for conversion.

### Elements and ions

| Analyte | Column name | Atomic weight (g/mol) | Valence | Notes |
|---------|------------|----------------------|---------|-------|
| Arsenic | `AS(mg/l)` | 74.992 | 5 | Trace metal |
| Cadmium | `CD(mg/l)` | 112.41 | 2 | Trace metal |
| Chromium | `CR(mg/l)` | 51.996 | 6 | Trace metal |
| Copper | `CU(mg/l)` | 63.546 | 2 | Trace metal |
| Cobalt | `CO(mg/l)` | 58.933 | 6 | Trace metal |
| Nickel | `NI(mg/l)` | 58.693 | 2 | Trace metal |
| Lead | `PB(mg/l)` | 207.20 | 2 | Trace metal |
| Zinc | `ZN(mg/l)` | 65.380 | 2 | Trace metal |
| Phosphorus | `P(mg/l)` | 30.974 | 3 | Element |
| Sulphur | `S(mg/l)` | 32.065 | 2 | Element |
| Calcium | `CA(mg/l)` | 40.08 | 2 | Major cation |
| Magnesium | `MG(mg/l)` | 24.31 | 2 | Major cation |
| Sodium | `NA(mg/l)` | 22.99 | 1 | Major cation |
| Potassium | `K(mg/l)` | 39.1 | 1 | Major cation |
| Aluminium | `AL(mg/l)` | 26.982 | 3 | Metal |
| Iron | `FE(mg/l)` | 55.8 | 2 | Metal |
| Manganese | `MN(mg/l)` | 54.938 | 1 | Metal |
| Chloride | `CL(mg/l)` | 35.45 | 1 | Major anion |

### Molecules

| Analyte | Column name | Molecular weight (g/mol) | Charge | Notes |
|---------|------------|--------------------------|--------|-------|
| Ammonium | `NH4(mg/l)` | 18.0 | 1 | |
| Nitrate | `NO3(mg/l)` | 61.997 | 1 | |
| Sulphate | `SO4(mg/l)` | 95.996 | 2 | |
| Phosphate | `PO4(mg/l)` | 94.974 | 3 | |
| Dissolved organic carbon | `DOC(mg/l)` | 12.0 (C) | 4 | Uses C atomic weight |

---

## Paired cross-conversions

In analytical chemistry, nitrogen-bearing and sulphur-bearing compounds are
sometimes reported in their molecular form (e.g. NO₃⁻) and sometimes as the
element alone (e.g. N from NO₃). Both representations carry the same
information but require different weights for conversion.

The component handles four such pairs automatically — **if either form is
present in the input, both forms are generated in the output**:

### NH4 ↔ NH4N

| Direction | Formula | Constants |
|-----------|---------|-----------|
| NH4N → NH4 | `NH4(mg/l) = NH4N(mg/l) × MW_NH4 / AW_N` | MW_NH4 = 18, AW_N = 14 |
| NH4 → NH4N | `NH4N(mg/l) = NH4(mg/l) × AW_N / MW_NH4` | |

### NO3 ↔ NO3N

| Direction | Formula | Constants |
|-----------|---------|-----------|
| NO3 → NO3N | `NO3N(mg/l) = NO3(mg/l) × AW_N / MW_NO3` | MW_NO3 = 61.997, AW_N = 14 |
| NO3N → NO3 | `NO3(mg/l) = NO3N(mg/l) × MW_NO3 / AW_N` | |

### SO4 ↔ SO4S

| Direction | Formula | Constants |
|-----------|---------|-----------|
| SO4 → SO4S | `SO4S(mg/l) = SO4(mg/l) × AW_S / MW_SO4` | MW_SO4 = 95.996, AW_S = 32.065 |
| SO4S → SO4 | `SO4(mg/l) = SO4S(mg/l) × MW_SO4 / AW_S` | |

### PO4 ↔ PO4P

| Direction | Formula | Constants |
|-----------|---------|-----------|
| PO4 → PO4P | `PO4P(mg/l) = PO4(mg/l) × AW_P / MW_PO4` | MW_PO4 = 94.974, AW_P = 30.974 |
| PO4P → PO4 | `PO4(mg/l) = PO4P(mg/l) × MW_PO4 / AW_P` | |

---

## What the output looks like — example per CSV type

Starting from the LOQ-corrected CSVs (same structure as Component 2 output,
see Component 3 README for the exact column layout), each recognised analyte
column is expanded into three. Below are the new columns added per CSV type.

### AMMONIUM CSV — columns added

| Original column | New columns generated |
|-----------------|----------------------|
| `NH4N(mg/l)` | `NH4N(mg/l)` (kept), `NH4N(µg/l)`, `NH4N(µeq/l)`, `NH4(mg/l)`, `NH4(µg/l)`, `NH4(µeq/l)` |

### ANIONS CSV — columns added

| Original column | New columns generated |
|-----------------|----------------------|
| `CL(mg/l)` | `CL(mg/l)`, `CL(µg/l)`, `CL(µeq/l)` |
| `NO3(mg/l)` | `NO3(mg/l)`, `NO3(µg/l)`, `NO3(µeq/l)`, `NO3N(mg/l)`, `NO3N(µg/l)`, `NO3N(µeq/l)` |
| `SO4(mg/l)` | `SO4(mg/l)`, `SO4(µg/l)`, `SO4(µeq/l)`, `SO4S(mg/l)`, `SO4S(µg/l)`, `SO4S(µeq/l)` |
| `PO4(mg/l)` | `PO4(mg/l)`, `PO4(µg/l)`, `PO4(µeq/l)`, `PO4P(mg/l)`, `PO4P(µg/l)`, `PO4P(µeq/l)` |

### CATIONS CSV — columns added

| Original column | New columns generated |
|-----------------|----------------------|
| `CA(mg/l)` | `CA(mg/l)`, `CA(µg/l)`, `CA(µeq/l)` |
| `MG(mg/l)` | `MG(mg/l)`, `MG(µg/l)`, `MG(µeq/l)` |
| `NA(mg/l)` | `NA(mg/l)`, `NA(µg/l)`, `NA(µeq/l)` |
| `K(mg/l)` | `K(mg/l)`, `K(µg/l)`, `K(µeq/l)` |
| `AL(mg/l)` | `AL(mg/l)`, `AL(µg/l)`, `AL(µeq/l)` |
| `FE(mg/l)` | `FE(mg/l)`, `FE(µg/l)`, `FE(µeq/l)` |
| `MN(mg/l)` | `MN(mg/l)`, `MN(µg/l)`, `MN(µeq/l)` |
| `AS(mg/l)` | `AS(mg/l)`, `AS(µg/l)`, `AS(µeq/l)` |
| `CD(mg/l)` | `CD(mg/l)`, `CD(µg/l)`, `CD(µeq/l)` |
| `CR(mg/l)` | `CR(mg/l)`, `CR(µg/l)`, `CR(µeq/l)` |
| `CU(mg/l)` | `CU(mg/l)`, `CU(µg/l)`, `CU(µeq/l)` |
| `CO(mg/l)` | `CO(mg/l)`, `CO(µg/l)`, `CO(µeq/l)` |
| `NI(mg/l)` | `NI(mg/l)`, `NI(µg/l)`, `NI(µeq/l)` |
| `PB(mg/l)` | `PB(mg/l)`, `PB(µg/l)`, `PB(µeq/l)` |
| `ZN(mg/l)` | `ZN(mg/l)`, `ZN(µg/l)`, `ZN(µeq/l)` |
| `P(mg/l)` | `P(mg/l)`, `P(µg/l)`, `P(µeq/l)` |
| `S(mg/l)` | `S(mg/l)`, `S(µg/l)`, `S(µeq/l)` |

### DOC_TN CSV — columns added

| Original column | New columns generated |
|-----------------|----------------------|
| `DOC(mg/l)` | `DOC(mg/l)`, `DOC(µg/l)`, `DOC(µeq/l)` |
| `TN(mg/l)` | not expanded (TN has no ionic charge and is not in the analyte dictionary) |

### ALKALINITY and pH/Conductivity CSVs

These CSVs (`AlkalinityICPForests(µeq/l)`, `WeightedConductivity(µS/cm)`,
`WeightedpH`, `H(µeq/l)` etc.) do not follow the `{ELEMENT}(mg/l)` pattern
and are not in the analyte dictionary. They pass through unchanged.

---

## Reusing this component with other datasets

This component can be applied to **any ZIP of tab-separated CSV files** as
long as these conditions are met:

### ✅ Requirements

1. **Column naming convention:** analyte columns must follow `{ANALYTE}({unit})`,
   e.g. `CA(mg/l)`, `NO3(µg/l)`, `SO4(µeq/l)`. The analyte name is matched
   case-insensitively against the supported list.

2. **Tab separator (`\t`):** files must use tab as the column delimiter.

3. **Header row:** the first row must contain column names.

4. **Numeric values:** analyte columns must contain numbers or be empty.

### ✅ Supported input units

Any of the following input units are accepted — the component detects the unit
from the column name and converts to all three regardless:

| Input unit | Recognised as |
|------------|--------------|
| `mg/l` | mg/l |
| `µg/l` or `ug/l` | µg/l |
| `µeq/l` or `ueq/l` | µeq/l |
| `μg/l` (Greek mu) | µg/l (normalised) |
| `μeq/l` (Greek mu) | µeq/l (normalised) |

### ⚠️ Only the listed analytes are expanded

The component only generates unit columns for the **22 analytes** in the
supported list above. Any column whose name does not match a known analyte
passes through unchanged without error. This means the component works
directly with any dataset measuring a **subset** of these analytes.

### ⚠️ Existing columns are never overwritten

If a column already exists in the input (e.g. the dataset already contains
both `NO3(mg/l)` and `NO3N(mg/l)`), the existing column is **preserved** and
not recalculated. Only genuinely missing unit columns are added.

---

## Notes

- Both `μ` (Greek mu, U+03BC) and `µ` (micro sign, U+00B5) are treated
  identically throughout — the component normalises to the micro sign before
  any comparison.
- The ALKALINITY CSV passes through this component without any unit expansion
  because its main column `AlkalinityICPForests(µeq/l)` does not match any
  analyte in the dictionary.
- All output CSVs use tab (`\t`) as the column separator and include a
  header row, preserving the same format as the input.
