# LifeWatch Workflows for Data Management — Long-Term Forest and Ecosystem Monitoring in Spain: Integration of ICP Forests and ICP IM Datasets

> BIOMA Institute · University of Navarra · LifeWatch ERIC

---

# Background: Long-Term Forest Monitoring in Europe

## The ICP Monitoring Programmes

European forests are under sustained pressure from atmospheric pollution, climate change, land-use shifts and biological stressors. Understanding how these pressures interact — and what their long-term effects are on forest ecosystems — requires systematic, high-quality data collected consistently over decades and across national boundaries.

Two complementary international monitoring programmes address this need under the framework of the **United Nations Economic Commission for Europe (UNECE)** and the **Convention on Long-range Transboundary Air Pollution (CLRTAP)**:

**ICP Forests** (International Co-operative Programme on Assessment and Monitoring of Air Pollution Effects on Forests) operates at two levels:

- **Level I** — Large-scale forest condition surveys at around 6,000 plots across Europe, focusing on tree crown condition and foliar chemistry.
- **Level II** — Intensive monitoring at approximately 640 permanent plots across 40 countries, where multiple ecosystem compartments are measured in detail: atmospheric deposition (bulk and throughfall), soil water chemistry, soil properties, phenology, biodiversity, meteorology, and tree growth.

**ICP Integrated Monitoring (ICP IM)** takes a whole-catchment approach at 48 stations across 15 countries, tracking the integrated response of ecosystems to deposition and climate. The Spanish ICP IM station **ES02 (Bertiz, Navarra)** is operated by BIOMA and represents one of the longest-running integrated monitoring records in southern Europe.

Spain participates in both programmes through the **Ministry for Ecological Transition and the Demographic Challenge (MITECO)** in coordination with BIOMA — Institute of Biodiversity and Environmental Management at the **University of Navarra**.

## The 14 Spanish Level-II Plots

The Spanish ICP Forests network includes 14 intensive Level-II monitoring plots distributed across the main forest biomes of the Iberian Peninsula, covering a climatic gradient from the Atlantic north (Galicia, Navarra, País Vasco) to the Mediterranean south and east (Andalucía, Valencia, Murcia) and the continental interior (Castilla y León, Aragón):

| Plot code | Name | Region | Main species |
|-----------|------|--------|-------------|
| 05 | Valsain | Castilla y León | *Pinus sylvestris* |
| 06 | Morella | Comunitat Valenciana | *Quercus ilex* |
| 07 | Majadas | Extremadura | *Quercus ilex* |
| 10 | Almonte | Andalucía | *Pinus pinea* |
| 11 | Villanueva de la Sierra | Extremadura | *Quercus pyrenaica* |
| 22 | Mora de Rubielos | Aragón | *Pinus sylvestris* |
| 25 | Tibi | Comunitat Valenciana | *Pinus halepensis* |
| 26 | Andújar | Andalucía | *Quercus ilex* |
| 30 | Soria | Castilla y León | *Pinus sylvestris* |
| 33 | Cervera de Pisuerga | Castilla y León | *Pinus sylvestris* |
| 37 | Cuéllar | Castilla y León | *Pinus pinaster* |
| 54 | El Saler | Comunitat Valenciana | *Pinus pinea* |
| 102 | Padrón | Galicia | *Pinus radiata* |
| 115 | Burguete | Navarra | *Fagus sylvatica* |

Each plot collects water samples from multiple subprogrammes every month, generating a large volume of analytical data that feeds directly into European-scale assessments.

## The ICP IM Station ES02 — Bertiz (Navarra)

The Spanish ICP Integrated Monitoring station **ES02** is located in the **Señorío de Bertiz Natural Park** in Navarra, within an Atlantic mixed forest dominated by *Quercus robur*, *Alnus glutinosa* and *Fraxinus excelsior*. It is operated by BIOMA and has been active since the early 1990s, making it one of the longest continuous integrated monitoring records in southern Europe.

Unlike the ICP Forests Level-II plots — which focus on a single forest stand — ES02 operates at the **catchment scale**, tracking the full water and element budget from atmospheric input to stream output. All water subprogrammes are active at ES02, plus runoff water from the gauged catchment outlet.

