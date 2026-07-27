"""
InfraGuard AI
Computer Vision — Class Filter & Label Remap

Purpose:
    Remove the "other_corruption" class from RDD2022 labels and remap
    the remaining class IDs to the contiguous 0-3 scheme used by
    InfraGuard AI.  Write a dataset.yaml that points Ultralytics at the
    raw images and the filtered labels — so images are never duplicated.

Input:
    data/raw/<split>/labels/*.txt   — original RDD2022 YOLO annotations
    data/raw/<split>/images/        — original images (read-only, never touched)

Output:
    data/processed/<split>/labels/*.txt  — filtered + remapped annotations
    data/processed/dataset.yaml          — Ultralytics training config

Responsibilities:
    1. Read every .txt label from data/raw/.
    2. Drop any row whose class ID is in REMOVED_CLASS_IDS (other_corruption = 3).
    3. Remap surviving class IDs via CLASS_REMAP.
    4. Write cleaned labels to data/processed/<split>/labels/.
    5. Write dataset.yaml with absolute image paths pointing to data/raw/.
    6. Never copy, move, or modify images.
    7. Never modify the original label files.

Execution:
    # From ai/computer_vision/
    python -m preprocessing.filter_classes
"""

import logging
from pathlib import Path

import yaml  # PyYAML — already in requirements.txt

from configs.config import (
    CLASS_NAMES,
    CLASS_REMAP,
    DATASET_YAML,
    PROCESSED_DATASET,
    RAW_DATASET,
    REMOVED_CLASS_IDS,
    SPLITS,
)
from utils.utils import (
    create_directory,
    get_logger,
    list_labels,
    parse_yolo_label,
    print_section,
    print_separator,
)

# ---------------------------------------------------------------------------
# Module logger
# ---------------------------------------------------------------------------

logger: logging.Logger = get_logger(__name__)


# ---------------------------------------------------------------------------
# Internal helpers — label processing
# ---------------------------------------------------------------------------

def _format_yolo_row(class_id: int, coords: list[float]) -> str:
    """
    Serialise one annotation back to YOLO .txt format.

    Args:
        class_id: Remapped integer class index.
        coords:   ``[cx, cy, w, h]`` as floats (normalised 0–1).

    Returns:
        String of the form ``"0 0.512345 0.487654 0.123456 0.098765"``.
    """
    coord_str = " ".join(f"{v:.6f}" for v in coords)
    return f"{class_id} {coord_str}"


def _filter_and_remap_label(
    src_label: Path,
    dst_label: Path,
) -> tuple[int, int]:
    """
    Filter and remap one YOLO label file.

    Reads *src_label*, skips rows whose class is in ``REMOVED_CLASS_IDS``,
    remaps remaining class IDs via ``CLASS_REMAP``, and writes the result
    to *dst_label*.  The destination parent directory is created if needed.

    Args:
        src_label: Source annotation file (original RDD2022 label).
        dst_label: Destination annotation file (processed label).

    Returns:
        ``(kept, dropped)`` — count of annotation rows kept and dropped.

    Raises:
        ValueError: Propagated from :func:`parse_yolo_label` on malformed input.
        OSError:    If the destination file cannot be written.
    """
    rows = parse_yolo_label(src_label)

    kept_lines: list[str] = []
    dropped = 0

    for row in rows:
        class_id = int(row[0])

        if class_id in REMOVED_CLASS_IDS:
            dropped += 1
            continue

        if class_id not in CLASS_REMAP:
            logger.warning(
                "Unexpected class ID %d in '%s' — skipping row.",
                class_id,
                src_label,
            )
            dropped += 1
            continue

        remapped_id = CLASS_REMAP[class_id]
        kept_lines.append(_format_yolo_row(remapped_id, row[1:]))

    create_directory(dst_label.parent)

    with dst_label.open("w", encoding="utf-8") as fh:
        if kept_lines:
            fh.write("\n".join(kept_lines) + "\n")
        # Empty file is valid for background images — leave blank intentionally

    return len(kept_lines), dropped


