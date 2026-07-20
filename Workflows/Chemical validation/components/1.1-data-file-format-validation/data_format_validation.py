# ------------------------------------------------------------
# GENERAL DATA FORMAT VALIDATOR
# ------------------------------------------------------------
# Validates either one standalone Excel/CSV/TSV/TXT table or a ZIP
# containing any mixture of those formats. Reading and validation rules
# are defined in a JSON configuration.
# ------------------------------------------------------------

from __future__ import annotations

import argparse
import csv
import fnmatch
import json
import math
import os
import re
import shutil
import sys
import zipfile
from datetime import date, datetime
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd


# ------------------------------------------------------------
# CLI
# ------------------------------------------------------------
parser = argparse.ArgumentParser(description="Flexible Excel/CSV format validator")
parser.add_argument(
    "--stopOnErrors",
    default="TRUE",
    help="Exit with code 1 if critical errors are found (TRUE/FALSE)",
)
parser.add_argument(
    "--inputMode",
    default="AUTO",
    help="AUTO, ARCHIVE or SINGLE_FILE. AUTO detects the input content.",
)
parser.add_argument(
    "--unmatchedFiles",
    default="ERROR",
    help="How to handle data files that cannot be associated with a table rule: ERROR, WARNING or IGNORE.",
)
parser.add_argument(
    "--outputPrefix",
    default="validated_",
    help="Prefix added to filenames in the output ZIP.",
)
args = parser.parse_args()


def parse_bool(value: str) -> bool:
    return str(value).strip().upper() == "TRUE"


stop_on_errors = parse_bool(args.stopOnErrors)
input_mode = args.inputMode.strip().upper()
unmatched_policy = args.unmatchedFiles.strip().upper()
output_prefix = args.outputPrefix

if input_mode not in {"AUTO", "ARCHIVE", "SINGLE_FILE"}:
    parser.error("--inputMode must be AUTO, ARCHIVE or SINGLE_FILE")
if unmatched_policy not in {"ERROR", "WARNING", "IGNORE"}:
    parser.error("--unmatchedFiles must be ERROR, WARNING or IGNORE")


# ------------------------------------------------------------
# PATHS — Tesseract convention
# ------------------------------------------------------------
INPUT_ROOT = Path("/mnt/inputs")
PRIMARY_INPUT_PATH = INPUT_ROOT / "input_data"
CONFIG_CANDIDATES = [
    INPUT_ROOT / "tables_config.json",
    INPUT_ROOT / "tables_config.txt",
]
OUTPUT_LOG_PATH = Path("/mnt/outputs/validation_log.txt")
OUTPUT_JSON_PATH = Path("/mnt/outputs/validation_report.json")
OUTPUT_ZIP_PATH = Path("/mnt/outputs/validated_data.zip")
WORK_DIR = Path("/tmp/data_format_validation/prepared_input")
PREPARED_DATA_ROOT = WORK_DIR / "input_data"


# ------------------------------------------------------------
# CONSTANTS
# ------------------------------------------------------------
DEFAULTS: dict[str, Any] = {
    "supported_extensions": [".xlsx", ".xlsm", ".xls", ".csv", ".tsv", ".txt"],
    "reader": {
        "excel": {
            "sheet_name": "data",
        },
        "csv": {
            "sep": ";",
            "decimal": ".",
            "encoding": "utf-8-sig",
            "quotechar": '"',
        },
        "tsv": {
            "sep": "\\t",
            "decimal": ".",
            "encoding": "utf-8-sig",
            "quotechar": '"',
        },
        "txt": {
            "sep": ";",
            "decimal": ".",
            "encoding": "utf-8-sig",
            "quotechar": '"',
        },
    },
    "na_values": ["", "n.a", "n.a.", "NA", "N/A", "na", "NaN", "null", "NULL"],
    "strip_column_names": True,
    "strip_string_values": True,
    "drop_completely_empty_rows": True,
    "drop_unnamed_empty_columns": True,
    "warn_unexpected_columns": True,
    "warn_empty_optional_columns": True,
    "fail_if_no_files": False,
    "max_examples_per_rule": 8,
}

EXCEL_EXTENSIONS = {".xlsx", ".xlsm", ".xls"}
CSV_EXTENSIONS = {".csv", ".tsv", ".txt"}


# ------------------------------------------------------------
# GENERIC HELPERS
# ------------------------------------------------------------
def deep_merge(base: dict[str, Any], override: dict[str, Any] | None) -> dict[str, Any]:
    """Recursively merge dictionaries without modifying the originals."""
    result = dict(base)
    for key, value in (override or {}).items():
        if isinstance(value, dict) and isinstance(result.get(key), dict):
            result[key] = deep_merge(result[key], value)
        else:
            result[key] = value
    return result


def safe_extract_zip(zip_path: Path, destination: Path) -> None:
    """Extract a ZIP while preventing path traversal outside destination."""
    destination = destination.resolve()
    with zipfile.ZipFile(zip_path, "r") as archive:
        for member in archive.infolist():
            target = (destination / member.filename).resolve()
            if target != destination and destination not in target.parents:
                raise RuntimeError(f"Unsafe path found in ZIP: {member.filename}")
        archive.extractall(destination)



