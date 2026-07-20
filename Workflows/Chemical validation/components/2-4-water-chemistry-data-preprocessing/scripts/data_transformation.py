# -*- coding: utf-8 -*-
# ------------------------------------------------------------
# WATER CHEMICAL DATA TRANSFORMATION
# ------------------------------------------------------------
# This script transforms validated Excel templates into
# analysis-ready CSV files, grouped by SiteCode.
#
# - ALKALINITY:          computes alkalinity via linear regression
# - pH_COND_WEIGHTED_RAW: computes weighted pH and conductivity
# - AMMONIUM, ANIONS, CATIONS, DOC_TN: consolidates and deduplicates
#
# Input:  ZIP archive containing validated .xlsx files (one 'data' sheet each)
# Output: one tab-separated CSV per SiteCode per subprogram + level1.zip
# ------------------------------------------------------------

# ============================================================
# IMPORTS
# ============================================================
import pandas as pd
import numpy as np
import zipfile
import os
from pathlib import Path
import argparse

# ------------------------------------------------------------
# CLI argument parsing (Tesseract wrapper convention)
# ------------------------------------------------------------
parser = argparse.ArgumentParser(description="Water Chemical Data Transformation wrapper")
args = parser.parse_args()

# ------------------------------------------------------------
# Paths — Tesseract mounts inputs at /mnt/inputs, outputs at /mnt/outputs
# ------------------------------------------------------------
input_zip_path = os.environ.get(
    "INPUT_ZIP_PATH", "/mnt/inputs/allData_templates_format_validated.zip"
)
output_dir = os.environ.get("OUTPUT_DIR", "/mnt/outputs/level1")
os.makedirs(output_dir, exist_ok=True)

# Extract input ZIP to a temporary working directory
extract_dir = os.environ.get("EXTRACT_DIR", "/tmp/output/level0")
os.makedirs(extract_dir, exist_ok=True)
with zipfile.ZipFile(input_zip_path, "r") as z:
    z.extractall(extract_dir)
print(f"Input ZIP extracted to {extract_dir}")

input_dir = Path(extract_dir)

# ============================================================
# TRANSFORMATION: ALKALINITY
# ============================================================
# Alkalinity is computed via linear regression using 4 reference
# pH points per sample. The x-axis intercept of the regression
# line is used to derive the alkalinity value in µeq/l.
# ============================================================

REFERENCE_PH_POINTS = [4, 4.2, 4.3, 4.5]

archivos = [f for f in input_dir.rglob("*") if f.is_file() and "ALKALINITY" in f.name.upper()]

