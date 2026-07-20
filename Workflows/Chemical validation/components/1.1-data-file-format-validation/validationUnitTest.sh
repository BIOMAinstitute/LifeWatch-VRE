#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
IMAGE_NAME="lw-flexible-data-format-validation:test"
TMP_DIR="$(mktemp -d)"
trap 'rm -rf "$TMP_DIR"' EXIT

echo "Building ${IMAGE_NAME}..."
docker build -t "$IMAGE_NAME" "$ROOT_DIR"

run_case() {
  local case_name="$1"
  local input_dir="$2"
  shift 2

  local output_dir="$TMP_DIR/$case_name"
  mkdir -p "$output_dir"

  echo
  echo "Running test case: $case_name"
  docker run --rm \
    -v "$input_dir:/mnt/inputs:ro" \
    -v "$output_dir:/mnt/outputs" \
    "$IMAGE_NAME" "$@"

  test -s "$output_dir/validation_log.txt"
  test -s "$output_dir/validation_report.json"
  test -s "$output_dir/validated_data.zip"
}

# -----------------------------------------------------------------------------
# 1. ZIP containing several Excel files.
# -----------------------------------------------------------------------------
run_case \
  "zip-input" \
  "$ROOT_DIR/resources/example/data-zip-file/inputs" \
  --stopOnErrors TRUE \
  --inputMode AUTO \
  --unmatchedFiles ERROR \
  --outputPrefix validated_

python - "$TMP_DIR/zip-input/validation_report.json" "$TMP_DIR/zip-input/validated_data.zip" <<'PY'
import json
import sys
import zipfile

report_path, zip_path = sys.argv[1:]
with open(report_path, encoding="utf-8") as handle:
    report = json.load(handle)

summary = report["summary"]
assert summary["files_checked"] == 44, summary
assert summary["critical_errors"] == 0, summary
assert {item["table_type"] for item in report["files"]} >= {
    "phWeighted", "Alkalinity", "Ammonium", "Anions", "Cations", "DocTN"
}

with zipfile.ZipFile(zip_path) as archive:
    names = archive.namelist()
assert names, "The output ZIP is empty"
assert all(name.startswith("input_data/") for name in names), names[:5]
assert all("/validated_" in name for name in names), names[:5]
PY

# -----------------------------------------------------------------------------
# 2. One standalone extensionless Excel file, as mounted by a Tesseract Bin
#    input. Its file kind and table type must both be detected automatically.
# -----------------------------------------------------------------------------
SINGLE_INPUT_DIR="$TMP_DIR/single-excel-inputs"
mkdir -p "$SINGLE_INPUT_DIR"
cp "$ROOT_DIR/resources/example/data-1-template/inputs/tables_config.json" \
  "$SINGLE_INPUT_DIR/tables_config.json"
cp "$ROOT_DIR/resources/example/data-1-template/inputs/2025_01_FOREST_CATIONS.xlsx" \
  "$SINGLE_INPUT_DIR/input_data"

run_case \
  "single-excel" \
  "$SINGLE_INPUT_DIR" \
  --stopOnErrors TRUE \
  --inputMode SINGLE_FILE \
  --unmatchedFiles ERROR \
  --outputPrefix validated_

python - "$TMP_DIR/single-excel/validation_report.json" <<'PY'
import json
import sys

with open(sys.argv[1], encoding="utf-8") as handle:
    report = json.load(handle)

summary = report["summary"]
assert summary["files_checked"] == 1, summary
assert summary["critical_errors"] == 0, summary
assert report["files"][0]["table_type"] == "Cations", report["files"][0]
assert report["files"][0]["reader"]["kind"] == "excel", report["files"][0]
PY

# -----------------------------------------------------------------------------
# 3. Several standalone files in AUTO mode: one CSV and one Excel workbook.
# -----------------------------------------------------------------------------
run_case \
  "mixed-standalone" \
  "$ROOT_DIR/resources/example/data/inputs" \
  --stopOnErrors TRUE \
  --inputMode AUTO \
  --unmatchedFiles ERROR \
  --outputPrefix validated_

python - "$TMP_DIR/mixed-standalone/validation_report.json" <<'PY'
import json
import sys

with open(sys.argv[1], encoding="utf-8") as handle:
    report = json.load(handle)

summary = report["summary"]
assert summary["files_checked"] == 2, summary
assert summary["critical_errors"] == 0, summary
assert {item["table_type"] for item in report["files"]} == {"example"}
assert {item["reader"]["kind"] for item in report["files"]} == {"csv", "excel"}
PY

echo
echo "All validation component tests passed."
