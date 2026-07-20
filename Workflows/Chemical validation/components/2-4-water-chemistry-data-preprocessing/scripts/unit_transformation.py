# -*- coding: utf-8 -*-
# ------------------------------------------------------------
# WATER CHEMISTRY UNIT TRANSFORMATION
# ------------------------------------------------------------
# This script converts water chemistry measurements to a
# standardised set of three units for each analyte:
#   - mg/l   (mass concentration)
#   - µg/l   (mass concentration, micro scale)
#   - µeq/l  (equivalent concentration, charge-based)
#
# The script is designed to be unit-agnostic: it detects the
# unit from the column name (e.g. "NH4N(µg/l)") and converts
# accordingly, regardless of which unit the input data uses.
# This makes the component reusable with any CSV dataset that
# follows the "{ANALYTE}({unit})" column naming convention.
#
# Supported input units: mg/l, µg/l, ug/l, µeq/l, ueq/l
#
# Special paired conversions handled:
#   NH4  <-> NH4N   (ammonium / ammonium-nitrogen)
#   NO3  <-> NO3N   (nitrate  / nitrate-nitrogen)
#   SO4  <-> SO4S   (sulphate / sulphate-sulphur)
#   PO4  <-> PO4P   (phosphate / phosphate-phosphorus)
#
# Input:  ZIP archive containing tab-separated CSV files
#         (one per SiteCode per subprogram), as produced by
#         the LoqApplication wrapper.
# Output: ZIP archive with the same CSVs after unit expansion.
# ------------------------------------------------------------

# ============================================================
# IMPORTS
# ============================================================
import os
import re
import zipfile
import argparse
import pandas as pd
from pathlib import Path

# ------------------------------------------------------------
# CLI argument parsing (Tesseract wrapper convention)
# No user parameters: the transformation is fully deterministic
# from the column names and the chemical constants below.
# ------------------------------------------------------------
parser = argparse.ArgumentParser(description="Water Chemistry Unit Transformation wrapper")
args = parser.parse_args()

# ------------------------------------------------------------
# Paths — Tesseract mounts inputs at /mnt/inputs, outputs at /mnt/outputs
# ------------------------------------------------------------
input_zip_path = os.environ.get(
    "INPUT_ZIP_PATH", "/mnt/inputs/water_chemical_data_level1_loq.zip"
)
output_dir = os.environ.get("OUTPUT_DIR", "/mnt/outputs/level1_units")
output_zip_path = os.environ.get(
    "OUTPUT_ZIP_PATH", "/mnt/outputs/water_chemical_data_level1_units.zip"
)
os.makedirs(output_dir, exist_ok=True)

# Extract input ZIP to a temporary working directory
extract_dir = os.environ.get("EXTRACT_DIR", "/tmp/input/level1_loq")
os.makedirs(extract_dir, exist_ok=True)
with zipfile.ZipFile(input_zip_path, "r") as z:
    z.extractall(extract_dir)
print(f"Input ZIP extracted to {extract_dir}")

# ============================================================
# CHEMICAL CONSTANTS
# ============================================================

# Atomic weights (g/mol)
ATOMIC_WEIGHTS = {
    'H':  1,
    'C':  12,
    'N':  14,
    'O':  16,
    'S':  32.065,
    'P':  30.974,
    'Na': 22.99,
    'K':  39.1,
    'Mg': 24.31,
    'Ca': 40.08,
    'Fe': 55.8,
    'Mn': 54.938,
    'Al': 26.982,
    'Zn': 65.38,
    'As': 74.992,
    'Cd': 112.41,
    'Cr': 51.996,
    'Cu': 63.546,
    'Co': 58.933,
    'Ni': 58.693,
    'Pb': 207.2,
    'Cl': 35.45
}

