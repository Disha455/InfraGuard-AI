"""
InfraGuard AI
Computer Vision — Dataset Preparation Orchestrator

Purpose:
    Single entry-point that runs the complete dataset preparation pipeline
    from download through to verification.  The user only needs to run
    this one script.

Pipeline:
    [1] download_dataset   — download RDD2022 from Kaggle → data/raw/
    [2] inspect_dataset    — print a report of the raw dataset (read-only)
    [3] filter_classes     — remove other_corruption, remap IDs → data/processed/
    [4] verify_dataset     — integrity checks; exits non-zero on failure

Input:
    Kaggle credentials (~/.kaggle/kaggle.json or env vars).

Output:
    data/raw/                        — extracted original dataset
    data/processed/<split>/labels/   — filtered + remapped YOLO labels
    data/processed/dataset.yaml      — Ultralytics training config

Execution:
    # From ai/computer_vision/
    python prepare_dataset.py

Each individual stage script can still be run independently:
    python -m preprocessing.download_dataset
    python -m preprocessing.inspect_dataset
    python -m preprocessing.filter_classes
    python -m preprocessing.verify_dataset
"""

import sys
import time
from pathlib import Path

from configs.config import (
    CLASS_NAMES,
    DATASET_NAME,
    DATASET_YAML,
    PROCESSED_DATASET,
    RAW_DATASET,
)
from preprocessing.download_dataset import download_dataset
from preprocessing.filter_classes import filter_classes
from preprocessing.inspect_dataset import inspect_dataset
from preprocessing.verify_dataset import verify_dataset
from utils.utils import get_logger, print_section, print_separator

# ---------------------------------------------------------------------------
# Module logger
# ---------------------------------------------------------------------------

logger = get_logger(__name__)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _format_elapsed(seconds: float) -> str:
    """Return a human-readable elapsed time string."""
    if seconds < 60:
        return f"{seconds:.1f}s"
    minutes, secs = divmod(int(seconds), 60)
    return f"{minutes}m {secs}s"


def _print_final_summary(
    processed_dir: Path,
    yaml_path: Path,
    elapsed: float,
    verification_passed: bool,
) -> None:
    """Print the final pipeline summary block."""
    print_section("Preparation Complete")
    print(f"  Dataset          : {DATASET_NAME}")
    print(f"  Classes          : {len(CLASS_NAMES)}  →  {CLASS_NAMES}")
    print(f"  Raw data         : {RAW_DATASET}")
    print(f"  Processed labels : {processed_dir}")
    print(f"  dataset.yaml     : {yaml_path}")
    print(f"  Total time       : {_format_elapsed(elapsed)}")
    print()

    if verification_passed:
        print("  Status  : READY FOR TRAINING")
        print()
        print("  Next step:")
        print(f"    yolo train data={yaml_path} model=yolov8n.pt epochs=50")
    else:
        print("  Status  : VERIFICATION FAILED")
        print("  Fix the issues reported above before starting training.")

    print_separator()


# ---------------------------------------------------------------------------
# Orchestrator
# ---------------------------------------------------------------------------

def prepare_dataset(
    *,
    skip_if_exists: bool = True,
    keep_zip: bool = False,
) -> bool:
    """
    Run the full dataset preparation pipeline end-to-end.

    Stages:
        1. Download  — fetch from Kaggle (skipped if already present).
        2. Inspect   — print raw dataset report.
        3. Filter    — remove other_corruption, remap class IDs.
        4. Verify    — integrity checks on processed labels.

    Args:
        skip_if_exists: Pass-through to each stage.  When ``True``, stages
                        that have already produced their output are skipped
                        so the pipeline can be safely re-run.
        keep_zip:       Whether to keep the downloaded archive after
                        extraction.  Defaults to ``False``.

    Returns:
        ``True`` if the pipeline completed and verification passed,
        ``False`` otherwise.
    """
    pipeline_start = time.time()

    print_section(f"InfraGuard AI — {DATASET_NAME} Dataset Preparation")
    print(f"  Raw dir      : {RAW_DATASET}")
    print(f"  Processed dir: {PROCESSED_DATASET}")
    print(f"  dataset.yaml : {DATASET_YAML}")
    print(f"  Classes      : {CLASS_NAMES}")
    print_separator()

    # ------------------------------------------------------------------
    # Stage 1 — Download
    # ------------------------------------------------------------------
    stage_start = time.time()
    print()
    logger.info("STAGE 1/4 — Download")

    try:
        download_dataset(
            destination=RAW_DATASET,
            keep_zip=keep_zip,
            skip_if_exists=skip_if_exists,
        )
    except Exception as exc:
        logger.error("Download failed: %s", exc)
        logger.error("Ensure ~/.kaggle/kaggle.json is present and valid.")
        return False

    logger.info("Stage 1 complete  (%s)", _format_elapsed(time.time() - stage_start))

    # ------------------------------------------------------------------
    # Stage 2 — Inspect
    # ------------------------------------------------------------------
    stage_start = time.time()
    print()
    logger.info("STAGE 2/4 — Inspect")

    try:
        inspect_dataset(raw_dir=RAW_DATASET)
    except FileNotFoundError as exc:
        logger.error("Inspection failed: %s", exc)
        return False

    logger.info("Stage 2 complete  (%s)", _format_elapsed(time.time() - stage_start))

    # ------------------------------------------------------------------
    # Stage 3 — Filter classes
    # ------------------------------------------------------------------
    stage_start = time.time()
    print()
    logger.info("STAGE 3/4 — Filter Classes")

    try:
        filter_classes(
            raw_dir=RAW_DATASET,
            processed_dir=PROCESSED_DATASET,
            yaml_path=DATASET_YAML,
            skip_if_exists=skip_if_exists,
        )
    except FileNotFoundError as exc:
        logger.error("Filtering failed: %s", exc)
        return False

    logger.info("Stage 3 complete  (%s)", _format_elapsed(time.time() - stage_start))

    # ------------------------------------------------------------------
    # Stage 4 — Verify
    # ------------------------------------------------------------------
    stage_start = time.time()
    print()
    logger.info("STAGE 4/4 — Verify")

    verification_passed = verify_dataset(
        processed_dir=PROCESSED_DATASET,
        raw_dir=RAW_DATASET,
        class_names=CLASS_NAMES,
        yaml_path=DATASET_YAML,
    )

    logger.info("Stage 4 complete  (%s)", _format_elapsed(time.time() - stage_start))

    # ------------------------------------------------------------------
    # Final summary
    # ------------------------------------------------------------------
    total_elapsed = time.time() - pipeline_start
    _print_final_summary(PROCESSED_DATASET, DATASET_YAML, total_elapsed, verification_passed)

    return verification_passed


# ---------------------------------------------------------------------------
# CLI entry-point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    success = prepare_dataset()
    sys.exit(0 if success else 1)
