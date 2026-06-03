# 5 — Water Chemistry Validation

This is the **central quality control step** of the workflow. Every analytical
sample that has passed format validation and preprocessing is subjected here
to a set of physicochemical checks that verify internal consistency of the
measurements. The result is a `FINAL_VALIDATION` flag (SI/NO) per sample,
indicating whether the data are fit for reporting.

The component merges all subprogram CSV files for each SiteCode into a single
wide table, propagates metadata to replicate samples, joins the sampling
typology from `samplesInfo.xlsx`, and runs 14 sequential calculation modules
to derive all chemical quality indicators.

---

## Workflow position

```
UnitTransformation  →  WaterChemistryValidation  →  WaterChemistryValidationReport
```

---

## Inputs

| Name | Type | Path | Description |
|------|------|------|-------------|
| input-data | Zip | `/mnt/inputs/water_chemical_data_level1_units.zip` | ZIP of tab-separated CSV files with all three unit representations per analyte (mg/l, µg/l, µeq/l), as produced by component 4. One CSV per SiteCode per subprogram. |
| input-samples | Text | `/mnt/inputs/samplesInfo.xlsx` | Excel file mapping each SampleID to its SamplingTypology and programme metadata. If not provided, all typology-dependent checks are skipped. |

### Input CSV format

The input ZIP must contain tab-separated CSVs following this naming convention:
`<SiteCode>_WATER_<SUBPROGRAM>.csv`

The component expects CSVs for these subprograms (any subset is accepted):

| File pattern | Key columns required for validation |
|---|---|
| `*_WATER_ALKALINITY.csv` | `SampleID`, `SiteCode`, `year`, `month`, `AlkalinityICPForests(µeq/l)` |
| `*_WATER_AMMONIUM.csv` | `SampleID`, `SiteCode`, `year`, `month`, `NH4N(µeq/l)`, `NH4N(mg/l)` |
| `*_WATER_ANIONS.csv` | `SampleID`, `SiteCode`, `year`, `month`, `CL(µeq/l)`, `SO4S(µeq/l)`, `NO3N(µeq/l)`, `NO3N(mg/l)` |
| `*_WATER_CATIONS.csv` | `SampleID`, `SiteCode`, `year`, `month`, `CA(µeq/l)`, `MG(µeq/l)`, `NA(µeq/l)`, `K(µeq/l)`, `AL(µeq/l)`, `FE(µeq/l)`, `MN(µeq/l)` |
| `*_WATER_DOC_TN.csv` | `SampleID`, `SiteCode`, `year`, `month`, `DOC(mg/l)`, `TN(mg/l)` |
| `*_WATER_pH_COND_WEIGHTED_RAW.csv` | `SampleID`, `SiteCode`, `year`, `month`, `WeightedConductivity(µS/cm)`, `WeightedpH`, `H(µeq/l)` |

### samplesInfo.xlsx format

This file maps each SampleID to its programme metadata. It is used to:
1. Assign the `SamplingTypology` to each sample — required for several
   typology-dependent calculations (Org-, ion balance filter, Na/Cl filter).
2. Fill typology for replicate (REP) samples whose SampleID suffix was added
   during transformation and may not appear in this file.

| Column | Required | Description |
|--------|----------|-------------|
| `SampleID` | ✅ | Sample identifier — must match those in the CSVs |
| `SamplingTypology` | ✅ | Sampling type code (see table below) |
| `SiteCode` | ⚠️ optional | Plot code |
| `SiteName` | ⚠️ optional | Plot name |
| `ICP_Program` | ⚠️ optional | Programme (e.g. `ICP-Forest`, `ICP-IM`) |
| `Instrument` | ⚠️ optional | Instrument identifier (e.g. `LISIM-20`) |
| `ID_PostgreSQL` | ⚠️ optional | Database identifier |

**Real example from the ICP-Forest Spain network:**

| SampleID | SiteCode | SamplingTypology | ICP_Program |
|----------|----------|-----------------|-------------|
| 05PS INT | 05 | THR CON | ICP-Forest |
| 05PS INT LIX 20 | 05 | SW CON | ICP-Forest |
| 05PS EXT | 05 | BOF CON | ICP-Forest |
| 06QI INT | 06 | THR BL | ICP-Forest |
| 06QI EXT | 06 | BOF BL | ICP-Forest |

