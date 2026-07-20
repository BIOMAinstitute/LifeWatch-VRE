# -*- coding: utf-8 -*-
# ------------------------------------------------------------
# WATER CHEMISTRY VALIDATION
# ------------------------------------------------------------
# This script performs quality validation of water chemistry data
# for ICP-Forest monitoring sites. It merges per-subprogram CSV
# files by SiteCode, fills replicate samples, and computes a set
# of chemical quality indicators:
#
#   1.  Heavy metals sum for SW (soil water) samples
#   2.  NDON  = TN - (NO3-N + NH4-N)
#   3.  Org-  = estimated organic anion from DOC (typology-dependent)
#   4.  Sum of anions (SumAnions)
#   5.  Sum of cations (SumCations, includes metals for SW)
#   6.  Ionic balance  sC - sA  (IonsDiff.%)
#   7.  Ionic balance  sC - sA - Org-  (IonsDiff.% with organic correction)
#   8.  Na/Cl ratio
#   9.  Calculated conductivity (without ionic activity correction)
#   10. Ionic strength
#   11. Ionic activity factor → corrected calculated conductivity
#   12. Conductivity difference %  (Cc - Xm)
#   13. OrgN quality flag  (TN vs NO3+NH4)
#   14. FINAL_VALIDATION flag  (SI / NO)
#
# Thresholds for quality flags are fully configurable via CLI parameters.
#
# Input:  ZIP of unit-transformed CSVs  +  samplesInfo.xlsx
# Output: two ZIP archives:
#           - allData ZIP  : merged (pre-validation) CSV per SiteCode
#           - validated ZIP: validated CSV per SiteCode
# ------------------------------------------------------------

# ============================================================
# IMPORTS
# ============================================================
import os
import re
import sys
import zipfile
import argparse
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

# ------------------------------------------------------------
# CLI argument parsing (Tesseract wrapper convention)
# All quality thresholds are configurable parameters.
# ------------------------------------------------------------
parser = argparse.ArgumentParser(description="Water Chemistry Validation wrapper")

# --- Ion balance thresholds ---
parser.add_argument("--param_ionsdiff_low_k",  type=float, default=20.0,
    help="Max allowed IonsDiff%% for WeightedConductivity <= 20 µS/cm (default: 20.0)")
parser.add_argument("--param_ionsdiff_high_k", type=float, default=10.0,
    help="Max allowed IonsDiff%% for WeightedConductivity > 20 µS/cm (default: 10.0)")

# --- Conductivity difference thresholds (3 tiers based on WeightedConductivity) ---
parser.add_argument("--param_conddiff_low_1",  type=float, default=30.0,
    help="Max allowed CondDiff%% for WeightedConductivity <= 10 µS/cm (default: 30.0)")
parser.add_argument("--param_conddiff_low_2",  type=float, default=20.0,
    help="Max allowed CondDiff%% for WeightedConductivity 10–20 µS/cm (default: 20.0)")
parser.add_argument("--param_conddiff_high",   type=float, default=10.0,
    help="Max allowed CondDiff%% for WeightedConductivity > 20 µS/cm (default: 10.0)")

# --- Na/Cl ratio thresholds ---
parser.add_argument("--param_ratio_nacl_low",  type=float, default=0.5,
    help="Lower bound of acceptable Na/Cl ratio (default: 0.5)")
parser.add_argument("--param_ratio_nacl_high", type=float, default=1.5,
    help="Upper bound of acceptable Na/Cl ratio (default: 1.5)")

args = parser.parse_args()

# ------------------------------------------------------------
# Paths — Tesseract mounts inputs at /mnt/inputs, outputs at /mnt/outputs
# ------------------------------------------------------------
input_zip_path        = os.environ.get("INPUT_ZIP_PATH", "/mnt/inputs/water_chemical_data_level1_units.zip")
input_samples_path    = os.environ.get("INPUT_SAMPLES_PATH", "/mnt/inputs/samplesInfo.xlsx")
output_alldata_dir    = os.environ.get("OUTPUT_ALLDATA_DIR", "/mnt/outputs/level2_alldata")
output_validated_dir  = os.environ.get("OUTPUT_VALIDATED_DIR", "/mnt/outputs/level2_validated")
output_alldata_zip    = os.environ.get("OUTPUT_ALLDATA_ZIP", "/mnt/outputs/water_chemical_data_level2_alldata.zip")
output_validated_zip  = os.environ.get("OUTPUT_VALIDATED_ZIP", "/mnt/outputs/water_chemical_data_level2_validated.zip")

os.makedirs(output_alldata_dir,   exist_ok=True)
os.makedirs(output_validated_dir, exist_ok=True)

# Extract input ZIP to a temporary working directory
extract_dir = os.environ.get("EXTRACT_DIR", "/tmp/input/level1_units")
os.makedirs(extract_dir, exist_ok=True)
with zipfile.ZipFile(input_zip_path, "r") as z:
    z.extractall(extract_dir)