def is_excel_ooxml(path: Path) -> bool:
    """Return True when a ZIP-compatible file is an XLSX/XLSM workbook."""
    if not zipfile.is_zipfile(path):
        return False
    try:
        with zipfile.ZipFile(path, "r") as archive:
            names = set(archive.namelist())
        return "[Content_Types].xml" in names and any(
            name in names for name in ("xl/workbook.xml", "xl/workbook.bin")
        )
    except (OSError, zipfile.BadZipFile):
        return False


def inspect_file_kind(path: Path) -> str:
    """Identify archive, Excel, or delimited text even when the input has no suffix."""
    if not path.is_file():
        return "unsupported"

    suffix = path.suffix.lower()
    try:
        with path.open("rb") as handle:
            magic = handle.read(8)
    except OSError:
        return "unsupported"

    if is_excel_ooxml(path):
        return "excel"
    if magic.startswith(b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1"):
        return "excel_legacy"
    if zipfile.is_zipfile(path):
        return "archive"
    if suffix in {".xlsx", ".xlsm"}:
        return "excel"
    if suffix == ".xls":
        return "excel_legacy"
    if suffix == ".tsv":
        return "tsv"
    if suffix == ".txt":
        return "txt"
    if suffix == ".csv" or suffix == "":
        return "csv"
    return "unsupported"


def inferred_suffix(kind: str) -> str:
    return {
        "excel": ".xlsx",
        "excel_legacy": ".xls",
        "csv": ".csv",
        "tsv": ".tsv",
        "txt": ".txt",
    }.get(kind, "")


def locate_configuration(input_root: Path) -> Path:
    for candidate in CONFIG_CANDIDATES:
        if candidate.exists():
            return candidate

    possible = sorted(
        path for path in input_root.rglob("*")
        if path.is_file()
        and not path.name.startswith(".")
        and path.suffix.lower() in {".json", ".txt"}
        and "config" in path.name.casefold()
    )
    if len(possible) == 1:
        return possible[0]
    if not possible:
        raise RuntimeError(
            "Configuration file not found. Expected /mnt/inputs/tables_config.json "
            "or /mnt/inputs/tables_config.txt"
        )
    raise RuntimeError(
        "Several possible configuration files were found: "
        + ", ".join(str(path) for path in possible)
    )


def discover_top_level_inputs(input_root: Path, config_path: Path) -> list[Path]:
    candidates: list[Path] = []
    if PRIMARY_INPUT_PATH.exists() and PRIMARY_INPUT_PATH.resolve() != config_path.resolve():
        candidates.append(PRIMARY_INPUT_PATH)

    for path in sorted(input_root.rglob("*")):
        if not path.is_file() or path.name.startswith(".") or path.name.startswith("~$"):
            continue
        if path.resolve() == config_path.resolve():
            continue
        if path in candidates:
            continue
        candidates.append(path)
    return candidates


def unique_destination(directory: Path, filename: str) -> Path:
    candidate = directory / filename
    if not candidate.exists():
        return candidate
    stem = Path(filename).stem
    suffix = Path(filename).suffix
    counter = 2
    while True:
        candidate = directory / f"{stem}_{counter}{suffix}"
        if not candidate.exists():
            return candidate
        counter += 1


def prepare_input_data(
    input_root: Path,
    config_path: Path,
    mode: str,
) -> tuple[list[Path], list[str]]:
    """Materialize archives and standalone files in a common work directory."""
    if WORK_DIR.exists():
        shutil.rmtree(WORK_DIR)
    WORK_DIR.mkdir(parents=True, exist_ok=True)
    PREPARED_DATA_ROOT.mkdir(parents=True, exist_ok=True)

    input_candidates = discover_top_level_inputs(input_root, config_path)
    if not input_candidates:
        raise RuntimeError("No data input was found in /mnt/inputs")

    prepared_files: list[Path] = []
    preparation_notes: list[str] = []
    archives = [path for path in input_candidates if inspect_file_kind(path) == "archive"]
    standalone = [
        path for path in input_candidates
        if inspect_file_kind(path) in {"excel", "excel_legacy", "csv", "tsv", "txt"}
    ]
    unsupported = [path for path in input_candidates if inspect_file_kind(path) == "unsupported"]

    if mode == "ARCHIVE" and not archives:
        raise RuntimeError("inputMode=ARCHIVE but no ZIP archive was found")
    if mode == "SINGLE_FILE" and not standalone:
        raise RuntimeError("inputMode=SINGLE_FILE but no standalone Excel/CSV file was found")
    if mode == "SINGLE_FILE" and len(standalone) != 1:
        raise RuntimeError(
            f"inputMode=SINGLE_FILE requires exactly one standalone file; found {len(standalone)}"
        )

    selected_archives = archives if mode in {"AUTO", "ARCHIVE"} else []
    selected_standalone = standalone if mode in {"AUTO", "SINGLE_FILE"} else []

    for number, archive_path in enumerate(selected_archives, start=1):
        # A single archive is extracted directly under input_data/. If several
        # archives are supplied, each receives a subfolder to avoid collisions.
        destination = (
            PREPARED_DATA_ROOT
            if len(selected_archives) == 1
            else PREPARED_DATA_ROOT / f"archive_{number}_{archive_path.stem or 'input'}"
        )
        destination.mkdir(parents=True, exist_ok=True)
        safe_extract_zip(archive_path, destination)
        preparation_notes.append(f"Extracted archive: {archive_path.name}")

    loose_dir = PREPARED_DATA_ROOT
    loose_dir.mkdir(parents=True, exist_ok=True)
    for source in selected_standalone:
        kind = inspect_file_kind(source)
        filename = source.name
        if not Path(filename).suffix:
            filename += inferred_suffix(kind)
        destination = unique_destination(loose_dir, filename)
        shutil.copy2(source, destination)
        preparation_notes.append(
            f"Prepared standalone file: {source.name} -> {destination.name} ({kind})"
        )

    for path in sorted(WORK_DIR.rglob("*")):
        if not path.is_file() or path.name.startswith("~$"):
            continue
        if inspect_file_kind(path) in {"excel", "excel_legacy", "csv", "tsv", "txt"}:
            prepared_files.append(path)

    if unsupported:
        preparation_notes.append(
            "Ignored unsupported input file(s): " + ", ".join(path.name for path in unsupported)
        )
    if not prepared_files:
        raise RuntimeError("No supported Excel/CSV/TSV/TXT files were found in the input")

    return sorted(prepared_files, key=lambda path: path.as_posix().casefold()), preparation_notes


def load_configuration(config_path: Path) -> dict[str, Any]:
    with config_path.open("r", encoding="utf-8") as handle:
        raw = json.load(handle)

    # New format: {"defaults": {...}, "tables": [...]}
    if isinstance(raw, dict):
        tables = raw.get("tables")
        if not isinstance(tables, list):
            raise ValueError("Configuration must contain a 'tables' list")
        defaults = deep_merge(DEFAULTS, raw.get("defaults", {}))
        return {"defaults": defaults, "tables": tables}

    # Backward-compatible format: a direct list of table definitions
    if isinstance(raw, list):
        return {"defaults": dict(DEFAULTS), "tables": raw}

    raise ValueError("Configuration must be either a JSON object or a JSON list")


def normalize_reader_options(options: dict[str, Any]) -> dict[str, Any]:
    """Convert JSON-friendly reader values to values expected by pandas."""
    normalized = dict(options)
    if normalized.get("sep") == "\\t":
        normalized["sep"] = "\t"
    return normalized


def table_patterns(table_cfg: dict[str, Any]) -> list[str]:
    patterns = table_cfg.get("patterns")
    if patterns is None:
        path = table_cfg.get("path")
        patterns = [path] if path else []
    elif isinstance(patterns, str):
        patterns = [patterns]

    if not patterns:
        raise ValueError(f"Table '{table_cfg.get('type', '<unknown>')}' has no path/patterns")
    return patterns


def find_matching_files(
    root: Path,
    table_cfg: dict[str, Any],
    defaults: dict[str, Any],
) -> list[Path]:
    """Find files recursively, matching patterns against relative path and filename."""
    supported = {
        str(ext).lower() if str(ext).startswith(".") else f".{str(ext).lower()}"
        for ext in table_cfg.get("supported_extensions", defaults["supported_extensions"])
    }
    patterns = table_patterns(table_cfg)
    matches: set[Path] = set()

    for candidate in root.rglob("*"):
        if not candidate.is_file() or candidate.name.startswith("~$"):
            continue
        if candidate.suffix.lower() not in supported:
            continue

        relative = candidate.relative_to(root).as_posix()
        if any(
            fnmatch.fnmatch(relative, pattern)
            or fnmatch.fnmatch(candidate.name, pattern)
            for pattern in patterns
        ):
            matches.add(candidate)

    return sorted(matches, key=lambda p: p.as_posix().lower())


def get_file_reader_options(
    fpath: Path,
    table_cfg: dict[str, Any],
    defaults: dict[str, Any],
) -> tuple[str, dict[str, Any]]:
    detected_kind = inspect_file_kind(fpath)
    reader_defaults = defaults.get("reader", {})
    reader_override = table_cfg.get("reader", {})

    if detected_kind in {"excel", "excel_legacy"}:
        kind = "excel"
    elif detected_kind in {"csv", "tsv", "txt"}:
        kind = detected_kind
    else:
        raise ValueError(f"Unsupported table file: {fpath.name}")

    options = deep_merge(reader_defaults.get(kind, {}), reader_override.get(kind, {}))
    options["_detected_kind"] = detected_kind
    return kind, normalize_reader_options(options)


def read_table(
    fpath: Path,
    table_cfg: dict[str, Any],
    defaults: dict[str, Any],
) -> tuple[pd.DataFrame, dict[str, Any]]:
    """Read Excel/CSV/TSV/TXT through one common interface."""
    kind, options = get_file_reader_options(fpath, table_cfg, defaults)
    detected_kind = options.pop("_detected_kind", kind)
    na_values = table_cfg.get("na_values", defaults.get("na_values", []))

    if kind == "excel":
        read_options = dict(options)
        if detected_kind == "excel":
            read_options.setdefault("engine", "openpyxl")
        elif detected_kind == "excel_legacy":
            read_options.setdefault("engine", "xlrd")
        df = pd.read_excel(
            fpath,
            dtype=object,
            na_values=na_values,
            keep_default_na=True,
            **read_options,
        )
    else:
        read_options = dict(options)
        sep = read_options.pop("sep", ";")
        if sep in {None, "auto", "AUTO"}:
            sep = None
            read_options.setdefault("engine", "python")
        df = pd.read_csv(
            fpath,
            sep=sep,
            dtype=object,
            na_values=na_values,
            keep_default_na=True,
            **read_options,
        )

    df = normalize_dataframe(df, table_cfg, defaults)
    return df, {"kind": kind, "detected_kind": detected_kind, **options}


def normalize_dataframe(
    df: pd.DataFrame,
    table_cfg: dict[str, Any],
    defaults: dict[str, Any],
) -> pd.DataFrame:
    result = df.copy()

    if table_cfg.get("strip_column_names", defaults["strip_column_names"]):
        result.columns = [str(col).replace("\ufeff", "").strip() for col in result.columns]

    if table_cfg.get("strip_string_values", defaults["strip_string_values"]):
        for col in result.columns:
            result[col] = result[col].map(lambda value: value.strip() if isinstance(value, str) else value)

    # Convert strings that became empty after stripping into missing values.
    result.replace(r"^\s*$", np.nan, regex=True, inplace=True)

    if table_cfg.get("drop_completely_empty_rows", defaults["drop_completely_empty_rows"]):
        result.dropna(axis=0, how="all", inplace=True)

    if table_cfg.get("drop_unnamed_empty_columns", defaults["drop_unnamed_empty_columns"]):
        removable = [
            col
            for col in result.columns
            if str(col).startswith("Unnamed:") and result[col].isna().all()
        ]
        if removable:
            result.drop(columns=removable, inplace=True)

    result.reset_index(drop=True, inplace=True)
    return result


# ------------------------------------------------------------
# CONFIGURATION NORMALIZATION
# ------------------------------------------------------------
def normalize_column_rule(rule: Any) -> dict[str, Any]:
    if isinstance(rule, str):
        return {"type": rule}
    if isinstance(rule, dict):
        return dict(rule)
    raise ValueError(f"Invalid column rule: {rule!r}")


def convert_legacy_table_config(table_cfg: dict[str, Any]) -> dict[str, Any]:
    """Convert the original schema/lists format into unified per-column rules."""
    if "columns" in table_cfg:
        converted = dict(table_cfg)
        converted["columns"] = {
            col: normalize_column_rule(rule)
            for col, rule in table_cfg["columns"].items()
        }
        return converted

    if "schema" not in table_cfg:
        raise ValueError(f"Table '{table_cfg.get('type', '<unknown>')}' has no 'columns' or 'schema'")

    converted = dict(table_cfg)
    required_columns = set(table_cfg.get("required_columns", table_cfg.get("critical_columns", [])))
    no_empty = set(table_cfg.get("no_empty", []))
    optional_columns = set(table_cfg.get("optional_columns", []))
    no_negatives = set(table_cfg.get("no_negatives", []))
    formats = table_cfg.get("formats", {})
    ranges = table_cfg.get("expected_ranges", {})

    columns: dict[str, dict[str, Any]] = {}
    for col, legacy_rule in table_cfg["schema"].items():
        rule = normalize_column_rule(legacy_rule)
        rule["required"] = col in required_columns or col in no_empty
        rule["nullable"] = col not in no_empty
        if col in optional_columns:
            rule["required"] = False
        if col in no_negatives:
            rule["min"] = 0
        if col in formats:
            rule["regex"] = formats[col]
        if col in ranges:
            rule["expected_range"] = ranges[col]
        columns[col] = rule

    converted["columns"] = columns
    return converted


def validate_table_configuration(table_cfg: dict[str, Any]) -> list[str]:
    warnings: list[str] = []
    columns = table_cfg.get("columns", {})
    if not isinstance(columns, dict) or not columns:
        raise ValueError(f"Table '{table_cfg.get('type', '<unknown>')}' has no column definitions")

    allowed_types = {"object", "string", "float", "number", "integer", "int", "datetime", "date", "boolean", "bool"}
    for col, rule in columns.items():
        col_type = str(rule.get("type", "object")).lower()
        if col_type not in allowed_types:
            raise ValueError(f"Unsupported type '{col_type}' for column '{col}'")
        if rule.get("nullable") is False and not rule.get("required", False):
            warnings.append(
                f"Column '{col}' is nullable=false but required=false; missing column is allowed, empty cells are not"
            )
    return warnings


# ------------------------------------------------------------
# VALUE CONVERSION HELPERS
# ------------------------------------------------------------
def is_missing(value: Any) -> bool:
    try:
        return bool(pd.isna(value))
    except (TypeError, ValueError):
        return False


def parse_number(value: Any, decimal: str = ".", thousands: str | None = None) -> float:
    if is_missing(value):
        return math.nan
    if isinstance(value, (int, float, np.integer, np.floating)) and not isinstance(value, bool):
        return float(value)

    text = str(value).strip().replace("\u2212", "-").replace("\xa0", "")
    text = text.replace(" ", "")
    if thousands:
        text = text.replace(thousands, "")
    if decimal and decimal != ".":
        text = text.replace(decimal, ".")
    return float(text)


def coerce_numeric_series(
    series: pd.Series,
    decimal: str = ".",
    thousands: str | None = None,
) -> pd.Series:
    converted: dict[Any, float] = {}
    for idx, value in series.items():
        try:
            converted[idx] = parse_number(value, decimal=decimal, thousands=thousands)
        except (TypeError, ValueError, OverflowError):
            converted[idx] = math.nan
    return pd.Series(converted, index=series.index, dtype="float64")


def coerce_datetime_series(series: pd.Series, rule: dict[str, Any]) -> pd.Series:
    formats = rule.get("formats", rule.get("format"))
    if formats is None:
        formats_list: list[str | None] = [None]
    elif isinstance(formats, list):
        formats_list = formats
    else:
        formats_list = [formats]

    dayfirst = bool(rule.get("dayfirst", False))
    converted: dict[Any, Any] = {}

    for idx, value in series.items():
        if isinstance(value, (datetime, date, pd.Timestamp, np.datetime64)):
            converted[idx] = pd.to_datetime(value, errors="coerce")
            continue

        parsed = pd.NaT
        for fmt in formats_list:
            parsed = pd.to_datetime(value, format=fmt, dayfirst=dayfirst, errors="coerce")
            if not pd.isna(parsed):
                break
        converted[idx] = parsed

    return pd.Series(converted, index=series.index)


def compact_examples(df: pd.DataFrame, col: str, indexes: list[int], maximum: int) -> str:
    examples = []
    for idx in indexes[:maximum]:
        examples.append(f"row {idx + 2}: {df.at[idx, col]!r}")
    suffix = "" if len(indexes) <= maximum else f"; +{len(indexes) - maximum} more"
    return "; ".join(examples) + suffix


# ------------------------------------------------------------
# VALIDATION
# ------------------------------------------------------------
def validate_dataframe(
    df: pd.DataFrame,
    table_cfg: dict[str, Any],
    reader_options: dict[str, Any],
    defaults: dict[str, Any],
) -> tuple[list[str], list[str]]:
    errors: list[str] = []
    warnings: list[str] = []
    columns: dict[str, dict[str, Any]] = table_cfg["columns"]
    max_examples = int(table_cfg.get("max_examples_per_rule", defaults["max_examples_per_rule"]))

    expected_columns = set(columns)
    actual_columns = set(df.columns)

    # Duplicate headers are ambiguous and therefore critical.
    duplicated_headers = pd.Index(df.columns)[pd.Index(df.columns).duplicated()].tolist()
    if duplicated_headers:
        errors.append(f"Critical: duplicated column name(s): {sorted(set(duplicated_headers))}")

    # Required column presence.
    for col, rule in columns.items():
        if rule.get("required", False) and col not in actual_columns:
            errors.append(f"Critical: missing required column '{col}'")

    # Unexpected columns.
    unexpected = sorted(actual_columns - expected_columns)
    if unexpected and table_cfg.get("warn_unexpected_columns", defaults["warn_unexpected_columns"]):
        warnings.append(f"Unexpected column(s): {unexpected}")

    decimal = str(reader_options.get("decimal", "."))
    thousands = reader_options.get("thousands")

    for col, rule in columns.items():
        if col not in df.columns:
            continue

        series = df[col]
        non_missing = series.dropna()

        # Cell-level missing values.
        if rule.get("nullable", True) is False:
            missing_idx = series[series.isna()].index.tolist()
            if missing_idx:
                errors.append(
                    f"Critical: column '{col}' has {len(missing_idx)} empty value(s): "
                    + compact_examples(df, col, missing_idx, max_examples)
                )
        elif (
            not rule.get("required", False)
            and table_cfg.get("warn_empty_optional_columns", defaults["warn_empty_optional_columns"])
        ):
            if series.isna().all():
                warnings.append(f"Optional column '{col}' is completely empty")

        if non_missing.empty:
            continue

        col_type = str(rule.get("type", "object")).lower()
        numeric: pd.Series | None = None

        # Type checks.
        if col_type in {"float", "number", "integer", "int"}:
            numeric = coerce_numeric_series(non_missing, decimal=decimal, thousands=thousands)
            invalid_idx = numeric[numeric.isna()].index.tolist()
            if invalid_idx:
                errors.append(
                    f"Critical: column '{col}' has {len(invalid_idx)} non-numeric value(s): "
                    + compact_examples(df, col, invalid_idx, max_examples)
                )

            if col_type in {"integer", "int"}:
                valid_numeric = numeric.dropna()
                non_integer_idx = valid_numeric[(valid_numeric % 1).abs() > 1e-12].index.tolist()
                if non_integer_idx:
                    errors.append(
                        f"Critical: column '{col}' has {len(non_integer_idx)} non-integer value(s): "
                        + compact_examples(df, col, non_integer_idx, max_examples)
                    )

        elif col_type in {"datetime", "date"}:
            converted = coerce_datetime_series(non_missing, rule)
            invalid_idx = converted[converted.isna()].index.tolist()
            if invalid_idx:
                format_text = rule.get("formats", rule.get("format", "recognisable date"))
                errors.append(
                    f"Critical: column '{col}' has {len(invalid_idx)} invalid date value(s) "
                    f"for format {format_text!r}: "
                    + compact_examples(df, col, invalid_idx, max_examples)
                )

        elif col_type in {"boolean", "bool"}:
            allowed = rule.get("allowed_values", [True, False, "TRUE", "FALSE", "Y", "N", "1", "0"])
            allowed_text = {str(v).strip().casefold() for v in allowed}
            invalid_idx = [
                idx for idx, value in non_missing.items()
                if str(value).strip().casefold() not in allowed_text
            ]
            if invalid_idx:
                errors.append(
                    f"Critical: column '{col}' has {len(invalid_idx)} invalid boolean value(s): "
                    + compact_examples(df, col, invalid_idx, max_examples)
                )

        # Numeric constraints.
        if any(key in rule for key in ("min", "max", "expected_range")):
            if numeric is None:
                numeric = coerce_numeric_series(non_missing, decimal=decimal, thousands=thousands)
            valid_numeric = numeric.dropna()

            if "min" in rule:
                idxs = valid_numeric[valid_numeric < float(rule["min"])].index.tolist()
                if idxs:
                    errors.append(
                        f"Critical: column '{col}' has {len(idxs)} value(s) below minimum {rule['min']}: "
                        + compact_examples(df, col, idxs, max_examples)
                    )

            if "max" in rule:
                idxs = valid_numeric[valid_numeric > float(rule["max"])].index.tolist()
                if idxs:
                    errors.append(
                        f"Critical: column '{col}' has {len(idxs)} value(s) above maximum {rule['max']}: "
                        + compact_examples(df, col, idxs, max_examples)
                    )

            if "expected_range" in rule:
                min_expected, max_expected = rule["expected_range"]
                idxs = valid_numeric[
                    (valid_numeric < float(min_expected)) | (valid_numeric > float(max_expected))
                ].index.tolist()
                if idxs:
                    warnings.append(
                        f"Column '{col}' has {len(idxs)} value(s) outside expected range "
                        f"[{min_expected}, {max_expected}]: "
                        + compact_examples(df, col, idxs, max_examples)
                    )

        # Allowed values.
        if "allowed_values" in rule and col_type not in {"boolean", "bool"}:
            case_sensitive = bool(rule.get("case_sensitive", True))
            allowed_values = rule["allowed_values"]
            if case_sensitive:
                allowed = {str(v) for v in allowed_values}
                invalid_idx = [idx for idx, value in non_missing.items() if str(value) not in allowed]
            else:
                allowed = {str(v).casefold() for v in allowed_values}
                invalid_idx = [
                    idx for idx, value in non_missing.items()
                    if str(value).casefold() not in allowed
                ]
            if invalid_idx:
                errors.append(
                    f"Critical: column '{col}' has {len(invalid_idx)} value(s) outside allowed values "
                    f"{allowed_values}: "
                    + compact_examples(df, col, invalid_idx, max_examples)
                )

        # Regex.
        if "regex" in rule:
            regex = re.compile(str(rule["regex"]))
            invalid_idx = [
                idx for idx, value in non_missing.items()
                if regex.fullmatch(str(value)) is None
            ]
            if invalid_idx:
                errors.append(
                    f"Critical: column '{col}' has {len(invalid_idx)} value(s) that fail regex "
                    f"{rule['regex']!r}: "
                    + compact_examples(df, col, invalid_idx, max_examples)
                )

    return errors, warnings


def validate_file(
    fpath: Path,
    table_cfg: dict[str, Any],
    defaults: dict[str, Any],
) -> dict[str, Any]:
    result: dict[str, Any] = {
        "table_type": table_cfg.get("type", "unknown"),
        "file": fpath,
        "errors": [],
        "warnings": [],
        "rows": None,
        "columns": None,
        "reader": None,
    }

    try:
        df, reader_options = read_table(fpath, table_cfg, defaults)
        result["reader"] = reader_options
        result["rows"] = len(df)
        result["columns"] = len(df.columns)
        result["errors"], result["warnings"] = validate_dataframe(
            df, table_cfg, reader_options, defaults
        )
    except Exception as exc:  # Keep validating remaining files.
        result["errors"].append(
            f"Critical: could not read or validate file ({type(exc).__name__}: {exc})"
        )

    return result



# ------------------------------------------------------------
# FILE-TO-TABLE ASSIGNMENT
# ------------------------------------------------------------
def file_matches_patterns(fpath: Path, table_cfg: dict[str, Any], root: Path) -> bool:
    relative = fpath.relative_to(root).as_posix()
    return any(
        fnmatch.fnmatch(relative, pattern) or fnmatch.fnmatch(fpath.name, pattern)
        for pattern in table_patterns(table_cfg)
    )


def table_by_type(tables: list[dict[str, Any]], requested_type: str) -> dict[str, Any] | None:
    requested = requested_type.casefold()
    matches = [
        table for table in tables
        if str(table.get("type", "")).casefold() == requested
    ]
    if len(matches) == 1:
        return matches[0]
    return None


def common_configuration_columns(tables: list[dict[str, Any]]) -> set[str]:
    counts: dict[str, int] = {}
    for table in tables:
        for column in table["columns"]:
            counts[column] = counts.get(column, 0) + 1
    threshold = max(2, math.ceil(len(tables) / 2))
    return {column for column, count in counts.items() if count >= threshold}


def score_table_candidate(
    actual_columns: set[str],
    table_cfg: dict[str, Any],
    common_columns: set[str],
) -> tuple[int, int, int, int, int]:
    expected = set(table_cfg["columns"])
    required = {
        column for column, rule in table_cfg["columns"].items()
        if rule.get("required", False)
    }
    missing_required = len(required - actual_columns)
    discriminator_overlap = len(actual_columns & (expected - common_columns))
    total_overlap = len(actual_columns & expected)
    unexpected = len(actual_columns - expected)
    size_distance = abs(len(actual_columns) - len(expected))
    return (
        -missing_required,
        discriminator_overlap,
        total_overlap,
        -unexpected,
        -size_distance,
    )


def choose_table_by_schema(
    fpath: Path,
    candidates: list[dict[str, Any]],
    defaults: dict[str, Any],
    all_tables: list[dict[str, Any]],
) -> tuple[dict[str, Any] | None, str]:
    common_columns = common_configuration_columns(all_tables)
    scored: list[tuple[tuple[int, int, int, int, int], dict[str, Any], set[str]]] = []
    failures: list[str] = []

    for table_cfg in candidates:
        try:
            df, _ = read_table(fpath, table_cfg, defaults)
        except Exception as exc:
            failures.append(f"{table_cfg.get('type', 'unknown')}: {type(exc).__name__}: {exc}")
            continue
        actual = set(df.columns)
        scored.append((score_table_candidate(actual, table_cfg, common_columns), table_cfg, actual))

    if not scored:
        detail = "; ".join(failures[:3])
        return None, f"could not read the file with any candidate configuration ({detail})"

    scored.sort(key=lambda item: item[0], reverse=True)
    best_score, best_table, actual = scored[0]
    tied = [item for item in scored if item[0] == best_score]

    # With multiple configurations, at least one table-specific column should normally match.
    discriminator_overlap = best_score[1]
    if len(candidates) > 1 and discriminator_overlap == 0:
        return None, (
            "schema inference found no table-specific columns; use a filename matching a "
            "configured pattern or make the table schemas more distinct"
        )
    if len(tied) > 1:
        tied_types = [str(item[1].get("type", "unknown")) for item in tied]
        return None, (
            f"schema inference is ambiguous between {tied_types}; use a filename matching one pattern or make the schemas more distinct"
        )

    return best_table, (
        f"schema inference selected '{best_table.get('type', 'unknown')}' "
        f"with score {best_score} from columns {sorted(actual)}"
    )


def assign_table_configuration(
    fpath: Path,
    tables: list[dict[str, Any]],
    defaults: dict[str, Any],
) -> tuple[dict[str, Any] | None, str]:
    pattern_matches = [
        table for table in tables if file_matches_patterns(fpath, table, WORK_DIR)
    ]
    if len(pattern_matches) == 1:
        return pattern_matches[0], "filename pattern"
    if len(pattern_matches) > 1:
        selected, detail = choose_table_by_schema(
            fpath, pattern_matches, defaults, tables
        )
        return selected, f"multiple filename patterns; {detail}"

    selected, detail = choose_table_by_schema(fpath, tables, defaults, tables)
    return selected, detail


# ------------------------------------------------------------
# REPORTING AND OUTPUT
# ------------------------------------------------------------
def write_validation_log(
    results: list[dict[str, Any]],
    config_warnings: list[str],
    preparation_notes: list[str],
    output_path: Path,
) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)

    file_results = [result for result in results if result.get("file") is not None]
    total_files = len(file_results)
    total_errors = sum(len(result["errors"]) for result in results)
    total_warnings = sum(len(result["warnings"]) for result in results) + len(config_warnings)
    valid_files = sum(1 for result in file_results if not result["errors"])

    with output_path.open("w", encoding="utf-8") as handle:
        handle.write(f"TABLE VALIDATION — {datetime.now().isoformat(sep=' ', timespec='seconds')}\n")
        handle.write("=" * 78 + "\n")
        handle.write(f"Input mode: {input_mode}\n")
        handle.write(f"Files checked: {total_files}\n")
        handle.write(f"Files without critical errors: {valid_files}\n")
        handle.write(f"Critical errors: {total_errors}\n")
        handle.write(f"Warnings: {total_warnings}\n")
        handle.write("=" * 78 + "\n\n")

        if preparation_notes:
            handle.write("INPUT PREPARATION\n")
            for note in preparation_notes:
                handle.write(f"• {note}\n")
            handle.write("-" * 78 + "\n\n")

        if config_warnings:
            handle.write("CONFIGURATION WARNINGS\n")
            for warning in config_warnings:
                handle.write(f"⚠️  {warning}\n")
            handle.write("-" * 78 + "\n\n")

        for result in results:
            handle.write(f"Table type: {result['table_type']}\n")
            if result.get("file") is None:
                handle.write("File: <no matching file>\n")
            else:
                handle.write(f"File: {result.get('display_file', result['file'])}\n")
                if result.get("assignment_method"):
                    handle.write(f"Configuration assignment: {result['assignment_method']}\n")
                if result.get("reader"):
                    handle.write(f"Reader: {result['reader']}\n")
                if result.get("rows") is not None and result.get("columns") is not None:
                    handle.write(
                        f"Dimensions: {result['rows']} row(s) x {result['columns']} column(s)\n"
                    )

            if not result["errors"] and not result["warnings"]:
                handle.write("✅ No issues found. Format is valid.\n")
            else:
                for error in result["errors"]:
                    handle.write(f"❌ {error}\n")
                for warning in result["warnings"]:
                    handle.write(f"⚠️  {warning}\n")
            handle.write("-" * 78 + "\n")


