#!/usr/bin/env bash
set -euo pipefail

IMAGE_NAME="lw-water-chemistry-preprocessing"
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
INPUT_DIR="$ROOT_DIR/resources/example/data/inputs"
OUTPUT_DIR="$ROOT_DIR/resources/example/data/outputs/test-run"

rm -rf "$OUTPUT_DIR"
mkdir -p "$OUTPUT_DIR"

docker build -t "$IMAGE_NAME" "$ROOT_DIR"

docker run --rm \
  -v "$INPUT_DIR/validated_data.zip:/mnt/inputs/validated_data.zip:ro" \
  -v "$OUTPUT_DIR:/mnt/outputs" \
  "$IMAGE_NAME"

python - "$OUTPUT_DIR" <<'PY'
import sys
from pathlib import Path
from zipfile import ZipFile

output = Path(sys.argv[1])
final_zip = output / "water_chemical_data_level1_units.zip"
loq_log = output / "loq_substitutions.log"
pipeline_log = output / "pipeline_execution.log"

for path in (final_zip, loq_log, pipeline_log):
    if not path.is_file() or path.stat().st_size == 0:
        raise SystemExit(f"Missing or empty expected output: {path}")

with ZipFile(final_zip) as archive:
    csv_files = [name for name in archive.namelist() if name.lower().endswith(".csv")]
    bad = archive.testzip()

if bad is not None:
    raise SystemExit(f"Corrupted file inside final ZIP: {bad}")
if len(csv_files) != 84:
    raise SystemExit(f"Expected 84 CSV files, found {len(csv_files)}")

header = loq_log.read_text(encoding="utf-8").splitlines()[0]
if header != "FILE\tROW\tCOLUMN\tORIGINAL_VALUE\tLOQ\tREPLACED_BY":
    raise SystemExit("Unexpected LOQ log header")

print("Unit test passed: three stages completed and 84 CSV files were generated.")
PY
