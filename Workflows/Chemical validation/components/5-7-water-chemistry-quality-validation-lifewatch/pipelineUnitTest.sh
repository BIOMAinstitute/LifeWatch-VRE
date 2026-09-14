#!/usr/bin/env bash
set -euo pipefail

IMAGE_NAME="water-chemistry-quality-report:test"
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
INPUT_DIR="$ROOT_DIR/resources/example/data/inputs"
OUTPUT_DIR="$ROOT_DIR/resources/example/data/outputs"

rm -rf "$OUTPUT_DIR"
mkdir -p "$OUTPUT_DIR"
touch "$OUTPUT_DIR/.gitignore"

docker build --no-cache -t "$IMAGE_NAME" "$ROOT_DIR"

docker run --rm \
  -v "$INPUT_DIR:/mnt/inputs:ro" \
  -v "$OUTPUT_DIR:/mnt/outputs" \
  "$IMAGE_NAME"

required=(
  validation_report.pdf
  Samples2Repeat.xlsx
  All_Validated_Data.xlsx
  Final_Data.xlsx
  pipeline_execution.log
)

for file in "${required[@]}"; do
  test -s "$OUTPUT_DIR/$file" || {
    echo "Missing or empty output: $file"
    exit 1
  }
done

# The two ZIP files are internal temporary artifacts and must not be published.
for file in water_chemical_alldata_calculated.zip water_chemical_alldata_validated.zip; do
  test ! -e "$OUTPUT_DIR/$file" || {
    echo "Unexpected public ZIP output: $file"
    exit 1
  }
done

python - "$OUTPUT_DIR" "$INPUT_DIR/samplesInfo.xlsx" <<'PY'
import re
import sys
from pathlib import Path

from openpyxl import load_workbook

out = Path(sys.argv[1])
samples_path = Path(sys.argv[2])

pdf = (out / "validation_report.pdf").read_bytes()
assert pdf.startswith(b"%PDF"), "validation_report.pdf is not a valid PDF file"

expected_rows = {
    "Samples2Repeat.xlsx": 194,
    "All_Validated_Data.xlsx": 300,
    "Final_Data.xlsx": 106,
}
for name, expected_data_rows in expected_rows.items():
    workbook = load_workbook(out / name, read_only=True, data_only=True)
    sheet = workbook[workbook.sheetnames[0]]
    data_rows = max(sheet.max_row - 1, 0)
    assert data_rows == expected_data_rows, (
        f"Unexpected row count in {name}: "
        f"expected {expected_data_rows}, found {data_rows}"
    )
    assert sheet.max_column >= 1, f"No columns in {name}"

all_validated = load_workbook(
    out / "All_Validated_Data.xlsx", read_only=True, data_only=True
).active
all_headers = {
    cell.value for cell in next(all_validated.iter_rows(min_row=1, max_row=1))
}
for required in [
    "StartDate",
    "EndDate",
    "PO4P(mg/l)",
    "AS(mg/l)",
    "MO(mg/l)",
    "P(mg/l)",
    "S(mg/l)",
    "NING(mg/l)",
    "NDON(mg/l)",
]:
    assert required in all_headers, (
        f"Missing {required} in All_Validated_Data.xlsx"
    )

final_sheet = load_workbook(
    out / "Final_Data.xlsx", read_only=True, data_only=True
).active
final_headers = [
    cell.value for cell in next(final_sheet.iter_rows(min_row=1, max_row=1))
]
final_header_set = set(final_headers)

for required in [
    "SampleID",
    "program",
    "subprogram",
    "lis_tip",
    "PTOT (mg/l)",
    "STOT (mg/l)",
    "VOL (ml)",
    "Deposition K (kg/ha)",
    "Deposition PTOT (kg/ha)",
    "StartDate",
    "EndDate",
    "Precip(l/m2)",
    "AlkalinityICPForests(µeq/l)",
]:
    assert required in final_header_set, f"Missing {required} in Final_Data.xlsx"

for removed in [
    "date_1",
    "date_2",
    "Precipitation (mm)",
    "Alkalinity (mg/l)",
    "Deposition Alkalinity (kg/ha)",
    "q",
    "hg",
    "f",
    "cnr",
    "sio2",
    "ALL",
]:
    assert removed not in final_header_set, (
        f"Unexpected field {removed} in Final_Data.xlsx"
    )

# Every final SampleID must be an official SampleID from samplesInfo.xlsx.
def norm(value):
    return re.sub(r"[^A-Z0-9]", "", str(value).upper())

samples_sheet = load_workbook(samples_path, read_only=True, data_only=True).active
sample_headers = [
    cell.value for cell in next(samples_sheet.iter_rows(min_row=1, max_row=1))
]
sample_id_index = sample_headers.index("SampleID")
official_ids = {
    str(row[sample_id_index])
    for row in samples_sheet.iter_rows(min_row=2, values_only=True)
    if row[sample_id_index] not in (None, "")
}

sample_id_index_final = final_headers.index("SampleID")
final_ids = [
    row[sample_id_index_final]
    for row in final_sheet.iter_rows(min_row=2, values_only=True)
]
assert all(value in official_ids for value in final_ids), (
    "Final_Data.xlsx contains SampleID values not present in samplesInfo.xlsx"
)
assert "05PS INT" in final_ids, "Expected official SampleID '05PS INT'"
assert "05PS INT NIEVE" in final_ids, (
    "Expected official SampleID '05PS INT NIEVE'"
)

log_text = (out / "pipeline_execution.log").read_text(encoding="utf-8")
assert "Pipeline completed successfully." in log_text
assert "water_chemical_alldata_calculated.zip" not in "\n".join(
    line for line in log_text.splitlines() if line.startswith("Output:")
)
assert "water_chemical_alldata_validated.zip" not in "\n".join(
    line for line in log_text.splitlines() if line.startswith("Output:")
)

print("Pipeline unit test passed.")
PY
