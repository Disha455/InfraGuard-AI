"""
InfraGuard AI
Computer Vision — Dataset Verification

Purpose:
    Confirm the filtered dataset is structurally sound before training begins.

Input:
    data/raw/<split>/images/         — original images (existence check only)
    data/processed/<split>/labels/   — filtered + remapped label files
    data/processed/dataset.yaml      — Ultralytics training config

Output:
    Pass / fail report printed to stdout.
    Exit code 0 on success, 1 on any hard failure (CI-compatible).

Responsibilities:
    1. Verify all expected split directories exist in data/processed/.
    2. Cross-check: every processed label has a corresponding raw image,
       resolving the actual dataset root to handle Kaggle wrapper folders
       (e.g. raw/RDD_SPLIT/) exactly as filter_classes.py does.
    3. Confirm all class IDs are within the valid range [0, n_classes - 1].
    4. Warn (non-fatal) if any label file is empty.
    5. Verify dataset.yaml exists at the configured path.

Note on class ID 3:
    After remapping, class ID 3 maps to ``alligator_crack`` and is a
    fully valid processed-label class.  Checking for "removed class
    residue" by numeric ID would produce false positives for every
    alligator_crack annotation, so that check is intentionally absent.
    Responsibility 3 (valid ID range) already catches any genuine remap
    failure by asserting all IDs fall within [0, n_classes-1].

Execution:
    # From ai/computer_vision/
    python -m preprocessing.verify_dataset
"""

import logging
import sys
from dataclasses import dataclass, field
from pathlib import Path

from configs.config import (
    CLASS_NAMES,
    DATASET_YAML,
    PROCESSED_DATASET,
    RAW_DATASET,
    SPLITS,
)
from utils.utils import (
    IMAGE_EXTENSIONS,
    get_class_ids,
    get_logger,
    list_labels,
    print_section,
    print_separator,
)

# ---------------------------------------------------------------------------
# Module logger
# ---------------------------------------------------------------------------

logger: logging.Logger = get_logger(__name__)


# ---------------------------------------------------------------------------
# Result container
# ---------------------------------------------------------------------------