print(f"Input ZIP extracted to {extract_dir}")

# ============================================================
# CHEMICAL CONSTANTS
# ============================================================

# Equivalent conductances (S·cm²/eq) used to compute theoretical conductivity
EQUIV_COND = {
    'H(µeq/l)':                    350,
    'NH4N(µeq/l)':                 73.5,
    'CA(µeq/l)':                   59.5,
    'MG(µeq/l)':                   53.1,
    'NA(µeq/l)':                   50.1,
    'K(µeq/l)':                    73.5,
    'AL(µeq/l)':                   61,
    'FE(µeq/l)':                   68,
    'MN(µeq/l)':                   53.5,
    'AlkalinityICPForests(µeq/l)': 44.5,
    'SO4S(µeq/l)':                 80,
    'NO3N(µeq/l)':                 71.4,
    'CL(µeq/l)':                   76.4,
}

# Ionic charges used for ionic strength calculation
ION_CHARGE = {
    'H(µeq/l)':                    1,
    'NH4N(µeq/l)':                 1,
    'CA(µeq/l)':                   2,
    'MG(µeq/l)':                   2,
    'NA(µeq/l)':                   1,
    'K(µeq/l)':                    1,
    'AlkalinityICPForests(µeq/l)': 1,
    'SO4S(µeq/l)':                 2,
    'NO3N(µeq/l)':                 1,
    'CL(µeq/l)':                   1,
}

# Column subsets expected from each subprogram CSV
# Used to select and align columns during the merge step
PATTERNS = {
    "ANIONS": [
        'SampleID', 'SiteCode', 'SiteName', 'year', 'month',
        'CL(µeq/l)', 'CL(mg/l)', 'SO4S(µeq/l)', 'SO4S(mg/l)',
        'NO3N(µeq/l)', 'NO3N(mg/l)', 'PO4P(µeq/l)', 'PO4P(mg/l)',
    ],
    "CATIONS": [
        'SampleID', 'SiteCode', 'SiteName', 'year', 'month',
        'CA(µeq/l)', 'CA(mg/l)', 'MG(µeq/l)', 'MG(mg/l)',
        'NA(µeq/l)', 'NA(mg/l)', 'K(µeq/l)', 'K(mg/l)',
        'AL(µeq/l)', 'AL(mg/l)', 'FE(µeq/l)', 'FE(mg/l)',
        'MN(µeq/l)', 'MN(mg/l)', 'AS(µeq/l)', 'AS(mg/l)',
        'CD(µeq/l)', 'CD(mg/l)', 'CR(µeq/l)', 'CR(mg/l)',
        'CU(µeq/l)', 'CU(mg/l)', 'CO(µeq/l)', 'CO(mg/l)',
        'MO(µeq/l)', 'MO(mg/l)', 'NI(µeq/l)', 'NI(mg/l)',
        'PB(µeq/l)', 'PB(mg/l)', 'ZN(µeq/l)', 'ZN(mg/l)',
        'P(µeq/l)',  'P(mg/l)',  'S(µeq/l)',  'S(mg/l)',
    ],
    "AMMONIUM": [
        'SampleID', 'SiteCode', 'SiteName', 'year', 'month',
        'NH4N(µeq/l)', 'NH4N(mg/l)',
    ],
    "DOC_TN": [
        'SampleID', 'SiteCode', 'SiteName', 'year', 'month',
        'TN(mg/l)', 'DOC(mg/l)',
    ],
    "pH_COND": [
        'SampleID', 'SiteCode', 'SiteName', 'year', 'month',
        'H(µeq/l)', 'WeightedConductivity(µS/cm)',
        'Volume(ml)', 'Precip(l/m2)', 'WeightedpH',
    ],
    "ALKALINITY": [
        'SampleID', 'SiteCode', 'SiteName', 'year', 'month',
        'AlkalinityICPForests(µeq/l)',
    ],
}

# Final column order for the merged allData output
FINAL_COLUMNS = [
    'SampleID', 'SiteCode', 'SiteName', 'year', 'month',
    'CL(µeq/l)', 'CL(mg/l)', 'SO4S(µeq/l)', 'SO4S(mg/l)',
    'NO3N(µeq/l)', 'NO3N(mg/l)', 'PO4P(µeq/l)', 'PO4P(mg/l)',
    'CA(µeq/l)', 'CA(mg/l)', 'MG(µeq/l)', 'MG(mg/l)',
    'NA(µeq/l)', 'NA(mg/l)', 'K(µeq/l)', 'K(mg/l)',
    'AL(µeq/l)', 'AL(mg/l)', 'FE(µeq/l)', 'FE(mg/l)',
    'MN(µeq/l)', 'MN(mg/l)', 'AS(µeq/l)', 'AS(mg/l)',
    'CD(µeq/l)', 'CD(mg/l)', 'CR(µeq/l)', 'CR(mg/l)',
    'CU(µeq/l)', 'CU(mg/l)', 'CO(µeq/l)', 'CO(mg/l)',
    'MO(µeq/l)', 'MO(mg/l)', 'NI(µeq/l)', 'NI(mg/l)',
    'PB(µeq/l)', 'PB(mg/l)', 'ZN(µeq/l)', 'ZN(mg/l)',
    'P(µeq/l)',  'P(mg/l)',  'S(µeq/l)',  'S(mg/l)',
    'NH4N(µeq/l)', 'NH4N(mg/l)', 'TN(mg/l)', 'DOC(mg/l)',
    'H(µeq/l)', 'WeightedConductivity(µS/cm)',
    'Volume(ml)', 'Precip(l/m2)', 'WeightedpH',
    'AlkalinityICPForests(µeq/l)',
]

