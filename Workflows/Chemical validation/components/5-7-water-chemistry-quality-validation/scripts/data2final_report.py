# -*- coding: utf-8 -*-
"""Select final monthly water-chemistry records and prepare database fields.

Selection logic per base SampleID/year/month is preserved:
  1. Keep NOREP when it passes validation.
  2. Otherwise keep REP when it passes.
  3. If both NOREP and REP fail, keep NOREP when a REP exists.
  4. If NOREP fails and no REP exists, discard it.

Selected records with the same site, sampling typology, instrument, programme,
derived subprogram, year and month are combined using the existing volume-weighted
aggregation rules. The subprogram is inferred from SamplingTypology before
additional database-oriented fields are derived. Final_Data retains one canonical
representation for dates (StartDate/EndDate), precipitation (Precip(l/m2)) and
alkalinity (AlkalinityICPForests(µeq/l)); database-specific renaming is deferred
to the database-loading step.
"""

from __future__ import annotations

import argparse
import os
from pathlib import Path
from typing import Iterable

import numpy as np
import openpyxl
import pandas as pd

parser = argparse.ArgumentParser(description="Data to Final Report wrapper")
parser.parse_args()

print(f"openpyxl version: {openpyxl.__version__}")

input_data_path = os.environ.get(
    "INPUT_DATA_PATH", "/mnt/inputs/All_Validated_Data.xlsx"
)
input_samples_path = os.environ.get(
    "INPUT_SAMPLES_PATH", "/mnt/inputs/samplesInfo.xlsx"
)
output_path = os.environ.get("OUTPUT_PATH", "/mnt/outputs/Final_Data.xlsx")


def clean_sample_id(series: pd.Series) -> pd.Series:
    """Normalise SampleID: uppercase and remove spaces/separators."""
    return (
        series.astype(str)
        .str.upper()
        .str.strip()
        .str.replace(r"[ \-_]", "", regex=True)
    )


def is_empty(value) -> bool:
    if pd.isna(value):
        return True
    return str(value).strip().lower() in ("", "nan", "none", "nat")


def first_non_empty(values: Iterable) -> str:
    for value in values:
        if not is_empty(value):
            return str(value).strip()
    return ""


def remove_all_spaces(value) -> str:
    if is_empty(value):
        return ""
    return "".join(str(value).strip().split())


def build_final_sample_id(site_code, sampling_typology, instrument) -> str:
    parts = [
        first_non_empty([site_code]),
        remove_all_spaces(sampling_typology),
    ]
    instrument = remove_all_spaces(instrument)
    if instrument:
        parts.append(instrument)
    return "_".join(part for part in parts if part)


def derive_subprogram(sampling_typology) -> str:
    """Derive the ICP subprogram code from SamplingTypology.

    Mapping requested for the workflow:
      * values containing THR -> TF
      * values containing BOF -> PC
      * values containing RW  -> RW
      * values containing SF  -> SF
      * values containing SW  -> SW

    An empty string is returned when no configured marker is present.
    """
    if is_empty(sampling_typology):
        return ""

    value = str(sampling_typology).strip().upper()
    mapping = (
        ("THR", "TF"),
        ("BOF", "PC"),
        ("RW", "RW"),
        ("SF", "SF"),
        ("SW", "SW"),
    )
    for marker, subprogram in mapping:
        if marker in value:
            return subprogram
    return ""


def weighted_mean_by_volume(
    group: pd.DataFrame,
    value_col: str,
    volume_col: str = "Volume(ml)",
):
    values = pd.to_numeric(group[value_col], errors="coerce")
    weights = pd.to_numeric(group[volume_col], errors="coerce")
    mask = values.notna() & weights.notna() & (weights > 0)
    if not mask.any():
        available = values.dropna()
        return available.iloc[0] if not available.empty else pd.NA
    denominator = weights[mask].sum()
    if denominator == 0:
        return pd.NA
    return (values[mask] * weights[mask]).sum() / denominator


def weighted_ph_by_volume(
    group: pd.DataFrame,
    ph_col: str = "WeightedpH",
    volume_col: str = "Volume(ml)",
):
    ph = pd.to_numeric(group[ph_col], errors="coerce")
    weights = pd.to_numeric(group[volume_col], errors="coerce")
    mask = ph.notna() & weights.notna() & (weights > 0)
    if not mask.any():
        available = ph.dropna()
        return available.iloc[0] if not available.empty else pd.NA
    denominator = weights[mask].sum()
    if denominator == 0:
        return pd.NA
    h_final = (np.power(10.0, -ph[mask]) * weights[mask]).sum() / denominator
    return -np.log10(h_final) if pd.notna(h_final) and h_final > 0 else pd.NA