| Station | Name | Programme | Region | Catchment area | Main vegetation |
|---------|------|-----------|--------|---------------|-----------------|
| ES02 | Bertiz | ICP Integrated Monitoring | Navarra | ~100 ha | *Quercus robur*, *Alnus glutinosa*, *Fraxinus excelsior* |

The same analytical templates and data processing pipeline used for ICP Forests Level-II plots apply to ES02. The `ICP_Program` column in `samplesInfo.xlsx` distinguishes between `ICP-Forest` and `ICP-IM` samples, allowing the pipeline to process both networks simultaneously within the same workflow execution.

## Water Monitoring Subprogrammes

Water chemistry is one of the most information-rich components of Level-II monitoring. It captures the chemical signature of atmospheric deposition as it passes through the ecosystem — from open-field precipitation, through the canopy (throughfall and stemflow), into the soil (soil water at different depths), and out of the catchment (runoff water). The five water subprogrammes are:

| Subprogramme | Abbreviation | What it measures |
|---|---|---|
| Precipitation Chemistry | PC | Bulk deposition in the open field — the atmospheric input before any ecosystem interaction |
| Throughfall | TF | Water passing through and dripping from the forest canopy — reflects canopy exchange processes including dry deposition capture, leaching and uptake |
| Stemflow | SF | Water flowing down tree stems — a localised but sometimes concentrated flux |
| Soil Water | SW | Soil solution collected by lysimeters at 20 and 60 cm depth — reflects the geochemical transformation of inputs as they percolate through the soil |
| Runoff Water | RW | Water leaving the catchment — integrates the chemical signal of the whole ecosystem |

All five subprogrammes measure the same set of chemical parameters: major ions (Ca²⁺, Mg²⁺, Na⁺, K⁺, NH₄⁺, Cl⁻, NO₃⁻, SO₄²⁻), trace metals (Al, Fe, Mn, As, Cd, Cr, Cu, Co, Ni, Pb, Zn), dissolved organic carbon (DOC), total nitrogen (TN), pH, electrical conductivity, and alkalinity. This analytical consistency is what makes cross-site and cross-subprogram comparisons possible — and what makes data quality control so critical.

---

# Why Data Quality Matters

## From Field to Policy: The Stakes of Monitoring Data

The data produced by ICP monitoring do not stay within the boundaries of individual research projects. They are submitted annually to international programme coordinators, aggregated across countries, and used to:

- Assess the **status and trends of forest health** across Europe
- Calculate **critical loads** of acidity and nutrient nitrogen — the thresholds below which harmful ecological effects are not expected to occur — which directly inform **emission reduction targets** under CLRTAP
- Track the **effectiveness of air pollution abatement policies** over decades
- Provide baseline evidence for the **EU Water Framework Directive (2000/60/EC)** and **biodiversity strategies**
- Feed into **IPCC** and **EEA** environmental state assessments

Errors in monitoring data therefore do not merely affect a local dataset. A systematic error in how a single element is reported — a wrong unit conversion, an uncorrected value below the detection limit, an incorrectly calculated alkalinity — can propagate into load calculations, European database aggregations, and ultimately into scientific conclusions and policy recommendations affecting forests across an entire continent.

This makes robust, systematic, and reproducible data quality control not a technical nicety but a scientific and policy obligation.

## The Fragility of Manual Processing

Historically, the validation of ICP water chemistry data has been performed largely by hand: researchers process Excel templates, apply unit conversions, check ion balances and flag outliers using a combination of spreadsheet formulas, visual inspection and expert judgement. This approach has several structural weaknesses:

- **Inconsistency across operators and years** — as staff change, validation criteria drift
- **Limited traceability** — it is often impossible to reconstruct exactly what transformations were applied to a given data point
- **Slow turnaround** — manual processing of monthly templates for 14 plots and 5 subprogrammes can take weeks
- **No formal audit trail** — there is no log of which values were substituted, corrected or flagged and why
- **Difficulty scaling** — expanding the network or adding new subprogrammes multiplies the manual workload proportionally

The LifeWatch workflows described in this document address all five of these weaknesses by replacing manual steps with automated, version-controlled, documented processing components.

---

# The Data Journey: Four Stages from Measurement to Knowledge