# ============================================================
# QUALITY THRESHOLDS (from CLI args)
# ============================================================

@dataclass
class Limits:
    ionsdiff_low_k:  float  # IonsDiff% limit when WeightedConductivity <= 20 µS/cm
    ionsdiff_high_k: float  # IonsDiff% limit when WeightedConductivity > 20 µS/cm
    conddiff_low_1:  float  # CondDiff% limit when WeightedConductivity <= 10 µS/cm
    conddiff_low_2:  float  # CondDiff% limit when WeightedConductivity 10–20 µS/cm
    conddiff_high:   float  # CondDiff% limit when WeightedConductivity > 20 µS/cm
    ratio_nacl_low:  float  # Lower bound of acceptable Na/Cl ratio
    ratio_nacl_high: float  # Upper bound of acceptable Na/Cl ratio

limits = Limits(
    ionsdiff_low_k  = args.param_ionsdiff_low_k,
    ionsdiff_high_k = args.param_ionsdiff_high_k,
    conddiff_low_1  = args.param_conddiff_low_1,
    conddiff_low_2  = args.param_conddiff_low_2,
    conddiff_high   = args.param_conddiff_high,
    ratio_nacl_low  = args.param_ratio_nacl_low,
    ratio_nacl_high = args.param_ratio_nacl_high,
)

# ============================================================
# HELPER FUNCTIONS
# ============================================================

def clean_id(value):
    """
    Normalises a SampleID to uppercase with no spaces, underscores,
    hyphens, commas or dots. Used for robust cross-file matching.
    """
    return re.sub(r"[ _\-,.]", "", str(value).upper()) if pd.notna(value) else value


def ensure_columns(df, columns, to_numeric=False, fill_value=np.nan):
    """
    Ensures all listed columns exist in the DataFrame.
    - If a column exists and to_numeric=True, converts it to numeric (coercing errors to NaN).
    - If a column does not exist, creates it with fill_value.
    """
    for c in columns:
        if c in df.columns:
            if to_numeric:
                df[c] = pd.to_numeric(df[c], errors='coerce')
        else:
            df[c] = fill_value
    return df


def safe_sum(df, cols):
    """
    Row-wise sum of columns, returning NaN where ALL values are NaN
    (i.e. min_count=1 semantics, unlike the pandas default of returning 0).
    """
    return df[cols].sum(axis=1, min_count=1)


# ============================================================
# MERGE: combine per-subprogram CSVs into one row per sample
# ============================================================

def merge_csv_files(input_dir, code):
    """
    Reads all CSV files that belong to a given SiteCode and merges
    them into a single wide DataFrame (one row per sample).

    File matching: filename must start with exactly <code>_ to avoid
    partial matches (e.g. code '5' matching '50_...').
    Each file is matched to a subprogram via PATTERNS keys in its name.
    Only the columns listed in PATTERNS are kept, then an outer join
    is performed on the identity columns (SampleID, SiteCode, SiteName,
    year, month).
    """
    all_data = pd.DataFrame()
    files = [
        f for f in os.listdir(input_dir)
        if f.split('_', 1)[0] == code and f.endswith(".csv")
    ]

    for archivo in files:
        for key, columns in PATTERNS.items():
            if key not in archivo:
                continue

            df = pd.read_csv(os.path.join(input_dir, archivo), sep="\t")

            # Drop rows that have no data beyond the identity columns
            id_cols  = ['SampleID', 'SiteCode', 'SiteName', 'year', 'month']
            data_cols = [c for c in df.columns if c not in id_cols]
            df = df[df[data_cols].notna().sum(axis=1) > 0]

            # Keep only the columns defined for this subprogram
            df = df[[c for c in columns if c in df.columns]]
            df = df.drop_duplicates(subset=id_cols)
            df['SampleID'] = df['SampleID'].apply(clean_id)

            if all_data.empty:
                all_data = df
            else:
                all_data = pd.merge(all_data, df, on=id_cols, how="outer")
            break

    if not all_data.empty:
        all_data = all_data.reindex(columns=FINAL_COLUMNS)
        all_data = all_data.sort_values(by=["year", "month"]).reset_index(drop=True)

    return all_data


# ============================================================
# FILL REPLICATE SAMPLES
# ============================================================