if archivos:
    archivos_df = pd.DataFrame({'Files': archivos})
    archivos_df['FileName'] = archivos_df['Files'].apply(lambda x: x.name)
    archivos_df = archivos_df.sort_values(by="FileName").reset_index(drop=True)

    # Read all ALKALINITY files into a single DataFrame
    all_raw = []
    for _, row in archivos_df.iterrows():
        df = pd.read_excel(row['Files'], sheet_name='data')
        df.replace(['n.a', 'n.a.'], np.nan, inplace=True)
        df['SiteCode'] = df['SiteCode'].astype(str)  # ensure string for safe comparisons
        df['_source_file'] = row['Files']
        # Append _REP suffix to SampleID if the source file is a replicate
        df['SampleID'] = df['SampleID'].astype(str) + '_REP' if '_REP' in row['FileName'].upper() else df['SampleID']
        all_raw.append(df)

    all_raw = pd.concat(all_raw, ignore_index=True)

    # Iterate over unique SiteCodes found in the data (not in the filename)
    unique_codes = all_raw['SiteCode'].dropna().unique()

    for codigo in unique_codes:
        datosAnalisis = pd.DataFrame()

        # Filter data for the current SiteCode and drop rows with no usable values
        subset_code = all_raw[all_raw['SiteCode'].str.lower() == str(codigo).lower()].copy()
        subset_code = subset_code.dropna(subset=['HCLVolume(ml)', 'pH'], how='all')

        years  = subset_code['year'].dropna().unique()
        months = subset_code['month'].dropna().unique()

        for year in years:
            for month in months:
                # Filter for the current year/month combination
                subset = subset_code[
                    (subset_code['year'] == year) &
                    (subset_code['month'] == month)
                ].reset_index(drop=True)

                if subset.empty:
                    continue

                # Build the monthly output DataFrame
                datosMensuales = pd.DataFrame()
                datosMensuales['SampleID'] = subset['SampleID'].unique().tolist()
                datosMensuales['SiteCode'] = subset['SiteCode'].iloc[0]
                datosMensuales['SiteName'] = subset['SiteName'].iloc[0]
                datosMensuales['year']     = year
                datosMensuales['month']    = month

                # Select the 4 closest rows to each reference pH point per sample
                selectedRows = []
                for sample in datosMensuales['SampleID'].unique().tolist():
                    subsetPoints = subset[subset['SampleID'] == sample].copy()
                    for refNum in REFERENCE_PH_POINTS:
                        closestValue = subsetPoints.iloc[
                            (subsetPoints['pH'] - refNum).abs().argsort()[:1]
                        ]
                        selectedRows.append(closestValue)
                        subsetPoints = subsetPoints.drop(closestValue.index)

                subset = pd.concat(selectedRows)

                # Compute alkalinity for each sample via linear regression
                AlkalinityICPForest = []
                for sample in datosMensuales['SampleID'].unique().tolist():
                    subsetAlk = subset[subset['SampleID'] == sample]
                    xAxis    = subsetAlk[['HCLVolume(ml)']].values.flatten()
                    yAxisRaw = (
                        10**(-subsetAlk['pH']) *
                        (subsetAlk['HCLVolume(ml)'] + subsetAlk['SamplingVolume(ml)']) /
                        1000 * 10
                    )
                    yAxis = yAxisRaw.values.flatten()

                    pendiente, intercept = np.polyfit(xAxis, yAxis, 1)
                    x_intercept = intercept  # x-axis intercept used for alkalinity

                    AlkalinityICPForestVal = (
                        (((((-x_intercept / pendiente) / 1000)
                        * subsetAlk['HCL(mol/l)'].iloc[0])
                        / subsetAlk['SamplingVolume(ml)'].iloc[0]
                        / 1000 * 100) * 10) * 1000
                    ) * 1000000

                    AlkalinityICPForest.append(AlkalinityICPForestVal)

                # Replace negative alkalinity values with 0
                AlkalinityICPForest = [x if x >= 0 else 0 for x in AlkalinityICPForest]
                datosMensuales['AlkalinityICPForests(µeq/l)'] = AlkalinityICPForest

                datosAnalisis = pd.concat([datosAnalisis, datosMensuales]).reset_index(drop=True)

        if not datosAnalisis.empty:
            out_path = os.path.join(output_dir, f"{codigo}_WATER_ALKALINITY.csv")
            datosAnalisis.to_csv(out_path, sep="\t", index=False)
            print(f"Exported: {out_path}")

else:
    print("No ALKALINITY files found.")


# ============================================================
# TRANSFORMATION: pH WEIGHTED
# ============================================================
# For each sample, computes volume-weighted pH, conductivity,
# hydron concentration and precipitation. Temperature and
# dissolved oxygen are averaged across sub-samples.
# ============================================================

archivos = [f for f in input_dir.rglob("*") if f.is_file() and "PH_COND_WEIGHTED_RAW" in f.name.upper()]