**SamplingTypology codes** — the first part identifies the water collection
type, which drives which validation rules apply:

| Code prefix | Full name | Validation rules applied |
|-------------|-----------|--------------------------|
| `BOF` | Bulk open field (wet deposition) | Ion balance + Na/Cl ratio |
| `WET` | Wet-only deposition | Ion balance + Na/Cl ratio |
| `THR` | Throughfall | Na/Cl ratio; Org- coefficient |
| `THR BL` | Throughfall bulk/litterfall | Na/Cl ratio; specific Org- coefficient |
| `STF` | Stemflow | Na/Cl ratio; specific Org- coefficient |
| `SW` | Soil water | Metal sum; specific Org- coefficient |

The suffix (e.g. `CON`, `BL`, `SNOW`) provides additional detail about the
collection method but does not change the validation rules.

---

## Outputs

| Name | Type | Path | Description |
|------|------|------|-------------|
| output-alldata | Zip | `/mnt/outputs/water_chemical_data_level2_alldata.zip` | One merged CSV per SiteCode with all subprograms joined into a single wide table (pre-validation, no quality indicator columns). |
| output-validated | Zip | `/mnt/outputs/water_chemical_data_level2_validated.zip` | Same CSV per SiteCode with all 14 quality indicator sets appended and the `FINAL_VALIDATION` flag per sample. |

---

## Parameters — quality thresholds

All thresholds have ICP-Forest default values and can be overridden per
execution. They correspond to the acceptable limits defined in the ICP-Forest
manual for water chemistry quality control.

| Parameter | Default | Unit | Description |
|-----------|---------|------|-------------|
| `param_ionsdiff_low_k` | `20.0` | % | Max IonsDiff% for WeightedConductivity ≤ 20 µS/cm |
| `param_ionsdiff_high_k` | `10.0` | % | Max IonsDiff% for WeightedConductivity > 20 µS/cm |
| `param_conddiff_low_1` | `30.0` | % | Max CondDiff% for WeightedConductivity ≤ 10 µS/cm |
| `param_conddiff_low_2` | `20.0` | % | Max CondDiff% for WeightedConductivity 10–20 µS/cm |
| `param_conddiff_high` | `10.0` | % | Max CondDiff% for WeightedConductivity > 20 µS/cm |
| `param_ratio_nacl_low` | `0.5` | — | Lower bound of acceptable Na/Cl ratio (µeq/l basis) |
| `param_ratio_nacl_high` | `1.5` | — | Upper bound of acceptable Na/Cl ratio (µeq/l basis) |

**Why two tiers for ionic balance and three tiers for conductivity?**
Both thresholds depend on WeightedConductivity because more dilute samples
(lower conductivity) have proportionally larger analytical errors — a 2 µeq/l
measurement error matters much more in a 10 µS/cm sample than in a 100 µS/cm
sample. The tiered thresholds reflect this: dilute samples are allowed a
larger relative deviation before being flagged.

---

## Local execution (Windows PowerShell)

```powershell
cd "C:\path\to\5-water-chemistry-samples-quality-validation"

docker build -t water-chemistry-samples-quality-validation:0.0.1 .

docker run --rm `
  -v "${PWD}/resources/example/data/inputs:/mnt/inputs:ro" `
  -v "${PWD}/resources/example/data/outputs:/mnt/outputs" `
  water-chemistry-samples-quality-validation:0.0.1 `
  --param_ionsdiff_low_k=20.0 --param_ionsdiff_high_k=10.0
```

## resources/example/data/execution-parameters.json

```json
{
  "parameters": [
    { "name": "param_ionsdiff_low_k",  "defaultValue": "20.0", "value": "20.0" },
    { "name": "param_ionsdiff_high_k", "defaultValue": "10.0", "value": "10.0" },
    { "name": "param_conddiff_low_1",  "defaultValue": "30.0", "value": "30.0" },
    { "name": "param_conddiff_low_2",  "defaultValue": "20.0", "value": "20.0" },
    { "name": "param_conddiff_high",   "defaultValue": "10.0", "value": "10.0" },
    { "name": "param_ratio_nacl_low",  "defaultValue": "0.5",  "value": "0.5"  },
    { "name": "param_ratio_nacl_high", "defaultValue": "1.5",  "value": "1.5"  }
  ]
}
```