def fill_repetitions(df):
    """
    Propagates metadata from a base sample to its replicate (REP).

    For each group sharing the same SiteCode / year / month / base SampleID,
    if a REP row has NaN in a column that the base row has a value for,
    the base value is copied into the REP row. This ensures replicates
    carry the same site/date metadata even if it was only recorded once.
    """
    d = df.copy()
    d["SampleID"] = d["SampleID"].apply(clean_id)
    d = d.replace(r"^\s*$", np.nan, regex=True)

    d["is_rep"]       = d["SampleID"].astype(str).str.contains(r"REP$", na=False)
    d["SampleID_base"] = d["SampleID"].astype(str).str.replace(r"REP$", "", regex=True)

    helper_cols  = ["SampleID", "SampleID_base", "is_rep"]
    cols_to_fill = [c for c in d.columns if c not in helper_cols]

    for _, g in d.groupby(["SiteCode", "year", "month", "SampleID_base"], dropna=False):
        normal = g[~g["is_rep"]]
        rep    = g[g["is_rep"]]
        if normal.empty or rep.empty:
            continue
        source = normal.iloc[0]
        for rep_idx in rep.index:
            d.loc[rep_idx, cols_to_fill] = (
                d.loc[rep_idx, cols_to_fill].combine_first(source[cols_to_fill])
            )

    return d.drop(columns=["SampleID_base", "is_rep"])


# ============================================================
# CHEMICAL VALIDATION
# ============================================================