@dataclass
class CheckResult:
    """Outcome of one verification check."""
    name: str
    passed: bool
    message: str = ""
    warnings: list[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Dataset root resolution
# ---------------------------------------------------------------------------

def _resolve_raw_root(raw_dir: Path) -> Path | None:
    """
    Locate the actual split root inside *raw_dir*.

    Kaggle sometimes extracts the archive into a sub-folder (e.g.
    ``raw/RDD_SPLIT/`` or ``raw/rdd2022/``).  This function checks
    *raw_dir* itself first, then one level deeper, mirroring the logic
    in :func:`filter_classes._resolve_raw_root`.

    Args:
        raw_dir: Configured ``RAW_DATASET`` path.

    Returns:
        Resolved dataset root that contains the expected split directories,
        or ``None`` if neither *raw_dir* nor any immediate child qualifies.
    """
    if any((raw_dir / s).exists() for s in SPLITS):
        return raw_dir

    if raw_dir.exists():
        for candidate in sorted(raw_dir.iterdir()):
            if candidate.is_dir() and any(
                (candidate / s).exists() for s in SPLITS
            ):
                return candidate

    return None


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _find_raw_image(label_path: Path, raw_split_images_dir: Path) -> bool:
    """
    Return ``True`` if any image file with the same stem as *label_path*
    exists in *raw_split_images_dir*.

    Args:
        label_path:           Path to a processed ``.txt`` label file.
        raw_split_images_dir: ``<dataset_root>/<split>/images/`` directory.

    Returns:
        Boolean — ``True`` means a matching raw image was found.
    """
    stem = label_path.stem
    for ext in IMAGE_EXTENSIONS:
        if (raw_split_images_dir / f"{stem}{ext}").exists():
            return True
    return False


# ---------------------------------------------------------------------------
# Individual checks
# ---------------------------------------------------------------------------

def _check_splits_exist(processed_dir: Path) -> CheckResult:
    """All expected split label directories must be present in processed/."""
    missing = [
        s for s in SPLITS
        if not (processed_dir / s / "labels").exists()
    ]
    if missing:
        return CheckResult(
            name="Split label dirs exist",
            passed=False,
            message=f"Missing splits in processed/: {missing}",
        )
    return CheckResult(name="Split label dirs exist", passed=True)


def _check_label_image_alignment(
    processed_dir: Path,
    raw_dir: Path,
) -> CheckResult:
    """
    Every processed label must have a corresponding raw image.

    Uses :func:`_resolve_raw_root` to locate the actual split root inside
    *raw_dir* before building image paths.  This handles Kaggle wrapper
    folders (e.g. ``raw/RDD_SPLIT/``) identically to
    :func:`filter_classes.filter_classes`.

    Args:
        processed_dir: Root of the processed dataset.
        raw_dir:       Configured ``RAW_DATASET`` path (may contain a
                       wrapper sub-folder).

    Returns:
        :class:`CheckResult` — passes when every label has a matching image.
    """
    # Resolve the actual split root — handles Kaggle sub-folder extraction
    dataset_root = _resolve_raw_root(raw_dir)

    if dataset_root is None:
        return CheckResult(
            name="Labels have matching raw images",
            passed=False,
            message=(
                f"Cannot locate split directories inside '{raw_dir}'. "
                "Run download_dataset.py first."
            ),
        )

    logger.info(
        "Image alignment check using dataset root: %s", dataset_root
    )

    missing_images: list[str] = []

    for split_name in SPLITS:
        labels_dir = processed_dir / split_name / "labels"
        raw_images_dir = dataset_root / split_name / "images"

        if not labels_dir.exists():
            continue

        if not raw_images_dir.exists():
            missing_images.append(
                f"{split_name}/ — raw images directory not found: "
                f"{raw_images_dir}"
            )
            continue

        for label_path in list_labels(labels_dir):
            if not _find_raw_image(label_path, raw_images_dir):
                missing_images.append(f"{split_name}/{label_path.name}")

    if missing_images:
        preview = [f"  No raw image for: {p}" for p in missing_images[:10]]
        if len(missing_images) > 10:
            preview.append(f"  … and {len(missing_images) - 10} more.")
        return CheckResult(
            name="Labels have matching raw images",
            passed=False,
            message=f"{len(missing_images)} label(s) have no matching image in raw/.",
            warnings=preview,
        )
    return CheckResult(name="Labels have matching raw images", passed=True)


def _check_valid_class_ids(processed_dir: Path, n_classes: int) -> CheckResult:
    """
    All class IDs in processed labels must be in the range
    ``[0, n_classes - 1]``.

    This is the single authoritative check for remap correctness.
    For a 4-class project the valid IDs are 0, 1, 2, 3 — including 3
    (``alligator_crack``), which is a fully valid post-remap class.

    Args:
        processed_dir: Root of the processed dataset.
        n_classes:     Number of classes after filtering
                       (``len(CLASS_NAMES)``).

    Returns:
        :class:`CheckResult` — passes when every annotation uses a
        valid class ID.
    """
    valid = set(range(n_classes))
    violations: list[str] = []

    for split_name in SPLITS:
        labels_dir = processed_dir / split_name / "labels"
        for label_path in list_labels(labels_dir):
            invalid = get_class_ids(label_path) - valid
            if invalid:
                violations.append(
                    f"{split_name}/{label_path.name}: invalid IDs {sorted(invalid)}"
                )

    if violations:
        preview = [f"  {v}" for v in violations[:10]]
        if len(violations) > 10:
            preview.append(f"  … and {len(violations) - 10} more.")
        return CheckResult(
            name="Valid class IDs only",
            passed=False,
            message=f"{len(violations)} label(s) contain out-of-range class IDs.",
            warnings=preview,
        )
    return CheckResult(name="Valid class IDs only", passed=True)


def _check_no_empty_labels(processed_dir: Path) -> CheckResult:
    """
    Warn (non-fatal) if any label files are empty after filtering.

    Empty labels are valid for background images but unexpected in a road
    damage dataset — flag them for manual review.

    Args:
        processed_dir: Root of the processed dataset.

    Returns:
        :class:`CheckResult` — always passes (warning only).
    """
    empty: list[str] = []

    for split_name in SPLITS:
        labels_dir = processed_dir / split_name / "labels"
        for label_path in list_labels(labels_dir):
            if not label_path.read_text(encoding="utf-8").strip():
                empty.append(f"{split_name}/{label_path.name}")

    warnings: list[str] = []
    if empty:
        warnings.append(
            f"{len(empty)} empty label file(s) — images have no valid annotations."
        )
        warnings.extend(f"  {p}" for p in empty[:10])
        if len(empty) > 10:
            warnings.append(f"  … and {len(empty) - 10} more.")

    return CheckResult(
        name="No empty labels  (warning only)",
        passed=True,    # warning, not a hard failure
        warnings=warnings,
    )


def _check_dataset_yaml(yaml_path: Path) -> CheckResult:
    """
    ``dataset.yaml`` must exist at the configured path.

    Args:
        yaml_path: Expected path of ``dataset.yaml``.

    Returns:
        :class:`CheckResult`.
    """
    if not yaml_path.exists():
        return CheckResult(
            name="dataset.yaml present",
            passed=False,
            message=(
                f"'{yaml_path}' not found.\n"
                "    Run filter_classes.py to generate it."
            ),
        )
    return CheckResult(name="dataset.yaml present", passed=True)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def verify_dataset(
    processed_dir: Path = PROCESSED_DATASET,
    raw_dir: Path = RAW_DATASET,
    class_names: list[str] = CLASS_NAMES,
    yaml_path: Path = DATASET_YAML,
) -> bool:
    """
    Run all integrity checks and print a pass / fail report.

    Args:
        processed_dir: Directory containing filtered labels and dataset.yaml.
                       Defaults to ``PROCESSED_DATASET`` from ``config.py``.
        raw_dir:       Directory containing the original dataset, passed to
                       :func:`_resolve_raw_root` to handle Kaggle wrapper
                       sub-folders before image path construction.
                       Defaults to ``RAW_DATASET`` from ``config.py``.
        class_names:   Ordered list of class names (used to derive n_classes).
        yaml_path:     Expected path of ``dataset.yaml``.

    Returns:
        ``True`` if all hard checks pass, ``False`` otherwise.
        Warnings (empty labels) do not count as failures.
    """
    print_section("Dataset Verification")

    if not processed_dir.exists():
        logger.error(
            "Processed dataset directory not found: '%s'\n"
            "Run filter_classes.py first.",
            processed_dir,
        )
        return False

    n_classes = len(class_names)
    logger.info("Processed dir  : %s", processed_dir)
    logger.info("Raw dir        : %s", raw_dir)
    logger.info("Expected classes (%d): %s", n_classes, class_names)

    # ------------------------------------------------------------------
    # Run all checks
    # ------------------------------------------------------------------
    results: list[CheckResult] = [
        _check_splits_exist(processed_dir),
        _check_label_image_alignment(processed_dir, raw_dir),
        _check_valid_class_ids(processed_dir, n_classes),
        _check_no_empty_labels(processed_dir),
        _check_dataset_yaml(yaml_path),
    ]

    # ------------------------------------------------------------------
    # Results table
    # ------------------------------------------------------------------
    print_separator("-", 60)
    print(f"  {'Check':<42} {'Result'}")
    print_separator("-", 60)

    all_passed = True
    for result in results:
        status = "PASS" if result.passed else "FAIL"
        print(f"  {result.name:<42} {status}")
        if not result.passed:
            all_passed = False
            if result.message:
                print(f"    → {result.message}")
        for warning in result.warnings:
            print(f"    ⚠  {warning}")

    print_separator("-", 60)

    # ------------------------------------------------------------------
    # Per-split label counts
    # ------------------------------------------------------------------
    print("\n  Label Counts (processed/):")
    print_separator("-", 60)
    print(f"  {'Split':<10} {'Labels':>10}")
    print_separator("-", 60)

    for split_name in SPLITS:
        labels_dir = processed_dir / split_name / "labels"
        lbl_count = len(list_labels(labels_dir))
        print(f"  {split_name:<10} {lbl_count:>10,}")

    print_separator("-", 60)

    # ------------------------------------------------------------------
    # Final verdict
    # ------------------------------------------------------------------
    print()
    if all_passed:
        print("  ✓  All checks passed.  Dataset is ready for training.")
        print(f"     Use: {yaml_path}")
    else:
        print("  ✗  One or more checks FAILED.  Fix the issues above before training.")
    print()

    logger.info("Verification complete. All passed: %s", all_passed)
    return all_passed


# ---------------------------------------------------------------------------
# CLI entry-point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    ok = verify_dataset()
    sys.exit(0 if ok else 1)
