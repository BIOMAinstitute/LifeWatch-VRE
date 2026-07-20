# -*- coding: utf-8 -*-
"""Coordinator for the original water chemistry components 5, 6 and 7.

The scientific logic remains in three independent scripts under scripts/.
This coordinator only resolves inputs, forwards the original validation
parameters, runs the stages in sequence and verifies/publishes their outputs.
"""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
import zipfile
from datetime import datetime
from pathlib import Path

INPUT_ROOT = Path("/mnt/inputs")
OUTPUT_ROOT = Path("/mnt/outputs")
WORK_ROOT = Path("/tmp/water_chemistry_quality_report")
SCRIPT_ROOT = Path(__file__).resolve().parent / "scripts"

OUTPUT_ALLDATA_ZIP = OUTPUT_ROOT / "water_chemical_data_level2_alldata.zip"
OUTPUT_VALIDATED_ZIP = OUTPUT_ROOT / "water_chemical_data_level2_validated.zip"
OUTPUT_PDF = OUTPUT_ROOT / "validation_report.pdf"
OUTPUT_REPEAT = OUTPUT_ROOT / "Samples2Repeat.xlsx"
OUTPUT_ALL = OUTPUT_ROOT / "All_Validated_Data.xlsx"
OUTPUT_FINAL = OUTPUT_ROOT / "Final_Data.xlsx"
PIPELINE_LOG = OUTPUT_ROOT / "pipeline_execution.log"

QUALITY_PARAMETERS: list[tuple[str, float]] = [
    ("param_ionsdiff_low_k", 20.0),
    ("param_ionsdiff_high_k", 10.0),
    ("param_conddiff_low_1", 30.0),
    ("param_conddiff_low_2", 20.0),
    ("param_conddiff_high", 10.0),
    ("param_ratio_nacl_low", 0.5),
    ("param_ratio_nacl_high", 1.5),
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Water chemistry quality pipeline: chemical validation, validation "
            "report generation and final data selection"
        )
    )
    for name, default in QUALITY_PARAMETERS:
        parser.add_argument(f"--{name}", type=float, default=default)
    return parser.parse_args()


def is_data_zip(path: Path) -> bool:
    """Detect a real data ZIP without confusing XLSX files with ZIP archives."""
    if not path.is_file():
        return False

    # Normal ZIP input with an explicit .zip extension.
    if path.suffix.casefold() == ".zip":
        return zipfile.is_zipfile(path)

    # Tesseract may mount a generic Bin input without an extension.
    if path.name == "input_data" and zipfile.is_zipfile(path):
        try:
            with zipfile.ZipFile(path, "r") as archive:
                names = set(archive.namelist())

            # XLSX/XLSM files are also ZIP containers, so exclude Excel workbooks.
            is_excel_workbook = (
                "[Content_Types].xml" in names
                and any(
                    name in names
                    for name in ("xl/workbook.xml", "xl/workbook.bin")
                )
            )

            return not is_excel_workbook

        except (OSError, zipfile.BadZipFile):
            return False

    return False


def locate_units_zip() -> Path:
    preferred = [
        INPUT_ROOT / "water_chemical_data_level1_units.zip",
        INPUT_ROOT / "input_data",
    ]

    for candidate in preferred:
        if is_data_zip(candidate):
            return candidate

    candidates = [
        path
        for path in sorted(INPUT_ROOT.rglob("*"))
        if is_data_zip(path)
    ]

    if len(candidates) == 1:
        return candidates[0]

    if not candidates:
        raise RuntimeError(
            "No unit-transformed ZIP input was found under /mnt/inputs"
        )

    raise RuntimeError(
        "Several ZIP inputs were found; expected one unit-transformed data ZIP: "
        + ", ".join(path.name for path in candidates)
    )


def locate_samples_file() -> Path:
    preferred = INPUT_ROOT / "samplesInfo.xlsx"
    if preferred.is_file():
        return preferred

    candidates = [
        p for p in sorted(INPUT_ROOT.rglob("*.xlsx"))
        if p.is_file() and "sample" in p.name.casefold()
    ]
    if len(candidates) == 1:
        return candidates[0]
    if not candidates:
        raise RuntimeError("samplesInfo.xlsx was not found under /mnt/inputs")
    raise RuntimeError(
        "Several possible samples-information files were found: "
        + ", ".join(p.name for p in candidates)
    )


def write_log_line(handle, text: str) -> None:
    print(text, flush=True)
    handle.write(text + "\n")
    handle.flush()


def run_step(
    *,
    title: str,
    script: Path,
    environment: dict[str, str],
    arguments: list[str],
    log_handle,
) -> None:
    write_log_line(log_handle, "")
    write_log_line(log_handle, "=" * 78)
    write_log_line(log_handle, title)
    write_log_line(log_handle, "=" * 78)

    env = os.environ.copy()
    env.update(environment)
    env["PYTHONUNBUFFERED"] = "1"

    process = subprocess.Popen(
        [sys.executable, str(script), *arguments],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="replace",
        env=env,
    )
    assert process.stdout is not None
    for line in process.stdout:
        write_log_line(log_handle, line.rstrip("\n"))

    return_code = process.wait()
    if return_code != 0:
        raise RuntimeError(f"{title} failed with exit code {return_code}")


