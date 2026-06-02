# ------------------------------------------------------------
# DATA FORMAT VALIDATION
# ------------------------------------------------------------
# This script validates multiple Excel files contained in a ZIP
# according to a configuration file (JSON) that defines:
# - required columns
# - optional columns
# - expected data types
# - allowed ranges
# - validation regex
# Finally, it generates a TXT file with errors and warnings.
# ------------------------------------------------------------

import pandas as pd
import numpy as np
import glob
import os
from datetime import datetime
import sys
import re
import zipfile
import json
from pathlib import Path
import argparse
import openpyxl

# ------------------------------------------------------------
# CLI argument parsing (Tesseract wrapper convention)
# ------------------------------------------------------------
parser = argparse.ArgumentParser(description="Data Format Validation wrapper")
parser.add_argument(
    "--stopOnErrors",
    default="TRUE",
    help="Exit with code 1 if critical errors are found (TRUE/FALSE)",
)
args = parser.parse_args()

stop_on_errors = args.stopOnErrors.strip().upper() == "TRUE"

# ------------------------------------------------------------
# Paths — Tesseract mounts inputs at /mnt/inputs, outputs at /mnt/outputs
# ------------------------------------------------------------
input_zip_path    = "/mnt/inputs/allData.zip"
input_config_path = "/mnt/inputs/tables_config.txt"
output_log_path   = "/mnt/outputs/level0/validation_log.txt"
output_zip_path   = "/mnt/outputs/level0/allData_templates_format_validated.zip"
extract_dir       = "/mnt/outputs/templates"

# ------------------------------------------------------------
# Dependency version check
# ------------------------------------------------------------
print(f"openpyxl version: {openpyxl.__version__}")

# ------------------------------------------------------------
# Guard: required input files must exist
# ------------------------------------------------------------
for p in (input_zip_path, input_config_path):
    if not os.path.exists(p):
        raise RuntimeError(f"Required input file not found: {p}")

# ------------------------------------------------------------
# 1. EXTRACT ZIP
# ------------------------------------------------------------
os.makedirs(extract_dir, exist_ok=True)
with zipfile.ZipFile(input_zip_path, "r") as zip_ref:
    zip_ref.extractall(extract_dir)
print(f"ZIP extracted to {extract_dir}")

# ------------------------------------------------------------
# 2. LOAD CONFIGURATION FILE
# ------------------------------------------------------------
with open(input_config_path, "r", encoding="utf-8") as f:
    tables_config = json.load(f)

# ------------------------------------------------------------
# 3. NORMALIZE CONFIGURATION
# ------------------------------------------------------------
def normalize_config(tables_config, extract_dir):
    for cfg in tables_config:
        # Schema: convert type strings to Python types
        for col, val in cfg["schema"].items():
            if isinstance(val, str):
                if val == "float":
                    cfg["schema"][col] = float
                elif val == "object":
                    cfg["schema"][col] = object
            # datetime dicts are left as-is; handled during validation
        # Ranges: lists → tuples
        for col, val in cfg.get("expected_ranges", {}).items():
            if isinstance(val, list):
                cfg["expected_ranges"][col] = tuple(val)
        # Formats: strings → compiled regex
        for col, val in cfg.get("formats", {}).items():
            if isinstance(val, str):
                cfg["formats"][col] = re.compile(val)
        # Paths: make absolute relative to extract_dir
        cfg["path"] = str(Path(extract_dir) / cfg["path"])

normalize_config(tables_config, extract_dir)
print("Configuration normalised correctly.")

# ------------------------------------------------------------
# 4. FILE VALIDATION
# ------------------------------------------------------------
all_errors   = []   # list of (fpath, [error strings])
all_warnings = []   # list of (fpath, [warning strings])