---

## Pre-processing steps before validation

Before running the 14 quality checks, two preparatory steps are applied:

### Step A — Merge subprogram files by SiteCode

For each SiteCode, all available subprogram CSVs are read and joined into a
single wide DataFrame on the identity columns
`(SampleID, SiteCode, SiteName, year, month)` using an outer join. Only
columns defined in `PATTERNS` for each subprogram are kept. Rows with no
data beyond the identity columns are dropped. Duplicates on the identity key
are removed (first occurrence kept).

The result is one row per sample per month with all measured parameters
side by side — the `allData` output.

### Step B — Fill replicate (REP) samples

Replicate samples (SampleID ending in `REP`) often lack some metadata columns
because only the parameters that were re-analysed are recorded in the REP file.
For each group sharing the same `(SiteCode, year, month, base SampleID)`,
if a REP row has NaN in a column where the base NOREP row has a value, the
NOREP value is propagated into the REP row. This ensures REP samples carry
complete site and date metadata before entering the quality checks.

---

## The 14 quality checks — detailed description

### Check 1 — Heavy metal sum for soil water (SW) samples

**Output column:** `Metals_SW(µeq/l)`

For samples with SamplingTypology containing `SW` (soil water), the sum of
aluminium, iron and manganese in µeq/l is computed:

```
Metals_SW(µeq/l) = AL(µeq/l) + FE(µeq/l) + MN(µeq/l)
```

This sum is used later as an additional cation contribution in the ionic
balance for soil water samples, where dissolved metals represent a
significant fraction of the cation load. For all other typologies this
column is NaN.

---

### Check 2 — Dissolved organic nitrogen (NDON)

**Output columns:** `NDON(mg/l)`, `Quality_NDON`

```
NDON(mg/l) = TN(mg/l) - (NO3N(mg/l) + NH4N(mg/l))
```

NDON (Non-ionic Dissolved Organic Nitrogen) represents the organic nitrogen
fraction not accounted for by the inorganic nitrogen species. It is computed
as a difference and serves as a data consistency check.

`Quality_NDON` is set to `ok` if all three input columns are present, or
`incomplete` if any is missing. Note: a negative NDON value is handled
separately in Check 13 (OrgN quality flag).

---

### Check 3 — Organic anion estimation (Org-)

**Output column:** `Org-(µeq/l)`

Dissolved organic matter carries a negative charge that contributes to the
overall anion balance but is not directly measured. It is estimated from DOC
using **empirical linear relationships calibrated by sampling typology**
(ICP-Forest protocol):

| SamplingTypology contains | Formula |
|---------------------------|---------|
| `STF` (stemflow) | `Org- = 5.04 × DOC - 6.67` |
| `THR` and ends with `BL` (throughfall bulk) | `Org- = 6.80 × DOC - 12.32` |
| `THR` (other throughfall) | `Org- = 4.17 × DOC - 5.01` |
| `SW` (soil water) | `Org- = 9.80 × DOC` |

These coefficients are derived from regression analyses specific to European
forest monitoring sites. If no typology information is available, `Org-`
remains NaN and the organic-corrected ion balance cannot be computed.

---

### Check 4 — Sum of anions

**Output column:** `SumAnions(µeq/l)`

```
SumAnions(µeq/l) = AlkalinityICPForests(µeq/l) + CL(µeq/l) + SO4S(µeq/l) + NO3N(µeq/l)
```

This is the total measured anion charge in the sample. NaN values for
individual anions are treated as zero in the sum (min_count=1 — at least
one non-NaN value must be present for a non-NaN result).

---

### Check 5 — Sum of anions with organic correction, and sum of cations

**Output columns:** `+Org(µeq/l)`, `SumCations(µeq/l)`

```
+Org(µeq/l) = SumAnions(µeq/l) + Org-(µeq/l)
```

```
SumCations(µeq/l) = H(µeq/l) + NH4N(µeq/l) + CA(µeq/l) + MG(µeq/l)
                  + NA(µeq/l) + K(µeq/l) + Metals_SW(µeq/l)
```

