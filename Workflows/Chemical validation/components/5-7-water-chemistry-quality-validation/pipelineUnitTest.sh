#!/usr/bin/env bash
set -euo pipefail

IMAGE_NAME="water-chemistry-quality-report:test"
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
INPUT_DIR="$ROOT_DIR/resources/example/data/inputs"
OUTPUT_DIR="$ROOT_DIR/resources/example/data/outputs"

rm -rf "$OUTPUT_DIR"
mkdir -p "$OUTPUT_DIR"
touch "$OUTPUT_DIR/.gitignore"

docker build -t "$IMAGE_NAME" "$ROOT_DIR"

docker run --rm \
  -v "$INPUT_DIR:/mnt/inputs:ro" \
  -v "$OUTPUT_DIR:/mnt/outputs" \
  "$IMAGE_NAME"

required=(
  water_chemical_data_level2_alldata.zip
  water_chemical_data_level2_validated.zip
  validation_report.pdf
  Samples2Repeat.xlsx
  All_Validated_Data.xlsx
  Final_Data.xlsx
  pipeline_execution.log
)

for file in "${required[@]}"; do
  test -s "$OUTPUT_DIR/$file" || { echo "Missing or empty output: $file"; exit 1; }
done

python - "$OUTPUT_DIR" <<'PY'
import sys, zipfile
from pathlib import Path
from openpyxl import load_workbook
out=Path(sys.argv[1])
for name in ["water_chemical_data_level2_alldata.zip","water_chemical_data_level2_validated.zip"]:
    with zipfile.ZipFile(out/name) as z:
        csvs=[n for n in z.namelist() if n.lower().endswith('.csv')]
        assert csvs, f"No CSV files in {name}"
for name in ["Samples2Repeat.xlsx","All_Validated_Data.xlsx","Final_Data.xlsx"]:
    wb=load_workbook(out/name, read_only=True)
    ws=wb[wb.sheetnames[0]]
    assert ws.max_row >= 1 and ws.max_column >= 1, f"Empty workbook: {name}"
print("Pipeline unit test passed.")
PY