for cfg in tables_config:
    files = glob.glob(cfg["path"])
    print(f"Files matching '{cfg['path']}': {files}")

    for fpath in files:
        errors   = []
        warnings_ = []

        df = pd.read_excel(fpath, sheet_name="data", dtype=object, engine="openpyxl")
        df.replace(["n.a", "n.a."], np.nan, inplace=True)
        schema = cfg["schema"]

        # Required columns
        for col in schema.keys():
            if col not in df.columns:
                errors.append(f"Critical: Missing column '{col}'")

        # Critical columns — must not be empty
        for col in cfg.get("critical_columns", []):
            if col in df.columns:
                if df[col].isnull().all():
                    errors.append(f"Critical: Column '{col}' is completely empty")
                elif df[col].isnull().any():
                    errors.append(f"Critical: Column '{col}' has empty values")

        # Optional columns — warn if empty
        for col in cfg.get("optional_columns", []):
            if col in df.columns:
                if df[col].isnull().all():
                    warnings_.append(f"Optional column '{col}' is completely empty")
                elif df[col].isnull().any():
                    warnings_.append(f"Optional column '{col}' has some empty values")

        # Type / format validation
        for col, expected in schema.items():
            if col not in df.columns:
                continue
            series = df[col].dropna()
            if series.empty:
                continue

            expected_type = expected if isinstance(expected, type) else expected.get("type", object)

            if expected_type == "datetime":
                fmt = expected.get("format") if isinstance(expected, dict) else None
                conv = pd.to_datetime(series, format=fmt, errors="coerce")
                for idx in conv[conv.isna()].index:
                    errors.append(
                        f"Critical: Column '{col}' has invalid datetime '{df.at[idx, col]}' (row {idx+2})"
                    )
            elif expected_type == float:
                numeric = pd.to_numeric(series, errors="coerce")
                for idx in numeric[numeric.isna()].index:
                    errors.append(
                        f"Critical: Column '{col}' contains non-numeric value '{df.at[idx, col]}' (row {idx+2})"
                    )
            # object: no strict validation

        # Negative values
        for col in cfg.get("no_negatives", []):
            if col in df.columns:
                neg = pd.to_numeric(df[col], errors="coerce")
                neg = neg[neg < 0].dropna()
                if len(neg) > 0:
                    errors.append(f"Critical: Column '{col}' has {len(neg)} negative value(s)")

        # Expected ranges
        for col, (min_val, max_val) in cfg.get("expected_ranges", {}).items():
            if col in df.columns:
                series = pd.to_numeric(df[col], errors="coerce")
                out = series[(series < min_val) | (series > max_val)].dropna()
                if len(out) > 0:
                    warnings_.append(
                        f"Column '{col}' has {len(out)} value(s) outside expected range [{min_val}, {max_val}]"
                    )

        # Regex formats
        for col, regex in cfg.get("formats", {}).items():
            if col in df.columns:
                col_series = df[col].dropna().astype(str)
                invalid = col_series[~col_series.str.match(regex)]
                if not invalid.empty:
                    errors.append(f"Critical: Column '{col}' has {len(invalid)} value(s) that fail regex validation")

        if errors or warnings_:
            all_errors.append((fpath, errors))
            all_warnings.append((fpath, warnings_))

print("Validation completed.")

# ------------------------------------------------------------
# 5. WRITE VALIDATION LOG
# ------------------------------------------------------------
os.makedirs(os.path.dirname(output_log_path), exist_ok=True)

with open(output_log_path, "w", encoding="utf-8") as f:
    f.write(f"TABLE VALIDATION — {datetime.now()}\n")
    f.write("=" * 60 + "\n\n")

    all_files = [fp for cfg in tables_config for fp in glob.glob(cfg["path"])]

    for file in all_files:
        errs  = next((e for path, e in all_errors   if path == file), [])
        warns = next((w for path, w in all_warnings if path == file), [])
        f.write(f"File: {file}\n")
        if not errs and not warns:
            f.write("✅ No issues found. Template is valid.\n")
        else:
            for e in errs:
                f.write(f"❌ {e}\n")
            for w in warns:
                f.write(f"⚠️  {w}\n")
        f.write("-" * 60 + "\n")

print(f"Validation log written to {output_log_path}")

# ------------------------------------------------------------
# 6. BUILD VALIDATED OUTPUT ZIP
# Re-pack the extracted Excel files with "validated_" prefix
# added to every filename, preserving folder structure.
# ------------------------------------------------------------
os.makedirs(os.path.dirname(output_zip_path), exist_ok=True)

with zipfile.ZipFile(output_zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zout:
    for root, _, files in os.walk(extract_dir):
        for fname in files:
            full_path = os.path.join(root, fname)
            rel_path  = os.path.relpath(full_path, extract_dir)
            parts     = list(Path(rel_path).parts)
            parts[-1] = "validated_" + parts[-1]
            arc_name  = str(Path(*parts))
            zout.write(full_path, arc_name)

print(f"Validated ZIP written to {output_zip_path}")

# ------------------------------------------------------------
# 7. EXIT WITH ERROR CODE IF CRITICAL ERRORS FOUND
# ------------------------------------------------------------
has_critical = any(len(errs) > 0 for _, errs in all_errors)
if has_critical:
    print("\u26a0\ufe0f  Critical errors found. Check validation_log.txt for details.")
    if stop_on_errors:
        sys.exit(1)

print("\u2705 Validation finished successfully.")