def require_file(path: Path, label: str) -> None:
    if not path.is_file() or path.stat().st_size == 0:
        raise RuntimeError(f"{label} was not generated correctly: {path}")


def main() -> int:
    args = parse_args()
    input_zip = locate_units_zip()
    samples_file = locate_samples_file()

    if WORK_ROOT.exists():
        shutil.rmtree(WORK_ROOT)
    WORK_ROOT.mkdir(parents=True, exist_ok=True)
    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)

    step5_root = WORK_ROOT / "step5_quality_validation"
    step6_root = WORK_ROOT / "step6_validation_report"
    step7_root = WORK_ROOT / "step7_final_selection"
    for directory in (step5_root, step6_root, step7_root):
        directory.mkdir(parents=True, exist_ok=True)

    with PIPELINE_LOG.open("w", encoding="utf-8") as log:
        write_log_line(
            log,
            "WATER CHEMISTRY QUALITY AND REPORT PIPELINE — "
            + datetime.now().isoformat(sep=" ", timespec="seconds"),
        )
        write_log_line(log, f"Input data ZIP: {input_zip}")
        write_log_line(log, f"Samples information: {samples_file}")

        quality_arguments: list[str] = []
        for name, _ in QUALITY_PARAMETERS:
            quality_arguments.extend([f"--{name}", str(getattr(args, name))])

        run_step(
            title="STEP 5 — WATER CHEMISTRY SAMPLES QUALITY VALIDATION",
            script=SCRIPT_ROOT / "chemical_quality_validation.py",
            environment={
                "INPUT_ZIP_PATH": str(input_zip),
                "INPUT_SAMPLES_PATH": str(samples_file),
                "OUTPUT_ALLDATA_DIR": str(step5_root / "level2_alldata"),
                "OUTPUT_VALIDATED_DIR": str(step5_root / "level2_validated"),
                "OUTPUT_ALLDATA_ZIP": str(OUTPUT_ALLDATA_ZIP),
                "OUTPUT_VALIDATED_ZIP": str(OUTPUT_VALIDATED_ZIP),
                "EXTRACT_DIR": str(step5_root / "extracted_input"),
            },
            arguments=quality_arguments,
            log_handle=log,
        )
        require_file(OUTPUT_ALLDATA_ZIP, "Merged allData ZIP")
        require_file(OUTPUT_VALIDATED_ZIP, "Validated data ZIP")

        run_step(
            title="STEP 6 — CHEMISTRY QUALITY VALIDATED REPORT",
            script=SCRIPT_ROOT / "validation_report.py",
            environment={
                "INPUT_ZIP_PATH": str(OUTPUT_VALIDATED_ZIP),
                "INPUT_SAMPLES_PATH": str(samples_file),
                "OUTPUT_PDF_PATH": str(OUTPUT_PDF),
                "OUTPUT_REPEAT_PATH": str(OUTPUT_REPEAT),
                "OUTPUT_ALL_PATH": str(OUTPUT_ALL),
                "EXTRACT_DIR": str(step6_root / "extracted_input"),
                "CHARTS_DIR": str(step6_root / "charts"),
            },
            arguments=[],
            log_handle=log,
        )
        require_file(OUTPUT_PDF, "Validation report PDF")
        require_file(OUTPUT_REPEAT, "Samples-to-repeat Excel")
        require_file(OUTPUT_ALL, "All validated data Excel")

        run_step(
            title="STEP 7 — SELECT DATA FOR FINAL REPORT",
            script=SCRIPT_ROOT / "data2final_report.py",
            environment={
                "INPUT_DATA_PATH": str(OUTPUT_ALL),
                "INPUT_SAMPLES_PATH": str(samples_file),
                "OUTPUT_PATH": str(OUTPUT_FINAL),
            },
            arguments=[],
            log_handle=log,
        )
        require_file(OUTPUT_FINAL, "Final report data Excel")

        write_log_line(log, "")
        write_log_line(log, "Pipeline completed successfully.")
        for output in (
            OUTPUT_ALLDATA_ZIP,
            OUTPUT_VALIDATED_ZIP,
            OUTPUT_PDF,
            OUTPUT_REPEAT,
            OUTPUT_ALL,
            OUTPUT_FINAL,
        ):
            write_log_line(log, f"Output: {output}")

    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as exc:
        OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)
        message = f"Pipeline failed ({type(exc).__name__}: {exc})"
        print(f"❌ {message}", file=sys.stderr)
        with PIPELINE_LOG.open("a", encoding="utf-8") as log:
            log.write("\n❌ " + message + "\n")
        sys.exit(1)