# ---------------------------------------------------------------------------
# Internal helper — dataset.yaml
# ---------------------------------------------------------------------------

def _write_dataset_yaml(
    processed_dir: Path,
    raw_dir: Path,
    class_names: list[str],
    yaml_path: Path,
) -> None:
    """
    Write the Ultralytics ``dataset.yaml`` configuration file.

    Image paths point to *raw_dir* so images are never duplicated.
    Label paths are resolved automatically by Ultralytics by replacing
    ``images`` with ``labels`` in each image path — which works correctly
    because ``processed_dir/<split>/labels/`` mirrors the structure of
    ``raw_dir/<split>/images/``.

    The ``path`` key is set to *processed_dir* so Ultralytics resolves
    relative paths from there.  Image sub-paths use absolute paths to
    *raw_dir* to avoid any ambiguity.

    Args:
        processed_dir: Root of the processed dataset (contains labels/).
        raw_dir:       Root of the raw dataset (contains images/).
        class_names:   Ordered list of class name strings.
        yaml_path:     Destination path for the YAML file.
    """
    create_directory(yaml_path.parent)

    # Use absolute paths for images so the YAML is portable regardless of
    # the working directory from which training is launched.
    data: dict = {
        "path": str(processed_dir.resolve()),
        "train": str((raw_dir / "train" / "images").resolve()),
        "val":   str((raw_dir / "val"   / "images").resolve()),
        "test":  str((raw_dir / "test"  / "images").resolve()),
        "nc": len(class_names),
        "names": class_names,
    }

    with yaml_path.open("w", encoding="utf-8") as fh:
        yaml.dump(data, fh, default_flow_style=False, sort_keys=False)

    logger.info("dataset.yaml written → %s", yaml_path)


# ---------------------------------------------------------------------------
# Internal helper — dataset root resolution
# ---------------------------------------------------------------------------