def validate_chemistry(df, limits):
    """
    Computes all chemical quality indicators and adds them as new columns.

    Columns added (see module docstring for full list):
      Metals_SW(µeq/l), NDON(mg/l), Quality_NDON,
      Org-(µeq/l), SumAnions(µeq/l), +Org(µeq/l), SumCations(µeq/l),
      sC - sA IonsDiff.%, IonsDiff.Limit(%), IonsDiff.OverLimit.pp,
      IonsDiff.OverLimit.relative%, sC - sA QualityIonsBalance,
      sC - sA - Org- IonsDiff.%, [same OverLimit metrics],
      sC - sA - Org- QualityIonsBalance,
      RatioNa/Cl, NaClDelta, NaClOverLimit.relative%, QualityRatioNa/Cl,
      ConductivityCalculatedWithoutCorrection(µS/cm),
      IonicStrenght(mol/l), IonicActivityFactor,
      ConductivityCalculatedCorrected(µS/cm), ConductivityDiff.(µS/cm),
      Cond.-Cond.H+(µS/cm), Cond. Diff.%Cc-Xm,
      CondDiff.Limit(%), CondDiff.OverLimit.pp, CondDiff.OverLimit.relative%,
      QualityConductivity, QualityOrgN, OrgN_UnderLimit.mgL,
      OrgN_UnderLimit.relative%, FINAL_VALIDATION
    """

    # ----------------------------------------------------------
    # 1. Heavy metals sum — only for SW (soil water) samples
    # ----------------------------------------------------------
    metal_cols = ['AL(µeq/l)', 'FE(µeq/l)', 'MN(µeq/l)']
    df = ensure_columns(df, metal_cols, to_numeric=True)
    df['Metals_SW(µeq/l)'] = np.nan
    if 'SamplingTypology' in df.columns:
        mask_sw = df['SamplingTypology'].astype(str).str.contains('SW', na=False)
        df.loc[mask_sw, 'Metals_SW(µeq/l)'] = safe_sum(df.loc[mask_sw], metal_cols)

    # ----------------------------------------------------------
    # 2. NDON (mg/l) = TN - (NO3-N + NH4-N)
    #    Represents dissolved organic nitrogen not accounted for
    #    by inorganic fractions. Negative values flag TN inconsistency.
    # ----------------------------------------------------------
    ndon_cols = ['TN(mg/l)', 'NO3N(mg/l)', 'NH4N(mg/l)']
    df = ensure_columns(df, ndon_cols, to_numeric=True)
    df['NDON(mg/l)']    = df['TN(mg/l)'] - (df['NO3N(mg/l)'] + df['NH4N(mg/l)'])
    df['Quality_NDON']  = np.where(
        df[ndon_cols].isna().any(axis=1), 'incomplete', 'ok'
    )

    # ----------------------------------------------------------
    # 3. Organic anion (Org-) estimated from DOC
    #    Relationship coefficients are sampling-typology-dependent
    #    (ICP-Forest empirical calibrations):
    #      STF (stemflow):       Org- = 5.04·DOC - 6.67
    #      THR BL (throughfall): Org- = 6.80·DOC - 12.32
    #      THR other:            Org- = 4.17·DOC - 5.01
    #      SW (soil water):      Org- = 9.80·DOC
    # ----------------------------------------------------------
    df = ensure_columns(df, ['DOC(mg/l)'], to_numeric=True)
    df['Org-(µeq/l)'] = np.nan
    if 'SamplingTypology' in df.columns:
        s        = df['SamplingTypology'].astype(str)
        stf_m    = s.str.contains('STF', na=False)
        thr_m    = s.str.contains('THR', na=False)
        thr_bl_m = thr_m & s.str.endswith('BL', na=False)
        sw_m     = s.str.contains('SW', na=False)

        df.loc[stf_m,              'Org-(µeq/l)'] = 5.04 * df.loc[stf_m,              'DOC(mg/l)'] - 6.67
        df.loc[thr_bl_m,           'Org-(µeq/l)'] = 6.80 * df.loc[thr_bl_m,           'DOC(mg/l)'] - 12.32
        df.loc[thr_m & ~thr_bl_m,  'Org-(µeq/l)'] = 4.17 * df.loc[thr_m & ~thr_bl_m,  'DOC(mg/l)'] - 5.01
        df.loc[sw_m,               'Org-(µeq/l)'] = 9.80 * df.loc[sw_m,               'DOC(mg/l)']

    # ----------------------------------------------------------
    # 4. Sum of anions (µeq/l)
    # ----------------------------------------------------------
    anion_cols = ['AlkalinityICPForests(µeq/l)', 'CL(µeq/l)', 'SO4S(µeq/l)', 'NO3N(µeq/l)']
    df = ensure_columns(df, anion_cols, to_numeric=True)
    df['SumAnions(µeq/l)'] = safe_sum(df, anion_cols)

    # ----------------------------------------------------------
    # 5. Sum of anions + Org-  and  Sum of cations
    # ----------------------------------------------------------
    df['+Org(µeq/l)'] = safe_sum(df, ['SumAnions(µeq/l)', 'Org-(µeq/l)'])

    cation_cols = ['H(µeq/l)', 'NH4N(µeq/l)', 'CA(µeq/l)', 'MG(µeq/l)', 'NA(µeq/l)', 'K(µeq/l)']
    df = ensure_columns(df, cation_cols, to_numeric=True)
    base_cations = df[cation_cols].sum(axis=1, min_count=1)
    # Include SW metals in cation sum where available
    df['SumCations(µeq/l)'] = (
        pd.concat([base_cations, df['Metals_SW(µeq/l)']], axis=1)
        .sum(axis=1, min_count=1)
    )

    # ----------------------------------------------------------
    # 6. Ionic balance: sC - sA  (IonsDiff.%)
    #    IonsDiff% = 100 * (SumCations - SumAnions) / (0.5 * (SumCations + SumAnions))
    #    Quality limit depends on WeightedConductivity:
    #      <= 20 µS/cm -> param_ionsdiff_low_k
    #       > 20 µS/cm -> param_ionsdiff_high_k
    # ----------------------------------------------------------
    wc   = df['WeightedConductivity(µS/cm)']
    denom = (0.5 * (df['SumCations(µeq/l)'] + df['SumAnions(µeq/l)'])).replace(0, np.nan)
    df['sC - sA IonsDiff.%'] = 100 * (df['SumCations(µeq/l)'] - df['SumAnions(µeq/l)']) / denom
    ionsdiff_abs = df['sC - sA IonsDiff.%'].abs()

    ions_limit = np.where(wc <= 20, limits.ionsdiff_low_k, limits.ionsdiff_high_k)
    df['IonsDiff.Limit(%)']            = ions_limit
    df['IonsDiff.OverLimit.pp']        = (ionsdiff_abs - ions_limit).where(
        ~(ionsdiff_abs.isna() | pd.isna(ions_limit))
    ).clip(lower=0)
    df['IonsDiff.OverLimit.relative%'] = np.where(
        ions_limit > 0, 100 * df['IonsDiff.OverLimit.pp'] / ions_limit, np.nan
    )
    df['sC - sA QualityIonsBalance'] = np.where(
        ((wc <= 20) & (ionsdiff_abs <= limits.ionsdiff_low_k)) |
        ((wc  > 20) & (ionsdiff_abs <= limits.ionsdiff_high_k)),
        'ok', 'NO'
    )
    df.loc[wc.isna() | ionsdiff_abs.isna(), 'sC - sA QualityIonsBalance'] = np.nan

    # ----------------------------------------------------------
    # 7. Ionic balance with organic correction: sC - sA - Org-
    # ----------------------------------------------------------
    denom_org = (0.5 * (df['SumCations(µeq/l)'] + df['+Org(µeq/l)'])).replace(0, np.nan)
    df['sC - sA - Org- IonsDiff.%'] = (
        100 * (df['SumCations(µeq/l)'] - df['+Org(µeq/l)']) / denom_org
    )
    ionsdiff_org_abs = df['sC - sA - Org- IonsDiff.%'].abs()

    df['IonsDiffOrg.Limit(%)']            = ions_limit
    df['IonsDiffOrg.OverLimit.pp']        = (ionsdiff_org_abs - ions_limit).where(
        ~(ionsdiff_org_abs.isna() | pd.isna(ions_limit))
    ).clip(lower=0)
    df['IonsDiffOrg.OverLimit.relative%'] = np.where(
        ions_limit > 0, 100 * df['IonsDiffOrg.OverLimit.pp'] / ions_limit, np.nan
    )
    df['sC - sA - Org- QualityIonsBalance'] = np.where(
        ((wc <= 20) & (ionsdiff_org_abs <= limits.ionsdiff_low_k)) |
        ((wc  > 20) & (ionsdiff_org_abs <= limits.ionsdiff_high_k)),
        'ok', 'NO'
    )
    df.loc[wc.isna() | ionsdiff_org_abs.isna(), 'sC - sA - Org- QualityIonsBalance'] = np.nan

    # ----------------------------------------------------------
    # 8. Na/Cl ratio
    #    Expected range: [param_ratio_nacl_low, param_ratio_nacl_high]
    #    Deviations suggest sea-salt influence or analytical errors.
    # ----------------------------------------------------------
    df = ensure_columns(df, ['NA(µeq/l)', 'CL(µeq/l)'], to_numeric=True)
    cl    = df['CL(µeq/l)'].replace(0, np.nan)
    ratio = df['NA(µeq/l)'] / cl
    df['RatioNa/Cl'] = ratio

    below   = ratio < limits.ratio_nacl_low
    above   = ratio > limits.ratio_nacl_high
    outside = below | above

    df['NaClDelta'] = 0.0
    df.loc[below, 'NaClDelta'] = limits.ratio_nacl_low  - ratio
    df.loc[above, 'NaClDelta'] = ratio - limits.ratio_nacl_high

    nearest_limit = pd.Series(np.nan, index=df.index)
    nearest_limit.loc[below] = limits.ratio_nacl_low
    nearest_limit.loc[above] = limits.ratio_nacl_high

    df['NaClOverLimit.relative%'] = np.where(
        nearest_limit > 0, 100 * df['NaClDelta'] / nearest_limit, 0
    )
    df['QualityRatioNa/Cl'] = 'ok'
    df.loc[outside,    'QualityRatioNa/Cl'] = 'NO'
    df.loc[ratio.isna(), 'QualityRatioNa/Cl'] = np.nan

    # ----------------------------------------------------------
    # 9. Theoretical conductivity (without ionic activity correction)
    #    Cc = sum(conc_i * lambda_i) / 1000
    #    where lambda_i is the equivalent conductance of ion i.
    # ----------------------------------------------------------
    cond_cols = list(EQUIV_COND.keys())
    df = ensure_columns(df, cond_cols, to_numeric=True)
    exist_cond = [c for c in cond_cols if c in df.columns]
    if exist_cond:
        lambda_series = pd.Series({c: EQUIV_COND[c] for c in exist_cond})
        df['ConductivityCalculatedWithoutCorrection(µS/cm)'] = (
            (df[exist_cond] * lambda_series).sum(axis=1, min_count=1) / 1000
        )
    else:
        df['ConductivityCalculatedWithoutCorrection(µS/cm)'] = np.nan

    # ----------------------------------------------------------
    # 10. Ionic strength (semi-empirical formula)
    #     I = sum(conc_i * z_i) / (1000 * 2000)
    # ----------------------------------------------------------
    ionic_cols = list(ION_CHARGE.keys())
    df = ensure_columns(df, ionic_cols, to_numeric=True)
    exist_ionic = [c for c in ionic_cols if c in df.columns]
    if exist_ionic:
        charge_series = pd.Series({c: ION_CHARGE[c] for c in exist_ionic})
        df['IonicStrenght(mol/l)'] = (
            (df[exist_ionic] * charge_series).sum(axis=1, min_count=1) / 1000 / 2000
        )
    else:
        df['IonicStrenght(mol/l)'] = np.nan

    # ----------------------------------------------------------
    # 11. Ionic activity factor (Davies equation, semi-empirical)
    #     f = 10^(-0.5 * (sqrt(I)/(1+sqrt(I)) - 0.3*I))
    #     Corrected conductivity: Cc_corr = Cc * f^2
    # ----------------------------------------------------------
    df = ensure_columns(df, ['IonicStrenght(mol/l)'], to_numeric=True)
    I = df['IonicStrenght(mol/l)'].clip(lower=0)
    df['IonicActivityFactor'] = 10 ** (-0.5 * ((I**0.5 / (1 + I**0.5)) - 0.3 * I))
    df['ConductivityCalculatedCorrected(µS/cm)'] = (
        df['ConductivityCalculatedWithoutCorrection(µS/cm)'] * (df['IonicActivityFactor'] ** 2)
    )

    # ----------------------------------------------------------
    # 12. Conductivity difference %  (Cc - Xm)
    #     CondDiff% = 100 * (Cc_corr - Xm) / Xm
    #     Three quality tiers based on measured conductivity (Xm):
    #       Xm <= 10  -> param_conddiff_low_1
    #       Xm 10–20  -> param_conddiff_low_2
    #       Xm > 20   -> param_conddiff_high
    # ----------------------------------------------------------
    df = ensure_columns(df, ['WeightedConductivity(µS/cm)'], to_numeric=True)
    wc_safe = df['WeightedConductivity(µS/cm)'].replace(0, np.nan)

    df['ConductivityDiff.(µS/cm)'] = (
        df['ConductivityCalculatedCorrected(µS/cm)'] - df['WeightedConductivity(µS/cm)']
    )
    if 'H(µeq/l)' in df.columns:
        df = ensure_columns(df, ['H(µeq/l)'], to_numeric=True)
        H_lambda = EQUIV_COND.get('H(µeq/l)', 350) * 0.001
        df['Cond.-Cond.H+(µS/cm)'] = (
            df['WeightedConductivity(µS/cm)'] - df['H(µeq/l)'] * H_lambda
        )
    else:
        df['Cond.-Cond.H+(µS/cm)'] = np.nan

    df['Cond. Diff.%Cc-Xm'] = 100 * (
        df['ConductivityCalculatedCorrected(µS/cm)'] - wc_safe
    ) / wc_safe

    conddiff_abs = df['Cond. Diff.%Cc-Xm'].abs()
    cond_limit   = np.select(
        [wc_safe <= 10, (wc_safe > 10) & (wc_safe <= 20), wc_safe > 20],
        [limits.conddiff_low_1, limits.conddiff_low_2, limits.conddiff_high],
        default=np.nan
    )
    df['CondDiff.Limit(%)']            = cond_limit
    df['CondDiff.OverLimit.pp']        = (conddiff_abs - cond_limit).where(
        ~(conddiff_abs.isna() | pd.isna(cond_limit))
    ).clip(lower=0)
    df['CondDiff.OverLimit.relative%'] = np.where(
        cond_limit > 0, 100 * df['CondDiff.OverLimit.pp'] / cond_limit, np.nan
    )

    df['QualityConductivity'] = 'NO'
    df.loc[
        ((wc_safe <= 10) & (conddiff_abs <= limits.conddiff_low_1)) |
        ((wc_safe > 10) & (wc_safe <= 20) & (conddiff_abs <= limits.conddiff_low_2)) |
        ((wc_safe > 20) & (conddiff_abs <= limits.conddiff_high)),
        'QualityConductivity'
    ] = 'ok'
    df.loc[wc_safe.isna() | conddiff_abs.isna(), 'QualityConductivity'] = np.nan

    # ----------------------------------------------------------
    # 13. OrgN quality flag
    #     OrgN = TN - (NO3-N + NH4-N)
    #     Negative result means TN is lower than the sum of its
    #     inorganic N fractions, which is chemically impossible
    #     and flags a measurement inconsistency.
    # ----------------------------------------------------------
    orgn_cols = ['TN(mg/l)', 'NO3N(mg/l)', 'NH4N(mg/l)']
    df = ensure_columns(df, orgn_cols, to_numeric=True)
    orgn = df['TN(mg/l)'] - (df['NO3N(mg/l)'] + df['NH4N(mg/l)'])

    df['QualityOrgN'] = pd.NA
    mask_valid = orgn.notna()
    df.loc[mask_valid & (orgn > 0),  'QualityOrgN'] = 'ok'
    df.loc[mask_valid & (orgn <= 0), 'QualityOrgN'] = 'NO TN'

    df['OrgN_UnderLimit.mgL']       = (-orgn).clip(lower=0)
    df['OrgN_UnderLimit.relative%'] = np.where(
        df['TN(mg/l)'].abs() > 0,
        100 * df['OrgN_UnderLimit.mgL'] / df['TN(mg/l)'].abs(),
        np.nan
    )

    # ----------------------------------------------------------
    # 14. FINAL_VALIDATION flag
    #     A sample fails (FINAL_VALIDATION = 'NO') if any of:
    #       - BOF/WET typology AND organic-corrected ion balance fails
    #       - Conductivity check fails
    #       - OrgN check fails (TN inconsistency)
    #       - BOF/WET/THR/STF typology AND Na/Cl ratio fails
    # ----------------------------------------------------------
    df['FINAL_VALIDATION'] = 'SI'

    if 'SamplingTypology' in df.columns:
        s = df['SamplingTypology'].astype(str)

        fail_ions = df.loc[
            s.str.contains('BOF|WET', regex=True, na=False) &
            ((df['sC - sA - Org- QualityIonsBalance'] == 'NO') |
             (df['sC - sA - Org- QualityIonsBalance'].isna()))
        ]
        fail_nacl = df.loc[
            s.str.contains('BOF|WET|THR|STF', regex=True, na=False) &
            ((df['QualityRatioNa/Cl'] == 'NO') |
             (df['QualityRatioNa/Cl'].isna()))
        ]
    else:
        fail_ions = pd.DataFrame()
        fail_nacl = pd.DataFrame()

    fail_cond = df.loc[
        (df['QualityConductivity'] == 'NO') | (df['QualityConductivity'].isna())
    ]
    fail_orgn = df.loc[
        (df['QualityOrgN'] == 'NO TN') | (df['QualityOrgN'].isna())
    ]

    failed = pd.concat([fail_ions, fail_cond, fail_orgn, fail_nacl]).drop_duplicates()
    df.loc[failed.index, 'FINAL_VALIDATION'] = 'NO'

    return df


