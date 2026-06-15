# -*- coding: utf-8 -*-
# ------------------------------------------------------------
# DATA TO FINAL REPORT
# ------------------------------------------------------------
# This script selects the best available measurement per sample
# per month to produce the final dataset for ICP reporting and
# database ingestion.
#
# Selection logic (evaluated per base SampleID / year / month):
#   1. NOREP passes validation (VAL = SI)  -> keep NOREP
#   2. NOREP fails, REP passes             -> keep REP
#   3. NOREP fails, REP also fails         -> keep NOREP
#      (only when a REP exists; having both means the sample
#       was repeated deliberately and must be reported)
#   4. NOREP fails, no REP exists          -> discard
#
# After selecting the final valid/representative row, the script
# aggregates samples that belong to the same SiteCode, SiteName,
# year and month.
#
# Aggregation logic:
#   - Concentrations, conductivity, alkalinity and H+:
#       weighted mean by Volume(ml)
#   - WeightedpH:
#       convert pH to [H+], weight by Volume(ml), convert back to pH
#   - Volume(ml):
#       direct sum
#   - Precip(l/m2):
#       direct sum
#   - SampleID:
#       SiteCode_SamplingTypology_Instrument
#       spaces removed from SamplingTypology
#       Instrument only added if not empty
#
# Input:  All_Validated_Data.xlsx (from WaterChemistryValidationReport)
#         samplesInfo.xlsx  (SampleID -> ICP_Program, Instrument, etc.)
# Output: Final_Data.xlsx  (one row per sample/site per month, final columns only)
# ------------------------------------------------------------

# ============================================================
# IMPORTS
# ============================================================

import os
import argparse
import numpy as np
import pandas as pd
import openpyxl

# ------------------------------------------------------------
# CLI argument parsing (Tesseract wrapper convention)
# No user-configurable parameters: selection logic is fixed.
# ------------------------------------------------------------

parser = argparse.ArgumentParser(description="Data to Final Report wrapper")
args = parser.parse_args()

print(f"openpyxl version: {openpyxl.__version__}")

# ------------------------------------------------------------
# Paths — Tesseract mounts inputs at /mnt/inputs, outputs at /mnt/outputs
# ------------------------------------------------------------

input_data_path    = "/mnt/inputs/All_Validated_Data.xlsx"
input_samples_path = "/mnt/inputs/samplesInfo.xlsx"
output_path        = "/mnt/outputs/Final_Data.xlsx"

# ============================================================
# HELPER
# ============================================================

def clean_sample_id(series):
    """Normalise SampleID: uppercase, strip whitespace and separators."""
    return (
        series.astype(str)
        .str.upper()
        .str.strip()
        .str.replace(r"[ \-_]", "", regex=True)
    )


def is_empty(x):
    """Return True for empty-like values."""
    if pd.isna(x):
        return True

    return str(x).strip().lower() in ("", "nan", "none", "nat")


def first_non_empty(series):
    """Return first non-empty value from a Series or list."""
    for x in series:
        if not is_empty(x):
            return str(x).strip()

    return ""


def remove_all_spaces(x):
    """Remove all spaces from a value."""
    if is_empty(x):
        return ""

    return "".join(str(x).strip().split())


def build_final_sample_id(site_code, sampling_typology, instrument):
    """
    Build final SampleID as:

        SiteCode_SamplingTypology_Instrument

    SamplingTypology spaces are removed.
    Instrument is added only if it is not empty.
    """
    site_code = first_non_empty([site_code])
    sampling_typology = remove_all_spaces(sampling_typology)
    instrument = remove_all_spaces(instrument)

    parts = [site_code, sampling_typology]

    if instrument:
        parts.append(instrument)

    return "_".join([p for p in parts if p])


def weighted_mean_by_volume(g, value_col, volume_col="Volume(ml)"):
    """
    Weighted mean using Volume(ml) as weight.

    Used for concentrations, conductivity, alkalinity, H+, etc.
    """
    values = pd.to_numeric(g[value_col], errors="coerce")
    weights = pd.to_numeric(g[volume_col], errors="coerce")

    mask = values.notna() & weights.notna() & (weights > 0)

    if not mask.any():
        return pd.NA

    denominator = weights[mask].sum()

    if denominator == 0:
        return pd.NA

    return (values[mask] * weights[mask]).sum() / denominator


