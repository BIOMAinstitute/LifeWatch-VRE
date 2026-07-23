# -*- coding: utf-8 -*-
# ------------------------------------------------------------
# LABORATORY QUANTIFICATION LIMIT (LOQ) APPLICATION
# ------------------------------------------------------------
# This script applies the Limit of Quantification (LOQ) to
# water chemistry CSV files produced by the transformation step.
#
# The LOQ is the minimum concentration that a laboratory instrument
# can reliably measure for a given element or compound. Values below
# the LOQ are considered unreliable and are replaced by LOQ / 2,
# which is the standard convention in analytical chemistry for
# left-censored data.
#
# Each LOQ parameter corresponds to a specific element or compound
# measured by the ICP-Forest laboratory equipment.
#
# Input:  ZIP archive containing tab-separated CSV files (one per SiteCode
#         per subprogram), as produced by the DataTransformation wrapper.
# Output: ZIP archive with the same CSVs after LOQ replacement, plus a
#         plain-text log listing every substitution made (file, row, column).
# ------------------------------------------------------------

# ============================================================
# IMPORTS
# ============================================================
import os
import zipfile
import argparse
import pandas as pd
from pathlib import Path

# ------------------------------------------------------------
# CLI argument parsing (Tesseract wrapper convention)
# Parameters are the LOQ values for each measured element/compound.
# Units are mg/L unless stated otherwise.
# ------------------------------------------------------------
parser = argparse.ArgumentParser(description="LOQ Application wrapper")

parser.add_argument("--param_WeightedConductivity", type=float, default=3.0,
    help="LOQ for weighted conductivity (µS/cm)")
parser.add_argument("--param_NH4N",  type=float, default=0.04,     help="LOQ for NH4-N (mg/L)")
parser.add_argument("--param_NO3",   type=float, default=0.05,     help="LOQ for NO3 (mg/L)")
parser.add_argument("--param_SO4",   type=float, default=0.1,      help="LOQ for SO4 (mg/L)")
parser.add_argument("--param_CL",    type=float, default=0.05,     help="LOQ for Cl (mg/L)")
parser.add_argument("--param_AS",    type=float, default=0.000025, help="LOQ for As (mg/L)")
parser.add_argument("--param_CD",    type=float, default=0.000008, help="LOQ for Cd (mg/L)")
parser.add_argument("--param_CR",    type=float, default=0.000037, help="LOQ for Cr (mg/L)")
parser.add_argument("--param_CU",    type=float, default=0.000062, help="LOQ for Cu (mg/L)")
parser.add_argument("--param_CO",    type=float, default=0.000010, help="LOQ for Co (mg/L)")
parser.add_argument("--param_NI",    type=float, default=0.000073, help="LOQ for Ni (mg/L)")
parser.add_argument("--param_PB",    type=float, default=0.000011, help="LOQ for Pb (mg/L)")
parser.add_argument("--param_ZN",    type=float, default=0.000049, help="LOQ for Zn (mg/L)")
parser.add_argument("--param_P",     type=float, default=0.016603, help="LOQ for P (mg/L)")
parser.add_argument("--param_S",     type=float, default=0.500000, help="LOQ for S (mg/L)")
parser.add_argument("--param_CA",    type=float, default=0.150000, help="LOQ for Ca (mg/L)")
parser.add_argument("--param_K",     type=float, default=0.150000, help="LOQ for K (mg/L)")
parser.add_argument("--param_MG",    type=float, default=0.030000, help="LOQ for Mg (mg/L)")
parser.add_argument("--param_NA",    type=float, default=0.040000, help="LOQ for Na (mg/L)")
parser.add_argument("--param_AL",    type=float, default=0.010000, help="LOQ for Al (mg/L)")
parser.add_argument("--param_FE",    type=float, default=0.005000, help="LOQ for Fe (mg/L)")
parser.add_argument("--param_MN",    type=float, default=0.005000, help="LOQ for Mn (mg/L)")
parser.add_argument("--param_DOC",   type=float, default=0.5,      help="LOQ for DOC (mg/L)")
parser.add_argument("--param_TN",    type=float, default=0.1,      help="LOQ for TN (mg/L)")

args = parser.parse_args()