Note that `Metals_SW(µeq/l)` is only non-NaN for SW samples — for all other
typologies, only the six base cations contribute to the sum.

---

### Check 6 — Ionic balance: sC - sA (without organic correction)

**Output columns:** `sC - sA IonsDiff.%`, `IonsDiff.Limit(%)`,
`IonsDiff.OverLimit.pp`, `IonsDiff.OverLimit.relative%`,
`sC - sA QualityIonsBalance`

In a chemically consistent water sample, the total positive charge (cations)
must equal the total negative charge (anions). The **IonsDiff%** quantifies
the relative deviation from this balance:

```
IonsDiff% = 100 × (SumCations - SumAnions) / (0.5 × (SumCations + SumAnions))
```

The acceptable limit depends on WeightedConductivity:

```
If WeightedConductivity ≤ 20 µS/cm  →  limit = param_ionsdiff_low_k  (default 20%)
If WeightedConductivity  > 20 µS/cm  →  limit = param_ionsdiff_high_k (default 10%)
```

`sC - sA QualityIonsBalance` = `ok` if `|IonsDiff%| ≤ limit`, otherwise `NO`.

Additional diagnostic columns:
- `IonsDiff.OverLimit.pp`: excess in percentage points above the limit (0 if within limit)
- `IonsDiff.OverLimit.relative%`: excess expressed as % of the limit itself

---

### Check 7 — Ionic balance with organic correction: sC - sA - Org-

**Output columns:** `sC - sA - Org- IonsDiff.%`, `IonsDiffOrg.Limit(%)`,
`IonsDiffOrg.OverLimit.pp`, `IonsDiffOrg.OverLimit.relative%`,
`sC - sA - Org- QualityIonsBalance`

Same calculation as Check 6, but using `+Org(µeq/l)` (SumAnions + Org-)
as the anion sum:

```
IonsDiff_Org% = 100 × (SumCations - +Org) / (0.5 × (SumCations + +Org))
```

This version is more complete for samples rich in dissolved organic matter,
where ignoring Org- would artificially inflate the apparent cation excess.
The same tiered limits apply.

**This is the version used for the FINAL_VALIDATION flag** for BOF and WET
typology samples, as specified by the ICP-Forest protocol.

---

### Check 8 — Na/Cl ratio

**Output columns:** `RatioNa/Cl`, `NaClDelta`, `NaClOverLimit.relative%`,
`QualityRatioNa/Cl`

```
RatioNa/Cl = NA(µeq/l) / CL(µeq/l)
```

The ratio of sodium to chloride (in µeq/l) reflects the marine origin of
these ions. In most European forest monitoring contexts the expected range is
`[param_ratio_nacl_low, param_ratio_nacl_high]` (default [0.5, 1.5]), which
brackets the seawater ratio (~1.17 µeq/µeq).

- Below 0.5: possible Cl contamination or analytical error
- Above 1.5: possible Na contamination, road salt influence, or analytical error

`QualityRatioNa/Cl` = `ok` if within range, `NO` otherwise.
`NaClDelta`: absolute distance to the nearest limit (0 if within range).
`NaClOverLimit.relative%`: delta expressed as % of the relevant limit.

**Applied only to:** BOF, WET, THR, THR BL and STF typologies.
Not applied to SW (soil water) because soil processes can substantially
alter Na/Cl ratios independently of atmospheric deposition.

---

### Check 9 — Theoretical conductivity (without ionic activity correction)

**Output column:** `ConductivityCalculatedWithoutCorrection(µS/cm)`