def sum_numeric(group: pd.DataFrame, column: str):
    return pd.to_numeric(group[column], errors="coerce").sum(min_count=1)


def parse_dates(values: pd.Series) -> pd.Series:
    """Parse Excel dates plus the two formats used by the templates."""
    parsed_values = []
    for value in values:
        if pd.isna(value):
            parsed_values.append(pd.NaT)
            continue
        if isinstance(value, (pd.Timestamp, np.datetime64)):
            parsed_values.append(pd.to_datetime(value, errors="coerce"))
            continue
        parsed = pd.NaT
        for date_format in ("%Y-%m-%d", "%d/%m/%Y", "%Y-%m-%d %H:%M:%S"):
            parsed = pd.to_datetime(value, format=date_format, errors="coerce")
            if not pd.isna(parsed):
                break
        if pd.isna(parsed):
            parsed = pd.to_datetime(value, errors="coerce")
        parsed_values.append(parsed)
    return pd.Series(parsed_values, index=values.index)


def min_date(values: pd.Series):
    parsed = parse_dates(values).dropna()
    return parsed.min() if not parsed.empty else pd.NaT


def max_date(values: pd.Series):
    parsed = parse_dates(values).dropna()
    return parsed.max() if not parsed.empty else pd.NaT


def numeric_sum_preserve_na(*series: pd.Series) -> pd.Series:
    frame = pd.concat(
        [pd.to_numeric(s, errors="coerce") for s in series], axis=1
    )
    return frame.sum(axis=1, min_count=1)


def deposition(concentration: pd.Series, precipitation: pd.Series) -> pd.Series:
    """kg/ha = concentration (mg/L) × precipitation (mm=L/m²) × 0.01."""
    concentration = pd.to_numeric(concentration, errors="coerce")
    precipitation = pd.to_numeric(precipitation, errors="coerce")
    return concentration * precipitation * 0.01


df = pd.read_excel(input_data_path)
samples_info = pd.read_excel(input_samples_path)

print(f"Loaded {len(df)} rows from All_Validated_Data.xlsx")
print(f"Loaded {len(samples_info)} rows from samplesInfo.xlsx")

if "SampleID" not in df.columns or "SampleID" not in samples_info.columns:
    raise RuntimeError("Both inputs must contain a SampleID column")

for column in [
    "StartDate", "EndDate", "PO4P(mg/l)", "AS(mg/l)", "CD(mg/l)",
    "CR(mg/l)", "CU(mg/l)", "CO(mg/l)", "MO(mg/l)", "NI(mg/l)",
    "PB(mg/l)", "ZN(mg/l)", "P(mg/l)", "S(mg/l)", "NING(mg/l)",
    "NDON(mg/l)", "Temperature(ºC)", "Volume(ml)", "Precip(l/m2)",
]:
    if column not in df.columns:
        df[column] = pd.NA

samples_info = samples_info.copy()
samples_info["SampleID_clean"] = clean_sample_id(samples_info["SampleID"])


def first_existing_column(frame: pd.DataFrame, candidates: list[str]) -> str | None:
    lookup = {str(column).casefold(): column for column in frame.columns}
    for candidate in candidates:
        if candidate.casefold() in lookup:
            return lookup[candidate.casefold()]
    return None


metadata_sources = {
    "ICP_Program": ["ICP_Program", "program"],
    "SamplingTypology": ["SamplingTypology"],
    "Instrument": ["Instrument"],
    "ID_PostgreSQL": ["ID_PostgreSQL", "id_site"],
}

metadata = samples_info[["SampleID_clean"]].copy()
for canonical, candidates in metadata_sources.items():
    source = first_existing_column(samples_info, candidates)
    metadata[canonical] = samples_info[source] if source else pd.NA

metadata = metadata.drop_duplicates(subset=["SampleID_clean"], keep="first")

df["SampleID_clean"] = clean_sample_id(df["SampleID"])
df = df.merge(metadata, on="SampleID_clean", how="left", validate="many_to_one")
df["DerivedSubprogram"] = df["SamplingTypology"].map(derive_subprogram)