# Molecules: molecular weight (PM) and ionic charge (carga)
MOLECULES = {
    'NH4(mg/l)': {'PM': 18,      'carga': 1},
    'NO3(mg/l)': {'PM': 61.997,  'carga': 1},
    'SO4(mg/l)': {'PM': 95.996,  'carga': 2},
    'PO4(mg/l)': {'PM': 94.974,  'carga': 3},
    'DOC(mg/l)': {'PA': 12,      'val':   4},
}

# Elements and ions: atomic weight (PA) and valence (val)
# Na and K appear as both ions and elements with identical properties;
# the elements dictionary takes precedence (same values, no impact).
ELEMENTS = {
    'AS(mg/l)':  {'PA': 74.992,  'val': 5},
    'CD(mg/l)':  {'PA': 112.41,  'val': 2},
    'CR(mg/l)':  {'PA': 51.996,  'val': 6},
    'CU(mg/l)':  {'PA': 63.546,  'val': 2},
    'CO(mg/l)':  {'PA': 58.933,  'val': 6},
    'NI(mg/l)':  {'PA': 58.693,  'val': 2},
    'PB(mg/l)':  {'PA': 207.20,  'val': 2},
    'ZN(mg/l)':  {'PA': 65.380,  'val': 2},
    'P(mg/l)':   {'PA': 30.974,  'val': 3},
    'S(mg/l)':   {'PA': 32.065,  'val': 2},
    'CA(mg/l)':  {'PA': 40.08,   'val': 2},
    'MG(mg/l)':  {'PA': 24.31,   'val': 2},
    'NA(mg/l)':  {'PA': 22.99,   'val': 1},
    'K(mg/l)':   {'PA': 39.1,    'val': 1},
    'AL(mg/l)':  {'PA': 26.982,  'val': 3},
    'FE(mg/l)':  {'PA': 55.8,    'val': 2},
    'MN(mg/l)':  {'PA': 54.938,  'val': 1},
    'CL(mg/l)':  {'PA': 35.45,   'val': 1},
}

# ============================================================
# HELPER FUNCTIONS
# ============================================================

def normalise_unit(unit):
    """
    Normalises unit string variants to a canonical lowercase form:
      ug/l  -> µg/l
      μg/l  -> µg/l   (Greek mu vs micro sign)
      ueq/l -> µeq/l
      μeq/l -> µeq/l
    """
    unit = str(unit).lower().strip()
    unit = unit.replace("μ", "µ")   # Greek mu (U+03BC) -> micro sign (U+00B5)
    unit = unit.replace("ug/l",  "µg/l")
    unit = unit.replace("ueq/l", "µeq/l")
    return unit


def parse_column(col):
    """
    Extracts analyte name and unit from a column header.
    Expects format: "{ANALYTE}({unit})"  e.g. "NH4N(µg/l)"

    Returns (analyte, normalised_unit) or (None, None) if not matched.
    """
    match = re.match(r"^(.+?)\((.+?)\)$", str(col).strip())
    if not match:
        return None, None
    analyte = match.group(1).strip()
    unit    = normalise_unit(match.group(2).strip())
    return analyte, unit


def to_mg_l(series, unit, weight, valence):
    """
    Converts a pandas Series to mg/l from the given input unit.

    Conversions:
      mg/l  -> mg/l  (no-op)
      µg/l  -> mg/l  (divide by 1000)
      µeq/l -> mg/l  (µeq/l * equivalent_weight / 1000)
               where equivalent_weight = molecular_weight / valence
    """
    unit = normalise_unit(unit)
    if unit == "mg/l":
        return series
    if unit == "µg/l":
        return series / 1000
    if unit == "µeq/l":
        return series * weight / valence / 1000
    return None


def generate_three_units(df, analyte, mg_l_values, weight, valence, overwrite=False):
    """
    Adds (or updates) the three standard unit columns for an analyte:
      {analyte}(mg/l)
      {analyte}(µg/l)
      {analyte}(µeq/l)

    If overwrite=False, existing columns are preserved.
    If overwrite=True,  existing columns are recalculated.
    """
    col_mg  = f"{analyte}(mg/l)"
    col_ug  = f"{analyte}(µg/l)"
    col_ueq = f"{analyte}(µeq/l)"

    if overwrite or col_mg  not in df.columns:
        df[col_mg]  = mg_l_values
    if overwrite or col_ug  not in df.columns:
        df[col_ug]  = mg_l_values * 1000
    if overwrite or col_ueq not in df.columns:
        df[col_ueq] = mg_l_values * valence / weight * 1000

    return df


