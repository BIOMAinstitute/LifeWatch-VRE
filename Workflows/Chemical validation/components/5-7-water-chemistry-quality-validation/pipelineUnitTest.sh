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

SYNTH_INPUT_DIR="$ROOT_DIR/resources/example/synthetic-final-data/inputs"
SYNTH_OUTPUT_DIR="$ROOT_DIR/resources/example/synthetic-final-data/outputs"
rm -rf "$SYNTH_OUTPUT_DIR"
mkdir -p "$SYNTH_OUTPUT_DIR"

docker run --rm \
  --entrypoint python \
  -e INPUT_DATA_PATH=/mnt/synthetic/inputs/All_Validated_Data.xlsx \
  -e INPUT_SAMPLES_PATH=/mnt/synthetic/inputs/samplesInfo.xlsx \
  -e OUTPUT_PATH=/mnt/synthetic/outputs/Final_Data.xlsx \
  -v "$SYNTH_INPUT_DIR:/mnt/synthetic/inputs:ro" \
  -v "$SYNTH_OUTPUT_DIR:/mnt/synthetic/outputs" \
  "$IMAGE_NAME" \
  /app/scripts/data2final_report.py

required=(
  water_chemical_alldata_calculated.zip
  water_chemical_alldata_validated.zip
  validation_report.pdf
  Samples2Repeat.xlsx
  All_Validated_Data.xlsx
  Final_Data.xlsx
  pipeline_execution.log
)

for file in "${required[@]}"; do
  test -s "$OUTPUT_DIR/$file" || { echo "Missing or empty output: $file"; exit 1; }
done

python - "$OUTPUT_DIR" "$SYNTH_OUTPUT_DIR" <<'PY'
import sys
import zipfile
from pathlib import Path
from openpyxl import load_workbook

out = Path(sys.argv[1])
synth_out = Path(sys.argv[2])

for name in [
    "water_chemical_alldata_calculated.zip",
    "water_chemical_alldata_validated.zip",
]:
    with zipfile.ZipFile(out / name) as archive:
        assert archive.testzip() is None, f"Corrupt member in {name}"
        csvs = [n for n in archive.namelist() if n.lower().endswith(".csv")]
        assert len(csvs) == 14, f"Expected 14 CSV files in {name}, found {len(csvs)}"

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
        f"Unexpected row count in {name}: expected {expected_data_rows}, found {data_rows}"
    )
    assert sheet.max_column >= 1, f"No columns in {name}"

all_validated = load_workbook(
    out / "All_Validated_Data.xlsx", read_only=True, data_only=True
).active
all_headers = {cell.value for cell in next(all_validated.iter_rows(min_row=1, max_row=1))}
for required in [
    "StartDate", "EndDate", "PO4P(mg/l)", "AS(mg/l)", "MO(mg/l)",
    "P(mg/l)", "S(mg/l)", "NING(mg/l)", "NDON(mg/l)",
]:
    assert required in all_headers, f"Missing {required} in All_Validated_Data.xlsx"

final_data = load_workbook(
    out / "Final_Data.xlsx", read_only=True, data_only=True
).active
final_headers = {cell.value for cell in next(final_data.iter_rows(min_row=1, max_row=1))}
for required in [
    "program", "subprogram", "lis_tip", "PTOT (mg/l)", "STOT (mg/l)",
    "VOL (ml)", "q", "hg", "f", "cnr", "sio2", "ALL",
    "Deposition K (kg/ha)", "Deposition PTOT (kg/ha)",
]:
    assert required in final_headers, f"Missing {required} in Final_Data.xlsx"
for removed in [
    "date_1", "date_2", "Precipitation (mm)",
    "Alkalinity (mg/l)", "Deposition Alkalinity (kg/ha)",
]:
    assert removed not in final_headers, f"Unexpected duplicate/unsupported field {removed}"
for retained in [
    "StartDate", "EndDate", "Precip(l/m2)",
    "AlkalinityICPForests(µeq/l)",
]:
    assert retained in final_headers, f"Missing canonical field {retained}"

synthetic = load_workbook(
    synth_out / "Final_Data.xlsx", read_only=True, data_only=True
).active
headers = [cell.value for cell in next(synthetic.iter_rows(min_row=1, max_row=1))]
rows = list(synthetic.iter_rows(min_row=2, values_only=True))
records = [dict(zip(headers, row)) for row in rows]
assert len(records) == 2
open_field = next(row for row in records if row["subprogram"] == "PC")
soil_water = next(row for row in records if row["subprogram"] == "SW")
assert abs(open_field["NING (mg/l)"] - 0.3) < 1e-12
assert abs(open_field["NDON (mg/l)"] - 0.7) < 1e-12
assert abs(open_field["PTOT (mg/l)"] - 1.5) < 1e-12
assert abs(open_field["STOT (mg/l)"] - 5.0) < 1e-12
assert abs(open_field["Deposition K (kg/ha)"] - 2.0) < 1e-12
assert abs(open_field["Deposition PTOT (kg/ha)"] - 1.5) < 1e-12
assert soil_water["lis_tip"] == "LISIM-20"
assert abs(soil_water["VOL (ml)"] - 50.0) < 1e-12
assert soil_water["Deposition K (kg/ha)"] is None

log_text = (out / "pipeline_execution.log").read_text(encoding="utf-8")
assert "Pipeline completed successfully." in log_text
print("Pipeline unit test passed.")
PY