The complete lifecycle of an ICP monitoring data point spans four distinct conceptual stages. Workflows 1 and 2 together cover Stage 2 (validation), while Workflows 3 and 4 cover integration and analysis respectively. The diagram below shows how the four workflows map onto these stages:

```
┌──────────────────────────────────────────────────────────────────────────────┐
│  STAGE 1         STAGE 2              STAGE 3             STAGE 4            │
│  COLLECTION  →   VALIDATION       →   INTEGRATION     →   ANALYSIS           │
│                                                                               │
│  Field &         Quality control,     Database             Trend analysis,    │
│  laboratory      anomaly screening,   update,              load calculations, │
│  templates       NOREP/REP            satellite            cross-site         │
│                  selection            data fusion          comparisons        │
│                                                                               │
│  Workflow 1      Workflow 2           Workflow 3           Workflow 4         │
└──────────────────────────────────────────────────────────────────────────────┘
```

## Stage 1 — Data Collection and Entry (Level 0)

Every month, field technicians collect water samples from each active subprogramme at each Level-II plot. Samples are shipped to the laboratory, where they undergo a standardised analytical protocol. Results are entered manually into six Excel templates — one per analytical subprogramme:

| Template | Key measurements |
|---|---|
| `AMMONIUM` | NH₄-N concentration |
| `ANIONS` | Cl⁻, NO₃⁻, SO₄²⁻, PO₄³⁻ |
| `CATIONS` | Ca²⁺, Mg²⁺, Na⁺, K⁺, Al, Fe, Mn, and 10 trace metals |
| `DOC_TN` | Dissolved organic carbon, total nitrogen |
| `pH_COND` | pH and conductivity per individual collector (before mixing) |
| `ALKALINITY` | Titration series for Gran-method alkalinity determination |

These templates constitute the **Level 0** data — the raw entry point of the pipeline. They are the most vulnerable stage: values that are incorrectly entered, formatted or labelled here will propagate through every subsequent step unless caught early. This is why the first workflow begins with a format validation step before any scientific processing is applied.

The templates are collected monthly into a ZIP archive (`allData.zip`) and submitted to the processing pipeline.

## Stage 2 — Validation and Pre-Processing (Workflows 1 & 2)

Stage 2 transforms Level 0 templates into a scientifically validated, analysis-ready dataset. It comprises two workflows that operate sequentially.

### Workflow 1 — Data Validation (7 steps)

Workflow 1 implements the complete chain of transformations and quality checks required before ICP data can be submitted or used for analysis. It is the most complex part of the pipeline, with seven distinct components:

**Step 1 — Format Validation:** Checks that each Excel template conforms to the expected structure — required columns are present, dates are valid, concentrations are non-negative, critical fields are not empty. A plain-text log reports errors and warnings per file. The workflow halts if critical errors are found.

**Step 2 — Transformation:** Applies subprogram-specific transformations to the validated templates:
- For `pH_COND`: computes volume-weighted pH, conductivity, and hydron concentration from individual collector measurements. Volume-weighted pH is necessary because pH is a logarithmic quantity — averaging raw pH values is mathematically incorrect.
- For `ALKALINITY`: applies the Gran method (linear regression on titration data) to derive alkalinity in µeq/L per sample.
- For `AMMONIUM`, `ANIONS`, `CATIONS`, `DOC_TN`: consolidates monthly files and deduplicates by sample identity.

**Step 3 — LOQ Application:** Applies the Limit of Quantification (LOQ) correction. Values reported below the LOQ are replaced by LOQ/2 — the standard convention for left-censored analytical data in environmental chemistry. Every substitution is logged for traceability.

**Step 4 — Unit Conversion:** Generates three unit representations for every analyte (mg/L, µg/L, µeq/L) regardless of the input unit. Also handles paired molecular/elemental cross-conversions (e.g. NH₄ ↔ NH₄-N, SO₄ ↔ SO₄-S). The µeq/L representation is essential for the ionic balance calculations in Step 5.

**Step 5 — Chemical Quality Validation:** The central quality control step. Applies 14 sequential physicochemical checks to each sample:

| Check | Calculation | Quality flag |
|---|---|---|
| Ionic balance | IonsDiff% = 100 × (ΣCations − ΣAnions) / (0.5 × (ΣCations + ΣAnions)) | Limit: ±20% (EC ≤ 20 µS/cm) or ±10% (EC > 20 µS/cm) |
| Ionic balance with organic correction | Same, but including estimated organic anion (Org⁻) from DOC | Same thresholds |
| Conductivity check | Theoretical vs. measured conductivity (Kohlrausch + Davies correction) | Limit: ±30/20/10% depending on EC |
| Na/Cl ratio | Na(µeq/L) / Cl(µeq/L) | Expected range: [0.5, 1.5] |
| OrgN consistency | TN − (NO₃-N + NH₄-N) ≥ 0 | Violation = TN below sum of inorganic fractions |

The organic anion (Org⁻) is estimated from DOC using empirical linear relationships calibrated by sampling typology (throughfall, stemflow, soil water), following ICP-Forest protocol. A `FINAL_VALIDATION` flag (SI/NO) is assigned to each sample based on all checks combined.

**Step 6 — Validation Report:** Generates a multi-page PDF report with key indicators, six analytical charts (failure rates by month, typology and site, heatmap of failure rate by typology × month, REP improvement analysis), and a colour-coded per-sample validation table. Produces `Samples2Repeat.xlsx` — the list of samples that failed and must be re-analysed.

**Step 7 — Final Data Selection:** Applies the NOREP/REP priority logic to select one validated row per sample per month:

1. If the original (NOREP) sample passed → keep NOREP
2. If NOREP failed and the replicate (REP) passed → keep REP
3. If both failed → keep NOREP (result must be reported)
4. If NOREP failed and no REP exists → discard

The output is a clean Level-3 Excel file with one row per sample per month, formatted for ICP programme submission.

### Workflow 2 — Outlier Detection and Database Update

Workflow 2 operates on the validated Level-3 data and performs two functions:

**Outlier detection:** Statistical screening using z-scores, IQR-based rules and temporal trend analysis to identify measurements that are valid according to the physicochemical checks but anomalous in a statistical or temporal sense. Flagged samples are sent for expert review rather than automatic exclusion.

**Database update:** Clean, reviewed records are ingested into the internal structured database (PostgreSQL + MinIO object storage), ensuring that all downstream analyses operate on the most current validated data. Every ingestion event is versioned and logged.

## Stage 3 — Multi-Source Data Integration (Workflow 3)

Stage 3 extends the monitoring dataset beyond laboratory chemistry by integrating it with complementary environmental data sources. This is where the controlled experiment of the monitoring plot connects to the broader landscape and atmospheric context.

Workflow 3 combines:

- **Satellite imagery** (Sentinel-2, every 5 days): spectral indices reflecting vegetation condition, canopy moisture and disturbance (NDVI, EVI, NBR and others)
- **Atmospheric deposition model outputs**: gridded estimates of sulfur and nitrogen deposition for attribution and load calculation
- **Land-use and land-cover data**: spatial context around each plot that may explain chemical signals
- **PRTR emission records**: point-source emissions in the vicinity of monitored plots

The output is a harmonised, analysis-ready dataset that links field chemistry with the spatial and atmospheric pressures acting on each site — enabling questions that neither the chemistry data nor the satellite data could answer alone.

## Stage 4 — Environmental Analysis (Workflow 4)

Stage 4 applies the validated, integrated dataset to scientific questions about forest ecosystem response. This workflow does not produce new data — it produces knowledge from the data assembled in Stages 1–3.

Analyses currently implemented or planned include:

- **Long-term trend detection**: Mann-Kendall trend tests and Sen's slope estimation on key chemical indicators (acidity, sulphate, nitrate, DOC) over the full monitoring record
- **Deposition load calculations**: bulk and net throughfall loads (kg ha⁻¹ yr⁻¹) of nitrogen, sulphur and base cations for each plot and year
- **Cross-site comparisons**: spatial patterns in deposition chemistry across the Spanish network, linked to site characteristics and regional emission sources
- **Ion budget analysis**: source apportionment using the Na/Cl ratio and sea-salt correction
- **Satellite-chemistry correlations**: linking canopy spectral indices to solution chemistry as a proxy for ecosystem stress

---

# Workflow Architecture: Design Principles

## Modular Components on LifeWatch Tesseract