def build_analyte_dict():
    """
    Builds a unified lookup dictionary from ELEMENTS and MOLECULES.
    Keys are uppercase analyte names for case-insensitive matching.
    """
    analytes = {}

    for name, props in ELEMENTS.items():
        analyte, _ = parse_column(name)
        if analyte and "PA" in props and "val" in props:
            analytes[analyte.upper()] = {
                "analyte": analyte,
                "weight":  props["PA"],
                "valence": props["val"]
            }

    for name, props in MOLECULES.items():
        analyte, _ = parse_column(name)
        if analyte and "PM" in props and "carga" in props:
            analytes[analyte.upper()] = {
                "analyte": analyte,
                "weight":  props["PM"],
                "valence": props["carga"]
            }
        elif analyte and "PA" in props and "val" in props:
            analytes[analyte.upper()] = {
                "analyte": analyte,
                "weight":  props["PA"],
                "valence": props["val"]
            }

    return analytes


# ============================================================
# MAIN TRANSFORMATION FUNCTION
# ============================================================

def transform_dataframe(df):
    """
    Applies unit transformations to all relevant columns in a DataFrame.

    Steps:
      1. Direct conversions for all known ions, elements and simple molecules.
      2. NH4  <-> NH4N  cross-conversion.
      3. NO3  <-> NO3N  cross-conversion.
      4. SO4  <-> SO4S  cross-conversion.
      5. PO4  <-> PO4P  cross-conversion.

    Each step generates the three standard unit columns (mg/l, µg/l, µeq/l)
    for both the molecule and its elemental counterpart where applicable.
    """
    analytes = build_analyte_dict()

    # ----------------------------------------------------------
    # 1. Direct conversions for ions, elements and molecules
    # ----------------------------------------------------------
    for col in list(df.columns):
        analyte, unit = parse_column(col)
        if analyte is None or unit is None:
            continue

        key = analyte.upper()
        if key not in analytes:
            continue

        props  = analytes[key]
        mg_l   = to_mg_l(df[col], unit, props["weight"], props["valence"])
        if mg_l is not None:
            df = generate_three_units(df, props["analyte"], mg_l,
                                      props["weight"], props["valence"])

    # ----------------------------------------------------------
    # 2. NH4 <-> NH4N  (ammonium / ammonium-nitrogen)
    # ----------------------------------------------------------
    PM_NH4   = MOLECULES["NH4(mg/l)"]["PM"]
    charge   = MOLECULES["NH4(mg/l)"]["carga"]
    MA_N     = ATOMIC_WEIGHTS["N"]

    for col in list(df.columns):
        analyte, unit = parse_column(col)
        if analyte is None:
            continue
        key = analyte.upper()

        if key == "NH4N":
            mg_l_nh4n = to_mg_l(df[col], unit, MA_N, charge)
            if mg_l_nh4n is not None:
                df = generate_three_units(df, "NH4N", mg_l_nh4n, MA_N, charge)
                df = generate_three_units(df, "NH4",  mg_l_nh4n * PM_NH4 / MA_N, PM_NH4, charge)

        if key == "NH4":
            mg_l_nh4 = to_mg_l(df[col], unit, PM_NH4, charge)
            if mg_l_nh4 is not None:
                df = generate_three_units(df, "NH4N", mg_l_nh4 * MA_N / PM_NH4, MA_N, charge)

    # ----------------------------------------------------------
    # 3. NO3 <-> NO3N  (nitrate / nitrate-nitrogen)
    # ----------------------------------------------------------
    PM_NO3 = MOLECULES["NO3(mg/l)"]["PM"]
    charge = MOLECULES["NO3(mg/l)"]["carga"]

    for col in list(df.columns):
        analyte, unit = parse_column(col)
        if analyte is None:
            continue
        key = analyte.upper()

        if key == "NO3":
            mg_l_no3 = to_mg_l(df[col], unit, PM_NO3, charge)
            if mg_l_no3 is not None:
                df = generate_three_units(df, "NO3N", mg_l_no3 * MA_N / PM_NO3, MA_N, charge)

        if key == "NO3N":
            mg_l_no3n = to_mg_l(df[col], unit, MA_N, charge)
            if mg_l_no3n is not None:
                df = generate_three_units(df, "NO3N", mg_l_no3n, MA_N, charge)
                df = generate_three_units(df, "NO3",  mg_l_no3n * PM_NO3 / MA_N, PM_NO3, charge)

    # ----------------------------------------------------------
    # 4. SO4 <-> SO4S  (sulphate / sulphate-sulphur)
    # ----------------------------------------------------------
    PM_SO4 = MOLECULES["SO4(mg/l)"]["PM"]
    charge = MOLECULES["SO4(mg/l)"]["carga"]
    MA_S   = ATOMIC_WEIGHTS["S"]

    for col in list(df.columns):
        analyte, unit = parse_column(col)
        if analyte is None:
            continue
        key = analyte.upper()

        if key == "SO4":
            mg_l_so4 = to_mg_l(df[col], unit, PM_SO4, charge)
            if mg_l_so4 is not None:
                df = generate_three_units(df, "SO4S", mg_l_so4 * MA_S / PM_SO4, MA_S, charge)

        if key == "SO4S":
            mg_l_so4s = to_mg_l(df[col], unit, MA_S, charge)
            if mg_l_so4s is not None:
                df = generate_three_units(df, "SO4S", mg_l_so4s, MA_S, charge)
                df = generate_three_units(df, "SO4",  mg_l_so4s * PM_SO4 / MA_S, PM_SO4, charge)

    # ----------------------------------------------------------
    # 5. PO4 <-> PO4P  (phosphate / phosphate-phosphorus)
    # ----------------------------------------------------------
    PM_PO4 = MOLECULES["PO4(mg/l)"]["PM"]
    charge = MOLECULES["PO4(mg/l)"]["carga"]
    MA_P   = ATOMIC_WEIGHTS["P"]

    for col in list(df.columns):
        analyte, unit = parse_column(col)
        if analyte is None:
            continue
        key = analyte.upper()

        if key == "PO4":
            mg_l_po4 = to_mg_l(df[col], unit, PM_PO4, charge)
            if mg_l_po4 is not None:
                df = generate_three_units(df, "PO4P", mg_l_po4 * MA_P / PM_PO4, MA_P, charge)

        if key == "PO4P":
            mg_l_po4p = to_mg_l(df[col], unit, MA_P, charge)
            if mg_l_po4p is not None:
                df = generate_three_units(df, "PO4P", mg_l_po4p, MA_P, charge)
                df = generate_three_units(df, "PO4",  mg_l_po4p * PM_PO4 / MA_P, PM_PO4, charge)

    return df


# ============================================================
# PROCESS ALL CSV FILES
# ============================================================

for archivo in sorted(os.listdir(extract_dir)):
    if not archivo.endswith(".csv"):
        continue

    input_path  = os.path.join(extract_dir, archivo)
    output_path = os.path.join(output_dir,  archivo)

    df = pd.read_csv(input_path, sep='\t')
    df = transform_dataframe(df)
    df.to_csv(output_path, index=False, sep='\t')

    print(f"Processed: {archivo}")

# ============================================================
# PACKAGE OUTPUT FILES INTO ZIP
# ============================================================
with zipfile.ZipFile(output_zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zout:
    for fpath in Path(output_dir).glob("*"):
        zout.write(fpath, fpath.name)

print(f"Output ZIP written to {output_zip_path}")