def _resolve_raw_root(raw_dir: Path) -> Path:
    """
    Locate the actual split root inside *raw_dir*.

    Kaggle sometimes extracts the archive into a sub-folder (e.g.
    ``raw/rdd2022/``).  This function checks *raw_dir* itself first,
    then one level deeper.

    Args:
        raw_dir: Configured ``RAW_DATASET`` path.

    Returns:
        Resolved dataset root that contains train/val/test.

    Raises:
        FileNotFoundError: If no split directories are found.
    """
    if any((raw_dir / s).exists() for s in SPLITS):
        return raw_dir

    for candidate in sorted(raw_dir.iterdir()):
        if candidate.is_dir() and any((candidate / s).exists() for s in SPLITS):
            return candidate

    raise FileNotFoundError(
        f"Cannot find split directories {SPLITS} inside '{raw_dir}'.\n"
        "Run download_dataset.py first."
    )


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def filter_classes(
    raw_dir: Path = RAW_DATASET,
    processed_dir: Path = PROCESSED_DATASET,
    yaml_path: Path = DATASET_YAML,
    *,
    skip_if_exists: bool = True,
) -> Path:
    """
    Filter and remap all RDD2022 labels, then write ``dataset.yaml``.

    For each split the function:

    * Reads every ``.txt`` label from ``raw_dir/<split>/labels/``.
    * Drops rows for classes listed in ``REMOVED_CLASS_IDS``.
    * Remaps surviving class IDs via ``CLASS_REMAP``.
    * Writes cleaned labels to ``processed_dir/<split>/labels/``.

    After processing all splits it writes a ``dataset.yaml`` whose image
    paths reference ``raw_dir`` directly — so **no images are ever copied**.

    Args:
        raw_dir:        Source directory containing the extracted dataset.
                        Defaults to ``RAW_DATASET`` from ``config.py``.
        processed_dir:  Destination for filtered labels and ``dataset.yaml``.
                        Defaults to ``PROCESSED_DATASET`` from ``config.py``.
        yaml_path:      Path where ``dataset.yaml`` will be written.
                        Defaults to ``DATASET_YAML`` from ``config.py``.
        skip_if_exists: When ``True`` and *processed_dir* already contains
                        files, the entire operation is skipped.  Set to
                        ``False`` to force a re-run.

    Returns:
        Path to *processed_dir*.

    Raises:
        FileNotFoundError: If *raw_dir* does not exist or contains no splits.
    """
    print_section("Filter Classes & Remap Labels")

    # ------------------------------------------------------------------
    # Guard — raw dataset must exist
    # ------------------------------------------------------------------
    if not raw_dir.exists():
        raise FileNotFoundError(
            f"Raw dataset not found: '{raw_dir}'\n"
            "Run download_dataset.py first."
        )

    # ------------------------------------------------------------------
    # Guard — skip if already processed
    # ------------------------------------------------------------------
    if skip_if_exists and processed_dir.exists() and any(processed_dir.rglob("*.txt")):
        logger.info(
            "Processed labels already exist in '%s' — skipping.",
            processed_dir,
        )
        logger.info("Set skip_if_exists=False to force re-processing.")
        return processed_dir

    # ------------------------------------------------------------------
    # Resolve actual dataset root (handles Kaggle sub-folder extraction)
    # ------------------------------------------------------------------
    dataset_root = _resolve_raw_root(raw_dir)

    create_directory(processed_dir)

    logger.info("Raw dataset root : %s", dataset_root)
    logger.info("Processed dir    : %s", processed_dir)
    logger.info("Removing class IDs : %s  (other_corruption)", sorted(REMOVED_CLASS_IDS))
    logger.info("Remap table        : %s", CLASS_REMAP)
    logger.info("Output class names : %s", CLASS_NAMES)
    logger.info("Images stay in raw/ — no duplication.")

    total_kept = 0
    total_dropped = 0
    total_labels = 0

    # ------------------------------------------------------------------
    # Process each split
    # ------------------------------------------------------------------
    for split_name in SPLITS:
        split_src = dataset_root / split_name
        if not split_src.exists():
            logger.warning("Split '%s' not found in raw/ — skipping.", split_name)
            continue

        labels_src = split_src / "labels"
        labels_dst = processed_dir / split_name / "labels"

        src_labels = list_labels(labels_src)
        split_kept = 0
        split_dropped = 0

        logger.info(
            "Processing split '%-5s' — %d label files …",
            split_name, len(src_labels),
        )

        for src_label in src_labels:
            rel = src_label.relative_to(labels_src)
            dst_label = labels_dst / rel

            try:
                kept, dropped = _filter_and_remap_label(src_label, dst_label)
                split_kept += kept
                split_dropped += dropped
            except (ValueError, OSError) as exc:
                logger.error("Failed to process '%s': %s", src_label, exc)

        total_kept += split_kept
        total_dropped += split_dropped
        total_labels += len(src_labels)

        print_separator("-", 60)
        print(f"  Split   : {split_name}")
        print(f"  Labels  : {len(src_labels):,} files processed")
        print(f"  Kept    : {split_kept:,} annotations")
        print(f"  Dropped : {split_dropped:,} annotations  (other_corruption)")

    # ------------------------------------------------------------------
    # Write dataset.yaml
    # ------------------------------------------------------------------
    _write_dataset_yaml(processed_dir, dataset_root, CLASS_NAMES, yaml_path)

    # ------------------------------------------------------------------
    # Final summary
    # ------------------------------------------------------------------
    print_separator()
    print(f"  Total label files : {total_labels:,}")
    print(f"  Total kept        : {total_kept:,} annotations")
    print(f"  Total dropped     : {total_dropped:,} annotations")
    print(f"  Images            : untouched in raw/")
    print(f"  Filtered labels   : {processed_dir}")
    print(f"  dataset.yaml      : {yaml_path}")
    print_separator()

    logger.info("filter_classes complete.")
    return processed_dir


# ---------------------------------------------------------------------------
# CLI entry-point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    filter_classes()