def weighted_ph_by_volume(g, ph_col="WeightedpH", volume_col="Volume(ml)"):
    """
    Correct pH aggregation.

    pH is logarithmic, so it cannot be averaged directly.

    Steps:
      1. Convert pH to [H+]
      2. Calculate weighted mean of [H+] by volume
      3. Convert final [H+] back to pH
    """
    ph = pd.to_numeric(g[ph_col], errors="coerce")
    weights = pd.to_numeric(g[volume_col], errors="coerce")

    mask = ph.notna() & weights.notna() & (weights > 0)

    if not mask.any():
        return pd.NA

    denominator = weights[mask].sum()

    if denominator == 0:
        return pd.NA

    h_final = (np.power(10.0, -ph[mask]) * weights[mask]).sum() / denominator

    if pd.isna(h_final) or h_final <= 0:
        return pd.NA

    return -np.log10(h_final)


def sum_numeric(g, col):
    """Sum numeric values, preserving NA if all values are missing."""
    return pd.to_numeric(g[col], errors="coerce").sum(min_count=1)


def aggregate_same_site_month(g, final_columns):
    """
    Aggregate one SiteCode / SiteName / year / month group.

    If there is only one row, values are kept as they are, but SampleID
    is regenerated using the new naming rule.

    If there is more than one row, values are combined using the
    weighted aggregation rules.
    """
    row0 = g.iloc[0].copy()

    site_code = first_non_empty(g["SiteCode"]) if "SiteCode" in g.columns else ""
    site_name = first_non_empty(g["SiteName"]) if "SiteName" in g.columns else ""

    sampling_typology = (
        first_non_empty(g["SamplingTypology"])
        if "SamplingTypology" in g.columns
        else ""
    )

    instrument = (
        first_non_empty(g["Instrument"])
        if "Instrument" in g.columns
        else ""
    )

    # If there is only one row, keep analytical values exactly as they are,
    # but regenerate SampleID with the final naming rule.
    if len(g) == 1:
        row0["SampleID"] = build_final_sample_id(
            site_code,
            sampling_typology,
            instrument
        )

        return row0.reindex(final_columns)

    out = {col: pd.NA for col in final_columns}

    out["SampleID"] = build_final_sample_id(
        site_code,
        sampling_typology,
        instrument
    )

    out["SiteCode"] = site_code
    out["SiteName"] = site_name
    out["year"] = row0["year"]
    out["month"] = row0["month"]

    for col in final_columns:
        if col in ["SampleID", "SiteCode", "SiteName", "year", "month"]:
            continue

        if col not in g.columns:
            continue

        if col in ["Volume(ml)", "Precip(l/m2)"]:
            out[col] = sum_numeric(g, col)

        elif col == "WeightedpH":
            out[col] = weighted_ph_by_volume(g, col)

        else:
            out[col] = weighted_mean_by_volume(g, col)

    return pd.Series(out).reindex(final_columns)


# ============================================================
# LOAD DATA
# ============================================================

df = pd.read_excel(input_data_path)
sampling_ty = pd.read_excel(input_samples_path)

print(f"Loaded {len(df)} rows from allFinalData.xlsx")
print(f"Loaded {len(sampling_ty)} rows from samplesInfo.xlsx")

# ============================================================
# CLEAN AND MERGE
# ============================================================

df["SampleID_clean"] = clean_sample_id(df["SampleID"])
sampling_ty["SampleID_clean"] = clean_sample_id(sampling_ty["SampleID"])

# Bring in programme/instrument/DB metadata from samplesInfo
merge_cols = [
    c for c in [
        "SampleID_clean",
        "ICP_Program",
        "SamplingTypology",
        "Instrument",
        "ID_PostgreSQL"
    ]
    if c in sampling_ty.columns
]

df = df.merge(
    sampling_ty[merge_cols],
    on="SampleID_clean",
    how="left"
)

# ============================================================
# DETECT REPLICATES
# ============================================================

df["is_rep"] = df["SampleID_clean"].str.contains(r"REP$", na=False)
df["base_id"] = df["SampleID_clean"].str.replace(r"REP$", "", regex=True)

# ============================================================
# NORMALISE VALIDATION FLAG
# ============================================================

df["VAL_bool"] = df["VAL"].astype(str).str.upper().str.strip().eq("SI")