matched_metadata = df["SamplingTypology"].notna().sum()
print(
    f"Metadata matched for {matched_metadata}/{len(df)} rows "
    f"using normalised SampleID"
)
subprogram_counts = df["DerivedSubprogram"].replace("", pd.NA).value_counts(dropna=False)
print("Derived subprogram counts before selection:")
for code, count in subprogram_counts.items():
    label = "<unmapped>" if pd.isna(code) else str(code)
    print(f"  {label}: {count}")

df["is_rep"] = df["SampleID_clean"].str.contains(r"REP$", na=False)
df["base_id"] = df["SampleID_clean"].str.replace(r"REP$", "", regex=True)
df["VAL_bool"] = df["VAL"].astype(str).str.upper().str.strip().eq("SI")

selected_rows = []
for _, group in df.groupby(["base_id", "year", "month"], dropna=False):
    normal = group[~group["is_rep"]]
    repeat = group[group["is_rep"]]

    normal_ok = normal[normal["VAL_bool"]]
    if not normal_ok.empty:
        selected_rows.append(normal_ok.iloc[0])
        continue

    repeat_ok = repeat[repeat["VAL_bool"]]
    if not repeat_ok.empty:
        selected_rows.append(repeat_ok.iloc[0])
        continue

    if not normal.empty and not repeat.empty:
        selected_rows.append(normal.iloc[0])

print(f"Rows selected after filtering: {len(selected_rows)}")
selected = pd.DataFrame(selected_rows).reset_index(drop=True)

ANALYTICAL_COLUMNS = [
    "CL(mg/l)", "SO4S(mg/l)", "NO3N(mg/l)", "PO4P(mg/l)",
    "CA(mg/l)", "MG(mg/l)", "NA(mg/l)", "K(mg/l)",
    "AL(mg/l)", "FE(mg/l)", "MN(mg/l)",
    "AS(mg/l)", "CD(mg/l)", "CR(mg/l)", "CU(mg/l)", "CO(mg/l)",
    "MO(mg/l)", "NI(mg/l)", "PB(mg/l)", "ZN(mg/l)",
    "P(mg/l)", "S(mg/l)", "NH4N(mg/l)", "TN(mg/l)", "DOC(mg/l)",
    "NING(mg/l)", "NDON(mg/l)", "H(µeq/l)",
    "WeightedConductivity(µS/cm)", "Temperature(ºC)", "WeightedpH",
    "AlkalinityICPForests(µeq/l)",
]

for column in ANALYTICAL_COLUMNS:
    if column not in selected.columns:
        selected[column] = pd.NA

for column in [
    "SiteCode", "SiteName", "year", "month", "SamplingTypology",
    "Instrument", "ICP_Program", "DerivedSubprogram", "ID_PostgreSQL",
    "StartDate", "EndDate", "Temperature(ºC)", "Volume(ml)", "Precip(l/m2)",
]:
    if column not in selected.columns:
        selected[column] = pd.NA

GROUP_COLUMNS = [
    "SiteCode", "SiteName", "year", "month", "ICP_Program",
    "SamplingTypology", "Instrument", "DerivedSubprogram", "ID_PostgreSQL",
]

aggregated_rows: list[dict] = []
for _, group in selected.groupby(GROUP_COLUMNS, dropna=False, sort=False):
    row: dict = {
        "SiteCode": first_non_empty(group["SiteCode"]),
        "SiteName": first_non_empty(group["SiteName"]),
        "year": group.iloc[0]["year"],
        "month": group.iloc[0]["month"],
        "ICP_Program": first_non_empty(group["ICP_Program"]),
        "SamplingTypology": first_non_empty(group["SamplingTypology"]),
        "Instrument": first_non_empty(group["Instrument"]),
        "DerivedSubprogram": first_non_empty(group["DerivedSubprogram"]),
        "ID_PostgreSQL": first_non_empty(group["ID_PostgreSQL"]),
        "StartDate": min_date(group["StartDate"]),
        "EndDate": max_date(group["EndDate"]),
        "Volume(ml)": sum_numeric(group, "Volume(ml)"),
        "Precip(l/m2)": sum_numeric(group, "Precip(l/m2)"),
    }
    row["SampleID"] = build_final_sample_id(
        row["SiteCode"], row["SamplingTypology"], row["Instrument"]
    )

    for column in ANALYTICAL_COLUMNS:
        if column == "WeightedpH":
            row[column] = weighted_ph_by_volume(group, column)
        else:
            row[column] = weighted_mean_by_volume(group, column)

    aggregated_rows.append(row)