The theoretical conductivity is calculated from the ion concentrations
using their equivalent conductances (Kohlrausch's law):

```
Cc_uncorrected = Σ(c_i × λ_i) / 1000
```

where `c_i` is the concentration of ion i in µeq/l and `λ_i` is its
equivalent conductance in S·cm²/eq. The constants used are:

| Ion | λ (S·cm²/eq) |
|-----|-------------|
| H⁺ | 350.0 |
| NH₄⁺ (as NH4N) | 73.5 |
| Ca²⁺ | 59.5 |
| Mg²⁺ | 53.1 |
| Na⁺ | 50.1 |
| K⁺ | 73.5 |
| Al³⁺ | 61.0 |
| Fe²⁺ | 68.0 |
| Mn²⁺ | 53.5 |
| Alkalinity (HCO₃⁻) | 44.5 |
| SO₄²⁻ (as SO4S) | 80.0 |
| NO₃⁻ (as NO3N) | 71.4 |
| Cl⁻ | 76.4 |

---

### Check 10 — Ionic strength

**Output column:** `IonicStrenght(mol/l)`

The ionic strength is computed using a semi-empirical formula based on
the measured ion concentrations:

```
I = Σ(c_i × z_i) / (1000 × 2000)
```

where `c_i` is the concentration in µeq/l and `z_i` is the charge number
of ion i. This is used as input for the ionic activity correction in Check 11.

---

### Check 11 — Ionic activity factor and corrected conductivity

**Output columns:** `IonicActivityFactor`,
`ConductivityCalculatedCorrected(µS/cm)`

At higher ionic strengths, ions interact with each other and their effective
conductance decreases. The **ionic activity factor** accounts for this using
the Davies equation (semi-empirical):

```
f = 10^(-0.5 × (√I / (1 + √I) - 0.3 × I))
```

The corrected theoretical conductivity is:

```
Cc_corrected = Cc_uncorrected × f²
```

This corrected value is what gets compared to the measured WeightedConductivity
in Check 12.

---

### Check 12 — Conductivity difference %

**Output columns:** `ConductivityDiff.(µS/cm)`, `Cond.-Cond.H+(µS/cm)`,
`Cond. Diff.%Cc-Xm`, `CondDiff.Limit(%)`, `CondDiff.OverLimit.pp`,
`CondDiff.OverLimit.relative%`, `QualityConductivity`

The relative difference between the theoretically calculated conductivity
and the measured conductivity (Xm = WeightedConductivity) is:

```
CondDiff%Cc-Xm = 100 × (Cc_corrected - Xm) / Xm
```

The acceptable limit depends on Xm (three tiers):

```
Xm ≤ 10 µS/cm       →  limit = param_conddiff_low_1  (default 30%)
10 < Xm ≤ 20 µS/cm  →  limit = param_conddiff_low_2  (default 20%)
Xm > 20 µS/cm       →  limit = param_conddiff_high   (default 10%)
```

A large discrepancy indicates a missing ion, a measurement error, or a
systematic offset in one of the analytical methods.

`Cond.-Cond.H+(µS/cm)` is an auxiliary diagnostic: the measured conductivity
minus the H⁺ contribution — useful for assessing conductivity in acidic samples
where H⁺ dominates.

`QualityConductivity` = `ok` if `|CondDiff%| ≤ limit`, otherwise `NO`.

---

### Check 13 — OrgN quality flag

**Output columns:** `QualityOrgN`, `OrgN_UnderLimit.mgL`,
`OrgN_UnderLimit.relative%`

Total Nitrogen must be greater than or equal to the sum of its measured
inorganic fractions. If this is violated, TN was measured lower than the
sum of its components, which is chemically impossible:

```
OrgN = TN(mg/l) - (NO3N(mg/l) + NH4N(mg/l))

OrgN > 0  →  QualityOrgN = 'ok'
OrgN ≤ 0  →  QualityOrgN = 'NO TN'
```

`OrgN_UnderLimit.mgL`: the absolute deficit (0 if OrgN ≥ 0).
`OrgN_UnderLimit.relative%`: deficit expressed as % of |TN|.

---

### Check 14 — FINAL_VALIDATION flag

**Output column:** `FINAL_VALIDATION`

The final flag aggregates all quality checks. A sample receives
`FINAL_VALIDATION = NO` if **any** of the following conditions are true:

| Condition | Typologies checked |
|-----------|-------------------|
| Organic-corrected ion balance fails (`sC - sA - Org- QualityIonsBalance = NO` or NaN) | BOF, WET |
| Conductivity check fails (`QualityConductivity = NO` or NaN) | All |
| OrgN check fails (`QualityOrgN = NO TN` or NaN) | All |
| Na/Cl ratio fails (`QualityRatioNa/Cl = NO` or NaN) | BOF, WET, THR, THR BL, STF |

If none of these conditions apply, `FINAL_VALIDATION = SI`.

**Note on NaN handling:** a NaN result in a quality column (caused by missing
input data) is treated the same as a failing result — the sample is flagged
NO. This is conservative: incomplete data cannot be considered validated.

---

## Complete list of output columns added by this component

The validated CSV contains all the input columns plus:

| Column | Type | Description |
|--------|------|-------------|
| `SamplingTypology` | text | From samplesInfo.xlsx |
| `Metals_SW(µeq/l)` | float | AL+FE+MN sum (SW only) |
| `NDON(mg/l)` | float | TN - NO3N - NH4N |
| `Quality_NDON` | text | `ok` / `incomplete` |
| `Org-(µeq/l)` | float | Estimated organic anion |
| `SumAnions(µeq/l)` | float | Alkalinity + Cl + SO4S + NO3N |
| `+Org(µeq/l)` | float | SumAnions + Org- |
| `SumCations(µeq/l)` | float | H + NH4N + Ca + Mg + Na + K + metals |
| `sC - sA IonsDiff.%` | float | Ion balance deviation % |
| `IonsDiff.Limit(%)` | float | Applicable threshold |
| `IonsDiff.OverLimit.pp` | float | Excess in pp above threshold |
| `IonsDiff.OverLimit.relative%` | float | Excess as % of threshold |
| `sC - sA QualityIonsBalance` | text | `ok` / `NO` |
| `sC - sA - Org- IonsDiff.%` | float | Ion balance with organic correction |
| `IonsDiffOrg.Limit(%)` | float | Applicable threshold |
| `IonsDiffOrg.OverLimit.pp` | float | Excess in pp above threshold |
| `IonsDiffOrg.OverLimit.relative%` | float | Excess as % of threshold |
| `sC - sA - Org- QualityIonsBalance` | text | `ok` / `NO` |
| `RatioNa/Cl` | float | Na/Cl molar ratio in µeq/l |
| `NaClDelta` | float | Distance to nearest limit |
| `NaClOverLimit.relative%` | float | Delta as % of nearest limit |
| `QualityRatioNa/Cl` | text | `ok` / `NO` |
| `ConductivityCalculatedWithoutCorrection(µS/cm)` | float | Theoretical Cc before activity correction |
| `IonicStrenght(mol/l)` | float | Ionic strength I |
| `IonicActivityFactor` | float | Activity correction factor f |
| `ConductivityCalculatedCorrected(µS/cm)` | float | Corrected theoretical conductivity |
| `ConductivityDiff.(µS/cm)` | float | Absolute difference Cc - Xm |
| `Cond.-Cond.H+(µS/cm)` | float | Xm minus H⁺ contribution |
| `Cond. Diff.%Cc-Xm` | float | Relative conductivity difference % |
| `CondDiff.Limit(%)` | float | Applicable threshold |
| `CondDiff.OverLimit.pp` | float | Excess in pp above threshold |
| `CondDiff.OverLimit.relative%` | float | Excess as % of threshold |
| `QualityConductivity` | text | `ok` / `NO` |
| `QualityOrgN` | text | `ok` / `NO TN` |
| `OrgN_UnderLimit.mgL` | float | Deficit below zero |
| `OrgN_UnderLimit.relative%` | float | Deficit as % of TN |
| `FINAL_VALIDATION` | text | `SI` / `NO` |

---

## Reusing this component

This component can be applied to **any ZIP of tab-separated CSV files**
with water chemistry data, provided:

1. **Column naming:** analyte columns follow `{ELEMENT}(µeq/l)` and
   `{ELEMENT}(mg/l)` conventions (as produced by Component 4).
2. **Identity columns:** each CSV must have `SampleID`, `SiteCode`, `year`,
   `month`.
3. **Tab separator and header row** as in all other components.

The `samplesInfo.xlsx` is optional but strongly recommended. Without it:
- `Org-` estimation is skipped (requires typology).
- Ion balance filter for BOF/WET is skipped.
- Na/Cl filter for BOF/WET/THR/STF is skipped.
- All other checks (conductivity, OrgN) still run on all samples.

The quality thresholds are fully configurable via parameters, making the
component adaptable to other monitoring programmes with different
analytical precision standards.