# ============================================================
# COMPUTE: attach sampling typology and run validation
# ============================================================

def compute_chemistry(df, sampling_ty, limits):
    """
    Merges sampling typology into the data and runs validate_chemistry.
    The join is done on a cleaned base SampleID (without the REP suffix)
    so that both base samples and replicates get the correct typology.
    """
    d = df.copy()
    d["CleanSampleID"]      = d["SampleID"].apply(clean_id)
    d["CleanSampleID_base"] = d["CleanSampleID"].astype(str).str.replace(r"REP$", "", regex=True)

    ty = sampling_ty.copy()
    ty["CleanSampleID"]      = ty["CleanSampleID"].astype(str)
    ty["CleanSampleID_base"] = ty["CleanSampleID"].astype(str).str.replace(r"REP$", "", regex=True)
    ty = ty[["CleanSampleID_base", "SamplingTypology"]].drop_duplicates(
        subset=["CleanSampleID_base"]
    )

    d = d.merge(ty, on="CleanSampleID_base", how="left")
    d = d.drop(columns=["CleanSampleID_base"])
    d = validate_chemistry(d, limits)
    return d


# ============================================================
# MAIN PROCESSING LOOP
# ============================================================

print("--- START PROCESSING ---")

# Load sampling typology file
# samplesInfo.xlsx maps each SampleID to its SamplingTypology
# (e.g. THR CON, BOF BL, SW CON), which drives several
# typology-dependent calculations (Org-, ion balance filter, Na/Cl filter).
if os.path.exists(input_samples_path):
    sampling_ty = pd.read_excel(input_samples_path)
    sampling_ty['CleanSampleID'] = sampling_ty['SampleID'].apply(clean_id)
    sampling_ty = sampling_ty[['CleanSampleID', 'SamplingTypology']]
    print(f"Sampling typology file loaded: {len(sampling_ty)} records")