aggregated = pd.DataFrame(aggregated_rows)
print(
    f"Rows after sampling-unit/month aggregation: {len(aggregated)} "
    f"(from {len(selected)} selected rows)"
)

# Keep the output schema stable even when no sample survives selection.
required_derived_inputs = [
    "NH4N(mg/l)", "NO3N(mg/l)", "TN(mg/l)", "P(mg/l)",
    "PO4P(mg/l)", "S(mg/l)", "SO4S(mg/l)", "ICP_Program",
    "DerivedSubprogram", "SamplingTypology", "Instrument", "Volume(ml)",
    "Precip(l/m2)", "Temperature(ºC)", "StartDate", "EndDate",
] + ANALYTICAL_COLUMNS
for column in required_derived_inputs:
    if column not in aggregated.columns:
        aggregated[column] = pd.Series(dtype="object")

aggregated["NING(mg/l)"] = numeric_sum_preserve_na(
    aggregated["NH4N(mg/l)"], aggregated["NO3N(mg/l)"]
)
aggregated["NDON(mg/l)"] = (
    pd.to_numeric(aggregated["TN(mg/l)"], errors="coerce")
    - pd.to_numeric(aggregated["NING(mg/l)"], errors="coerce")
)

aggregated["PTOT (mg/l)"] = numeric_sum_preserve_na(
    aggregated["P(mg/l)"], aggregated["PO4P(mg/l)"]
)
aggregated["STOT (mg/l)"] = numeric_sum_preserve_na(
    aggregated["S(mg/l)"], aggregated["SO4S(mg/l)"]
)

aggregated["program"] = aggregated["ICP_Program"]
aggregated["subprogram"] = aggregated["DerivedSubprogram"]

is_soil_water = aggregated["SamplingTypology"].astype(str).str.contains(
    "SW", case=False, na=False
)
aggregated["lis_tip"] = aggregated["Instrument"].where(is_soil_water, pd.NA)

# VOL is the same collected-sample volume represented by Volume(ml).
# It is retained for every sample type whenever a volume is available.
aggregated["VOL (ml)"] = aggregated["Volume(ml)"]

# Temperature is reported in the database only for runoff-water (RW) rows.
subprogram_code = (
    aggregated["subprogram"].astype("string").str.strip().str.upper()
)
is_runoff_water = subprogram_code.eq("RW")
aggregated["TEMP (oC)"] = aggregated["Temperature(ºC)"].where(
    is_runoff_water, pd.NA
)

aggregated["NDON (mg/l)"] = aggregated["NDON(mg/l)"]
aggregated["NING (mg/l)"] = aggregated["NING(mg/l)"]

for column in ["q", "hg", "f", "cnr", "sio2", "ALL"]:
    aggregated[column] = pd.NA

deposition_sources = {
    "Deposition K (kg/ha)": "K(mg/l)",
    "Deposition Ca (kg/ha)": "CA(mg/l)",
    "Deposition Mg (kg/ha)": "MG(mg/l)",
    "Deposition Na (kg/ha)": "NA(mg/l)",
    "Deposition NH4N (kg/ha)": "NH4N(mg/l)",
    "Deposition Cl (kg/ha)": "CL(mg/l)",
    "Deposition NO3N (kg/ha)": "NO3N(mg/l)",
    "Deposition SO4S (kg/ha)": "SO4S(mg/l)",
    "Deposition NTOT (kg/ha)": "TN(mg/l)",
    "Deposition DOC (kg/ha)": "DOC(mg/l)",
    "Deposition Al (kg/ha)": "AL(mg/l)",
    "Deposition Mn (kg/ha)": "MN(mg/l)",
    "Deposition Fe (kg/ha)": "FE(mg/l)",
    "Deposition NDON (kg/ha)": "NDON (mg/l)",
    "Deposition NING (kg/ha)": "NING (mg/l)",
    "Deposition As (kg/ha)": "AS(mg/l)",
    "Deposition Cd (kg/ha)": "CD(mg/l)",
    "Deposition Cr (kg/ha)": "CR(mg/l)",
    "Deposition Cu (kg/ha)": "CU(mg/l)",
    "Deposition Mo (kg/ha)": "MO(mg/l)",
    "Deposition Ni (kg/ha)": "NI(mg/l)",
    "Deposition Pb (kg/ha)": "PB(mg/l)",
    "Deposition Zn (kg/ha)": "ZN(mg/l)",
    "Deposition PO4P (kg/ha)": "PO4P(mg/l)",
    "Deposition PTOT (kg/ha)": "PTOT (mg/l)",
    "Deposition STOT (kg/ha)": "STOT (mg/l)",
}
# Stemflow (SF) and runoff water (RW) require specific flow/area data.
# Therefore, the generic concentration × precipitation deposition formula is
# deliberately not applied to those subprogrammes.
skip_generic_deposition = subprogram_code.isin({"SF", "RW"})
for output_column, source_column in deposition_sources.items():
    calculated = deposition(
        aggregated[source_column], aggregated["Precip(l/m2)"]
    )
    aggregated[output_column] = calculated.where(
        ~skip_generic_deposition, pd.NA
    )