# ============================================================
# SELECTION LOGIC
# ============================================================
# For each unique (base_id, year, month) group apply the four
# rules described in the module docstring above.
# ============================================================

result_rows = []

for _, g in df.groupby(["base_id", "year", "month"], dropna=False):
    normal = g[~g["is_rep"]]
    rep = g[g["is_rep"]]

    # Rule 1: NOREP passes -> keep NOREP
    normal_si = normal[normal["VAL_bool"]]

    if not normal_si.empty:
        result_rows.append(normal_si.iloc[0])
        continue

    # Rule 2: NOREP fails, REP passes -> keep REP
    rep_si = rep[rep["VAL_bool"]]

    if not rep_si.empty:
        result_rows.append(rep_si.iloc[0])
        continue

    # Rule 3: both NOREP and REP fail -> keep NOREP
    # Only when a REP exists.
    if not normal.empty and not rep.empty:
        result_rows.append(normal.iloc[0])
        continue

    # Rule 4: NOREP fails, no REP -> discard
    # Do nothing.

print(f"Rows selected after filtering: {len(result_rows)}")

# ============================================================
# BUILD FINAL TABLE
# ============================================================

tabla_final = pd.DataFrame(result_rows).reset_index(drop=True)

FINAL_COLUMNS = [
    "SampleID", "SiteCode", "SiteName", "year", "month",
    "CL(mg/l)", "SO4S(mg/l)", "NO3N(mg/l)", "PO4P(mg/l)",
    "CA(mg/l)", "MG(mg/l)", "NA(mg/l)", "K(mg/l)",
    "AL(mg/l)", "FE(mg/l)", "MN(mg/l)",
    "AS(mg/l)", "CD(mg/l)", "CR(mg/l)", "CU(mg/l)", "CO(mg/l)",
    "MO(mg/l)", "NI(mg/l)", "PB(mg/l)", "ZN(mg/l)",
    "P(mg/l)", "S(mg/l)",
    "NH4N(mg/l)", "TN(mg/l)", "DOC(mg/l)",
    "H(µeq/l)", "WeightedConductivity(µS/cm)",
    "Volume(ml)", "Precip(l/m2)", "WeightedpH",
    "AlkalinityICPForests(µeq/l)",
]

# Keep auxiliary columns needed for the new SampleID.
# These columns come from samplesInfo.xlsx and will not be exported.
AUX_COLUMNS = [
    "SamplingTypology",
    "Instrument"
]

working_columns = FINAL_COLUMNS + [
    c for c in AUX_COLUMNS
    if c in tabla_final.columns and c not in FINAL_COLUMNS
]

tabla_final = tabla_final.reindex(columns=working_columns)

# ============================================================
# WEIGHTED AGGREGATION BY SITE / YEAR / MONTH
# ============================================================
# If several selected samples have the same SiteCode, SiteName,
# year and month, they are combined into one representative sample.
#
# Aggregation rules:
#   - Concentrations:
#       weighted mean by Volume(ml)
#   - Conductivity:
#       weighted mean by Volume(ml)
#   - Alkalinity:
#       weighted mean by Volume(ml)
#   - H(µeq/l):
#       weighted mean by Volume(ml)
#   - WeightedpH:
#       convert pH to H+, weight by Volume(ml), convert back to pH
#   - Volume(ml):
#       direct sum
#   - Precip(l/m2):
#       direct sum
#   - SampleID:
#       SiteCode_SamplingTypology_Instrument
# ============================================================

GROUP_COLS = [
    "SiteCode",
    "SiteName",
    "year",
    "month"
]

rows_before_aggregation = len(tabla_final)

aggregated_rows = []

for _, g in tabla_final.groupby(GROUP_COLS, dropna=False, sort=False):
    aggregated_rows.append(
        aggregate_same_site_month(
            g=g,
            final_columns=FINAL_COLUMNS
        )
    )

tabla_final = pd.DataFrame(aggregated_rows).reindex(columns=FINAL_COLUMNS)

print(
    f"Rows after weighted aggregation: {len(tabla_final)} "
    f"(from {rows_before_aggregation} selected rows)"
)

# ============================================================
# EXPORT
# ============================================================

tabla_final.to_excel(
    output_path,
    index=False,
    sheet_name="Datos"
)

print(
    f"Output saved: {output_path}  "
    f"({len(tabla_final)} rows, {len(tabla_final.columns)} columns)"
)