else:
    # If no typology file is provided, typology-dependent checks are skipped
    sampling_ty = pd.DataFrame(columns=['CleanSampleID', 'SamplingTypology'])
    print("WARNING: samplesInfo.xlsx not found — typology-dependent checks will be skipped.")

# Get unique SiteCodes from CSV filenames
files         = [f for f in os.listdir(extract_dir) if f.endswith(".csv")]
unique_codes  = sorted(set(f.split('_')[0] for f in files))

for code in unique_codes:
    try:
        print(f"\nProcessing SiteCode: {code}")

        # --- A. Merge all subprogram CSVs for this SiteCode ---
        df_merged = merge_csv_files(extract_dir, code)
        if df_merged.empty:
            print(f"  No data found for code {code}, skipping.")
            continue

        # Save allData (pre-validation merged file)
        path_alldata = os.path.join(output_alldata_dir, f"{code}_WATER_allData.csv")
        df_merged.to_csv(path_alldata, sep="\t", index=False)
        print(f"  allData saved: {path_alldata}")

        # --- B. Fill replicate samples with base sample metadata ---
        df_filled = fill_repetitions(df_merged)

        # --- C. Attach typology and run chemical validation ---
        df_validated = compute_chemistry(df_filled, sampling_ty, limits)

        # --- D. Deduplicate: keep the row with fewest NaNs per SampleID/month ---
        # When a SampleID appears multiple times for the same month (e.g. due to
        # partial merges), keep the row that carries the most complete data.
        df_validated['_num_nans'] = df_validated.isna().sum(axis=1)
        df_validated = (
            df_validated
            .sort_values(by=['SampleID', 'month', '_num_nans'])
            .drop_duplicates(subset=['SampleID', 'month'], keep='first')
            .drop(columns='_num_nans')
            .reset_index(drop=True)
        )

        # Save validated file
        path_validated = os.path.join(output_validated_dir, f"{code}_VALIDATED.csv")
        df_validated.to_csv(path_validated, sep="\t", index=False)
        print(f"  Validated saved: {path_validated}")

    except Exception as e:
        print(f"  [ERROR] SiteCode {code}: {e}")

# ============================================================
# PACKAGE OUTPUTS INTO ZIP ARCHIVES
# ============================================================

for zip_path, source_dir in [
    (output_alldata_zip,   output_alldata_dir),
    (output_validated_zip, output_validated_dir),
]:
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zout:
        for fpath in Path(source_dir).glob("*"):
            zout.write(fpath, fpath.name)
    print(f"ZIP written: {zip_path}")

print("\n--- PROCESSING COMPLETE ---")