print("Final-data source availability:")
for column in [
    "DerivedSubprogram", "Temperature(ºC)", "Precip(l/m2)",
    "P(mg/l)", "PO4P(mg/l)", "S(mg/l)", "SO4S(mg/l)",
    "Volume(ml)", "NING(mg/l)", "NDON(mg/l)",
]:
    available = aggregated[column].notna().sum() if column in aggregated.columns else 0
    print(f"  {column}: {available}/{len(aggregated)} non-empty")

final_subprogram_counts = aggregated["subprogram"].replace("", pd.NA).value_counts(dropna=False)
print("Final subprogram counts:")
for code, count in final_subprogram_counts.items():
    label = "<unmapped>" if pd.isna(code) else str(code)
    print(f"  {label}: {count}")

OUTPUT_COLUMNS = [
    "SampleID", "SiteCode", "SiteName", "year", "month",
    "StartDate", "EndDate",
    "program", "subprogram", "lis_tip", "ID_PostgreSQL",
    "CL(mg/l)", "SO4S(mg/l)", "NO3N(mg/l)", "PO4P(mg/l)",
    "CA(mg/l)", "MG(mg/l)", "NA(mg/l)", "K(mg/l)",
    "AL(mg/l)", "FE(mg/l)", "MN(mg/l)",
    "AS(mg/l)", "CD(mg/l)", "CR(mg/l)", "CU(mg/l)", "CO(mg/l)",
    "MO(mg/l)", "NI(mg/l)", "PB(mg/l)", "ZN(mg/l)",
    "P(mg/l)", "S(mg/l)", "PTOT (mg/l)", "STOT (mg/l)",
    "NH4N(mg/l)", "TN(mg/l)", "DOC(mg/l)",
    "NING (mg/l)", "NDON (mg/l)",
    "H(µeq/l)", "WeightedConductivity(µS/cm)",
    "Volume(ml)", "VOL (ml)", "Precip(l/m2)",
    "WeightedpH", "AlkalinityICPForests(µeq/l)",
    "TEMP (oC)", "q", "hg", "f", "cnr", "sio2", "ALL",
    "Deposition K (kg/ha)", "Deposition Ca (kg/ha)",
    "Deposition Mg (kg/ha)", "Deposition Na (kg/ha)",
    "Deposition NH4N (kg/ha)", "Deposition Cl (kg/ha)",
    "Deposition NO3N (kg/ha)", "Deposition SO4S (kg/ha)",
    "Deposition NTOT (kg/ha)",
    "Deposition DOC (kg/ha)", "Deposition Al (kg/ha)",
    "Deposition Mn (kg/ha)", "Deposition Fe (kg/ha)",
    "Deposition NDON (kg/ha)", "Deposition NING (kg/ha)",
    "Deposition As (kg/ha)", "Deposition Cd (kg/ha)",
    "Deposition Cr (kg/ha)", "Deposition Cu (kg/ha)",
    "Deposition Mo (kg/ha)", "Deposition Ni (kg/ha)",
    "Deposition Pb (kg/ha)", "Deposition Zn (kg/ha)",
    "Deposition PO4P (kg/ha)", "Deposition PTOT (kg/ha)",
    "Deposition STOT (kg/ha)",
]

for column in OUTPUT_COLUMNS:
    if column not in aggregated.columns:
        aggregated[column] = pd.NA

output = aggregated.reindex(columns=OUTPUT_COLUMNS)
Path(output_path).parent.mkdir(parents=True, exist_ok=True)
output.to_excel(output_path, index=False, sheet_name="Datos")
print(
    f"Output saved: {output_path} "
    f"({len(output)} rows, {len(output.columns)} columns)"
)