if archivos:
    archivos_df = pd.DataFrame({'Files': archivos})
    archivos_df['FileName'] = archivos_df['Files'].apply(lambda x: x.name)
    archivos_df = archivos_df.sort_values(by="FileName").reset_index(drop=True)

    # Read all pH files into a single DataFrame
    all_raw = []
    for _, row in archivos_df.iterrows():
        df = pd.read_excel(row['Files'], sheet_name='data')
        df.replace(['n.a', 'n.a.'], np.nan, inplace=True)
        df = df.dropna(subset=['SiteCode'], how='all')  # drop rows with no SiteCode
        df['SiteCode'] = df['SiteCode'].astype(str)
        df['SampleID'] = df['SampleID'].astype(str) + '_REP' if '_REP' in row['FileName'].upper() else df['SampleID']
        all_raw.append(df)

    all_raw = pd.concat(all_raw, ignore_index=True)

    # Iterate over unique SiteCodes found in the data
    unique_codes = all_raw['SiteCode'].dropna().unique()

    for codigo in unique_codes:
        datosAnalisis = pd.DataFrame()

        # Filter data for the current SiteCode
        subset_code = all_raw[all_raw['SiteCode'].str.lower() == str(codigo).lower()].copy()

        years  = subset_code['year'].dropna().unique()
        months = subset_code['month'].dropna().unique()

        for year in years:
            for month in months:
                # Filter for the current year/month combination
                subset = subset_code[
                    (subset_code['year'] == year) &
                    (subset_code['month'] == month)
                ].reset_index(drop=True)

                if subset.empty:
                    continue

                # Build the monthly output DataFrame
                datosMensuales = pd.DataFrame()
                datosMensuales['SampleID']  = subset['SampleID'].unique().tolist()
                datosMensuales['SiteCode']  = subset['SiteCode'].iloc[0]
                datosMensuales['SiteName']  = subset['SiteName'].iloc[0]
                datosMensuales['StartDate'] = subset['StartDate'].iloc[0]
                datosMensuales['EndDate']   = subset['EndDate'].iloc[0]
                datosMensuales['year']      = year
                datosMensuales['month']     = month

                for sample in datosMensuales['SampleID']:

                    # Average temperature and dissolved oxygen across sub-samples
                    for col in ['Temperature(ºC)', 'DO(%)', 'DO(ppm)']:
                        valores = subset.loc[subset['SampleID'] == sample, col].values
                        datosMensuales.loc[datosMensuales['SampleID'] == sample, col] = np.nanmean(valores)

                    # Total collected volume (sum of sub-samples)
                    valores = subset.loc[subset['SampleID'] == sample, 'VolumeCollector(ml)'].values
                    datosMensuales.loc[datosMensuales['SampleID'] == sample, 'Volume(ml)'] = (
                        np.nansum(valores) if not np.isnan(valores).all() else np.nan
                    )

                    # Precipitation: volume / (n_samples * collector_area)
                    radius = subset.loc[subset['SampleID'] == sample, 'sampler_radius'].mean()
                    if 'Precip(l/m2)' not in datosMensuales.columns:
                        datosMensuales['Precip(l/m2)'] = np.nan
                    if pd.notna(radius):
                        num_valid = subset.loc[
                            (subset['SampleID'] == sample) &
                            (subset['VolumeCollector(ml)'].notna())
                        ].shape[0]
                        vol = datosMensuales.loc[datosMensuales['SampleID'] == sample, 'Volume(ml)'].values[0]
                        radius = subset.loc[
                            (subset['SampleID'] == sample) & (subset['sampler_radius'].notna())
                        ]['sampler_radius'].mean()
                        datosMensuales.loc[datosMensuales['SampleID'] == sample, 'Precip(l/m2)'] = (
                            (vol / 1000) / (num_valid * radius) if num_valid > 0 else np.nan
                        )

                    # Volume-weighted conductivity
                    dfP = subset.loc[subset['SampleID'] == sample].dropna(
                        subset=['VolumeCollector(ml)', 'Conductivity(µS/cm)']
                    )
                    suma = np.nansum(dfP['VolumeCollector(ml)'] * dfP['Conductivity(µS/cm)'])
                    peso = np.nansum(dfP['VolumeCollector(ml)'])
                    datosMensuales.loc[datosMensuales['SampleID'] == sample, 'WeightedConductivity(µS/cm)'] = (
                        suma / peso if peso > 0 else None
                    )

                    # Volume-weighted hydron concentration → weighted pH
                    dfP = subset.loc[subset['SampleID'] == sample].dropna(subset=['pH'], how='all')
                    suma   = np.nansum(dfP['VolumeCollector(ml)'] * (10 ** dfP['pH']))
                    peso   = np.nansum(dfP['VolumeCollector(ml)'])
                    hydron = suma / peso if peso > 0 else None
                    datosMensuales.loc[datosMensuales['SampleID'] == sample, 'WeightedHydron(µeq/l)'] = hydron
                    datosMensuales.loc[datosMensuales['SampleID'] == sample, 'WeightedpH'] = (
                        np.log10(hydron) if hydron and hydron > 0 else np.nan
                    )

                    # Keep first comment for the sample
                    comentarios = subset.loc[subset['SampleID'] == sample, 'Comments'].values
                    datosMensuales.loc[datosMensuales['SampleID'] == sample, 'Comments'] = (
                        comentarios[0] if len(comentarios) > 0 else ""
                    )

                # Append monthly results and remove duplicates
                datosAnalisis = pd.concat([datosAnalisis, datosMensuales], ignore_index=True)
                datosAnalisis = datosAnalisis.drop_duplicates(
                    subset=['SiteCode', 'SampleID', 'EndDate', 'month'], keep='first'
                )

        # Compute final H+ concentration from weighted pH
        datosAnalisis['H(µeq/l)'] = np.where(
            datosAnalisis['WeightedpH'] == 0.0,
            0.0,
            10**(-(datosAnalisis['WeightedpH'])) * 10**6
        )

        out_path = os.path.join(output_dir, f"{codigo}_WATER_pH_COND_WEIGHTED_RAW.csv")
        datosAnalisis.to_csv(out_path, sep="\t", index=False)
        print(f"Exported: {out_path}")

