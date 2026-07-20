# -*- coding: utf-8 -*-
"""Coordinator for the original components 2, 3 and 4.

The scientific processing remains in three independent scripts under scripts/.
This file only prepares paths, forwards the LOQ parameters, executes the steps
in order, and publishes the final outputs.
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
WORK_ROOT = Path("/tmp/water_chemistry_preprocessing")
SCRIPT_ROOT = Path(__file__).resolve().parent / "scripts"

FINAL_ZIP = OUTPUT_ROOT / "water_chemical_data_level1_units.zip"
FINAL_LOQ_LOG = OUTPUT_ROOT / "loq_substitutions.log"
PIPELINE_LOG = OUTPUT_ROOT / "pipeline_execution.log"

LOQ_PARAMETERS: list[tuple[str, float]] = [
    ("param_WeightedConductivity", 3.0),
    ("param_NH4N", 0.04),
    ("param_NO3", 0.05),
    ("param_SO4", 0.1),
    ("param_CL", 0.05),
    ("param_AS", 0.000025),
    ("param_CD", 0.000008),
    ("param_CR", 0.000037),
    ("param_CU", 0.000062),
    ("param_CO", 0.000010),
    ("param_NI", 0.000073),
    ("param_PB", 0.000011),
    ("param_ZN", 0.000049),
    ("param_P", 0.016603),
    ("param_S", 0.5),
    ("param_CA", 0.15),
    ("param_K", 0.15),
    ("param_MG", 0.03),
    ("param_NA", 0.04),
    ("param_AL", 0.01),
    ("param_FE", 0.005),
    ("param_MN", 0.005),
    ("param_DOC", 0.5),
    ("param_TN", 0.1),
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Water chemistry preprocessing pipeline: template transformation, "
            "LOQ application and unit transformation"
        )
    )
    for name, default in LOQ_PARAMETERS:
        parser.add_argument(f"--{name}", type=float, default=default)
    return parser.parse_args()


def locate_input_zip() -> Path:
    """Locate the validated-data ZIP, including Tesseract's fixed mount path."""
    preferred = [
        INPUT_ROOT / "validated_data.zip",
        INPUT_ROOT / "allData_templates_format_validated.zip",
        INPUT_ROOT / "input_data",
    ]
    for candidate in preferred:
        if candidate.is_file() and zipfile.is_zipfile(candidate):
            return candidate

    zip_candidates = [
        path
        for path in sorted(INPUT_ROOT.rglob("*"))
        if path.is_file() and zipfile.is_zipfile(path)
    ]
    if len(zip_candidates) == 1:
        return zip_candidates[0]
    if not zip_candidates:
        raise RuntimeError("No ZIP input was found under /mnt/inputs")
    raise RuntimeError(
        "Several ZIP inputs were found under /mnt/inputs; expected one validated-data ZIP: "
        + ", ".join(path.name for path in zip_candidates)
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

    command = [sys.executable, str(script), *arguments]
    process = subprocess.Popen(
        command,
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
    input_zip = locate_input_zip()

    if WORK_ROOT.exists():
        shutil.rmtree(WORK_ROOT)
    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)
    WORK_ROOT.mkdir(parents=True, exist_ok=True)

    step2_root = WORK_ROOT / "step2_transformation"
    step3_root = WORK_ROOT / "step3_loq"
    step4_root = WORK_ROOT / "step4_units"
    for directory in (step2_root, step3_root, step4_root):
        directory.mkdir(parents=True, exist_ok=True)

    step2_zip = step2_root / "water_chemical_data_level1.zip"
    step3_zip = step3_root / "water_chemical_data_level1_loq.zip"
    step3_log = step3_root / "level1_loq" / "loq_substitutions.log"

    with PIPELINE_LOG.open("w", encoding="utf-8") as log:
        write_log_line(
            log,
            "WATER CHEMISTRY PREPROCESSING — "
            + datetime.now().isoformat(sep=" ", timespec="seconds"),
        )
        write_log_line(log, f"Input ZIP: {input_zip}")

        run_step(
            title="STEP 2 — WATER CHEMICAL DATA TRANSFORMATION",
            script=SCRIPT_ROOT / "data_transformation.py",
            environment={
                "INPUT_ZIP_PATH": str(input_zip),
                "OUTPUT_DIR": str(step2_root / "level1"),
                "OUTPUT_ZIP_PATH": str(step2_zip),
                "EXTRACT_DIR": str(step2_root / "extracted_input"),
            },
            arguments=[],
            log_handle=log,
        )
        require_file(step2_zip, "Step 2 output ZIP")

        loq_arguments: list[str] = []
        for name, _ in LOQ_PARAMETERS:
            loq_arguments.extend([f"--{name}", str(getattr(args, name))])

        run_step(
            title="STEP 3 — LABORATORY QUANTIFICATION LIMIT APPLICATION",
            script=SCRIPT_ROOT / "laboratory_loq_application.py",
            environment={
                "INPUT_ZIP_PATH": str(step2_zip),
                "OUTPUT_DIR": str(step3_root / "level1_loq"),
                "OUTPUT_ZIP_PATH": str(step3_zip),
                "OUTPUT_LOG_PATH": str(step3_log),
                "EXTRACT_DIR": str(step3_root / "extracted_input"),
            },
            arguments=loq_arguments,
            log_handle=log,
        )
        require_file(step3_zip, "Step 3 output ZIP")
        require_file(step3_log, "LOQ substitution log")

        run_step(
            title="STEP 4 — WATER CHEMISTRY UNIT TRANSFORMATION",
            script=SCRIPT_ROOT / "unit_transformation.py",
            environment={
                "INPUT_ZIP_PATH": str(step3_zip),
                "OUTPUT_DIR": str(step4_root / "level1_units"),
                "OUTPUT_ZIP_PATH": str(FINAL_ZIP),
                "EXTRACT_DIR": str(step4_root / "extracted_input"),
            },
            arguments=[],
            log_handle=log,
        )
        require_file(FINAL_ZIP, "Final unit-transformed ZIP")

        shutil.copy2(step3_log, FINAL_LOQ_LOG)
        require_file(FINAL_LOQ_LOG, "Published LOQ substitution log")

        write_log_line(log, "")
        write_log_line(log, "Pipeline completed successfully.")
        write_log_line(log, f"Final ZIP: {FINAL_ZIP}")
        write_log_line(log, f"LOQ log: {FINAL_LOQ_LOG}")

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