The four workflows are implemented as chains of **Tesseract wrappers** on the LifeWatch ERIC Virtual Research Environment. Each wrapper is a self-contained Docker container that:

- Receives inputs as files mounted at `/mnt/inputs/`
- Writes outputs to `/mnt/outputs/`
- Exposes configurable parameters via a standardised CLI argument interface
- Is described by an `annotation.json` metadata file that registers it in the LifeWatch component catalogue

This architecture has several important properties:

**Reproducibility:** Every run of a wrapper produces the same output from the same input. Parameters are logged. Outputs are versioned ZIP archives. The complete chain can be re-run at any time on historical data.

**Traceability:** Every LOQ substitution is logged with the original value, the LOQ threshold and the replacement. Every validation flag has a documented calculation. Every database ingestion is versioned. A data point can be traced from the final analytical output back to the raw template row.

**Modularity:** Each wrapper can be run independently. A researcher with only ALKALINITY data can run the alkalinity transformation without running the full validation chain. The LOQ application can be applied to any dataset with `{ANALYTE}(mg/l)` column names, regardless of its origin.

**Reusability:** The validation components are not specific to ICP data. Any research group with water chemistry data in Excel templates can adopt the pipeline by providing a `tables_config.txt` configuration file that describes their template structure. The scientific checks in Workflow 1 (ionic balance, conductivity check, Na/Cl ratio) are standard analytical chemistry quality controls applicable to any surface water dataset.

## Data Levels

The pipeline produces outputs at four formally defined data levels:

| Level | Name | Description | Main output |
|---|---|---|---|
| **0** | Raw data | Laboratory results entered into Excel templates by the researcher | `allData.zip` |
| **1** | Pre-processed | Format-validated, transformed (Gran alkalinity, weighted pH), LOQ-corrected, unit-converted | `water_chemical_data_level1_units.zip` |
| **2** | Chemically validated | All physicochemical checks applied; FINAL_VALIDATION flag per sample | `water_chemical_data_level2_validated.zip` |
| **3** | Reporting-ready | Best measurement selected per sample per month (NOREP/REP logic); ICP-format columns only | `data2report.xlsx` |

Each level is a distinct, versioned dataset. Moving from one level to the next is a documented transformation, not an in-place edit.

## Input Files Shared Across Workflows

Two external files are required by multiple workflows and must be maintained and updated by the research team:

**`samplesInfo.xlsx`** — Maps each SampleID to its metadata:

| Column | Description |
|---|---|
| `SampleID` | Standardised sample identifier |
| `SamplingTypology` | Collection type code (BOF, WET, THR, THR BL, STF, SW) — drives typology-specific calculations |
| `ICP_Program` | Programme (ICP-Forest, ICP-IM) |
| `Instrument` | Laboratory instrument identifier |
| `ID_PostgreSQL` | Database record key |

**`tables_config.txt`** — JSON array defining the validation rules applied in Workflow 1, Step 1. One entry per template type, specifying expected columns, data types, critical columns, no-negative constraints, allowed ranges and regex formats.

---

# Usage

## Running a Workflow

All workflows are available from the LifeWatch VRE at `beta.my.lifewatch.dev/vre`. Log in with your LifeWatch account and navigate to the **BIOMA ICP** virtual research environment.

### Workflow 1 — Data Validation

```
Inputs required:
  /mnt/inputs/allData.zip           — ZIP of completed Excel templates (Level 0)
  /mnt/inputs/tables_config.txt     — Validation configuration JSON
  /mnt/inputs/samplesInfo.xlsx      — Sample metadata (required from Step 5 onwards)

Key parameters (Step 5):
  param_ionsdiff_low_k   = 20.0   (IonsDiff% limit for EC ≤ 20 µS/cm)
  param_ionsdiff_high_k  = 10.0   (IonsDiff% limit for EC > 20 µS/cm)
  param_conddiff_low_1   = 30.0   (CondDiff% limit for EC ≤ 10 µS/cm)
  param_conddiff_low_2   = 20.0   (CondDiff% limit for 10 < EC ≤ 20 µS/cm)
  param_conddiff_high    = 10.0   (CondDiff% limit for EC > 20 µS/cm)
  param_ratio_nacl_low   = 0.5    (Na/Cl lower bound)
  param_ratio_nacl_high  = 1.5    (Na/Cl upper bound)

LOQ parameters (Step 3): 24 element-specific parameters — see component documentation.

Primary outputs:
  validation_log.txt                  — Format check report (Step 1)
  water_chemical_data_level2_validated.zip — Validated CSV per SiteCode (Step 5)
  validation_report.pdf               — QC summary report (Step 6)
  Samples2Repeat.xlsx                 — Samples requiring re-analysis (Step 6)
  allFinalData.xlsx                   — All validated samples (Step 6)
  data2report.xlsx                    — Level-3 reporting dataset (Step 7)
```

