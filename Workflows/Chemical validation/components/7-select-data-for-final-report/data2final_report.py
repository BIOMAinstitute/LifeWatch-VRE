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
# This ensures that only validated data reaches the final report,
# using the replicate to rescue failed measurements where possible.
#
# Input:  allFinalData.xlsx (from WaterChemistryValidationReport)
#         samplesInfo.xlsx  (SampleID -> ICP_Program, Instrument, etc.)
# Output: data2report.xlsx  (one row per sample per month, final columns only)
# ------------------------------------------------------------

# ============================================================
# IMPORTS
# ============================================================
import os
import argparse
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
input_data_path    = "/mnt/inputs/allFinalData.xlsx"
input_samples_path = "/mnt/inputs/samplesInfo.xlsx"
output_path        = "/mnt/outputs/data2report.xlsx"

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

# ============================================================
# LOAD DATA
# ============================================================

df          = pd.read_excel(input_data_path)
sampling_ty = pd.read_excel(input_samples_path)
print(f"Loaded {len(df)} rows from allFinalData.xlsx")
print(f"Loaded {len(sampling_ty)} rows from samplesInfo.xlsx")

# ============================================================
# CLEAN AND MERGE
# ============================================================

df["SampleID_clean"]          = clean_sample_id(df["SampleID"])
sampling_ty["SampleID_clean"] = clean_sample_id(sampling_ty["SampleID"])

# Bring in programme/instrument/DB metadata from samplesInfo
merge_cols = [c for c in ["SampleID_clean", "ICP_Program", "SamplingTypology", "Instrument", "ID_PostgreSQL"]
              if c in sampling_ty.columns]
df = df.merge(sampling_ty[merge_cols], on="SampleID_clean", how="left")

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
    rep    = g[g["is_rep"]]

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

    # Rule 3: both NOREP and REP fail -> keep NOREP (REP must exist)
    if not normal.empty and not rep.empty:
        result_rows.append(normal.iloc[0])
        continue

    # Rule 4: NOREP fails, no REP -> discard (do nothing)

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

tabla_final = tabla_final.reindex(columns=FINAL_COLUMNS)

# ============================================================
# EXPORT
# ============================================================

tabla_final.to_excel(output_path, index=False, sheet_name="Datos")
print(f"Output saved: {output_path}  ({len(tabla_final)} rows, {len(tabla_final.columns)} columns)")