else:
    print("No pH_COND_WEIGHTED_RAW files found.")


# ============================================================
# TRANSFORMATION: REMAINING SUBPROGRAMS
# ============================================================
# AMMONIUM, ANIONS, CATIONS and DOC_TN files only require
# consolidation across months and deduplication by sample.
# ============================================================

SUBPROGRAMS = ['AMMONIUM', 'ANIONS', 'CATIONS', 'DOC_TN']
all_files = [f for f in input_dir.rglob("*") if f.is_file()]

for subprogram in SUBPROGRAMS:

    archivos_sub = [f for f in all_files if subprogram in f.name.upper()]

    if not archivos_sub:
        print(f"No files found for subprogram: {subprogram}")
        continue

    # Read all files for this subprogram into a single DataFrame
    all_raw = []
    for f in sorted(archivos_sub, key=lambda x: x.name):
        df = pd.read_excel(f, sheet_name='data')
        df.replace(['n.a', 'n.a.'], np.nan, inplace=True)
        df['SiteCode'] = df['SiteCode'].astype(str)
        df['SampleID'] = df['SampleID'].astype(str) + '_REP' if '_REP' in f.name.upper() else df['SampleID']
        all_raw.append(df)

    all_raw = pd.concat(all_raw, ignore_index=True)

    # Iterate over unique SiteCodes found in the data
    unique_codes = all_raw['SiteCode'].dropna().unique()

    for codigo in unique_codes:
        # Filter by SiteCode and deduplicate by sample identity
        datosAnalisis = all_raw[
            all_raw['SiteCode'].str.lower() == str(codigo).lower()
        ].drop_duplicates(
            subset=['SampleID', 'SiteCode', 'SiteName', 'EndDate'], keep='first'
        ).reset_index(drop=True)

        if not datosAnalisis.empty:
            out_path = os.path.join(output_dir, f"{codigo}_WATER_{subprogram}.csv")
            datosAnalisis.to_csv(out_path, sep="\t", index=False)
            print(f"Exported: {out_path}")

# ============================================================
# PACKAGE OUTPUT FILES INTO ZIP
# ============================================================
output_zip_path = os.environ.get("OUTPUT_ZIP_PATH", "/mnt/outputs/water_chemical_data_level1.zip")
with zipfile.ZipFile(output_zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zout:
    for fpath in Path(output_dir).glob("*"):
        zout.write(fpath, fpath.name)

print(f"Output ZIP written to {output_zip_path}")