#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
IMAGE_NAME="lw-flexible-data-format-validation:test"
TMP_DIR="$(mktemp -d)"
trap 'rm -rf "$TMP_DIR"' EXIT

docker build -t "$IMAGE_NAME" "$ROOT_DIR"

run_case() {
  local case_name="$1"
  local input_dir="$2"
  shift 2

  local output_dir="$TMP_DIR/$case_name"
  mkdir -p "$output_dir"

  docker run --rm \
    -v "$input_dir:/mnt/inputs:ro" \
    -v "$output_dir:/mnt/outputs" \
    "$IMAGE_NAME" "$@"

  test -s "$output_dir/level0/validation_log.txt"
  test -s "$output_dir/level0/validation_report.json"
  test -s "$output_dir/level0/validated_data.zip"
}

# The supplied ZIP has known critical data findings, so continue after reporting.
run_case \
  "archive" \
  "$ROOT_DIR/resources/example/data/inputs" \
  --stopOnErrors FALSE \
  --inputMode AUTO \
  --tableType "" \
  --requireAllTableTypes TRUE \
  --unmatchedFiles ERROR \
  --outputPrefix validated_

python - "$TMP_DIR/archive/level0/validation_report.json" <<'PY'
import json
import sys

with open(sys.argv[1], encoding="utf-8") as handle:
    report = json.load(handle)

assert report["summary"]["files_checked"] == 44, report["summary"]
assert report["summary"]["critical_errors"] > 0, report["summary"]
assert {item["table_type"] for item in report["files"]} >= {
    "phWeighted", "Alkalinity", "Ammonium", "Anions", "Cations", "DocTN"
}
PY

# A standalone extensionless XLSX must be identified and inferred as Anions.
run_case \
  "single-file" \
  "$ROOT_DIR/resources/example/single-file/inputs" \
  --stopOnErrors TRUE \
  --inputMode SINGLE_FILE \
  --tableType "" \
  --requireAllTableTypes FALSE \
  --unmatchedFiles ERROR \
  --outputPrefix validated_

python - "$TMP_DIR/single-file/level0/validation_report.json" <<'PY'
import json
import sys

with open(sys.argv[1], encoding="utf-8") as handle:
    report = json.load(handle)

assert report["summary"]["files_checked"] == 1, report["summary"]
assert report["summary"]["critical_errors"] == 0, report["summary"]
assert report["files"][0]["table_type"] == "Anions", report["files"][0]
assert report["files"][0]["reader"]["kind"] == "excel", report["files"][0]
PY

echo "All validation wrapper tests passed."