# ------------------------------------------------------------
# Paths — Tesseract mounts inputs at /mnt/inputs, outputs at /mnt/outputs
# ------------------------------------------------------------
input_zip_path = os.environ.get(
    "INPUT_ZIP_PATH", "/mnt/inputs/water_chemical_data_transformed.zip"
)
output_dir = os.environ.get("OUTPUT_DIR", "/mnt/outputs/level1_loq")
output_zip_path = os.environ.get(
    "OUTPUT_ZIP_PATH", "/mnt/outputs/water_chemical_data_transformed_loq.zip"
)
output_log_path = os.environ.get(
    "OUTPUT_LOG_PATH", os.path.join(output_dir, "loq_substitutions.log")
)
os.makedirs(output_dir, exist_ok=True)

# Extract input ZIP to a temporary working directory
extract_dir = os.environ.get("EXTRACT_DIR", "/tmp/input/level1")
os.makedirs(extract_dir, exist_ok=True)
with zipfile.ZipFile(input_zip_path, "r") as z:
    z.extractall(extract_dir)
print(f"Input ZIP extracted to {extract_dir}")

# ------------------------------------------------------------
# Map each CSV column name to its LOQ value from CLI args
# Column names are normalised to lowercase for case-insensitive matching.
# The CSV columns will also be lowercased at read time (see below).
loq_limits = {
    'weightedconductivity(µs/cm)': args.param_WeightedConductivity,
    'nh4n(mg/l)':  args.param_NH4N,
    'no3(mg/l)':   args.param_NO3,
    'so4(mg/l)':   args.param_SO4,
    'cl(mg/l)':    args.param_CL,
    'as(mg/l)':    args.param_AS,
    'cd(mg/l)':    args.param_CD,
    'cr(mg/l)':    args.param_CR,
    'cu(mg/l)':    args.param_CU,
    'co(mg/l)':    args.param_CO,
    'ni(mg/l)':    args.param_NI,
    'pb(mg/l)':    args.param_PB,
    'zn(mg/l)':    args.param_ZN,
    'p(mg/l)':     args.param_P,
    's(mg/l)':     args.param_S,
    'ca(mg/l)':    args.param_CA,
    'k(mg/l)':     args.param_K,
    'mg(mg/l)':    args.param_MG,
    'na(mg/l)':    args.param_NA,
    'al(mg/l)':    args.param_AL,
    'fe(mg/l)':    args.param_FE,
    'mn(mg/l)':    args.param_MN,
    'doc(mg/l)':   args.param_DOC,
    'tn(mg/l)':    args.param_TN,
}

# ============================================================
# APPLY LOQ TO ALL CSV FILES
# ============================================================
# For each value below the LOQ in a relevant column, the value
# is replaced by LOQ / 2. This is the standard half-LOQ
# substitution method for left-censored analytical data.
# Every substitution is recorded in the log file.
# ============================================================

total_substitutions = 0

with open(output_log_path, 'w', encoding='utf-8') as log:
    log.write("FILE\tROW\tCOLUMN\tORIGINAL_VALUE\tLOQ\tREPLACED_BY\n")

    for archivo in sorted(os.listdir(extract_dir)):
        if not archivo.endswith(".csv"):
            continue

        input_path  = os.path.join(extract_dir, archivo)
        output_path = os.path.join(output_dir, archivo)

        df = pd.read_csv(input_path, sep='\t')
        # Normalise column names to lowercase for case-insensitive LOQ matching
        original_columns = {col.lower(): col for col in df.columns}  # lowercase -> original
        df.columns = [col.lower() for col in df.columns]

        for col, loq in loq_limits.items():
            if col not in df.columns:
                continue

            # Convert column to numeric, coercing non-numeric to NaN
            df[col] = pd.to_numeric(df[col], errors='coerce')

            # Identify rows below the LOQ (NaN rows are ignored)
            mask = df[col] < loq
            rows_below = df.index[mask].tolist()

            # Log each substitution with original value for traceability
            for row_idx in rows_below:
                original_value = df.at[row_idx, col]
                replacement    = loq / 2
                log.write(f"{archivo}\t{row_idx + 1}\t{col}\t{original_value}\t{loq}\t{replacement}\n")
                total_substitutions += 1

            # Replace values below LOQ with LOQ / 2
            df.loc[mask, col] = loq / 2

        # Restore original column casing before saving
        df.columns = [original_columns.get(col, col) for col in df.columns]
        df.to_csv(output_path, index=False, sep='\t')
        print(f"Processed: {archivo}")

print(f"LOQ application complete. Total substitutions: {total_substitutions}")
print(f"Substitution log written to {output_log_path}")

# ============================================================
# PACKAGE OUTPUT FILES INTO ZIP
# ============================================================
with zipfile.ZipFile(output_zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zout:
    for fpath in Path(output_dir).glob("*"):
        zout.write(fpath, fpath.name)

print(f"Output ZIP written to {output_zip_path}")