## 1. Scientific context — ICP-Forest water chemistry workflow

### 1.1 Background

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

### 1.2 Water subprogrammes

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

### 1.3 Template structure and sample representation

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

### 1.4 The four data levels

| Level | Name | Description |
|-------|------|-------------|
| **Level 0** | Raw data | Laboratory results recorded directly into templates. No processing applied. Entry point of the workflow. |
| **Level 1** | Pre-processed | Passed format validation + basic transformations: LOQ substitution, unit conversion, alkalinity calculation (Gran method), volume-weighted pH and conductivity. |
| **Level 2** | Chemically validated | Advanced physicochemical quality checks per sample: ion balance, conductivity consistency, Na/Cl ratio, organic nitrogen check, ionic strength. Each sample carries a `FINAL_VALIDATION` flag (SI/NO). |
| **Level 3** | Reporting-ready | Best measurement selected per sample per month (NOREP/REP priority logic). One row per sample per month, ready for ICP programme submission and database ingestion. |

### 1.5 Replicate (REP) samples

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

### 1.6 SamplingTypology codes

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

### 1.7 SiteCode

SiteCode identifies a monitoring plot. It is stored as a **column inside each
Excel file**, not in the filename. Always group data by SiteCode from file
content — never parse it from the filename. Each file may contain rows for
multiple SiteCodes.

---

## 2. The workflow step by step

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

## 3. Key chemistry — what each validation checks and why

### 3.1 LOQ substitution (component 3)

The Limit of Quantification (LOQ) is the minimum concentration a laboratory
instrument can reliably measure. Values below the LOQ are not zero — they are
simply below the detection threshold. The standard method in environmental
chemistry is to replace them with LOQ/2, which preserves the information that
the value is low without treating it as absent. Every substitution is logged
for traceability.

### 3.2 Unit conventions (component 4)

Three unit representations are generated for every analyte:
- **mg/l** — mass concentration (most common in templates)
- **µg/l** — mass concentration at micro scale (trace metals)
- **µeq/l** — equivalent concentration, charge-based (required for ion balance)

Conversion from µeq/l to mg/l: `mg/l = µeq/l × (atomic or molecular weight / valence) / 1000`

### 3.3 Ionic balance (components 5)

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

### 3.4 Organic anion estimation (Org-) (components 5)

Dissolved organic matter carries a negative charge that contributes to the
anion balance but is not directly measured. It is estimated from DOC using
empirical relationships calibrated by sampling typology (ICP-Forest protocol):

| Typology | Formula |
|----------|---------|
| STF (stemflow) | Org- = 5.04 × DOC - 6.67 |
| THR BL (throughfall bulk) | Org- = 6.80 × DOC - 12.32 |
| THR (other throughfall) | Org- = 4.17 × DOC - 5.01 |
| SW (soil water) | Org- = 9.80 × DOC |

### 3.5 Conductivity check (component 5)

A theoretical conductivity is calculated from the measured ion concentrations
using their equivalent conductances (Kohlrausch's law), then corrected for
ionic activity using the Davies equation. The difference between this
theoretical value and the measured WeightedConductivity should be small:

- WeightedConductivity ≤ 10 µS/cm → max ±30%
- WeightedConductivity 10–20 µS/cm → max ±20%
- WeightedConductivity > 20 µS/cm → max ±10%

A large discrepancy indicates a missing or incorrectly measured ion.

### 3.6 Na/Cl ratio (component 5)

The ratio of sodium to chloride (in µeq/l) reflects the marine origin of
these ions. In most European forest monitoring contexts, Na/Cl should be
close to the seawater ratio (~1.0). Acceptable range: [0.5, 1.5].
Values outside this range suggest sea-salt influence, Na contamination,
or analytical errors. Only checked for BOF, WET, THR and STF samples.

### 3.7 OrgN check (component 5)

Total Nitrogen (TN) must always be greater than or equal to the sum of its
inorganic fractions: TN ≥ NO3-N + NH4-N. If this is violated it means TN
was measured lower than the sum of its known components, which is chemically
impossible and indicates a measurement error.