def write_json_report(
    results: list[dict[str, Any]],
    config_warnings: list[str],
    preparation_notes: list[str],
    output_path: Path,
) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    file_results = [result for result in results if result.get("file") is not None]
    payload = {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "input_mode": input_mode,
        "summary": {
            "files_checked": len(file_results),
            "files_without_critical_errors": sum(
                1 for result in file_results if not result["errors"]
            ),
            "critical_errors": sum(len(result["errors"]) for result in results),
            "warnings": sum(len(result["warnings"]) for result in results)
            + len(config_warnings),
        },
        "input_preparation": preparation_notes,
        "configuration_warnings": config_warnings,
        "files": [],
    }

    for result in results:
        payload["files"].append(
            {
                "file": result.get("display_file")
                or (str(result["file"]) if result.get("file") is not None else None),
                "table_type": result["table_type"],
                "assignment_method": result.get("assignment_method"),
                "reader": result.get("reader"),
                "rows": result.get("rows"),
                "columns": result.get("columns"),
                "errors": result["errors"],
                "warnings": result["warnings"],
                "valid": not result["errors"],
            }
        )

    with output_path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2)


def build_output_zip(
    data_files: list[Path],
    source_root: Path,
    output_zip: Path,
    prefix: str,
) -> None:
    output_zip.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(output_zip, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for full_path in sorted(data_files, key=lambda path: path.as_posix().casefold()):
            relative = full_path.relative_to(source_root)
            renamed = relative.with_name(prefix + relative.name)
            archive.write(full_path, renamed.as_posix())


def missing_table_result(table_cfg: dict[str, Any]) -> dict[str, Any]:
    table_type = table_cfg.get("type", "unknown")
    message = f"No file was assigned to table type '{table_type}'"
    return {
        "table_type": table_type,
        "file": None,
        "display_file": None,
        "assignment_method": None,
        "errors": [f"Critical: {message}"],
        "warnings": [],
        "rows": None,
        "columns": None,
        "reader": None,
    }


# ------------------------------------------------------------
# MAIN
# ------------------------------------------------------------
def main() -> int:
    config_path = locate_configuration(INPUT_ROOT)
    print(f"Configuration: {config_path}")

    config = load_configuration(config_path)
    defaults = config["defaults"]
    config_warnings: list[str] = []
    tables: list[dict[str, Any]] = []

    for raw_table in config["tables"]:
        table_cfg = convert_legacy_table_config(raw_table)
        table_warnings = validate_table_configuration(table_cfg)
        config_warnings.extend(
            f"{table_cfg.get('type', 'unknown')}: {warning}" for warning in table_warnings
        )
        tables.append(table_cfg)

    prepared_files, preparation_notes = prepare_input_data(
        INPUT_ROOT, config_path, input_mode
    )
    print(f"Prepared {len(prepared_files)} data file(s)")

    results: list[dict[str, Any]] = []
    assigned_types: set[str] = set()

    for fpath in prepared_files:
        display_file = fpath.relative_to(WORK_DIR).as_posix()
        table_cfg, assignment_method = assign_table_configuration(
            fpath, tables, defaults
        )

        if table_cfg is None:
            message = (
                f"File could not be associated with a table configuration: {assignment_method}"
            )
            if unmatched_policy == "IGNORE":
                preparation_notes.append(f"Ignored unmatched file {display_file}: {assignment_method}")
                continue
            result = {
                "table_type": "<unmatched>",
                "file": fpath,
                "display_file": display_file,
                "assignment_method": assignment_method,
                "errors": [f"Critical: {message}"] if unmatched_policy == "ERROR" else [],
                "warnings": [message] if unmatched_policy == "WARNING" else [],
                "rows": None,
                "columns": None,
                "reader": None,
            }
            results.append(result)
            continue

        result = validate_file(fpath, table_cfg, defaults)
        result["display_file"] = display_file
        result["assignment_method"] = assignment_method
        results.append(result)
        assigned_types.add(str(table_cfg.get("type", "unknown")).casefold())
        print(
            f"[{table_cfg.get('type', 'unknown')}] {display_file} ({assignment_method})"
        )

    for table_cfg in tables:
        table_type = str(table_cfg.get("type", "unknown"))
        table_required = bool(
            table_cfg.get("fail_if_no_files", defaults.get("fail_if_no_files", False))
        )
        if table_required and table_type.casefold() not in assigned_types:
            results.append(missing_table_result(table_cfg))

    write_validation_log(results, config_warnings, preparation_notes, OUTPUT_LOG_PATH)
    write_json_report(results, config_warnings, preparation_notes, OUTPUT_JSON_PATH)
    build_output_zip(prepared_files, WORK_DIR, OUTPUT_ZIP_PATH, output_prefix)

    print(f"Validation log written to {OUTPUT_LOG_PATH}")
    print(f"JSON report written to {OUTPUT_JSON_PATH}")
    print(f"Validated data ZIP written to {OUTPUT_ZIP_PATH}")

    has_critical = any(result["errors"] for result in results)
    if has_critical:
        print("⚠️ Critical errors found. Check validation_log.txt for details.")
        return 1 if stop_on_errors else 0

    print("✅ Validation finished successfully.")
    return 0


def write_fatal_error_outputs(exc: Exception) -> None:
    OUTPUT_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    message = f"Critical: wrapper execution failed ({type(exc).__name__}: {exc})"
    OUTPUT_LOG_PATH.write_text(
        "TABLE VALIDATION — FATAL ERROR\n"
        + "=" * 78
        + "\n❌ "
        + message
        + "\n",
        encoding="utf-8",
    )
    with OUTPUT_JSON_PATH.open("w", encoding="utf-8") as handle:
        json.dump(
            {
                "generated_at": datetime.now().isoformat(timespec="seconds"),
                "summary": {
                    "files_checked": 0,
                    "files_without_critical_errors": 0,
                    "critical_errors": 1,
                    "warnings": 0,
                },
                "fatal_error": message,
                "files": [],
            },
            handle,
            ensure_ascii=False,
            indent=2,
        )
    with zipfile.ZipFile(OUTPUT_ZIP_PATH, "w", compression=zipfile.ZIP_DEFLATED):
        pass


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as exc:
        write_fatal_error_outputs(exc)
        print(f"❌ {type(exc).__name__}: {exc}", file=sys.stderr)
        sys.exit(1)