### Workflow 2 — Outlier Detection and Database Update

```
Inputs required:
  /mnt/inputs/allFinalData.xlsx     — Level-3 validated data from Workflow 1
  /mnt/inputs/samplesInfo.xlsx      — Sample metadata

Outputs:
  outlier_report.xlsx               — Flagged samples for expert review
  database_update_log.txt           — Record of ingested samples
```

### Workflow 3 — Multi-Source Data Integration

```
Inputs required:
  Validated Level-3 chemistry data
  Area of Interest (AOI) spatial boundary
  Date range for satellite image retrieval

Outputs:
  Harmonised analysis-ready dataset combining chemistry, spectral indices
  and environmental covariates
```

### Workflow 4 — Environmental Analysis

```
Inputs required:
  Integrated dataset from Workflow 3 (or directly from Workflow 2)

Outputs:
  Trend analysis tables and plots
  Deposition load summaries
  Cross-site comparison figures
```

## Local Execution (Workflow 1)

All Tesseract wrappers can be built and run locally using Docker. Workflow 1 components are available as individual Docker images:

```bash
# Build a component
docker build -t input-data-format-validation:0.0.1 .

# Run with example data (Windows PowerShell)
docker run --rm `
  -v "${PWD}/resources/example/data/inputs:/mnt/inputs:ro" `
  -v "${PWD}/resources/example/data/outputs:/mnt/outputs" `
  input-data-format-validation:0.0.1
```

---

# Repository Structure

```
lifewatch-vre/Workflows/Chemical validation/
├── components/
│   ├── 1-input-data-format-validation/
│   │   ├── annotation.json
│   │   ├── data_format_validation.py
│   │   ├── Dockerfile
│   │   ├── requirements.txt
│   │   ├── README.md
│   │   └── resources/example/data/
│   │       ├── inputs/
│   │       └── execution-parameters.json
│   ├── 2-water-chemical-data-transformation/
│   ├── 3-loq-application/
│   ├── 4-unit-transformation/
│   ├── 5-water-chemistry-validation/
│   ├── 6-water-chemistry-validation-report/
│   └── 7-data2final-report/
└── README.Rmd     ← this file
```

---

# Research Team

| Name | Institution | Role |
|---|---|---|
| David Elustondo | BIOMA — University of Navarra | Project coordinator |
| Esther Lasheras Adot | BIOMA — University of Navarra | Scientific leader, water quality & analytical techniques |
| Sheila Izquieta | BIOMA — University of Navarra | Development and innovation |
| Julen Torrens | BIOMA — University of Navarra | Data scientist, workflow development |
| Nicolás Goyena | BIOMA — University of Navarra | Data scientist |

**Collaborating institutions:**  
Confederación Hidrográfica del Júcar (CHJ) — data and site access  
Ministry for Ecological Transition and the Demographic Challenge (MITECO) — national ICP coordination  
LifeWatch ERIC — platform infrastructure and technical support

---

# References and Further Reading

- **ICP Forests** programme manual: <https://www.icp-forests.org/pdf/manual.pdf>
- **ICP Integrated Monitoring** manual: <https://www.syke.fi/nature/icpim>
- Gran, G. (1952). Determination of the equivalence point in potentiometric titrations. Part II. *Analyst*, 77(920), 661–671.
- Davies, C.W. (1962). *Ion Association*. Butterworths, London.
- Kohlrausch, F. (1876). Ueber das Leitvermögen der Elektrolyte. *Annalen der Physik*, 237(9), 1–14.
- **LifeWatch ERIC** VRE: <https://www.lifewatch.eu>
- **CLRTAP** protocols: <https://unece.org/environment-policy/air/clrtap>
